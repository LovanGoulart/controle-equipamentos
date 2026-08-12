const CACHE_NAME = 'patrimonio-v3';  // <-- bump version para forçar atualização
const STATIC_CACHE = 'patrimonio-static-v3';

const STATIC_ASSETS = [
  '/login',
  '/static/css/style.css',
  '/static/js/app.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// Rotas dinâmicas que NUNCA devem ser cache-first
const DYNAMIC_ROUTES = [
  '/dashboard',
  '/equipamentos',
  '/equipamento/',
  '/historico',
  '/relatorios',
  '/impressao',
  '/exportar/',
  '/observacao/',
  '/offline.html'
];

function isDynamicRoute(url) {
  return DYNAMIC_ROUTES.some(route => url.pathname.startsWith(route));
}

// ========== INSTALL ==========
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ========== ACTIVATE ==========
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// ========== FETCH ==========
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // 1) Rotas dinâmicas → Network-first (sempre busca no servidor)
  if (isDynamicRoute(url)) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // Atualiza o cache com a versão mais recente
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Se offline, tenta o cache como fallback
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            if (event.request.destination === 'document') {
              return caches.match('/offline.html');
            }
          });
        })
    );
    return;
  }

  // 2) Assets estáticos (CSS, JS, imagens, fontes) → Cache-first
  if (
    url.pathname.startsWith('/static/') ||
    event.request.destination === 'style' ||
    event.request.destination === 'script' ||
    event.request.destination === 'image' ||
    event.request.destination === 'font'
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) {
          // Atualiza em segundo plano (stale-while-revalidate)
          fetch(event.request).then((response) => {
            if (response && response.status === 200) {
              caches.open(STATIC_CACHE).then((cache) => {
                cache.put(event.request, response.clone());
              });
            }
          }).catch(() => {});
          return cached;
        }
        return fetch(event.request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // 3) Outras requisições (API, etc.) → Network-first
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});