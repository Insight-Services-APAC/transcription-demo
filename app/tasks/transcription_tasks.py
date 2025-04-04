import os
import logging
import time
import traceback
import sys
import json
from celery import shared_task
from app.extensions import db
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.services.batch_transcription_service import BatchTranscriptionService
from flask import current_app
from datetime import datetime, timedelta
from app.errors.exceptions import (
    TranscriptionError,
    StorageError,
    DatabaseError,
    ResourceNotFoundError,
)
from app.errors.logger import log_exception

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("transcription_tasks.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("app.tasks.transcription")


def get_blob_service():
    logger.debug("Initializing blob service")
    try:
        return BlobStorageService(
            connection_string=current_app.config["AZURE_STORAGE_CONNECTION_STRING"],
            container_name=current_app.config["AZURE_STORAGE_CONTAINER"],
        )
    except Exception as e:
        log_exception(e, logger)
        raise StorageError(
            f"Failed to initialize blob storage service: {str(e)}",
            service="azure_storage",
        )


@shared_task
def transcribe_file(file_id, model_locale=None):
    """
    Main Celery task that orchestrates the batch transcription pipeline
    using Azure's Speech Service Batch Transcription API.
    """
    logger.info(f"=== Starting transcription pipeline for file {file_id} ===")
    start_time = time.time()
    
    # Create new session to avoid transaction conflicts
    file = None
    try:
        file = db.session.query(File).filter(File.id == file_id).first()
        if not file:
            logger.error(f"File with ID {file_id} not found in DB.")
            return {"status": "error", "message": f"No File with ID {file_id}"}
    except Exception as e:
        log_exception(e, logger)
        return {
            "status": "error",
            "message": f"Database error looking up file: {str(e)}",
        }
        
    # Update file status with safe transaction handling
    try:
        # Use session.begin() for automatic transaction management
        with db.session.begin():
            # Refresh the object to ensure we have the latest state
            file.status = "processing"
            file.current_stage = "transcribing"
            file.progress_percent = 10
        logger.info(f"File {file_id} set to processing state.")
    except Exception as e:
        log_exception(e, logger)
        db.session.rollback()  # Explicit rollback on error
        logger.error(f"Failed to update file status, rolled back transaction: {str(e)}")
        return {
            "status": "error",
            "message": f"Database error updating file status: {str(e)}",
        }
    
    try:
        subscription_key = current_app.config["AZURE_SPEECH_KEY"]
        region = current_app.config["AZURE_SPEECH_REGION"]
        if not subscription_key or not region:
            raise TranscriptionError(
                "Missing Azure Speech API configuration. Check AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.",
                service="azure_speech",
            )
        transcription_service = BatchTranscriptionService(
            subscription_key, region, locale=model_locale
        )
        model_id = file.model_id
        if model_id:
            logger.info(
                f"Using specified model: {model_id} ({file.model_name or 'unknown'})"
            )
            if model_locale:
                logger.info(f"Using locale: {model_locale}")
        else:
            logger.info("Using default model (no specific model requested)")
        logger.info(f"Submitting batch transcription for blob: {file.blob_url}")
        result_job = transcription_service.submit_transcription(
            audio_url=file.blob_url,
            enable_diarization=True,
            model_id=model_id,
            locale=model_locale,
        )
        transcription_id = result_job["id"]
        
        try:
            with db.session.begin():
                file.transcription_id = transcription_id
            logger.info(f"Updated file with transcription_id: {transcription_id}")
        except Exception as e:
            log_exception(e, logger)
            db.session.rollback()
            logger.error(f"Failed to update transcription ID, continuing anyway: {str(e)}")
        
        try:
            with db.session.begin():
                file.progress_percent = 50
            logger.info(f"Updated progress to 50% for file {file_id}")
        except Exception as e:
            log_exception(e, logger)
            db.session.rollback()
            logger.error(f"Failed to update progress, continuing anyway: {str(e)}")
            
        max_attempts = 120
        for attempt in range(max_attempts):
            status_info = transcription_service.get_transcription_status(
                transcription_id
            )
            status = status_info["status"]
            logger.info(
                f"Transcription {transcription_id} status: {status} (attempt {attempt + 1}/{max_attempts})"
            )
            if status == "Running":
                progress = min(50 + attempt / max_attempts * 40, 90)
                try:
                    with db.session.begin():
                        file = db.session.query(File).filter(File.id == file_id).first()
                        if file:
                            file.progress_percent = progress
                    logger.info(f"Updated progress to {progress:.1f}% for file {file_id}")
                except Exception as e:
                    log_exception(e, logger)
                    db.session.rollback()
                    logger.error(f"Failed to update progress, continuing anyway: {str(e)}")
                    
            if status == "Succeeded":
                logger.info("Transcription succeeded; fetching final JSON result.")
                try:
                    with db.session.begin():
                        file = db.session.query(File).filter(File.id == file_id).first()
                        if file:
                            file.progress_percent = 95
                    logger.info(f"Updated progress to 95% for file {file_id}")
                except Exception as e:
                    log_exception(e, logger)
                    db.session.rollback()
                    logger.error(f"Failed to update progress, continuing anyway: {str(e)}")
                    
                logger.info(
                    "Retrieving final transcription JSON for job %s", transcription_id
                )
                result_json = transcription_service.get_transcription_result(
                    transcription_id
                )
                logger.info("Uploading final transcription JSON to Azure Blob.")
                blob_service = get_blob_service()
                base_name = os.path.splitext(os.path.basename(file.filename))[0]
                json_blob_path = f"{base_name}/transcript/final.json"
                text_json = json.dumps(result_json, indent=2)
                transcript_url = blob_service.upload_bytes(
                    text_json.encode("utf-8"), json_blob_path, "application/json"
                )
                
                try:
                    # Use session.begin() for automatic transaction management
                    with db.session.begin():
                        file = db.session.query(File).filter(File.id == file_id).first()
                        if not file:
                            logger.error(f"File {file_id} no longer exists in database")
                            raise ResourceNotFoundError(f"File with ID {file_id} not found")
                        
                        file.transcript_url = transcript_url
                        file.status = "completed"
                        file.progress_percent = 100
                        
                        # Extract metadata from the transcript
                        try:
                            if "durationInTicks" in result_json:
                                duration_seconds = result_json["durationInTicks"] / 10000000.0
                                file.duration_seconds = str(
                                    timedelta(seconds=int(duration_seconds))
                                )
                            if "recognizedPhrases" in result_json:
                                speakers = set()
                                for phrase in result_json["recognizedPhrases"]:
                                    if "speaker" in phrase:
                                        speakers.add(phrase["speaker"])
                                if speakers:
                                    file.speaker_count = str(len(speakers))
                                word_confidences = []
                                for phrase in result_json["recognizedPhrases"]:
                                    if (
                                        phrase.get("recognitionStatus") == "Success"
                                        and phrase.get("nBest")
                                        and (len(phrase["nBest"]) > 0)
                                    ):
                                        best_result = phrase["nBest"][0]
                                        if "words" in best_result:
                                            for word in best_result["words"]:
                                                if "confidence" in word:
                                                    word_confidences.append(
                                                        word.get("confidence", 0)
                                                    )
                                if word_confidences:
                                    avg_accuracy = (
                                        sum(word_confidences) / len(word_confidences) * 100
                                    )
                                    file.accuracy_percent = round(avg_accuracy, 2)
                                    logger.info(
                                        f"Calculated average accuracy: {file.accuracy_percent}%"
                                    )
                        except Exception as meta_err:
                            logger.error(f"Metadata extraction error: {str(meta_err)}")
                    
                    logger.info(f"Successfully updated file record with transcript data")
                except Exception as db_error:
                    log_exception(db_error, logger)
                    db.session.rollback()
                    logger.error(f"Database error saving transcript data: {str(db_error)}")
                    # Even though DB update failed, we completed transcription
                    
                total_time = time.time() - start_time
                logger.info(
                    f"Transcription pipeline completed for file {file_id} in {total_time:.2f} seconds."
                )
                return {
                    "status": "success",
                    "file_id": file_id,
                    "transcript_url": transcript_url,
                }
            if status == "Failed":
                error = status_info.get("properties", {}).get("error", {})
                error_message = error.get("message", "Unknown error")
                logger.error(f"Transcription failed for {file_id}: {error_message}")
                
                try:
                    with db.session.begin():
                        file = db.session.query(File).filter(File.id == file_id).first()
                        if file:
                            file.status = "error"
                            file.error_message = f"Transcription failed: {error_message}"
                    logger.info(f"Updated file status to error")
                except Exception as e:
                    log_exception(e, logger)
                    db.session.rollback()
                    logger.error(f"Failed to update file error status: {str(e)}")
                
                return {"status": "error", "message": error_message}
            time.sleep(60)
        
        logger.error(f"Transcription timed out for {file_id} after 2 hours.")
        try:
            with db.session.begin():
                file = db.session.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = "error"
                    file.error_message = "Transcription timed out after 2 hours"
            logger.info(f"Updated file status to error (timeout)")
        except Exception as e:
            log_exception(e, logger)
            db.session.rollback()
            logger.error(f"Failed to update file error status: {str(e)}")
            
        return {"status": "error", "message": "Transcription timed out"}
    except TranscriptionError as te:
        logger.error(f"TranscriptionError in task for file {file_id}: {str(te)}")
        try:
            with db.session.begin():
                file = db.session.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = "error"
                    file.error_message = str(te)
            logger.info(f"Updated file status to error (TranscriptionError)")
        except Exception as e:
            log_exception(e, logger)
            db.session.rollback()
            logger.error(f"Failed to update file error status: {str(e)}")
            
        return {"status": "error", "message": str(te), "code": te.error_code}
    except StorageError as se:
        logger.error(f"StorageError in task for file {file_id}: {str(se)}")
        try:
            with db.session.begin():
                file = db.session.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = "error"
                    file.error_message = str(se)
            logger.info(f"Updated file status to error (StorageError)")
        except Exception as e:
            log_exception(e, logger)
            db.session.rollback()
            logger.error(f"Failed to update file error status: {str(e)}")
            
        return {"status": "error", "message": str(se), "code": se.error_code}
    except DatabaseError as de:
        logger.error(f"DatabaseError in task for file {file_id}: {str(de)}")
        try:
            with db.session.begin():
                file = db.session.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = "error"
                    file.error_message = str(de)
        except:
            db.session.rollback()
            pass
        return {"status": "error", "message": str(de), "code": de.error_code}
    except Exception as e:
        logger.error(f"Unhandled exception in task for file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        try:
            with db.session.begin():
                file = db.session.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = "error"
                    file.error_message = f"Unexpected error: {str(e)}"
            logger.info(f"Updated file status to error (unexpected exception)")
        except Exception as db_err:
            log_exception(db_err, logger)
            db.session.rollback()
            logger.error(f"Failed to update file error status: {str(db_err)}")
            
        return {"status": "error", "message": str(e)}