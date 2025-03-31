/**
 * Main JavaScript for Transcription App
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds, but exclude the ones in modals
    setTimeout(function() {
        // Only select alerts that are not inside modals
        const alerts = document.querySelectorAll('.alert:not(.modal .alert)');
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
});