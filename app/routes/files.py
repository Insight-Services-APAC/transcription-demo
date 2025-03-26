from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort
from werkzeug.utils import secure_filename
import os
import uuid
from app.models import db_session
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file

files_bp = Blueprint('files', __name__)


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

            # Upload to Azure Blob Storage
            blob_service = BlobStorageService(
                connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                container_name=current_app.config['AZURE_STORAGE_CONTAINER']
            )

            blob_url = blob_service.upload_file(tmp_path, filename)

            # Create file record in database
            file_record = File(
                filename=filename,
                blob_url=blob_url
            )

            db_session.add(file_record)
            db_session.commit()

            # Remove temporary file
            os.remove(tmp_path)

            # Redirect to file dashboard
            flash('File uploaded successfully', 'success')
            return redirect(url_for('files.file_list'))

        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
            return redirect(request.url)

    # GET request - show upload form
    return render_template('upload.html')


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

    # Start transcription task
    result = transcribe_file.delay(file_id)

    flash('Transcription started', 'success')
    return redirect(url_for('files.file_detail', file_id=file_id))


@files_bp.route('/api/files')
def api_file_list():
    """API endpoint for file list"""
    files = db_session.query(File).order_by(File.upload_time.desc()).all()
    return jsonify([file.to_dict() for file in files])
