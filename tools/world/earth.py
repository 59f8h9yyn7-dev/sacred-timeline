#!/usr/bin/env python3
"""Mondo 616 — la Terra del globo: immagini NASA (Blue Marble di giorno, Black Marble di notte) e Natural Earth
(confini, nomi dei paesi e delle città in italiano). Gira nella GitHub Action "Mondo 616" (serve internet e Pillow)
e scrive data/world/earth/ + la voce "earth" di data/world/index.json. Se i file della versione VER ci sono già, non fa nulla.

Immagini NASA: pubblico dominio. Natural Earth: pubblico dominio."""
import io, json, math, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTW = os.path.join(ROOT, 'data', 'world')
OUT = os.path.join(OUTW, 'earth')
VER = 1
UA = {'User-Agent': 'sacred-timeline-world/1 (app personale, una tantum)'}
GIBS = 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi'
NE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/'
TX, TY, TS = 8, 4, 2048  # tasselli ad alta definizione: 8 x 4 da 45°, 2048 px ciascuno


def log(*a):
    print(' '.join(str(x) for x in a), flush=True)


def get(url, timeout=180, tries=3):
    last = None
    for i in range(tries):
        try:
            t0 = time.time()
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                b = r.read()
                ct = r.headers.get('Content-Type', '')
            log(f'  {url[:110]} → {len(b) // 1024} KB in {time.time() - t0:.0f}s ({ct})')
            return b, ct
        except Exception as e:
            last = e
            log(f'  {url[:110]} non risponde ({str(e)[:120]})')
            time.sleep(4 * (i + 1))
    raise RuntimeError(str(last))


def image(b):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(io.BytesIO(b))
    im.load()
    return im


def gibs(layer, s, w, n, e, W, H, fmt='image/jpeg'):
    q = f'{GIBS}?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS={layer}&STYLES=&CRS=EPSG:4326&BBOX={s},{w},{n},{e}&WIDTH={W}&HEIGHT={H}&FORMAT={fmt}'
    b, ct = get(q, timeout=240)
    if 'image' not in ct:
        raise RuntimeError('GIBS: ' + b[:200].decode('utf-8', 'replace'))
    return image(b).convert('RGB')


def gibs_world(layers, W, H):
    """Il mondo intero da GIBS, a pezzi da 2048 px se una richiesta sola è troppo grande."""
    from PIL import Image
    for layer in layers:
        try:
            return gibs(layer, -90, -180, 90, 180, W, H)
        except Exception as e:
            log(f'  {layer} intero: {str(e)[:120]}')
        try:
            out = Image.new('RGB', (W, H))
            nx, ny = max(1, W // 2048), max(1, H // 2048)
            for j in range(ny):
                for i in range(nx):
                    w = -180 + 360 * i / nx; e = w + 360 / nx; n = 90 - 180 * j / ny; s = n - 180 / ny
                    out.paste(gibs(layer, s, w, n, e, W // nx, H // ny), (i * W // nx, j * H // ny))
            return out
        except Exception as e:
            log(f'  {layer} a pezzi: {str(e)[:120]}')
    return None


def nasa_page(page, pat):
    """Cerca nella pagina NASA il collegamento a un file (i siti NASA cambiano indirizzi: meglio leggerli)."""
    try:
        b, _ = get(page, timeout=60, tries=2)
        m = re.findall(r'href="([^"]*' + pat + r')"', b.decode('utf-8', 'replace'))
        return [u if u.startswith('http') else 'https://science.nasa.gov' + u for u in m]
    except Exception:
        return []


def first_image(urls):
    for u in urls:
        try:
            b, ct = get(u, timeout=300, tries=2)
            return image(b).convert('RGB')
        except Exception:
            pass
    return None


def enc_line(pts):
    out, px, py = [], None, None
    for x, y in pts:
        X, Y = int(round(x * 100)), int(round(y * 100))
        if px is None:
            out += [X, Y]
        elif (X, Y) != (px, py):
            out += [X - px, Y - py]
        else:
            continue
        px, py = X, Y
    return out


def main():
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    names = {k: f'earth/{k}-v{VER}.{ext}' for k, ext in (('day', 'webp'), ('lo', 'webp'), ('night', 'webp'), ('earth', 'json'))}
    tile = lambda i, j: f'earth/t-v{VER}-{i}-{j}.webp'
    need = [names[k] for k in names] + [tile(i, j) for j in range(TY) for i in range(TX)]
    idx_path = os.path.join(OUTW, 'index.json')
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {'zones': {}}
    if all(os.path.exists(os.path.join(OUTW, f)) for f in need) and (index.get('earth') or {}).get('v') == VER:
        log('Terra: già pronta, niente da fare'); return
    # vecchie versioni via
    for f in os.listdir(OUT):
        if not re.search(rf'-v{VER}[.-]', f):
            os.remove(os.path.join(OUT, f))
    save = lambda im, f, q=80: im.save(os.path.join(OUTW, f), 'WEBP', quality=q, method=6)

    # ---- di giorno: Blue Marble con rilievo e fondali ----
    if not os.path.exists(os.path.join(OUTW, names['day'])):
        log('== Terra di giorno ==')
        day = gibs_world(['BlueMarble_ShadedRelief_Bathymetry', 'BlueMarble_NextGeneration'], 4096, 2048)
        if day is None:
            urls = nasa_page('https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry', r'world\.topo\.bathy\.2004\d\d\.3x5400x2700\.jpg')
            urls += ['https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73751/world.topo.bathy.200407.3x5400x2700.jpg',
                     'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73776/world.topo.bathy.200408.3x5400x2700.jpg']
            day = first_image(urls)
        if day is None:
            raise RuntimeError('nessuna immagine della Terra di giorno')
        day = day.resize((4096, 2048), Image.LANCZOS)
        save(day, names['day'], 82)
        save(day.resize((1024, 512), Image.LANCZOS), names['lo'], 80)
    # ---- di notte: le luci delle città (Black Marble 2016) ----
    if not os.path.exists(os.path.join(OUTW, names['night'])):
        log('== Terra di notte ==')
        night = gibs_world(['VIIRS_Black_Marble', 'VIIRS_CityLights_2012'], 4096, 2048)
        if night is None:
            urls = nasa_page('https://science.nasa.gov/earth/earth-observatory/earth-at-night/maps', r'BlackMarble_2016_(?:01deg|3km)(?:_gray)?\.jpg')
            urls += ['https://viirsland.gsfc.nasa.gov/images/BlackMarble_2016_3km.jpg',
                     'https://eoimages.gsfc.nasa.gov/images/imagerecords/144000/144898/BlackMarble_2016_01deg.jpg']
            night = first_image(urls)
        if night is not None:
            night = night.resize((4096, 2048), Image.LANCZOS)
            save(night, names['night'], 78)
        else:
            log('  niente luci notturne: il globo farà senza')
    # ---- tasselli ad alta definizione (per quando si scende verso una città) ----
    log('== tasselli ==')
    for j in range(TY):
        for i in range(TX):
            f = tile(i, j)
            if os.path.exists(os.path.join(OUTW, f)):
                continue
            w = -180 + 45 * i; n = 90 - 45 * j
            im = None
            for layer in ('BlueMarble_ShadedRelief_Bathymetry', 'BlueMarble_NextGeneration'):
                try:
                    im = gibs(layer, n - 45, w, n, w + 45, TS, TS); break
                except Exception as e:
                    log(f'  tassello {i},{j} {layer}: {str(e)[:100]}')
            if im is not None:
                save(im, f, 78)
            time.sleep(1)
    tiles_ok = all(os.path.exists(os.path.join(OUTW, tile(i, j))) for j in range(TY) for i in range(TX))
    # ---- confini e nomi (Natural Earth) ----
    if not os.path.exists(os.path.join(OUTW, names['earth'])):
        log('== confini e nomi ==')
        from shapely.geometry import shape
        bl = json.loads(get(NE + 'ne_50m_admin_0_boundary_lines_land.geojson')[0])
        B = []
        for f in bl['features']:
            g = shape(f['geometry']).simplify(0.03)
            for ln in (g.geoms if hasattr(g, 'geoms') else [g]):
                e = enc_line(list(ln.coords))
                if len(e) >= 4:
                    B.append(e)
        co = json.loads(get(NE + 'ne_50m_admin_0_countries.geojson')[0])
        C = []
        for f in co['features']:
            p = {k.lower(): v for k, v in f['properties'].items()}
            nm = p.get('name_it') or p.get('name')
            x, y = p.get('label_x'), p.get('label_y')
            if nm and x is not None and y is not None:
                C.append([nm, round(x, 2), round(y, 2), int(p.get('labelrank') or 5), round(float(p.get('min_label') or 3), 1)])
        pp = json.loads(get(NE + 'ne_50m_populated_places.geojson')[0])
        Pl = []
        for f in pp['features']:
            p = {k.lower(): v for k, v in f['properties'].items()}
            sr = int(p.get('scalerank') if p.get('scalerank') is not None else 9)
            cap = 1 if 'capital' in str(p.get('featurecla') or '').lower() and 'admin-0' in str(p.get('featurecla') or '').lower() else 0
            if sr > 6 and not cap:
                continue
            nm = p.get('name_it') or p.get('name')
            lon, lat = (f['geometry']['coordinates'] if f.get('geometry') else (p.get('longitude'), p.get('latitude')))[:2]
            Pl.append([nm, round(lon, 3), round(lat, 3), sr, cap])
        Pl.sort(key=lambda r: (r[3], -r[4]))
        js = {'v': VER, 'b': B, 'c': C, 'p': Pl, 'src': 'Natural Earth'}
        open(os.path.join(OUTW, names['earth']), 'w').write(json.dumps(js, ensure_ascii=False, separators=(',', ':')))
        log(f'  confini {len(B)} linee, paesi {len(C)}, città {len(Pl)}')
    index['earth'] = {'v': VER, 'day': names['day'], 'lo': names['lo'], 'night': names['night'] if os.path.exists(os.path.join(OUTW, names['night'])) else None,
                      'json': names['earth'], 'tiles': {'f': f'earth/t-v{VER}-{{i}}-{{j}}.webp', 'nx': TX, 'ny': TY, 'px': TS} if tiles_ok else None,
                      'src': 'Immagini NASA (Blue Marble, Black Marble) · Natural Earth'}
    json.dump(index, open(idx_path, 'w'), ensure_ascii=False, separators=(',', ':'))
    log('Terra pronta')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        log('ERRORE Terra:\n' + traceback.format_exc())
        sys.exit(0)  # le zone vanno avanti lo stesso
