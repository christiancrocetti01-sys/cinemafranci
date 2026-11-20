#!/usr/bin/env python3
"""Raccoglie la programmazione dei cinema e la salva in site/data/programmazione.json.

Usa solo la libreria standard di Python.
Fonti: ComingSoon.it per la maggior parte dei cinema, siti ufficiali per Teatro Italia e Il Girone.

Uso:
    python3 scraper/scrape.py [--out PATH] [--prev URL_O_FILE] [--solo id1,id2]

--prev: JSON della volta precedente (URL del sito pubblicato o file locale). Se una fonte
        fallisce, per quel cinema si riusano i dati precedenti invece di lasciarlo vuoto.
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
CS = "https://www.comingsoon.it"
PAUSA = 0.4  # secondi tra una richiesta e l'altra, per essere educati

CINEMA = [
    {"id": "uci", "nome": "UCI Campi Bisenzio", "zona": "Campi Bisenzio",
     "sito": "https://ucicinemas.it/cinema/uci-cinemas-campi-bisenzio-firenze",
     "fonte": "comingsoon", "path": "/cinema/firenze/uci-cinemas-campi-bisenzio/2510/"},
    {"id": "space", "nome": "The Space Novoli", "zona": "Firenze",
     "sito": "https://www.thespacecinema.it/cinema/firenze/al-cinema",
     "fonte": "comingsoon", "path": "/cinema/firenze/the-space-cinema-firenze-novoli/5396/"},
    {"id": "fiorella", "nome": "Fiorella", "zona": "Firenze",
     "sito": "https://www.circuitocinema.com/cinema/fiorella/",
     "fonte": "comingsoon", "path": "/cinema/firenze/fiorella/1400/"},
    {"id": "marconi", "nome": "Marconi", "zona": "Firenze",
     "sito": "https://www.staseraalcinema.it/multisala-marconi/",
     "fonte": "comingsoon", "path": "/cinema/firenze/marconi/1411/"},
    {"id": "principe", "nome": "Principe", "zona": "Firenze",
     "sito": "https://www.staseraalcinema.it/multisala-principe/",
     "fonte": "comingsoon", "path": "/cinema/firenze/principe/1415/"},
    {"id": "portico", "nome": "Il Portico", "zona": "Firenze",
     "sito": "https://www.cinemailportico.it/programmazione.php",
     "fonte": "comingsoon", "path": "/cinema/firenze/portico/1414/"},
    {"id": "italia", "nome": "Teatro Italia", "zona": "Pontassieve",
     "sito": "https://www.teatrocinemaitalia.it/programma/cinema/",
     "fonte": "italia"},
    {"id": "girone", "nome": "Il Girone", "zona": "Fiesole",
     "sito": "https://www.ilgirone.it/arci/cinema/programmazione/",
     "fonte": "girone"},
]

MESI = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
        "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}
GIORNI_RE = r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
MESI_RE = (r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
           r"settembre|ottobre|novembre|dicembre)")
DATA_RE = re.compile(GIORNI_RE + r"\s+(\d{1,2})\s+" + MESI_RE, re.I)
ORA_RE = re.compile(r"\b([01]?\d|2[0-3])[.:]([0-5]\d)\b")


# ---------------------------------------------------------------- utilità

def oggi():
    return dt.datetime.now(ROMA).date()


def scarica(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"})
    for tentativo in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                testo = r.read().decode("utf-8", "replace")
            time.sleep(PAUSA)
            return testo
        except Exception:
            if tentativo == 2:
                raise
            time.sleep(2 * (tentativo + 1))


def testo_pulito(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def righe(pagina):
    """Converte l'HTML in righe di testo (una per elemento)."""
    pagina = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "", pagina)
    pagina = re.sub(r"(?i)<br\s*/?>", "\n", pagina)
    pagina = re.sub(r"<[^>]+>", "\n", pagina)
    pagina = html.unescape(pagina)
    return [re.sub(r"\s+", " ", r).strip() for r in pagina.split("\n") if r.strip()]


def data_da(giorno, mese, rif):
    """Giorno + mese (nome o abbreviazione) -> date, deducendo l'anno rispetto a oggi."""
    m = MESI[mese.strip().lower()[:3]]
    d = dt.date(rif.year, m, int(giorno))
    if d < rif - dt.timedelta(days=90):
        d = d.replace(year=rif.year + 1)
    elif d > rif + dt.timedelta(days=270):
        d = d.replace(year=rif.year - 1)
    return d


def chiave_film(titolo):
    """Normalizza un titolo per riconoscere lo stesso film tra cinema diversi."""
    t = unicodedata.normalize("NFKD", titolo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\((?:o\.?v\.?|v\.?o\.?)[^)]*\)", " ", t)
    t = re.sub(r"\b(imax|3d|4dx|v\.?o\.?s?|o\.?v\.?|versione originale|lingua originale)\b", " ", t)
    t = re.sub(r"[.'’]", "", t)  # "Z.U.C.C.A." = "z.u.c.ca", "l'alba" = "l’alba"
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", "-", t.strip())


def titolo_leggibile(t):
    t = re.sub(r"\s+", " ", t).strip()
    if t.isupper():  # "SE DOMANI NON TORNO" -> "Se domani non torno"
        t = t.capitalize()
    return t


def etichette(versione):
    """Ricava i tag (IMAX, lingua originale, ...) dal nome della versione."""
    v = " " + versione.upper() + " "
    tag = []
    if re.search(r"\(O\.?V\.?\)|\bV\.?O\.?S?\b|\bO\.?V\.?\b|ORIGINAL|\bENG\b|SUB ITA", v):
        tag.append("Lingua originale")
    for parola, nome in (("IMAX", "IMAX"), ("4DX", "4DX"), ("3D", "3D"), ("ATMOS", "Dolby Atmos"),
                         ("ISENSE", "iSense"), ("SCREENX", "ScreenX")):
        if re.search(r"\b" + parola + r"\b", v):
            tag.append(nome)
    return tag


# ---------------------------------------------------------------- ComingSoon

def da_comingsoon(cin, rif):
    pagina = scarica(CS + cin["path"])
    film, spett = {}, []
    blocchi = pagina.split('class="header-scheda')[1:]
    for b in blocchi:
        m = re.search(r'href="/cinema/firenze/(?:[a-z0-9-]+/)?\?idf=(\d+)" title="([^"]+)" class="tit_olo', b)
        if not m:
            continue
        idf, titolo = m.group(1), html.unescape(m.group(2))
        info = {"titolo": titolo}
        img = re.search(r'<img src="(https://mr\.comingsoon\.it/imgdb/locandine/[^"]+)"', b)
        if img:
            info["locandina"] = img.group(1)
        for campo, chiave in (("Genere", "genere"), ("Durata", "durata")):
            g = re.search(r"<b>" + campo + r":</b>\s*<span>([^<]+)</span>", b)
            if g:
                info[chiave] = html.unescape(g.group(1)).strip()
        film[idf] = info

    for idf, info in film.items():
        bigl = scarica(f"{CS}{cin['path']}ticket/?idf={idf}")
        i = bigl.find('id="salaFilmList"')
        if i < 0:
            continue
        sezione = bigl[i:]
        # Ogni versione (normale, O.V., IMAX...) ha il suo blocco con il proprio titolo.
        for versione_html in sezione.split('<p class="h1">')[1:]:
            versione = testo_pulito(versione_html.split("</p>", 1)[0])
            tag = etichette(versione)
            giorno = None
            for t in re.finditer(r'<span class="day">(\d{1,2})</span>\s*<span class="month">([A-Za-z]+)</span>'
                                 r'|<button([^>]*)>\s*(\d{1,2}:\d{2})\s*</button>', versione_html):
                if t.group(1):
                    giorno = data_da(t.group(1), t.group(2), rif)
                elif giorno:
                    attr = t.group(3)
                    s = {"k": chiave_film(info["titolo"]), "d": giorno.isoformat(), "h": t.group(4).zfill(5)}
                    sala = re.search(r'title="([^"]*)"', attr)
                    if sala and sala.group(1).strip():
                        s["sala"] = sala.group(1).strip().title()
                    url = re.search(r'data-url="([^"]+)"', attr)
                    if url:
                        s["url"] = html.unescape(url.group(1)).split("#")[0]
                    if tag:
                        s["tag"] = tag
                    spett.append(s)
    return list(film.values()), spett


# ---------------------------------------------------------------- Teatro Italia (Pontassieve)

def spettacoli_da_righe(linee, chiave, rif, richiedi_ore=False):
    """Righe tipo 'Venerdì 20 novembre' seguite da '19:00 in sala piccola' / 'Ore 19.00 in sala grande'."""
    out, giorno = [], None
    for r in linee:
        d = DATA_RE.fullmatch(r.rstrip(":"))
        if d:
            giorno = data_da(d.group(1), d.group(2), rif)
            continue
        o = re.fullmatch(r"(ore\s*)?([01]?\d|2[0-3])[.:]([0-5]\d)(?:\s+(?:in\s+)?(.*))?", r, re.I)
        if o and giorno and (o.group(1) or not richiedi_ore):
            s = {"k": chiave, "d": giorno.isoformat(), "h": f"{int(o.group(2)):02d}:{o.group(3)}"}
            if o.group(4):
                s["sala"] = o.group(4).strip().capitalize()
            out.append(s)
        else:
            giorno = None
    return out


def da_italia(cin, rif):
    pagina = scarica(cin["sito"])
    film, spett = [], []
    for card in pagina.split('<article class="calendario-card')[1:]:
        m = re.search(r'class="calendario-card__title"><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        if not m:
            continue
        url, titolo = m.group(1), titolo_leggibile(testo_pulito(m.group(2)))
        k = chiave_film(titolo)
        info = {"titolo": titolo}
        img = re.search(r'data-orig-src="([^"]+)"', card) or re.search(r'<img[^>]+src="(https?://[^"]+)"', card)
        if img:
            info["immagine"] = img.group(1)
        # La pagina del film ha tutti i giorni (la scheda solo i primi) e, quando le due
        # non coincidono, è la più aggiornata: la scheda si usa solo se la pagina non si legge.
        try:
            trovati = spettacoli_da_righe(righe(scarica(url)), k, rif, richiedi_ore=True)
        except Exception as e:
            print(f"  [italia] dettaglio non letto ({url}): {e}", file=sys.stderr)
            trovati = []
        if not trovati:
            trovati = spettacoli_da_righe(righe(card), k, rif)
        if trovati:
            film.append(info)
            spett += trovati
    return film, spett


# ---------------------------------------------------------------- Il Girone (Fiesole)

def da_girone(cin, rif):
    pagina = scarica(cin["sito"])
    link = sorted(set(re.findall(r'href="(https://www\.ilgirone\.it/arci/evento/[^"#?]+/)"', pagina)))
    film, spett = [], []
    for url in link:
        p = scarica(url)
        t = re.search(r'<meta property="og:title" content="([^"]+)"', p) or re.search(r"<title>([^<]+)", p)
        titolo = html.unescape(t.group(1)).split(" - Circolo")[0] if t else url.rstrip("/").rsplit("/", 1)[-1]
        tag = []
        mer = re.match(r"cinema a merenda\s*[–-]\s*(.+)", titolo, re.I)
        if mer:
            titolo, tag = mer.group(1), ["Cinema a merenda"]
        titolo = titolo_leggibile(titolo)
        k = chiave_film(titolo)
        info = {"titolo": titolo}
        img = re.search(r'<meta property="og:image" content="([^"]+)"', p)
        if img:
            info["immagine"] = img.group(1)

        linee = righe(p)
        trovati = []
        try:
            inizio = next(i for i, r in enumerate(linee) if r.strip().upper() == "PROGRAMMAZIONE")
        except StopIteration:
            inizio = None
        if inizio is not None:
            giorno = None
            for r in linee[inizio + 1:inizio + 40]:
                if re.search(r"non vedi l|iscriviti|data e ora", r, re.I):
                    break
                d = DATA_RE.search(r)
                resto = r
                if d:
                    giorno = data_da(d.group(1), d.group(2), rif)
                    resto = r[d.end():]
                if giorno:
                    for o in ORA_RE.finditer(resto):
                        trovati.append({"k": k, "d": giorno.isoformat(), "h": f"{int(o.group(1)):02d}:{o.group(2)}"})
        if not trovati:  # eventi singoli: "Data e ora | 21/11/2026 | 16:00"
            for i, r in enumerate(linee):
                if r.lower() == "data e ora":
                    blocco = " ".join(linee[i + 1:i + 5])
                    d = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*(?:-|\s)\s*(\d{1,2})[.:](\d{2})", blocco)
                    if d:
                        trovati.append({"k": k, "d": f"{d.group(3)}-{d.group(2)}-{d.group(1)}",
                                        "h": f"{int(d.group(4)):02d}:{d.group(5)}"})
                    break
        for s in trovati:
            if tag:
                s["tag"] = tag
        if trovati:
            film.append(info)
            spett += trovati
    return film, spett


FONTI = {"comingsoon": da_comingsoon, "italia": da_italia, "girone": da_girone}


# ---------------------------------------------------------------- main

def carica_precedente(sorgente):
    if not sorgente:
        return None
    try:
        if re.match(r"https?://", sorgente):
            return json.loads(scarica(sorgente))
        return json.loads(Path(sorgente).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Dati precedenti non disponibili ({sorgente}): {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "site" / "data" / "programmazione.json"))
    ap.add_argument("--prev", default=None)
    ap.add_argument("--solo", default=None, help="id dei cinema da aggiornare, separati da virgola")
    args = ap.parse_args()

    rif = oggi()
    adesso = dt.datetime.now(ROMA).isoformat(timespec="seconds")
    prec = carica_precedente(args.prev)
    solo = set(args.solo.split(",")) if args.solo else None

    film = {}         # chiave -> info
    spettacoli = []
    errori, aggiornato = {}, {}

    def aggiungi_film(info, da_comingsoon):
        k = chiave_film(info["titolo"])
        if k not in film:
            film[k] = dict(info)
        else:  # i dati di ComingSoon (titolo e locandina) hanno la precedenza
            for c, v in info.items():
                if c not in film[k] or (da_comingsoon and c in ("titolo", "locandina")):
                    film[k][c] = v

    for cin in CINEMA:
        if solo and cin["id"] not in solo:
            continue
        print(f"→ {cin['nome']}…", file=sys.stderr)
        try:
            lista, sp = FONTI[cin["fonte"]](cin, rif)
            if not sp:
                raise RuntimeError("nessuno spettacolo trovato")
            for info in lista:
                aggiungi_film(info, cin["fonte"] == "comingsoon")
            for s in sp:
                s["c"] = cin["id"]
            spettacoli += sp
            aggiornato[cin["id"]] = adesso
            print(f"   {len(lista)} film, {len(sp)} spettacoli", file=sys.stderr)
        except Exception as e:
            errori[cin["id"]] = f"{type(e).__name__}: {e}"
            print(f"   ERRORE: {errori[cin['id']]}", file=sys.stderr)
            if prec:  # riusa i dati della volta precedente per questo cinema
                vecchi = [s for s in prec.get("spettacoli", []) if s.get("c") == cin["id"]]
                for s in vecchi:
                    spettacoli.append(s)
                    if s["k"] not in film and s["k"] in prec.get("film", {}):
                        film[s["k"]] = prec["film"][s["k"]]
                if prec.get("aggiornato", {}).get(cin["id"]):
                    aggiornato[cin["id"]] = prec["aggiornato"][cin["id"]]

    # pulizia: niente giorni passati, niente doppioni, ordine per data/ora
    visti, puliti = set(), []
    for s in spettacoli:
        if s["d"] < rif.isoformat():
            continue
        chiave = (s["c"], s["k"], s["d"], s["h"], tuple(s.get("tag", [])))
        if chiave in visti:
            continue
        visti.add(chiave)
        puliti.append(s)
    puliti.sort(key=lambda s: (s["d"], s["h"], s["c"], s["k"]))
    usati = {s["k"] for s in puliti}

    dati = {
        "generato": adesso,
        "cinema": [{k: c[k] for k in ("id", "nome", "zona", "sito")} for c in CINEMA],
        "film": {k: v for k, v in sorted(film.items()) if k in usati},
        "spettacoli": puliti,
        "aggiornato": aggiornato,
        "errori": errori,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dati, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Salvato {out}: {len(dati['film'])} film, {len(puliti)} spettacoli, errori: {list(errori) or 'nessuno'}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
