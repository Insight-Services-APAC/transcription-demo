/**
 * Transcript Player Application
 * Main controller for the transcript player functionality
 */
import { AudioPlayerComponent } from "./components/audio-player.js";
import { TranscriptRendererComponent } from "./components/transcript-renderer.js";
import { AudioTranscriptSynchronizer } from "./components/audio-transcript-synchronizer.js";
import { EventBindingsManager } from "./components/event-bindings-manager.js";

class TranscriptPlayerApp {
  constructor() {
    this.transcriptData = null;
    this.currentSegment = null;

    // Initialize components
    this.audioPlayer = new AudioPlayerComponent();
    this.transcriptRenderer = new TranscriptRendererComponent();
    this.synchronizer = new AudioTranscriptSynchronizer(
      this.audioPlayer,
      this.transcriptRenderer,
    );
    this.eventBindings = new EventBindingsManager(
      this.audioPlayer,
      this.transcriptRenderer,
    );

    this.init();
  }

  init() {
    if (!document.getElementById("transcript-container")) return;

    // Fetch transcript data
    this.fetchTranscript()
      .then((data) => {
        // Log the structure to help with debugging
        console.log("Transcript data structure:", Object.keys(data));
        if (data.segments && data.segments.length > 0) {
          console.log("First segment structure:", Object.keys(data.segments[0]));
          
          // Check if it's likely a Whisper model output
          const hasDisplayWords = data.segments[0].displayWords && data.segments[0].displayWords.length > 0;
          const hasRegularWords = data.segments[0].words && data.segments[0].words.length > 0;
          
          if (hasDisplayWords) {
            console.log("Found displayWords array - likely Whisper model output");
            console.log("Sample display word:", data.segments[0].displayWords[0]);
          } else if (hasRegularWords) {
            console.log("Found regular words array");
            console.log("Sample word:", data.segments[0].words[0]);
          } else {
            console.log("No word-level data found. Basic transcript will be displayed without word-level highlighting.");
          }
        }

        this.transcriptData = data;
        this.transcriptRenderer.setData(data);
        this.transcriptRenderer.render();
        this.synchronizer.setData(data);
        this.eventBindings.bindEvents();
      })
      .catch((error) => {
        console.error("Error loading transcript:", error);
        this.transcriptRenderer.showError(
          `Failed to load transcript: ${error.message}. This may happen if the transcript format is incompatible with the player.`
        );
      });
  }

  fetchTranscript() {
    const transcriptUrl = document.body.dataset.transcriptUrl;

    if (!transcriptUrl) {
      return Promise.reject(new Error("Transcript URL not found"));
    }

    return window.fetchWithCsrf(transcriptUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load transcript (HTTP ${response.status})`);
        }
        return response.json();
      })
      .then(data => {
        // Process and normalize the transcript data if needed
        if (!data.segments && data.results && data.results.length > 0) {
          // Handle alternative format - some APIs return results instead of segments
          data.segments = data.results;
        }
        
        if (data.segments && data.segments.length > 0) {
          // Ensure each segment has at least basic required properties
          data.segments = data.segments.map(segment => {
            // Normalize timing properties if needed
            if (!segment.offsetMilliseconds && segment.offset !== undefined) {
              segment.offsetMilliseconds = segment.offset;
            }
            
            if (!segment.durationMilliseconds && segment.duration !== undefined) {
              segment.durationMilliseconds = segment.duration;
            }
            
            return segment;
          });
        }
        
        return data;
      });
  }
}

// Initialize on document ready
document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("transcript-container")) {
    window.transcriptPlayerApp = new TranscriptPlayerApp();
  }
});