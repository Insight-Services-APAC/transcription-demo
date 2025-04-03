/**
 * User Modal Handler
 * Handles user-related modals in the admin section
 */
document.addEventListener('DOMContentLoaded', function() {
    // User deletion modal
    const deleteUserModal = document.getElementById('deleteUserModal');
    
    if (deleteUserModal) {
        deleteUserModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            
            // Extract info from data attributes
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            
            // Update modal content
            const usernameElement = deleteUserModal.querySelector('#deleteUsername');
            if (usernameElement) {
                usernameElement.textContent = username;
            }
            
            // Update form action
            const deleteForm = deleteUserModal.querySelector('#deleteUserForm');
            if (deleteForm) {
                const urlTemplate = deleteForm.getAttribute('data-url-template');
                if (urlTemplate && userId) {
                    deleteForm.action = urlTemplate.replace('USER_ID_PLACEHOLDER', userId);
                }
            }
        });
    }
});