"""Vérifie que le site en ligne (GitHub Pages) sert bien la version du dépôt : même numéro de version
dans index.html et sw.js, et chaque fichier de données identique à celui du dépôt (empreinte).

Usage : python3 outils/verifier-site.py [adresse du site]   (par défaut https://nthfv.github.io/lectio/)"""
import hashlib, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = (sys.argv[1] if len(sys.argv) > 1 else 'https://nthfv.github.io/lectio/').rstrip('/') + '/'

def get(path):
    req = urllib.request.Request(SITE + path + ('&' if '?' in path else '?') + f'nocache={time.time()}',
                                 headers={'User-Agent': 'Lectio-verification', 'Cache-Control': 'no-cache'})
    return urllib.request.urlopen(req, timeout=30).read()

def build(s):
    m = re.search(r"const BUILD = \"([^\"]+)\"", s) or re.search(r"const BUILD = '([^']+)'", s)
    return m.group(1) if m else None

local_html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
want = build(local_html)
fails = []
online_html = get('index.html').decode('utf-8')
online_sw = get('sw.js').decode('utf-8')
print('version du dépôt   :', want)
print('version en ligne   :', build(online_html), '(index.html) /', build(online_sw), '(sw.js)')
if build(online_html) != want or build(online_sw) != want:
    fails.append('version en ligne différente')
dh = json.loads(re.search(r'const DH = (\{[^}]*\})', local_html).group(1))
bad = []
for i, h in dh.items():
    data = get(f'data/{i}.json?v={h}')
    if hashlib.sha256(data).hexdigest()[:10] != h:
        bad.append(i)
print(f'{len(dh)} fichiers de données contrôlés, {len(bad)} différents', bad)
if bad: fails.append('données en ligne différentes')
lect = get('data/lectionnaire.json')
same = lect == open(os.path.join(ROOT, 'data', 'lectionnaire.json'), 'rb').read()
print('lectionnaire en ligne identique au dépôt :', same)
if not same: fails.append('lectionnaire différent')
print('RÉSULTAT :', 'tout est à jour' if not fails else ' ; '.join(fails))
sys.exit(1 if fails else 0)
