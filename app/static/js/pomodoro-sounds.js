// Pomodoro Timer Sound Effects using Web Audio API

// Audio Context
let audioContext;

// Initialize audio context when needed (needs user interaction first)
function initAudioContext() {
  if (!audioContext) {
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    } catch (error) {
      console.error('Web Audio API not supported:', error);
    }
  }
  return audioContext;
}

// Create a beep sound with the specified parameters
function createBeep(options = {}) {
  const ctx = initAudioContext();
  if (!ctx) return;
  
  const defaults = {
    frequency: 660,
    type: 'sine',
    duration: 200,
    volume: 0.5,
    fadeOut: true
  };
  
  const settings = {...defaults, ...options};
  
  try {
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();
    
    oscillator.type = settings.type;
    oscillator.frequency.value = settings.frequency;
    gainNode.gain.value = settings.volume;
    
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    
    // Start the sound
    oscillator.start();
    
    // Handle fade out
    if (settings.fadeOut) {
      gainNode.gain.exponentialRampToValueAtTime(
        0.001, ctx.currentTime + settings.duration / 1000
      );
    }
    
    // Stop the sound after duration
    setTimeout(() => {
      oscillator.stop();
    }, settings.duration);
    
    return true;
  } catch (error) {
    console.error('Failed to create sound:', error);
    return false;
  }
}

// Sound patterns for different timer events
const soundPatterns = {
  // Start sound: Cheerful ascending arpeggio
  start: [
    { frequency: 523.25, duration: 80, volume: 0.4, type: 'sine' },   // C5
    { frequency: 659.25, duration: 80, volume: 0.4, type: 'sine', delay: 100 },   // E5
    { frequency: 783.99, duration: 120, volume: 0.5, type: 'sine', delay: 200 }   // G5
  ],
  
  // Pause sound: Descending two-tone with triangle wave
  pause: [
    { frequency: 659.25, duration: 100, volume: 0.4, type: 'triangle' },  // E5
    { frequency: 440.00, duration: 200, volume: 0.5, type: 'triangle', delay: 150 }   // A4
  ],
  
  // Complete sound: Google-style alarm with repeating high-low pattern
  complete: [
    // First cycle
    { frequency: 880, duration: 150, volume: 0.6, type: 'sawtooth' },   // A5 (high)
    { frequency: 440, duration: 150, volume: 0.6, type: 'sawtooth', delay: 200 },   // A4 (low)
    // Second cycle
    { frequency: 880, duration: 150, volume: 0.7, type: 'sawtooth', delay: 400 },   // A5 (high)
    { frequency: 440, duration: 150, volume: 0.7, type: 'sawtooth', delay: 200 },   // A4 (low)
    // Third cycle
    { frequency: 880, duration: 150, volume: 0.8, type: 'sawtooth', delay: 400 },   // A5 (high)
    { frequency: 440, duration: 150, volume: 0.8, type: 'sawtooth', delay: 200 },   // A4 (low)
    // Fourth cycle (louder)
    { frequency: 880, duration: 150, volume: 0.8, type: 'sawtooth', delay: 400 },   // A5 (high)
    { frequency: 440, duration: 300, volume: 0.8, type: 'sawtooth', delay: 200 }    // A4 (low, longer)
  ]
};

// Play a pattern of beeps to create more complex sounds
function playPattern(pattern) {
  if (!pattern || !Array.isArray(pattern)) return;
  
  // Initialize audio context with user interaction
  const ctx = initAudioContext();
  if (!ctx) return;
  
  // Clear any previous sounds in progress
  if (window._currentOscillators) {
    window._currentOscillators.forEach(osc => {
      try { osc.stop(); } catch (e) {}
    });
  }
  window._currentOscillators = [];
  
  // Play each note in the pattern with its specified delay
  pattern.forEach((note, index) => {
    // Use the delay specified in the note, or a default based on position
    const noteDelay = note.delay !== undefined ? note.delay : index * 150;
    
    setTimeout(() => {
      try {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        
        oscillator.type = note.type || 'sine';
        oscillator.frequency.value = note.frequency;
        gainNode.gain.value = note.volume || 0.5;
        
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        
        // Store reference for potential cleanup
        window._currentOscillators.push(oscillator);
        
        // Start the sound
        oscillator.start();
        
        // Handle fade out
        gainNode.gain.exponentialRampToValueAtTime(
          0.001, ctx.currentTime + (note.duration || 200) / 1000
        );
        
        // Stop the sound after duration
        setTimeout(() => {
          try {
            oscillator.stop();
            // Remove from array
            const index = window._currentOscillators.indexOf(oscillator);
            if (index > -1) window._currentOscillators.splice(index, 1);
          } catch (e) {
            console.error('Failed to stop oscillator:', e);
          }
        }, note.duration || 200);
      } catch (error) {
        console.error('Failed to play note:', error);
      }
    }, noteDelay);
  });
}

// Sound functions to export
const PomodoroSounds = {
  initAudio: () => {
    // Initialize audio context on user interaction
    initAudioContext();
    // Play a silent sound to unlock audio on mobile
    createBeep({ volume: 0.01, duration: 1 });
  },
  playStart: () => playPattern(soundPatterns.start),
  playPause: () => playPattern(soundPatterns.pause),
  playComplete: () => playPattern(soundPatterns.complete)
};

// Initialize on DOM load or on first user interaction
document.addEventListener('DOMContentLoaded', () => {
  // Listen for any user interaction to initialize audio
  const initAudio = () => {
    PomodoroSounds.initAudio();
    // Remove listeners after first interaction
    document.removeEventListener('click', initAudio);
    document.removeEventListener('touchstart', initAudio);
    document.removeEventListener('keydown', initAudio);
  };
  
  document.addEventListener('click', initAudio);
  document.addEventListener('touchstart', initAudio);
  document.addEventListener('keydown', initAudio);
});

// Make sounds available globally
window.PomodoroSounds = PomodoroSounds; 