/**
 * Audio Transcript Synchronizer
 * Synchronizes audio playback with transcript highlighting
 */
export class AudioTranscriptSynchronizer {
  constructor(audioPlayer, transcriptRenderer) {
    this.audioPlayer = audioPlayer;
    this.transcriptRenderer = transcriptRenderer;
    this.transcriptData = null;
  }

  setData(data) {
    this.transcriptData = data;

    // Register time update callback
    this.audioPlayer.registerTimeUpdateCallback(this.onTimeUpdate.bind(this));
  }

  onTimeUpdate(currentTime) {
    if (!this.transcriptData || !this.transcriptRenderer) return;
    
    try {
      // Highlight the current segment
      this.transcriptRenderer.highlightSegmentAtTime(currentTime);
      
      // Highlight the current word if word-level timestamps are available
      // This will work with both standard and Whisper transcripts
      this.transcriptRenderer.highlightWordAtTime(currentTime);
    } catch (error) {
      console.error("Error during transcript synchronization:", error);
    }
  }
}