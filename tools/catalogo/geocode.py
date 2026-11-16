#!/usr/bin/env python3
"""Posizioni dei luoghi del catalogo 616: legge geo.txt, chiede a OpenStreetMap (Nominatim per le ricerche,
Overpass per gli incroci) solo ciò che non è già in geo-osm.json, e aggiorna quel file.
Gira nella Action "Catalogo 616 - posizioni" (il sandbox non ha internet). Rispetta la policy di Nominatim:
una richiesta al secondo, User-Agent riconoscibile, risultati salvati per non richiederli più.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'geo-osm.json')
UA = 'sacred-timeline/1.0 (app personale; https://github.com/59f8h9yyn7-dev/sacred-timeline)'
OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
            'https://overpass.private.coffee/api/interpreter']


def righe():
    for n, raw in enumerate(open(os.path.join(HERE, 'geo.txt'), encoding='utf-8'), 1):
        s = raw.strip()
        if s and not s.startswith('#'):
            yield n, [p.strip() for p in re.split(r'(?<!\|)\|(?!\|)', s)]


def get(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept-Language': 'it,en'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


last = [0.0]


def nominatim(q):
    wait = 1.15 - (time.time() - last[0])
    if wait > 0:
        time.sleep(wait)
    last[0] = time.time()
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'limit': 1})
    for attempt in range(3):
        try:
            res = get(url)
            break
        except Exception as e:
            print('  errore', q, e)
            time.sleep(5 * (attempt + 1))
    else:
        return None
    if not res:
        return {'q': q, 'trovato': False}
    r = res[0]
    return {'q': q, 'trovato': True, 'lat': float(r['lat']), 'lon': float(r['lon']), 'nome': r.get('display_name', ''),
            'cat': r.get('category', ''), 'tipo': r.get('type', ''), 'rank': r.get('place_rank', 0),
            'bbox': [float(v) for v in r.get('boundingbox', [])], 'osm': f"{r.get('osm_type', '')}/{r.get('osm_id', '')}"}


def incrocio(spec, bbox):
    a, b = [s.strip() for s in spec.split('&')]
    s, w, n, e = bbox
    q = f'''[out:json][timeout:60];
way["name"="{a}"]({s},{w},{n},{e})->.a; way["name"="{b}"]({s},{w},{n},{e})->.b;
node(w.a)->.na; node(w.b)->.nb; node.na.nb; out;'''
    for ep in OVERPASS:
        try:
            res = get(ep, data=urllib.parse.urlencode({'data': q}).encode(), timeout=120)
            els = res.get('elements', [])
            if not els:
                return {'q': spec, 'trovato': False}
            lat = sum(x['lat'] for x in els) / len(els)
            lon = sum(x['lon'] for x in els) / len(els)
            return {'q': spec, 'trovato': True, 'lat': lat, 'lon': lon, 'nome': f'{a} & {b}', 'cat': 'highway',
                    'tipo': 'incrocio', 'rank': 30, 'bbox': [], 'osm': f"node/{els[0]['id']}"}
        except Exception as e:
            print('  overpass', ep, e)
            time.sleep(5)
    return None


def main():
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    nuove = 0
    for n, p in righe():
        if len(p) < 3:
            continue
        k, m = p[0], p[1]
        if m == 'q':
            for q in [s.strip() for s in p[2].split('||')]:
                if q not in cache:
                    r = nominatim(q)
                    if r is None:
                        continue
                    cache[q] = r
                    nuove += 1
                    print(('ok  ' if r['trovato'] else 'NO  ') + q + ('  →  ' + r['nome'][:90] if r['trovato'] else ''))
                if cache[q].get('trovato'):
                    break
        elif m == 'x':
            key = 'x:' + p[2]
            if key not in cache:
                r = incrocio(p[2], [float(v) for v in p[3].split(',')])
                if r is not None:
                    cache[key] = r
                    nuove += 1
                    print(('ok  ' if r['trovato'] else 'NO  ') + key)
            if not cache.get(key, {}).get('trovato'):
                # di riserva: la prima delle due strade
                q = p[2].split('&')[0].strip() + ', New York'
                if q not in cache:
                    r = nominatim(q)
                    if r:
                        cache[q] = r
                        nuove += 1
    with open(CACHE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(cache, ensure_ascii=False, separators=(',', ':'), sort_keys=True))
    print(f'{nuove} richieste nuove, {len(cache)} in memoria')


if __name__ == '__main__':
    main()
