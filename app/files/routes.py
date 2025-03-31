from flask import render_template, redirect, url_for, flash, abort, jsonify, request
from app.extensions import db
from app.models.file import File
from app.files import files_bp
from app.tasks.transcription_tasks import transcribe_file
from app.services.blob_storage import BlobStorageService
from flask import current_app
import os
from urllib.parse import urlparse

@files_bp.route('/files')
def file_list():
    """Dashboard of all files"""
    files = db.session.query(File).order_by(File.upload_time.desc()).all()
    return render_template('files.html', files=files)

@files_bp.route('/files/<file_id>')
def file_detail(file_id):
    """File detail page"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)
    return render_template('file_detail.html', file=file)

@files_bp.route('/transcribe/<file_id>', methods=['POST'])
def start_transcription(file_id):
    """Start transcription process for a file"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)

    # Check if file is already being processed
    if file.status in ['processing', 'completed']:
        flash(f'File is already {file.status}', 'warning')
        return redirect(url_for('files.file_detail', file_id=file_id))

    # Update file status
    file.status = 'processing'
    file.current_stage = 'queued'
    file.progress_percent = 0.0
    db.session.commit()

    # Start transcription task
    result = transcribe_file.delay(file_id)

    flash('Transcription started', 'success')
    return redirect(url_for('files.file_detail', file_id=file_id))

@files_bp.route('/delete/<file_id>', methods=['POST'])
def delete_file(file_id):
    """Delete file and associated resources"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)
    
    try:
        # Initialize blob service to handle Azure storage deletion
        blob_service = BlobStorageService(
            connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
            container_name=current_app.config['AZURE_STORAGE_CONTAINER']
        )
        
        # Delete audio blob if URL exists
        if file.blob_url:
            try:
                # Extract blob path from URL
                parsed_url = urlparse(file.blob_url)
                path = parsed_url.path
                # Get blob name (everything after container name in the path)
                container_name = current_app.config['AZURE_STORAGE_CONTAINER']
                blob_name = path.split(f'/{container_name}/')[-1].split('?')[0]
                
                # Delete the blob
                blob_service.delete_blob(blob_name)
                current_app.logger.info(f"Deleted audio blob: {blob_name}")
            except Exception as e:
                current_app.logger.error(f"Error deleting audio blob: {str(e)}")
        
        # Delete transcript blob if URL exists
        if file.transcript_url:
            try:
                # Extract blob path from URL
                parsed_url = urlparse(file.transcript_url)
                path = parsed_url.path
                # Get blob name (everything after container name in the path)
                container_name = current_app.config['AZURE_STORAGE_CONTAINER']
                blob_name = path.split(f'/{container_name}/')[-1].split('?')[0]
                
                # Delete the blob
                blob_service.delete_blob(blob_name)
                current_app.logger.info(f"Deleted transcript blob: {blob_name}")
            except Exception as e:
                current_app.logger.error(f"Error deleting transcript blob: {str(e)}")
        
        # Delete record from database
        db.session.delete(file)
        db.session.commit()
        
        flash('File and associated transcription deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting file: {str(e)}")
        flash(f'Error deleting file: {str(e)}', 'danger')
    
    # Redirect based on request source
    if request.referrer and url_for('files.file_detail', file_id=file_id) in request.referrer:
        return redirect(url_for('files.file_list'))
    return redirect(url_for('files.file_list'))

@files_bp.route('/api/files')
def api_file_list():
    """API endpoint for file list"""
    files = db.session.query(File).order_by(File.upload_time.desc()).all()
    return jsonify([file.to_dict() for file in files])

@files_bp.route('/api/files/<file_id>')
def api_file_detail(file_id):
    """API endpoint for file details - used for progress updates"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        return jsonify({"error": "File not found"}), 404
    return jsonify(file.to_dict())