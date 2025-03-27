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
            tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)

            # If AJAX request, return upload ID instead of redirecting
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                upload_id = str(uuid.uuid4())
                
                # Initialize progress tracker using current app
                app = current_app._get_current_object()
                progress_tracker = UploadProgressTracker(app)
                progress_tracker.update_progress(upload_id, {
                    'file_path': tmp_path,
                    'filename': filename,
                    'status': 'local_complete',
                    'azure_status': 'pending',
                    'progress': 0,
                    'stage': 'preparing',
                    'start_time': time.time()
                })
                
                # Start Celery task for Azure upload
                task = upload_to_azure_task.delay(tmp_path, filename, upload_id)

                return jsonify({
                    'upload_id': upload_id,
                    'task_id': task.id
                })

            # Regular form submission - upload to Azure directly
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

            db.session.add(file_record)
            db.session.commit()

            # Remove temporary file
            os.remove(tmp_path)

            # Automatically start transcription process
            from app.tasks.transcription_tasks import transcribe_file
            transcribe_file.delay(file_record.id)

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
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'})

        if not file.filename.lower().endswith(('.mp3', '.wav')):
            return jsonify({'error': 'Only .MP3 and .WAV files are allowed'})

        filename = secure_filename(file.filename)

        try:
            tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(tmp_path)

            upload_id = str(uuid.uuid4())

            progress_tracker = UploadProgressTracker()
            progress_tracker.update_progress(upload_id, {
                'file_path': tmp_path,
                'filename': filename,
                'status': 'local_complete',
                'azure_status': 'pending',
                'progress': 0,
                'start_time': time.time()
            })

            task = upload_to_azure_task.delay(tmp_path, filename, upload_id)

            return jsonify({
                'upload_id': upload_id,
                'task_id': task.id
            })

        except Exception as e:
            error_message = str(e)
            current_app.logger.error(f"Error in start_upload: {error_message}")
            return jsonify({'error': f'Error uploading file: {error_message}'})
