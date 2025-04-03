/**
 * Delete Modal Handler
 * Handles deletion confirmation modals throughout the application
 */

class DeleteModalHandler {
  constructor() {
    this.deleteModal = document.getElementById("deleteModal");
    this.init();
  }

  /**
   * Initialize delete modal handler
   */
  init() {
    if (!this.deleteModal) return;

    // Set up event listener for modal showing
    this.deleteModal.addEventListener(
      "show.bs.modal",
      this.handleModalShow.bind(this),
    );
  }

  /**
   * Handle modal show event
   * Updates modal content with file information from trigger button
   */
  handleModalShow(event) {
    // Button that triggered the modal
    const button = event.relatedTarget;

    // Check if we need to extract data from button attributes
    if (
      button.hasAttribute("data-file-id") &&
      button.hasAttribute("data-file-name")
    ) {
      // Extract info from data attributes
      const fileId = button.getAttribute("data-file-id");
      const fileName = button.getAttribute("data-file-name");

      // Update modal content
      const fileToDelete = this.deleteModal.querySelector("#fileToDelete");
      if (fileToDelete) {
        fileToDelete.textContent = fileName;
      }

      // Update form action
      const deleteForm = this.deleteModal.querySelector("#deleteForm");
      if (deleteForm) {
        // Set the form action to the correct delete URL
        deleteForm.action = `/delete/${fileId}`;
      }
    }

    // Ensure modal alerts don't get auto-dismissed
    const modalAlerts = this.deleteModal.querySelectorAll(".alert");
    modalAlerts.forEach((alert) => {
      alert.classList.add("modal-alert");
    });
  }
}

// Initialize on document ready
document.addEventListener("DOMContentLoaded", function () {
  new DeleteModalHandler();
});
