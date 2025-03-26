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
    
    // File upload progress visualization
    const fileInput = document.getElementById('file');
    const uploadForm = document.querySelector('form[enctype="multipart/form-data"]');
    
    if (fileInput && uploadForm) {
        fileInput.addEventListener('change', function() {
            const fileSize = this.files[0]?.size;
            if (fileSize > 5 * 1024 * 1024 * 1024) { // 5GB
                alert('File is too large. Maximum size is 5GB.');
                this.value = '';
            }
        });
        
        uploadForm.addEventListener('submit', function() {
            if (fileInput.files.length > 0) {
                // Create and show loading indicator
                const submitBtn = this.querySelector('button[type="submit"]');
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';
                
                // Create progress container
                const progressContainer = document.createElement('div');
                progressContainer.className = 'mt-3';
                progressContainer.innerHTML = `
                    <div class="progress">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 0%"></div>
                    </div>
                    <p class="text-center text-muted mt-2">Large files may take several minutes to upload</p>
                `;
                
                submitBtn.parentNode.after(progressContainer);
                
                // Fake progress for visual feedback (actual progress monitoring would require AJAX)
                const progressBar = progressContainer.querySelector('.progress-bar');
                let progress = 0;
                
                const progressInterval = setInterval(function() {
                    progress += (100 - progress) / 20;
                    if (progress > 90) {
                        progress = 90; // Cap at 90% until server confirms completion
                        clearInterval(progressInterval);
                    }
                    progressBar.style.width = progress + '%';
                }, 500);
            }
        });
    }
}); 