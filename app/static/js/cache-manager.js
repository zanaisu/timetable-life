/**
 * Cache Manager for Timetable App
 * Handles service worker registration and browser caching
 */

// Register service worker
function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/service-worker.js')
        .then(registration => {
          console.log('Service Worker registered with scope:', registration.scope);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });
    });
  }
}

// Prefetch important pages
function prefetchResources() {
  // Only prefetch if the browser supports it
  if ('connection' in navigator && navigator.connection.saveData === true) {
    // Don't prefetch if data-saver is enabled
    return;
  }

  const pagesToPrefetch = [
    '/',
    '/curriculum',
    '/static/css/style.css',
    '/static/js/theme.js',
    // Add other important pages here
  ];

  // Wait until after page load to prefetch
  window.addEventListener('load', () => {
    // Wait a bit to not compete with initial page resources
    setTimeout(() => {
      pagesToPrefetch.forEach(url => {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = url;
        document.head.appendChild(link);
      });
    }, 1000);
  });
}

// Quick response for repeat views
function implementQuickResponse() {
  // Add page transition cache hint
  document.addEventListener('click', event => {
    // Only for internal links
    const link = event.target.closest('a');
    if (link && link.href && link.href.startsWith(window.location.origin) && !link.href.includes('/api/')) {
      // Hint to browser to preconnect to the URL
      const hint = document.createElement('link');
      hint.rel = 'preconnect';
      hint.href = link.href;
      document.head.appendChild(hint);
    }
  });
}

// Initialize cache manager
function initCacheManager() {
  registerServiceWorker();
  prefetchResources();
  implementQuickResponse();
}

// Run initialization
initCacheManager(); 