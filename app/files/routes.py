from flask import render_template, redirect, url_for, flash, abort, jsonify
from app.extensions import db
from app.models.file import File
from app.files import files_bp
from app.tasks.transcription_tasks import transcribe_file

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
