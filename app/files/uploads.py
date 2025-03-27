import os
import uuid
import threading
import time
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from app.models import db_session
from app.models.file import File
from app.files import files_bp
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file
from app.files.progress import local_uploads, upload_to_azure

@files_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page for audio files"""
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
        if not file.filename.lower().endswith(('.mp3', '.wav')):
            flash('Only .MP3 and .WAV files are allowed', 'danger')
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

            blob_url = blob_service.upload_file(tmp_path, filename, upload_id=None)

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
            flash(
                'File uploaded successfully. Processing has started automatically.', 'success')
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
        if not file.filename.lower().endswith(('.mp3', '.wav')):
            return jsonify({'error': 'Only .MP3 and .WAV files are allowed'})

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