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
    
    // Set up CSRF token for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Set up AJAX requests to include the CSRF token
    // For fetch API calls
    window.fetchWithCsrf = function(url, options = {}) {
        // Create headers if they don't exist
        if (!options.headers) {
            options.headers = {};
        }
        
        // Add CSRF token header for non-GET requests
        if (!options.method || options.method.toUpperCase() !== 'GET') {
            options.headers['X-CSRFToken'] = csrfToken;
        }
        
        return fetch(url, options);
    };
    
    // For XMLHttpRequest
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        originalXhrOpen.apply(this, arguments);
        if (method.toUpperCase() !== 'GET') {
            this.setRequestHeader('X-CSRFToken', csrfToken);
        }
    };
});