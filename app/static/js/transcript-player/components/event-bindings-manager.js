/**
 * Event Bindings Manager
 * Manages all event listeners for the transcript player
 */
export class EventBindingsManager {
  constructor(audioPlayer, transcriptRenderer) {
    this.audioPlayer = audioPlayer;
    this.transcriptRenderer = transcriptRenderer;
  }

  bindEvents() {
    // Play/Pause button
    if (this.audioPlayer.btnPlayPause) {
      this.audioPlayer.btnPlayPause.addEventListener("click", () => {
        this.audioPlayer.togglePlayPause();
      });
    }

    // Jump back button
    if (this.audioPlayer.btnJumpBack) {
      this.audioPlayer.btnJumpBack.addEventListener("click", () => {
        this.audioPlayer.jumpBack();
      });
    }

    // Jump forward button
    if (this.audioPlayer.btnJumpForward) {
      this.audioPlayer.btnJumpForward.addEventListener("click", () => {
        this.audioPlayer.jumpForward();
      });
    }

    // Playback speed button
    if (this.audioPlayer.btnPlaybackSpeed) {
      this.audioPlayer.btnPlaybackSpeed.addEventListener("click", () => {
        this.audioPlayer.changePlaybackSpeed();
      });
    }

    // Document click for word-level navigation
    document.addEventListener("click", this.handleDocumentClick.bind(this));

    // Keyboard shortcuts
    document.addEventListener("keydown", this.handleKeyDown.bind(this));

    // Segment click events
    document.querySelectorAll(".speaker-segment").forEach((segment) => {
      segment.addEventListener("click", (event) => {
        // Don't trigger if clicking on a word which has its own handler
        if (
          event.target.classList.contains("word-highlight") ||
          event.target.closest(".word-highlight")
        ) {
          return;
        }

        const startTime = parseFloat(segment.dataset.start);
        this.audioPlayer.seekToTime(startTime);
        this.audioPlayer.play();
      });
    });
  }

  handleDocumentClick(e) {
    if (
      e.target.classList.contains("word-highlight") ||
      e.target.closest(".word-highlight")
    ) {
      const wordSpan = e.target.classList.contains("word-highlight")
        ? e.target
        : e.target.closest(".word-highlight");
      const startTime = parseFloat(wordSpan.dataset.start);

      this.audioPlayer.seekToTime(startTime);
      this.audioPlayer.play();
    }
  }

  handleKeyDown(e) {
    // Skip if inside input, textarea, or other interactive elements
    if (e.target.matches("input, textarea, button, select")) {
      return;
    }

    // Space - play/pause
    if (e.code === "Space") {
      e.preventDefault();
      this.audioPlayer.togglePlayPause();
    }

    // Left arrow - jump back
    if (e.code === "ArrowLeft") {
      e.preventDefault();
      this.audioPlayer.jumpBack();
    }

    // Right arrow - jump forward
    if (e.code === "ArrowRight") {
      e.preventDefault();
      this.audioPlayer.jumpForward();
    }
  }
}
