// Main JavaScript for Transcription App

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Add confirm dialog to delete buttons
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // File upload progress monitoring
    monitorFileUploadProgress();
});

// Function to handle file upload progress monitoring
function monitorFileUploadProgress() {
    // These elements will be in the upload.html page
    const fileUploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('file');
    const uploadButton = document.getElementById('uploadButton');
    const uploadProgressContainer = document.getElementById('uploadProgressContainer');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    const uploadPercentage = document.getElementById('uploadPercentage');
    const uploadStatusText = document.getElementById('uploadStatusText');
    const uploadStageText = document.getElementById('uploadStageText');
    const currentStage = document.getElementById('currentStage');
    const uploadTimeRemaining = document.getElementById('uploadTimeRemaining');
    const timeRemaining = document.getElementById('timeRemaining');
    
    // Exit if not on upload page
    if (!fileUploadForm) return;
    
    // Check file size when selected
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const fileSize = this.files[0].size;
            
            // Check if file is too large (over 5GB)
            if (fileSize > 5 * 1024 * 1024 * 1024) {
                alert('File is too large. Maximum size is 5GB.');
                this.value = '';
            }
        }
    });
    
    // Monitor active uploads
    const fileDetailsPage = document.querySelector('.file-row');
    if (fileDetailsPage) {
        // If we're on the file details page, check for processing files
        const processingFiles = document.querySelectorAll('.file-row');
        
        processingFiles.forEach(row => {
            const fileId = row.dataset.fileId;
            const status = row.querySelector('.badge');
            
            if (status && status.textContent.includes('Processing')) {
                // Set up polling for this file
                pollFileProgress(fileId);
            }
        });
    }
    
    // Poll for file processing progress
    function pollFileProgress(fileId) {
        const pollInterval = setInterval(function() {
            fetch(`/api/files/${fileId}`)
                .then(response => response.json())
                .then(data => {
                    // Update UI with the progress
                    updateFileProgressUI(data);
                    
                    // If processing is complete, stop polling
                    if (data.status !== 'processing') {
                        clearInterval(pollInterval);
                        
                        // Reload page after a small delay
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error fetching file progress:', error);
                });
        }, 3000);
    }
    
    // Update file progress UI
    function updateFileProgressUI(file) {
        const row = document.querySelector(`.file-row[data-file-id="${file.id}"]`);
        if (!row) return;
        
        const progressBar = row.querySelector('.progress-bar');
        const progressPercent = row.querySelector('.progress-percent');
        const currentStageText = row.querySelector('.current-stage');
        
        if (progressBar) {
            progressBar.style.width = `${file.progress_percent}%`;
        }
        
        if (progressPercent) {
            progressPercent.textContent = `${Math.round(file.progress_percent)}%`;
        }
        
        if (currentStageText) {
            let stageText = 'Processing';
            
            switch (file.current_stage) {
                case 'extract_audio':
                    stageText = 'Extracting Audio';
                    break;
                case 'chunk_audio':
                    stageText = 'Chunking Audio';
                    break;
                case 'transcribe_chunks':
                    stageText = `Transcribing (${file.chunks_processed || 0}/${file.chunk_count || '?'})`;
                    break;
                case 'diarization':
                    stageText = 'Identifying Speakers';
                    break;
                case 'stitch_transcript':
                    stageText = 'Generating Transcript';
                    break;
                case 'queued':
                    stageText = 'Queued for Processing';
                    break;
            }
            
            currentStageText.textContent = stageText;
        }
    }
}