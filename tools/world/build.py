#!/usr/bin/env python3
"""Mondo 616 — scarica le zone di tools/world/zones.json da OpenStreetMap (Overpass)
e le scrive compatte in data/world/ per l'app (edifici con altezze vere, strade, acqua, verde, quartieri).
Gira in una GitHub Action (serve internet e shapely). Dati © OpenStreetMap contributors, licenza ODbL."""
import json, math, os, re, sys, time, traceback, urllib.request, urllib.parse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'world')
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


EPS = ['https://overpass-api.de/api/interpreter',
       'https://overpass.kumi.systems/api/interpreter',
       'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
       'https://overpass.private.coffee/api/interpreter']


def overpass(q, label, start=0):
    data = urllib.parse.urlencode({'data': q}).encode()
    last = None
    for attempt in range(3):
        for j in range(len(EPS)):
            ep = EPS[(start + j + attempt) % len(EPS)]
            host = ep.split('/')[2]
            try:
                t0 = time.time()
                req = urllib.request.Request(ep, data=data, headers={'User-Agent': 'sacred-timeline-world/1 (app personale, una tantum)'})
                with urllib.request.urlopen(req, timeout=330) as r:
                    raw = r.read()
                j_ = json.loads(raw)
                rem = j_.get('remark') or ''
                if 'error' in rem.lower():
                    raise RuntimeError(rem[:200])
                els = j_.get('elements', [])
                log(f'  {label}: {len(els)} elementi da {host} in {time.time() - t0:.0f}s ({len(raw) // 1024} KB)')
                return els
            except Exception as e:
                last = e
                log(f'  {label}: {host} non risponde bene dopo {time.time() - t0:.0f}s ({str(e)[:140]})')
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f'{label}: nessun server Overpass ha risposto ({last})')


class Proj:
    """Piano locale attorno al centro della zona: x verso est, z verso sud (in three.js il nord è -z), in metri."""
    def __init__(s, lat0, lon0):
        f = math.radians(lat0)
        s.lat0, s.lon0 = lat0, lon0
        s.kz = 111132.954 - 559.822 * math.cos(2 * f) + 1.175 * math.cos(4 * f)
        s.kx = 111412.84 * math.cos(f) - 93.5 * math.cos(3 * f)

    def __call__(s, lat, lon):
        return ((lon - s.lon0) * s.kx, -(lat - s.lat0) * s.kz)


def num(v):
    if v is None:
        return None
    m = re.match(r'^\s*(-?[0-9]+(?:[.,][0-9]+)?)', str(v))
    return float(m.group(1).replace(',', '.')) if m else None


def length(v):
    """Altezze OSM: metri di solito, a volte piedi (12', 40 ft)."""
    if v is None:
        return None
    s = str(v).strip().lower()
    n = num(s)
    if n is None:
        return None
    if "'" in s or 'ft' in s or 'feet' in s:
        n *= 0.3048
    return n


def main():
    from shapely.geometry import Polygon, LineString, Point, MultiPolygon, GeometryCollection, box
    from shapely.ops import unary_union, polygonize, nearest_points
    from shapely.prepared import prep
    try:
        from shapely.validation import make_valid
    except Exception:
        make_valid = lambda g: g.buffer(0)

    def polys(g):
        if g is None or g.is_empty:
            return []
        if isinstance(g, Polygon):
            return [g]
        if hasattr(g, 'geoms'):
            out = []
            for x in g.geoms:
                out += polys(x)
            return out
        return []

    def lines(g):
        if g is None or g.is_empty:
            return []
        if isinstance(g, LineString):
            return [g]
        if hasattr(g, 'geoms'):
            out = []
            for x in g.geoms:
                out += lines(x)
            return out
        return []

    def fix(p):
        try:
            if not p.is_valid:
                p = make_valid(p)
            return p
        except Exception:
            return None

    def way_pts(el, P):
        return [P(g['lat'], g['lon']) for g in (el.get('geometry') or []) if g]

    def area_geom(el, P):
        """Poligono di una way chiusa o di una relazione multipolygon (out geom)."""
        if el['type'] == 'way':
            pts = way_pts(el, P)
            if len(pts) < 4:
                return None
            if pts[0] != pts[-1]:
                nd = el.get('nodes') or []
                if not nd or nd[0] != nd[-1]:
                    return None
            return fix(Polygon(pts))
        outers, inners = [], []
        for m in el.get('members', []):
            if m.get('type') != 'way' or not m.get('geometry'):
                continue
            pts = [P(g['lat'], g['lon']) for g in m['geometry'] if g]
            if len(pts) < 2:
                continue
            (inners if m.get('role') == 'inner' else outers).append(LineString(pts))
        if not outers:
            return None
        po = [fix(p) for p in polygonize(unary_union(outers))]
        po = [p for p in po if p is not None and not p.is_empty]
        if not po:
            return None
        g = unary_union(po)
        if inners:
            pi = [fix(p) for p in polygonize(unary_union(inners))]
            pi = [p for p in pi if p is not None and not p.is_empty]
            if pi:
                g = g.difference(unary_union(pi))
        return g

    def q(v):
        return int(round(v * 10))

    def enc(coords, closed):
        pts = list(coords)
        if closed and len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        out, px, pz = [], None, None
        for x, z in pts:
            X, Z = q(x), q(z)
            if px is None:
                out += [X, Z]
            else:
                dx, dz = X - px, Z - pz
                if dx == 0 and dz == 0:
                    continue
                out += [dx, dz]
            px, pz = X, Z
        return out

    def enc_poly(p):
        r = [enc(p.exterior.coords, True)]
        for h in p.interiors:
            e = enc(h.coords, True)
            if len(e) >= 6:
                r.append(e)
        return r if len(r[0]) >= 6 else None

    cfg = json.load(open(os.path.join(ROOT, 'tools', 'world', 'zones.json')))
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, 'index.json')
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {'zones': {}}

    for Z in cfg['zones']:
        zid, ver = Z['id'], Z.get('v', 1)
        fname = f'{zid}-v{ver}.json'
        log(f'== zona {zid} (v{ver}) ==')
        rects = Z['rects']
        S = min(r[0] for r in rects); W = min(r[1] for r in rects); N = max(r[2] for r in rects); E = max(r[3] for r in rects)
        lat0, lon0 = (S + N) / 2, (W + E) / 2
        P = Proj(lat0, lon0)
        lrects = []
        for s_, w_, n_, e_ in rects:
            x0, z1 = P(s_, w_); x1, z0 = P(n_, e_)
            lrects.append([round(min(x0, x1), 1), round(min(z0, z1), 1), round(max(x0, x1), 1), round(max(z0, z1), 1)])
        zone = unary_union([box(*r) for r in lrects])
        zp = prep(zone)
        bb = lambda r: f'{r[0]},{r[1]},{r[2]},{r[3]}'
        big = [S - 0.01, W - 0.01, N + 0.01, E + 0.01]

        # ---- scarico (in parallelo: ogni richiesta su un server diverso) ----
        from concurrent.futures import ThreadPoolExecutor
        Q = {}
        for i, r in enumerate(rects):
            Q[f'edifici {i + 1}'] = f'[out:json][timeout:300];(way["building"]({bb(r)});relation["building"]["type"="multipolygon"]({bb(r)}););out tags geom;'
            Q[f'strade {i + 1}'] = f'[out:json][timeout:240];(way["highway"]({bb(r)});way["railway"~"^(subway|rail|light_rail|monorail)$"]({bb(r)}););out tags geom;'
            Q[f'verde {i + 1}'] = f'[out:json][timeout:240];(way["leisure"~"^(park|garden|playground|pitch|dog_park|common|recreation_ground|nature_reserve)$"]({bb(r)});relation["leisure"~"^(park|garden|playground|pitch|common|recreation_ground|nature_reserve)$"]({bb(r)});way["landuse"~"^(grass|recreation_ground|cemetery|village_green|meadow|forest)$"]({bb(r)});relation["landuse"~"^(grass|recreation_ground|cemetery|village_green|meadow|forest)$"]({bb(r)});way["natural"~"^(wood|scrub|grassland|heath)$"]({bb(r)}););out tags geom;'
        Q['acqua'] = f'[out:json][timeout:240];(way["natural"="water"]({bb(big)});relation["natural"="water"]({bb(big)});way["waterway"="riverbank"]({bb(big)});relation["waterway"="riverbank"]({bb(big)}););out tags geom;'
        Q['costa'] = f'[out:json][timeout:180];way["natural"="coastline"]({bb(big)});out geom;'
        Q['quartieri'] = f'[out:json][timeout:120];node["place"~"^(neighbourhood|suburb|quarter|borough)$"]["name"]({bb([S, W, N, E])});out;'
        Q['distretti'] = f'[out:json][timeout:240];relation["boundary"="administrative"]["admin_level"~"^(5|6)$"]({bb([S, W, N, E])});out tags geom;'
        aq = ''.join(f'nwr["addr:housenumber"="{m["addr"][0]}"]["addr:street"="{m["addr"][1]}"]({bb(big)});' for m in Z.get('marks', []) if m.get('addr'))
        if aq:
            Q['indirizzi'] = f'[out:json][timeout:120];({aq});out tags center;'
        optional = {'distretti', 'indirizzi'}
        res = {}
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {k: ex.submit(overpass, q, k, n) for n, (k, q) in enumerate(Q.items())}
            for k, f in futs.items():
                try:
                    res[k] = f.result()
                except Exception as e:
                    if k in optional:
                        log(f'  {k}: niente ({str(e)[:100]})'); res[k] = []
                    else:
                        raise
        bels, rels_, gels = {}, {}, {}
        for i in range(len(rects)):
            for el in res[f'edifici {i + 1}']:
                bels[(el['type'], el['id'])] = el
            for el in res[f'strade {i + 1}']:
                rels_[(el['type'], el['id'])] = el
            for el in res[f'verde {i + 1}']:
                gels[(el['type'], el['id'])] = el
        wels, cels, nels, bor, aels = res['acqua'], res['costa'], res['quartieri'], res['distretti'], res.get('indirizzi', [])

        # ---- edifici ----
        B = []
        skipped = 0
        for el in bels.values():
            t = el.get('tags', {})
            if t.get('building') in ('roof', 'no', 'construction', 'demolished', 'proposed') or t.get('location') == 'underground':
                skipped += 1; continue
            if num(t.get('layer')) is not None and num(t.get('layer')) < 0:
                skipped += 1; continue
            try:
                g = area_geom(el, P)
            except Exception:
                g = None
            if g is None:
                skipped += 1; continue
            h = length(t.get('height'))
            lv = num(t.get('building:levels'))
            if h is None and lv is not None:
                h = lv * 3.2 + 1.5
            if h is None:
                h = {'house': 8, 'detached': 8, 'semidetached_house': 8, 'terrace': 9, 'garage': 3, 'garages': 3, 'shed': 3, 'kiosk': 3, 'hut': 3, 'carport': 3}.get(t.get('building'), 10)
            mh = length(t.get('min_height'))
            ml = num(t.get('building:min_level'))
            if mh is None and ml is not None:
                mh = ml * 3.2
            h = max(2.5, min(h, 600.0)); mh = max(0.0, min(mh or 0.0, h - 1.0))
            for p in polys(g):
                if p.area < 6:
                    continue
                c = p.representative_point()
                if not zp.contains(c):
                    continue
                p2 = p.simplify(0.35, preserve_topology=True)
                if p2.is_empty or not isinstance(p2, Polygon):
                    p2 = p
                B.append({'p': p2, 'h': h, 'mh': mh, 't': t, 'id': f"{el['type'][0]}{el['id']}", 'c': c})
        log(f'  edifici tenuti: {len(B)} (scartati {skipped})')

        # ---- strade, ponti, binari sopraelevati ----
        RC = {'motorway': 0, 'trunk': 0, 'motorway_link': 0, 'trunk_link': 0, 'primary': 1, 'primary_link': 1, 'secondary': 2, 'secondary_link': 2,
              'tertiary': 3, 'tertiary_link': 3, 'residential': 4, 'unclassified': 4, 'living_street': 4, 'road': 4, 'service': 5, 'pedestrian': 6,
              'footway': 7, 'path': 7, 'cycleway': 7, 'bridleway': 7, 'track': 7}
        R, EL, named = [], [], {}
        for el in rels_.values():
            t = el.get('tags', {})
            pts = way_pts(el, P)
            if len(pts) < 2:
                continue
            try:
                ln = LineString(pts)
            except Exception:
                continue
            if 'highway' in t:
                hw = t['highway']
                if hw not in RC or t.get('area') == 'yes' or t.get('indoor') == 'yes':
                    continue
                if t.get('tunnel') not in (None, 'no', 'building_passage'):
                    continue
                if t.get('footway') in ('sidewalk', 'crossing', 'traffic_island') or t.get('path') == 'sidewalk':
                    continue
                lay = num(t.get('layer')) or 0
                if lay < 0:
                    continue
                if t.get('name'):
                    named.setdefault(t['name'].lower(), []).append(ln)
                br = 0
                if t.get('bridge') not in (None, 'no'):
                    br = int(max(1, min(lay or 1, 9)))
                    if ln.length > 450 and RC[hw] <= 3:
                        br = 9  # grande ponte sul fiume
                for part in lines(ln.intersection(zone)):
                    s = part.simplify(0.8, preserve_topology=False)
                    e = enc(s.coords, False)
                    if len(e) >= 4:
                        R.append([RC[hw] + 16 * br] + e)
            elif t.get('railway'):
                if t.get('tunnel') not in (None, 'no'):
                    continue
                lay = num(t.get('layer')) or 0
                if t.get('bridge') in (None, 'no') and lay < 1 and t.get('embankment') != 'yes':
                    continue
                for part in lines(ln.intersection(zone)):
                    e = enc(part.simplify(0.8, preserve_topology=False).coords, False)
                    if len(e) >= 4:
                        EL.append(e)
        log(f'  strade: {len(R)} tratti, binari sopraelevati: {len(EL)}')

        # ---- acqua: la costa divide la zona in pezzi, la terra sta a sinistra della linea di costa (in lat/lon) ----
        water = []
        try:
            coast = []
            for el in cels:
                pts = way_pts(el, P)
                if len(pts) >= 2:
                    coast.append(pts)
            if coast:
                cl = []
                for pts in coast:
                    cl += lines(LineString(pts).intersection(zone))
                net = unary_union([zone.boundary] + cl)
                pieces = [p for p in polygonize(net) if p.area > 1]
                pp = [prep(p) for p in pieces]
                votes = [0] * len(pieces)
                for pts in coast:
                    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
                        dx, dz = x1 - x0, z1 - z0
                        L = math.hypot(dx, dz)
                        if L < 0.5:
                            continue
                        mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
                        if not zp.contains(Point(mx, mz)):
                            continue
                        nx, nz = dz / L * 0.4, -dx / L * 0.4  # in x/z (z verso sud) la terra è da questa parte
                        a, b = Point(mx + nx, mz + nz), Point(mx - nx, mz - nz)
                        for i, p in enumerate(pp):
                            if p.contains(a):
                                votes[i] += 1
                            if p.contains(b):
                                votes[i] -= 1
                wat = [pieces[i] for i in range(len(pieces)) if votes[i] < 0]
                log(f'  costa: {len(coast)} linee, {len(pieces)} pezzi, acqua in {len(wat)} ({sum(p.area for p in wat) / 1e6:.2f} km²)')
                water += wat
        except Exception as e:
            log('  costa: errore ' + str(e)[:200]); log(traceback.format_exc()[-800:])
        nw = 0
        for el in wels:
            t = el.get('tags', {})
            if t.get('covered') == 'yes' or t.get('tunnel') not in (None, 'no') or t.get('intermittent') == 'yes':
                continue
            try:
                g = area_geom(el, P)
                if g is None:
                    continue
                g = g.intersection(zone)
            except Exception:
                continue
            for p in polys(g):
                water.append(p); nw += 1
        log(f'  specchi d\'acqua: {nw}')
        Wout = []
        if water:
            wl = [fix(p) for p in water if p is not None]
            try:
                wu = unary_union(wl)
            except Exception:
                wu = unary_union([p.buffer(0) for p in wl if p is not None])
            wu = wu.simplify(2.0, preserve_topology=True)
            for p in polys(wu):
                if p.area < 40:
                    continue
                e = enc_poly(p)
                if e:
                    Wout.append(e)
            wprep = prep(wu)
        else:
            wprep = None

        # ---- verde ----
        G = []
        for el in gels.values():
            try:
                g = area_geom(el, P)
                if g is not None:
                    G += polys(g.intersection(zone))
            except Exception:
                pass
        Gout = []
        if G:
            gl = [fix(p) for p in G if p is not None and p.area > 15]
            try:
                gu = unary_union(gl)
            except Exception:
                gu = unary_union([p.buffer(0) for p in gl if p is not None])
            gu = gu.simplify(1.2, preserve_topology=True)
            for p in polys(gu):
                if p.area < 25:
                    continue
                e = enc_poly(p)
                if e:
                    Gout.append(e)
        log(f'  verde: {len(Gout)} aree')

        # ---- distretti e quartieri ----
        boro = []
        for el in bor:
            t = el.get('tags', {})
            nm = (t.get('name') or '') + ' ' + (t.get('official_name') or '') + ' ' + (t.get('alt_name') or '')
            name = 'Manhattan' if ('Manhattan' in nm or 'New York County' in nm) else 'Queens' if 'Queens' in nm else 'Brooklyn' if ('Brooklyn' in nm or 'Kings County' in nm) else 'The Bronx' if 'Bronx' in nm else None
            if not name:
                continue
            try:
                g = area_geom(el, P)
                if g is not None and not g.is_empty:
                    boro.append((name, prep(g)))
            except Exception:
                pass
        log(f'  distretti: {[b[0] for b in boro]}')
        Nout = []
        for el in nels:
            t = el.get('tags', {})
            x, z = P(el['lat'], el['lon'])
            if not zp.contains(Point(x, z)):
                continue
            bn = ''
            for name, g in boro:
                if g.contains(Point(x, z)):
                    bn = name; break
            nm = t.get('name')
            if t.get('place') == 'borough':
                continue
            Nout.append([nm, round(x, 1), round(z, 1), bn, t.get('place')])
        log(f'  quartieri: {len(Nout)} → ' + ', '.join(n[0] for n in Nout)[:900])

        # ---- luoghi Marvel: l'edificio vero da evidenziare o da sostituire ----
        addr_pts = {}
        for el in aels:
            t = el.get('tags', {})
            c = el.get('center') or ({'lat': el['lat'], 'lon': el['lon']} if 'lat' in el else None)
            if not c:
                continue
            addr_pts.setdefault((t.get('addr:housenumber'), (t.get('addr:street') or '').lower()), []).append(P(c['lat'], c['lon']))
        remove = set()
        marks = {}
        for m in Z.get('marks', []):
            x, z = P(*m['ll'])
            pt = Point(x, z)
            hit, how = None, ''
            if m.get('addr'):
                hn, st = m['addr'][0], m['addr'][1].lower()
                cands = [b for b in B if b['t'].get('addr:housenumber') == hn and (b['t'].get('addr:street') or '').lower() == st]
                if cands:
                    hit = min(cands, key=lambda b: b['c'].distance(pt)); how = 'indirizzo sull\'edificio'
                if hit is None:
                    for ap in addr_pts.get((hn, st), []):
                        a = Point(*ap)
                        inside = [b for b in B if b['p'].contains(a)]
                        if inside:
                            hit = min(inside, key=lambda b: b['p'].area); how = 'nodo indirizzo'; break
                if hit is not None and hit['c'].distance(pt) > 600:
                    log(f'  {m["k"]}: indirizzo trovato troppo lontano ({hit["c"].distance(pt):.0f} m), lo ignoro'); hit = None
            if hit is None and m.get('names'):
                cands = [b for b in B if b['t'].get('name') in m['names']]
                if cands:
                    hit = min(cands, key=lambda b: b['c'].distance(pt)); how = 'nome'
            if hit is None:
                inside = [b for b in B if b['p'].contains(pt)]
                if inside:
                    hit = min(inside, key=lambda b: b['p'].area); how = 'punto'
            rec = {'x': round(x, 1), 'z': round(z, 1), 'how': how or 'solo coordinate'}
            if hit is not None:
                c = hit['p'].centroid
                rec.update({'x': round(c.x, 1), 'z': round(c.y, 1), 'h': round(hit['h'], 1), 'osm': hit['id']})
                if m['mode'] == 'replace':
                    fp = hit['p'].buffer(3)
                    gone = [b for b in B if b is hit or fp.contains(b['c']) or (m.get('names') and b['t'].get('name') in m['names'] and b['c'].distance(c) < 150)]
                    for b in gone:
                        remove.add(id(b))
                    foot = unary_union([b['p'] for b in gone]).convex_hull if len(gone) > 1 else hit['p']
                    rec['fp'] = enc(foot.exterior.coords, True) if isinstance(foot, Polygon) else enc(hit['p'].exterior.coords, True)
                    rec['h'] = round(max(b['h'] for b in gone), 1)
                    rec['gone'] = len(gone)
                    road = named.get((m.get('face') or '').lower())
                    if road:
                        ru = unary_union(road)
                        a, bpt = nearest_points(c, ru)
                        d = math.hypot(bpt.x - c.x, bpt.y - c.y) or 1
                        rec['face'] = [round((bpt.x - c.x) / d, 3), round((bpt.y - c.y) / d, 3)]
                elif m['mode'] == 'highlight':
                    hit['mark'] = m['k']
            marks[m['k']] = rec
            log(f'  luogo {m["k"]}: {rec}')
        B = [b for b in B if id(b) not in remove]
        Bout = []
        for i, b in enumerate(B):
            e = enc(b['p'].exterior.coords, True)
            if len(e) < 6:
                continue
            if b.get('mark'):
                marks[b['mark']]['b'] = len(Bout)
            Bout.append([int(round(b['h'] * 10)), int(round(b['mh'] * 10))] + e)

        out = {'v': 1, 'id': zid, 'ver': ver, 'name': Z.get('name', zid), 'll0': [lat0, lon0], 'k': [round(P.kx, 3), round(P.kz, 3)], 'q': 10,
               'rects': lrects, 'b': Bout, 'r': R, 'e': EL, 'w': Wout, 'g': Gout, 'n': Nout, 'm': marks,
               'src': '© OpenStreetMap contributors (ODbL)', 'date': datetime.date.today().isoformat()}
        js = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
        for f in os.listdir(OUT):
            if re.match(rf'^{re.escape(zid)}-v\d+\.json$', f) and f != fname:
                os.remove(os.path.join(OUT, f))
        open(os.path.join(OUT, fname), 'w').write(js)
        index['zones'][zid] = {'f': fname, 'name': out['name'], 'date': out['date'], 'kb': len(js.encode()) // 1024, 'b': len(Bout), 'r': len(R), 'w': len(Wout), 'g': len(Gout), 'n': len(Nout)}
        log(f'  scritto {fname}: {len(js.encode()) // 1024} KB')
    json.dump(index, open(idx_path, 'w'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    t0 = time.time()
    ok = True
    try:
        main()
    except Exception:
        ok = False
        log('ERRORE:\n' + traceback.format_exc())
    log(f'fine in {time.time() - t0:.0f}s, {"ok" if ok else "con errori"}')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'log.txt'), 'w').write('\n'.join(LOG) + '\n')
