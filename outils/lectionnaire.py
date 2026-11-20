"""Met à jour data/lectionnaire.json : références des lectures de la messe et célébration du jour
(calendrier liturgique pour la France), d'après le service public de l'AELF (api.aelf.org).

Seules les RÉFÉRENCES (ex. « Lc 19, 45-48 ») et les noms des célébrations sont gardés : aucun texte
liturgique (protégé) n'est recopié. Chaque référence est reliée au texte Crampon de l'appli
(livre, chapitre, versets), et vérifiée : le passage doit exister dans data/<livre>.json.

Usage :
  python3 outils/lectionnaire.py              télécharge les dates publiées et met le fichier à jour
  python3 outils/lectionnaire.py --verifier   relit le fichier, sans réseau, et revérifie chaque passage
Lancé chaque semaine par .github/workflows/lectionnaire.yml : l'appli reçoit les nouvelles dates seule."""
import concurrent.futures, datetime, json, os, re, sys, time, unicodedata, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'lectionnaire.json')
API = 'https://api.aelf.org/v1/messes/{}/france'
UA = 'Lectio/1.0 (+https://github.com/nthfv/lectio)'
KEEP_PAST = 62          # jours passés gardés
AHEAD_MAX = 460         # jours futurs au plus

# ---------- livres de l'appli ----------
def load_books():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    m = re.search(r'const BOOKS = (\[.*?\]);\n', html)
    books = json.loads(m.group(1))
    out = {b['a'].replace(' ', '').lower(): b for b in books}
    for b in books:      # noms complets aussi (« Isaïe »)
        out.setdefault(fold(b['s']).replace(' ', ''), b)
    return out
def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
BOOKS = load_books()
_maxv = {}
def chapters(bid):
    if bid not in _maxv:
        d = json.load(open(os.path.join(ROOT, 'data', bid + '.json'), encoding='utf-8'))
        _maxv[bid] = {ch['n']: max([x[1] for x in ch['b'] if x[0] in ('v', 'c')] or [0]) for ch in d['c']}
    return _maxv[bid]

def lit_to_heb(n, letter=''):
    """Numérotation liturgique (grecque) des psaumes -> numérotation de la Bible (hébraïque, celle de Crampon)."""
    if n == 9: return 10 if letter.upper() == 'B' else 9
    if n == 113: return 115 if letter.upper() == 'B' else 114
    if n <= 8 or n >= 148: return n
    if n <= 112: return n + 1
    if n in (114, 115): return 116
    if n <= 145: return n + 1
    return 147   # 146 et 147

ITEM = re.compile(r'^(\d+)([a-z]*)(?:\s*-\s*(\d+)([a-z]*))?$')
DASH = re.compile(r'\s*[–—]\s*')

class RefError(Exception):
    pass

def book_of(tok):
    b = BOOKS.get(fold(tok).replace(' ', '').replace('.', ''))
    if not b: raise RefError('livre inconnu : ' + tok)
    return b

def items(spec, bid, chap):
    """« 11-12.15-17 », « 1-2ab, 2c-3, 4 » -> [(chap, v1, v2)]"""
    if bid == 'est' and chap == 4 and re.search(r'17\s*[a-z]', spec):
        # ajouts grecs d'Esther (4, 17a-17z… dans la liturgie) : chapitres 13 et 14 dans Crampon
        # 4, 17a-i : prière de Mardochée (Crampon 13, 8-18) ; 4, 17k et suivants : prière d'Esther (Crampon 14, 1-19)
        return [('est-esther',)] if re.search(r'17\s*[k-z]|[a-z]{2}', spec) else [('est-mardochee',)]
    out = []
    for it in re.split(r'\s*[.,]\s*', spec.strip()):
        if not it or re.fullmatch(r'[a-z]+', it): continue   # « 4a.c » : 4c, partie du même verset
        m = ITEM.match(it)
        if not m: raise RefError(f'versets illisibles : {it!r}')
        a, la, b, lb = m.groups()
        out.append((chap, int(a), int(b) if b else int(a)))
    return out

def parse_one(ref, typ):
    s = ref.replace(' ', ' ').replace(' ', ' ').strip().rstrip('.')
    s = re.sub(r'^\[[^\]]*\]\s*', '', s)                          # « [CANTIQUE] Lc 1, … »
    s = re.sub(r'^(?:cf\.?|cantique)\s*', '', s, flags=re.I)
    s = re.sub(r'\s*\((?!\s*\d+\s*[ABab]?\s*\))[^)]*\)', '', s)    # « (lecture brève) », « (Vg : 5-10) » ; garde « (23) »
    s = re.sub(r'\s+et\s+', ', ', s)                               # « 3 et 5 »
    s = re.sub(r',\s*-', '-', s)                                   # « 11,-12ab »
    s = re.sub(r'(\d)\s+([a-z]+)\b', r'\1\2', s)                   # « 8 cde »
    s = re.sub(r'(\d[a-z]*)\s*-\s*(\d)', r'\1-\2', s)              # « 46b- 47 »
    s = re.sub(r'(\d[a-z]*)[–—](\d)', r'\1-\2', s)                 # « 1–2a » : tiret long collé = même chapitre
    s = re.sub(r'(\d[a-z]*)\s*[–—]\s*(\d+[a-z]*)(?!\d)(?!\s*,\s*\d)', r'\1-\2', s)   # « 13 – 53, 12 » reste un saut de chapitre
    s = re.sub(r'\s+', ' ', s)
    segs, book = [], None
    for part in [p.strip() for p in s.split(';') if p.strip()]:
        m = re.match(r'^((?:[123]\s?)?[A-Za-zÀ-ÿ]+)\.?\s+(\d.*)$', part)
        if m:
            book = book_of(m.group(1)); rest = m.group(2)
        elif book is None and typ.startswith('psaume') and re.match(r'^\d', part):
            book = BOOKS['ps']; rest = part
        elif book is not None and re.match(r'^\d', part):
            rest = part
        else:
            raise RefError('référence illisible : ' + part)
        bid = book['id']
        if bid == 'ps':
            # « 22 (23) », « 18b (19) », « 146 (147A) », « 114 (116 A) », « 44, (45) », « 9a »
            pm = re.match(r'^(\d+)\s*([ABab])?\s*,?\s*(?:\((\d+)\s*[ABab]?\))?\s*(?:,\s*(.*))?$', rest)
            if not pm: raise RefError('psaume illisible : ' + rest)
            # le numéro liturgique fait foi ; le numéro hébreu entre parenthèses sert à choisir 9/10 et 114/115
            # (et une coquille de l'AELF comme « Ps 129 (103) » ne fait pas afficher le mauvais psaume)
            lit = lit_to_heb(int(pm.group(1)), pm.group(2) or '')
            ok = {9: (9, 10), 113: (114, 115)}.get(int(pm.group(1)), (lit,))
            chap = int(pm.group(3)) if pm.group(3) and int(pm.group(3)) in ok else lit
            spec = pm.group(4) or ''
            found = items(spec, bid, chap) if spec else [(chap, 1, 999)]
        elif book['n'] == 1 and ',' not in rest:
            found = items(rest, bid, 1)
        else:
            if ',' not in rest:
                found = [(int(rest), 1, 999)]
            else:
                c, spec = rest.split(',', 1)
                chap = int(c)
                if DASH.search(spec):     # « 13 – 53, 12 » : d'un chapitre à un autre
                    left, right = DASH.split(spec, 1)
                    c2, spec2 = right.split(',', 1)
                    found = items(left, bid, chap)
                    *head, last = found
                    found = head + [(chap, last[1], 999)]
                    for cc in range(chap + 1, int(c2)):
                        found.append((cc, 1, 999))
                    rest2 = items(spec2, bid, int(c2))
                    found += [(int(c2), 1, rest2[0][2])] + rest2[1:]
                else:
                    found = items(spec, bid, chap)
        for f in found:
            if f[0] == 'est-esther': segs.append([bid, 14, 1, 19, 'esther'])
            elif f[0] == 'est-mardochee': segs.append([bid, 13, 8, 18, 'mardochee'])
            else:
                c, a, b = f
                vm = VMAP.get((bid, c))
                if vm and (a in vm or b in vm):
                    segs.append([bid, c, vm[a][0] if a in vm else a, vm[b][1] if b in vm and b != 999 else b, 'approx'])
                elif bid in APPROX_BOOKS:
                    segs.append([bid, c, a, b, 'approx'])
                else:
                    segs.append([bid, c, a, b])
    # vérification, bornes, fusion des passages contigus
    out = []
    for sg in segs:
        bid, c, a, b = sg[:4]
        chs = chapters(bid)
        if c not in chs: raise RefError(f'chapitre absent : {bid} {c}')
        b = chs[c] if b == 999 else b
        if a < 1 or a > chs[c] or b < a: raise RefError(f'versets absents : {bid} {c}, {a}-{b} (max {chs[c]})')
        # numérotation un peu différente dans Crampon (Siracide…) : passage borné et signalé
        sg = [bid, c, a, min(b, chs[c])] + (sg[4:] or (['approx'] if b > chs[c] else []))
        b = sg[3]
        prev = out[-1] if out else None
        if (prev and prev[0] == bid and prev[1] == c and prev[4:] in ([], ['approx']) and sg[4:] in ([], ['approx'])
                and prev[2] <= a <= prev[3] + 1):
            prev[3] = max(prev[3], b)                       # passages contigus : un seul bloc
            if sg[4:] and not prev[4:]: prev.append('approx')
        elif not (prev and prev == sg):
            out.append(sg)
    return out

# Passages où la numérotation de la Bible Crampon diffère de celle de la liturgie (néo-Vulgate) :
# verset liturgique -> (premier, dernier) verset Crampon. Chaque correspondance a été contrôlée sur le texte
# (outils/verifier-lectures.py compare chaque lecture au texte officiel).
VMAP = {
    ('si', 3): {20: (19, 19), 21: (20, 20), 22: (21, 21), 23: (22, 22), 24: (23, 23), 26: (24, 24), 27: (25, 25),
                28: (26, 26), 29: (27, 27), 30: (28, 28), 31: (29, 29)},
    ('si', 17): {24: (19, 19), 25: (20, 20), 26: (21, 21), 27: (22, 22), 28: (23, 23), 29: (24, 24), 30: (25, 25),
                 31: (26, 26), 32: (27, 27)},
    ('si', 36): {16: (13, 13), 17: (14, 14), 18: (15, 15), 19: (16, 16), 20: (17, 17), 21: (18, 18), 22: (19, 19),
                 23: (20, 20), 24: (21, 21), 25: (22, 22), 26: (23, 23), 27: (24, 24), 28: (25, 25), 29: (26, 26),
                 30: (27, 27), 31: (28, 28)},
    ('tb', 13): {7: (6, 6), 8: (6, 6)},
    ('jdt', 13): {18: (23, 24), 19: (25, 25), 20: (25, 26)},
}
# Judith : Crampon suit la Vulgate, la liturgie le grec ; tout passage non contrôlé est signalé.
APPROX_BOOKS = {'jdt'}
# Coquilles connues dans les références publiées par l'AELF (référence sans espaces -> référence corrigée)
CORRECTIONS = {'Rm8,28,30': 'Rm 8, 28-30'}

def fix_ref(ref, typ=''):
    """Corrige les coquilles connues de l'AELF dans une référence (texte affiché et passage)."""
    r = CORRECTIONS.get(re.sub(r'\s', '', ref), ref)
    m = re.match(r'^(\s*(?:(?:Cantique\s+)?Ps\.?\s*)?)(\d+)\s*([ABab])?\s*,?\s*\((\d+)\s*[ABab]?\)', r)
    if m and (typ.startswith('psaume') or 'Ps' in m.group(1)):
        n = int(m.group(2)); lit = lit_to_heb(n, m.group(3) or '')
        if int(m.group(4)) not in {9: (9, 10), 113: (114, 115)}.get(n, (lit,)):
            r = r[:m.start(4)] + str(lit) + r[m.end(4):]      # « Ps 129 (103) » -> « Ps 129 (130) »
    return r

def parse(ref, typ):
    """Une référence (avec d'éventuelles variantes « … ou … ») -> liste de variantes, chacune liste de passages."""
    ref = fix_ref(ref, typ)
    try:
        return [parse_one(alt, typ) for alt in re.split(r'\s+ou\s+', ref.strip())]
    except (RefError, ValueError, IndexError) as e:
        if '. ' in ref:      # étiquette avant la référence : « Stabat Mater. Jn 19, 25-27 »
            again = parse(ref.split('. ', 1)[1], typ)
            if not isinstance(again, dict): return again
        return {'erreur': str(e)}

# ---------- téléchargement ----------
def get(day):
    url = API.format(day)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    raise RuntimeError('AELF injoignable pour ' + day)

def clean(s):
    return re.sub(r'\s+', ' ', (s or '').replace(' ', ' ')).strip()

def entry(j):
    i = j.get('informations') or {}
    e = {'n': clean(i.get('jour_liturgique_nom')), 'g': clean(i.get('degre')), 'c': clean(i.get('couleur')),
         'l': [clean(i.get(k)) for k in ('ligne1', 'ligne2', 'ligne3') if clean(i.get(k))],
         't': clean(i.get('temps_liturgique')), 'a': clean(i.get('annee'))}
    for k in ('couleur2', 'couleur3'):
        if clean(i.get(k)): e.setdefault('c2', []).append(clean(i.get(k)))
    masses = []
    for m in j.get('messes') or []:
        lec = []
        for l in m.get('lectures') or []:
            ref = fix_ref(clean(l.get('ref')), clean(l.get('type')))
            if not ref: continue
            lec.append([clean(l.get('type')), ref, parse(ref, clean(l.get('type')))])
        masses.append([clean(m.get('nom')), lec])
    e['m'] = masses
    return {k: v for k, v in e.items() if v not in ('', [], None)}

def download(existing):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=7)
    days = [(start + datetime.timedelta(days=k)).isoformat() for k in range(AHEAD_MAX + 7)]
    got, misses = {}, 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for k in range(0, len(days), 20):
            batch = days[k:k + 20]
            for day, j in zip(batch, ex.map(get, batch)):
                if j is None: misses += 1
                else: misses = 0; got[day] = entry(j)
            if misses >= 20 and k > 60: break   # au-delà de ce que l'AELF a publié
            time.sleep(0.5)
    keep = (today - datetime.timedelta(days=KEEP_PAST)).isoformat()
    d = {k: v for k, v in existing.items() if k >= keep}
    d.update(got)
    return dict(sorted(d.items()))

def report(d):
    bad = [(day, m[0], l[0], l[1], l[2]['erreur']) for day, e in d.items() for m in e.get('m', []) for l in m[1] if isinstance(l[2], dict)]
    n = sum(len(m[1]) for e in d.values() for m in e.get('m', []))
    print(f'{len(d)} jours, {n} lectures, {len(bad)} références non reliées au texte Crampon')
    for b in bad[:40]: print('  ', *b)
    return bad

def main():
    old = {}
    if os.path.exists(OUT):
        old = json.load(open(OUT, encoding='utf-8'))
    if '--verifier' in sys.argv:
        d = json.loads(json.dumps(old.get('d', {})))
        for e in d.values():
            for m in e.get('m', []):
                for l in m[1]: l[1] = fix_ref(l[1], l[0]); l[2] = parse(l[1], l[0])
    else:
        d = download(old.get('d', {}))
    report(d)
    if not d: sys.exit('aucune date')
    body = {'v': 1, 'source': 'AELF, calendrier liturgique pour la France — références uniquement', 'jusqua': max(d), 'd': d}
    same = {k: v for k, v in old.items() if k != 'maj'} == body
    last = old.get('maj', '2000-01-01')
    if same and (datetime.date.today() - datetime.date.fromisoformat(last)).days < 28:
        print('Rien de nouveau.'); return
    body = {'v': 1, 'maj': datetime.date.today().isoformat(), **{k: v for k, v in body.items() if k != 'v'}}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(body, f, ensure_ascii=False, separators=(',', ':'))
    print('Écrit :', OUT, os.path.getsize(OUT), 'octets, jusqu’au', body['jusqua'])

if __name__ == '__main__':
    main()
