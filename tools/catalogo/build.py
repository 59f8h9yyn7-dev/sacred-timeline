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


POI = {'amenity', 'tourism', 'historic', 'building', 'man_made', 'aeroway', 'leisure', 'office', 'shop', 'railway', 'bridge', 'military', 'highway'}


def prec_osm(r):
    rank = r.get('rank') or 0
    if rank >= 28 or r.get('cat') in POI or (r.get('cat') == 'natural' and r.get('tipo') in ('peak', 'volcano')):
        return 'e'
    return 'q' if rank >= 20 else 'c' if rank >= 13 else 'r'


def km(a, b, c, d):
    from math import radians, sin, cos, asin, sqrt
    a, b, c, d = map(radians, (a, b, c, d))
    return 12742 * asin(sqrt(sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2))


def posizioni(luoghi):
    """Mette in luoghi[k] lat, lon, precisione e fonte (8° campo). Restituisce le righe del rapporto."""
    gp = os.path.join(HERE, 'geo.txt')
    cache = json.load(open(os.path.join(HERE, 'geo-osm.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'geo-osm.json')) else {}
    geo, log, attesa = {}, [], []
    for n, raw in enumerate(open(gp, encoding='utf-8'), 1):
        s = raw.strip()
        if s and not s.startswith('#'):
            p = [x.strip() for x in s.split('|')]
            if p[0] not in luoghi:
                log.append(f'geo.txt:{n}: luogo sconosciuto {p[0]}')
            elif p[0] in geo:
                log.append(f'geo.txt:{n}: {p[0]} ripetuto')
            geo[p[0]] = p
    def risolvi(k, p):
        m = p[1]
        if m == '-':
            return None, None, '', 'Il film non dice dove: ' + p[2]
        if m == 'll':
            lat, lon = [float(v) for v in p[2].split(',')]
            return lat, lon, p[3] if p[3] != '-' else '', p[4] if len(p) > 4 else 'a mano'
        if m == 'q':
            for q in [x.strip() for x in p[2].split('||')]:
                r = cache.get(q)
                if r and r.get('trovato'):
                    fonte = p[3] if len(p) > 3 else ''
                    osm = 'OpenStreetMap: ' + r['nome'].split(',')[0]
                    return r['lat'], r['lon'], prec_osm(r), (fonte + ' · ' if fonte else '') + osm
            return 'attesa', None, '', ''
        if m == 'x':
            r = cache.get('x:' + p[2])
            if r and r.get('trovato'):
                return r['lat'], r['lon'], 'e', (p[4] if len(p) > 4 else '') + ' · OpenStreetMap: incrocio'
            q = p[2].split('&')[0].strip() + ', New York'
            r = cache.get(q)
            if r and r.get('trovato'):
                return r['lat'], r['lon'], 'q', (p[4] if len(p) > 4 else '') + ' · OpenStreetMap: ' + q
            return 'attesa', None, '', ''
        return 'rel', None, '', ''
    out = {}
    for k, p in geo.items():
        if p[1] != 'rel':
            out[k] = risolvi(k, p)
    for k, p in geo.items():
        if p[1] == 'rel':
            base = out.get(p[2])
            if base and isinstance(base[0], float):
                dlat, dlon = [float(v) for v in p[3].split(',')]
                out[k] = (round(base[0] + dlat, 6), round(base[1] + dlon, 6), 'q' if base[2] in ('e', 'q') else base[2] or 'r', p[4] if len(p) > 4 else 'vicino a ' + p[2])
            else:
                out[k] = ('attesa', None, '', '')
    for k, v in luoghi.items():
        old = (v[4], v[5])
        if k not in out:
            if v[3] in 'rmi':
                log.append(f'senza posizione in geo.txt: {k} ({v[0]})')
            v.append('stima' if v[4] is not None else '')
            continue
        lat, lon, prec, fonte = out[k]
        if lat == 'attesa':
            attesa.append(k)
            v.append('stima, in attesa di OpenStreetMap')
            continue
        if lat is not None and old[0] is not None:
            d = km(old[0], old[1], lat, lon)
            lim = {'e': 15, 'q': 25, 'c': 60}.get(prec, 400)
            if d > lim:
                log.append(f'CONTROLLA {k} ({v[0]}): {d:.0f} km dalla stima · {fonte}')
        v[4], v[5] = (round(lat, 6), round(lon, 6)) if lat is not None else (None, None)
        v[6] = prec if lat is not None else ''
        v.append(fonte)
    if attesa:
        log.append('in attesa di OpenStreetMap: ' + ', '.join(attesa))
    nterra = sum(1 for v in luoghi.values() if v[3] in 'rmix' and v[4] is not None)
    log.insert(0, f'{nterra} luoghi con posizione sulla Terra · ' + ' · '.join(f"{p}: {sum(1 for v in luoghi.values() if v[4] is not None and v[6] == p)}" for p in 'eqcr'))
    return log


def main():
    cards = json.load(open(os.path.join(ROOT, 'data', 'cards.json'), encoding='utf-8'))
    prods = {p[1]: p for p in cards['prods']}
    zone, luoghi, titoli, errs = [], {}, [], []
    cur = None
    for fn in sorted(f for f in os.listdir(HERE) if f.endswith('.txt') and f[:2].isdigit()):
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
    # voci confermate dall'utente nell'app
    conf = set()
    cp = os.path.join(HERE, 'confermate.lst')
    if os.path.exists(cp):
        conf = {l.strip() for l in open(cp, encoding='utf-8') if l.strip() and not l.startswith('#')}
    for t in titoli:
        for v in t[2]:
            if t[0] + '|' + v[0] in conf:
                v.append(1)
    # posizioni (geo.txt + risultati di OpenStreetMap in geo-osm.json)
    log = posizioni(luoghi)
    open(os.path.join(HERE, 'geo-log.txt'), 'w', encoding='utf-8').write('\n'.join(log) + '\n')
    # in ordine di uscita, come sulla mappa
    titoli.sort(key=lambda t: (prods[t[0]][2], t[0]))
    out = {
        'v': 2, 'stato': 'corretto', 'creato': datetime.date.today().isoformat(),
        'nota': "Luoghi del 616 titolo per titolo: bozza di Claude corretta dall'utente (novembre 2026). Le note che cominciano con '?' "
                "sono da verificare. luoghi[k] = [nome, dove, zona, tipo, lat, lon, precisione, fonte della posizione]; "
                "voci [k, nota, 1 se confermata]. Le correzioni fatte nell'app restano in map.json (cat616) finché non vengono riportate qui.",
        'tipi': TIPI, 'zone': zone, 'luoghi': luoghi, 'titoli': titoli,
    }
    dst = os.path.join(ROOT, 'data', 'catalogo616.json')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    nv = sum(len(t[2]) for t in titoli)
    dv = sum(1 for t in titoli for v in t[2] if v[1].startswith('?'))
    print(f'{len(titoli)} titoli · {len(luoghi)} luoghi · {nv} voci ({dv} da verificare) · {os.path.getsize(dst) // 1024} KB')
    print('\n'.join(l[:160] for l in log[:30]))
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
