"""Établit, pour quelques chapitres, la correspondance entre la numérotation des versets de la Bible
liturgique (AELF) et celle de la Bible Crampon de l'appli, en comparant le contenu verset par verset.
Sert à contrôler les tables de correspondance de outils/lectionnaire.py (VMAP).

Rien n'est recopié : le texte AELF reste en mémoire le temps de la comparaison ; seuls des numéros de
versets et des scores sont affichés.

Usage : python3 outils/correspondances.py Tb/13 Si/17 Est/4:est/14 …
        (livre/chapitre AELF, et en option :livre/chapitre Crampon à comparer s'il diffère)"""
import html, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Lectio/1.0 (+https://github.com/nthfv/lectio)'
STOP = set('''le la les l un une des du de d et ou a au aux en dans sur sous par pour pas ne n que qu qui quoi dont
ce cet cette ces se s sa son ses leur leurs lui elle il ils elles eux je j me m moi tu t te toi nous vous mon ma
mes ton ta tes notre nos votre vos est sont etre ete etait fut fait dit car mais comme si plus tout tous toute
toutes y avec sans vers donc ainsi alors aussi meme la ici voici quand afin puis dieu seigneur yahweh'''.split())

def fold(s):
    s = s.lower().replace('œ', 'oe').replace('æ', 'ae')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def stems(t):
    return {w[:5] for w in re.findall(r'[a-z]+', fold(t)) if len(w) > 2 and w not in STOP}

def crampon(bid, c):
    d = json.load(open(os.path.join(ROOT, 'data', bid + '.json'), encoding='utf-8'))
    ch = next(x for x in d['c'] if x['n'] == c)
    out = {}
    for b in ch['b']:
        if b[0] in ('v', 'c'):
            out[b[1]] = out.get(b[1], '') + ' ' + re.sub('[\u0001-\u0013]', ' ', b[2])
    return out

def aelf(book, c):
    req = urllib.request.Request(f'https://www.aelf.org/bible/{book}/{c}', headers={'User-Agent': UA})
    h = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
    h = re.sub(r'(?is)<(script|style|nav|header|footer)\b.*?</\1>', ' ', h)
    # numéros de versets : essayer plusieurs balisages
    pats = [r'<span[^>]*class="[^"]*(?:verse|vers|num)[^"]*"[^>]*>\s*(\d+[a-z]{0,2})\s*</span>',
            r'<sup[^>]*>\s*(\d+[a-z]{0,2})\s*</sup>',
            r'<span[^>]*>\s*(\d+[a-z]{0,2})\s*</span>']
    for p in pats:
        parts = re.split(p, h)
        if len(parts) > 7:
            verses = {}
            for k in range(1, len(parts) - 1, 2):
                t = html.unescape(re.sub(r'<[^>]+>', ' ', parts[k + 1]))
                verses[parts[k]] = t
            return verses, p
    tags = sorted(set(re.findall(r'<(\w+)[^>]*class="([^"]+)"', h)))[:80]
    raise RuntimeError(f'numéros de versets introuvables ; balises vues : {tags}')

def messe(arg):
    """« 2027-02-18:lecture_1:est/14 » : phrase par phrase, verset Crampon le plus proche dans ce chapitre."""
    day, typ, target = arg.split(':')
    bid, cc = target.split('/')
    req = urllib.request.Request(f'https://api.aelf.org/v1/messes/{day}/france', headers={'User-Agent': UA})
    j = json.load(urllib.request.urlopen(req, timeout=30))
    C = crampon(bid, int(cc)); CS = {v: stems(t) for v, t in C.items()}
    for m in j.get('messes') or []:
        for l in m.get('lectures') or []:
            if l.get('type') != typ: continue
            t = html.unescape(re.sub(r'<[^>]+>', '\n', l.get('contenu') or ''))
            sents = [s for s in re.split(r'(?<=[.;:!?»])\s+|\n+', t) if len(stems(s)) >= 3]
            out = []
            for k, s in enumerate(sents, 1):
                S = stems(s)
                sc = sorted(((len(S & CS[v]) / len(S) if S else 0, v) for v in CS), reverse=True)
                out.append(f'{k}→{sc[0][1]}({sc[0][0]:.2f}' + (f';{sc[1][1]}:{sc[1][0]:.2f}' if sc[1][0] > sc[0][0] * 0.7 else '') + ')')
            print(f'== {day} {typ} ({m.get("nom")}) {l.get("ref")} : {len(sents)} phrases -> Crampon {bid} {cc}')
            print('  ' + '  '.join(out))

def main():
    for arg in sys.argv[1:]:
        if arg.count(':') == 2:
            messe(arg); continue
        a, _, b = arg.partition(':')
        book, c = a.split('/')
        bid, cc = (b.split('/') if b else (book.lower(), c))
        try:
            A, how = aelf(book, int(c))
        except Exception as e:
            print(arg, 'ERREUR', e); continue
        C = crampon(bid, int(cc))
        CS = {v: stems(t) for v, t in C.items()}
        print(f'== AELF {book} {c} ({len(A)} versets) -> Crampon {bid} {cc} ({len(C)} versets)')
        line = []
        for n, t in A.items():
            S = stems(t)
            if len(S) < 3:
                line.append(f'{n}:-'); continue
            sc = sorted(((len(S & CS[v]) / len(S | CS[v]) if CS[v] else 0, v) for v in CS), reverse=True)
            best, second = sc[0], sc[1] if len(sc) > 1 else (0, None)
            line.append(f'{n}→{best[1]}({best[0]:.2f}' + (f';{second[1]}:{second[0]:.2f}' if second[0] > best[0] * 0.7 else '') + ')')
        print('  ' + '  '.join(line))

if __name__ == '__main__':
    main()
