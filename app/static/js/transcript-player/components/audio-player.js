/**
 * Audio Player Component
 * Handles audio playback controls and state
 */
export class AudioPlayerComponent {
    constructor() {
        // DOM elements
        this.audioElement = document.getElementById('audio-element');
        this.btnPlayPause = document.getElementById('btn-play-pause');
        this.btnJumpBack = document.getElementById('btn-jump-back');
        this.btnJumpForward = document.getElementById('btn-jump-forward');
        this.btnPlaybackSpeed = document.getElementById('btn-playback-speed');
        this.progressBar = document.getElementById('audio-progress-bar');
        this.currentTimeDisplay = document.getElementById('current-time');
        this.durationDisplay = document.getElementById('duration');
        
        // State
        this.speedLevels = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
        this.currentSpeedIndex = 1; // Start at 1.0x
        
        this.timeUpdateCallbacks = [];
        
        this.init();
    }
    
    init() {
        if (!this.audioElement) return;
        
        // Set up audio event listeners
        this.audioElement.addEventListener('loadedmetadata', this.onMetadataLoaded.bind(this));
        this.audioElement.addEventListener('timeupdate', this.onTimeUpdate.bind(this));
        this.audioElement.addEventListener('ended', this.onAudioEnded.bind(this));
    }
    
    onMetadataLoaded() {
        this.durationDisplay.textContent = this.formatTime(this.audioElement.duration);
    }
    
    onTimeUpdate() {
        const currentTime = this.audioElement.currentTime;
        
        // Update progress bar
        const progress = (currentTime / this.audioElement.duration) * 100;
        this.progressBar.style.width = `${progress}%`;
        
        // Update time display
        this.currentTimeDisplay.textContent = this.formatTime(currentTime);
        
        // Call registered callbacks
        this.timeUpdateCallbacks.forEach(callback => callback(currentTime));
    }
    
    onAudioEnded() {
        this.btnPlayPause.innerHTML = '<i class="fas fa-play"></i>';
    }
    
    registerTimeUpdateCallback(callback) {
        this.timeUpdateCallbacks.push(callback);
    }
    
    togglePlayPause() {
        if (this.audioElement.paused) {
            this.play();
        } else {
            this.pause();
        }
    }
    
    play() {
        this.audioElement.play();
        this.btnPlayPause.innerHTML = '<i class="fas fa-pause"></i>';
    }
    
    pause() {
        this.audioElement.pause();
        this.btnPlayPause.innerHTML = '<i class="fas fa-play"></i>';
    }
    
    jumpBack() {
        this.audioElement.currentTime = Math.max(0, this.audioElement.currentTime - 10);
    }
    
    jumpForward() {
        this.audioElement.currentTime = Math.min(this.audioElement.duration, this.audioElement.currentTime + 10);
    }
    
    changePlaybackSpeed() {
        this.currentSpeedIndex = (this.currentSpeedIndex + 1) % this.speedLevels.length;
        const newSpeed = this.speedLevels[this.currentSpeedIndex];
        this.audioElement.playbackRate = newSpeed;
        this.btnPlaybackSpeed.textContent = `${newSpeed}x`;
    }
    
    seekToTime(time) {
        this.audioElement.currentTime = time;
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}
