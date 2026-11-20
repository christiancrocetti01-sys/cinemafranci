# CinemaFranci — Contesto progetto

> File di contesto sempre aggiornato. Va letto a inizio sessione e aggiornato a ogni decisione o passo importante,
> così l'utente può fare `/clear` senza perdere niente.

## Chi e cosa
- Progetto fatto dall'utente (Christian) per un amico (Franci).
- Obiettivo: **rendere più facile cercare la programmazione dei cinema**, invece di guardare a mano tutti i siti.
- Formato: **sito web** (scelto perché più semplice di un'app; all'amico va bene qualsiasi cosa: sito, app o bot, purché automatico).

## Requisiti (dai vocali e messaggi dell'amico, 20/11/2026)
1. **Lista fissa di circa 10 cinema della zona**, scelti dall'amico (zona Firenze; esempio citato: *Cinema Luce, Sesto Fiorentino*).
   - La lista è ancora da ricevere (vedi "Da chiarire").
2. **Dati aggiornati automaticamente** ogni giorno / a ogni apertura del sito (scraping dei siti dei cinema).
3. **Ricerca per film**: scrivo il nome del film e ottengo **in quali cinema** è proiettato e **a che ora**,
   per **oggi o per una data scelta** (anche i giorni dopo).
4. **Ricerca inversa per cinema**: scelgo 1, 2 o 3 cinema e vedo **tutti i film** proiettati lì nella data scelta.
   - In pratica è una tabella cinema × film per giorno, interrogabile da entrambi i lati.
5. **L'orario è FONDAMENTALE**, non è un dettaglio: l'amico sa già quali film ci sono, gli serve sapere *quando*.
   Risultati **in ordine cronologico per orario**.
6. **Includere/escludere i cinema** dalla ricerca (es. deselezionare il Luce di Sesto Fiorentino il giorno che non ci vuole andare).
7. Possibilità di cercare 1 o 2 film insieme.

## Interfaccia richiesta (vocale + screenshot dell'amico, 20/11/2026)
L'amico ha mandato uno screenshot della pagina "FILM IN SALA" del sito di un cinema come spunto grafico
("molto intuitiva"). Com'è fatta quella pagina:
- Tema scuro (blu notte), righe alternate con sfondo leggermente diverso.
- Prima colonna: **locandina + titolo del film**. Colonne: **i giorni** (es. "VENERDÌ 20 NOVEMBRE", in azzurro).
- Nelle celle: **orari come "pillole"** arrotondate con bordo azzurro (es. 16:00, 18:15, 20:30).

**Cosa vuole lui invece (adattamento):**
- Non servono i giorni in colonna: **si seleziona un giorno** (selettore data in alto).
- **Colonne = le sale/cinema selezionati.**
- **Righe = i film in programma a Firenze** quel giorno (con locandina e titolo).
- **Incrocio riga×colonna = gli orari** (pillole). Cella vuota se il film non c'è in quel cinema.
- Stessa estetica: scuro, pillole orarie, locandine.
- Da valutare: su telefono con tanti cinema la tabella va scorsa in orizzontale (prima colonna fissa)
  oppure va trasformata in schede/lista. Il filtro per film o cinema riduce righe e colonne.

## Cinema scelti (lista ricevuta 20/11/2026) e fonte dati
Analisi fatta il 20/11/2026. **Fonte principale: ComingSoon.it** (un solo scraper per 6 cinema).

| id | Cinema | Sito ufficiale | Fonte dati scelta |
|---|---|---|---|
| uci | UCI Cinemas Campi Bisenzio | ucicinemas.it/cinema/uci-cinemas-campi-bisenzio-firenze | ComingSoon `/cinema/firenze/uci-cinemas-campi-bisenzio/2510/` |
| space | The Space Firenze (Novoli) | thespacecinema.it/cinema/firenze/al-cinema | ComingSoon `/cinema/firenze/the-space-cinema-firenze-novoli/5396/` |
| fiorella | Fiorella | circuitocinema.com/cinema/fiorella/ | ComingSoon `/cinema/firenze/fiorella/1400/` |
| marconi | Multisala Marconi | staseraalcinema.it/multisala-marconi/ | ComingSoon `/cinema/firenze/marconi/1411/` |
| principe | Multisala Principe | staseraalcinema.it/multisala-principe/ | ComingSoon `/cinema/firenze/principe/1415/` |
| portico | Il Portico | cinemailportico.it/programmazione.php | ComingSoon `/cinema/firenze/portico/1414/` |
| italia | Teatro Cinema Italia (Pontassieve) | teatrocinemaitalia.it/programma/cinema/ | **Sito ufficiale** (su ComingSoon ci sono i film ma non gli orari) |
| girone | Nuovo Cinema L'Unione – Il Girone (Fiesole) | ilgirone.it/arci/cinema/programmazione/ | **Sito ufficiale** (non è su ComingSoon) |

Lo screenshot "FILM IN SALA" mandato dall'amico è del **Fiorella** (circuitocinema.com).

### Come leggere ComingSoon (verificato)
- Pagina cinema `https://www.comingsoon.it<path>` → elenco film: `<a href="/cinema/firenze/[comune/]?idf=NNN" title="Titolo" class="tit_olo ...">`,
  con locandina `mr.comingsoon.it/imgdb/locandine/235x336/XXXX.jpg`.
  ATTENZIONE: gli orari su questa pagina sono "tipici", NON del giorno → non usarli.
- Pagina biglietti `<path>ticket/?idf=NNN` → **orari esatti giorno per giorno** (circa 5–6 giorni avanti), verificati
  identici al sito ufficiale del Fiorella. Struttura: `#salaFilmList` → uno o più blocchi `<div><p class="h1">VERSIONE</p>`
  (es. normale / "(O.V.)" / "IMAX": vanno gestiti tutti, non sovrascritti) → `.media` con `span.day` + `span.month` (es. "20","NOV")
  → `button.btn-fab` con `title="Sala X"`, testo `HH:MM`, a volte `data-url` = link d'acquisto.
- Spettacoli dopo mezzanotte (es. 00:45 sotto il "20 NOV" all'UCI): convenzione dei cinema = notte del giorno indicato. Da gestire.
- Funziona con semplice HTTP (urllib + User-Agent da browser), nessun blocco. ~1 richiesta per cinema + 1 per film (~40 al giorno).
- Possibili piccole lacune per eventi speciali (es. "Mustang" al Portico 23–25/11 c'è sul sito ufficiale ma non su ComingSoon).

### Siti ufficiali
- **UCI e The Space**: bloccati da Cloudflare (403 anche con Chromium headless da IP datacenter) → impossibile direttamente.
- **LiveTicket** (biglietteria di Italia e Girone): 403.
- **Teatro Italia**: HTML WordPress pulito: `article.calendario-card` → `.calendario-card__title a` + `.calendario-card__date p`
  con `<strong>venerdì 20 Novembre</strong><br/>19:00 in sala piccola<br/>...`.
- **Il Girone**: pagina programmazione = elenco link `/arci/evento/<slug>/`; nella pagina evento, sezione "PROGRAMMAZIONE" in testo libero:
  "Sabato 21 novembre ore 21.15" → regex. Ci sono anche eventi non-film (es. "Cinema a Merenda", "Jam session").
- Portico ha JSON-LD ItemList ma senza orari; staseraalcinema (Marconi/Principe) mostra un giorno per volta.

## Da chiarire / in attesa
- [x] Lista dei cinema (8, vedi sopra).
- [x] Hosting: **GitHub Pages** + GitHub Actions (deciso 20/11).
- [x] Uso **principalmente da telefono**: deve essere ottimizzato mobile "come un'app" (deciso 20/11) → PWA installabile.
- [x] Branch `main` creato (20/11) da `claude/relaxed-tesla-obj9y3`. Il sito si pubblica da `main`: le modifiche vanno portate lì.
- [ ] Attivare Pages: Settings → Pages → Source = "GitHub Actions" (lo fa l'utente). URL: https://christiancrocetti01-sys.github.io/cinemafranci/

## Decisioni prese
- Sito web statico (non app nativa), installabile come PWA, pensato per il telefono.
- GitHub Pages; i dati li produce il workflow (`site/data/` è in .gitignore, non si committano).
- Teatro Italia: se scheda riassuntiva e pagina del film non coincidono (succede!), vale la pagina del film.

## Stato attuale
- Fatto (20/11): scraper funzionante su 8/8 cinema (~20 film, ~500 spettacoli, ~1,5 min), sito mobile con vista Tabella e vista Orari,
  PWA (manifest + service worker + icone), workflow di aggiornamento e pubblicazione.
- Da fare: attivare Pages (vedi sopra) e farlo provare all'amico; poi raccogliere il suo feedback.
- Idee possibili: pagina/scheda del film, filtro "dalle ore", aggiungere altri cinema (basta il path ComingSoon in `CINEMA`).

## Struttura del codice
- `scraper/scrape.py`: solo libreria standard. Lista `CINEMA` (id, nome, zona, sito, fonte, path ComingSoon). Fonti: `da_comingsoon`,
  `da_italia`, `da_girone`. Uscita: `site/data/programmazione.json` =
  `{generato, cinema:[{id,nome,zona,sito}], film:{chiave:{titolo,locandina|immagine,genere,durata}},
  spettacoli:[{k:chiave film, c:id cinema, d:"YYYY-MM-DD", h:"HH:MM", sala?, tag?:[...], url?}], aggiornato:{id:iso}, errori:{id:msg}}`.
  - `chiave_film()` normalizza i titoli (accenti, punteggiatura, O.V./IMAX) per unire lo stesso film tra cinema diversi.
  - `--prev URL`: se un cinema fallisce si riusano i suoi spettacoli della pubblicazione precedente (e l'errore appare nel piè di pagina).
  - Prova in locale: `python3 scraper/scrape.py` poi `cd site && python3 -m http.server`.
- `site/`: `index.html`, `style.css`, `app.js` (JS vanilla, nessun build), `sw.js` (offline), `manifest.webmanifest`, `icons/`.
  - Vista **Tabella**: righe = film (alfabetico), colonne = cinema attivi che hanno spettacoli quel giorno, celle = pillole orarie
    (link d'acquisto se c'è). Prima colonna e intestazione fisse.
  - Vista **Orari**: elenco cronologico per fasce (mattina/pomeriggio/sera/notte), nasconde quelli già iniziati (pulsante per mostrarli).
  - Ricerca: più film separati da virgola. Cinema esclusi e vista scelta salvati in localStorage.
  - Spettacoli prima delle 05:00 = notte del giorno indicato (ordinati in fondo, pillola tratteggiata "notte").
  - Stile ispirato al sito del Fiorella: blu notte, accento #3ab0ff, font Outfit, pillole con bordo.
- `.github/workflows/aggiorna.yml`: alle 5:17, 11:17 e 16:17 UTC + a ogni push su main + manuale → scraper → deploy Pages.

## Note tecniche
- Branch di sviluppo: `claude/relaxed-tesla-obj9y3`.
