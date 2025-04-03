/**
 * File Detail Application
 * Main controller for file detail page
 */
import { FileDetailView } from "./components/file-detail-view.js";
import { DetailPollingService } from "./services/detail-polling-service.js";

class FileDetailApp {
  constructor() {
    this.fileDetailView = new FileDetailView();
    this.filePollingService = new DetailPollingService(this.fileDetailView);

    this.init();
  }

  init() {
    // Get file ID
    const fileId = this.fileDetailView.getFileId();
    if (!fileId) return;

    // Check if file is in processing state and start polling if it is
    if (this.fileDetailView.isFileProcessing()) {
      this.filePollingService.startPolling(fileId);
    }
  }
}

// Initialize the app
document.addEventListener("DOMContentLoaded", function () {
  window.fileDetailApp = new FileDetailApp();
});

// Clean up on page unload
window.addEventListener("beforeunload", function () {
  if (window.fileDetailApp && window.fileDetailApp.filePollingService) {
    window.fileDetailApp.filePollingService.stopPolling();
  }
});
