/**
 * File Upload UI Manager
 * Handles the UI for file uploads
 */
export class FileUploadUIManager {
    constructor() {
        // DOM elements
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
        
        // Callbacks
        this.fileChangeCallback = null;
        this.formSubmitCallback = null;
    }
    
    initEventListeners() {
        if (!this.fileInput || !this.uploadForm) return;
        
        // File selection change
        this.fileInput.addEventListener('change', () => {
            const file = this.fileInput.files.length > 0 ? this.fileInput.files[0] : null;
            if (this.fileChangeCallback) this.fileChangeCallback(file);
        });
        
        // Form submission
        this.uploadForm.addEventListener('submit', e => {
            e.preventDefault();
            if (this.fileInput.files.length > 0) {
                // Prepare form data
                const formData = new FormData(this.uploadForm);
                
                // Display progress UI
                this.showProgressUI();
                
                // Call submit callback
                if (this.formSubmitCallback) this.formSubmitCallback(formData);
            }
        });
        
        // Drag and drop functionality
        this.initDragDropEvents();
    }
    
    initDragDropEvents() {
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
    
    setFileChangeCallback(callback) {
        this.fileChangeCallback = callback;
    }
    
    setFormSubmitCallback(callback) {
        this.formSubmitCallback = callback;
    }
    
    updateFileInfo(file) {
        this.selectedFileName.textContent = file.name;
        this.selectedFileSize.textContent = `File size: ${this.formatFileSize(file.size)}`;
        
        this.dropArea.classList.add('has-file');
        this.dropAreaContent.classList.add('d-none');
        this.fileSelectedContent.classList.remove('d-none');
    }
    
    showProgressUI() {
        this.uploadProgressContainer.classList.remove('d-none');
        this.uploadStatusText.classList.remove('d-none');
        this.uploadStageText.classList.remove('d-none');
        this.uploadTimeRemaining.classList.remove('d-none');
        
        // Disable upload button
        this.uploadButton.disabled = true;
        this.uploadButton.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i>Uploading...';
    }
    
    updateProgress(progressData) {
        // Update progress bar
        this.uploadProgressBar.style.width = progressData.percent + '%';
        this.uploadPercentage.textContent = progressData.percent + '%';
        
        // Update stage
        if (progressData.stage) {
            this.currentStage.textContent = progressData.stage;
        }
        
        // Update status text
        if (progressData.statusText) {
            this.uploadStatusText.innerHTML = progressData.statusText;
        }
        
        // Update time remaining
        if (progressData.timeRemaining !== undefined) {
            this.timeRemaining.textContent = progressData.timeRemaining;
        }
    }
    
    showError(message) {
        this.uploadButton.disabled = false;
        this.uploadButton.innerHTML = '<i class="fas fa-upload me-2"></i>Try Again';
        this.uploadStatusText.innerHTML = `<small class="text-danger">Error: ${message}</small>`;
        this.timeRemaining.textContent = 'N/A';
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    highlight() {
        this.dropArea.classList.add('has-file');
    }
    
    unhighlight() {
        if (this.fileInput.files.length === 0) {
            this.dropArea.classList.remove('has-file');
        }
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        this.fileInput.files = files;
        
        const event = new Event('change');
        this.fileInput.dispatchEvent(event);
    }
    
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
    
    formatTimeRemaining(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)} seconds`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)} minutes ${Math.round(seconds % 60)} seconds`;
        } else {
            return `${Math.floor(seconds / 3600)} hours ${Math.floor((seconds % 3600) / 60)} minutes`;
        }
    }
