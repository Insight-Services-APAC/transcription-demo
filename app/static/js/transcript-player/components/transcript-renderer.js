/**
 * Transcript Renderer Component
 * Handles rendering and highlighting of transcript segments
 */
export class TranscriptRendererComponent {
    constructor() {
        this.transcriptContainer = document.getElementById('transcript-container');
        this.segments = [];
        this.activeSegment = null;
    }
    
    setData(data) {
        this.segments = data.segments || [];
    }
    
    render() {
        if (!this.segments || this.segments.length === 0) {
            this.showEmpty();
            return;
        }
        
        let html = '';
        let speakerMap = {}; // Map to track speaker number assignments
        let speakerCount = 0;
        
        // First pass: assign consistent speaker numbers
        this.segments.forEach(segment => {
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
            const speakerNum = (segment.speaker !== undefined ? speakerMap[segment.speaker] : 1) % 6 || 6; // Limit to 6 colors, cycling
            
            // Process words with confidence
            let processedText = segment.text;
            
            // If segment has words with confidence, create highlighted spans
            if (segment.words && segment.words.length > 0) {
                processedText = this.createHighlightedText(segment.words, segment.text);
            }
            
            html += `
                <div class="speaker-segment speaker-${speakerNum}" data-index="${index}" data-start="${segment.offsetMilliseconds / 1000}" data-end="${(segment.offsetMilliseconds + segment.durationMilliseconds) / 1000}">
                    <span class="timestamp">${segment.start} - ${segment.end}</span>
                    <span class="speaker-label">Speaker ${segment.speaker !== undefined ? speakerMap[segment.speaker] : 1}</span>
                    <span class="segment-text">${processedText}</span>
                </div>
            `;
        });
        
        this.transcriptContainer.innerHTML = html;
    }
    
    createHighlightedText(words, originalText) {
        let highlightedText = '';
        
        words.forEach(word => {
            let confidenceClass = 'high-confidence';
            
            if (word.confidence < 0.5) {
                confidenceClass = 'low-confidence';
            } else if (word.confidence < 0.8) {
                confidenceClass = 'medium-confidence';
            }
            
            highlightedText += `<span class="word-highlight ${confidenceClass}" data-start="${word.offsetMilliseconds / 1000}" data-end="${(word.offsetMilliseconds + word.durationMilliseconds) / 1000}">
                ${word.word}
                <span class="word-tooltip">Confidence: ${Math.round(word.confidence * 100)}%</span>
            </span> `;
        });
        
        return highlightedText;
    }
    
    showEmpty() {
        this.transcriptContainer.innerHTML = '<div class="alert alert-warning">No transcript data found.</div>';
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
        const segmentElements = document.querySelectorAll('.speaker-segment');
        let activeSegment = null;
        
        segmentElements.forEach(segment => {
            const start = parseFloat(segment.dataset.start);
            const end = parseFloat(segment.dataset.end);
            
            if (currentTime >= start && currentTime <= end) {
                activeSegment = segment;
            }
            
            // Remove active class from all segments
            segment.classList.remove('active-segment');
        });
        
        // Add active class to current segment and scroll if needed
        if (activeSegment) {
            activeSegment.classList.add('active-segment');
            
            // Scroll to active segment if it changed
            if (this.activeSegment !== activeSegment) {
                this.activeSegment = activeSegment;
                activeSegment.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
    
    highlightWordAtTime(currentTime) {
        document.querySelectorAll('.word-highlight').forEach(wordSpan => {
            wordSpan.style.backgroundColor = '';
            
            const wordStart = parseFloat(wordSpan.dataset.start);
            const wordEnd = parseFloat(wordSpan.dataset.end);
            
            if (currentTime >= wordStart && currentTime <= wordEnd) {
                // Highlight current word
                if (wordSpan.classList.contains('low-confidence')) {
                    wordSpan.style.backgroundColor = 'rgba(239, 68, 68, 0.3)';
                } else if (wordSpan.classList.contains('medium-confidence')) {
                    wordSpan.style.backgroundColor = 'rgba(245, 158, 11, 0.3)';  
                } else {
                    wordSpan.style.backgroundColor = 'rgba(67, 97, 238, 0.2)';
                }
            }
        });
    }
}
