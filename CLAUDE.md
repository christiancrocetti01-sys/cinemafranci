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

## Da chiarire / in attesa
- [ ] Lista esatta dei ~10 cinema con i rispettivi siti web.
- [ ] Dove ospitare il sito (proposta: GitHub Pages + GitHub Actions che fa lo scraping ogni giorno, tutto gratis).
- [ ] Va usato soprattutto da telefono? (si presume di sì → design mobile-first)

## Decisioni prese
- Sito web (non app nativa).

## Stato attuale
- Repo creato, nessun codice ancora. Raccolta requisiti fatta.

## Note tecniche
- Branch di sviluppo: `claude/relaxed-tesla-obj9y3`.
