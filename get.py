import json, math, os, subprocess, urllib.request, concurrent.futures as cf
os.makedirs('out', exist_ok=True)
def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout
tj = urllib.request.urlopen('https://tiles.openfreemap.org/planet', timeout=30).read().decode()
open('out/planet.json', 'w').write(tj)
url = json.loads(tj)['tiles'][0]
# headers, as the browser on the phone would see them
open('out/headers.txt', 'w').write(
    sh(f"curl -sS -D - -o /dev/null -H 'Origin: https://59f8h9yyn7-dev.github.io' -H 'Accept-Encoding: gzip, deflate, br' '{url.replace('{z}','14').replace('{x}','4825').replace('{y}','6156')}'")
    + '\n---planet\n' + sh("curl -sS -D - -o /dev/null -H 'Origin: https://59f8h9yyn7-dev.github.io' https://tiles.openfreemap.org/planet")
    + '\n---fonts\n' + sh("curl -sS -D - -o /dev/null -H 'Origin: https://59f8h9yyn7-dev.github.io' 'https://tiles.openfreemap.org/fonts/Noto%20Sans%20Regular/0-255.pbf'"))
def t(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y
want = set()
for z in range(0, 4):
    for x in range(2 ** z):
        for y in range(2 ** z):
            want.add((z, x, y))
# areas: centre, half size in km at z14 (lower zooms: a few tiles around)
areas = [(40.754, -73.984, 6.0), (40.73, -73.99, 3.0), (40.744, -73.86, 3.5), (37.79, -122.42, 5.0), (34.02, -118.75, 2.0), (51.507, -0.12, 2.5)]
for la, lo, km in areas:
    for z in range(4, 15):
        n = 2 ** z
        tkm = 40075 * math.cos(math.radians(la)) / n
        r = max(1.0, km / tkm) if z >= 12 else 1.0
        x, y = t(la, lo, z)
        for i in range(int(x - r), int(x + r) + 1):
            for j in range(int(y - r), int(y + r) + 1):
                want.add((z, i % n, j))
print(len(want), 'tiles')
def get(k):
    z, x, y = k
    p = f'out/t/{z}/{x}/{y}.pbf'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    u = url.replace('{z}', str(z)).replace('{x}', str(x)).replace('{y}', str(y))
    for _ in range(3):
        r = subprocess.run(['curl', '-sS', '--compressed', '-o', p, '-w', '%{http_code}', u], capture_output=True, text=True)
        if r.stdout.strip() == '200':
            return 1
    if os.path.exists(p): os.remove(p)
    return 0
with cf.ThreadPoolExecutor(8) as ex:
    ok = sum(ex.map(get, sorted(want)))
print(ok, 'ok')
open('out/list.txt', 'w').write('\n'.join(f'{z}/{x}/{y}' for z, x, y in sorted(want)))
