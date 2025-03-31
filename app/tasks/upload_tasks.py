import os
import time
import logging
import traceback
from celery import shared_task
from flask import current_app
from app.extensions import db
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file
from redis import Redis
import json
from app.errors.exceptions import UploadError, StorageError, DatabaseError, ValidationError
from app.errors.logger import log_exception
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('app.tasks.upload')

class UploadProgressTracker:
    """Utility class to track upload progress in Redis"""

    def __init__(self, app=None):
        self.app = app or current_app._get_current_object()
        try:
            redis_url = self.app.config.get('broker_url') or self.app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            if redis_url.startswith('redis://'):
                parts = redis_url.replace('redis://', '').split('/')
                host_port = parts[0].split(':')
                host = host_port[0] or 'localhost'
                port = int(host_port[1]) if len(host_port) > 1 else 6379
                db_index = int(parts[1]) if len(parts) > 1 else 0
                self.redis = Redis(host=host, port=port, db=db_index)
            else:
                self.redis = Redis(host='localhost', port=6379, db=0)
        except Exception as e:
            log_exception(e, logger)
            logger.error(f'Error initializing Redis connection: {str(e)}')
            self.redis = Redis(host='localhost', port=6379, db=0)

    def update_progress(self, upload_id, progress_data):
        if not upload_id:
            raise ValidationError('Upload ID is required', field='upload_id')
        if not progress_data:
            raise ValidationError('Progress data is required', field='progress_data')
        try:
            progress_data['last_update'] = time.time()
            self.redis.setex(f'upload_progress:{upload_id}', 3600, json.dumps(progress_data))
        except Exception as e:
            logger.error(f'Error updating progress in Redis: {str(e)}')
            self._fallback_progress_store = getattr(self, '_fallback_progress_store', {})
            self._fallback_progress_store[upload_id] = progress_data

    def get_progress(self, upload_id):
        if not upload_id:
            raise ValidationError('Upload ID is required', field='upload_id')
        try:
            data = self.redis.get(f'upload_progress:{upload_id}')
            if data:
                return json.loads(data)
            fallback_store = getattr(self, '_fallback_progress_store', {})
            return fallback_store.get(upload_id)
        except Exception as e:
            logger.error(f'Error getting progress from Redis: {str(e)}')
            fallback_store = getattr(self, '_fallback_progress_store', {})
            return fallback_store.get(upload_id)
        return None

@shared_task(bind=True)
def upload_to_azure_task(self, file_path, filename, upload_id):
    """
    Celery task to handle file upload to Azure Blob Storage.
    """
    logger.info(f'Starting upload task for {filename} (ID: {upload_id})')
    from flask import current_app
    from app import create_app
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    with app.app_context():
        progress_tracker = UploadProgressTracker(app)
        try:
            progress_tracker.update_progress(upload_id, {'status': 'starting', 'progress': 0, 'file_path': file_path, 'filename': filename, 'azure_status': 'pending', 'stage': 'preparing'})
        except Exception as e:
            logger.error(f'Error updating progress tracker: {str(e)}')
        try:
            if not os.path.exists(file_path):
                raise UploadError(f'File not found at path: {file_path}', filename=filename)
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise UploadError(f'File is empty (0 bytes)', filename=filename)
            try:
                progress_tracker.update_progress(upload_id, {'status': 'uploading', 'progress': 0, 'file_path': file_path, 'filename': filename, 'azure_status': 'in_progress', 'stage': 'azure_upload', 'start_time': time.time(), 'file_size': file_size})
            except Exception as e:
                logger.error(f'Error updating progress tracker: {str(e)}')
            try:
                blob_service = BlobStorageService(connection_string=app.config['AZURE_STORAGE_CONNECTION_STRING'], container_name=app.config['AZURE_STORAGE_CONTAINER'])
                blob_url = blob_service.upload_file(file_path, filename, upload_id, progress_tracker)
            except StorageError as se:
                raise UploadError(f'Storage error during upload: {str(se)}', filename=filename, original_error=str(se))
            try:
                session = db.session
                file_record = File(filename=filename, blob_url=blob_url, status='processing', current_stage='queued', progress_percent=0.0)
                session.add(file_record)
                session.commit()
            except Exception as e:
                log_exception(e, logger)
                raise DatabaseError(f'Database error creating file record: {str(e)}', filename=filename)
            try:
                from app.tasks.transcription_tasks import transcribe_file
                transcribe_result = transcribe_file.delay(file_record.id)
            except Exception as e:
                log_exception(e, logger)
                raise UploadError(f'Error starting transcription task: {str(e)}', filename=filename, file_id=file_record.id)
            try:
                progress_tracker.update_progress(upload_id, {'status': 'completed', 'progress': 100, 'azure_status': 'completed', 'file_id': file_record.id, 'transcription_task_id': transcribe_result.id})
            except Exception as e:
                logger.error(f'Error updating progress tracker: {str(e)}')
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f'Removed temporary file: {file_path}')
            except Exception as e:
                logger.error(f'Error removing temporary file: {str(e)}')
            return {'status': 'success', 'file_id': file_record.id, 'progress': 100}
        except UploadError as ue:
            log_exception(ue, logger)
            try:
                progress_tracker.update_progress(upload_id, {'status': 'error', 'azure_status': 'error', 'error': str(ue)})
            except:
                pass
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f'Cleaned up temporary file after error: {file_path}')
                except Exception as cleanup_error:
                    logger.error(f'Error cleaning up temporary file: {str(cleanup_error)}')
            return {'status': 'error', 'error': str(ue), 'code': ue.error_code, 'filename': filename}
        except (StorageError, DatabaseError) as e:
            log_exception(e, logger)
            try:
                progress_tracker.update_progress(upload_id, {'status': 'error', 'azure_status': 'error', 'error': str(e)})
            except:
                pass
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f'Cleaned up temporary file after error: {file_path}')
                except Exception as cleanup_error:
                    logger.error(f'Error cleaning up temporary file: {str(cleanup_error)}')
            return {'status': 'error', 'error': str(e), 'code': e.error_code, 'filename': filename}
        except Exception as e:
            log_exception(e, logger)
            logger.error(traceback.format_exc())
            try:
                progress_tracker.update_progress(upload_id, {'status': 'error', 'azure_status': 'error', 'error': str(e)})
            except:
                pass
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f'Cleaned up temporary file after error: {file_path}')
                except Exception as cleanup_error:
                    logger.error(f'Error cleaning up temporary file: {str(cleanup_error)}')
            return {'status': 'error', 'error': f'Unexpected error: {str(e)}', 'filename': filename}