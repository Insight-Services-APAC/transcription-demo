/**
 * Transcript Player Application
 * Main controller for the transcript player functionality
 */
import { AudioPlayerComponent } from './components/audio-player.js';
import { TranscriptRendererComponent } from './components/transcript-renderer.js';
import { AudioTranscriptSynchronizer } from './components/audio-transcript-synchronizer.js';
import { EventBindingsManager } from './components/event-bindings-manager.js';

class TranscriptPlayerApp {
    constructor() {
        this.transcriptData = null;
        this.currentSegment = null;
        
        // Initialize components
        this.audioPlayer = new AudioPlayerComponent();
        this.transcriptRenderer = new TranscriptRendererComponent();
        this.synchronizer = new AudioTranscriptSynchronizer(this.audioPlayer, this.transcriptRenderer);
        this.eventBindings = new EventBindingsManager(this.audioPlayer, this.transcriptRenderer);
        
        this.init();
    }
    
    init() {
        if (!document.getElementById('transcript-container')) return;
        
        // Fetch transcript data
        this.fetchTranscript()
            .then(data => {
                this.transcriptData = data;
                this.transcriptRenderer.setData(data);
                this.transcriptRenderer.render();
                this.synchronizer.setData(data);
                this.eventBindings.bindEvents();
            })
            .catch(error => {
                this.transcriptRenderer.showError(error.message);
            });
    }
    
    fetchTranscript() {
        const transcriptUrl = document.body.dataset.transcriptUrl;
        
        if (!transcriptUrl) {
            return Promise.reject(new Error('Transcript URL not found'));
        }
        
        return window.fetchWithCsrf(transcriptUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load transcript');
                }
                return response.json();
            });
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('transcript-container')) {
        window.transcriptPlayerApp = new TranscriptPlayerApp();
    }
});