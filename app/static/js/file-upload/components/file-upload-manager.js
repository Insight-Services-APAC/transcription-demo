/**
 * File Upload Manager
 * Handles the actual file upload process
 */
export class FileUploadManager {
    constructor(uiManager) {
        this.uiManager = uiManager;
        this.uploadForm = document.getElementById('uploadForm');
    }
    
    startUpload(formData) {
        return new Promise((resolve, reject) => {
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
                    
                    // Update UI
                    this.uiManager.updateProgress({
                        percent: totalPercentComplete,
                        stage: 'Local upload',
                        statusText: '<small class="text-muted">Uploading file to server...</small>'
                    });
                    
                    // Estimate time remaining for local upload
                    if (uploadSpeed > 0) {
                        const remainingBytes = event.total - event.loaded;
                        const remainingTimeMs = remainingBytes / uploadSpeed;
                        const remainingTimeSec = remainingTimeMs / 1000;
                        
                        this.uiManager.updateProgress({
                            timeRemaining: this.uiManager.formatTimeRemaining(remainingTimeSec)
                        });
                    }
                }
            });
            
            // Configure load event (successful local upload)
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    try {
                        // Local upload complete, now update for azure upload (remaining 75%)
                        this.uiManager.updateProgress({
                            percent: 25,
                            stage: 'Initializing Azure upload',
                            statusText: '<small class="text-muted">Starting Celery task for Azure upload...</small>'
                        });
                        
                        // Parse the JSON response to get upload_id and task_id
                        const response = JSON.parse(xhr.responseText);
                        if (response.upload_id && response.task_id) {
                            resolve(response);
                        } else {
                            reject(new Error('Invalid server response'));
                        }
                    } catch (e) {
                        reject(new Error('Error parsing server response: ' + e.message));
                    }
                } else {
                    reject(new Error('Upload failed with status ' + xhr.status));
                }
            });
            
            // Configure error event
            xhr.addEventListener('error', () => {
                reject(new Error('Network error occurred'));
            });
            
            // Capture model selection
            const modelSelect = document.getElementById('transcription_model');
            if (modelSelect && modelSelect.value) {
                // Add the model information to the form data
                formData.append('model_id', modelSelect.value);
                
                // Also add the model name if available
                const selectedOption = modelSelect.options[modelSelect.selectedIndex];
                if (selectedOption && selectedOption.dataset.name) {
                    formData.append('model_name', selectedOption.dataset.name);
                }
            }
            
            // Open and send the request to the AJAX upload start endpoint
            xhr.open('POST', this.uploadForm.getAttribute('data-start-url'), true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            // CSRF token is automatically added by the XHR prototype override in main.js
            xhr.send(formData);
        });
    }
}