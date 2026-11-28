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

## Feedback dell'amico (vocali del 21/11/2026) → fatto il 21/11
- La grafica gli piace così.
- Sotto ogni locandina: **📌 fissa** (il film resta sempre in cima, tutti i giorni) e **✕ nascondi** (sparisce dalla vista).
- Orario: invece di andare dritto al pagamento, meglio la **pagina del film "un passo prima"** (deciso con Christian:
  pagina ComingSoon con gli orari di quel film in quel cinema + pulsanti d'acquisto; Italia e Girone → pagina del film sul loro sito).
- Toccando **titolo/locandina** → scheda di presentazione del film (ricerca Google "titolo film").

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
- **MyMovies** (`mymovies.it/cinema/firenze/21354/` = Space, `/cinema/firenze/campibisenzio/5748/` = UCI Campi) ha gli orari di OGGI
  in HTML semplice: utile come controllo/riserva per UCI e Space (non mostra gli spettacoli dopo mezzanotte).

### Verifica del 20/11/2026 (sito pubblicato vs fonti ufficiali)
- Fiorella, Portico, Marconi, Principe (oggi), Teatro Italia (pagine film), Girone: tutto coincide.
- UCI e Space confrontati con MyMovies: coincidono.
- Corretto: al Girone "ore 16.00 merenda; ore 16.30 proiezione" dava due orari → ora si tiene solo la proiezione.
- ComingSoon toglie gli spettacoli già iniziati: per "oggi" il sito mostra solo quelli ancora da fare (va bene).

## Da chiarire / in attesa
- [x] Lista dei cinema (8, vedi sopra).
- [x] Hosting: **GitHub Pages** + GitHub Actions (deciso 20/11).
- [x] Uso **principalmente da telefono**: deve essere ottimizzato mobile "come un'app" (deciso 20/11) → PWA installabile.
- [x] Branch `main` creato (20/11) da `claude/relaxed-tesla-obj9y3`. Il sito si pubblica da `main`: le modifiche vanno portate lì.
- [x] Pages attivo e funzionante (confermato 20/11). URL: https://christiancrocetti01-sys.github.io/cinemafranci/

## Decisioni prese
- Sito web statico (non app nativa), installabile come PWA, pensato per il telefono.
- GitHub Pages; i dati li produce il workflow (`site/data/` è in .gitignore, non si committano).
- Teatro Italia: se scheda riassuntiva e pagina del film non coincidono (succede!), vale la pagina del film.

## Stato attuale
- Fatto (21/11): test completo dell'app (Playwright, 62 controlli ok); versione PC ottimizzata (≥1000px: locandina a lato del titolo,
  tutte le colonne a schermo, vista Orari centrata, effetti al passaggio del mouse).
- Fatto (21/11): pin/nascondi film, orario → pagina del film, titolo → Google (feedback dell'amico).
- Fatto (20/11): scraper funzionante su 8/8 cinema (~20 film, ~500 spettacoli, ~1,5 min), sito mobile con vista Tabella e vista Orari,
  PWA (manifest + service worker + icone), workflow di aggiornamento e pubblicazione.
- Fatto (24/11): "non aggiorna" → cron GitHub inaffidabile (passato a ogni ora); Marconi vuoto su ComingSoon
  per qualche ora il 22–23/11 (errore temporaneo) → se una fonte è vuota si riprova dopo 60 s.
- Fatto (28/11): "ha smesso di aggiornarsi e si sono persi film". Due cause:
  1. **Film persi**: la pagina del cinema su ComingSoon elenca solo i film con spettacoli OGGI → un film proiettato
     solo nei giorni dopo spariva (es. "Il rumore delle cose nuove" al Space solo il 29). Ora per ogni cinema si
     controllano anche i film della pagina città `/cinema/firenze/` e quelli trovati lì nella pubblicazione precedente
     (`prepara_extra`). Lo scraper ora dura ~3,5 min (~200 richieste).
  2. **Aggiornamenti**: anche con cron ogni ora GitHub esegue solo ~2 run al giorno (verso le 14 e le 23 UTC).
     Soluzione: avvio esterno con cron-job.org che chiama l'API `workflow_dispatch` (vedi `docs/aggiornamento-esterno.md`).
     **Configurato e testato da Christian il 28/11** (risposta 204, run partito). Token fine-grained con scadenza:
     quando scade gli aggiornamenti tornano ~2 al giorno → rigenerarlo e aggiornare l'header su cron-job.org.
- Fatto (28/11): **check completo degli orari** contro i siti ufficiali (script indipendente, tutti i giorni disponibili).
  Trovati e corretti dei buchi:
  - ComingSoon non conosce i film che un cinema fa solo nei giorni dopo se oggi non sono in nessun cinema di Firenze
    ("Gli anni del padre" al Marconi 1–2/12), gli eventi lontani (10/12 "Succederà questa notte" con ospiti al Fiorella e al Principe)
    e a volte salta un orario (Portico 30/11 18:00). → **Fiorella, Marconi, Principe e Portico ora si leggono dal sito ufficiale**
    (`da_fiorella`, `da_stasera`, `da_portico`), e ComingSoon aggiunge sala, link d'acquisto e pagina "un passo prima"
    quando lo spettacolo coincide (`unisci`). Se il sito ufficiale non si legge → solo ComingSoon come prima.
  - UCI e Space: ComingSoon non aveva "La luce del mondo" (4 spettacoli oggi al Space) → si aggiungono da **MyMovies**
    i film di OGGI che ComingSoon non ha (`integra_mymovies`, solo spettacoli non ancora iniziati, niente doppioni).
  - Teatro Italia: una nota sotto un orario ("evento speciale Disney…") faceva perdere gli orari dopo (Hexe 28/11 18:00).
  - Dopo mezzanotte: fino alle 05:00 "oggi" = giornata di ieri (sito e scraper), così gli spettacoli di notte restano visibili.
  - Risultato: Fiorella, Portico, Marconi, Principe identici al sito ufficiale su tutti i giorni; UCI e Space identici a MyMovies
    (oggi); Teatro Italia e Girone ricontrollati a mano pagina per pagina. Girone: il sito ha solo 2 eventi, tutti presi.
- Da fare: farlo provare all'amico e raccogliere il suo feedback.
- Idee possibili: pagina/scheda del film, filtro "dalle ore", aggiungere altri cinema (basta il path ComingSoon in `CINEMA`).

## Struttura del codice
- `scraper/scrape.py`: solo libreria standard. Lista `CINEMA` (id, nome, zona, sito, fonte, path ComingSoon, `ufficiale`, `mymovies`).
  Fonti: `da_cinema_cs` (ComingSoon + sito ufficiale o MyMovies), `da_italia`, `da_girone`. Uscita: `site/data/programmazione.json` =
  `{generato, cinema:[{id,nome,zona,sito}], film:{chiave:{titolo,locandina|immagine,genere,durata}},
  spettacoli:[{k:chiave film, c:id cinema, d:"YYYY-MM-DD", h:"HH:MM", p:pagina del film in quel cinema, sala?, tag?:[...], url?:acquisto}], aggiornato:{id:iso}, errori:{id:msg}}`.
  - `chiave_film()` normalizza i titoli (accenti, punteggiatura, O.V./IMAX) per unire lo stesso film tra cinema diversi.
  - `--prev URL`: se un cinema fallisce si riusano i suoi spettacoli della pubblicazione precedente (e l'errore appare nel piè di pagina).
  - Prova in locale: `python3 scraper/scrape.py` poi `cd site && python3 -m http.server`.
- `site/`: `index.html`, `style.css`, `app.js` (JS vanilla, nessun build), `sw.js` (offline), `manifest.webmanifest`, `icons/`.
  - Vista **Tabella**: righe = film (alfabetico), colonne = cinema attivi che hanno spettacoli quel giorno, celle = pillole orarie
    (link d'acquisto se c'è). Prima colonna e intestazione fisse.
  - Vista **Orari**: elenco cronologico per fasce (mattina/pomeriggio/sera/notte), nasconde quelli già iniziati (pulsante per mostrarli).
  - Ricerca: più film separati da virgola. Cinema esclusi, vista scelta, film fissati e nascosti salvati in localStorage
    (`cf.esclusi`, `cf.vista`, `cf.fissati`, `cf.nascosti`, per chiave film).
  - Film fissati: in cima alla Tabella (bordo oro), 📌 nella vista Orari. Nascosti: spariscono da entrambe le viste,
    avviso "Annulla" per 5 s, pulsante "N film nascosti · Mostra" in fondo (con "Rimetti"); cercandoli per nome si vedono comunque.
  - Pillola orario → `p` (pagina del film in quel cinema), altrimenti `url`. Titolo/locandina → ricerca Google.
  - Spettacoli prima delle 05:00 = notte del giorno indicato (ordinati in fondo, pillola tratteggiata "notte").
  - Stile ispirato al sito del Fiorella: blu notte, accento #3ab0ff, font Outfit, pillole con bordo.
- `.github/workflows/aggiorna.yml`: ogni ora 4:17–22:17 UTC + a ogni push su main + manuale → scraper → deploy Pages.
  (24/11: con 3 orari fissi GitHub ne eseguiva solo 1-2 al giorno, con ore di ritardo → passato a ogni ora.)

## Note tecniche
- Branch di sviluppo: `claude/relaxed-tesla-obj9y3`.
