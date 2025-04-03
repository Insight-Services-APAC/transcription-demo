/**
 * Transcript Renderer Component
 * Handles rendering and highlighting of transcript segments
 */
export class TranscriptRendererComponent {
  constructor() {
    this.transcriptContainer = document.getElementById("transcript-container");
    this.segments = [];
    this.activeSegment = null;
    this.isWhisperModel = false;
  }

  setData(data) {
    this.segments = data.segments || [];

    // Detect if this is likely a Whisper model output
    if (this.segments.length > 0) {
      const firstSegment = this.segments[0];
      // Whisper is a display-only model without lexical data
      // It may have different property names or missing properties
      this.isWhisperModel =
        !firstSegment.words ||
        (firstSegment.words &&
          firstSegment.words.length > 0 &&
          typeof firstSegment.words[0].confidence === "undefined");

      console.log(
        "Detected transcript type:",
        this.isWhisperModel ? "Whisper model" : "Standard model",
      );
    }
  }

  render() {
    if (!this.segments || this.segments.length === 0) {
      this.showEmpty();
      return;
    }

    let html = "";
    let speakerMap = {}; // Map to track speaker number assignments
    let speakerCount = 0;

    // First pass: assign consistent speaker numbers
    this.segments.forEach((segment) => {
      if (segment.speaker !== undefined && !speakerMap[segment.speaker]) {
        speakerCount++;
        speakerMap[segment.speaker] = speakerCount;
      }
    });

    // If no speakers were detected, default to one speaker
    if (speakerCount === 0) {
      speakerMap[0] = 1;
    }

    // Second pass: generate HTML
    this.segments.forEach((segment, index) => {
      const speakerNum =
        (segment.speaker !== undefined ? speakerMap[segment.speaker] : 1) % 6 ||
        6; // Limit to 6 colors, cycling

      // Process words with confidence
      let processedText = segment.text;

      // Handle word-level highlighting based on model type
      if (!this.isWhisperModel && segment.words && segment.words.length > 0) {
        // Standard model with confidence scores
        processedText = this.createHighlightedText(segment.words, segment.text);
      } else if (
        this.isWhisperModel &&
        segment.displayWords &&
        segment.displayWords.length > 0
      ) {
        // Whisper model with display words
        processedText = this.createWhisperHighlightedText(
          segment.displayWords,
          segment.text,
        );
      }

      // Format timestamp display in a user-friendly way
      const start = this.formatTimestamp(
        segment.start ||
          segment.offsetSeconds ||
          segment.offsetMilliseconds / 1000,
      );
      const end = this.formatTimestamp(
        segment.end ||
          segment.endSeconds ||
          (segment.offsetMilliseconds + segment.durationMilliseconds) / 1000,
      );
      const timestampDisplay = `${start} - ${end}`;

      // Get time values for segment, accounting for different property names
      const startTime =
        segment.offsetSeconds || segment.offsetMilliseconds / 1000 || 0;
      const endTime =
        segment.endSeconds ||
        (segment.offsetMilliseconds + segment.durationMilliseconds) / 1000 ||
        0;

      html += `
        <div class="speaker-segment speaker-${speakerNum}" data-index="${index}" data-start="${startTime}" data-end="${endTime}">
          <span class="timestamp">${timestampDisplay}</span>
          <span class="speaker-label">Speaker ${segment.speaker !== undefined ? speakerMap[segment.speaker] : 1}</span>
          <span class="segment-text">${processedText}</span>
        </div>
      `;
    });

    this.transcriptContainer.innerHTML = html;
  }

  createHighlightedText(words, originalText) {
    let highlightedText = "";

    words.forEach((word) => {
      let confidenceClass = "high-confidence";

      if (word.confidence < 0.5) {
        confidenceClass = "low-confidence";
      } else if (word.confidence < 0.8) {
        confidenceClass = "medium-confidence";
      }

      // Get timing info, handling different property names
      const startTime = word.offsetSeconds || word.offsetMilliseconds / 1000;
      const endTime =
        word.endSeconds ||
        (word.offsetMilliseconds + word.durationMilliseconds) / 1000;

      highlightedText += `<span class="word-highlight ${confidenceClass}" data-start="${startTime}" data-end="${endTime}">
        ${word.word || word.text}
        <span class="word-tooltip">Confidence: ${Math.round((word.confidence || 0.9) * 100)}%</span>
      </span> `;
    });

    return highlightedText;
  }

  createWhisperHighlightedText(displayWords, originalText) {
    let highlightedText = "";

    displayWords.forEach((word) => {
      // Whisper doesn't provide confidence scores, so we'll use high-confidence for all
      const confidenceClass = "high-confidence";

      // Get timing info from the displayWords format
      const startTime = word.offsetSeconds || word.offset / 1000 || 0;
      const endTime =
        startTime + (word.durationSeconds || word.duration / 1000 || 0.5);

      highlightedText += `<span class="word-highlight ${confidenceClass}" data-start="${startTime}" data-end="${endTime}">
        ${word.text || word.word || word.display}
      </span> `;
    });

    return highlightedText;
  }

  formatTimestamp(seconds) {
    if (!seconds || isNaN(seconds)) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  }

  showEmpty() {
    this.transcriptContainer.innerHTML =
      '<div class="alert alert-warning">No transcript data found.</div>';
  }

  showError(message) {
    this.transcriptContainer.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
      </div>
    `;
  }

  highlightSegmentAtTime(currentTime) {
    const segmentElements = document.querySelectorAll(".speaker-segment");
    let activeSegment = null;

    segmentElements.forEach((segment) => {
      const start = parseFloat(segment.dataset.start);
      const end = parseFloat(segment.dataset.end);

      if (currentTime >= start && currentTime <= end) {
        activeSegment = segment;
      }

      // Remove active class from all segments
      segment.classList.remove("active-segment");
    });

    // Add active class to current segment and scroll if needed
    if (activeSegment) {
      activeSegment.classList.add("active-segment");

      // Scroll to active segment if it changed
      if (this.activeSegment !== activeSegment) {
        this.activeSegment = activeSegment;
        activeSegment.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }

  highlightWordAtTime(currentTime) {
    document.querySelectorAll(".word-highlight").forEach((wordSpan) => {
      wordSpan.style.backgroundColor = "";

      const wordStart = parseFloat(wordSpan.dataset.start);
      const wordEnd = parseFloat(wordSpan.dataset.end);

      if (currentTime >= wordStart && currentTime <= wordEnd) {
        // Highlight current word
        if (wordSpan.classList.contains("low-confidence")) {
          wordSpan.style.backgroundColor = "rgba(239, 68, 68, 0.3)";
        } else if (wordSpan.classList.contains("medium-confidence")) {
          wordSpan.style.backgroundColor = "rgba(245, 158, 11, 0.3)";
        } else {
          wordSpan.style.backgroundColor = "rgba(67, 97, 238, 0.2)";
        }
      }
    });
  }
}
