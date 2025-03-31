/**
 * Upload Progress Tracker
 * Tracks upload progress and updates UI
 */
export class UploadProgressTracker {
    constructor(uiManager) {
        this.uiManager = uiManager;
        this.uploadForm = document.getElementById('uploadForm');
        this.progressPollInterval = null;
        this.taskStatusInterval = null;
        this.fileSize = 0;
    }
    
    startTracking(uploadId, taskId) {
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
        }
        
        if (this.taskStatusInterval) {
            clearInterval(this.taskStatusInterval);
        }
        
        // Get the file size from the file input
        const fileInput = document.getElementById('file');
        if (fileInput && fileInput.files.length > 0) {
            this.fileSize = fileInput.files[0].size;
        }
        
        // Start polling for progress
        this.pollUploadProgress(uploadId, taskId, this.fileSize);
    }
    
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
        this.uiManager.updateProgress({
            statusText: '<small class="text-muted">Preparing Azure upload...</small>'
        });
        
        // Poll for progress updates from the upload_progress endpoint
        this.progressPollInterval = setInterval(() => {
            pollCount++;
            
            if (pollCount > maxPolls) {
                clearInterval(this.progressPollInterval);
                this.uiManager.showError('Upload timeout after 30 minutes');
                return;
            }
            
            // Fetch progress from server
            const progressUrl = this.uploadForm.getAttribute('data-progress-url').replace('UPLOAD_ID_PLACEHOLDER', uploadId);
            
            fetch(progressUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        consecutiveEmptyResponses++;
                        if (consecutiveEmptyResponses >= maxEmptyResponses) {
                            clearInterval(this.progressPollInterval);
                            this.uiManager.showError(data.error);
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
                        
                        this.uiManager.updateProgress({
                            percent: 100,
                            stage: 'Processing',
                            statusText: '<small class="text-success">Upload complete! Processing file...</small>'
                        });
                        
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
                            
                            // Update UI
                            this.uiManager.updateProgress({
                                percent: totalPercentComplete,
                                stage: data.stage === 'azure_upload' ? 'Azure upload' : data.stage,
                                statusText: '<small class="text-muted">Uploading to Azure storage...</small>'
                            });
                            
                            if (azureUploadSpeed > 0) {
                                const remainingPercent = 100 - azurePercentComplete;
                                const remainingBytes = fileSize * (remainingPercent / 100);
                                const remainingTimeMs = remainingBytes / azureUploadSpeed;
                                const remainingTimeSec = remainingTimeMs / 1000;
                                
                                this.uiManager.updateProgress({
                                    timeRemaining: this.uiManager.formatTimeRemaining(remainingTimeSec)
                                });
                            }
                        } else {
                            if (pollCount > 10) {
                                this.uiManager.updateProgress({
                                    statusText: '<small class="text-muted">Upload in progress, waiting for progress data...</small>'
                                });
                            }
                        }
                    }
                })
                .catch(error => {
                    console.error('Error polling for progress:', error);
                    consecutiveEmptyResponses++;
                    if (consecutiveEmptyResponses >= 10) {
                        this.uiManager.updateProgress({
                            statusText: '<small class="text-warning">Network issues, retrying...</small>'
                        });
                    }
                });
        }, pollInterval);
        
        // Also poll for task status as a backup
        this.pollTaskStatus(taskId);
    }
    
    pollTaskStatus(taskId) {
        this.taskStatusInterval = setInterval(() => {
            const taskStatusUrl = `/task/status/${taskId}`;
            
            fetch(taskStatusUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.state === 'FAILURE') {
                        clearInterval(this.progressPollInterval);
                        clearInterval(this.taskStatusInterval);
                        this.uiManager.showError(data.error || 'Task failed');
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
    
    stopTracking() {
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
        }
        
        if (this.taskStatusInterval) {
            clearInterval(this.taskStatusInterval);
        }
    }
}
