import os
import tempfile
import json
import logging
import time
import traceback
import sys
from celery import shared_task, chain, group
from app.models import db_session
from app.models.file import File
from app.services.audio_processor import AudioProcessor
from app.services.speech_service import SpeechService
from app.services.diarization_service import DiarizationService
from app.services.transcript_stitcher import TranscriptStitcher
from app.services.blob_storage import BlobStorageService
import shutil
from flask import current_app

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('transcription_tasks.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('transcription_tasks')

# Initialize services


def get_blob_service():
    logger.debug("Initializing blob service")
    return BlobStorageService(
        connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
        container_name=current_app.config['AZURE_STORAGE_CONTAINER']
    )


def get_audio_processor():
    logger.debug("Initializing audio processor")
    return AudioProcessor(
        chunk_size_seconds=current_app.config['CHUNK_SIZE_SECONDS'],
        chunk_overlap_seconds=current_app.config['CHUNK_OVERLAP_SECONDS']
    )


def get_speech_service():
    logger.debug("Initializing speech service")
    return SpeechService(
        speech_key=current_app.config['AZURE_SPEECH_KEY'],
        speech_region=current_app.config['AZURE_SPEECH_REGION']
    )


def get_diarization_service():
    logger.debug("Initializing diarization service")
    return DiarizationService(
        auth_token=current_app.config['PYANNOTE_AUTH_TOKEN']
    )


def get_transcript_stitcher():
    logger.debug("Initializing transcript stitcher")
    return TranscriptStitcher()


def update_progress(file_id, stage, stage_progress, overall_progress=None):
    """Helper function to update progress in the database"""
    logger.debug(
        f"Updating progress for file {file_id}: stage={stage}, progress={stage_progress}%, overall={overall_progress}%")
    try:
        file = db_session.query(File).filter(File.id == file_id).first()

        if file:
            file.current_stage = stage
            file.stage_progress = stage_progress

            if overall_progress is not None:
                file.progress_percent = overall_progress

            db_session.commit()
            logger.debug(f"Progress updated successfully for file {file_id}")
        else:
            logger.warning(
                f"File with ID {file_id} not found when updating progress")
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        logger.error(traceback.format_exc())

    return file


@shared_task
def transcribe_file(file_id):
    """Main task that orchestrates the transcription pipeline"""
    logger.info(f"=== Starting transcription pipeline for file {file_id} ===")
    start_time = time.time()

    # Update file status to processing
    try:
        file = db_session.query(File).filter(File.id == file_id).first()

        if not file:
            logger.error(f"File with ID {file_id} not found")
            return {"status": "error", "message": f"File with ID {file_id} not found"}

        logger.info(f"Found file: {file.filename}")
        file.status = "processing"
        file.current_stage = "queued"
        file.progress_percent = 0
        db_session.commit()
        logger.info(f"Updated file status to 'processing'")

        try:
            # Create workflow
            logger.info("Setting up transcription workflow chain")
            workflow = chain(
                extract_audio.s(file_id),
                chunk_audio.s(),
                transcribe_chunks.s(file_id),
                perform_diarization.s(file_id),
                stitch_transcript.s(file_id)
            )

            # Execute workflow
            logger.info("Executing transcription workflow")
            result = workflow.apply_async()
            logger.info(f"Workflow started with task ID: {result.id}")
            logger.info(
                f"Transcription pipeline for file {file_id} initiated in {time.time() - start_time:.2f} seconds")
            return {"status": "success", "task_id": result.id}

        except Exception as e:
            # Handle any exception in the workflow
            logger.error(f"Error in transcription workflow: {str(e)}")
            logger.error(traceback.format_exc())
            file.status = "error"
            file.error_message = str(e)
            db_session.commit()
            logger.error(f"Updated file status to 'error': {str(e)}")
            return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in transcribe_file task: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


@shared_task
def extract_audio(file_id):
    """Extract audio from DCR file"""
    logger.info(f"=== Starting audio extraction for file {file_id} ===")
    start_time = time.time()

    # Update progress
    update_progress(file_id, "extract_audio", 0, 5)

    # Get file from database
    try:
        file = db_session.query(File).filter(File.id == file_id).first()

        if not file:
            logger.error(f"File with ID {file_id} not found")
            raise Exception(f"File with ID {file_id} not found")

        logger.info(f"Processing file: {file.filename}")

        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {temp_dir}")

        try:
            # Get blob service
            logger.info("Initializing blob service")
            blob_service = get_blob_service()

            # Update progress
            update_progress(file_id, "extract_audio", 20, 8)

            # Download DCR file from blob storage
            logger.info(
                f"Downloading DCR file from blob storage: {file.filename}")
            download_start = time.time()
            dcr_path = os.path.join(temp_dir, os.path.basename(file.filename))
            blob_service.download_file(
                os.path.basename(file.filename), dcr_path)
            download_time = time.time() - download_start

            # Check file size for logging
            file_size = os.path.getsize(
                dcr_path) if os.path.exists(dcr_path) else 0
            logger.info(
                f"Downloaded file size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
            logger.info(f"Download completed in {download_time:.2f} seconds")

            # Update progress
            update_progress(file_id, "extract_audio", 50, 12)

            # Extract audio
            logger.info("Extracting audio from DCR file")
            extract_start = time.time()
            audio_processor = get_audio_processor()
            wav_path = os.path.join(temp_dir, os.path.splitext(
                os.path.basename(file.filename))[0] + '.wav')
            audio_processor.extract_audio(dcr_path, wav_path)
            extract_time = time.time() - extract_start

            # Check WAV file size
            wav_size = os.path.getsize(
                wav_path) if os.path.exists(wav_path) else 0
            logger.info(
                f"Extracted WAV file size: {wav_size} bytes ({wav_size / (1024 * 1024):.2f} MB)")
            logger.info(
                f"Audio extraction completed in {extract_time:.2f} seconds")

            # Update progress
            update_progress(file_id, "extract_audio", 80, 16)

            # Upload WAV file to blob storage
            logger.info("Uploading WAV file to blob storage")
            upload_start = time.time()
            wav_blob_path = os.path.splitext(
                os.path.basename(file.filename))[0] + '.wav'
            audio_url = blob_service.upload_file(wav_path, wav_blob_path)
            upload_time = time.time() - upload_start
            logger.info(f"WAV upload completed in {upload_time:.2f} seconds")

            # Update file in database
            logger.info(f"Updating file record with audio URL: {audio_url}")
            file.audio_url = audio_url
            db_session.commit()

            # Update progress
            update_progress(file_id, "extract_audio", 100, 20)

            total_time = time.time() - start_time
            logger.info(
                f"Audio extraction completed in {total_time:.2f} seconds")

            # Return audio path and temp_dir
            return {
                "file_id": file_id,
                "audio_path": wav_path,
                "audio_blob_path": wav_blob_path,
                "temp_dir": temp_dir
            }

        except Exception as e:
            # Clean up temp directory
            logger.error(f"Error in audio extraction: {str(e)}")
            logger.error(traceback.format_exc())
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

            # Update file status
            file.status = "error"
            file.error_message = f"Error extracting audio: {str(e)}"
            db_session.commit()
            logger.error(f"Updated file status to 'error'")

            raise Exception(f"Error extracting audio: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in extract_audio task: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@shared_task
def chunk_audio(previous_result):
    """Split audio into chunks"""
    file_id = previous_result.get("file_id", None)
    logger.info(f"=== Starting audio chunking for file {file_id} ===")
    start_time = time.time()

    audio_path = previous_result["audio_path"]
    temp_dir = previous_result["temp_dir"]

    logger.info(f"Input audio path: {audio_path}")
    logger.info(f"Temp directory: {temp_dir}")

    try:
        # Get file from database for progress updates
        file = None
        if file_id:
            file = db_session.query(File).filter(File.id == file_id).first()
            if file:
                logger.info(f"Found file record: {file.filename}")
            else:
                logger.warning(f"File record not found for ID: {file_id}")
            update_progress(file_id, "chunk_audio", 0, 25)

        # Create chunks directory
        chunks_dir = os.path.join(temp_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        logger.info(f"Created chunks directory: {chunks_dir}")

        # Chunk audio
        logger.info("Starting audio chunking process")
        chunk_start = time.time()
        audio_processor = get_audio_processor()
        chunk_paths = audio_processor.chunk_audio(audio_path, chunks_dir)
        chunk_time = time.time() - chunk_start

        # Log chunk information
        num_chunks = len(chunk_paths)
        logger.info(
            f"Created {num_chunks} audio chunks in {chunk_time:.2f} seconds")
        for i, path in enumerate(chunk_paths):
            chunk_size = os.path.getsize(path) if os.path.exists(path) else 0
            logger.debug(
                f"Chunk {i+1}/{num_chunks}: {path} - Size: {chunk_size/1024:.2f} KB")

        # Update progress and store chunk count
        if file_id and file:
            file.chunk_count = num_chunks
            file.chunks_processed = 0
            db_session.commit()
            logger.info(f"Updated file record with chunk count: {num_chunks}")
            update_progress(file_id, "chunk_audio", 100, 30)

        total_time = time.time() - start_time
        logger.info(f"Audio chunking completed in {total_time:.2f} seconds")

        # Return results
        return {
            **previous_result,
            "file_id": file_id,  # Pass file_id along
            "chunk_paths": chunk_paths,
            "chunks_dir": chunks_dir
        }

    except Exception as e:
        # Clean up temp directory
        logger.error(f"Error in audio chunking: {str(e)}")
        logger.error(traceback.format_exc())
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")

        # Update file status if we have file_id
        if file_id:
            file = db_session.query(File).filter(File.id == file_id).first()
            if file:
                file.status = "error"
                file.error_message = f"Error chunking audio: {str(e)}"
                db_session.commit()
                logger.error(f"Updated file status to 'error'")

        raise Exception(f"Error chunking audio: {str(e)}")


@shared_task
def transcribe_chunks(previous_result, file_id):
    """Transcribe audio chunks using Azure STT"""
    logger.info(f"=== Starting chunk transcription for file {file_id} ===")
    start_time = time.time()

    chunk_paths = previous_result["chunk_paths"]
    temp_dir = previous_result["temp_dir"]

    logger.info(f"Number of chunks to transcribe: {len(chunk_paths)}")
    logger.info(f"Temp directory: {temp_dir}")

    try:
        # Get file for progress tracking
        file = db_session.query(File).filter(File.id == file_id).first()
        if not file:
            logger.error(f"File with ID {file_id} not found")
            raise Exception(f"File with ID {file_id} not found")

        logger.info(f"Processing file: {file.filename}")

        # Update initial progress
        update_progress(file_id, "transcribe_chunks", 0, 35)

        # Get speech service
        logger.info("Initializing speech service")
        speech_service = get_speech_service()

        # Transcribe each chunk
        chunk_transcripts = []
        total_chunks = len(chunk_paths)
        file.chunk_count = total_chunks
        db_session.commit()
        logger.info(f"Updated file record with total chunks: {total_chunks}")

        for i, chunk_path in enumerate(chunk_paths):
            chunk_start = time.time()
            logger.info(
                f"Transcribing chunk {i+1}/{total_chunks}: {os.path.basename(chunk_path)}")

            # Transcribe chunk
            try:
                transcript = speech_service.transcribe_audio_file(chunk_path)
                chunk_transcripts.append(transcript)

                # Log transcript details
                transcript_word_count = len(
                    transcript.split()) if isinstance(transcript, str) else 0
                logger.info(
                    f"Chunk {i+1} transcribed successfully: {transcript_word_count} words")
                logger.debug(f"Transcript: {transcript[:100]}..." if isinstance(
                    transcript, str) and len(transcript) > 100 else transcript)

            except Exception as e:
                logger.error(f"Error transcribing chunk {i+1}: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue with other chunks but note the error
                # Empty transcript for failed chunk
                chunk_transcripts.append("")

            # Update progress
            file.chunks_processed = i + 1
            progress_pct = ((i + 1) / total_chunks) * 100
            overall_progress = 35 + ((i + 1) / total_chunks) * 25  # 35% to 60%
            update_progress(file_id, "transcribe_chunks",
                            progress_pct, overall_progress)

            chunk_time = time.time() - chunk_start
            logger.info(f"Chunk {i+1} transcribed in {chunk_time:.2f} seconds")

        # Create transcripts directory
        transcripts_dir = os.path.join(temp_dir, "transcripts")
        os.makedirs(transcripts_dir, exist_ok=True)
        logger.info(f"Created transcripts directory: {transcripts_dir}")

        # Save raw transcriptions
        logger.info("Saving chunk transcripts to JSON files")
        transcript_paths = []
        for i, transcript in enumerate(chunk_transcripts):
            transcript_path = os.path.join(
                transcripts_dir, f"chunk_{i:03d}.json")
            with open(transcript_path, 'w') as f:
                json.dump({
                    "chunk_index": i,
                    "transcript": transcript
                }, f)
            transcript_paths.append(transcript_path)

        logger.info(f"Saved {len(transcript_paths)} transcript files")

        # Return paths and continue
        total_time = time.time() - start_time
        logger.info(
            f"Chunk transcription completed in {total_time:.2f} seconds")

        return {
            **previous_result,
            "transcript_paths": transcript_paths,
            "transcripts_dir": transcripts_dir
        }

    except Exception as e:
        # Clean up temp directory
        logger.error(f"Error in chunk transcription: {str(e)}")
        logger.error(traceback.format_exc())
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")

        # Update file status
        file = db_session.query(File).filter(File.id == file_id).first()
        if file:
            file.status = "error"
            file.error_message = f"Error transcribing chunks: {str(e)}"
            db_session.commit()
            logger.error(f"Updated file status to 'error'")

        raise Exception(f"Error transcribing chunks: {str(e)}")


@shared_task
def perform_diarization(previous_result, file_id):
    """Perform speaker diarization"""
    audio_path = previous_result["audio_path"]
    temp_dir = previous_result["temp_dir"]

    try:
        # Update progress
        update_progress(file_id, "diarization", 0, 60)

        # Get diarization service
        diarization_service = get_diarization_service()

        # Update progress - diarization initialization
        update_progress(file_id, "diarization", 20, 65)

        # Perform diarization
        diarization_segments = diarization_service.diarize(audio_path)

        # Update progress - diarization complete
        update_progress(file_id, "diarization", 75, 75)

        # Create diarization directory
        diarization_dir = os.path.join(temp_dir, "diarization")
        os.makedirs(diarization_dir, exist_ok=True)

        # Save diarization results
        diarization_path = os.path.join(diarization_dir, "diarization.json")
        diarization_service.save_diarization(
            diarization_segments, diarization_path)

        # Upload diarization results to blob storage
        blob_service = get_blob_service()
        file = db_session.query(File).filter(File.id == file_id).first()

        diarization_blob_path = os.path.splitext(os.path.basename(file.filename))[
            0] + '/diarization/diarization.json'
        diarization_url = blob_service.upload_file(
            diarization_path, diarization_blob_path)

        # Update file in database
        file.diarization_url = diarization_url
        file.speaker_count = str(
            len(set(segment['speaker'] for segment in diarization_segments)))
        db_session.commit()

        # Update progress - upload complete
        update_progress(file_id, "diarization", 100, 80)

        # Return results
        return {
            **previous_result,
            "diarization_segments": diarization_segments,
            "diarization_path": diarization_path,
            "diarization_blob_path": diarization_blob_path
        }

    except Exception as e:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Update file status
        file = db_session.query(File).filter(File.id == file_id).first()
        if file:
            file.status = "error"
            file.error_message = f"Error performing diarization: {str(e)}"
            db_session.commit()

        raise Exception(f"Error performing diarization: {str(e)}")


@shared_task
def stitch_transcript(previous_result, file_id):
    """Stitch together the transcripts and apply diarization"""
    chunk_transcripts = previous_result["chunk_transcripts"]
    diarization_segments = previous_result["diarization_segments"]
    temp_dir = previous_result["temp_dir"]

    try:
        # Update progress
        update_progress(file_id, "stitch_transcript", 0, 80)

        # Get transcript stitcher
        transcript_stitcher = get_transcript_stitcher()

        # Update progress - stitching in progress
        update_progress(file_id, "stitch_transcript", 30, 85)

        # Stitch transcript
        stitched_transcript = transcript_stitcher.stitch(
            chunk_transcripts, diarization_segments)

        # Update progress - stitching complete
        update_progress(file_id, "stitch_transcript", 60, 90)

        # Create final transcript directory
        transcript_dir = os.path.join(temp_dir, "transcript")
        os.makedirs(transcript_dir, exist_ok=True)

        # Save final transcript
        json_path = os.path.join(transcript_dir, "final.json")
        txt_path = os.path.join(transcript_dir, "final.txt")
        transcript_stitcher.save_transcript(
            stitched_transcript, json_path, txt_path)

        # Update progress - saving complete
        update_progress(file_id, "stitch_transcript", 80, 95)

        # Upload final transcript to blob storage
        blob_service = get_blob_service()
        file = db_session.query(File).filter(File.id == file_id).first()

        json_blob_path = os.path.splitext(os.path.basename(file.filename))[
            0] + '/transcript/final.json'
        txt_blob_path = os.path.splitext(os.path.basename(file.filename))[
            0] + '/transcript/final.txt'

        json_url = blob_service.upload_file(json_path, json_blob_path)
        txt_url = blob_service.upload_file(txt_path, txt_blob_path)

        # Update file in database
        file.transcript_url = json_url
        file.status = "completed"
        file.progress_percent = 100
        db_session.commit()

        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Return result
        return {
            "status": "success",
            "file_id": file_id,
            "transcript_url": json_url,
            "transcript_txt_url": txt_url
        }

    except Exception as e:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Update file status
        file = db_session.query(File).filter(File.id == file_id).first()
        if file:
            file.status = "error"
            file.error_message = f"Error stitching transcript: {str(e)}"
            db_session.commit()

        raise Exception(f"Error stitching transcript: {str(e)}")
