import os
import time
import logging
from flask import jsonify, url_for, current_app
from app.files import files_bp
from app.tasks.upload_tasks import UploadProgressTracker
from app.services.blob_storage import BlobStorageService
from celery.result import AsyncResult

# Configure logging
logger = logging.getLogger(__name__)

@files_bp.route('/upload/progress/<upload_id>')
def upload_progress(upload_id):
    """Get upload progress for a specific upload using Redis-based tracking"""
    try:
        logger.info(f"upload_progress endpoint called for upload_id={upload_id}")
        
        # Get progress from Redis with current app
        app = current_app._get_current_object()
        progress_tracker = UploadProgressTracker(app)
        progress_info = progress_tracker.get_progress(upload_id)
        
        if not progress_info:
            # Check if upload_id exists in blob storage as fallback
            try:
                blob_service = BlobStorageService(
                    connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                    container_name=current_app.config['AZURE_STORAGE_CONTAINER']
                )
                legacy_progress = blob_service.get_upload_progress(upload_id)
                if legacy_progress:
                    return jsonify({
                        'status': 'uploading' if legacy_progress['progress'] < 100 else 'completed',
                        'progress': legacy_progress['progress'],
                        'stage': 'azure_upload',
                        'uploaded_bytes': legacy_progress.get('uploaded_bytes', 0),
                        'total_bytes': legacy_progress.get('file_size', 0),
                        'message': 'Progress recovered from blob service'
                    })
            except Exception as e:
                logger.error(f"Error checking blob service: {str(e)}")
            
            return {'status': 'error', 'error': 'Upload not found'}
            
        # Check different states
        if progress_info.get('status') == 'error':
            error_msg = progress_info.get('error', 'Unknown error during upload')
            logger.error(f"Upload error for {upload_id}: {error_msg}")
            
            # Clean up temporary file if it exists
            tmp_path = progress_info.get('file_path')
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    logger.info(f"Cleaned up temporary file: {tmp_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")
                    
            return {'status': 'error', 'error': error_msg}
            
        if progress_info.get('status') == 'completed':
            file_id = progress_info.get('file_id')
            logger.info(f"Upload completed for {upload_id}, file_id: {file_id}")
            
            return jsonify({
                'status': 'completed',
                'progress': 100,
                'stage': 'complete',
                'redirect_url': url_for('files.file_detail', file_id=file_id) if file_id else url_for('files.file_list')
            })
            
        # For in-progress uploads
        if progress_info.get('azure_status') == 'in_progress':
            last_update = progress_info.get('last_update', 0)
            current_progress = progress_info.get('progress', 0)
            
            # Check if progress might be stale
            if time.time() - last_update > 10:
                logger.info(f"Progress info may be stale for {upload_id} (last updated {time.time() - last_update:.1f}s ago)")
                return jsonify({
                    'status': 'uploading',
                    'progress': current_progress,
                    'stage': 'azure_upload',
                    'uploaded_bytes': progress_info.get('uploaded_bytes', 0),
                    'total_bytes': progress_info.get('file_size', 0),
                    'message': 'Progress information may be delayed'
                })
                
            return jsonify({
                'status': 'uploading',
                'progress': current_progress,
                'stage': 'azure_upload',
                'uploaded_bytes': progress_info.get('uploaded_bytes', 0),
                'total_bytes': progress_info.get('file_size', 0)
            })
            
        if progress_info.get('azure_status') == 'pending':
            logger.info(f"Azure upload is pending for {upload_id}")
            return {'status': 'uploading', 'progress': 0, 'stage': 'azure_pending'}
            
        # Default response for other states
        return jsonify({
            'status': 'uploading',
            'progress': progress_info.get('progress', 0),
            'stage': progress_info.get('stage', 'unknown'),
            'message': 'Upload in progress'
        })
            
    except Exception as e:
        import traceback
        logger.error(f"Error in upload_progress endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': f'Server error: {str(e)}'})


@files_bp.route('/task/status/<task_id>')
def task_status(task_id):
    """Get status of a Celery task by its ID"""
    try:
        from app.tasks.upload_tasks import upload_to_azure_task
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'state': task_result.state,
                'status': 'Pending...'
            }
        elif task_result.state == 'FAILURE':
            response = {
                'state': task_result.state,
                'status': 'Error',
                'error': str(task_result.info),
                'traceback': task_result.traceback
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'state': task_result.state,
                'status': 'Completed',
                'result': task_result.result
            }
        else:
            # Task in progress
            response = {
                'state': task_result.state,
                'status': 'In Progress',
                'info': task_result.info
            }
            
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in task_status endpoint: {str(e)}")
        return {'status': 'error', 'error': str(e)}