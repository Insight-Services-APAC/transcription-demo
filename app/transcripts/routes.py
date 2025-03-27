from flask import render_template, abort, jsonify, current_app, request
from app.models import db_session
from app.models.file import File
import json
import requests
from app.services.blob_storage import BlobStorageService
import traceback
from app.transcripts import transcripts_bp


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
    """
    API endpoint to get transcript data.
    This endpoint regenerates a fresh SAS URL using blob_storage.py
    before fetching the transcript JSON (to avoid expired SAS URLs).
    """
    file = db_session.query(File).filter(File.id == file_id).first()
    if file is None:
        return jsonify({"error": "File not found"}), 404

    # Check if transcript exists
    if file.status != 'completed' or not file.transcript_url:
        return jsonify({"error": "Transcript not available"}), 404

    try:
        # Create BlobStorageService to regenerate a full SAS URL
        blob_service = BlobStorageService(
            connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
            container_name=current_app.config['AZURE_STORAGE_CONTAINER']
        )

        # Fetch transcript JSON from that fresh SAS URL
        response = requests.get(file.transcript_url)
        response.raise_for_status()
        transcript_data = response.json()

        # Process the transcript data to make it more frontend-friendly
        processed_data = process_transcript_data(transcript_data)

        return jsonify(processed_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error fetching transcript: {str(e)}"}), 500


def process_transcript_data(data):
    """Process the transcript data from Azure Speech Service format to a more frontend-friendly format"""
    result = {
        "source": data.get("source", ""),
        "duration": data.get("duration", ""),
        "combinedResults": [],
        "segments": []
    }
    
    # Add combined results
    if "combinedRecognizedPhrases" in data:
        result["combinedResults"] = [
            {
                "channel": item.get("channel", 0),
                "text": item.get("display", ""),
                "lexical": item.get("lexical", "")
            }
            for item in data["combinedRecognizedPhrases"]
        ]
    
    # Process recognized phrases into segments
    if "recognizedPhrases" in data:
        segments = []
        
        for phrase in data["recognizedPhrases"]:
            # Skip phrases with no results
            if phrase.get("recognitionStatus") != "Success" or not phrase.get("nBest") or len(phrase["nBest"]) == 0:
                continue

            # Get the best recognition option
            best_result = phrase["nBest"][0]

            # Create a segment with time offsets
            segment = {
                "start": phrase.get("offset", "0:00:00"),
                "end": add_time_strings(
                    phrase.get("offset", "0:00:00"), 
                    phrase.get("duration", "0:00:00")
                ),
                "offsetMilliseconds": phrase.get("offsetMilliseconds", 0),
                "durationMilliseconds": phrase.get("durationMilliseconds", 0),
                "speaker": phrase.get("speaker", 0),
                "text": best_result.get("display", ""),
                "confidence": best_result.get("confidence", 0),
                "words": []
            }

            # Add word-level details if available
            if "words" in best_result:
                segment["words"] = [
                    {
                        "word": word.get("word", ""),
                        "start": word.get("offset", "0:00:00"),
                        "duration": word.get("duration", "0:00:00"),
                        "offsetMilliseconds": word.get("offsetMilliseconds", 0),
                        "durationMilliseconds": word.get("durationMilliseconds", 0),
                        "confidence": word.get("confidence", 0)
                    }
                    for word in best_result["words"]
                ]

            segments.append(segment)

        # Sort segments by time
        result["segments"] = sorted(segments, key=lambda x: x["offsetMilliseconds"])

    return result


def add_time_strings(time1, time2):
    """Add two time strings in HH:MM:SS or HH:MM:SS.msec format"""
    # Convert to seconds
    def to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return 0
    
    # Convert back to string
    def to_string(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    
    total_seconds = to_seconds(time1) + to_seconds(time2)
    return to_string(total_seconds)