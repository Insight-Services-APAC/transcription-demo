from flask import (
    render_template,
    jsonify,
    current_app,
    request,
    flash,
    redirect,
    url_for,
)
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.models.file import File
import json
import requests
from app.services.blob_storage import BlobStorageService
import logging
from app.transcripts import transcripts_bp
from app.errors.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    ServiceError,
    StorageError,
)
from app.errors.logger import log_exception
from app.auth.decorators import approval_required

logger = logging.getLogger(__name__)


@transcripts_bp.route("/transcript/<file_id>")
@login_required
@approval_required
def view_transcript(file_id):
    """View transcript page"""
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f"File with ID {file_id} not found")
    if file.user_id != current_user.id:
        flash("You do not have permission to view this transcript.", "danger")
        return redirect(url_for("files.file_list"))
    if file.status != "completed" or not file.transcript_url:
        raise ResourceNotFoundError(
            "Transcript not available for this file",
            file_id=file_id,
            status=file.status,
        )
    return render_template("transcript.html", file=file)


@transcripts_bp.route("/api/transcript/<file_id>")
@login_required
@approval_required
@csrf.exempt
def api_transcript(file_id):
    """
    API endpoint to get transcript data.
    This endpoint regenerates a fresh SAS URL before fetching the transcript JSON.
    """
    file = db.session.query(File).filter(File.id == file_id).first()
    if file is None:
        raise ResourceNotFoundError(f"File with ID {file_id} not found")
    if file.user_id != current_user.id:
        return (
            jsonify({"error": "You do not have permission to view this transcript."}),
            403,
        )
    if file.status != "completed" or not file.transcript_url:
        raise ResourceNotFoundError(
            "Transcript not available for this file",
            file_id=file_id,
            status=file.status,
        )
    try:
        blob_service = BlobStorageService(
            connection_string=current_app.config["AZURE_STORAGE_CONNECTION_STRING"],
            container_name=current_app.config["AZURE_STORAGE_CONTAINER"],
        )
        try:
            response = requests.get(file.transcript_url)
            response.raise_for_status()
            transcript_data = response.json()
        except requests.exceptions.RequestException as e:
            log_exception(e, logger)
            raise ServiceError(
                f"Error fetching transcript from URL: {str(e)}",
                service="http",
                url=file.transcript_url,
            )
        except json.JSONDecodeError as e:
            log_exception(e, logger)
            raise ServiceError(
                f"Invalid JSON in transcript response: {str(e)}", service="json"
            )
        processed_data = process_transcript_data(transcript_data)
        return jsonify(processed_data)
    except StorageError as e:
        log_exception(e, logger)
        raise ServiceError(
            f"Storage error accessing transcript: {str(e)}", service="azure_storage"
        )
    except Exception as e:
        log_exception(e, logger)
        raise ServiceError(
            f"Unexpected error processing transcript: {str(e)}", file_id=file_id
        )


def process_transcript_data(data):
    """Process transcript data into a frontend-friendly format"""
    if not data:
        raise ValidationError("Transcript data is empty or null", field="data")
    result = {
        "source": data.get("source", ""),
        "duration": data.get("duration", ""),
        "combinedResults": [],
        "segments": [],
    }
    if "combinedRecognizedPhrases" in data:
        result["combinedResults"] = [
            {
                "channel": item.get("channel", 0),
                "text": item.get("display", ""),
                "lexical": item.get("lexical", ""),
            }
            for item in data["combinedRecognizedPhrases"]
        ]
    if "recognizedPhrases" in data:
        segments = []
        for phrase in data["recognizedPhrases"]:
            if (
                phrase.get("recognitionStatus") != "Success"
                or not phrase.get("nBest")
                or len(phrase["nBest"]) == 0
            ):
                continue
            best_result = phrase["nBest"][0]
            offset_str = format_timestamp(phrase.get("offsetMilliseconds", 0))
            end_offset = phrase.get("offsetMilliseconds", 0) + phrase.get(
                "durationMilliseconds", 0
            )
            end_str = format_timestamp(end_offset)
            segment = {
                "start": offset_str,
                "end": end_str,
                "offsetMilliseconds": phrase.get("offsetMilliseconds", 0),
                "durationMilliseconds": phrase.get("durationMilliseconds", 0),
                "speaker": phrase.get("speaker", 0),
                "text": best_result.get("display", ""),
                "confidence": best_result.get("confidence", 0),
                "words": [],
            }
            if "words" in best_result:
                segment["words"] = [
                    {
                        "word": word.get("word", ""),
                        "start": format_timestamp(word.get("offsetMilliseconds", 0)),
                        "duration": format_timestamp_duration(
                            word.get("durationMilliseconds", 0)
                        ),
                        "offsetMilliseconds": word.get("offsetMilliseconds", 0),
                        "durationMilliseconds": word.get("durationMilliseconds", 0),
                        "confidence": word.get("confidence", 0),
                    }
                    for word in best_result["words"]
                ]
            segments.append(segment)
        result["segments"] = sorted(segments, key=lambda x: x["offsetMilliseconds"])
    return result


def format_timestamp(milliseconds):
    """Convert milliseconds to a user-friendly timestamp format (MM:SS.mmm)"""
    seconds = milliseconds / 1000
    minutes = int(seconds // 60)
    seconds_remainder = seconds % 60
    return f"{minutes:02d}:{seconds_remainder:06.3f}"


def format_timestamp_duration(milliseconds):
    """Format a duration in milliseconds to a user-friendly format"""
    seconds = milliseconds / 1000
    return f"{seconds:.3f}s"


def add_time_strings(time1, time2):
    """
    Add two time strings in HH:MM:SS, HH:MM:SS.msec, or ISO 8601 duration format (PT1.5S)
    """

    def to_seconds(time_str):
        if time_str.startswith("PT") and time_str.endswith("S"):
            try:
                return float(time_str[2:-1])
            except ValueError:
                return 0
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return 0

    def to_string(seconds):
        h = int(seconds // 3600)
        m = int(seconds % 3600 // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    total_seconds = to_seconds(time1) + to_seconds(time2)
    return to_string(total_seconds)
