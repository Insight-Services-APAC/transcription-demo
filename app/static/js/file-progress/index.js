/**
 * File Progress Application
 * Main controller for monitoring file processing status
 */
import { ProgressManager } from './components/progress-manager.js';
import { FilePollingService } from './services/file-polling-service.js';

class FileProgressApp {
    constructor() {
        this.progressManager = new ProgressManager();
        this.pollingService = new FilePollingService(this.progressManager);
        
        this.init();
    }
    
    init() {
        // Check if we're on a page with file rows
        if (!document.querySelector('.file-row')) return;
        
        // Find processing files and start polling
        this.progressManager.findProcessingFiles();
        
        // Start polling for each processing file
        const fileIds = this.progressManager.getProcessingFileIds();
        fileIds.forEach(fileId => {
            this.pollingService.startPolling(fileId);
        });
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    window.fileProgressApp = new FileProgressApp();
});

// Clean up intervals on page unload
window.addEventListener('beforeunload', function() {
    if (window.fileProgressApp && window.fileProgressApp.pollingService) {
        window.fileProgressApp.pollingService.stopAllPolling();
    }
});
