/**
 * Pomodoro Timer JavaScript
 * This script implements a Pomodoro timer with task integration.
 */

class PomodoroTimer {
    constructor() {
        // Timer state
        this.isRunning = false;
        this.isBreak = false;
        this.minutes = 25;
        this.seconds = 0;
        this.originalMinutes = 25;
        this.breakMinutes = 5;
        this.longBreakMinutes = 15;
        this.interval = null;
        this.completedSessions = 0;
        this.totalSessions = 4;
        this.currentTaskId = null;
        
        // Element references - will be initialized when DOM loads
        this.timerDisplay = null;
        this.startBtn = null;
        this.pauseBtn = null;
        this.resetBtn = null;
        this.progressBar = null;
        this.sessionDots = null;
        
        // Bind methods to prevent 'this' context issues
        this.startTimer = this.startTimer.bind(this);
        this.pauseTimer = this.pauseTimer.bind(this);
        this.resetTimer = this.resetTimer.bind(this);
        this.updateDisplay = this.updateDisplay.bind(this);
        this.updateProgress = this.updateProgress.bind(this);
        this.handleTimerComplete = this.handleTimerComplete.bind(this);
        this.toggleBreak = this.toggleBreak.bind(this);
        this.updateSettings = this.updateSettings.bind(this);
        this.selectTask = this.selectTask.bind(this);
    }
    
    /**
     * Initialize the timer and attach event listeners
     */
    initialize() {
        // Get element references
        this.timerDisplay = document.getElementById('timer-display');
        this.startBtn = document.getElementById('start-timer');
        this.pauseBtn = document.getElementById('pause-timer');
        this.resetBtn = document.getElementById('reset-timer');
        this.progressBar = document.getElementById('timer-progress-bar');
        this.sessionDots = document.querySelectorAll('.session-dot');
        
        // Settings inputs and displays
        this.pomodoroInput = document.getElementById('pomodoro-minutes');
        this.shortBreakDisplay = document.getElementById('short-break-display');
        this.longBreakDisplay = document.getElementById('long-break-display');
        this.sessionsDisplay = document.getElementById('sessions-display');
        
        // Task integration
        this.taskSelect = document.getElementById('task-select');
        
        // Calculate and update display values based on focus time
        this.calculateTimerValues();
        
        // Initialize display
        this.updateDisplay();
        
        // Attach event listeners
        if (this.startBtn) {
            this.startBtn.addEventListener('click', this.startTimer);
        }
        
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', this.pauseTimer);
        }
        
        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', this.resetTimer);
        }
        
        // Settings listeners
        if (this.pomodoroInput) {
            this.pomodoroInput.addEventListener('change', this.updateSettings);
            this.pomodoroInput.addEventListener('input', this.updateSettings);
        }
        
        // Task selection listener
        if (this.taskSelect) {
            this.taskSelect.addEventListener('change', this.selectTask);
        }
        
        // Setup notification permission
        this.setupNotifications();
    }
    
    /**
     * Start the timer
     */
    startTimer() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        
        // Play start sound with our improved sound system
        if (window.PomodoroSounds) {
            window.PomodoroSounds.playStart();
        } else {
            console.warn('PomodoroSounds not loaded');
        }
        
        // Update UI
        this.timerDisplay.classList.add('running');
        this.timerDisplay.classList.remove('paused');
        
        // Start the interval
        this.interval = setInterval(() => {
            // Decrement time
            if (this.seconds === 0) {
                if (this.minutes === 0) {
                    this.handleTimerComplete();
                    return;
                }
                this.minutes--;
                this.seconds = 59;
            } else {
                this.seconds--;
            }
            
            // Update display and progress
            this.updateDisplay();
            this.updateProgress();
        }, 1000);
        
        // Update task status if a task is selected
        if (this.currentTaskId) {
            this.updateTaskStatus(this.currentTaskId, 'in_progress');
        }
        
        // Trigger event
        this.dispatchTimerEvent('start');
    }
    
    /**
     * Pause the timer
     */
    pauseTimer() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        
        // Play pause sound with our improved sound system
        if (window.PomodoroSounds) {
            window.PomodoroSounds.playPause();
        } else {
            console.warn('PomodoroSounds not loaded');
        }
        
        // Update UI
        this.timerDisplay.classList.remove('running');
        this.timerDisplay.classList.add('paused');
        
        // Clear interval
        clearInterval(this.interval);
        
        // Trigger event
        this.dispatchTimerEvent('pause');
    }
    
    /**
     * Reset the timer
     */
    resetTimer() {
        // Clear interval
        clearInterval(this.interval);
        
        // Make sure values are calculated properly before resetting
        this.calculateTimerValues();
        
        // Reset state
        this.isRunning = false;
        this.minutes = this.isBreak ? 
            (this.completedSessions % this.totalSessions === 0 ? this.longBreakMinutes : this.breakMinutes) : 
            this.originalMinutes;
        this.seconds = 0;
        
        // Update UI
        this.timerDisplay.classList.remove('running', 'paused');
        this.updateDisplay();
        this.updateProgress();
        
        // Trigger event
        this.dispatchTimerEvent('reset');
    }
    
    /**
     * Update the timer display
     */
    updateDisplay() {
        if (!this.timerDisplay) return;
        
        // Format time
        const formattedMinutes = String(this.minutes).padStart(2, '0');
        const formattedSeconds = String(this.seconds).padStart(2, '0');
        
        // Update display
        this.timerDisplay.textContent = `${formattedMinutes}:${formattedSeconds}`;
        
        // Update page title
        document.title = `${formattedMinutes}:${formattedSeconds} - ${this.isBreak ? 'Break' : 'Focus'} | Timetable`;
    }
    
    /**
     * Update the progress bar
     */
    updateProgress() {
        if (!this.progressBar) return;
        
        const totalTime = (this.isBreak ? 
            (this.completedSessions % this.totalSessions === 0 ? this.longBreakMinutes : this.breakMinutes) : 
            this.originalMinutes) * 60;
        const remainingTime = (this.minutes * 60) + this.seconds;
        const progress = ((totalTime - remainingTime) / totalTime) * 100;
        
        // Set the width of the progress bar to match the progress percentage
        this.progressBar.style.width = `${progress}%`;
        
        // Change color based on current state
        const color = this.isBreak 
            ? 'var(--info-color)' 
            : (!this.isRunning ? 'var(--warning-color)' : 'var(--accent-color)');
            
        this.progressBar.style.backgroundColor = color;
    }
    
    /**
     * Handle timer completion
     */
    handleTimerComplete() {
        // Clear interval
        clearInterval(this.interval);
        
        // Play complete sound with our improved sound system
        if (window.PomodoroSounds) {
            window.PomodoroSounds.playComplete();
        } else {
            console.warn('PomodoroSounds not loaded');
        }
        
        // Show notification
        this.showNotification(
            this.isBreak ? 'Break Complete!' : 'Session Complete!',
            this.isBreak ? 'Time to focus again.' : 'Time for a break!'
        );
        
        // Toggle between focus and break
        this.toggleBreak();
        
        // Update session counter if focus period ended
        if (!this.isBreak) {
            this.completedSessions++;
            this.updateSessionDots();
            
            // Update task completion if all sessions are done
            if (this.completedSessions === this.totalSessions && this.currentTaskId) {
                this.updateTaskStatus(this.currentTaskId, 'completed');
            }
        }
        
        // Reset timer for next session
        this.resetTimer();
        
        // Trigger event
        this.dispatchTimerEvent('complete');
    }
    
    /**
     * Toggle between focus and break
     */
    toggleBreak() {
        this.isBreak = !this.isBreak;
        
        // Update display
        if (this.timerDisplay) {
            if (this.isBreak) {
                this.timerDisplay.classList.add('break');
            } else {
                this.timerDisplay.classList.remove('break');
            }
        }
        
        // Reset time based on break status
        if (this.isBreak) {
            // Determine if it should be a long break
            if (this.completedSessions % this.totalSessions === 0 && this.completedSessions > 0) {
                this.minutes = this.longBreakMinutes;
            } else {
                this.minutes = this.breakMinutes;
            }
        } else {
            this.minutes = this.originalMinutes;
        }
        this.seconds = 0;
        
        // Update display
        this.updateDisplay();
    }
    
    /**
     * Update session dots
     */
    updateSessionDots() {
        if (!this.sessionDots) return;
        
        // Update session dots
        this.sessionDots.forEach((dot, index) => {
            if (index < this.completedSessions) {
                dot.classList.add('completed');
            } else {
                dot.classList.remove('completed');
            }
        });
    }
    
    /**
     * Calculate timer values based on focus time
     */
    calculateTimerValues() {
        console.log('Calculating timer values based on focus time:', this.originalMinutes);
        
        // Using the 5:1:3 ratio (focus:short break:long break)
        // Short break is 1/5 of focus time, minimum 1 minute
        this.breakMinutes = Math.max(1, Math.round(this.originalMinutes / 5));
        
        // Long break is 3/5 of focus time, minimum 3 minutes
        this.longBreakMinutes = Math.max(3, Math.round((this.originalMinutes / 5) * 3));
        
        // Sessions are calculated based on focus time: 1 session per 25 minutes, min 2, max 6
        this.totalSessions = Math.max(2, Math.min(6, Math.round(this.originalMinutes / 25) + 2));
        
        console.log('Calculated values - Short break:', this.breakMinutes, 'Long break:', this.longBreakMinutes, 'Sessions:', this.totalSessions);
        
        // Get references to display elements if not already available
        if (!this.shortBreakDisplay) {
            this.shortBreakDisplay = document.getElementById('short-break-display');
        }
        
        if (!this.longBreakDisplay) {
            this.longBreakDisplay = document.getElementById('long-break-display');
        }
        
        if (!this.sessionsDisplay) {
            this.sessionsDisplay = document.getElementById('sessions-display');
        }
        
        // Update display elements
        if (this.shortBreakDisplay) {
            this.shortBreakDisplay.textContent = `${this.breakMinutes} min`;
            console.log('Updated short break display to:', this.breakMinutes);
        } else {
            console.warn('Short break display element not found');
        }
        
        if (this.longBreakDisplay) {
            this.longBreakDisplay.textContent = `${this.longBreakMinutes} min`;
            console.log('Updated long break display to:', this.longBreakMinutes);
        } else {
            console.warn('Long break display element not found');
        }
        
        if (this.sessionsDisplay) {
            this.sessionsDisplay.textContent = this.totalSessions;
            console.log('Updated sessions display to:', this.totalSessions);
        } else {
            console.warn('Sessions display element not found');
        }
    }
    
    /**
     * Update timer settings
     */
    updateSettings() {
        // Get values from inputs (with validation)
        if (this.pomodoroInput) {
            this.originalMinutes = Math.max(1, parseInt(this.pomodoroInput.value) || 25);
            
            // Update minutes immediately if not in a break
            if (!this.isBreak) {
                this.minutes = this.originalMinutes;
            }
        }
        
        // Calculate other values based on focus time
        this.calculateTimerValues();
        
        // Update session dots
        this.createSessionDots();
        
        // Reset timer with new settings
        this.resetTimer();
        
        // Save settings to localStorage
        this.saveSettings();
    }
    
    /**
     * Create session dots based on total sessions
     */
    createSessionDots() {
        const container = document.querySelector('.session-counter');
        if (!container) return;
        
        // Clear existing dots
        container.innerHTML = '';
        
        // Create new dots
        for (let i = 0; i < this.totalSessions; i++) {
            const dot = document.createElement('div');
            dot.className = 'session-dot';
            if (i < this.completedSessions) {
                dot.classList.add('completed');
            }
            container.appendChild(dot);
        }
        
        // Update session dots reference
        this.sessionDots = document.querySelectorAll('.session-dot');
    }
    
    /**
     * Save settings to localStorage
     */
    saveSettings() {
        const settings = {
            pomodoroMinutes: this.originalMinutes,
            shortBreakMinutes: this.breakMinutes,
            longBreakMinutes: this.longBreakMinutes,
            totalSessions: this.totalSessions
        };
        
        localStorage.setItem('pomodoroSettings', JSON.stringify(settings));
    }
    
    /**
     * Load settings from localStorage
     */
    loadSettings() {
        const savedSettings = localStorage.getItem('pomodoroSettings');
        if (!savedSettings) return;
        
        try {
            const settings = JSON.parse(savedSettings);
            
            // Update instance variables
            this.originalMinutes = settings.pomodoroMinutes || 25;
            
            // Update input field
            if (this.pomodoroInput) this.pomodoroInput.value = this.originalMinutes;
            
            // Calculate other values based on focus time
            this.calculateTimerValues();
            
            // Reset timer with loaded settings
            this.resetTimer();
            
            // Update session dots
            this.createSessionDots();
        } catch (error) {
            console.error('Error loading Pomodoro settings:', error);
        }
    }
    
    /**
     * Select a task to associate with the timer
     */
    selectTask() {
        if (!this.taskSelect) return;
        
        const selectedOption = this.taskSelect.options[this.taskSelect.selectedIndex];
        this.currentTaskId = selectedOption.value;
        
        // Save to localStorage
        localStorage.setItem('currentPomodoroTask', this.currentTaskId);
        
        // Trigger event
        this.dispatchTimerEvent('taskSelected', { taskId: this.currentTaskId });
    }
    
    /**
     * Update task status in the backend
     * @param {string} taskId - The ID of the task to update
     * @param {string} status - The new status (in_progress or completed)
     */
    updateTaskStatus(taskId, status) {
        // Skip for empty task ID
        if (!taskId || taskId === 'none') return;
        
        // API endpoint based on status
        let endpoint = '';
        if (status === 'in_progress') {
            endpoint = `/api/tasks/start/${taskId}`;
        } else if (status === 'completed') {
            endpoint = `/api/tasks/complete/${taskId}`;
        } else {
            return;
        }
        
        // Send request to update task status
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const message = status === 'completed' 
                    ? 'Task completed successfully!' 
                    : 'Task started';
                
                showToast(message, 'success');
                
                // If task completed, reset current task
                if (status === 'completed') {
                    this.currentTaskId = null;
                    localStorage.removeItem('currentPomodoroTask');
                    
                    // Update select if it exists
                    if (this.taskSelect) {
                        this.taskSelect.value = 'none';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error updating task status:', error);
            showToast('Error updating task', 'error');
        });
    }
    
    /**
     * Setup browser notifications
     */
    setupNotifications() {
        // Check if browser supports notifications
        if (!('Notification' in window)) {
            console.log('This browser does not support notifications');
            return;
        }
        
        // Request permission if not already granted
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
    
    /**
     * Show a browser notification
     * @param {string} title - Notification title
     * @param {string} body - Notification body text
     */
    showNotification(title, body) {
        // Check if browser supports notifications and permission is granted
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            // Fallback to toast notification
            this.showToast(title, body);
            return;
        }
        
        // Create and show the notification
        const notification = new Notification(title, {
            body: body,
            icon: '/static/images/pomodoro-icon.png'
        });
        
        // Auto-close after 5 seconds
        setTimeout(() => {
            notification.close();
        }, 5000);
    }
    
    /**
     * Show a toast notification
     * @param {string} title - Toast title
     * @param {string} message - Toast message
     */
    showToast(title, message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'timer-notification';
        toast.innerHTML = `
            <div class="timer-notification-title">${title}</div>
            <div class="timer-notification-message">${message}</div>
        `;
        
        // Add to DOM
        document.body.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    }
    
    /**
     * Dispatch a custom event for the timer
     * @param {string} action - The action that occurred
     * @param {Object} data - Additional data to include
     */
    dispatchTimerEvent(action, data = {}) {
        const event = new CustomEvent('pomodoroTimer', {
            detail: {
                action,
                isBreak: this.isBreak,
                completedSessions: this.completedSessions,
                totalSessions: this.totalSessions,
                currentTaskId: this.currentTaskId,
                ...data
            }
        });
        
        document.dispatchEvent(event);
    }
}

// Initialize timer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        const pomodoroTimer = new PomodoroTimer();
        pomodoroTimer.initialize();
        
        // Force a refresh of the UI
        setTimeout(() => {
            // Load saved settings
            pomodoroTimer.loadSettings();
            
            // Make sure values are calculated and displayed
            pomodoroTimer.calculateTimerValues();
            
            // Show a debug message in console
            console.log('Pomodoro timer initialized and refreshed');
            
            // Try direct DOM updates as a fallback
            try {
                // Get the values
                const shortBreak = Math.max(1, Math.round(pomodoroTimer.originalMinutes / 5));
                const longBreak = Math.max(3, Math.round((pomodoroTimer.originalMinutes / 5) * 3));
                const sessions = Math.max(2, Math.min(6, Math.round(pomodoroTimer.originalMinutes / 25) + 2));
                
                // Update DOM directly
                const shortBreakElement = document.getElementById('short-break-display');
                if (shortBreakElement) shortBreakElement.textContent = `${shortBreak} min`;
                
                const longBreakElement = document.getElementById('long-break-display');
                if (longBreakElement) longBreakElement.textContent = `${longBreak} min`;
                
                const sessionsElement = document.getElementById('sessions-display');
                if (sessionsElement) sessionsElement.textContent = sessions;
                
                console.log('Direct DOM update completed');
            } catch (err) {
                console.error('Error during direct DOM update:', err);
            }
        }, 500);
        
        // Load saved task
        const savedTaskId = localStorage.getItem('currentPomodoroTask');
        if (savedTaskId && pomodoroTimer.taskSelect) {
            pomodoroTimer.taskSelect.value = savedTaskId;
            pomodoroTimer.currentTaskId = savedTaskId;
        }
        
        // Make timer available globally for debugging
        window.pomodoroTimer = pomodoroTimer;
    } catch (err) {
        console.error('Failed to initialize pomodoro timer:', err);
    }
});
