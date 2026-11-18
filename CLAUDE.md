# Sacred Timeline — note di progetto

App personale (PWA installata sull'iPhone dell'utente) che mostra la sua mappa Marvel: timeline, multiverso 2D/3D, fascicoli dei personaggi. Rispondere in italiano, brevi e diretti; le modifiche vanno consegnate direttamente nell'app (push su GitHub), non come consigli.

## Com'è fatta
- `index.html`: tutta l'app in un file (~12.500 righe). three.js 0.160 in `vendor/three.module.min.js`, caricato solo per il 3D.
- `data/map.json`: la mappa (items `img`/`line`/`text` con id `e###`, gruppi `g###`), più `cardData` (modifiche fatte dall'utente ai fascicoli), `cardPhotos`, `backups`, `rev`, `saved`.
- `data/cards.json`: archivio fascicoli. `cards[]` (non riordinare: gli indici sono riferimenti, i nuovi vanno in coda), `idx[textId] = [[riga, indiceCard], ...]`, `prods` (titoli), `pm`. Apparizioni `ap = [prodIdx, textId, riga, tipo, nota]`, tipi f/n/c/i/m/a/r.
- `data/chrono.json`: posizioni in modalità Cronologia (`pos[id]`).
- Con il token, l'app legge e salva `map.json` sul ramo **`dati`** via API GitHub; senza token legge `main`. `cards.json`, `chrono.json` e il codice arrivano da GitHub Pages (`main`). Le foto salvate dall'app finiscono in `img/` su `dati`.

## Come pubblicare
- Lavorare sul ramo `dati` (aggiornato da `origin/dati`: l'utente salva spesso dall'app), commit, poi `git push origin HEAD:dati` e `git push origin HEAD:main` (main è sempre antenato di dati).
- JSON scritti compatti: `json.dumps(d, ensure_ascii=False, separators=(',', ':'))`.
- Prima di cambiare `map.json` aggiungere in `backups` una copia `bk/<data>.json` con `w: 'start'` (come fa l'app; si tengono le 15 più recenti + una a settimana per 12 settimane).
- Cambiando `index.html` alzare `VERSION` in `sw.js`; i file in `data/` sono network-first.

## Convenzioni della mappa
- Nomi come appaiono in quel titolo; alias in grafia ufficiale (Peter Parker/Spider-Man); "(imaginary)" per visioni; alias metà italiani in italiano (Ciclope, Mystica).
- Etichette universo (`U-616`, chip verticali) attaccate al loro ramo; parentesi dei rami chiuse sul bordo del proprio elenco; gradini della linea 616 centrati tra i loghi.

## Provare in locale
- `python3 -m http.server` nella cartella del repo + Playwright (preinstallato). Prima del caricamento impostare in localStorage `stl-intro-v1`, `stl-seen-v1` = `'1'`, `stl-hint-v1` = un oggetto JSON (es. `'{"mv":1,"mv3":1,"mv3b":1,"uni":1}'`, con `'1'` il multiverso si interrompe), `stl-today-v1` = data di oggi, `stl-view-v1` = `{z, tx, ty}` per inquadrare un punto; nascondere `header.bar,#corner,#chr,#rulerC` per screenshot puliti. I font Google qui non si caricano (i testi risultano un po' più larghi che sull'iPhone).
- Nel sandbox la shell non ha internet (niente pip/npm); git verso GitHub funziona, e `curl https://api.github.com/repos/59f8h9yyn7-dev/sacred-timeline/actions/runs` mostra lo stato delle Action. Download di dati esterni: con una GitHub Action che li scrive nel repo.
- Playwright con WebGL: lanciare Chromium con `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader` (va bene `/usr/bin/google-chrome`); `window.__w6open()` apre il Mondo 616 sul globo, `window.__w6open({k: 'times-sq'})` dritto nella città di un luogo; `window.__w6` / `window.__g6` sono gli stati di città e globo, `window.__g6fn` alcune funzioni (g6CheckEnter, g6Sel, g6FromCity, c6Fly…).
- Le Action si possono fermare dal sandbox: `curl -X POST https://api.github.com/repos/59f8h9yyn7-dev/sacred-timeline/actions/runs/<id>/cancel` (il proxy mette le credenziali).

## Progetto in corso: il Mondo 616 (3D)
Obiettivo finale: l'intero mondo del 616 ricostruito con elementi reali + elementi dei film; **tutte** le zone viste nei film e nelle serie vanno riportate.

Meccanica di riferimento: prima il gioco "COO — Covert Ornithological Operations" (città vera, dall'alto mappa 2D che scendendo diventa 3D serale senza stacchi, cartello "Stai entrando a <quartiere>"); dal 18/11 l'utente vuole soprattutto **le funzioni di Mappe del telefono** (joystick e minimappa tolti). Ignorare lo scopo del gioco.

Struttura (novembre 2026, "effetto Mappe"): **una mappa sola dal globo alla strada, ovunque**, come Mappe dell'iPhone.
- Lontano: il globo con la Terra vera (NASA, `data/world/earth/`, fatta da `tools/world/earth.py`). Sotto i ~2600 km sfuma nella mappa.
- Base reale: tasselli vettoriali di OpenStreetMap da **OpenFreeMap** (`https://tiles.openfreemap.org/planet` → indirizzo della settimana, salvato 7 giorni in `stl-tiles-tj`; schema OpenMapTiles, livelli 0–14, CORS aperto, gratis, senza chiave). Si chiedono solo i quadrati sullo schermo; il service worker li tiene nella cache `tiles` (offline per le zone già viste). Attribuzione "© OpenStreetMap · OpenFreeMap".
- Strato Marvel: tutti i luoghi del catalogo nel loro punto; modelli fatti a mano dove i film cambiano un palazzo (Avengers Tower sul MetLife, Sanctum al 177A di Bleecker: `modello` in `luoghi616.json`); i luoghi con punto "edificio" illuminano il palazzo vero. Luoghi nello stesso punto (film che dice solo la città) si aprono a raggiera, ognuno col suo segnaposto.
- Le vecchie zone 3D (`data/world/z-*.json`, `nyc616-v1.json`, `tools/world/zones*.json`, `build.py`, Action `mondo616.yml`) non le usa più l'app: restano nel repo.
- Più avanti gli altri universi riusano la stessa base con i propri luoghi (Raimi: Daily Bugle nel Flatiron; Webb: Oscorp Tower; Fox: X-Mansion a Westchester). Luoghi inventati come diorami e luoghi fuori dalla Terra come corpi del sistema solare: ancora da fare.
- Vincoli: deve girare bene sull'iPhone (quadrati max ~110, palazzi solo nei tasselli z14 vicini, max 10 sul telefono; pixel ratio ≤ 1,6), niente interni né fotorealismo.

Fasi:
1. Prototipo Manhattan 616 (fatto, novembre 2026).
2. Catalogo di tutti i luoghi del 616 titolo per titolo (fatto: 570 voci confermate dall'utente).
3. Tutte le zone + il globo (fatto) → sostituito dalla mappa unica a tasselli (fatto, 18 novembre 2026).
4. Indirizzi precisi: il 18/11 ~20 luoghi "in città" spostati sull'indirizzo vero (San Francisco di Ant-Man, She-Hulk, Hawkeye, Strange, Fisk, Rand, Josie's, Jane a Londra…). Restano ~170 luoghi con punto città/regione: per molti il film non dice dove (filtro "punto solo città o regione" del catalogo). Regola: indirizzo visto sullo schermo > edificio reale della storia > riprese nella stessa città della storia > quartiere/città. Fonti utili: mculocationscout.com, movie-locations.com.
5. Altri universi.

### Com'è fatto il Mondo 616 (index.html)
- `92-w616.js` (W6): guscio (apri/chiudi, renderer unico, ciclo dei fotogrammi, cartello "Stai entrando a", schermo), funzioni dei modelli (`w6Tower(T, S, fp)`, `w6Sanctum(T, S, fp, fronte)`: fp = impronta in metri x est / z sud).
- `95-m6.js` (M6): i tasselli. Le funzioni `m6Pbf` (lettore protobuf), `m6P`, `m6G`, `m6Polys`, `m6Clip`, `m6Raster` (dipinge un quadrato 512 px: terra, acqua, parchi, strade per classe con i nomi lungo la via, palazzi dall'alto; restituisce i nomi di città/quartieri/mari), `m6Bld` (palazzi 3D di un tassello z14: pareti + tetti, in metri attorno al centro del tassello, ritagliati al quadrato) e `m6Wmain` girano in un **Web Worker** (modulo da Blob, il loro testo con `toString()`; importa three solo per `ShapeUtils`); se il worker non parte, `m6Local` fa lo stesso qui. `m6Select` sceglie i quadrati (quadtree, divide sopra ~380 px, 460 sul telefono; oltre lo z14 riusa i dati dello z14 fino a z18); `m6Leaf` stende il quadrato sulla sfera (griglia, posizioni relative al centro per la precisione); se manca la sua immagine usa un pezzo di quella più grande (`m6Src`), e chiede prima il quadrato tre livelli sopra. Palazzi: `m6BldWant`/`m6GotBld`, telaio locale `m6Frame` (x est, y su, z sud, metri). Nebbia e cielo della sera solo in basso.
- `94-g616.js` (G6): camera (lat/lon del centro, distanza in km da 30 000 a 0,05, nord, inclinazione: `G6.d3` = scelta 3D, `G6.auto` = l'inclinazione segue la quota, `g6AutoTilt`/`g6MaxTilt`), globo, cielo (`G6.sky`), segnaposti e nomi (`g6Over`, raggiera per i luoghi nello stesso punto), gesti come Mappe (trascina con inerzia, pizzica, ruota, due dita su/giù = inclina, doppio tocco = avvicina, doppio tocco e trascina, tocco a due dita = allontana, tocco lungo = segna un punto; mouse: rotella, tasto destro/Maiusc per girare e inclinare), pulsanti 2D/3D, posizione (pallino blu), bussola, scala; scheda in basso trascinabile (pannello a sinistra sopra i 760 px) con ricerca (`g6Search`: luoghi, titoli → `g6Title` mostra tutti i luoghi del titolo, città e paesi di Natural Earth), scheda del luogo `g6PlaceHtml` (con testo e personaggi da `luoghi616.json`, "Vista 3D", "Apri in Mappe").
- Dal catalogo: `c6Fly(k)` apre il Mondo 616 sul luogo (`g6Sel(k, true)`); bollino "3D" = luogo con punto edificio (`w6Keys3d`).

### Provare il Mondo 616 nel sandbox
- La shell non raggiunge OpenFreeMap: per avere tasselli di prova si usa un ramo usa-e-getta con un'Action che li scarica (fatto il 18/11 col ramo `prove-tiles`, poi cancellato), li si mette in una cartella servita in locale e si imposta in localStorage `stl-tiles-url` = `'/_t/{z}/{x}/{y}.pbf'` (cartella `_t` esclusa da git). L'Action deve usare curl con un User-Agent da browser (OpenFreeMap risponde 403 a Python).
- `window.__w6open()` apre; `window.__g6` è la camera (es. `Object.assign(__g6, {lat, lon, alt, head, auto: false, tilt: 1.2, dirty: 3})`), `window.__m6` lo stato dei tasselli, `window.__g6fn` alcune funzioni (g6Sel, g6Title, g6Search, g6Go, g6FlyTo…).

### Catalogo dei luoghi (fase 2)
- Sorgente: `tools/catalogo/*.txt` (formato spiegato in `01-zone.txt`: zone, poi `== Titolo` e le voci; `+chiave | nome | dove | zona | tipo | lat,lon | precisione | nota` definisce un luogo, `chiave | nota` lo riusa; nota che comincia con `?` = da verificare). `python3 tools/catalogo/build.py` controlla titoli e chiavi e scrive `data/catalogo616.json` (`zone`, `luoghi[k] = [nome, dove, zona, tipo, lat, lon, prec]`, `titoli = [[titolo, nota, [[k, nota]…]]…]` in ordine di uscita). Tipi: r reale, m reale con elementi Marvel, i inventato sulla Terra, s fuori dalla Terra, d altra dimensione, x base mobile.
- `confermate.lst`: voci confermate dall'utente (`titolo|chiave`); nel JSON diventano il terzo campo della voce (`[k, nota, 1]`) e nell'app partono come confermate.
- Posizioni: `geo.txt` dice per ogni luogo sulla Terra come trovarlo (`q` ricerca Nominatim con alternative `||`, `x` incrocio di due strade via Overpass, `ll` a mano, `rel` scostamento da un altro luogo, `-` il film non dice dove). Regola: conta dove la storia mette il luogo (indirizzo visto sullo schermo > edificio reale > quartiere/città dichiarati); il luogo delle riprese solo se coincide con quello della storia. La Action `.github/workflows/catalogo616.yml` (parte quando cambia `geo.txt` sul ramo `dati`) esegue `geocode.py` (risultati in `geo-osm.json`, chiesti una volta sola) e `build.py`, che scrive `geo-log.txt` (luoghi lontani dalla stima, ricerche fallite) e mette in `luoghi[k]` lat, lon, precisione (e edificio, q quartiere, c città, r regione) e l'8° campo `fonte`.
- Bollino "3D" e "Vola qui nel Mondo 616" per ogni luogo dentro una zona pronta (`w6Keys3d`); gli altri luoghi con un punto hanno "Vedi sul globo del Mondo 616" (`c6Fly`).
- Nell'app: sezione `93-c616.js` (C6). Si apre dal pulsante "Catalogo luoghi" nel Mondo 616 e da "Catalogo dei luoghi del 616" nel pannello del sistema 616 del multiverso. Vista per titolo e per zona, ricerca, filtri per tipo e stato; ogni voce si conferma, si toglie, si corregge; si possono aggiungere luoghi.
- Ogni luogo sulla Terra nell'app mostra la posizione, la fonte e "Apri in Mappe" (Apple Maps); filtri "senza punto" e "punto solo città o regione".
- Correzioni dell'utente in `doc.cat616` (salvate con map.json): `s["titolo|k"]` 1 confermata / -1 tolta / 0 tolta la conferma (solo se diverso dal catalogo), `p[k].ll = [lat, lon]` posizione corretta, `n["titolo|k"]` nota riscritta, `p[k]` campi del luogo corretti (nome, dove, tipo, zona), `nuovi[k]` luoghi aggiunti (chiavi `u-…`, stesso formato di `luoghi`), `add[titolo]` chiavi aggiunte al titolo, `ts` ultima modifica. Riportate le correzioni nella sorgente, togliere da `cat616` ciò che è stato integrato.
