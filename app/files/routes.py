import os
import logging
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from app.extensions import db, csrf
from app.models.file import File
from app.files import files_bp
from app.tasks.transcription_tasks import transcribe_file
from app.services.blob_storage import BlobStorageService
from app.errors.exceptions import ResourceNotFoundError, ServiceError, StorageError, ValidationError
logger = logging.getLogger(__name__)

@files_bp.route('/files')
@login_required
def file_list():
    """Dashboard of all files for the current user"""
    files = db.session.query(File).filter(File.user_id == current_user.id).order_by(File.upload_time.desc()).all()
    return render_template('files.html', files=files)

@files_bp.route('/files/<file_id>')
@login_required
def file_detail(file_id):
    """File detail page"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
    
    # Check if the file belongs to the current user
    if file.user_id != current_user.id:
        flash('You do not have permission to view this file.', 'danger')
        return redirect(url_for('files.file_list'))
        
    return render_template('file_detail.html', file=file)

@files_bp.route('/transcribe/<file_id>', methods=['POST'])
@login_required
def start_transcription(file_id):
    """Start transcription process for a file"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
        
    # Check if the file belongs to the current user
    if file.user_id != current_user.id:
        flash('You do not have permission to transcribe this file.', 'danger')
        return redirect(url_for('files.file_list'))
        
    if file.status in ['processing', 'completed']:
        flash(f'File is already {file.status}', 'warning')
        return redirect(url_for('files.file_detail', file_id=file_id))
        
    file.status = 'processing'
    file.current_stage = 'queued'
    file.progress_percent = 0.0
    db.session.commit()
    result = transcribe_file.delay(file_id)
    flash('Transcription started', 'success')
    return redirect(url_for('files.file_detail', file_id=file_id))

@files_bp.route('/delete/<file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete file and associated resources"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
        
    # Check if the file belongs to the current user
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
@csrf.exempt  # Exempt this endpoint from CSRF protection as it's read-only
def api_file_list():
    """API endpoint for file list"""
    files = db.session.query(File).filter(File.user_id == current_user.id).order_by(File.upload_time.desc()).all()
    return jsonify([file.to_dict() for file in files])

@files_bp.route('/api/files/<file_id>')
@login_required
@csrf.exempt  # Exempt this endpoint from CSRF protection as it's read-only
def api_file_detail(file_id):
    """API endpoint for file details - used for progress updates"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f'File with ID {file_id} not found')
        
    # Check if the file belongs to the current user
    if file.user_id != current_user.id:
        return jsonify({'error': 'You do not have permission to view this file.'}), 403
        
    return jsonify(file.to_dict())