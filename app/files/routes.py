import os
import logging
import uuid
import time
from datetime import datetime, timezone 
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from app.extensions import db, csrf
from app.models.file import File
from app.files import files_bp
from app.tasks.transcription_tasks import transcribe_file
from app.services.blob_storage import BlobStorageService
from app.services.batch_transcription_service import BatchTranscriptionService
from app.tasks.upload_tasks import upload_to_azure_task, UploadProgressTracker
from app.errors.exceptions import ResourceNotFoundError, ServiceError, StorageError, ValidationError, DatabaseError, UploadError
from app.errors.logger import log_exception
from app.auth.decorators import approval_required
logger = logging.getLogger(__name__)

@files_bp.route('/files')
@login_required
@approval_required
def file_list():
    """Dashboard of all files for the current user"""
    files = db.session.query(File).filter(File.user_id == current_user.id).order_by(File.upload_time.desc()).all()
    return render_template('files.html', files=files)

@files_bp.route('/files/<file_id>')
@login_required
@approval_required
def file_detail(file_id):
    """File detail page"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
    if file.user_id != current_user.id:
        flash('You do not have permission to view this file.', 'danger')
        return redirect(url_for('files.file_list'))
    return render_template('file_detail.html', file=file)

@files_bp.route('/transcribe/<file_id>', methods=['POST'])
@login_required
@approval_required
def start_transcription(file_id):
    """Start transcription process for a file"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
    if file.user_id != current_user.id:
        flash('You do not have permission to transcribe this file.', 'danger')
        return redirect(url_for('files.file_list'))
    if file.status in ['processing', 'completed']:
        flash(f'File is already {file.status}', 'warning')
        return redirect(url_for('files.file_detail', file_id=file_id))
    
    # Check if a specific model ID is provided in the form
    model_id = request.form.get('model_id')
    model_name = request.form.get('model_name', "Default")
    
    if model_id:
        file.model_id = model_id
        file.model_name = model_name
    
    file.status = 'processing'
    file.current_stage = 'queued'
    file.progress_percent = 0.0
    db.session.commit()
    
    result = transcribe_file.delay(file_id)
    flash('Transcription started', 'success')
    return redirect(url_for('files.file_detail', file_id=file_id))

@files_bp.route('/delete/<file_id>', methods=['POST'])
@login_required
@approval_required
def delete_file(file_id):
    """Delete file and associated resources"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
    if file.user_id != current_user.id:
        flash('You do not have permission to delete this file.', 'danger')
        return redirect(url_for('files.file_list'))
    try:
        blob_service = BlobStorageService(connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'], container_name=current_app.config['AZURE_STORAGE_CONTAINER'])
        if file.blob_url:
            try:
                parsed_url = urlparse(file.blob_url)
                path = parsed_url.path
                container_name = current_app.config['AZURE_STORAGE_CONTAINER']
                blob_name = path.split(f'/{container_name}/')[-1].split('?')[0]
                blob_service.delete_blob(blob_name)
                logger.info(f'Deleted audio blob: {blob_name}')
            except Exception as e:
                logger.error(f'Error deleting audio blob: {str(e)}')
        if file.transcript_url:
            try:
                parsed_url = urlparse(file.transcript_url)
                path = parsed_url.path
                container_name = current_app.config['AZURE_STORAGE_CONTAINER']
                blob_name = path.split(f'/{container_name}/')[-1].split('?')[0]
                blob_service.delete_blob(blob_name)
                logger.info(f'Deleted transcript blob: {blob_name}')
            except Exception as e:
                logger.error(f'Error deleting transcript blob: {str(e)}')
        db.session.delete(file)
        db.session.commit()
        flash('File and associated transcription deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting file: {str(e)}')
        raise StorageError(f'Error deleting file: {str(e)}', filename=file.filename)
    if request.referrer and url_for('files.file_detail', file_id=file_id) in request.referrer:
        return redirect(url_for('files.file_list'))
    return redirect(url_for('files.file_list'))

@files_bp.route('/api/files')
@login_required
@approval_required
@csrf.exempt
def api_file_list():
    """API endpoint for file list"""
    files = db.session.query(File).filter(File.user_id == current_user.id).order_by(File.upload_time.desc()).all()
    return jsonify([file.to_dict() for file in files])

@files_bp.route('/api/files/<file_id>')
@login_required
@approval_required
@csrf.exempt
def api_file_detail(file_id):
    """API endpoint for file details - used for progress updates"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
    if file.user_id != current_user.id:
        return (jsonify({'error': 'You do not have permission to view this file.'}), 403)
    return jsonify(file.to_dict())

@files_bp.route('/api/models')
@login_required
@approval_required
@csrf.exempt
def api_models():
    """
    API endpoint to get available transcription models.
    Formats the displayName as 'LOCALE - Description' for base models
    and 'LOCALE - Custom: Name' for custom models.
    """
    try:
        subscription_key = current_app.config.get('AZURE_SPEECH_KEY')
        region = current_app.config.get('AZURE_SPEECH_REGION')

        if not subscription_key or not region:
            logger.error('Azure Speech API configuration (Key or Region) is missing.')
            return jsonify({'error': 'Missing Azure Speech API configuration', 'models': []}), 500

        service = BatchTranscriptionService(subscription_key, region)

        base_models = []
        try:
            base_models_response = service.list_models(model_type="base")
            base_models = base_models_response.get('values', [])
            logger.info(f'Retrieved {len(base_models)} raw base models')
        except Exception as e:
            logger.error(f'Error retrieving base models: {str(e)}')
        custom_models = []
        try:
            custom_models_response = service.list_models(model_type="custom")
            custom_models = custom_models_response.get('values', [])
            logger.info(f'Retrieved {len(custom_models)} custom models')
        except Exception as e:
            logger.warning(f'Error retrieving custom models: {str(e)}')

        all_models_output = []
        latest_base_models_by_locale = {}

        # 1. When processing base models, store the self URL
        for model in base_models:
            locale = model.get('locale')
            created_str = model.get('createdDateTime')
            if not locale or not created_str: continue
            try:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Could not parse createdDateTime '{created_str}' for base model")
                continue
            model_description = model.get('description') or model.get('name') or 'Unknown Model'
            current_entry = latest_base_models_by_locale.get(locale)
            if not current_entry or created_dt > current_entry['created_dt']:
                latest_base_models_by_locale[locale] = {
                    'id': model.get('self'),  
                    'name': model.get('name'),
                    'locale': locale,
                    'created_dt': created_dt,
                    'description': model_description,
                    'type': 'base'
                }

        # 2. When creating output model data for base models
        for locale, model_data in latest_base_models_by_locale.items():
            locale_str = model_data['locale']
            description_part = model_data['description'] if model_data['description'] else 'Default'
            display_name = f"{locale_str} - {description_part}" 

            all_models_output.append({
                'id': model_data['id'],  
                'name': model_data['name'],
                'displayName': display_name,
                'locale': locale_str,
                'type': 'base'
            })

        # 3. When processing custom models
        for model in custom_models:
            locale_str = model.get('locale', 'Unknown')
            name = model.get('name', 'Unnamed')
            display_name = f"{locale_str} - Custom: {name}"

            all_models_output.append({
                'id': model.get('self', ''),  # CHANGED: Use self URL instead of id
                'name': name,
                'displayName': display_name,
                'locale': locale_str,
                'type': 'custom'
            })

        # 4. Sort the final list (by locale then name - No change here)
        all_models_output.sort(key=lambda m: (
            m.get('locale', ''),
            m.get('name', '')
        ))

        logger.info(f'Returning {len(all_models_output)} processed models to the API.')
        return jsonify({'models': all_models_output})

    except Exception as e:
        logger.error(f'Unexpected error in api_models endpoint: {str(e)}', exc_info=True)
        return jsonify({'error': f'An unexpected error occurred while retrieving models: {str(e)}', 'models': []}), 500

@files_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@approval_required
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
        
        model_id = request.form.get('transcription_model')
        model_name = None
        
        if model_id:
            try:
                subscription_key = current_app.config['AZURE_SPEECH_KEY']
                region = current_app.config['AZURE_SPEECH_REGION']
                service = BatchTranscriptionService(subscription_key, region)
                
                base_models = service.list_models(model_type="base").get('values', [])
                for model in base_models:
                    if model.get('id') == model_id:
                        model_name = model.get('name')
                        break
                
                # If not found, check custom models
                if not model_name:
                    custom_models = service.list_models(model_type="custom").get('values', [])
                    for model in custom_models:
                        if model.get('id') == model_id:
                            model_name = model.get('name')
                            break
            except Exception as e:
                logger.warning(f'Error fetching model name: {str(e)}')
                
            logger.info(f'Selected model: {model_id} ({model_name})')
        
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
                
                # Include model ID and name if provided
                task_kwargs = {
                    'tmp_path': tmp_path,
                    'filename': filename,
                    'upload_id': upload_id,
                    'user_id': current_user.id
                }
                
                if model_id:
                    task_kwargs['model_id'] = model_id
                    if model_name:
                        task_kwargs['model_name'] = model_name
                
                task = upload_to_azure_task.delay(**task_kwargs)
                return jsonify({'upload_id': upload_id, 'task_id': task.id})
            try:
                blob_service = BlobStorageService(connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'], container_name=current_app.config['AZURE_STORAGE_CONTAINER'])
                blob_url = blob_service.upload_file(tmp_path, filename, upload_id=None)
            except StorageError as e:
                raise UploadError(f'Storage error: {str(e)}', filename=filename)
            try:
                file_record = File(
                    filename=filename, 
                    blob_url=blob_url, 
                    status='processing', 
                    current_stage='queued', 
                    progress_percent=0.0, 
                    user_id=current_user.id,
                    model_id=model_id,
                    model_name=model_name if model_name else "Default"
                )
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
    
    # Try to fetch models for initial page load
    models = []
    try:
        subscription_key = current_app.config['AZURE_SPEECH_KEY']
        region = current_app.config['AZURE_SPEECH_REGION']
        service = BatchTranscriptionService(subscription_key, region)
        
        # First fetch base models
        base_models_response = service.list_models(model_type="base")
        base_models = base_models_response.get('values', [])
        
        # Format the base models
        for model in base_models:
            models.append({
                'id': model.get('id', ''),
                'name': model.get('name', ''),
                'displayName': f"Base: {model.get('name', '')}",
                'locale': model.get('locale', 'Unknown')
            })
        
        # Sort models by locale and name
        models.sort(key=lambda m: (m.get('locale', ''), m.get('name', '')))
    except Exception as e:
        logger.warning(f'Error fetching models for upload page: {str(e)}')
    
    return render_template('upload.html', models=models)

@files_bp.route('/upload/start', methods=['POST'])
@login_required
@approval_required
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
        
        # Get model selection if provided
        model_id = request.form.get('model_id')
        model_name = request.form.get('model_name')
        
        # Log model info for debugging
        if model_id:
            logger.info(f'Model selected - ID: {model_id}, Name: {model_name}')
        
        filename = secure_filename(file.filename)
        try:
            tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)
            upload_id = str(uuid.uuid4())
            progress_tracker = UploadProgressTracker()
            try:
                progress_tracker.update_progress(upload_id, {
                    'file_path': tmp_path, 
                    'filename': filename, 
                    'status': 'local_complete', 
                    'azure_status': 'pending', 
                    'progress': 0, 
                    'start_time': time.time(),
                    'model_id': model_id,
                    'model_name': model_name
                })
            except Exception as e:
                log_exception(e, logger)
                logger.warning(f'Failed to update progress tracker: {str(e)}')
            
            # Include model ID and name if provided
            task_kwargs = {
                'tmp_path': tmp_path,
                'filename': filename,
                'upload_id': upload_id,
                'user_id': current_user.id
            }
            
            if model_id:
                task_kwargs['model_id'] = model_id
                task_kwargs['model_name'] = model_name
            
            task = upload_to_azure_task.delay(**task_kwargs)
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