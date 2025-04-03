/**
 * File Polling Service
 * Handles polling for file processing status
 */
export class FilePollingService {
  constructor(progressManager) {
    this.progressManager = progressManager;
    this.pollIntervals = {};
    this.activePolling = {};
  }

  startPolling(fileId) {
    // Get the API URL from data attribute
    const baseUrl = document.querySelector("body").dataset.fileApiUrl;
    const apiUrl = baseUrl
      ? baseUrl.replace("FILE_ID_PLACEHOLDER", fileId)
      : `/api/files/${fileId}`;

    // Mark as active
    this.activePolling[fileId] = true;

    // Poll every 3 seconds
    this.pollIntervals[fileId] = setInterval(() => {
      if (!this.activePolling[fileId]) {
        clearInterval(this.pollIntervals[fileId]);
        return;
      }

      // Fetch file status using the API route
      fetch(apiUrl)
        .then((response) => response.json())
        .then((file) => {
          // Update the UI
          this.progressManager.updateFileRow(file);

          // If processing is complete, stop polling
          if (this.progressManager.getFileStatusIsComplete(file)) {
            this.stopPolling(fileId);

            // Refresh the page once after 1 second
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          }
        })
        .catch((error) => {
          console.error("Error fetching file status:", error);
        });
    }, 3000);
  }

  stopPolling(fileId) {
    if (this.pollIntervals[fileId]) {
      clearInterval(this.pollIntervals[fileId]);
      this.activePolling[fileId] = false;
    }
  }

  stopAllPolling() {
    Object.keys(this.pollIntervals).forEach((fileId) => {
      this.stopPolling(fileId);
    });
  }
}
