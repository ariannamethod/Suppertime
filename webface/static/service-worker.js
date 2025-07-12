self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open('suppertime-cache').then(cache => {
            return cache.addAll([
                '/',
                '/static/index.html',
                '/static/style.css',
                '/static/chat.js',
                '/static/suppertime_v1.4.html',
                '/static/suppertime_v1.6.html',
                '/static/resonance.html',
                '/static/page.css',
                '/static/page.js'
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
