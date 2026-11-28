"use strict";

const DATI_URL = "data/programmazione.json";
const NOTTE_FINO_A = "05:00"; // spettacoli prima di quest'ora = notte del giorno indicato
const GIORNI = ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"];
const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...figli) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of figli.flat()) if (f != null && f !== false) n.append(f);
  return n;
};

// ------------------------------------------------------------ memoria locale (preferenze)
const mem = {
  leggi(k, def) { try { const v = localStorage.getItem("cf." + k); return v == null ? def : JSON.parse(v); } catch { return def; } },
  scrivi(k, v) { try { localStorage.setItem("cf." + k, JSON.stringify(v)); } catch { /* niente */ } },
};

const stato = {
  dati: null,
  giorno: null,
  esclusi: new Set(mem.leggi("esclusi", [])),
  q: "",
  vista: mem.leggi("vista", "tabella"),
  mostraPassati: false,
  fissati: new Set(mem.leggi("fissati", [])),   // film sempre in cima (chiave film)
  nascosti: new Set(mem.leggi("nascosti", [])), // film tolti dalla vista
  mostraNascosti: false,
};

// ------------------------------------------------------------ utilità date/ore
const isoLocale = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
// Fino alle 5 di notte "oggi" è ancora la giornata di ieri: lo spettacolo dell'1:00 sotto "sabato" è sabato notte.
const oggiIso = () => isoLocale(new Date(Date.now() - 5 * 3600e3));
const dopoIso = (s, n = 1) => { const d = daIso(s); d.setDate(d.getDate() + n); return isoLocale(d); };
const daIso = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
const eNotte = (h) => h < NOTTE_FINO_A;
const chiaveOra = (h) => (eNotte(h) ? "2" : "1") + h; // la notte va in fondo alla giornata
const oraAdesso = () => { const n = new Date(); return `${String(n.getHours()).padStart(2, "0")}:${String(n.getMinutes()).padStart(2, "0")}`; };

function passato(s) {
  const oggi = oggiIso();
  if (s.d !== oggi) return s.d < oggi;
  return chiaveOra(s.h) < chiaveOra(oraAdesso()); // la notte (00:00–05:00) viene dopo la sera
}

const normalizza = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[.'’]/g, "").replace(/[^a-z0-9]+/g, " ").trim();

function etichettaTag(t) {
  return { "Lingua originale": "Orig.", "Cinema a merenda": "Bimbi", "Dolby Atmos": "Atmos", "Ospiti in sala": "Ospiti" }[t] || t;
}

// ------------------------------------------------------------ caricamento
async function carica() {
  try {
    const r = await fetch(DATI_URL, { cache: "no-cache" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    stato.dati = await r.json();
  } catch (e) {
    $("#contenuto").replaceChildren(el("div", { class: "stato" },
      el("strong", {}, "Non riesco a caricare gli orari"),
      "Controlla la connessione e riprova.",
      el("br"), el("button", { onclick: () => location.reload() }, "Riprova")));
    return;
  }
  const giorni = giorniDisponibili();
  const oggi = oggiIso();
  stato.giorno = giorni.includes(oggi) ? oggi : (giorni.find((g) => g >= oggi) || giorni[0] || oggi);
  disegnaTutto();
}

function giorniDisponibili() {
  const oggi = oggiIso();
  const set = new Set(stato.dati.spettacoli.map((s) => s.d).filter((d) => d >= oggi));
  set.add(oggi);
  return [...set].sort().slice(0, 14);
}

// ------------------------------------------------------------ disegno
function disegnaTutto() {
  disegnaGiorni();
  disegnaCinema();
  disegnaVista();
  disegnaPiede();
}

function disegnaGiorni() {
  const oggi = oggiIso();
  const domani = dopoIso(oggi);
  const box = $("#giorni");
  box.replaceChildren(...giorniDisponibili().map((g) => {
    const d = daIso(g);
    const sopra = g === oggi ? "Oggi" : g === domani ? "Domani" : GIORNI[d.getDay()];
    return el("button", {
      class: "giorno", "aria-pressed": String(g === stato.giorno), "data-g": g,
      onclick: () => { stato.giorno = g; stato.mostraPassati = false; disegnaGiorni(); disegnaVista(); $("#contenuto").scrollTo(0, 0); },
    }, el("span", { class: "gs" }, sopra), el("span", { class: "gn" }, String(d.getDate())), el("span", { class: "gm" }, MESI[d.getMonth()]));
  }));
  box.querySelector('[aria-pressed="true"]')?.scrollIntoView({ inline: "nearest", block: "nearest" });
}

function disegnaCinema() {
  const lista = stato.dati.cinema;
  const tuttiAttivi = lista.every((c) => !stato.esclusi.has(c.id));
  const box = $("#cinema");
  box.replaceChildren(
    el("button", {
      class: "chip tutti", "aria-pressed": String(tuttiAttivi),
      onclick: () => {
        if (tuttiAttivi) lista.forEach((c) => stato.esclusi.add(c.id)); else stato.esclusi.clear();
        salvaEsclusi(); disegnaCinema(); disegnaVista();
      },
    }, tuttiAttivi ? "Nessuno" : "Tutti"),
    ...lista.map((c) => el("button", {
      class: "chip", "aria-pressed": String(!stato.esclusi.has(c.id)), title: c.zona,
      onclick: () => {
        stato.esclusi.has(c.id) ? stato.esclusi.delete(c.id) : stato.esclusi.add(c.id);
        salvaEsclusi(); disegnaCinema(); disegnaVista();
      },
    }, c.nome)),
  );
}
const salvaEsclusi = () => mem.scrivi("esclusi", [...stato.esclusi]);

// Spettacoli del giorno nei cinema attivi (e che corrispondono alla ricerca).
// I film nascosti si vedono solo se li si cerca per nome o si sceglie "Mostra".
function spettacoliFiltrati() {
  const termini = stato.q.split(",").map(normalizza).filter(Boolean);
  const film = stato.dati.film;
  const tutti = stato.dati.spettacoli.filter((s) => {
    if (s.d !== stato.giorno || stato.esclusi.has(s.c)) return false;
    if (!termini.length) return true;
    const t = normalizza(film[s.k]?.titolo || s.k);
    return termini.some((q) => t.includes(q));
  });
  const vediNascosti = termini.length > 0 || stato.mostraNascosti;
  const sp = vediNascosti ? tutti : tutti.filter((s) => !stato.nascosti.has(s.k));
  const nascostiOggi = new Set(tutti.filter((s) => stato.nascosti.has(s.k)).map((s) => s.k));
  return { sp, nascostiOggi, vediNascosti };
}

// ------------------------------------------------------------ film fissati / nascosti
const titoloDi = (k) => stato.dati.film[k]?.titolo || k;
const ordinaFilm = (a, b) => (stato.fissati.has(b) - stato.fissati.has(a)) || titoloDi(a).localeCompare(titoloDi(b), "it");

function fissa(k) {
  stato.fissati.has(k) ? stato.fissati.delete(k) : stato.fissati.add(k);
  mem.scrivi("fissati", [...stato.fissati]);
  disegnaVista();
}

function nascondi(k) {
  stato.nascosti.add(k);
  mem.scrivi("nascosti", [...stato.nascosti]);
  disegnaVista();
  avviso(`"${titoloDi(k)}" nascosto`, "Annulla", () => mostra(k));
}

function mostra(k) {
  document.querySelector(".toast")?.remove(); // l'avviso "… nascosto" non vale più
  clearTimeout(timerAvviso);
  stato.nascosti.delete(k);
  mem.scrivi("nascosti", [...stato.nascosti]);
  disegnaVista();
}

let timerAvviso;
function avviso(testo, azione, fn) {
  document.querySelector(".toast")?.remove();
  clearTimeout(timerAvviso);
  const t = el("div", { class: "toast", role: "status" }, el("span", {}, testo),
    el("button", { onclick: () => { t.remove(); fn(); } }, azione));
  document.body.append(t);
  timerAvviso = setTimeout(() => t.remove(), 5000);
}

// Scheda di presentazione del film: ricerca Google (mostra trama, cast, trailer...).
const schedaFilm = (k) => "https://www.google.com/search?q=" + encodeURIComponent(titoloDi(k) + " film");

const ICONA_PIN = () => {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", "M15 3l6 6-3 1-4 4 1 5-2 2-4-4-5 5-1-1 5-5-4-4 2-2 5 1 4-4z");
  svg.append(path);
  return svg;
};

function azioniFilm(k) {
  const fiss = stato.fissati.has(k);
  if (stato.nascosti.has(k)) {
    return el("div", { class: "azioni" },
      el("button", { class: "az rimetti", onclick: () => mostra(k), "aria-label": "Rimetti " + titoloDi(k) }, "Rimetti"));
  }
  return el("div", { class: "azioni" },
    el("button", { class: "az pin", "aria-pressed": String(fiss), onclick: () => fissa(k),
      "aria-label": (fiss ? "Togli dall'alto " : "Fissa in alto ") + titoloDi(k), title: fiss ? "Fissato in alto" : "Fissa in alto" }, ICONA_PIN()),
    el("button", { class: "az nascondi", onclick: () => nascondi(k),
      "aria-label": "Nascondi " + titoloDi(k), title: "Nascondi questo film" }, "✕"));
}

function disegnaVista() {
  document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.vista === stato.vista)));
  const box = $("#contenuto");
  const { sp, nascostiOggi, vediNascosti } = spettacoliFiltrati();
  const attivi = stato.dati.cinema.filter((c) => !stato.esclusi.has(c.id));

  if (!attivi.length) {
    box.replaceChildren(el("div", { class: "stato" }, el("strong", {}, "Nessun cinema selezionato"), "Tocca i nomi dei cinema qui sopra per includerli."));
    return;
  }
  const barraNascosti = nascostiOggi.size && !stato.q ? el("button", {
    class: "mostra-passati nascosti-btn",
    onclick: () => { stato.mostraNascosti = !stato.mostraNascosti; disegnaVista(); },
  }, vediNascosti ? "Nascondi di nuovo i film tolti"
    : `${nascostiOggi.size} ${nascostiOggi.size === 1 ? "film nascosto" : "film nascosti"} · Mostra`) : null;

  if (!sp.length) {
    box.replaceChildren(el("div", { class: "stato" },
      el("strong", {}, stato.q ? "Nessun risultato" : "Nessuna proiezione"),
      stato.q ? `"${stato.q}" non è in programma in questo giorno nei cinema selezionati.`
        : nascostiOggi.size ? "Hai nascosto tutti i film in programma in questo giorno."
          : "Nessun film in programma in questo giorno nei cinema selezionati."), barraNascosti || "");
    return;
  }
  box.replaceChildren(stato.vista === "orari" ? vistaOrari(sp) : vistaTabella(sp, attivi), barraNascosti || "");
}

function locandina(f, classe) {
  const src = f?.locandina || f?.immagine;
  if (!src) return null;
  return el("img", { class: classe + (f.locandina ? "" : " largo"), src, alt: "", loading: "lazy", decoding: "async", referrerpolicy: "no-referrer" });
}

function pill(s) {
  const pas = passato(s);
  const tags = (s.tag || []).filter((t) => !(s.sala || "").toUpperCase().includes(t.toUpperCase())).map(etichettaTag);
  if (eNotte(s.h)) tags.push("notte");
  const tag = tags.join(" · ");
  const titolo = [s.sala, ...(s.tag || []), eNotte(s.h) ? "notte" : null, pas ? "già iniziato" : null].filter(Boolean).join(" · ");
  const attrs = { class: "pill" + (pas ? " passato" : "") + (eNotte(s.h) ? " notte" : ""), title: titolo || null };
  const figli = [s.h, tag ? el("span", { class: "tg" }, tag) : null];
  const link = s.p || s.url; // pagina del film in quel cinema (orari + acquisto), un passo prima del pagamento
  return link && !pas ? el("a", { ...attrs, href: link, target: "_blank", rel: "noopener" }, ...figli) : el("span", attrs, ...figli);
}

function vistaTabella(sp, attivi) {
  const film = stato.dati.film;
  const perCella = new Map(); // "k|c" -> [spettacoli]
  for (const s of sp) {
    const key = s.k + "|" + s.c;
    if (!perCella.has(key)) perCella.set(key, []);
    perCella.get(key).push(s);
  }
  const colonne = attivi.filter((c) => sp.some((s) => s.c === c.id));
  const senza = attivi.filter((c) => !colonne.includes(c));
  const righe = [...new Set(sp.map((s) => s.k))].sort(ordinaFilm);

  const tabella = el("table", { class: "tabella" },
    el("thead", {}, el("tr", {},
      el("th", { class: "angolo" }, `${righe.length} film`),
      ...colonne.map((c) => el("th", { scope: "col" }, el("span", { class: "cn" }, c.nome), el("span", { class: "cz" }, c.zona))))),
    el("tbody", {}, ...righe.map((k) => el("tr", { class: [stato.fissati.has(k) && "fissato", stato.nascosti.has(k) && "nascosto"].filter(Boolean).join(" ") || null },
      el("th", { scope: "row", class: "film-th" },
        el("a", { class: "scheda", href: schedaFilm(k), target: "_blank", rel: "noopener", title: "Scheda del film" },
          locandina(film[k], "poster"),
          el("span", { class: "tit" }, film[k]?.titolo || k)),
        film[k]?.durata ? el("span", { class: "dur" }, film[k].durata.replace(" Minuti", " min")) : null,
        azioniFilm(k)),
      ...colonne.map((c) => {
        const lista = (perCella.get(k + "|" + c.id) || []).sort((a, b) => chiaveOra(a.h).localeCompare(chiaveOra(b.h)));
        return lista.length ? el("td", {}, el("div", { class: "pills" }, lista.map(pill))) : el("td", { class: "vuota" });
      })))));

  const frammento = document.createDocumentFragment();
  frammento.append(tabella);
  if (senza.length) frammento.append(el("p", { class: "nota" }, "Niente in programma in questo giorno a: " + senza.map((c) => c.nome).join(", ") + "."));
  return frammento;
}

function vistaOrari(sp) {
  const film = stato.dati.film;
  const cinema = Object.fromEntries(stato.dati.cinema.map((c) => [c.id, c]));
  const ordinati = [...sp].sort((a, b) => chiaveOra(a.h).localeCompare(chiaveOra(b.h)) || a.c.localeCompare(b.c));
  const giaIniziati = ordinati.filter(passato);
  const visibili = stato.mostraPassati ? ordinati : ordinati.filter((s) => !passato(s));

  const fascia = (h) => eNotte(h) ? "Notte" : h < "13:00" ? "Mattina" : h < "17:00" ? "Pomeriggio" : h < "20:00" ? "Tardo pomeriggio" : "Sera";
  const ul = el("ul", { class: "elenco" });
  let ultima = null;
  for (const s of visibili) {
    const fa = fascia(s.h);
    if (fa !== ultima) { ul.append(el("li", { class: "fascia" }, fa)); ultima = fa; }
    const f = film[s.k];
    const pas = passato(s);
    const dettagli = [el("b", {}, cinema[s.c]?.nome || s.c), s.sala ? " · " + s.sala : null,
      s.tag?.length ? el("span", { class: "tg" }, " · " + s.tag.join(" · ")) : null];
    const link = s.p || s.url;
    const ora = link && !pas
      ? el("a", { class: "ora", href: link, target: "_blank", rel: "noopener", title: "Orari e biglietti" }, s.h)
      : el("span", { class: "ora" }, s.h);
    const img = f?.locandina || f?.immagine;
    ul.append(el("li", {}, el("div", { class: "riga" + (pas ? " passato" : "") + (stato.nascosti.has(s.k) ? " nascosto" : "") },
      ora,
      el("a", { class: "scheda", href: schedaFilm(s.k), target: "_blank", rel: "noopener", title: "Scheda del film" },
        img ? el("img", { class: "mini" + (f.locandina ? "" : " largo"), src: img, alt: "", loading: "lazy", referrerpolicy: "no-referrer" }) : el("span", { class: "mini vuota" }),
        el("div", { class: "info" },
          el("div", { class: "rt" }, stato.fissati.has(s.k) ? el("span", { class: "pin-segno", title: "Fissato" }, ICONA_PIN()) : null, f?.titolo || s.k),
          el("div", { class: "rc" }, ...dettagli))))));
  }
  const fr = document.createDocumentFragment();
  if (giaIniziati.length) {
    fr.append(el("button", {
      class: "mostra-passati",
      onclick: () => { stato.mostraPassati = !stato.mostraPassati; disegnaVista(); },
    }, stato.mostraPassati ? "Nascondi quelli già iniziati" : `Mostra anche i ${giaIniziati.length} già iniziati`));
  }
  if (!visibili.length) fr.append(el("div", { class: "stato" }, el("strong", {}, "Per oggi è finita"), "Tutti gli spettacoli di oggi sono già iniziati. Guarda domani!"));
  fr.append(ul);
  return fr;
}

function disegnaPiede() {
  const d = stato.dati;
  const g = new Date(d.generato);
  const quando = `${GIORNI[g.getDay()].toLowerCase()} ${g.getDate()} ${MESI[g.getMonth()]}, ${String(g.getHours()).padStart(2, "0")}:${String(g.getMinutes()).padStart(2, "0")}`;
  const figli = [el("span", {}, "Aggiornato " + quando), el("span", {}, "Dati: ", el("a", { href: "https://www.comingsoon.it/cinema/firenze/", target: "_blank", rel: "noopener" }, "ComingSoon"), " e siti dei cinema")];
  const conErrori = Object.keys(d.errori || {});
  if (conErrori.length) {
    const nomi = conErrori.map((id) => d.cinema.find((c) => c.id === id)?.nome || id);
    figli.push(el("span", { class: "avviso" }, `⚠ Orari non aggiornati oggi per: ${nomi.join(", ")} (mostro gli ultimi letti).`));
  }
  $("#piede").replaceChildren(...figli);
}

// ------------------------------------------------------------ eventi
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  stato.vista = b.dataset.vista; mem.scrivi("vista", stato.vista);
  if (stato.dati) { disegnaVista(); $("#contenuto").scrollTo(0, 0); }
}));

const boxCerca = $("#cerca"), inputQ = $("#q"), btnCerca = $("#btn-cerca");
btnCerca.addEventListener("click", () => {
  const apri = boxCerca.hidden;
  boxCerca.hidden = !apri;
  btnCerca.setAttribute("aria-expanded", String(apri));
  if (apri) inputQ.focus();
  else if (stato.q) { stato.q = ""; inputQ.value = ""; btnCerca.classList.remove("attivo"); disegnaVista(); }
});
let timer;
inputQ.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(() => { stato.q = inputQ.value.trim(); btnCerca.classList.toggle("attivo", !!stato.q); if (stato.dati) disegnaVista(); }, 120);
});
inputQ.addEventListener("keydown", (e) => { if (e.key === "Enter") inputQ.blur(); });
$("#pulisci").addEventListener("click", () => { inputQ.value = ""; stato.q = ""; btnCerca.classList.remove("attivo"); inputQ.focus(); if (stato.dati) disegnaVista(); });

// Riaprendo l'app dopo un po' (es. il giorno dopo) ricarica dati e orari "passati".
let ultimaVisita = Date.now();
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  if (Date.now() - ultimaVisita > 30 * 60e3) carica(); else if (stato.dati) disegnaVista();
  ultimaVisita = Date.now();
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}

carica();
