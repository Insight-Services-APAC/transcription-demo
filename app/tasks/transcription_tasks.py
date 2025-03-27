import os
import logging
import time
import traceback
import sys
import json
from celery import shared_task
from app.models import db_session
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.services.batch_transcription_service import BatchTranscriptionService
from flask import current_app
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import datetime, timedelta


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("transcription_tasks.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("transcription_tasks")


def get_db_session():
    """
    Get a fresh database session for the Celery task context.
    """
    from app.models import db_session, engine
    if db_session is None or not hasattr(db_session, "is_active") or not db_session.is_active:
        return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    return db_session


def get_blob_service():
    logger.debug("Initializing blob service")
    return BlobStorageService(
        connection_string=current_app.config["AZURE_STORAGE_CONNECTION_STRING"],
        container_name=current_app.config["AZURE_STORAGE_CONTAINER"]
    )


@shared_task
def transcribe_file(file_id):
    """
    Main Celery task that orchestrates the batch transcription pipeline 
    using Azure's Speech Service Batch Transcription API.
    """
    logger.info(f"=== Starting transcription pipeline for file {file_id} ===")
    start_time = time.time()

    session = get_db_session()
    file = session.query(File).filter(File.id == file_id).first()
    if not file:
        logger.error(f"File with ID {file_id} not found in DB.")
        return {"status": "error", "message": f"No File with ID {file_id}"}

    # Mark file as processing
    file.status = "processing"
    file.current_stage = "transcribing"
    file.progress_percent = 10
    session.commit()
    logger.info(f"File {file_id} set to processing state.")

    try:
        subscription_key = current_app.config["AZURE_SPEECH_KEY"]
        region = current_app.config["AZURE_SPEECH_REGION"]

        # Create the batch service instance
        transcription_service = BatchTranscriptionService(subscription_key, region)

        # Submit transcription job
        logger.info(f"Submitting batch transcription for blob: {file.blob_url}")
        result_job = transcription_service.submit_transcription(
            audio_url=file.blob_url,
            locale="en-US",
            enable_diarization=True
        )

        transcription_id = result_job["id"]
        file.transcription_id = transcription_id
        session.commit()

        # Poll for status
        file.progress_percent = 50
        session.commit()

        max_attempts = 120  # poll up to 120 times (2 hours at 60s intervals)
        for attempt in range(max_attempts):
            status_info = transcription_service.get_transcription_status(transcription_id)
            status = status_info["status"]
            logger.info(
                f"Transcription {transcription_id} status: {status} "
                f"(attempt {attempt+1}/{max_attempts})"
            )

            # Update file progress
            if status == "Running":
                # Synthetic ramp from 50% to 90% as we wait
                progress = min(50 + (attempt / max_attempts) * 40, 90)
                file.progress_percent = progress
                session.commit()

            if status == "Succeeded":
                logger.info("Transcription succeeded; fetching final JSON result.")
                file.progress_percent = 95
                session.commit()

                # Retrieve final transcription JSON
                logger.info("Retrieving final transcription JSON for job %s", transcription_id)
                result_json = transcription_service.get_transcription_result(transcription_id)

                # Store the JSON in Blob Storage
                logger.info("Uploading final transcription JSON to Azure Blob.")
                blob_service = get_blob_service()
                base_name = os.path.splitext(os.path.basename(file.filename))[0]
                json_blob_path = f"{base_name}/transcript/final.json"

                # convert to nicely formatted JSON
                text_json = json.dumps(result_json, indent=2)
                transcript_url = blob_service.upload_bytes(
                    text_json.encode("utf-8"), json_blob_path, "application/json"
                )

                # Update DB
                file.transcript_url = transcript_url
                file.status = "completed"
                file.progress_percent = 100

                # Extract metadata, e.g. duration & speakers
                try:
                    if "durationInTicks" in result_json:
                        # 1 tick = 100ns
                        duration_seconds = result_json["durationInTicks"] / 1e7
                        file.duration_seconds = str(timedelta(seconds=int(duration_seconds)))
                    # find unique speaker labels if present
                    if "recognizedPhrases" in result_json:
                        speakers = set()
                        for phrase in result_json["recognizedPhrases"]:
                            if "speaker" in phrase:
                                speakers.add(phrase["speaker"])
                        if speakers:
                            file.speaker_count = str(len(speakers))
                except Exception as meta_err:
                    logger.error(f"Metadata extraction error: {str(meta_err)}")

                session.commit()
                total_time = time.time() - start_time
                logger.info(
                    f"Transcription pipeline completed for file {file_id} "
                    f"in {total_time:.2f} seconds."
                )

                return {
                    "status": "success",
                    "file_id": file_id,
                    "transcript_url": transcript_url
                }

            if status == "Failed":
                error = status_info.get("properties", {}).get("error", {})
                error_message = error.get("message", "Unknown error")
                logger.error(f"Transcription failed for {file_id}: {error_message}")

                file.status = "error"
                file.error_message = f"Transcription failed: {error_message}"
                session.commit()

                return {"status": "error", "message": error_message}

            # Not done, so wait and continue
            time.sleep(60)

        # If we get here, we timed out
        logger.error(f"Transcription timed out for {file_id} after 2 hours.")
        file.status = "error"
        file.error_message = "Transcription timed out after 2 hours"
        session.commit()

        return {"status": "error", "message": "Transcription timed out"}

    except Exception as e:
        logger.error(f"Exception in transcription task for file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        file.status = "error"
        file.error_message = str(e)
        session.commit()
        return {"status": "error", "message": str(e)}