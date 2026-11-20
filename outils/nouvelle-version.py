"""Prépare une nouvelle version de Lectio, à lancer juste avant de publier :

    python3 outils/nouvelle-version.py

1. Donne un nouveau numéro de version (BUILD) à index.html ET à sw.js : c’est ce changement
   qui fait apparaître « Nouvelle version disponible › Mettre à jour » dans l’appli installée.
2. Recalcule l’empreinte de chaque fichier de data/ (DH dans index.html, DATA_FILES dans sw.js) :
   l’appli retélécharge alors seulement les fichiers modifiés.

Les versets aimés et la progression ne sont jamais touchés : ils sont sur le téléphone
(clé « lectio.state »), pas dans le dépôt."""
import datetime, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX, SW, DATA = os.path.join(ROOT, 'index.html'), os.path.join(ROOT, 'sw.js'), os.path.join(ROOT, 'data')
BUILD_RX = re.compile(r'const BUILD = "([^"]*)";')

def read(p): return open(p, encoding='utf-8').read()
def fail(m): sys.exit('ERREUR : ' + m)

index, sw = read(INDEX), read(SW)
old = BUILD_RX.findall(index)
if len(old) != 1 or BUILD_RX.findall(sw) != old: fail('BUILD introuvable ou différent entre index.html et sw.js')
old = old[0]

# 1. numéro de version : date du jour + compteur
today = datetime.date.today().strftime('%Y.%m.%d')
n = int(old.split('-')[1]) + 1 if old.startswith(today + '-') else 1
build = f'{today}-{n}' if len(sys.argv) < 2 else sys.argv[1]

# 2. empreintes des fichiers de données
m = re.search(r'const BOOKS = (\[.*?\]);\n', index)
if not m: fail('liste des livres (BOOKS) introuvable dans index.html')
ids = ['analyses', 'feed'] + [b['id'] for b in json.loads(m.group(1))]
for i in ids:
    if not os.path.exists(os.path.join(DATA, i + '.json')): fail(f'fichier manquant : data/{i}.json')
    json.load(open(os.path.join(DATA, i + '.json'), encoding='utf-8'))  # le fichier doit rester du JSON valide
dh = {i: hashlib.sha256(open(os.path.join(DATA, i + '.json'), 'rb').read()).hexdigest()[:10] for i in ids}
files = [f'data/{i}.json?v={dh[i]}' for i in ids]

def sub(rx, new, text, what):
    out, k = re.subn(rx, lambda _: new, text)
    if k != 1: fail(f'{what} introuvable')
    return out

index = sub(BUILD_RX, f'const BUILD = {json.dumps(build)};', index, 'BUILD (index.html)')
index = sub(r'const DH = \{[^}]*\};', f'const DH = {json.dumps(dh)};', index, 'DH (index.html)')
sw = sub(BUILD_RX, f'const BUILD = {json.dumps(build)};', sw, 'BUILD (sw.js)')
sw = sub(r'const DATA_FILES = \[[^\]]*\];', f'const DATA_FILES = {json.dumps(files)};', sw, 'DATA_FILES (sw.js)')
if 'lectio.state' not in index: fail('la clé de stockage lectio.state a disparu de index.html : les versets des utilisateurs seraient perdus')
open(INDEX, 'w', encoding='utf-8').write(index)
open(SW, 'w', encoding='utf-8').write(sw)
print(f'Version {old} → {build} ({len(ids)} fichiers de données vérifiés).')
print('Ensuite : git add -A && git commit -m "…" && git push')
