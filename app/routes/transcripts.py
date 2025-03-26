from flask import Blueprint, render_template, abort, jsonify, current_app, request
from app.models import db_session
from app.models.file import File
import json
import requests

transcripts_bp = Blueprint('transcripts', __name__)


@transcripts_bp.route('/transcript/<file_id>')
def view_transcript(file_id):
    """View transcript page"""
    file = db_session.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)

    # Check if transcript exists
    if file.status != 'completed' or not file.transcript_url:
        abort(404, description="Transcript not available")

    return render_template('transcript.html', file=file)


@transcripts_bp.route('/api/transcript/<file_id>')
def api_transcript(file_id):
    """API endpoint to get transcript data"""
    file = db_session.query(File).filter(File.id == file_id).first()
    if file is None:
        return jsonify({"error": "File not found"}), 404

    # Check if transcript exists
    if file.status != 'completed' or not file.transcript_url:
        return jsonify({"error": "Transcript not available"}), 404

    try:
        # Fetch transcript JSON from blob storage
        response = requests.get(file.transcript_url)
        response.raise_for_status()

        transcript_data = response.json()
        return jsonify(transcript_data)

    except Exception as e:
        return jsonify({"error": f"Error fetching transcript: {str(e)}"}), 500
