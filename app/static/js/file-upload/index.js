/**
 * File Upload Application
 * Main controller for the file upload functionality
 */
import { FileUploadUIManager } from './components/file-upload-ui-manager.js';
import { FileUploadManager } from './components/file-upload-manager.js';
import { UploadProgressTracker } from './components/upload-progress-tracker.js';

class FileUploadApp {
    constructor() {
        // Create component instances
        this.uiManager = new FileUploadUIManager();
        this.uploadManager = new FileUploadManager(this.uiManager);
        this.progressTracker = new UploadProgressTracker(this.uiManager);
        
        // Initialize
        this.init();
    }
    
    init() {
        // Check if we're on the upload page
        if (!document.getElementById('uploadForm')) return;
        
        // Set up event listeners
        this.uiManager.initEventListeners();
        this.uiManager.setFileChangeCallback(file => this.handleFileChange(file));
        this.uiManager.setFormSubmitCallback(formData => this.handleFormSubmit(formData));
    }
    
    handleFileChange(file) {
        if (!file) return;
        
        // Update UI with file info
        this.uiManager.updateFileInfo(file);
    }
    
    handleFormSubmit(formData) {
        // Start upload process
        this.uploadManager.startUpload(formData)
            .then(response => {
                // Start tracking progress
                this.progressTracker.startTracking(response.upload_id, response.task_id);
            })
            .catch(error => {
                this.uiManager.showError(error.message);
            });
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    new FileUploadApp();
});
