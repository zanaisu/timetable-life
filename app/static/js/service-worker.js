// Service Worker for Timetable App
const CACHE_NAME = 'timetable-app-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/animations.css',
  '/static/css/main.css',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/theme.js',
  '/static/images/favicon.svg',
  '/static/images/favicon-light.svg',
  '/static/images/favicon-dark.svg',
  // Add other important static assets here
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Skip API and dynamic routes - only cache static assets
  if (event.request.url.includes('/api/') || event.request.url.includes('/auth/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          // Return cached response
          return cachedResponse;
        }

        // If not in cache, fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache if not a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone the response as it can only be used once
            const responseToCache = response.clone();

            // Cache the fetched response for future use
            if (event.request.url.includes('/static/')) {
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseToCache);
                });
            }

            return response;
          })
          .catch(error => {
            console.error('Fetch failed:', error);
            // Show offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match('/offline.html');
            }
            return new Response('Network error happened', {
              status: 408,
              headers: { 'Content-Type': 'text/plain' }
            });
          });
      })
  );
});

// Background sync for offline form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-forms') {
    event.waitUntil(syncForms());
  }
});

// Helper function to sync data when online
async function syncForms() {
  try {
    const offlineData = await getOfflineData();
    for (const item of offlineData) {
      await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.body
      });
      await removeOfflineData(item.id);
    }
    return true;
  } catch (error) {
    console.error('Background sync failed:', error);
    return false;
  }
}

// Placeholder functions for offline data storage
// These would be implemented with IndexedDB in a real application
async function getOfflineData() {
  return [];
}

async function removeOfflineData(id) {
  return true;
} 