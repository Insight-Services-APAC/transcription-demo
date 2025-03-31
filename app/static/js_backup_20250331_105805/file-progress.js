/**
 * File Progress Management
 * Handles monitoring file processing status and updating UI
 */

class FileProgressManager {
    constructor() {
        this.processingFiles = document.querySelectorAll('.file-row');
        this.activePolling = {};
        this.pollIntervals = {};
        
        this.init();
    }
    
    /**
     * Initialize progress polling
     */
    init() {
        if (!this.processingFiles.length) return;
        
        // Set up polling for processing files
        this.processingFiles.forEach(row => {
            const fileId = row.dataset.fileId;
            const status = row.querySelector('.badge');
            
            if (status && status.textContent.includes('Processing')) {
                // Start polling for this file
                this.startPolling(fileId);
                this.activePolling[fileId] = true;
            }
        });
    }
    
    /**
     * Start polling for file progress
     */
    startPolling(fileId) {
        // Get the API URL from data attribute
        const baseUrl = document.querySelector('body').dataset.fileApiUrl;
        const apiUrl = baseUrl ? baseUrl.replace('FILE_ID_PLACEHOLDER', fileId) : `/api/files/${fileId}`;
        
        // Poll every 3 seconds
        this.pollIntervals[fileId] = setInterval(() => {
            if (!this.activePolling[fileId]) {
                clearInterval(this.pollIntervals[fileId]);
                return;
            }
            
            // Fetch file status using the API route
            fetch(apiUrl)
                .then(response => response.json())
                .then(file => {
                    this.updateFileRow(file);
                    
                    // If processing is complete, stop polling
                    if (file.status !== 'processing') {
                        this.activePolling[fileId] = false;
                        clearInterval(this.pollIntervals[fileId]);
                        
                        // If completed or error, refresh the page once after 1 second
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error fetching file status:', error);
                });
        }, 3000);
    }
    
    /**
     * Update the file row with progress information
     */
    updateFileRow(file) {
        // Find the row
        const row = document.querySelector(`.file-row[data-file-id="${file.id}"]`);
        if (!row) return;
        
        // Update progress
        const progressCell = row.querySelector('.progress-cell');
        const progressBar = progressCell.querySelector('.progress-bar');
        const progressPercent = progressCell.querySelector('.progress-percent');
        const currentStage = progressCell.querySelector('.current-stage');
        
        if (progressBar) progressBar.style.width = `${file.progress_percent}%`;
        if (progressPercent) progressPercent.textContent = `${Math.round(file.progress_percent)}%`;
        
        // Update current stage text
        if (currentStage) {
            if (file.current_stage === 'transcribing') {
                currentStage.textContent = 'Transcribing Audio';
            } else if (file.current_stage === 'queued') {
                currentStage.textContent = 'Queued for Processing';
            } else {
                currentStage.textContent = 'Processing';
            }
        }
    }
    
    /**
     * Stop polling for a specific file
     */
    stopPolling(fileId) {
        if (this.pollIntervals[fileId]) {
            clearInterval(this.pollIntervals[fileId]);
            this.activePolling[fileId] = false;
        }
    }
    
    /**
     * Stop all polling intervals
     */
    stopAllPolling() {
        Object.keys(this.pollIntervals).forEach(fileId => {
            this.stopPolling(fileId);
        });
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.file-row')) {
        window.fileProgressManager = new FileProgressManager();
    }
});

// Clean up intervals on page unload
window.addEventListener('beforeunload', function() {
    if (window.fileProgressManager) {
        window.fileProgressManager.stopAllPolling();
    }
});