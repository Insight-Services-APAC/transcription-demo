from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort
from werkzeug.utils import secure_filename
import os
import uuid
import threading
import time
import json
from app.models import db_session
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file

files_bp = Blueprint('files', __name__)

# Dictionary to store local upload progress
local_uploads = {}

@files_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page for DCR files"""
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']

        # Check if file was selected
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        # Check file extension
        if not file.filename.lower().endswith('.dcr'):
            flash('Only .DCR files are allowed', 'danger')
            return redirect(request.url)

        # Create secure filename
        filename = secure_filename(file.filename)

        try:
            # Save file to local upload folder temporarily
            tmp_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)
            
            # If AJAX request, return upload ID instead of redirecting
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                upload_id = str(uuid.uuid4())
                
                # Get the current app object for the thread
                app = current_app._get_current_object()
                
                # Start upload in background thread
                thread = threading.Thread(
                    target=upload_to_azure,
                    args=(tmp_path, filename, upload_id, app)
                )
                thread.daemon = True
                thread.start()
                
                return jsonify({'upload_id': upload_id})
            
            # Regular form submission - upload to Azure directly
            # Upload to Azure Blob Storage
            blob_service = BlobStorageService(
                connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                container_name=current_app.config['AZURE_STORAGE_CONTAINER']
            )

            blob_url = blob_service.upload_file(tmp_path, filename)

            # Create file record in database
            file_record = File(
                filename=filename,
                blob_url=blob_url,
                status='processing',
                current_stage='queued',
                progress_percent=0.0
            )

            db_session.add(file_record)
            db_session.commit()

            # Remove temporary file
            os.remove(tmp_path)
            
            # Automatically start transcription process
            transcribe_file.delay(file_record.id)

            # Redirect to file dashboard
            flash('File uploaded successfully. Processing has started automatically.', 'success')
            return redirect(url_for('files.file_list'))

        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
            return redirect(request.url)

    # GET request - show upload form
    return render_template('upload.html')


@files_bp.route('/upload/start', methods=['POST'])
def start_upload():
    """Handle AJAX upload start"""
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        # Check if file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'})

        # Check file extension
        if not file.filename.lower().endswith('.dcr'):
            return jsonify({'error': 'Only .DCR files are allowed'})

        # Create secure filename
        filename = secure_filename(file.filename)

        try:
            # Save file to local upload folder temporarily
            tmp_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)
            
            # Generate upload ID
            upload_id = str(uuid.uuid4())
            
            # Store upload info
            local_uploads[upload_id] = {
                'file_path': tmp_path,
                'filename': filename,
                'status': 'local_complete',
                'azure_status': 'pending',
                'progress': 0,
                'start_time': time.time()
            }
            
            # Get the current app object for the thread
            app = current_app._get_current_object()
            
            # Start upload in background thread
            thread = threading.Thread(
                target=upload_to_azure,
                args=(tmp_path, filename, upload_id, app)
            )
            thread.daemon = True
            thread.start()
            
            # Return JSON response with upload_id
            return jsonify({'upload_id': upload_id})
            
        except Exception as e:
            # Ensure any error is properly converted to JSON
            error_message = str(e)
            current_app.logger.error(f"Error in start_upload: {error_message}")
            return jsonify({'error': f'Error uploading file: {error_message}'})


def upload_to_azure(file_path, filename, upload_id, app):
    """Background task to upload file to Azure Blob Storage"""
    try:
        # Use the app parameter to create a context
        with app.app_context():
            # Mark as in progress
            if upload_id in local_uploads:
                local_uploads[upload_id]['azure_status'] = 'in_progress'
            
            # Get blob service
            blob_service = BlobStorageService(
                connection_string=app.config['AZURE_STORAGE_CONNECTION_STRING'],
                container_name=app.config['AZURE_STORAGE_CONTAINER']
            )
            
            # Check if file exists before upload (for debug/error handling)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found at path: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValueError(f"File is empty (0 bytes): {file_path}")
            
            # Upload to Azure Blob Storage with progress tracking
            blob_url = blob_service.upload_file(file_path, filename, upload_id)
            
            # Create file record in database
            file_record = File(
                filename=filename,
                blob_url=blob_url,
                status='processing',
                current_stage='queued',
                progress_percent=0.0
            )
            
            db_session.add(file_record)
            db_session.commit()
            
            # Automatically start transcription process
            transcribe_file.delay(file_record.id)
            
            # Update status
            if upload_id in local_uploads:
                local_uploads[upload_id]['azure_status'] = 'completed'
                local_uploads[upload_id]['file_id'] = file_record.id
            
            # Remove temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        # Log full exception details for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in background upload: {str(e)}")
        print(f"Error details: {error_details}")
        
        # Update status with error
        if upload_id in local_uploads:
            local_uploads[upload_id]['azure_status'] = 'error'
            local_uploads[upload_id]['error'] = str(e)
        
        # Clean up file if still exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@files_bp.route('/upload/progress/<upload_id>')
def upload_progress(upload_id):
    """Get upload progress for a specific upload"""
    try:
        # Check if upload_id exists in local tracking
        if upload_id in local_uploads:
            upload_info = local_uploads[upload_id]
            
            # If Azure upload is pending, return local upload status
            if upload_info['azure_status'] == 'pending':
                return jsonify({
                    'status': 'uploading',
                    'progress': 0,
                    'stage': 'azure_pending'
                })
            
            # If Azure upload is completed successfully
            if upload_info['azure_status'] == 'completed':
                # Check if we need to clean up and redirect
                file_id = upload_info.get('file_id')
                
                # Remove from tracking only if we have a file_id
                if file_id and upload_id in local_uploads:
                    del local_uploads[upload_id]
                    
                return jsonify({
                    'status': 'completed',
                    'progress': 100,
                    'stage': 'complete',
                    'redirect_url': url_for('files.file_detail', file_id=file_id) if file_id else url_for('files.file_list')
                })
                
            # If Azure upload is in progress, get status from blob service
            if upload_info['azure_status'] == 'in_progress':
                blob_service = BlobStorageService(
                    connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                    container_name=current_app.config['AZURE_STORAGE_CONTAINER']
                )
                
                # Get progress from blob service
                progress_info = blob_service.get_upload_progress(upload_id)
                
                if progress_info:
                    return jsonify({
                        'status': 'uploading',
                        'progress': progress_info['progress'],
                        'stage': 'azure_upload',
                        'uploaded_bytes': progress_info['uploaded_bytes'],
                        'total_bytes': progress_info['file_size']
                    })
                else:
                    # If progress info not available
                    return jsonify({
                        'status': 'uploading',
                        'progress': 0,
                        'stage': 'azure_upload',
                        'message': 'Progress information not available'
                    })
            
            # If Azure upload had an error
            if upload_info['azure_status'] == 'error':
                error_msg = upload_info.get('error', 'Unknown error during upload')
                
                # DO NOT remove from tracking yet - keep for a while so client can see the error
                # Only clean up temp file
                tmp_path = upload_info.get('file_path')
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                
                return jsonify({
                    'status': 'error',
                    'error': error_msg
                })
        
        # Handle case where upload ID is not found
        return jsonify({
            'status': 'error',
            'error': 'Upload not found'
        })
    
    except Exception as e:
        # Log the error and return a proper JSON response
        current_app.logger.error(f"Error in upload_progress: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': f'Server error: {str(e)}'
        })

@files_bp.route('/files')
def file_list():
    """Dashboard of all files"""
    files = db_session.query(File).order_by(File.upload_time.desc()).all()
    return render_template('files.html', files=files)


@files_bp.route('/files/<file_id>')
def file_detail(file_id):
    """File detail page"""
    file = db_session.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)
    return render_template('file_detail.html', file=file)


@files_bp.route('/transcribe/<file_id>', methods=['POST'])
def start_transcription(file_id):
    """Start transcription process for a file"""
    file = db_session.query(File).filter(File.id == file_id).first()
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
    db_session.commit()
    
    # Start transcription task
    result = transcribe_file.delay(file_id)

    flash('Transcription started', 'success')
    return redirect(url_for('files.file_detail', file_id=file_id))


@files_bp.route('/api/files')
def api_file_list():
    """API endpoint for file list"""
    files = db_session.query(File).order_by(File.upload_time.desc()).all()
    return jsonify([file.to_dict() for file in files])


@files_bp.route('/api/files/<file_id>')
def api_file_detail(file_id):
    """API endpoint for file details - used for progress updates"""
    file = db_session.query(File).filter(File.id == file_id).first()
    if file is None:
        return jsonify({"error": "File not found"}), 404
    return jsonify(file.to_dict())