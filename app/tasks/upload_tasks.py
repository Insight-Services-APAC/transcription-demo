import os
import time
import logging
import traceback
import uuid
from celery import shared_task
from flask import current_app
from app.extensions import db
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file
from redis import Redis
import json
from app.errors.exceptions import (
    UploadError,
    StorageError,
    DatabaseError,
    ValidationError,
)
from app.errors.logger import log_exception
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.tasks.upload")


class UploadProgressTracker:
    """Utility class to track upload progress in Redis"""

    def __init__(self, app=None):
        self.app = app or current_app._get_current_object()
        self._fallback_progress_store = {}
        try:
            # Try to get Redis URL from both new and old-style config keys
            redis_url = os.environ.get("CELERY_BROKER_URL")
            
            if not redis_url:
                logger.warning("No Redis URL configured, using in-memory storage for progress tracking")
                self.redis = None
                return
                
            # Log safely - don't show credentials in logs
            safe_url = redis_url
            if '@' in redis_url:
                parts = redis_url.split('@')
                safe_url = parts[0].split(':')[0] + "://*****@" + parts[1]
                
            logger.info(f"Connecting to Redis for progress tracking: {safe_url}")
            
            # Use same connection parameters as Celery
            from redis import Redis, from_url
            import ssl
            
            if redis_url.startswith('rediss://'):
                # Secure Redis connection (Azure Redis Cache)
                # Parse the URL manually since we need SSL options
                from urllib.parse import urlparse
                parsed = urlparse(redis_url)
                host = parsed.hostname
                port = parsed.port or 6380
                password = parsed.password
                db = int(parsed.path.lstrip('/') or 0)
                
                self.redis = Redis(
                    host=host,
                    port=port,
                    password=password,
                    db=db,
                    ssl=True,
                    ssl_cert_reqs=None  # Equivalent to ssl.CERT_NONE
                )
            else:
                # Regular Redis connection
                self.redis = from_url(redis_url)
                
            # Test the connection
            self.redis.ping()
            logger.info("Redis connected successfully for progress tracking")
            
        except Exception as e:
            logger.error(f"Redis connection failed, using in-memory fallback: {str(e)}")
            self.redis = None

    def update_progress(self, upload_id, progress_data):
        if not upload_id:
            raise ValidationError("Upload ID is required", field="upload_id")
        if not progress_data:
            raise ValidationError("Progress data is required", field="progress_data")
        
        progress_data["last_update"] = time.time()
        
        try:
            if self.redis:
                # Store in Redis if available
                self.redis.setex(
                    f"upload_progress:{upload_id}", 3600, json.dumps(progress_data)
                )
            else:
                # Fall back to in-memory storage
                self._fallback_progress_store[upload_id] = progress_data
        except Exception as e:
            logger.error(f"Error storing progress in Redis, using fallback: {str(e)}")
            self._fallback_progress_store[upload_id] = progress_data

    def get_progress(self, upload_id):
        if not upload_id:
            raise ValidationError("Upload ID is required", field="upload_id")
        
        # Try Redis first if available
        if self.redis:
            try:
                data = self.redis.get(f"upload_progress:{upload_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Error retrieving progress from Redis: {str(e)}")
        
        # Fall back to in-memory storage
        return self._fallback_progress_store.get(upload_id)

@shared_task(bind=True)
def upload_to_azure_task(
    self,
    tmp_path,
    filename,
    upload_id,
    user_id=None,
    model_id=None,
    model_name=None,
    model_locale=None,
):
    """
    Celery task to handle file upload to Azure Blob Storage.
    """
    logger.info(
        f"Starting upload task for {filename} (ID: {upload_id}, User: {user_id}, Model: {model_id}, Locale: {model_locale})"
    )
    from flask import current_app
    from app import create_app

    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    with app.app_context():
        progress_tracker = UploadProgressTracker(app)
        try:
            progress_data = {
                "status": "starting",
                "progress": 0,
                "file_path": tmp_path,
                "filename": filename,
                "azure_status": "pending",
                "stage": "preparing",
                "start_time": time.time(),
            }
            if model_id:
                progress_data["model_id"] = model_id
                progress_data["model_name"] = model_name
                progress_data["model_locale"] = model_locale
            progress_tracker.update_progress(upload_id, progress_data)
        except Exception as e:
            logger.error(f"Error updating progress tracker: {str(e)}")
        try:
            # Try different paths to find the file
            original_path = tmp_path
            file_found = False
            
            # List of potential paths to check
            potential_paths = [
                tmp_path,  # Original path as passed
                os.path.abspath(tmp_path),  # Absolute version of original path
                os.path.join(app.config["UPLOAD_FOLDER"], filename),  # File in configured upload folder
                os.path.join(os.getcwd(), tmp_path),  # Path relative to current working directory
                os.path.join(os.getcwd(), "uploads", filename),  # Common uploads folder location
            ]
            
            # Try each path
            for path in potential_paths:
                logger.info(f"Checking for file at: {path}")
                if os.path.exists(path) and os.path.isfile(path):
                    logger.info(f"✅ File found at: {path}")
                    tmp_path = path
                    file_found = True
                    break
            
            if not file_found:
                # Debug information for troubleshooting
                logger.error(f"❌ Could not find file at any of these locations:")
                for path in potential_paths:
                    logger.error(f"  - {path}")
                
                # Check if upload folder exists and list its contents
                upload_folder = app.config["UPLOAD_FOLDER"]
                logger.error(f"Upload folder config: {upload_folder}")
                logger.error(f"Current working directory: {os.getcwd()}")
                
                try:
                    if os.path.exists(upload_folder):
                        logger.error(f"Upload folder contents: {os.listdir(upload_folder)}")
                    else:
                        logger.error(f"Upload folder does not exist at: {upload_folder}")
                        # Try to create it for future uploads
                        os.makedirs(upload_folder, exist_ok=True)
                        logger.info(f"Created upload folder at: {upload_folder}")
                except Exception as e:
                    logger.error(f"Error accessing upload folder: {str(e)}")
                
                raise UploadError(
                    f"File not found at path: {original_path}", filename=filename
                )
            
            file_size = os.path.getsize(tmp_path)
            if file_size == 0:
                raise UploadError(f"File is empty (0 bytes)", filename=filename)
                
            # Continue with the rest of the function as before
            try:
                progress_tracker.update_progress(
                    upload_id,
                    {
                        "status": "uploading",
                        "progress": 0,
                        "file_path": tmp_path,
                        "filename": filename,
                        "azure_status": "in_progress",
                        "stage": "azure_upload",
                        "start_time": time.time(),
                        "file_size": file_size,
                    },
                )
            except Exception as e:
                logger.error(f"Error updating progress tracker: {str(e)}")
            try:
                blob_service = BlobStorageService(
                    connection_string=app.config["AZURE_STORAGE_CONNECTION_STRING"],
                    container_name=app.config["AZURE_STORAGE_CONTAINER"],
                )
                blob_url = blob_service.upload_file(
                    tmp_path, filename, upload_id, progress_tracker
                )
            except StorageError as se:
                raise UploadError(
                    f"Storage error during upload: {str(se)}",
                    filename=filename,
                    original_error=str(se),
                )
            try:
                session = db.session
                file_record = File(
                    filename=filename,
                    blob_url=blob_url,
                    status="processing",
                    current_stage="queued",
                    progress_percent=0.0,
                    user_id=user_id,
                    model_id=model_id,
                    model_name=model_name if model_name else "Default",
                )
                session.add(file_record)
                session.commit()
            except Exception as e:
                log_exception(e, logger)
                raise DatabaseError(
                    f"Database error creating file record: {str(e)}", filename=filename
                )
            try:
                os.remove(tmp_path)
                logger.info(f"Removed temporary file: {tmp_path}")
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            try:
                from app.tasks.transcription_tasks import transcribe_file

                transcribe_result = transcribe_file.delay(
                    file_record.id, model_locale=model_locale
                )
            except Exception as e:
                log_exception(e, logger)
                raise UploadError(
                    f"Error starting transcription task: {str(e)}",
                    filename=filename,
                    file_id=file_record.id,
                )
            try:
                progress_tracker.update_progress(
                    upload_id,
                    {
                        "status": "completed",
                        "progress": 100,
                        "azure_status": "completed",
                        "file_id": file_record.id,
                        "transcription_task_id": transcribe_result.id,
                    },
                )
            except Exception as e:
                logger.error(f"Error updating progress tracker: {str(e)}")
            return {"status": "success", "file_id": file_record.id, "progress": 100}
        except UploadError as ue:
            log_exception(ue, logger)
            try:
                progress_tracker.update_progress(
                    upload_id,
                    {"status": "error", "azure_status": "error", "error": str(ue)},
                )
            except:
                pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    logger.info(f"Cleaned up temporary file after error: {tmp_path}")
                except Exception as cleanup_error:
                    logger.error(
                        f"Error cleaning up temporary file: {str(cleanup_error)}"
                    )
            return {
                "status": "error",
                "error": str(ue),
                "code": ue.error_code,
                "filename": filename,
            }
        except (StorageError, DatabaseError) as e:
            log_exception(e, logger)
            try:
                progress_tracker.update_progress(
                    upload_id,
                    {"status": "error", "azure_status": "error", "error": str(e)},
                )
            except:
                pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    logger.info(f"Cleaned up temporary file after error: {tmp_path}")
                except Exception as cleanup_error:
                    logger.error(
                        f"Error cleaning up temporary file: {str(cleanup_error)}"
                    )
            return {
                "status": "error",
                "error": str(e),
                "code": e.error_code,
                "filename": filename,
            }
        except Exception as e:
            log_exception(e, logger)
            logger.error(traceback.format_exc())
            try:
                progress_tracker.update_progress(
                    upload_id,
                    {"status": "error", "azure_status": "error", "error": str(e)},
                )
            except:
                pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    logger.info(f"Cleaned up temporary file after error: {tmp_path}")
                except Exception as cleanup_error:
                    logger.error(
                        f"Error cleaning up temporary file: {str(cleanup_error)}"
                    )
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "filename": filename,
            }
