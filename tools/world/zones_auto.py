#!/usr/bin/env python3
"""Mondo 616 — zone 3D automatiche dal catalogo dei luoghi (data/catalogo616.json).

Ogni luogo sulla Terra con un punto abbastanza preciso (edificio, quartiere, città; per le grandi città anche "regione")
finisce in una zona: i luoghi a meno di 1,6 km si uniscono, la zona è il loro rettangolo più 500 m di margine
(almeno 1,4 km di lato, al massimo ~3,6 km: oltre si divide). I luoghi già dentro le zone fatte a mano
(tools/world/zones.json, es. nyc616) restano a quelle.

Scrive tools/world/zones-auto.json, che build.py scarica da OpenStreetMap insieme a zones.json.
Si rilancia a mano quando il catalogo cambia:  python3 tools/world/zones_auto.py
L'id di una zona viene dal suo luogo principale: se il catalogo cambia poco, le zone già scaricate restano valide."""
import json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAT = os.path.join(ROOT, 'data', 'catalogo616.json')
MAN = os.path.join(ROOT, 'tools', 'world', 'zones.json')
GEO = os.path.join(ROOT, 'tools', 'catalogo', 'geo.txt')
OUT = os.path.join(ROOT, 'tools', 'world', 'zones-auto.json')

# grandi città che OpenStreetMap restituisce come "regione" (città-stato, capitali con confine amministrativo largo)
CITY_Q = {'London, United Kingdom', 'Berlin, Germany', 'Prague, Czech Republic', 'Seoul, South Korea', 'Bucharest, Romania',
          'Busan, South Korea', 'Hong Kong', 'Mexico City', 'Moscow, Russia', 'Tokyo, Japan', 'Karachi, Pakistan',
          'Port-au-Prince, Haiti', 'Riga, Latvia', 'Baltimore, Maryland', 'San Francisco, California', 'San Juan, Puerto Rico'}
PREC = {'e': 0, 'q': 1, 'c': 2, 'r': 3}
LINK_KM, MARGIN_KM, MIN_KM, MAX_KM = 1.6, 0.5, 1.4, 3.6

# nomi delle zone (per id); le altre prendono il nome del loro luogo principale
NAMES = {
    'z-disney-hall': 'Los Angeles · Downtown',
    'z-alias': "New York · Hell's Kitchen e Columbus Circle",
    'z-lombard': 'San Francisco · centro, Russian Hill e il porto',
    'z-jane-londra': 'Londra · Trafalgar Square e Westminster',
    'z-casa-bianca': 'Washington · la Casa Bianca e il Mall',
    'z-city-hall': 'New York · Civic Center e Chinatown',
    'z-chinese-theatre': 'Los Angeles · Hollywood',
    'z-brooklyn-40': 'New York · Brooklyn, Flatbush',
    'z-campidoglio': 'Washington · Capitol Hill e il Mall',
    'z-berlino-ctc': 'Berlino · Mitte',
    'z-chicago-marc': 'Chicago · il Loop e Grant Park',
    'z-cimitero-may': 'New York · Queens, Forest Hills',
    'z-harlem-125': 'New York · Harlem',
    'z-agatha-casa': 'Westview · Lawrenceville, New Jersey',
    'z-bacon-casa': 'Los Angeles · Beverly Hills',
    'z-coles': 'Jersey City',
    'z-coney-island': 'New York · Coney Island e Brighton Beach',
    'z-mosca': 'Mosca · il centro',
    'z-northern-star': 'New York · Red Hook e il porto',
    'z-nuova-asgard': 'Nuova Asgard · Tønsberg, Norvegia',
    'z-tenochtitlan': 'Città del Messico · centro storico (Tenochtitlan)',
}


def km(a, b):
    return math.hypot((b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2)) * 111.32, (b[0] - a[0]) * 110.57)


def geo_queries():
    """chiave → ricerca Nominatim (la prima alternativa), seguendo i 'rel'."""
    q, rel = {}, {}
    for ln in open(GEO, encoding='utf-8'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        p = [x.strip() for x in ln.split('|')]
        if len(p) >= 3 and p[1] == 'q':
            q[p[0]] = p[2]
        elif len(p) >= 3 and p[1] == 'rel':
            rel[p[0]] = p[2]
    for k, o in rel.items():
        seen = set()
        while o in rel and o not in seen:
            seen.add(o); o = rel[o]
        if o in q:
            q[k] = q[o]
    return q


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    man = json.load(open(MAN, encoding='utf-8'))
    gq = geo_queries()
    shrink = 0.0012  # ~120 m: un luogo proprio sul bordo di una zona a mano merita la sua
    inman = lambda la, lo: any(r[0] + shrink < la < r[2] - shrink and r[1] + shrink < lo < r[3] - shrink for Z in man['zones'] for r in Z['rects'])
    pts = []
    for k, v in cat['luoghi'].items():
        nome, dove, zona, tipo, la, lo, pr = v[:7]
        if tipo not in 'rmi' or la is None:
            continue
        if pr == 'r' and gq.get(k) not in CITY_Q:
            continue
        if pr not in PREC:
            continue
        if inman(la, lo):
            continue
        pts.append({'k': k, 'll': (la, lo), 'pr': pr, 'tipo': tipo, 'nome': nome, 'dove': dove})
    # legame singolo a 1,6 km
    groups = []
    for p in pts:
        hit = [g for g in groups if any(km(p['ll'], q['ll']) < LINK_KM for q in g)]
        if hit:
            m = hit[0]
            for h in hit[1:]:
                m += h; groups.remove(h)
            m.append(p)
        else:
            groups.append([p])

    def ext(g):
        la = [p['ll'][0] for p in g]; lo = [p['ll'][1] for p in g]
        s, n, w, e = min(la), max(la), min(lo), max(lo)
        return s, w, n, e, km((s, w), (s, e)), km((s, w), (n, w))

    def split(g):
        s, w, n, e, wk, hk = ext(g)
        if (wk + 2 * MARGIN_KM <= MAX_KM and hk + 2 * MARGIN_KM <= MAX_KM) or len(g) < 2:
            return [g]
        ax = 1 if wk >= hk else 0
        g = sorted(g, key=lambda p: p['ll'][ax])
        gaps = [(g[i + 1]['ll'][ax] - g[i]['ll'][ax], i) for i in range(len(g) - 1)]
        mid = [t for t in gaps if len(g) / 4 <= t[1] + 1 <= len(g) * 3 / 4] or gaps  # il buco più largo, ma non ai margini
        i = max(mid)[1]
        return split(g[:i + 1]) + split(g[i + 1:])

    zl = []
    for g in groups:
        zl += split(g)
    zones, used = [], set()
    for g in zl:
        s, w, n, e, wk, hk = ext(g)
        la0, lo0 = (s + n) / 2, (w + e) / 2
        kx = 111.32 * math.cos(math.radians(la0))
        hw = max(MIN_KM, wk + 2 * MARGIN_KM) / 2 / kx
        hh = max(MIN_KM, hk + 2 * MARGIN_KM) / 2 / 110.57
        rect = [round(la0 - hh, 5), round(lo0 - hw, 5), round(la0 + hh, 5), round(lo0 + hw, 5)]
        g.sort(key=lambda p: (PREC[p['pr']], p['k']))
        anc = g[0]
        zid = 'z-' + anc['k']
        while zid in used:
            zid += '-2'
        used.add(zid)
        name = NAMES.get(zid)
        if not name:
            d = re.sub(r'\s*\([^)]*\)', '', anc['dove']).strip()
            name = anc['nome'] if (not d or d.lower() in anc['nome'].lower()) else f"{anc['nome']} · {d}"
            if len(name) > 64:
                name = name[:62].rstrip(' ,·') + '…'
        marks = []
        for p in sorted(g, key=lambda p: p['k']):
            mode = 'highlight' if p['pr'] == 'e' and p['tipo'] in 'rm' else 'ground'
            marks.append({'k': p['k'], 'mode': mode, 'll': [round(p['ll'][0], 6), round(p['ll'][1], 6)]})
        zones.append({'id': zid, 'v': 1, 'name': name, 'auto': 1, 'n': len(g), 'rects': [rect], 'marks': marks})
    # le più ricche (e New York) per prime: l'Action le scarica in quest'ordine
    zones.sort(key=lambda z: (-z['n'], z['id']))
    out = {'_nota': 'Generato da tools/world/zones_auto.py dal catalogo dei luoghi: non modificare a mano (i nomi stanno in NAMES). Rettangoli in [sud, ovest, nord, est].',
           'zones': zones}
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('{\n  "_nota": ' + json.dumps(out['_nota'], ensure_ascii=False) + ',\n  "zones": [\n')
        f.write(',\n'.join('    ' + json.dumps(z, ensure_ascii=False, separators=(',', ':')) for z in zones))
        f.write('\n  ]\n}\n')
    area = sum((z['rects'][0][2] - z['rects'][0][0]) * 110.57 * (z['rects'][0][3] - z['rects'][0][1]) * 111.32 * math.cos(math.radians(z['rects'][0][0])) for z in zones)
    print(f'{len(zones)} zone, {sum(z["n"] for z in zones)} luoghi, {area:.0f} km² in tutto')
    for z in zones:
        print(f"  {z['id']:28s} {z['n']:3d}  {z['name']}")


if __name__ == '__main__':
    main()
