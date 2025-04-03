import os
import time
import logging
from flask import jsonify, url_for, current_app
from app.files import files_bp
from app.tasks.upload_tasks import UploadProgressTracker
from app.services.blob_storage import BlobStorageService
from celery.result import AsyncResult
from app.errors.exceptions import ResourceNotFoundError, ServiceError, ValidationError
from app.errors.logger import log_exception
from app.extensions import csrf

logger = logging.getLogger(__name__)


@files_bp.route("/upload/progress/<upload_id>")
@csrf.exempt
def upload_progress(upload_id):
    """Get upload progress for a specific upload using Redis-based tracking"""
    try:
        logger.info(f"upload_progress endpoint called for upload_id={upload_id}")
        if not upload_id:
            raise ValidationError("Upload ID is required", field="upload_id")
        app = current_app._get_current_object()
        progress_tracker = UploadProgressTracker(app)
        try:
            progress_info = progress_tracker.get_progress(upload_id)
        except Exception as e:
            log_exception(e, logger)
            progress_info = None
        if not progress_info:
            try:
                blob_service = BlobStorageService(
                    connection_string=current_app.config[
                        "AZURE_STORAGE_CONNECTION_STRING"
                    ],
                    container_name=current_app.config["AZURE_STORAGE_CONTAINER"],
                )
                legacy_progress = blob_service.get_upload_progress(upload_id)
                if legacy_progress:
                    return jsonify(
                        {
                            "status": (
                                "uploading"
                                if legacy_progress["progress"] < 100
                                else "completed"
                            ),
                            "progress": legacy_progress["progress"],
                            "stage": "azure_upload",
                            "uploaded_bytes": legacy_progress.get("uploaded_bytes", 0),
                            "total_bytes": legacy_progress.get("file_size", 0),
                            "message": "Progress recovered from blob service",
                        }
                    )
            except Exception as e:
                log_exception(e, logger)
                logger.error(f"Error checking blob service: {str(e)}")
            raise ResourceNotFoundError(f"Upload with ID {upload_id} not found")
        if progress_info.get("status") == "error":
            error_msg = progress_info.get("error", "Unknown error during upload")
            logger.error(f"Upload error for {upload_id}: {error_msg}")
            tmp_path = progress_info.get("file_path")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    logger.info(f"Cleaned up temporary file: {tmp_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")
            return {"status": "error", "error": error_msg}
        if progress_info.get("status") == "completed":
            file_id = progress_info.get("file_id")
            logger.info(f"Upload completed for {upload_id}, file_id: {file_id}")
            return jsonify(
                {
                    "status": "completed",
                    "progress": 100,
                    "stage": "complete",
                    "redirect_url": (
                        url_for("files.file_detail", file_id=file_id)
                        if file_id
                        else url_for("files.file_list")
                    ),
                }
            )
        if progress_info.get("azure_status") == "in_progress":
            last_update = progress_info.get("last_update", 0)
            current_progress = progress_info.get("progress", 0)
            if time.time() - last_update > 10:
                logger.info(
                    f"Progress info may be stale for {upload_id} (last updated {time.time() - last_update:.1f}s ago)"
                )
                return jsonify(
                    {
                        "status": "uploading",
                        "progress": current_progress,
                        "stage": "azure_upload",
                        "uploaded_bytes": progress_info.get("uploaded_bytes", 0),
                        "total_bytes": progress_info.get("file_size", 0),
                        "message": "Progress information may be delayed",
                    }
                )
            return jsonify(
                {
                    "status": "uploading",
                    "progress": current_progress,
                    "stage": "azure_upload",
                    "uploaded_bytes": progress_info.get("uploaded_bytes", 0),
                    "total_bytes": progress_info.get("file_size", 0),
                }
            )
        if progress_info.get("azure_status") == "pending":
            logger.info(f"Azure upload is pending for {upload_id}")
            return {"status": "uploading", "progress": 0, "stage": "azure_pending"}
        return jsonify(
            {
                "status": "uploading",
                "progress": progress_info.get("progress", 0),
                "stage": progress_info.get("stage", "unknown"),
                "message": "Upload in progress",
            }
        )
    except ResourceNotFoundError as e:
        logger.error(f"Resource not found: {str(e)}")
        return ({"status": "error", "error": str(e)}, 404)
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return ({"status": "error", "error": str(e)}, 400)
    except ServiceError as e:
        logger.error(f"Service error: {str(e)}")
        return ({"status": "error", "error": str(e)}, 500)
    except Exception as e:
        log_exception(e, logger)
        return (jsonify({"status": "error", "error": f"Server error: {str(e)}"}), 500)


@files_bp.route("/task/status/<task_id>")
@csrf.exempt
def task_status(task_id):
    """Get status of a Celery task by its ID"""
    try:
        if not task_id:
            raise ValidationError("Task ID is required", field="task_id")
        from app.tasks.upload_tasks import upload_to_azure_task

        task_result = AsyncResult(task_id)
        if task_result.state == "PENDING":
            response = {"state": task_result.state, "status": "Pending..."}
        elif task_result.state == "FAILURE":
            error_info = str(task_result.info) if task_result.info else "Unknown error"
            response = {
                "state": task_result.state,
                "status": "Error",
                "error": error_info,
                "traceback": task_result.traceback,
            }
        elif task_result.state == "SUCCESS":
            response = {
                "state": task_result.state,
                "status": "Completed",
                "result": task_result.result,
            }
        else:
            response = {
                "state": task_result.state,
                "status": "In Progress",
                "info": task_result.info,
            }
        return jsonify(response)
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return ({"status": "error", "error": str(e)}, 400)
    except Exception as e:
        log_exception(e, logger)
        return ({"status": "error", "error": str(e)}, 500)
