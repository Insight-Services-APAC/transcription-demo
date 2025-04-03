/**
 * File Detail View
 * Handles file detail page UI updates
 */
export class FileDetailView {
  constructor() {
    this.fileRow = document.querySelector(".file-row");
    this.fileIdElement = document.querySelector("[data-file-id]");
    this.progressBar = document.querySelector(".progress-bar");
    this.progressPercent = document.querySelector(".progress-percent");
    this.currentStage = document.querySelector(".current-stage");
  }

  getFileId() {
    if (this.fileRow && this.fileRow.dataset.fileId) {
      return this.fileRow.dataset.fileId;
    }

    if (this.fileIdElement && this.fileIdElement.dataset.fileId) {
      return this.fileIdElement.dataset.fileId;
    }

    return null;
  }

  isFileProcessing() {
    const status = document.querySelector(".badge");
    return status && status.textContent.includes("Processing");
  }

  updateProgress(file) {
    if (this.progressBar) {
      this.progressBar.style.width = `${file.progress_percent}%`;
    }

    if (this.progressPercent) {
      this.progressPercent.textContent = `${Math.round(file.progress_percent)}%`;
    }

    if (this.currentStage) {
      let stageText = "Processing";

      switch (file.current_stage) {
        case "extract_audio":
          stageText = "Extracting Audio";
          break;
        case "chunk_audio":
          stageText = "Chunking Audio";
          break;
        case "transcribe_chunks":
          stageText = `Transcribing (${file.chunks_processed || 0}/${file.chunk_count || "?"})`;
          break;
        case "diarization":
          stageText = "Identifying Speakers";
          break;
        case "stitch_transcript":
          stageText = "Generating Transcript";
          break;
        case "queued":
          stageText = "Queued for Processing";
          break;
        case "transcribing":
          stageText = "Transcribing Audio";
          break;
      }

      this.currentStage.textContent = stageText;
    }
  }

  isProcessingComplete(file) {
    return file.status !== "processing";
  }
}
