self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open('suppertime-cache').then(cache => {
            return cache.addAll([
                '/',
                '/static/index.html',
                '/static/style.css',
                '/static/chat.js'
            ]);
        })
    );
});

self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then(response => {
            return response || fetch(e.request);
        })
    );
});
