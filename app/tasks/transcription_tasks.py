import os
import tempfile
import json
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

# Initialize services
def get_blob_service():
    return BlobStorageService(
        connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
        container_name=current_app.config['AZURE_STORAGE_CONTAINER']
    )

def get_audio_processor():
    return AudioProcessor(
        chunk_size_seconds=current_app.config['CHUNK_SIZE_SECONDS'],
        chunk_overlap_seconds=current_app.config['CHUNK_OVERLAP_SECONDS']
    )

def get_speech_service():
    return SpeechService(
        speech_key=current_app.config['AZURE_SPEECH_KEY'],
        speech_region=current_app.config['AZURE_SPEECH_REGION']
    )

def get_diarization_service():
    return DiarizationService(
        auth_token=current_app.config['PYANNOTE_AUTH_TOKEN']
    )

def get_transcript_stitcher():
    return TranscriptStitcher()

@shared_task
def transcribe_file(file_id):
    """Main task that orchestrates the transcription pipeline"""
    # Update file status to processing
    file = db_session.query(File).filter(File.id == file_id).first()
    
    if not file:
        return {"status": "error", "message": f"File with ID {file_id} not found"}
    
    file.status = "processing"
    db_session.commit()
    
    try:
        # Create workflow
        workflow = chain(
            extract_audio.s(file_id),
            chunk_audio.s(),
            transcribe_chunks.s(file_id),
            perform_diarization.s(file_id),
            stitch_transcript.s(file_id)
        )
        
        # Execute workflow
        result = workflow.apply_async()
        return {"status": "success", "task_id": result.id}
        
    except Exception as e:
        # Handle any exception in the workflow
        file.status = "error"
        file.error_message = str(e)
        db_session.commit()
        return {"status": "error", "message": str(e)}

@shared_task
def extract_audio(file_id):
    """Extract audio from DCR file"""
    # Get file from database
    file = db_session.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise Exception(f"File with ID {file_id} not found")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Get blob service
        blob_service = get_blob_service()
        
        # Download DCR file from blob storage
        dcr_path = os.path.join(temp_dir, os.path.basename(file.filename))
        blob_service.download_file(os.path.basename(file.filename), dcr_path)
        
        # Extract audio
        audio_processor = get_audio_processor()
        wav_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(file.filename))[0] + '.wav')
        audio_processor.extract_audio(dcr_path, wav_path)
        
        # Upload WAV file to blob storage
        wav_blob_path = os.path.splitext(os.path.basename(file.filename))[0] + '.wav'
        audio_url = blob_service.upload_file(wav_path, wav_blob_path)
        
        # Update file in database
        file.audio_url = audio_url
        db_session.commit()
        
        # Return audio path and temp_dir
        return {
            "audio_path": wav_path,
            "audio_blob_path": wav_blob_path,
            "temp_dir": temp_dir
        }
        
    except Exception as e:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Update file status
        file.status = "error"
        file.error_message = f"Error extracting audio: {str(e)}"
        db_session.commit()
        
        raise Exception(f"Error extracting audio: {str(e)}")

@shared_task
def chunk_audio(previous_result):
    """Split audio into chunks"""
    audio_path = previous_result["audio_path"]
    temp_dir = previous_result["temp_dir"]
    
    try:
        # Create chunks directory
        chunks_dir = os.path.join(temp_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        # Chunk audio
        audio_processor = get_audio_processor()
        chunk_paths = audio_processor.chunk_audio(audio_path, chunks_dir)
        
        # Return results
        return {
            **previous_result,
            "chunk_paths": chunk_paths,
            "chunks_dir": chunks_dir
        }
        
    except Exception as e:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Error chunking audio: {str(e)}")

@shared_task
def transcribe_chunks(previous_result, file_id):
    """Transcribe audio chunks using Azure STT"""
    chunk_paths = previous_result["chunk_paths"]
    temp_dir = previous_result["temp_dir"]
    
    try:
        # Get speech service
        speech_service = get_speech_service()
        
        # Transcribe each chunk
        chunk_transcripts = []
        
        for chunk_path in chunk_paths:
            # Transcribe chunk
            transcript = speech_service.transcribe_audio_file(chunk_path)
            chunk_transcripts.append(transcript)
            
        # Create transcripts directory
        transcripts_dir = os.path.join(temp_dir, "transcripts")
        os.makedirs(transcripts_dir, exist_ok=True)
        
        # Save raw transcriptions
        for i, transcript in enumerate(chunk_transcripts):
            transcript_path = os.path.join(transcripts_dir, f"chunk_{i:03d}.json")
            with open(transcript_path, 'w') as f:
                json.dump(transcript, f, indent=2)
                
        # Return results
        return {
            **previous_result,
            "chunk_transcripts": chunk_transcripts,
            "transcripts_dir": transcripts_dir
        }
        
    except Exception as e:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Update file status
        file = db_session.query(File).filter(File.id == file_id).first()
        if file:
            file.status = "error"
            file.error_message = f"Error transcribing chunks: {str(e)}"
            db_session.commit()
            
        raise Exception(f"Error transcribing chunks: {str(e)}")

@shared_task
def perform_diarization(previous_result, file_id):
    """Perform speaker diarization"""
    audio_path = previous_result["audio_path"]
    temp_dir = previous_result["temp_dir"]
    
    try:
        # Get diarization service
        diarization_service = get_diarization_service()
        
        # Perform diarization
        diarization_segments = diarization_service.diarize(audio_path)
        
        # Create diarization directory
        diarization_dir = os.path.join(temp_dir, "diarization")
        os.makedirs(diarization_dir, exist_ok=True)
        
        # Save diarization results
        diarization_path = os.path.join(diarization_dir, "diarization.json")
        diarization_service.save_diarization(diarization_segments, diarization_path)
        
        # Upload diarization results to blob storage
        blob_service = get_blob_service()
        file = db_session.query(File).filter(File.id == file_id).first()
        
        diarization_blob_path = os.path.splitext(os.path.basename(file.filename))[0] + '/diarization/diarization.json'
        diarization_url = blob_service.upload_file(diarization_path, diarization_blob_path)
        
        # Update file in database
        file.diarization_url = diarization_url
        file.speaker_count = str(len(set(segment['speaker'] for segment in diarization_segments)))
        db_session.commit()
        
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
        # Get transcript stitcher
        transcript_stitcher = get_transcript_stitcher()
        
        # Stitch transcript
        stitched_transcript = transcript_stitcher.stitch(chunk_transcripts, diarization_segments)
        
        # Create final transcript directory
        transcript_dir = os.path.join(temp_dir, "transcript")
        os.makedirs(transcript_dir, exist_ok=True)
        
        # Save final transcript
        json_path = os.path.join(transcript_dir, "final.json")
        txt_path = os.path.join(transcript_dir, "final.txt")
        transcript_stitcher.save_transcript(stitched_transcript, json_path, txt_path)
        
        # Upload final transcript to blob storage
        blob_service = get_blob_service()
        file = db_session.query(File).filter(File.id == file_id).first()
        
        json_blob_path = os.path.splitext(os.path.basename(file.filename))[0] + '/transcript/final.json'
        txt_blob_path = os.path.splitext(os.path.basename(file.filename))[0] + '/transcript/final.txt'
        
        json_url = blob_service.upload_file(json_path, json_blob_path)
        txt_url = blob_service.upload_file(txt_path, txt_blob_path)
        
        # Update file in database
        file.transcript_url = json_url
        file.status = "completed"
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