import os
import uuid
import time
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.file import File
from app.files import files_bp
from app.services.blob_storage import BlobStorageService
from app.tasks.upload_tasks import upload_to_azure_task, UploadProgressTracker
import logging
from app.errors.exceptions import ValidationError, UploadError, StorageError, DatabaseError
from app.errors.logger import log_exception
logger = logging.getLogger(__name__)

@files_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page for audio files"""
    if request.method == 'POST':
        if 'file' not in request.files:
            raise ValidationError('No file part in request', field='file')
        file = request.files['file']
        if file.filename == '':
            raise ValidationError('No file selected', field='file')
        if not file.filename.lower().endswith(('.mp3', '.wav')):
            raise ValidationError('Only .MP3 and .WAV files are allowed', field='file')
        filename = secure_filename(file.filename)
        try:
            tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                upload_id = str(uuid.uuid4())
                app = current_app._get_current_object()
                progress_tracker = UploadProgressTracker(app)
                try:
                    progress_tracker.update_progress(upload_id, {'file_path': tmp_path, 'filename': filename, 'status': 'local_complete', 'azure_status': 'pending', 'progress': 0, 'stage': 'preparing', 'start_time': time.time()})
                except Exception as e:
                    log_exception(e, logger)
                    logger.warning(f'Failed to update progress tracker: {str(e)}')
                task = upload_to_azure_task.delay(tmp_path, filename, upload_id)
                return jsonify({'upload_id': upload_id, 'task_id': task.id})
            try:
                blob_service = BlobStorageService(connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'], container_name=current_app.config['AZURE_STORAGE_CONTAINER'])
                blob_url = blob_service.upload_file(tmp_path, filename, upload_id=None)
            except StorageError as e:
                raise UploadError(f'Storage error: {str(e)}', filename=filename)
            try:
                file_record = File(filename=filename, blob_url=blob_url, status='processing', current_stage='queued', progress_percent=0.0)
                db.session.add(file_record)
                db.session.commit()
            except Exception as e:
                log_exception(e, logger)
                raise DatabaseError(f'Database error: {str(e)}', filename=filename)
            try:
                os.remove(tmp_path)
            except Exception as e:
                logger.error(f'Error removing temporary file: {str(e)}')
            try:
                from app.tasks.transcription_tasks import transcribe_file
                transcribe_file.delay(file_record.id)
            except Exception as e:
                log_exception(e, logger)
                flash(f'Warning: Error starting transcription process: {str(e)}', 'warning')
            flash('File uploaded successfully. Processing has started automatically.', 'success')
            return redirect(url_for('files.file_list'))
        except UploadError as ue:
            log_exception(ue, logger)
            flash(f'Error uploading file: {str(ue)}', 'danger')
            return redirect(request.url)
        except StorageError as se:
            log_exception(se, logger)
            flash(f'Storage error: {str(se)}', 'danger')
            return redirect(request.url)
        except DatabaseError as de:
            log_exception(de, logger)
            flash(f'Database error: {str(de)}', 'danger')
            return redirect(request.url)
        except Exception as e:
            log_exception(e, logger)
            flash(f'Unexpected error: {str(e)}', 'danger')
            return redirect(request.url)
    return render_template('upload.html')

@files_bp.route('/upload/start', methods=['POST'])
def start_upload():
    """Handle AJAX upload start"""
    if request.method == 'POST':
        if 'file' not in request.files:
            raise ValidationError('No file part in request', field='file')
        file = request.files['file']
        if file.filename == '':
            raise ValidationError('No file selected', field='file')
        if not file.filename.lower().endswith(('.mp3', '.wav')):
            raise ValidationError('Only .MP3 and .WAV files are allowed', field='file')
        filename = secure_filename(file.filename)
        try:
            tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)
            upload_id = str(uuid.uuid4())
            progress_tracker = UploadProgressTracker()
            try:
                progress_tracker.update_progress(upload_id, {'file_path': tmp_path, 'filename': filename, 'status': 'local_complete', 'azure_status': 'pending', 'progress': 0, 'start_time': time.time()})
            except Exception as e:
                log_exception(e, logger)
                logger.warning(f'Failed to update progress tracker: {str(e)}')
            task = upload_to_azure_task.delay(tmp_path, filename, upload_id)
            return jsonify({'upload_id': upload_id, 'task_id': task.id})
        except Exception as e:
            log_exception(e, logger)
            error_message = str(e)
            logger.error(f'Error in start_upload: {error_message}')
            if isinstance(e, (ValidationError, UploadError, StorageError, DatabaseError)):
                code = getattr(e, 'error_code', 'error')
                return ({'error': error_message, 'code': code}, e.status_code)
            else:
                return jsonify({'error': f'Unexpected error: {error_message}'})