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

Meccanica di riferimento (gioco "COO — Covert Ornithological Operations", video mandato dall'utente): città vera ricostruita dai dati cartografici reali; dall'alto è una mappa 2D, scendendo diventa 3D illustrato (palette serale, stile cartone) senza stacchi; volo libero, ci si posa ovunque; cartello "Stai entrando a <quartiere>"; minimappa rotonda. Ignorare tutto ciò che riguarda lo scopo del gioco.

Struttura decisa:
- Nel 3D ogni universo è già un sistema solare (`mvBuild`, sezione "P4" di `index.html`): la sua Terra diventa un globo navigabile → zone (città/aree) caricate solo quando ci si va → mappa 2D → città 3D.
- Base reale da OpenStreetMap (edifici estrusi con altezze vere, strade, parchi, acqua, quartieri), scaricata da una GitHub Action (Overpass), semplificata in file compatti sotto `data/world/`, salvata dall'app per l'uso offline. Attribuzione "© OpenStreetMap contributors".
- Strato Marvel sopra: luoghi dei film con modelli stilizzati (es. Avengers Tower al 200 di Park Avenue al posto del MetLife Building; Sanctum Sanctorum al 177A di Bleecker Street), toccabili, collegati a titoli e personaggi di `cards.json`.
- Luoghi inventati (Wakanda, Sokovia, Westview, Complesso degli Avengers…) come diorami fatti a mano, dove li collocano i film. Luoghi fuori dalla Terra (Asgard, Titano, Knowhere, Sakaar…) come corpi del sistema solare.
- Più avanti gli altri universi riusano la stessa base reale con i propri luoghi (Raimi: Daily Bugle nel Flatiron; Webb: Oscorp Tower; Fox: X-Mansion a Westchester).
- Vincoli: deve girare bene sull'iPhone (geometrie unite, zone piccole, livelli di dettaglio), offline, niente interni né fotorealismo.

Fasi:
1. **Prototipo Manhattan 616** (fatto, novembre 2026): Midtown con la Avengers Tower, Greenwich Village con il Sanctum, il Queens di Peter Parker; volo libero, passaggio 2D → 3D, cartelli dei quartieri, luoghi Marvel toccabili.
2. Catalogo di tutti i luoghi del 616 titolo per titolo (fatto, novembre 2026: bozza di Claude corretta dall'utente, 570 voci confermate e 8 tolte, correzioni riportate nella sorgente).
3. Tutte le zone del catalogo + il globo — **fatto in buona parte** (novembre 2026): posizioni di tutti i luoghi (`geo.txt` + OpenStreetMap), globo della Terra-616 con tutti i punti, 112 zone 3D automatiche scaricate dall'Action. Restano: i ~56 luoghi sulla Terra senza punto (da sistemare con l'utente: filtro "senza punto" del catalogo, pulsante "N senza punto" sul globo); i luoghi inventati come diorami; prima di ogni giro riportare nella sorgente le correzioni in `doc.cat616`.
4. Altri universi.

### Com'è fatto il Mondo 616 (fase 1)
- Dati: `tools/world/zones.json` (zone in lat/lon + punti dei luoghi Marvel, `mode` replace/highlight/point) → `tools/world/build.py` gira nella Action `.github/workflows/mondo616.yml` (parte quando cambia `tools/world/**` sul ramo `dati`, scrive su `dati` e `main`) → `data/world/<zona>-v<N>.json` + `data/world/index.json` + `data/world/log.txt`. Alzare `v` della zona per un file nuovo: il service worker tiene per sempre i file `-vN` (offline).
- Formato zona: coordinate locali in decimetri a delta (x verso est, z verso sud); `b` edifici `[h, minh, ring…]`, `r` strade `[classe + 16·ponte, linea…]`, `e` binari sopraelevati, `w` acqua e `g` verde come poligoni con buchi, `n` quartieri `[nome, x, z, distretto, tipo]`, `m` luoghi risolti sugli edifici veri (`fp` impronta, `b` indice edificio, `face`).
- Luoghi Marvel: `data/luoghi616.json` (testi, titoli come in `cards.json`, `pers` = id dei fascicoli, `modello` tower/sanctum per i modelli fatti a mano). Un luogo nuovo = punto in `zones.json` + voce in `luoghi616.json`.
- Codice: sezione `92-w616.js` di `index.html` (W6). Si entra dal pannello del sistema 616 del multiverso (pulsante "Mondo 616 · New York"). Mappa sopra i ~2600 m, 3D sotto i ~450 m, in mezzo il passaggio (altezze e colori sfumano). Il multiverso resta in pausa sotto (`window.__w6on`).

### Il globo e le zone automatiche (fase 3)
- Terra: `tools/world/earth.py` (nell'Action, passo "La Terra del globo") scarica da NASA GIBS il Blue Marble con rilievo (4096×2048 + 1024×512 per partire subito), le luci Black Marble, 32 tasselli 2048 px da 45° (si accendono sotto i ~2600 km), e da Natural Earth confini, nomi dei paesi e delle città in italiano → `data/world/earth/*-v1.*` + voce `earth` di `index.json`. Per rifarla alzare `VER`.
- Zone automatiche: `python3 tools/world/zones_auto.py` (da rilanciare a mano quando il catalogo cambia) scrive `tools/world/zones-auto.json`: luoghi con punto edificio/quartiere/città (più le grandi città che OSM dà come "regione", elenco `CITY_Q`) uniti entro 1,6 km, rettangolo +500 m (lato 1,4–3,6 km), fuori dalle zone a mano; id `z-<luogo principale>`, nomi in `NAMES`. Segni: `highlight` (edificio vero illuminato, anche il più vicino entro 25 m) per i luoghi reali con punto edificio, `ground` per gli altri.
- `build.py` salta le zone già scaricate (stesso file `-vN`; `FORCE` = id o `all` per rifarle), per le zone automatiche fa una richiesta Overpass sola, riparte dall'ultimo server che ha risposto, nell'Action salva e pubblica dopo ogni zona (`COMMIT=1`), si ferma dopo `BUDGET_MIN` e si rilancia da sola (`data/world/.more` + `gh workflow run`). Zone fallite 3 volte: `data/world/fails.json`. Zone tolte dal catalogo: file e voce cancellati. Ogni voce di `index.json` ha anche `bb`, `rects` (lat/lon), `ll` (centro), `k` (luoghi), `auto`: l'app ci mette dentro i luoghi del catalogo senza aprire la zona.
- App, sezione `94-g616.js` (G6): unità raggio terrestre = 1; camera = punto al centro (lat/lon) + altezza in km + direzione del nord; si inclina scendendo; il dito trascina il punto preso (nord fermo se era in alto), due dita zoom + rotazione, inerzia; campo visivo più largo sui telefoni in verticale (`g6FitAlt`). Sole sempre in alto a sinistra dello schermo (notte e luci sul bordo destro). Punti del catalogo come pulsanti HTML raggruppati in base alla distanza sullo schermo; nomi dei gruppi: zona 3D, città della zona del catalogo, area. Zone pronte: contorno arancione e pulsante "3D"; toccandolo, o scendendo sotto ~46 km entro 70 km da una zona, si entra (`g6Enter` → `w6City`). Dalla città si torna con "Globo", Esc, o allargando oltre la quota massima (`g6FromCity`).
- W6 ora ha `mode` 'globe'/'city', un solo renderer (`w6Renderer`), la scena della città si rifà a ogni zona (`w6Gl`/`w6ReleaseCity`, l'ultima zona resta in memoria). Nella città: i luoghi di `luoghi616.json` con il loro modello + tutti i luoghi del catalogo dentro la zona (posizione corretta nell'app > segno del download > coordinate); quelli nello stesso punto diventano un segnaposto con l'elenco ("Da qualche parte a …" se il film dice solo la città). Scheda dei luoghi del catalogo comune a globo e città (`g6PlaceHtml`).

### Catalogo dei luoghi (fase 2)
- Sorgente: `tools/catalogo/*.txt` (formato spiegato in `01-zone.txt`: zone, poi `== Titolo` e le voci; `+chiave | nome | dove | zona | tipo | lat,lon | precisione | nota` definisce un luogo, `chiave | nota` lo riusa; nota che comincia con `?` = da verificare). `python3 tools/catalogo/build.py` controlla titoli e chiavi e scrive `data/catalogo616.json` (`zone`, `luoghi[k] = [nome, dove, zona, tipo, lat, lon, prec]`, `titoli = [[titolo, nota, [[k, nota]…]]…]` in ordine di uscita). Tipi: r reale, m reale con elementi Marvel, i inventato sulla Terra, s fuori dalla Terra, d altra dimensione, x base mobile.
- `confermate.lst`: voci confermate dall'utente (`titolo|chiave`); nel JSON diventano il terzo campo della voce (`[k, nota, 1]`) e nell'app partono come confermate.
- Posizioni: `geo.txt` dice per ogni luogo sulla Terra come trovarlo (`q` ricerca Nominatim con alternative `||`, `x` incrocio di due strade via Overpass, `ll` a mano, `rel` scostamento da un altro luogo, `-` il film non dice dove). Regola: conta dove la storia mette il luogo (indirizzo visto sullo schermo > edificio reale > quartiere/città dichiarati); il luogo delle riprese solo se coincide con quello della storia. La Action `.github/workflows/catalogo616.yml` (parte quando cambia `geo.txt` sul ramo `dati`) esegue `geocode.py` (risultati in `geo-osm.json`, chiesti una volta sola) e `build.py`, che scrive `geo-log.txt` (luoghi lontani dalla stima, ricerche fallite) e mette in `luoghi[k]` lat, lon, precisione (e edificio, q quartiere, c città, r regione) e l'8° campo `fonte`.
- Bollino "3D" e "Vola qui nel Mondo 616" per ogni luogo dentro una zona pronta (`w6Keys3d`); gli altri luoghi con un punto hanno "Vedi sul globo del Mondo 616" (`c6Fly`).
- Nell'app: sezione `93-c616.js` (C6). Si apre dal pulsante "Catalogo luoghi" nel Mondo 616 e da "Catalogo dei luoghi del 616" nel pannello del sistema 616 del multiverso. Vista per titolo e per zona, ricerca, filtri per tipo e stato; ogni voce si conferma, si toglie, si corregge; si possono aggiungere luoghi.
- Ogni luogo sulla Terra nell'app mostra la posizione, la fonte e "Apri in Mappe" (Apple Maps); filtri "senza punto" e "punto solo città o regione".
- Correzioni dell'utente in `doc.cat616` (salvate con map.json): `s["titolo|k"]` 1 confermata / -1 tolta / 0 tolta la conferma (solo se diverso dal catalogo), `p[k].ll = [lat, lon]` posizione corretta, `n["titolo|k"]` nota riscritta, `p[k]` campi del luogo corretti (nome, dove, tipo, zona), `nuovi[k]` luoghi aggiunti (chiavi `u-…`, stesso formato di `luoghi`), `add[titolo]` chiavi aggiunte al titolo, `ts` ultima modifica. Riportate le correzioni nella sorgente, togliere da `cat616` ciò che è stato integrato.
