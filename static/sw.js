const CACHE_NAME = 'calendar-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/main.js',
  '/static/manifest.json'
];

self.addEventListener('install', event => {
  console.log('[SW] Установка');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Кэш открыт');
        return cache.addAll(urlsToCache);
      })
      .catch(err => console.log('[SW] Ошибка кэширования:', err))
  );
});

self.addEventListener('activate', event => {
  console.log('[SW] Активация');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Удаление старого кэша:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request).catch(error => {
          console.log('[SW] Ошибка сети:', error);
        });
      })
  );
});

// self.addEventListener('push', event => {
//   console.log('[SW] Push получен');
//   const options = {
//     body: event.data ? event.data.text() : 'Новое уведомление',
//     icon: '/static/icon-192.png',
//     badge: '/static/icon-192.png',
//     vibrate: [100, 50, 100],
//     data: {
//       dateOfArrival: Date.now(),
//       primaryKey: 1
//     }
//   };

//   event.waitUntil(
//     self.registration.showNotification('Календарь', options)
//   );
// });
// self.addEventListener('push', (event) => {
//     const data = event.data.json();
//     event.waitUntil(
//         self.registration.showNotification(data.title, {
//             body: data.body,
//             requireInteraction: true,
//             icon: '/static/icon-512.png',
//         })
//     );
// });

self.addEventListener('push', (event) => {
    let data = { title: 'Календарь', body: 'Новое уведомление', url: '/' };
    try {
        data = event.data.json();
    } catch (e) {
        data.body = event.data ? event.data.text() : data.body;
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icon-192.png',
            badge: '/static/icon-192.png',
            vibrate: [100, 50, 100],
            requireInteraction: true,
            data: { url: data.url || '/' },
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data?.url || '/'));
});