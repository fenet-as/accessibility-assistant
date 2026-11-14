/**
 * ALX Accessibility Assistant Service Worker
 * Caches widget assets and offline course packs. Chat/escalate stay network-only.
 */
/* eslint-disable no-restricted-globals */
const CACHE_VERSION = 'alx-assistant-sw-v2';
const ASSET_CACHE = `${CACHE_VERSION}-assets`;
const PACK_CACHE = `${CACHE_VERSION}-packs`;

const PRECACHE_URLS = [
  './assistant.js',
  './offline.js',
  './sw.js',
  './shell.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(ASSET_CACHE);
    await cache.addAll(PRECACHE_URLS.map((url) => new Request(url, { cache: 'reload' })));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => !key.startsWith(CACHE_VERSION)).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

function isPackRequest(url) {
  return url.pathname.endsWith('/api/offline/pack') || url.pathname.includes('/api/offline/pack?');
}

function isLanguageRequest(url) {
  return url.pathname.endsWith('/api/languages');
}

function isAssetRequest(url) {
  return url.pathname.includes('/widget/') && !url.pathname.endsWith('/sw.js');
}

function isApiMutation(url, method) {
  if (method !== 'GET' && method !== 'HEAD') return true;
  return url.pathname.includes('/api/chat') || url.pathname.includes('/api/escalate');
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response && response.ok) {
    cache.put(request, response.clone());
  }
  return response;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request).then((response) => {
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);
  if (cached) {
    networkPromise.catch(() => {});
    return cached;
  }
  const network = await networkPromise;
  if (network) return network;
  return new Response(JSON.stringify({ error: 'offline', message: 'Resource unavailable offline' }), {
    status: 503,
    headers: { 'Content-Type': 'application/json' },
  });
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (isApiMutation(url, request.method)) {
    return; // network only — never cache chat/escalate bodies
  }

  if (isPackRequest(url) || isLanguageRequest(url)) {
    event.respondWith(staleWhileRevalidate(request, PACK_CACHE));
    return;
  }

  if (isAssetRequest(url) || PRECACHE_URLS.some((u) => url.pathname.endsWith(u.replace('./', '')))) {
    event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
  }
});

self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (data.type === 'INVALIDATE_PACKS') {
    event.waitUntil(caches.delete(PACK_CACHE).then(() => caches.open(PACK_CACHE)));
  }
  if (data.type === 'GET_VERSION') {
    event.source && event.source.postMessage({ type: 'VERSION', cache: CACHE_VERSION });
  }
});
