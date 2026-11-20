"""Vérifie que chaque lecture de la messe affichée par Lectio (texte Crampon de l'appli) est bien
le passage lu à la messe ce jour-là (texte officiel de l'AELF), verset par verset.

Pour chaque lecture de data/lectionnaire.json, le texte AELF du jour est téléchargé (api.aelf.org),
puis comparé, mot à mot, aux versets Crampon affichés par l'appli ET à leurs voisins : un verset
affiché qui ne se retrouve pas dans la lecture, ou un verset voisin qui s'y retrouve, est signalé
(décalage de numérotation entre les deux Bibles, mauvais chapitre…).

Rien n'est recopié : le texte AELF (protégé) reste en mémoire le temps de la comparaison ; le rapport
ne contient que des références et des scores.

Usage : python3 outils/verifier-lectures.py [AAAA-MM-JJ AAAA-MM-JJ]   (par défaut : tout le lectionnaire)
Lancé à la main depuis GitHub : onglet Actions › « Vérification des lectures » › Run workflow."""
import concurrent.futures, html, json, os, re, sys, time, unicodedata, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = 'https://api.aelf.org/v1/messes/{}/france'
UA = 'Lectio/1.0 (+https://github.com/nthfv/lectio)'

STOP = set('''le la les l un une des du de d et ou a au aux en dans sur sous par pour pas ne n que qu qui quoi dont
ou ce cet cette ces se s sa son ses leur leurs lui elle il ils elles eux je j me m moi tu t te toi nous vous mon ma
mes ton ta tes notre nos votre vos est sont etre ete etait etaient sera seront ai as avons avez ont avait avaient
fut furent fait faire dit dire disait car mais comme si plus tout tous toute toutes y avec sans vers chez donc ainsi
alors aussi meme la ici voici voila quand lorsque afin parce puis dieu seigneur yahweh jesus christ oui non bien
tres celui celle ceux celles cela ceci ca rien point jour jours'''.split())

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

def stems(text):
    return {w[:5] for w in re.findall(r'[a-z]+', fold(text)) if len(w) > 2 and w not in STOP}

_books = {}
def verses(bid):
    if bid not in _books:
        d = json.load(open(os.path.join(ROOT, 'data', bid + '.json'), encoding='utf-8'))
        t = {}
        for ch in d['c']:
            for b in ch['b']:
                if b[0] in ('v', 'c'):
                    t[(ch['n'], b[1])] = t.get((ch['n'], b[1]), '') + ' ' + re.sub('[\u0001-\u0013]', ' ', b[2])
        _books[bid] = t
    return _books[bid]

def get(day):
    for attempt in range(4):
        try:
            req = urllib.request.Request(API.format(day), headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 + 3 * attempt)
        except Exception:
            time.sleep(2 + 3 * attempt)
    raise RuntimeError('AELF injoignable pour ' + day)

def aelf_text(lecture):
    h = lecture.get('contenu') or ''
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</p>', '\n', h)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    lines = [ln for ln in t.split('\n') if not re.match(r'\s*R\s*/', ln)]   # refrains des psaumes
    return ' '.join(lines)

def check(variant, text):
    """Profil d'un passage : part des mots de chaque verset (affiché ou voisin) qui se retrouvent dans le texte lu."""
    A = stems(text)
    shown, prof, flags = set(), [], []
    for sg in variant:
        bid, c, a, b = sg[:4]
        for v in range(a, b + 1): shown.add((bid, c, v))
    seen = set()
    for sg in variant:
        bid, c, a, b = sg[:4]
        T = verses(bid)
        for v in range(a - 3, b + 4):
            if (bid, c, v) in seen or (c, v) not in T: continue
            seen.add((bid, c, v))
            S = stems(T[(c, v)])
            if len(S) < 4: continue
            cov = len(S & A) / len(S)
            inside = (bid, c, v) in shown
            prof.append((c, v, round(cov, 2), inside))
    inside = [p[2] for p in prof if p[3]]
    mean = sum(inside) / len(inside) if inside else 0
    for c, v, cov, ins in prof:
        if ins and cov < 0.25 and cov < mean * 0.5:
            flags.append(f'affiché mais absent ? {c},{v} ({cov})')
        if not ins and cov >= max(0.55, mean * 0.85):
            flags.append(f'voisin présent ? {c},{v} ({cov})')
    return round(mean, 2), flags, prof

def main():
    lect = json.load(open(os.path.join(ROOT, 'data', 'lectionnaire.json'), encoding='utf-8'))['d']
    days = sorted(lect)
    if len(sys.argv) == 3:
        days = [d for d in days if sys.argv[1] <= d <= sys.argv[2]]
    n = bad = low = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for day, j in zip(days, ex.map(get, days)):
            if not j:
                print(f'{day}\tAELF ne répond pas pour ce jour'); continue
            ours = lect[day].get('m') or []
            for mi, m in enumerate(j.get('messes') or []):
                mine = ours[mi][1] if mi < len(ours) else []
                k = -1
                for l in m.get('lectures') or []:
                    ref = re.sub(r'\s+', ' ', (l.get('ref') or '').replace(' ', ' ')).strip()
                    if not ref: continue
                    typ = l.get('type') or ''
                    k += 1        # même ordre que dans data/lectionnaire.json (référence éventuellement corrigée)
                    hit = mine[k] if k < len(mine) and mine[k][0] == typ else None
                    ref = hit[1] if hit else ref
                    if not hit or not isinstance(hit[2], list):
                        print(f'{day}\t{typ}\t{ref}\tNON RELIÉE'); bad += 1; continue
                    text = aelf_text(l)
                    if len(stems(text)) < 5:
                        continue
                    n += 1
                    mean, flags, prof = check(hit[2][0], text)
                    if mean < 0.35: low += 1
                    if flags or mean < 0.35:
                        bad += 1 if flags else 0
                        segs = ' '.join(f'{s[0]} {s[1]},{s[2]}-{s[3]}' for s in hit[2][0])
                        p = ' '.join(f'{c},{v}={cov}{"*" if ins else ""}' for c, v, cov, ins in prof)
                        print(f'{day}\t{typ}\t{ref}\t[{segs}]\tmoy {mean}\t' + ' | '.join(flags) + f'\n\tprofil : {p}')
    print(f'\n{n} lectures comparées, {bad} à revoir, {low} à faible ressemblance (traductions très différentes ou passage décalé)')

if __name__ == '__main__':
    main()
