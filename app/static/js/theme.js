/**
 * Theme synchronization for favicon
 * Ensures the favicon matches the application theme (dark/light mode)
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get the current theme and update favicon
    const currentTheme = document.documentElement.getAttribute('data-theme');
    updateFavicon(currentTheme);
    
    // Listen for theme changes by observing the html data-theme attribute
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'data-theme') {
                const newTheme = document.documentElement.getAttribute('data-theme');
                updateFavicon(newTheme);
            }
        });
    });
    
    // Start observing theme changes
    observer.observe(document.documentElement, { attributes: true });
});

/**
 * Updates the favicon to match the current theme
 * @param {string} theme - The current theme ('light' or 'dark')
 */
function updateFavicon(theme) {
    // Find all favicon links
    const favicons = document.querySelectorAll('link[rel*="icon"]');
    
    // Remove any existing favicons
    favicons.forEach(favicon => {
        favicon.remove();
    });
    
    // Create new favicon link
    const newFavicon = document.createElement('link');
    newFavicon.rel = 'icon';
    newFavicon.type = 'image/svg+xml';
    
    // Set the appropriate favicon based on theme
    if (theme === 'dark') {
        newFavicon.href = '/static/images/favicon-dark.svg';
    } else {
        newFavicon.href = '/static/images/favicon-light.svg';
    }
    
    // Add the favicon to the head
    document.head.appendChild(newFavicon);
} 