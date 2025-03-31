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
        this.transcriptRenderer.highlightSegmentAtTime(currentTime);
        this.transcriptRenderer.highlightWordAtTime(currentTime);
    }
}
