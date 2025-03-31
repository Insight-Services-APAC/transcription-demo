/**
 * File Upload Management
 * Handles file selection, drag-and-drop, and upload progress tracking
 */

class FileUploadManager {
    constructor() {
        this.fileInput = document.getElementById('file');
        this.dropArea = document.querySelector('.form-file-container');
        this.dropAreaContent = document.getElementById('dropAreaContent');
        this.fileSelectedContent = document.getElementById('fileSelectedContent');
        this.selectedFileName = document.getElementById('selectedFileName');
        this.selectedFileSize = document.getElementById('selectedFileSize');
        this.uploadForm = document.getElementById('uploadForm');
        this.uploadButton = document.getElementById('uploadButton');
        this.uploadProgressContainer = document.getElementById('uploadProgressContainer');
        this.uploadProgressBar = document.getElementById('uploadProgressBar');
        this.uploadStatusText = document.getElementById('uploadStatusText');
        this.uploadPercentage = document.getElementById('uploadPercentage');
        this.uploadStageText = document.getElementById('uploadStageText');
        this.currentStage = document.getElementById('currentStage');
        this.uploadTimeRemaining = document.getElementById('uploadTimeRemaining');
        this.timeRemaining = document.getElementById('timeRemaining');
        
        this.progressPollInterval = null;
        this.taskStatusInterval = null;
        this.initEventListeners();
    }
    
    /**
     * Initialize all event listeners
     */
    initEventListeners() {
        if (!this.fileInput || !this.uploadForm) return;
        
        // File selection change
        this.fileInput.addEventListener('change', this.handleFileSelection.bind(this));
        
        // Form submission
        this.uploadForm.addEventListener('submit', this.handleFormSubmit.bind(this));
        
        // Drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.highlight.bind(this), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.unhighlight.bind(this), false);
        });
        
        this.dropArea.addEventListener('drop', this.handleDrop.bind(this), false);
    }
    
    /**
     * Format file size in a human-readable way
     */
    formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' bytes';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(2) + ' KB';
        } else if (bytes < 1024 * 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        } else {
            return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
        }
    }
    
    /**
     * Format time remaining in a human-readable way
     */
    formatTimeRemaining(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)} seconds`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)} minutes ${Math.round(seconds % 60)} seconds`;
        } else {
            return `${Math.floor(seconds / 3600)} hours ${Math.floor((seconds % 3600) / 60)} minutes`;
        }
    }
    
    /**
     * Handle file selection
     */
    handleFileSelection() {
        if (this.fileInput.files.length > 0) {
            const fileName = this.fileInput.files[0].name;
            const fileSize = this.fileInput.files[0].size;
            
            this.selectedFileName.textContent = fileName;
            this.selectedFileSize.textContent = `File size: ${this.formatFileSize(fileSize)}`;
            
            this.dropArea.classList.add('has-file');
            this.dropAreaContent.classList.add('d-none');
            this.fileSelectedContent.classList.remove('d-none');
        } else {
            this.dropArea.classList.remove('has-file');
            this.dropAreaContent.classList.remove('d-none');
            this.fileSelectedContent.classList.add('d-none');
        }
    }
    
    /**
     * Handle form submission
     */
    handleFormSubmit(e) {
        if (this.fileInput.files.length > 0) {
            e.preventDefault();
            
            const file = this.fileInput.files[0];
            const fileSize = file.size;
            
            // Display progress elements
            this.uploadProgressContainer.classList.remove('d-none');
            this.uploadStatusText.classList.remove('d-none');
            this.uploadStageText.classList.remove('d-none');
            this.uploadTimeRemaining.classList.remove('d-none');
            
            // Disable upload button
            this.uploadButton.disabled = true;
            this.uploadButton.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i>Uploading...';
            
            // Create FormData
            const formData = new FormData(this.uploadForm);
            
            // Create XHR request
            const xhr = new XMLHttpRequest();
            
            // Variables for progress tracking
            let uploadStartTime = Date.now();
            let lastLoaded = 0;
            let uploadSpeed = 0; // bytes per millisecond
            
            // Configure progress event - local upload (25% of progress)
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    // Calculate upload speed
                    const elapsedTime = Date.now() - uploadStartTime;
                    if (elapsedTime > 0) {
                        const loadedChange = event.loaded - lastLoaded;
                        const timeChange = elapsedTime;
                        // Moving average for upload speed
                        uploadSpeed = (uploadSpeed * 0.7) + (loadedChange / timeChange * 0.3);
                        lastLoaded = event.loaded;
                        uploadStartTime = Date.now();
                    }
                    
                    // Local upload is 25% of total progress
                    const localPercentComplete = Math.round((event.loaded / event.total) * 100);
                    const totalPercentComplete = Math.round(localPercentComplete * 0.25);
                    
                    // Update progress bar
                    this.uploadProgressBar.style.width = totalPercentComplete + '%';
                    this.uploadPercentage.textContent = totalPercentComplete + '%';
                    this.currentStage.textContent = 'Local upload';
                    
                    // Estimate time remaining for local upload
                    if (uploadSpeed > 0) {
                        const remainingBytes = event.total - event.loaded;
                        const remainingTimeMs = remainingBytes / uploadSpeed;
                        const remainingTimeSec = remainingTimeMs / 1000;
                        this.timeRemaining.textContent = this.formatTimeRemaining(remainingTimeSec);
                    }
                }
            });
            
            // Configure load event (successful local upload)
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    // Log the response for debugging
                    console.log("Server response:", xhr.responseText);
                    
                    try {
                        // Local upload complete, now update for azure upload (remaining 75%)
                        this.uploadStatusText.innerHTML = '<small class="text-muted">Starting Celery task for Azure upload...</small>';
                        this.currentStage.textContent = 'Initializing Azure upload';
                        
                        // Parse the JSON response to get upload_id and task_id
                        const response = JSON.parse(xhr.responseText);
                        if (response.upload_id && response.task_id) {
                            console.log(`Upload ID: ${response.upload_id}, Task ID: ${response.task_id}`);
                            
                            // Start polling for upload progress
                            this.pollUploadProgress(response.upload_id, response.task_id, fileSize);
                        } else {
                            this.handleUploadError('Invalid server response');
                        }
                    } catch (e) {
                        console.error("JSON parse error", e, "Response was:", xhr.responseText);
                        this.handleUploadError('Error parsing server response: ' + e.message);
                    }
                } else {
                    this.handleUploadError('Upload failed with status ' + xhr.status);
                }
            });
            
            // Configure error event
            xhr.addEventListener('error', () => {
                this.handleUploadError('Network error occurred');
            });
            
            // Open and send the request to the AJAX upload start endpoint
            xhr.open('POST', this.uploadForm.getAttribute('data-start-url'), true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
        }
    }
    
    /**
     * Poll for upload progress and task status
     */
    pollUploadProgress(uploadId, taskId, fileSize) {
        const pollInterval = 1500; // 1.5 seconds
        const maxPolls = 1800; // 30 minutes max (at 1.5s each)
        let pollCount = 0;
        let lastAzureProgress = 0;
        let azureUploadStartTime = Date.now();
        let azureUploadSpeed = 0;
        let consecutiveEmptyResponses = 0;
        const maxEmptyResponses = 5; // Number of empty responses before showing a note
        
        // Show initial message
        this.uploadStatusText.innerHTML = '<small class="text-muted">Preparing Azure upload...</small>';
        
        // Poll for progress updates from the upload_progress endpoint
        this.progressPollInterval = setInterval(() => {
            pollCount++;
            
            if (pollCount > maxPolls) {
                clearInterval(this.progressPollInterval);
                this.handleUploadError('Upload timeout after 30 minutes');
                return;
            }
            
            // Fetch progress from server
            const progressUrl = this.uploadForm.getAttribute('data-progress-url').replace('UPLOAD_ID_PLACEHOLDER', uploadId);
            
            fetch(progressUrl)
                .then(response => response.json())
                .then(data => {
                    console.log("Progress response:", data);
                    
                    if (data.error) {
                        consecutiveEmptyResponses++;
                        if (consecutiveEmptyResponses >= maxEmptyResponses) {
                            clearInterval(this.progressPollInterval);
                            this.handleUploadError(data.error);
                            return;
                        }
                        return;
                    }
                    
                    consecutiveEmptyResponses = 0;
                    
                    if (data.status === 'completed') {
                        clearInterval(this.progressPollInterval);
                        if (this.taskStatusInterval) {
                            clearInterval(this.taskStatusInterval);
                        }
                        
                        this.uploadProgressBar.style.width = '100%';
                        this.uploadPercentage.textContent = '100%';
                        this.uploadStatusText.innerHTML = '<small class="text-success">Upload complete! Processing file...</small>';
                        this.currentStage.textContent = 'Processing';
                        
                        if (data.redirect_url) {
                            window.location.href = data.redirect_url;
                        } else {
                            window.location.href = this.uploadForm.getAttribute('data-files-url');
                        }
                        return;
                    }
                    
                    if (data.status === 'uploading') {
                        if (data.progress > 0 || data.uploaded_bytes > 0) {
                            const elapsedTime = Date.now() - azureUploadStartTime;
                            const progressChange = data.progress - lastAzureProgress;
                            
                            if (elapsedTime > 0 && progressChange > 0) {
                                const bytesUploaded = fileSize * (progressChange / 100);
                                azureUploadSpeed = (azureUploadSpeed * 0.7) + ((bytesUploaded / elapsedTime) * 0.3);
                                lastAzureProgress = data.progress;
                                azureUploadStartTime = Date.now();
                            }
                            
                            const azurePercentComplete = data.progress;
                            const totalPercentComplete = 25 + (azurePercentComplete * 0.75);
                            
                            this.uploadProgressBar.style.width = totalPercentComplete + '%';
                            this.uploadPercentage.textContent = Math.round(totalPercentComplete) + '%';
                            this.uploadStatusText.innerHTML = '<small class="text-muted">Uploading to Azure storage...</small>';
                            
                            if (data.stage) {
                                this.currentStage.textContent = data.stage === 'azure_upload' ? 'Azure upload' : data.stage;
                            }
                            
                            if (azureUploadSpeed > 0) {
                                const remainingPercent = 100 - azurePercentComplete;
                                const remainingBytes = fileSize * (remainingPercent / 100);
                                const remainingTimeMs = remainingBytes / azureUploadSpeed;
                                const remainingTimeSec = remainingTimeMs / 1000;
                                this.timeRemaining.textContent = this.formatTimeRemaining(remainingTimeSec);
                            }
                        } else {
                            if (pollCount > 10) {
                                this.uploadStatusText.innerHTML = '<small class="text-muted">Upload in progress, waiting for progress data...</small>';
                            }
                        }
                    }
                })
                .catch(error => {
                    console.error('Error polling for progress:', error);
                    consecutiveEmptyResponses++;
                    if (consecutiveEmptyResponses >= 10) {
                        this.uploadStatusText.innerHTML = '<small class="text-warning">Network issues, retrying...</small>';
                    }
                });
        }, pollInterval);
        
        // Also poll for task status as a backup
        this.taskStatusInterval = setInterval(() => {
            const taskStatusUrl = `/task/status/${taskId}`;
            
            fetch(taskStatusUrl)
                .then(response => response.json())
                .then(data => {
                    console.log("Task status:", data);
                    
                    if (data.state === 'FAILURE') {
                        clearInterval(this.progressPollInterval);
                        clearInterval(this.taskStatusInterval);
                        this.handleUploadError(data.error || 'Task failed');
                    } else if (data.state === 'SUCCESS') {
                        // Task completed successfully, we'll let the progress endpoint handle redirect
                        clearInterval(this.taskStatusInterval);
                    }
                })
                .catch(error => {
                    console.error('Error polling for task status:', error);
                });
        }, 5000); // Check task status every 5 seconds
    }
    
    /**
     * Handle upload error
     */
    handleUploadError(message) {
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
        }
        if (this.taskStatusInterval) {
            clearInterval(this.taskStatusInterval);
        }
        
        this.uploadButton.disabled = false;
        this.uploadButton.innerHTML = '<i class="fas fa-upload me-2"></i>Try Again';
        this.uploadStatusText.innerHTML = `<small class="text-danger">Error: ${message}</small>`;
        this.timeRemaining.textContent = 'N/A';
        console.error('Upload error:', message);
    }
    
    /**
     * Prevent default events
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    /**
     * Highlight drop area
     */
    highlight() {
        this.dropArea.classList.add('has-file');
    }
    
    /**
     * Remove highlight from drop area
     */
    unhighlight() {
        if (this.fileInput.files.length === 0) {
            this.dropArea.classList.remove('has-file');
        }
    }
    
    /**
     * Handle file drop
     */
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        this.fileInput.files = files;
        
        const event = new Event('change');
        this.fileInput.dispatchEvent(event);
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    new FileUploadManager();
});