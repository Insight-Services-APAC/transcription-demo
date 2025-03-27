import os
import time
import threading
from flask import jsonify, url_for, current_app
from app.files import files_bp
from app.models import db_session
from app.models.file import File
from app.services.blob_storage import BlobStorageService
from app.tasks.transcription_tasks import transcribe_file

# Dictionary to store local upload progress
local_uploads = {}


@files_bp.route('/upload/progress/<upload_id>')
def upload_progress(upload_id):
    """Get upload progress for a specific upload"""
    import threading
    print(
        f"upload_progress endpoint called for upload_id={upload_id}, thread ID: {threading.get_ident()}")

    try:
        # Check if upload_id exists in local tracking
        if upload_id in local_uploads:
            upload_info = local_uploads[upload_id]
            print(
                f"Found upload_id in local_uploads: {upload_id}, status: {upload_info['azure_status']}")

            # If Azure upload is pending, return local upload status
            if upload_info['azure_status'] == 'pending':
                print(f"Azure upload is pending for {upload_id}")
                return jsonify({
                    'status': 'uploading',
                    'progress': 0,
                    'stage': 'azure_pending'
                })

            # If Azure upload is completed successfully
            if upload_info['azure_status'] == 'completed':
                # Check if we need to clean up and redirect
                file_id = upload_info.get('file_id')
                print(
                    f"Azure upload is completed for {upload_id}, file_id: {file_id}")

                # Remove from tracking only if we have a file_id and it's been a while
                # so we don't lose tracking information too early
                if file_id and upload_id in local_uploads and time.time() - upload_info.get('start_time', 0) > 10:
                    del local_uploads[upload_id]
                    print(f"Removed {upload_id} from local_uploads tracking")

                return jsonify({
                    'status': 'completed',
                    'progress': 100,
                    'stage': 'complete',
                    'redirect_url': url_for('files.file_detail', file_id=file_id) if file_id else url_for('files.file_list')
                })

            # If Azure upload is in progress, get status from blob service
            if upload_info['azure_status'] == 'in_progress':
                # Log that we're checking progress in blob service
                print(
                    f"Azure upload is in progress for {upload_id}, checking BlobStorageService")

                blob_service = BlobStorageService(
                    connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                    container_name=current_app.config['AZURE_STORAGE_CONTAINER']
                )

                # Get progress from blob service
                progress_info = blob_service.get_upload_progress(upload_id)

                if progress_info:
                    print(
                        f"Got progress from BlobStorageService: {progress_info}")

                    # Check if progress has been updated recently (within last 5 seconds)
                    last_update = progress_info.get('last_update', 0)
                    if time.time() - last_update > 5:
                        print(
                            f"Progress info is stale (last updated {time.time() - last_update:.1f}s ago)")
                        # Still return the data, but note it might be stale
                        return jsonify({
                            'status': 'uploading',
                            'progress': progress_info['progress'],
                            'stage': 'azure_upload',
                            'uploaded_bytes': progress_info['uploaded_bytes'],
                            'total_bytes': progress_info['file_size'],
                            'message': 'Progress information may be delayed'
                        })

                    # Normal case - recent progress update
                    return jsonify({
                        'status': 'uploading',
                        'progress': progress_info['progress'],
                        'stage': 'azure_upload',
                        'uploaded_bytes': progress_info['uploaded_bytes'],
                        'total_bytes': progress_info['file_size']
                    })
                else:
                    # Progress info not available, but upload is still in progress
                    print(
                        f"No progress info available from BlobStorageService for {upload_id}")

                    # Calculate a synthetic progress based on time elapsed if we know when it started
                    start_time = upload_info.get('start_time', 0)
                    if start_time > 0:
                        elapsed_time = time.time() - start_time
                        # Assumption: most uploads complete within 1-2 minutes
                        # Cap at 95% to prevent falsely showing completion
                        synthetic_progress = min(
                            95, int(elapsed_time / 120 * 100))
                        print(
                            f"Using synthetic progress based on time: {synthetic_progress}%")

                        return jsonify({
                            'status': 'uploading',
                            'progress': synthetic_progress,
                            'stage': 'azure_upload',
                            'message': 'Estimating progress based on elapsed time'
                        })

                    # Fallback when we can't calculate synthetic progress
                    # Update last_check time to avoid too many unnecessary blob service calls
                    upload_info['last_progress_check'] = time.time()

                    return jsonify({
                        'status': 'uploading',
                        'progress': upload_info.get('progress', 0),
                        'stage': 'azure_upload',
                        'message': 'Progress information not available'
                    })

            # If Azure upload had an error
            if upload_info['azure_status'] == 'error':
                error_msg = upload_info.get(
                    'error', 'Unknown error during upload')
                print(f"Upload error for {upload_id}: {error_msg}")

                # DO NOT remove from tracking yet - keep for a while so client can see the error
                # Only clean up temp file
                tmp_path = upload_info.get('file_path')
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                        print(f"Cleaned up temporary file: {tmp_path}")
                    except Exception as e:
                        print(f"Error cleaning up temporary file: {str(e)}")

                return jsonify({
                    'status': 'error',
                    'error': error_msg
                })

        # Handle case where upload ID is not found in local tracking but might be in blob service
        # This can happen if the app was restarted but the upload is still in progress
        print(
            f"Upload ID not found in local_uploads: {upload_id}, checking blob service")

        try:
            # Try to get progress from blob service directly
            blob_service = BlobStorageService(
                connection_string=current_app.config['AZURE_STORAGE_CONNECTION_STRING'],
                container_name=current_app.config['AZURE_STORAGE_CONTAINER']
            )

            progress_info = blob_service.get_upload_progress(upload_id)

            if progress_info:
                print(f"Found progress info in blob service for {upload_id}")
                # We found progress data in blob service but not in local tracking
                # Add to local tracking for future requests
                local_uploads[upload_id] = {
                    'azure_status': 'in_progress' if progress_info['progress'] < 100 else 'completed',
                    'progress': progress_info['progress'],
                    'start_time': time.time() - 60,  # Assume it started a minute ago
                }

                return jsonify({
                    'status': 'uploading' if progress_info['progress'] < 100 else 'completed',
                    'progress': progress_info['progress'],
                    'stage': 'azure_upload',
                    'uploaded_bytes': progress_info.get('uploaded_bytes', 0),
                    'total_bytes': progress_info.get('file_size', 0),
                    'message': 'Progress recovered from blob service'
                })
        except Exception as bs_error:
            print(
                f"Error checking blob service for upload progress: {str(bs_error)}")

        print(f"Available upload IDs: {list(local_uploads.keys())}")
        return jsonify({
            'status': 'error',
            'error': 'Upload not found'
        })

    except Exception as e:
        # Log the error and return a proper JSON response
        import traceback
        print(f"Error in upload_progress endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'error': f'Server error: {str(e)}'
        })


def upload_to_azure(file_path, filename, upload_id, app):
    """Background task to upload file to Azure Blob Storage"""
    blob_service = None
    try:
        # Print thread details for debugging
        import threading
        print(f"upload_to_azure started in thread: {threading.get_ident()}")
        print(
            f"Parameters: file_path={file_path}, filename={filename}, upload_id={upload_id}")

        # Use the app parameter to create a context
        with app.app_context():
            # Mark as in progress
            if upload_id in local_uploads:
                local_uploads[upload_id]['azure_status'] = 'in_progress'
                print(
                    f"Updated local_uploads[{upload_id}]['azure_status'] to 'in_progress'")
            else:
                print(
                    f"WARNING: upload_id {upload_id} not found in local_uploads")
                # Create entry if it doesn't exist
                local_uploads[upload_id] = {
                    'file_path': file_path,
                    'filename': filename,
                    'status': 'local_complete',
                    'azure_status': 'in_progress',
                    'progress': 0,
                    'start_time': time.time()
                }
                print(f"Created missing local_uploads entry for {upload_id}")

            # Get blob service
            print(f"Creating BlobStorageService for upload_id={upload_id}")
            blob_service = BlobStorageService(
                connection_string=app.config['AZURE_STORAGE_CONNECTION_STRING'],
                container_name=app.config['AZURE_STORAGE_CONTAINER']
            )

            # Check if file exists before upload (for debug/error handling)
            if not os.path.exists(file_path):
                print(f"ERROR: File not found at path: {file_path}")
                raise FileNotFoundError(f"File not found at path: {file_path}")

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                print(f"ERROR: File is empty (0 bytes): {file_path}")
                raise ValueError(f"File is empty (0 bytes): {file_path}")

            print(f"File exists and has size: {file_size} bytes")

            # Upload to Azure Blob Storage with progress tracking
            # Make sure upload_id is explicitly passed for progress tracking
            print(
                f"Starting blob_service.upload_file with explicit upload_id={upload_id}")
            blob_url = blob_service.upload_file(file_path, filename, upload_id)
            print(f"Blob upload completed, URL: {blob_url}")

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
            print(f"File record created in database with ID: {file_record.id}")

            # Automatically start transcription process
            transcribe_result = transcribe_file.delay(file_record.id)
            print(
                f"Transcription task started with task ID: {transcribe_result.id}")

            # Update status
            if upload_id in local_uploads:
                local_uploads[upload_id]['azure_status'] = 'completed'
                local_uploads[upload_id]['file_id'] = file_record.id
                print(
                    f"Updated local_uploads[{upload_id}]: azure_status='completed', file_id={file_record.id}")
            else:
                print(
                    f"WARNING: upload_id {upload_id} not found in local_uploads at completion")

            # Remove temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file removed: {file_path}")
            else:
                print(f"Temporary file already removed: {file_path}")

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
            print(f"Updated local_uploads[{upload_id}] with error: {str(e)}")
        else:
            print(
                f"WARNING: upload_id {upload_id} not found in local_uploads during error handling")
            # Create the entry with error state
            local_uploads[upload_id] = {
                'file_path': file_path,
                'filename': filename,
                'status': 'error',
                'azure_status': 'error',
                'error': str(e),
                'start_time': time.time()
            }
            print(
                f"Created missing local_uploads entry with error for {upload_id}")

        # Update blob storage progress tracking if available
        if blob_service and upload_id:
            try:
                with app.app_context():
                    # Use a separate thread context lock
                    with blob_service.upload_lock:
                        if upload_id in blob_service.upload_progress:
                            blob_service.upload_progress[upload_id]['status'] = 'error'
                            blob_service.upload_progress[upload_id]['error'] = str(
                                e)
                            print(
                                f"Updated blob storage progress tracking for {upload_id}")
            except Exception as progress_error:
                print(
                    f"Error updating blob storage progress: {str(progress_error)}")

        # Clean up file if still exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up temporary file after error: {file_path}")
            except Exception as cleanup_error:
                print(
                    f"Error cleaning up temporary file: {str(cleanup_error)}")