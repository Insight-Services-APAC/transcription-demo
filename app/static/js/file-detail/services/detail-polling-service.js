/**
 * Detail Polling Service
 * Polls for file detail status updates
 */
export class DetailPollingService {
  constructor(fileDetailView) {
    this.fileDetailView = fileDetailView;
    this.pollInterval = null;
  }

  startPolling(fileId) {
    const apiUrl = document.body.dataset.fileApiUrl || `/api/files/${fileId}`;

    this.pollInterval = setInterval(() => {
      window
        .fetchWithCsrf(apiUrl)
        .then((response) => response.json())
        .then((data) => {
          // Update the UI with the latest progress
          this.fileDetailView.updateProgress(data);

          // If processing is complete, stop polling and reload
          if (this.fileDetailView.isProcessingComplete(data)) {
            this.stopPolling();

            // Reload page after a short delay
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          }
        })
        .catch((error) => {
          console.error("Error fetching file progress:", error);
        });
    }, 3000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}
