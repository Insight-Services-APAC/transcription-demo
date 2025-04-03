/**
 * Progress Manager
 * Manages file progress state and UI updates
 */
export class ProgressManager {
  constructor() {
    this.processingFiles = [];
    this.processingFileIds = [];
  }

  findProcessingFiles() {
    const fileRows = document.querySelectorAll(".file-row");

    fileRows.forEach((row) => {
      const fileId = row.dataset.fileId;
      const status = row.querySelector(".badge");

      if (status && status.textContent.includes("Processing")) {
        this.processingFiles.push(row);
        this.processingFileIds.push(fileId);
      }
    });
  }

  getProcessingFileIds() {
    return this.processingFileIds;
  }

  updateFileRow(file) {
    // Find the row
    const row = document.querySelector(`.file-row[data-file-id="${file.id}"]`);
    if (!row) return;

    // Update progress
    const progressCell = row.querySelector(".progress-cell");
    if (!progressCell) return;

    const progressBar = progressCell.querySelector(".progress-bar");
    const progressPercent = progressCell.querySelector(".progress-percent");
    const currentStage = progressCell.querySelector(".current-stage");

    if (progressBar) progressBar.style.width = `${file.progress_percent}%`;
    if (progressPercent)
      progressPercent.textContent = `${Math.round(file.progress_percent)}%`;

    // Update current stage text
    if (currentStage) {
      if (file.current_stage === "transcribing") {
        currentStage.textContent = "Transcribing Audio";
      } else if (file.current_stage === "queued") {
        currentStage.textContent = "Queued for Processing";
      } else {
        currentStage.textContent = "Processing";
      }
    }
  }

  getFileStatusIsComplete(file) {
    return file.status !== "processing";
  }
}
