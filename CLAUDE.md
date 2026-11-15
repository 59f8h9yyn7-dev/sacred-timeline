# Sacred Timeline — note di progetto

App personale (PWA installata sull'iPhone dell'utente) che mostra la sua mappa Marvel: timeline, multiverso 2D/3D, fascicoli dei personaggi. Rispondere in italiano, brevi e diretti; le modifiche vanno consegnate direttamente nell'app (push su GitHub), non come consigli.

## Com'è fatta
- `index.html`: tutta l'app in un file (~10.600 righe). three.js 0.160 in `vendor/three.module.min.js`, caricato solo per il 3D.
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
- `python3 -m http.server` nella cartella del repo + Playwright (preinstallato). Prima del caricamento impostare in localStorage `stl-intro-v1`, `stl-hint-v1`, `stl-seen-v1` = `'1'`, `stl-today-v1` = data di oggi, `stl-view-v1` = `{z, tx, ty}` per inquadrare un punto; nascondere `header.bar,#corner,#chr,#rulerC` per screenshot puliti. I font Google qui non si caricano (i testi risultano un po' più larghi che sull'iPhone).
- Nel sandbox la shell non ha internet (niente pip/npm/curl); git verso GitHub funziona. Download di dati esterni: con una GitHub Action che li scrive nel repo.

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
1. **Prototipo Manhattan 616** (prossimo passo): Midtown con la Avengers Tower, Greenwich Village con il Sanctum, il Queens di Peter Parker; volo libero, passaggio 2D → 3D, cartelli dei quartieri, luoghi Marvel toccabili.
2. Catalogo di tutti i luoghi del 616 titolo per titolo (bozza di Claude, l'utente la corregge).
3. Tutte le zone del catalogo + il globo.
4. Altri universi.
