#!/usr/bin/env python3
"""Catalogo dei luoghi del Mondo 616: legge tools/catalogo/*.txt e scrive data/catalogo616.json.

Formato delle righe: vedi l'intestazione di 01-zone.txt. Controlla che i titoli esistano in data/cards.json,
che ogni luogo sia definito una volta sola e che le zone esistano.
Uso: python3 tools/catalogo/build.py
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TIPI = {'r': 'Luogo reale', 'm': 'Reale, con elementi Marvel', 'i': 'Inventato sulla Terra',
        's': 'Fuori dalla Terra', 'd': 'Altra dimensione', 'x': 'Base mobile o astronave'}
PREC = {'e', 'q', 'c', 'r', '-'}


def main():
    cards = json.load(open(os.path.join(ROOT, 'data', 'cards.json'), encoding='utf-8'))
    prods = {p[1]: p for p in cards['prods']}
    zone, luoghi, titoli, errs = [], {}, [], []
    cur = None
    for fn in sorted(f for f in os.listdir(HERE) if f.endswith('.txt')):
        for n, raw in enumerate(open(os.path.join(HERE, fn), encoding='utf-8'), 1):
            line = raw.strip()
            where = f'{fn}:{n}'
            if not line or line.startswith('#'):
                continue
            if line.startswith('Z '):
                k, nome, area = [s.strip() for s in line[2:].split('|')]
                zone.append([k, nome, area])
                continue
            if line.startswith('== '):
                t = line[3:].strip()
                if t not in prods:
                    errs.append(f'{where}: titolo sconosciuto {t!r}')
                if any(x[0] == t for x in titoli):
                    errs.append(f'{where}: titolo ripetuto {t!r}')
                cur = [t, '', []]
                titoli.append(cur)
                continue
            if line.startswith('! '):
                cur[1] = line[2:].strip()
                continue
            parts = [s.strip() for s in line.split('|')]
            if parts[0].startswith('+'):
                if len(parts) != 8:
                    errs.append(f'{where}: un luogo nuovo vuole 8 campi, ne ha {len(parts)}')
                    continue
                k, nome, dove, z, tipo, ll, prec, nota = parts
                k = k[1:]
                if k in luoghi:
                    errs.append(f'{where}: luogo {k!r} già definito')
                if tipo not in TIPI:
                    errs.append(f'{where}: tipo {tipo!r}')
                if prec not in PREC:
                    errs.append(f'{where}: precisione {prec!r}')
                lat = lon = None
                if ll != '-':
                    try:
                        lat, lon = [float(v) for v in ll.split(',')]
                        assert -90 <= lat <= 90 and -180 <= lon <= 180
                    except Exception:
                        errs.append(f'{where}: coordinate {ll!r}')
                luoghi[k] = [nome, dove, z, tipo, lat, lon, '' if prec == '-' else prec]
            else:
                if len(parts) != 2:
                    errs.append(f'{where}: una voce vuole "chiave | nota", trovati {len(parts)} campi')
                    continue
                k, nota = parts
            if cur is None:
                errs.append(f'{where}: voce fuori da un titolo')
                continue
            if any(v[0] == k for v in cur[2]):
                errs.append(f'{where}: {k!r} ripetuto nello stesso titolo')
            cur[2].append([k, nota])
    zk = {z[0] for z in zone}
    for k, p in luoghi.items():
        if p[2] not in zk:
            errs.append(f'luogo {k!r}: zona {p[2]!r} inesistente')
    for t in titoli:
        for k, _ in t[2]:
            if k not in luoghi:
                errs.append(f'{t[0]}: luogo {k!r} mai definito')
    if errs:
        print('\n'.join(errs))
        sys.exit(1)
    # in ordine di uscita, come sulla mappa
    titoli.sort(key=lambda t: (prods[t[0]][2], t[0]))
    out = {
        'v': 1, 'stato': 'bozza', 'creato': datetime.date.today().isoformat(),
        'nota': "Bozza di Claude dei luoghi del 616, titolo per titolo. Le note che cominciano con '?' sono da verificare. "
                "Le correzioni fatte nell'app restano in map.json (cat616) finché non vengono riportate qui.",
        'tipi': TIPI, 'zone': zone, 'luoghi': luoghi, 'titoli': titoli,
    }
    dst = os.path.join(ROOT, 'data', 'catalogo616.json')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    nv = sum(len(t[2]) for t in titoli)
    dv = sum(1 for t in titoli for v in t[2] if v[1].startswith('?'))
    print(f'{len(titoli)} titoli · {len(luoghi)} luoghi · {nv} voci ({dv} da verificare) · {os.path.getsize(dst) // 1024} KB')
    # titoli del ramo 616 rimasti fuori (per controllo)
    by = {}
    for c in cards['cards']:
        if c.get('uc') == '616' and (c.get('k') or 'sl') == 'sl':
            for a in c.get('ap', []):
                by[a[0]] = by.get(a[0], 0) + 1
    have = {t[0] for t in titoli}
    miss = [cards['prods'][i][1] for i in sorted(by) if by[i] >= 3 and cards['prods'][i][1] not in have]
    if miss:
        print('Titoli con personaggi del 616 non in catalogo:', ', '.join(miss))


if __name__ == '__main__':
    main()
