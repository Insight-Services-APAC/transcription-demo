/**
 * Transcript Player
 * Handles audio playback and transcript synchronization
 */

class TranscriptPlayer {
    constructor() {
        // Audio elements
        this.audioElement = document.getElementById('audio-element');
        this.btnPlayPause = document.getElementById('btn-play-pause');
        this.btnJumpBack = document.getElementById('btn-jump-back');
        this.btnJumpForward = document.getElementById('btn-jump-forward');
        this.btnPlaybackSpeed = document.getElementById('btn-playback-speed');
        this.progressBar = document.getElementById('audio-progress-bar');
        this.currentTimeDisplay = document.getElementById('current-time');
        this.durationDisplay = document.getElementById('duration');
        
        // Transcript elements
        this.transcriptContainer = document.getElementById('transcript-container');
        
        // State
        this.transcript = [];
        this.segments = [];
        this.currentSegment = null;
        this.speedLevels = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
        this.currentSpeedIndex = 1; // Start at 1.0x
        
        this.init();
    }
    
    /**
     * Initialize transcript player
     */
    init() {
        if (!this.transcriptContainer || !this.audioElement) return;
        
        // Fetch transcript data
        this.fetchTranscript();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Audio metadata loaded
        this.audioElement.addEventListener('loadedmetadata', this.onMetadataLoaded.bind(this));
        
        // Audio timeupdate
        this.audioElement.addEventListener('timeupdate', this.onTimeUpdate.bind(this));
        
        // Audio ended
        this.audioElement.addEventListener('ended', this.onAudioEnded.bind(this));
        
        // Play/Pause button
        this.btnPlayPause.addEventListener('click', this.togglePlayPause.bind(this));
        
        // Jump back button
        this.btnJumpBack.addEventListener('click', this.jumpBack.bind(this));
        
        // Jump forward button
        this.btnJumpForward.addEventListener('click', this.jumpForward.bind(this));
        
        // Playback speed button
        this.btnPlaybackSpeed.addEventListener('click', this.changePlaybackSpeed.bind(this));
        
        // Document click for word-level navigation
        document.addEventListener('click', this.handleDocumentClick.bind(this));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }
    
    /**
     * Fetch transcript data
     */
    fetchTranscript() {
        const transcriptUrl = document.body.dataset.transcriptUrl;
        
        if (!transcriptUrl) {
            this.showError('Transcript URL not found');
            return;
        }
        
        fetch(transcriptUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load transcript');
                }
                return response.json();
            })
            .then(data => {
                this.transcript = data;
                this.segments = data.segments || [];
                this.renderTranscript();
            })
            .catch(error => {
                this.showError(error.message);
            });
    }
    
    /**
     * Render transcript
     */
    renderTranscript() {
        if (!this.segments || this.segments.length === 0) {
            this.transcriptContainer.innerHTML = '<div class="alert alert-warning">No transcript data found.</div>';
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
                    <span class="speaker-label">Speaker ${segment.speaker !== undefined ? segment.speaker + 1 : 1}</span>
                    <span class="segment-text">${processedText}</span>
                </div>
            `;
        });
        
        this.transcriptContainer.innerHTML = html;
        
        // Add click event listeners to segments
        document.querySelectorAll('.speaker-segment').forEach(segment => {
            segment.addEventListener('click', event => {
                // Don't trigger if clicking on a word which has its own handler
                if (event.target.classList.contains('word-highlight') || 
                    event.target.closest('.word-highlight')) {
                    return;
                }
                
                const startTime = parseFloat(segment.dataset.start);
                this.seekToTime(startTime);
                this.playAudio();
            });
        });
    }
    
    /**
     * Create word-by-word highlighted text based on confidence
     */
    createHighlightedText(words, originalText) {
        // This is a simplified approach - for a production app, 
        // you'd need more sophisticated text alignment logic
        
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
    
    /**
     * Show error message in transcript container
     */
    showError(message) {
        this.transcriptContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }
    
    /**
     * Format time to MM:SS
     */
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    /**
     * Handle metadata loaded event
     */
    onMetadataLoaded() {
        this.durationDisplay.textContent = this.formatTime(this.audioElement.duration);
    }
    
    /**
     * Handle time update event
     */
    onTimeUpdate() {
        const currentTime = this.audioElement.currentTime;
        
        // Update progress bar
        const progress = (currentTime / this.audioElement.duration) * 100;
        this.progressBar.style.width = `${progress}%`;
        
        // Update time display
        this.currentTimeDisplay.textContent = this.formatTime(currentTime);
        
        // Find current segment
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
        
        // Find active word
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
        
        // Add active class to current segment and scroll if needed
        if (activeSegment) {
            activeSegment.classList.add('active-segment');
            
            // Scroll to active segment if it changed
            if (this.currentSegment !== activeSegment) {
                this.currentSegment = activeSegment;
                activeSegment.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
    
    /**
     * Handle audio ended event
     */
    onAudioEnded() {
        this.btnPlayPause.innerHTML = '<i class="fas fa-play"></i>';
    }
    
    /**
     * Toggle play/pause
     */
    togglePlayPause() {
        if (this.audioElement.paused) {
            this.playAudio();
        } else {
            this.pauseAudio();
        }
    }
    
    /**
     * Play audio
     */
    playAudio() {
        this.audioElement.play();
        this.btnPlayPause.innerHTML = '<i class="fas fa-pause"></i>';
    }
    
    /**
     * Pause audio
     */
    pauseAudio() {
        this.audioElement.pause();
        this.btnPlayPause.innerHTML = '<i class="fas fa-play"></i>';
    }
    
    /**
     * Jump back 10 seconds
     */
    jumpBack() {
        this.audioElement.currentTime = Math.max(0, this.audioElement.currentTime - 10);
    }
    
    /**
     * Jump forward 10 seconds
     */
    jumpForward() {
        this.audioElement.currentTime = Math.min(this.audioElement.duration, this.audioElement.currentTime + 10);
    }
    
    /**
     * Change playback speed
     */
    changePlaybackSpeed() {
        this.currentSpeedIndex = (this.currentSpeedIndex + 1) % this.speedLevels.length;
        const newSpeed = this.speedLevels[this.currentSpeedIndex];
        this.audioElement.playbackRate = newSpeed;
        this.btnPlaybackSpeed.textContent = `${newSpeed}x`;
    }
    
    /**
     * Seek to specific time
     */
    seekToTime(time) {
        this.audioElement.currentTime = time;
    }
    
    /**
     * Handle document click for word-level navigation
     */
    handleDocumentClick(e) {
        if (e.target.classList.contains('word-highlight') || e.target.closest('.word-highlight')) {
            const wordSpan = e.target.classList.contains('word-highlight') ? e.target : e.target.closest('.word-highlight');
            const startTime = parseFloat(wordSpan.dataset.start);
            
            this.seekToTime(startTime);
            this.playAudio();
        }
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyDown(e) {
        // Skip if inside input, textarea, or other interactive elements
        if (e.target.matches('input, textarea, button, select')) {
            return;
        }
        
        // Space - play/pause
        if (e.code === 'Space') {
            e.preventDefault();
            this.togglePlayPause();
        }
        
        // Left arrow - jump back
        if (e.code === 'ArrowLeft') {
            e.preventDefault();
            this.jumpBack();
        }
        
        // Right arrow - jump forward
        if (e.code === 'ArrowRight') {
            e.preventDefault();
            this.jumpForward();
        }
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('transcript-container')) {
        window.transcriptPlayer = new TranscriptPlayer();
    }
});