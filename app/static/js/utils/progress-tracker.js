/**
 * Progress Tracker
 * Utility for tracking and displaying progress
 */
import { formatTimeRemaining } from "./formatters.js";

export class ProgressTracker {
  constructor(options = {}) {
    this.options = {
      progressBarSelector: ".progress-bar",
      progressTextSelector: ".progress-text",
      stageTextSelector: ".stage-text",
      timeRemainingSelector: ".time-remaining",
      ...options,
    };

    this.progressBar = document.querySelector(this.options.progressBarSelector);
    this.progressText = document.querySelector(
      this.options.progressTextSelector,
    );
    this.stageText = document.querySelector(this.options.stageTextSelector);
    this.timeRemaining = document.querySelector(
      this.options.timeRemainingSelector,
    );

    this.callbacks = {};
    this.startTime = Date.now();
    this.lastUpdateTime = this.startTime;
    this.lastPercent = 0;
    this.estimatedTimeRemaining = null;
  }

  /**
   * Update the progress display
   * @param {Object} data - Progress data
   */
  updateProgress(data) {
    const now = Date.now();
    const elapsedSinceStart = (now - this.startTime) / 1000;
    const elapsedSinceUpdate = (now - this.lastUpdateTime) / 1000;

    // Update progress bar
    if (this.progressBar && data.percent !== undefined) {
      this.progressBar.style.width = `${data.percent}%`;

      // Calculate estimated time remaining if progress has changed
      if (data.percent > this.lastPercent && elapsedSinceUpdate > 0) {
        const percentChange = data.percent - this.lastPercent;
        const timePerPercent = elapsedSinceUpdate / percentChange;
        const remainingPercent = 100 - data.percent;
        this.estimatedTimeRemaining = remainingPercent * timePerPercent;

        this.lastPercent = data.percent;
        this.lastUpdateTime = now;
      }

      // Trigger callback
      this._triggerCallback("progressUpdate", data.percent);
    }

    // Update progress text
    if (this.progressText && data.percent !== undefined) {
      this.progressText.textContent = `${Math.round(data.percent)}%`;
    }

    // Update stage text
    if (this.stageText && data.stage) {
      this.stageText.textContent = data.stage;

      // Trigger callback
      this._triggerCallback("stageUpdate", data.stage);
    }

    // Update time remaining
    if (this.timeRemaining) {
      // If time remaining is provided, use it, otherwise use our calculation
      const remainingTime =
        data.timeRemaining !== undefined
          ? data.timeRemaining
          : this.estimatedTimeRemaining
            ? formatTimeRemaining(this.estimatedTimeRemaining)
            : "Calculating...";

      this.timeRemaining.textContent = remainingTime;
    }

    // Trigger overall update callback
    this._triggerCallback("update", data);

    return this;
  }

  /**
   * Show error message
   * @param {string} message - Error message
   */
  showError(message) {
    // Update status text if available
    if (this.progressText) {
      this.progressText.innerHTML = `<span class="text-danger">${message}</span>`;
    }

    // Update stage text if available
    if (this.stageText) {
      this.stageText.textContent = "Error";
    }

    // Reset time remaining
    if (this.timeRemaining) {
      this.timeRemaining.textContent = "N/A";
    }

    // Trigger error callback
    this._triggerCallback("error", message);

    return this;
  }

  /**
   * Reset progress tracker
   */
  reset() {
    this.startTime = Date.now();
    this.lastUpdateTime = this.startTime;
    this.lastPercent = 0;
    this.estimatedTimeRemaining = null;

    if (this.progressBar) {
      this.progressBar.style.width = "0%";
    }

    if (this.progressText) {
      this.progressText.textContent = "0%";
    }

    if (this.stageText) {
      this.stageText.textContent = "Starting...";
    }

    if (this.timeRemaining) {
      this.timeRemaining.textContent = "Calculating...";
    }

    this._triggerCallback("reset");

    return this;
  }

  /**
   * Register a callback function for events
   * @param {string} event - Event name to listen for
   * @param {Function} callback - Callback function
   */
  on(event, callback) {
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }

    this.callbacks[event].push(callback);
    return this;
  }

  /**
   * Trigger registered callbacks for an event
   * @param {string} event - Event name
   * @param {any} data - Data to pass to callbacks
   * @private
   */
  _triggerCallback(event, data) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach((callback) => {
        try {
          callback(data);
        } catch (e) {
          console.error(`Error in ${event} callback:`, e);
        }
      });
    }
  }
}
