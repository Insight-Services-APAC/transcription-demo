/**
 * File Detail Page Management
 * Handles updating file progress information on file detail page
 */

class FileDetailManager {
    constructor() {
        this.fileId = document.querySelector('.file-row')?.dataset.fileId || 
                     document.querySelector('[data-file-id]')?.dataset.fileId;
        this.progressBar = document.querySelector('.progress-bar');
        this.progressPercent = document.querySelector('.progress-percent');
        this.currentStage = document.querySelector('.current-stage');
        this.pollInterval = null;
        
        this.init();
    }
    
    /**
     * Initialize file detail page
     */
    init() {
        if (!this.fileId) return;
        
        // Check if file is in processing state
        const status = document.querySelector('.badge');
        if (status && status.textContent.includes('Processing')) {
            this.startPolling();
        }
    }
    
    /**
     * Start polling for file progress
     */
    startPolling() {
        const apiUrl = document.body.dataset.fileApiUrl || `/api/files/${this.fileId}`;
        
        this.pollInterval = setInterval(() => {
            fetch(apiUrl)
                .then(response => response.json())
                .then(data => {
                    this.updateProgress(data);
                    
                    // If processing is complete, stop polling and reload
                    if (data.status !== 'processing') {
                        this.stopPolling();
                        
                        // Reload page after a short delay
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
    
    /**
     * Update progress UI elements
     */
    updateProgress(file) {
        if (this.progressBar) {
            this.progressBar.style.width = `${file.progress_percent}%`;
        }
        
        if (this.progressPercent) {
            this.progressPercent.textContent = `${Math.round(file.progress_percent)}%`;
        }
        
        if (this.currentStage) {
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
                case 'transcribing':
                    stageText = 'Transcribing Audio';
                    break;
            }
            
            this.currentStage.textContent = stageText;
        }
    }
    
    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    new FileDetailManager();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.fileDetailManager) {
        window.fileDetailManager.stopPolling();
    }
});