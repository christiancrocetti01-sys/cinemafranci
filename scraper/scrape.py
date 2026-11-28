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
import urllib.parse
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
     "fonte": "comingsoon", "path": "/cinema/firenze/uci-cinemas-campi-bisenzio/2510/",
     "mymovies": "https://www.mymovies.it/cinema/firenze/campibisenzio/5748/"},
    {"id": "space", "nome": "The Space Novoli", "zona": "Firenze",
     "sito": "https://www.thespacecinema.it/cinema/firenze/al-cinema",
     "fonte": "comingsoon", "path": "/cinema/firenze/the-space-cinema-firenze-novoli/5396/",
     "mymovies": "https://www.mymovies.it/cinema/firenze/21354/"},
    {"id": "fiorella", "nome": "Fiorella", "zona": "Firenze",
     "sito": "https://www.circuitocinema.com/cinema/fiorella/",
     "fonte": "comingsoon", "path": "/cinema/firenze/fiorella/1400/", "ufficiale": "fiorella"},
    {"id": "marconi", "nome": "Marconi", "zona": "Firenze",
     "sito": "https://www.staseraalcinema.it/multisala-marconi/",
     "fonte": "comingsoon", "path": "/cinema/firenze/marconi/1411/", "ufficiale": "stasera"},
    {"id": "principe", "nome": "Principe", "zona": "Firenze",
     "sito": "https://www.staseraalcinema.it/multisala-principe/",
     "fonte": "comingsoon", "path": "/cinema/firenze/principe/1415/", "ufficiale": "stasera"},
    {"id": "portico", "nome": "Il Portico", "zona": "Firenze",
     "sito": "https://www.cinemailportico.it/programmazione.php",
     "fonte": "comingsoon", "path": "/cinema/firenze/portico/1414/", "ufficiale": "portico"},
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
    # Fino alle 5 di notte vale ancora la "giornata" di ieri (spettacoli dopo mezzanotte).
    return (dt.datetime.now(ROMA) - dt.timedelta(hours=5)).date()


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
    return re.sub(r"(?<=[a-zà-ÿ])[À-Þ]", lambda m: m.group().lower(), t)  # "SuccederÀ" -> "Succederà"


# Code nei titoli dei siti ufficiali: "WILD HORSE NINE - Dal 5 Novembre.", "MUSTANG - Evento in REPLICA da ...",
# "Succederà questa notte - Ospiti in sala". "Lorenzo - L'incredibile avventura..." invece resta com'è.
CODA_RE = re.compile(r"(?:\s+[-–]\s+(?:dal\b|da\s+(?:\d|oggi|" + GIORNI_RE + r")|evento\b|in replica\b|anteprima\b|"
                     r"solo\b|ultimi giorni\b)|\s*[-–:]?\s+ospiti in sala\b).*$", re.I)


def titolo_ufficiale(t):
    """Titolo dal sito di un cinema -> (titolo pulito, tag extra)."""
    t = testo_pulito(t)
    tag = ["Ospiti in sala"] if re.search(r"ospiti in sala", t, re.I) else []
    return titolo_leggibile(CODA_RE.sub("", t).rstrip(" .")), tag


def data_da_numero(giorno, rif):
    """Solo il giorno del mese (es. "Mar 01"): la data con quel numero più vicina a oggi."""
    for delta in range(-10, 21):
        d = rif + dt.timedelta(days=delta)
        if d.day == int(giorno):
            return d
    raise ValueError(f"giorno {giorno} non riconosciuto")


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

def film_da_pagina(pagina):
    """Schede film di una pagina ComingSoon (cinema o città): idf -> {titolo, locandina, genere, durata}."""
    film = {}
    for b in pagina.split('class="header-scheda')[1:]:
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
    return film


# Film da controllare oltre a quelli elencati oggi nella pagina del cinema (vedi da_comingsoon).
EXTRA = {"citta": {}, "prev": {}}


def prepara_extra(prec):
    """ComingSoon elenca nella pagina del cinema solo i film che hanno spettacoli OGGI: un film che
    quel cinema proietta solo domani o nei giorni dopo non compare (es. il 28/11 "Il rumore delle
    cose nuove" al The Space solo il 29). Per non perderli si controllano anche tutti i film in
    programma oggi a Firenze e provincia, e quelli già trovati in quel cinema l'ultima volta."""
    try:
        EXTRA["citta"] = film_da_pagina(scarica(CS + "/cinema/firenze/"))
    except Exception as e:
        print(f"Elenco film di Firenze non disponibile: {e}", file=sys.stderr)
    for s in (prec or {}).get("spettacoli", []):
        m = re.search(r"/ticket/\?idf=(\d+)", s.get("p", ""))
        info = (prec.get("film") or {}).get(s["k"])
        if m and info and info.get("titolo"):
            EXTRA["prev"].setdefault(s["c"], {})[m.group(1)] = info


def da_comingsoon(cin, rif):
    film = film_da_pagina(scarica(CS + cin["path"]))
    elencati = set(film)
    for fonte in (EXTRA["prev"].get(cin["id"], {}), EXTRA["citta"]):
        for idf, info in fonte.items():
            film.setdefault(idf, dict(info))
    spett = []
    con_spettacoli = set()

    for idf, info in film.items():
        pagina_film = f"{CS}{cin['path']}ticket/?idf={idf}"  # orari di quel film in quel cinema + acquisto
        try:
            bigl = scarica(pagina_film)
        except Exception:
            if idf in elencati:
                raise
            continue  # film extra: se la pagina non risponde pazienza
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
                    s = {"k": chiave_film(info["titolo"]), "d": giorno.isoformat(), "h": t.group(4).zfill(5),
                         "p": pagina_film}
                    sala = re.search(r'title="([^"]*)"', attr)
                    if sala and sala.group(1).strip():
                        s["sala"] = sala.group(1).strip().title()
                    url = re.search(r'data-url="([^"]+)"', attr)
                    if url:
                        s["url"] = html.unescape(url.group(1)).split("#")[0]
                    if tag:
                        s["tag"] = tag
                    spett.append(s)
                    con_spettacoli.add(idf)
    return [dict(film[i], _cs=True) for i in film if i in con_spettacoli], spett


# ---------------------------------------------------------------- siti ufficiali (Fiorella, Marconi, Principe, Portico)
# ComingSoon non conosce i film che un cinema proietta solo nei giorni dopo (se oggi non sono in nessun
# cinema di Firenze) né gli eventi lontani (es. "ospiti in sala" fra 2 settimane), e a volte salta un orario.
# Dove il sito del cinema si legge bene vale quello; ComingSoon aggiunge sala e link d'acquisto.

def nuovo_spettacolo(k, giorno, ora, pagina, url=None, tag=None):
    s = {"k": k, "d": giorno.isoformat(), "h": ora.zfill(5), "p": pagina}
    if url:
        s["url"] = url
    if tag:
        s["tag"] = tag
    return s


def da_fiorella(cin, rif):
    """circuitocinema.com: tabella "Film in sala" con righe = film e colonne = giorni."""
    pagina = scarica(cin["sito"])
    date = [data_da(g, m, rif) for g, m in re.findall(r'<span class="dm">(\d{1,2})\s+([A-Za-zì]+)</span>', pagina)]
    if not date:
        raise RuntimeError("tabella degli orari non trovata")
    film, spett = [], []
    for riga in pagina.split('<th class="headcol">')[1:]:
        tit = re.search(r'<h6 class="title">(.*?)</h6>', riga, re.S)
        if not tit:
            continue
        titolo, tag = titolo_ufficiale(tit.group(1))
        tag += [testo_pulito(t).capitalize() for t in re.findall(r'<span class="tag"[^>]*>(.*?)</span>', riga, re.S)
                if testo_pulito(t).capitalize() not in tag]
        k = chiave_film(titolo)
        link = re.search(r'<a class="movie" href="([^"]+)"', riga)
        info = {"titolo": titolo}
        img = re.search(r'<img class="cover" src="([^"]+)"', riga)
        if img:
            info["locandina"] = html.unescape(img.group(1))
        celle = riga.split("</th>", 1)[-1].split('<td class="col">')[1:]
        if len(celle) != len(date):
            raise RuntimeError(f"{titolo}: {len(celle)} colonne invece di {len(date)}")
        trovati = [nuovo_spettacolo(k, d, h, link.group(1) if link else cin["sito"], html.unescape(u).split("#")[0], tag)
                   for d, cella in zip(date, celle)
                   for u, h in re.findall(r'<a class="time" href="([^"]+)"[^>]*>\s*(\d{1,2}:\d{2})\s*</a>', cella)]
        if trovati:
            film.append(info)
            spett += trovati
    return film, spett


def da_stasera(cin, rif):
    """staseraalcinema.it (Marconi, Principe): una pagina per giorno, ?d=AAAA-MM-GG 00:00:00."""
    base = cin["sito"]
    pagina = scarica(base)
    giorni = sorted(set(re.findall(r"\?d=(\d{4}-\d\d-\d\d) 00:00:00", pagina)))
    if not giorni:
        raise RuntimeError("elenco dei giorni non trovato")
    film, spett = {}, []
    for g in giorni:
        p = scarica(base + "?d=" + urllib.parse.quote(g + " 00:00:00"))
        if not re.search(r"\?d=" + g + r" 00:00:00'><div class='bott_date_scheda_at'", p):
            raise RuntimeError(f"la pagina del {g} non mostra quel giorno")
        pezzi = p[p.find("Seleziona giorno"):].split("<h5 ")
        for prima, blocco in zip(pezzi, pezzi[1:]):
            tit = re.search(r"<a href='(/scheda-film/[^']+)'[^>]*title='Vai alla Scheda del Film'[^>]*>([^<]+)</a>", blocco)
            if not tit:
                continue
            titolo, tag = titolo_ufficiale(tit.group(2))
            k = chiave_film(titolo)
            scheda = urllib.parse.urljoin(base, html.unescape(tit.group(1)))
            for u, h in re.findall(r"(?:<a href='([^']+)'\s*>)?<div class='bott_orari[^']*'>\s*(\d{1,2}:\d{2})\s*</div>", blocco):
                spett.append(nuovo_spettacolo(k, dt.date.fromisoformat(g), h, scheda,
                                              urllib.parse.urljoin(base, html.unescape(u)) if u else None, tag))
                if k not in film:
                    film[k] = {"titolo": titolo}
                    img = re.findall(r"<img src='(https://secure\.webtic\.it/HandlerLocandina[^']+)'", prima)
                    if img:
                        film[k]["locandina"] = html.unescape(img[-1])
    return list(film.values()), spett


def da_portico(cin, rif):
    """cinemailportico.it/programmazione.php: una scheda per giorno della settimana (#thu, #fri, ...)."""
    pagina = scarica(cin["sito"])
    schede = re.findall(r'<a href="#(\w+)" class="giorno_w_\d">\s*\w+\s+(\d{1,2})\s*</a>', pagina)
    if not schede:
        raise RuntimeError("giorni non trovati")
    inizi = []
    for ancora, g in schede:
        i = pagina.find(f"<div id='{ancora}'>")
        if i < 0:
            raise RuntimeError(f"scheda {ancora} non trovata")
        inizi.append((i, data_da_numero(g, rif)))
    inizi.sort()
    film, spett = {}, []
    for n, (i, giorno) in enumerate(inizi):
        blocco = pagina[i:inizi[n + 1][0] if n + 1 < len(inizi) else len(pagina)]
        for f in blocco.split("<div class='row movie-tabs'>")[1:]:
            tit = re.search(r"<h3 class='no-underline'>(.*?)</h3>", f, re.S)
            if not tit:
                continue
            titolo, tag = titolo_ufficiale(tit.group(1))
            k = chiave_film(titolo)
            link = re.search(r"href='(film-singolo\.php[^']+)'", f)
            scheda = urllib.parse.urljoin(cin["sito"], html.unescape(link.group(1))) if link else cin["sito"]
            for h, versione in re.findall(r"<span class='time'>\s*(\d{1,2}:\d{2})\s*(?:<b>(.*?)</b>)?\s*</span>", f):
                spett.append(nuovo_spettacolo(k, giorno, h, scheda, None, tag + etichette(versione)))
                if k not in film:
                    film[k] = {"titolo": titolo}
                    img = re.search(r"<img itemprop='image' src='([^']+)'", f)
                    if img:
                        film[k]["locandina"] = html.unescape(img.group(1))
    return list(film.values()), spett


UFFICIALI = {"fiorella": da_fiorella, "stasera": da_stasera, "portico": da_portico}


def unisci(uff_film, uff_sp, cs_film, cs_sp):
    """Orari del sito ufficiale + dettagli di ComingSoon (sala, acquisto, versione) quando lo spettacolo coincide.
    I giorni che il sito ufficiale non elenca affatto si prendono da ComingSoon."""
    cs = {}
    for s in cs_sp:
        cs.setdefault((s["k"], s["d"], s["h"]), s)
    for s in uff_sp:
        c = cs.get((s["k"], s["d"], s["h"]))
        if not c:
            continue
        s["p"] = c["p"]  # pagina ComingSoon del film in quel cinema: orari + pulsanti d'acquisto
        for campo in ("sala", "url"):
            if campo in c:
                s.setdefault(campo, c[campo])
        tag = s.get("tag", []) + [t for t in c.get("tag", []) if t not in s.get("tag", [])]
        if tag:
            s["tag"] = tag
    giorni_uff = {s["d"] for s in uff_sp}
    return uff_film + cs_film, uff_sp + [s for s in cs_sp if s["d"] not in giorni_uff]


# ---------------------------------------------------------------- MyMovies (riserva per UCI e The Space, solo oggi)

def da_mymovies(cin, rif):
    """Spettacoli di oggi su MyMovies (pagina del cinema): film con titolo in maiuscolo, poi gli orari."""
    pagina = scarica(cin["mymovies"])
    titoli = [m for m in re.finditer(r'<a href="(https://www\.mymovies\.it/film/[^"]+)" title="([^"]+)">([^<]+)</a>', pagina)
              if m.group(3).strip().isupper()]
    film = []
    for m, dopo in zip(titoli, titoli[1:] + [None]):
        corpo = pagina[m.end():dopo.start() if dopo else len(pagina)]
        ore = sorted({h.zfill(5) for h in re.findall(r'<span class="mm-medium mm-weight-700">\s*(\d{1,2}:\d{2})\s*</span>', corpo)})
        if ore:
            info = {"titolo": titolo_leggibile(html.unescape(m.group(2)))}
            img = re.findall(r'class="poster-schedina[^"]*"[^>]*src="([^"]+)"', pagina[max(0, m.start() - 3000):m.start()])
            if img:
                info["locandina"] = img[-1]
            film.append((info, ore))
    return film


def integra_mymovies(cin, rif, cs_film, cs_sp):
    """Aggiunge i film di OGGI che MyMovies ha e ComingSoon no (es. "La luce del mondo" al The Space il 28/11).
    Si aggiungono solo gli spettacoli non ancora iniziati (ComingSoon toglie quelli già iniziati, quindi
    il confronto si fa su quelli) e solo se non sono lo stesso film con un titolo scritto diversamente."""
    oggi_iso = rif.isoformat()
    adesso = dt.datetime.now(ROMA).strftime("%H:%M")
    if dt.datetime.now(ROMA).date() != rif:  # dopo mezzanotte: MyMovies mostra già il giorno nuovo
        return cs_film, cs_sp
    ore_cs = {}
    for s in cs_sp:
        if s["d"] == oggi_iso:
            ore_cs.setdefault(s["k"], set()).add(s["h"])
    film, spett = list(cs_film), list(cs_sp)
    for info, ore in da_mymovies(cin, rif):
        k = chiave_film(info["titolo"])
        future = [h for h in ore if h >= adesso and h >= "05:00"]
        if not future or k in ore_cs or any(set(future) <= v for v in ore_cs.values()):
            continue
        print(f"   + da MyMovies: {info['titolo']} {future}", file=sys.stderr)
        film.append(info)
        spett += [nuovo_spettacolo(k, rif, h, cin["mymovies"]) for h in future]
    return film, spett


def da_cinema_cs(cin, rif):
    """Cinema presenti su ComingSoon, con eventuale sito ufficiale o MyMovies a integrare."""
    try:
        cs_film, cs_sp = da_comingsoon(cin, rif)
        errore_cs = None
    except Exception as e:
        cs_film, cs_sp, errore_cs = [], [], e
    if cin.get("ufficiale"):
        try:
            uff_film, uff_sp = UFFICIALI[cin["ufficiale"]](cin, rif)
            if uff_sp:
                print(f"   sito ufficiale: {len(uff_sp)} spettacoli, ComingSoon: {len(cs_sp)}", file=sys.stderr)
                return unisci(uff_film, uff_sp, cs_film, cs_sp)
            print("   sito ufficiale vuoto: uso solo ComingSoon", file=sys.stderr)
        except Exception as e:
            print(f"   sito ufficiale non letto ({type(e).__name__}: {e}): uso solo ComingSoon", file=sys.stderr)
    if errore_cs:
        raise errore_cs
    if cin.get("mymovies"):
        try:
            return integra_mymovies(cin, rif, cs_film, cs_sp)
        except Exception as e:
            print(f"   MyMovies non letto ({type(e).__name__}: {e})", file=sys.stderr)
    return cs_film, cs_sp


# ---------------------------------------------------------------- Teatro Italia (Pontassieve)

def spettacoli_da_righe(linee, chiave, rif, richiedi_ore=False):
    """Righe tipo 'Venerdì 20 novembre' seguite da '19:00 in sala piccola' / 'Ore 19.00 in sala grande'."""
    out, giorno, altre = [], None, 0
    for r in linee:
        d = DATA_RE.fullmatch(r.rstrip(":"))
        if d:
            giorno, altre = data_da(d.group(1), d.group(2), rif), 0
            continue
        o = re.fullmatch(r"(ore\s*)?([01]?\d|2[0-3])[.:]([0-5]\d)(?:\s+(?:in\s+)?(.*))?", r, re.I)
        if o and giorno and (o.group(1) or not richiedi_ore):
            s = {"k": chiave, "d": giorno.isoformat(), "h": f"{int(o.group(2)):02d}:{o.group(3)}"}
            if o.group(4):
                s["sala"] = o.group(4).strip().capitalize()
            out.append(s)
            altre = 0
        else:
            # Una nota sotto un orario ("evento speciale Disney: vestiti da strega...") non chiude il giorno:
            # il 28/11 si perdeva così "Hexe" delle 18:00. Si chiude dopo 2 righe di seguito senza orari.
            altre += 1
            if altre > 2:
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
        for s in trovati:
            s["p"] = url
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
                    # "ore 16.00 merenda offerta dal circolo; ore 16.30 proiezione del film":
                    # se la riga distingue, teniamo solo l'orario della proiezione.
                    pezzi = re.split(r"[;,]", resto)
                    proiez = [x for x in pezzi if ORA_RE.search(x) and re.search(r"proiez|inizio film", x, re.I)]
                    if proiez:
                        resto = " ".join(proiez)
                    else:
                        resto = " ".join(x for x in pezzi
                                         if not re.search(r"merenda|aperitiv|cena|apertura|buffet", x, re.I)) or resto
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
            s["p"] = url
            if tag:
                s["tag"] = tag
        if trovati:
            film.append(info)
            spett += trovati
    return film, spett


FONTI = {"comingsoon": da_cinema_cs, "italia": da_italia, "girone": da_girone}


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
    prepara_extra(prec)
    solo = set(args.solo.split(",")) if args.solo else None

    film = {}         # chiave -> info
    spettacoli = []
    errori, aggiornato = {}, {}

    def aggiungi_film(info):
        k = chiave_film(info["titolo"])
        if k not in film:
            film[k] = dict(info)
        else:  # i dati di ComingSoon (titolo e locandina) hanno la precedenza
            for c, v in info.items():
                if c not in film[k] or (info.get("_cs") and c in ("titolo", "locandina", "_cs")):
                    film[k][c] = v

    for cin in CINEMA:
        if solo and cin["id"] not in solo:
            continue
        print(f"→ {cin['nome']}…", file=sys.stderr)
        try:
            lista, sp = FONTI[cin["fonte"]](cin, rif)
            if not sp:  # a volte la fonte è vuota per poco (es. ComingSoon mentre aggiorna): si riprova
                time.sleep(60)
                lista, sp = FONTI[cin["fonte"]](cin, rif)
            if not sp:
                raise RuntimeError("nessuno spettacolo trovato")
            for info in lista:
                aggiungi_film(info)
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

    # Film presi solo da un sito ufficiale o da MyMovies: titolo e locandina come su ComingSoon se lo conosce.
    noti = {chiave_film(i["titolo"]): i for i in EXTRA["citta"].values()}
    for k, info in film.items():
        if not info.get("_cs") and k in noti:
            for c, v in noti[k].items():
                if c in ("titolo", "locandina") or c not in info:
                    info[c] = v
        info.pop("_cs", None)

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
