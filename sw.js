/* Lectio — service worker.
   L’appli s’ouvre sans connexion ; une nouvelle version remplace les fichiers de l’appli
   mais ne touche jamais à vos versets (ils sont dans le stockage de la page, pas ici). */
const BUILD = "2026.11.20-3";
const SHELL = 'lectio-shell-' + BUILD;
const DATA = 'lectio-data';
const FONTS = 'lectio-fonts';
const SHELL_FILES = ['manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png', 'icons/favicon-32.png'];
const DATA_FILES = ["data/analyses.json?v=3e91246b5c", "data/feed.json?v=047fd2e036", "data/gn.json?v=61aa16be77", "data/ex.json?v=3d60284703", "data/lv.json?v=d9a992e751", "data/nb.json?v=001e448ae1", "data/dt.json?v=8efcefaf38", "data/jos.json?v=2bf0e226b7", "data/jg.json?v=75ce8ef50b", "data/rt.json?v=cb6fa4e13d", "data/1s.json?v=ed3598dcb4", "data/2s.json?v=a13db7cfbe", "data/1r.json?v=090ae225ee", "data/2r.json?v=fb6744212c", "data/1ch.json?v=2b3d94a92f", "data/2ch.json?v=860e23f0d4", "data/esd.json?v=5950a10a73", "data/ne.json?v=74e0a37526", "data/tb.json?v=43fc77626b", "data/jdt.json?v=8a674cc968", "data/est.json?v=aa8f21f173", "data/1m.json?v=b7d0fe9c6a", "data/2m.json?v=61cd5d1dce", "data/jb.json?v=0cee0589a3", "data/ps.json?v=5c7135afc5", "data/pr.json?v=009cde48f7", "data/qo.json?v=7485f47e43", "data/ct.json?v=9e7aee22e4", "data/sg.json?v=f81388396d", "data/si.json?v=cf1d2d8ae0", "data/is.json?v=a1ac17620c", "data/jr.json?v=fe15080c40", "data/lm.json?v=cf06106648", "data/ba.json?v=90f9c534b5", "data/ez.json?v=fd146b0bd1", "data/dn.json?v=b499ad4a8f", "data/os.json?v=f0591038ab", "data/jl.json?v=5193104af6", "data/am.json?v=8266cc1d5f", "data/ab.json?v=be0785064d", "data/jon.json?v=4b6bf93e1c", "data/mi.json?v=b5ccc33d48", "data/na.json?v=803b73457b", "data/ha.json?v=bc7868f195", "data/so.json?v=7908013aa9", "data/ag.json?v=7bea7d1cd9", "data/za.json?v=55eab2ee45", "data/ml.json?v=81ae34c797", "data/mt.json?v=8c73175070", "data/mc.json?v=87f50e924e", "data/lc.json?v=d262fa00a0", "data/jn.json?v=367c505983", "data/ac.json?v=b25cd27915", "data/rm.json?v=cf088390cd", "data/1co.json?v=c369b213d1", "data/2co.json?v=34fcc5680f", "data/ga.json?v=bbf1b3ced4", "data/ep.json?v=f9a42b5555", "data/ph.json?v=37733e42d4", "data/col.json?v=79602a3980", "data/1th.json?v=cf990d786d", "data/2th.json?v=87bdab8c92", "data/1tm.json?v=b757a23db2", "data/2tm.json?v=b236a6b032", "data/tt.json?v=460e02be9e", "data/phm.json?v=8465cea793", "data/he.json?v=9bab10a198", "data/jc.json?v=6d56018212", "data/1p.json?v=60720efe74", "data/2p.json?v=0acd0ff0dd", "data/1jn.json?v=12d9c8331a", "data/2jn.json?v=80cc455771", "data/3jn.json?v=3ce7c7763c", "data/jude.json?v=40a02c3d04", "data/ap.json?v=281611bb53"];
const CORE = DATA_FILES.filter(u => /^data\/(analyses|feed)\.json/.test(u));
const LIVE = 'data/lectionnaire.json';   // lectures du jour : complété chaque semaine, servi aussitôt puis rafraîchi
const abs = u => new URL(u, self.registration.scope).href;

self.addEventListener('install', e => {
 e.waitUntil((async () => {
  // la page doit être celle de cette version (le serveur peut mettre quelques minutes à la publier)
  const r = await fetch(new Request('index.html', { cache: 'reload' }));
  const html = await r.text();
  if (!r.ok || !html.includes('const BUILD = ' + JSON.stringify(BUILD))) throw new Error('index.html pas encore à jour');
  const shell = await caches.open(SHELL);
  const page = () => new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  await shell.put('index.html', page());
  await shell.put('./', page());
  await shell.addAll(SHELL_FILES.map(u => new Request(u, { cache: 'reload' })));
  const data = await caches.open(DATA);
  for (const u of CORE.concat([LIVE])) if (!(await data.match(u))) { const d = await fetch(new Request(u, { cache: 'reload' })); if (d.ok) await data.put(u, d); }
 })());
});

self.addEventListener('message', e => { if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting(); });

self.addEventListener('activate', e => {
 e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k.startsWith('lectio-shell-') && k !== SHELL) await caches.delete(k);
  const keep = new Set(DATA_FILES.concat([LIVE]).map(abs));
  const data = await caches.open(DATA);
  for (const req of await data.keys()) if (!keep.has(req.url)) await data.delete(req);
  await self.clients.claim();
 })());
});

self.addEventListener('fetch', e => {
 const req = e.request;
 if (req.method !== 'GET') return;
 const url = new URL(req.url);
 if (url.origin === self.location.origin) {
  if (!url.href.startsWith(self.registration.scope)) return;
  if (req.mode === 'navigate') { e.respondWith(caches.open(SHELL).then(c => c.match('index.html')).then(r => r || fetch(req))); return; }
  if (url.pathname.endsWith('/' + LIVE)) { e.respondWith(fromLive(req, e)); return; }
  if (url.pathname.includes('/data/')) { e.respondWith(fromData(req)); return; }
  e.respondWith(caches.open(SHELL).then(c => c.match(req, { ignoreSearch: true })).then(r => r || fetch(req)));
  return;
 }
 if (url.hostname === 'fonts.gstatic.com' || url.hostname === 'fonts.googleapis.com') e.respondWith(fromFonts(req, e));
});

async function fromData(req) {
 const c = await caches.open(DATA);
 const hit = await c.match(req);
 if (hit) return hit;
 const r = await fetch(req);
 if (r.ok) await c.put(req, r.clone());
 return r;
}

async function fromLive(req, e) {
 const c = await caches.open(DATA);
 const hit = await c.match(LIVE);
 const net = fetch(new Request(LIVE, { cache: 'no-cache' })).then(r => { if (r.ok) return c.put(LIVE, r.clone()).then(() => r); return r; });
 if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
 return net;
}

async function fromFonts(req, e) {
 const c = await caches.open(FONTS);
 const hit = await c.match(req);
 const refresh = () => fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; });
 if (hit) { if (req.url.includes('fonts.googleapis.com')) e.waitUntil(refresh().catch(() => {})); return hit; }
 try { return await refresh(); } catch (err) { return new Response('', { status: 504 }); }
}
