import os
import time
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
import datetime
import threading
import json


class BlobStorageService:
    def __init__(self, connection_string, container_name):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string)
        self.container_name = container_name
        self.upload_progress = {}
        self.upload_lock = threading.Lock()

        print(
            f"BlobStorageService initialized, thread ID: {threading.get_ident()}")

        # Create container if it doesn't exist
        try:
            self.blob_service_client.create_container(self.container_name)
        except Exception as e:
            # Container may already exist, which is fine
            pass

    def upload_file(self, file_path, blob_path, upload_id=None):
        """
        Upload a file from a local path to Azure Blob Storage

        Args:
            file_path (str): Path to local file
            blob_path (str): Path in blob storage
            upload_id (str, optional): ID for tracking progress

        Returns:
            str: URL of the uploaded blob
        """
        # Import threading here to ensure it's available in this method's scope
        import threading

        print(
            f"Starting upload_file method for {file_path}, upload_id={upload_id}, thread ID: {threading.get_ident()}")

        # Debug statement to verify upload_id is not None
        if upload_id is None:
            print(f"WARNING: upload_id is None for file {file_path}")
        else:
            print(f"Using upload_id: {upload_id} for tracking progress")

        # Get file size for progress calculation
        file_size = os.path.getsize(file_path)
        print(
            f"Uploading file: {file_path}, Size: {file_size / (1024*1024):.2f} MB")

        # Initialize progress tracking if upload_id is provided
        if upload_id:
            print(
                f"Initializing progress tracking for file: {file_path}, size: {file_size} bytes, upload_id: {upload_id}")

            with self.upload_lock:
                # Print the current state of upload_progress before adding the new upload
                print(
                    f"Current tracked uploads before adding: {list(self.upload_progress.keys())}")

                self.upload_progress[upload_id] = {
                    'status': 'uploading',
                    'progress': 0,
                    'started_at': datetime.datetime.now().isoformat(),
                    'file_size': file_size,
                    'uploaded_bytes': 0,
                    'last_update': time.time()
                }
                print(
                    f"Initialized progress tracking for upload_id: {upload_id}")

                # Verify the upload_id was added correctly
                print(
                    f"Current tracked uploads after adding: {list(self.upload_progress.keys())}")
                print(
                    f"Verification - upload_id in self.upload_progress: {upload_id in self.upload_progress}")

        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )

        # Determine content type based on file extension
        content_type = self._get_content_type(file_path)

        # Track upload progress
        uploaded_bytes = 0
        last_percentage = 0
        callback_count = 0  # For debugging - count how many times the callback is called

        # Store this upload_id in a local variable that can be accessed by the closure
        local_upload_id = upload_id

        # Simplified progress_callback function
        def progress_callback(current):
            nonlocal uploaded_bytes, last_percentage, callback_count

            callback_count += 1
            print(
                f"Progress callback called #{callback_count}, upload_id={local_upload_id}, thread ID: {threading.get_ident()}")

            # Handle the case where current is a PipelineResponse object
            if hasattr(current, 'context'):
                try:
                    bytes_value = getattr(current.context, 'data_read', 0)
                    if bytes_value:
                        current = bytes_value
                        print(f"Extracted bytes from context: {current}")
                    else:
                        # Just increment by a small amount if we can't get the exact value
                        current = 1024  # 1KB
                        print(
                            f"Could not extract bytes from context, using default: {current}")
                except Exception as e:
                    current = 1024  # 1KB default increment
                    print(
                        f"Error getting bytes from context: {str(e)}, using default: {current}")

            # Sanity check that current is a number
            if not isinstance(current, (int, float)):
                try:
                    current = int(current)
                    print(f"Converted non-numeric current to int: {current}")
                except (TypeError, ValueError):
                    current = 1024  # Default to 1KB
                    print(
                        f"Could not convert current to number, using default: {current}")

            # Add to total bytes uploaded
            uploaded_bytes += current

            # Calculate percentage (cap at 99% until complete)
            percentage = min(
                99, int((uploaded_bytes / file_size) * 100)) if file_size > 0 else 0

            # Artificial progress - If we've uploaded at least half the file but progress is low,
            # make the progress at least 50% to keep the UI updating
            if uploaded_bytes > file_size / 2 and percentage < 50:
                percentage = 50
                print(f"Artificially bumping progress to 50% based on uploaded bytes")

            # Update progress in memory
            if local_upload_id:
                # Important: Use a copy of the upload_id that's consistent throughout this callback
                upload_id_to_use = local_upload_id
                try:
                    with self.upload_lock:
                        # Check if the key exists in dictionary before updating
                        if upload_id_to_use in self.upload_progress:
                            print(
                                f"Updating progress for {upload_id_to_use}: {percentage}% ({uploaded_bytes}/{file_size})")
                            self.upload_progress[upload_id_to_use]['progress'] = percentage
                            self.upload_progress[upload_id_to_use]['uploaded_bytes'] = uploaded_bytes
                            self.upload_progress[upload_id_to_use]['last_update'] = time.time(
                            )
                        else:
                            # If key no longer exists, recreate it
                            print(
                                f"WARNING: upload_id {upload_id_to_use} not found in upload_progress during callback, recreating entry")
                            self.upload_progress[upload_id_to_use] = {
                                'status': 'uploading',
                                'progress': percentage,
                                'started_at': datetime.datetime.now().isoformat(),
                                'file_size': file_size,
                                'uploaded_bytes': uploaded_bytes,
                                'last_update': time.time()
                            }
                except Exception as e:
                    print(f"Error updating progress data: {str(e)}")
            else:
                print(f"WARNING: No upload_id available for progress tracking")

            # Log progress at reasonable intervals
            if percentage > last_percentage:
                print(
                    f"Upload progress: {percentage}% ({uploaded_bytes / (1024*1024):.2f} MB / {file_size / (1024*1024):.2f} MB)")
                last_percentage = percentage

            # Every 10 callbacks, print the current state of upload_progress for debugging
            if callback_count % 10 == 0:
                with self.upload_lock:
                    print(
                        f"Current upload_progress keys: {list(self.upload_progress.keys())}")
                    if local_upload_id in self.upload_progress:
                        print(
                            f"Current progress value: {self.upload_progress[local_upload_id]['progress']}%")

        try:
            # Upload with progress tracking
            print(
                f"Starting Azure Blob upload for file: {file_path}, upload_id={local_upload_id}")

            # Start a thread to simulate progress updates for large files
            # This ensures progress updates continue even if Azure callbacks are infrequent
            if local_upload_id and file_size > 10*1024*1024:  # For files larger than 10MB
                simulate_progress = True
                thread_module = threading  # Store the module in a local variable for the closure

                def simulate_progress_updates():
                    """Simulate progress updates based on time"""
                    simulation_count = 0
                    while simulate_progress and local_upload_id:
                        time.sleep(1)  # Update progress every second
                        simulation_count += 1

                        # Get current progress data
                        current_progress = 0
                        try:
                            with self.upload_lock:
                                if local_upload_id in self.upload_progress:
                                    current_progress = self.upload_progress[local_upload_id].get(
                                        'progress', 0)
                                    current_status = self.upload_progress[local_upload_id].get(
                                        'status', 'uploading')

                                    # Stop if upload is completed or errored
                                    if current_status in ['completed', 'error']:
                                        break

                                    # If no progress update in last 3 seconds, increment by 1-2%
                                    last_update = self.upload_progress[local_upload_id].get(
                                        'last_update', 0)
                                    if time.time() - last_update > 3:
                                        # Artificially increment progress by 1-2% up to 95%
                                        new_progress = min(
                                            95, current_progress + 1)

                                        # Update progress
                                        print(
                                            f"Simulating progress update: {new_progress}% (simulation #{simulation_count})")
                                        self.upload_progress[local_upload_id]['progress'] = new_progress
                                        self.upload_progress[local_upload_id]['last_update'] = time.time(
                                        )
                                else:
                                    # Upload progress entry not found, stop simulation
                                    break
                        except Exception as e:
                            print(f"Error in progress simulation: {str(e)}")
                            break

                # Start progress simulation in a background thread
                progress_thread = thread_module.Thread(
                    target=simulate_progress_updates)
                progress_thread.daemon = True
                progress_thread.start()
                print(
                    f"Started progress simulation thread: {progress_thread.ident}")
            else:
                simulate_progress = False

            with open(file_path, "rb") as data:
                # Note the key parameters that affect callbacks:
                # - max_concurrency: Controls parallel upload chunks
                # - raw_response_hook: Our callback for progress tracking
                upload_start_time = time.time()

                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(
                        content_type=content_type),
                    max_concurrency=1,  # Use single thread for more reliable progress tracking
                    raw_response_hook=progress_callback
                )

            # Stop progress simulation
            if 'simulate_progress' in locals():
                simulate_progress = False

            upload_duration = time.time() - upload_start_time
            print(f"Azure upload completed in {upload_duration:.2f} seconds")
            print(f"Callback was called {callback_count} times")

            # Update status to completed
            if local_upload_id:
                upload_id_to_use = local_upload_id  # Consistent variable naming
                with self.upload_lock:
                    if upload_id_to_use in self.upload_progress:
                        print(
                            f"Marking upload {upload_id_to_use} as completed")
                        self.upload_progress[upload_id_to_use]['status'] = 'completed'
                        self.upload_progress[upload_id_to_use]['progress'] = 100
                        self.upload_progress[upload_id_to_use]['uploaded_bytes'] = file_size
                        self.upload_progress[upload_id_to_use]['last_update'] = time.time(
                        )
                    else:
                        print(
                            f"WARNING: upload_id {upload_id_to_use} not found in upload_progress at completion")
                        # Recreate entry if it disappeared
                        self.upload_progress[upload_id_to_use] = {
                            'status': 'completed',
                            'progress': 100,
                            'started_at': datetime.datetime.now().isoformat(),
                            'file_size': file_size,
                            'uploaded_bytes': file_size,
                            'last_update': time.time()
                        }

            return blob_client.url

        except Exception as e:
            # Update status to error
            print(f"Error during upload: {str(e)}")
            if local_upload_id:
                with self.upload_lock:
                    if local_upload_id in self.upload_progress:
                        self.upload_progress[local_upload_id]['status'] = 'error'
                        self.upload_progress[local_upload_id]['error'] = str(e)
                        self.upload_progress[local_upload_id]['last_update'] = time.time(
                        )
                    else:
                        print(
                            f"WARNING: upload_id {local_upload_id} not found in upload_progress during error handling")

            print(f"Upload error: {str(e)}")
            raise e

    def upload_bytes(self, data, blob_path, content_type=None):
        """Upload bytes data to Azure Blob Storage"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )

        # Set content type if provided
        content_settings = None
        if content_type:
            content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings
        )

        return blob_client.url

    def download_file(self, blob_path, local_path):
        """Download a file from Azure Blob Storage"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, "wb") as download_file:
            download_data = blob_client.download_blob()
            download_file.write(download_data.readall())

        return local_path

    def get_blob_url(self, blob_path):
        """Get the URL for a blob"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        return blob_client.url

    def get_upload_progress(self, upload_id):
        """Get the current progress of an upload"""
        print(
            f"get_upload_progress called for upload_id: {upload_id}, thread ID: {threading.get_ident()}")
        try:
            # Debug: print all tracked uploads
            with self.upload_lock:
                print(
                    f"Current tracked uploads: {list(self.upload_progress.keys())}")
                print(
                    f"Check if {upload_id} is in upload_progress: {upload_id in self.upload_progress}")

            with self.upload_lock:
                if upload_id in self.upload_progress:
                    # Make a copy of the progress data to avoid thread issues
                    progress_data = {
                        'status': self.upload_progress[upload_id].get('status', 'unknown'),
                        'progress': self.upload_progress[upload_id].get('progress', 0),
                        'started_at': self.upload_progress[upload_id].get('started_at', ''),
                        'file_size': self.upload_progress[upload_id].get('file_size', 0),
                        'uploaded_bytes': self.upload_progress[upload_id].get('uploaded_bytes', 0),
                        'last_update': self.upload_progress[upload_id].get('last_update', 0)
                    }

                    # Check for error
                    if 'error' in self.upload_progress[upload_id]:
                        progress_data['error'] = self.upload_progress[upload_id]['error']

                    print(f"Progress data for {upload_id}: {progress_data}")
                    return progress_data
                else:
                    print(f"No progress data found for upload_id: {upload_id}")
                    print(
                        f"Available keys: {list(self.upload_progress.keys())}")
                    return None
        except Exception as e:
            print(f"Error getting upload progress: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return a basic progress object that won't cause client-side issues
            return {
                'status': 'error',
                'progress': 0,
                'error': f'Error tracking progress: {str(e)}',
                'file_size': 0,
                'uploaded_bytes': 0
            }

    def cleanup_progress(self, upload_id):
        """Remove a completed or errored upload from progress tracking"""
        print(f"cleanup_progress called for upload_id: {upload_id}")
        with self.upload_lock:
            if upload_id in self.upload_progress:
                # Only remove if status is completed or error
                status = self.upload_progress[upload_id]['status']
                if status in ['completed', 'error']:
                    del self.upload_progress[upload_id]
                    print(
                        f"Removed upload_id {upload_id} from progress tracking")
                    return True
                else:
                    print(
                        f"Not removing upload_id {upload_id} because status is {status}")
            else:
                print(f"upload_id {upload_id} not found in progress tracking")
            return False

    def _get_content_type(self, file_path):
        """Determine content type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.dcr': 'application/octet-stream',
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        return content_types.get(extension, 'application/octet-stream')
