# Aggiornamento ogni ora con cron-job.org

GitHub avvia gli aggiornamenti programmati quando vuole: anche chiedendo "ogni ora",
in pratica parte circa 2 volte al giorno. Per avere orari sempre freschi, un servizio
esterno gratuito (cron-job.org) fa partire l'aggiornamento ogni ora.

## 1. Crea un token GitHub (solo per questo repository)
1. Vai su https://github.com/settings/personal-access-tokens/new (token *fine-grained*).
2. Nome: `cinemafranci-aggiorna`. Scadenza: la più lunga possibile (o "No expiration").
3. **Repository access** → *Only select repositories* → `cinemafranci`.
4. **Permissions → Repository permissions → Actions: Read and write** (il resto lascialo com'è).
5. *Generate token* e copialo (inizia con `github_pat_...`). Non metterlo in nessun file del repository.

## 2. Crea il job su cron-job.org
1. Registrati su https://cron-job.org (gratis) e fai *Create cronjob*.
2. **URL**: `https://api.github.com/repos/christiancrocetti01-sys/cinemafranci/actions/workflows/aggiorna.yml/dispatches`
3. **Schedule**: ogni ora, al minuto 17, dalle 5 alle 23 (fuso Europe/Rome).
4. Scheda **Advanced**:
   - Request method: **POST**
   - Headers:
     - `Authorization`: `Bearer github_pat_...` (il token del punto 1)
     - `Accept`: `application/vnd.github+json`
     - `X-GitHub-Api-Version`: `2022-11-28`
     - `Content-Type`: `application/json` (senza, il test dava 422)
   - Request body: `{"ref":"main"}`
5. Salva e premi *Test run*: deve rispondere **204**. Poi su GitHub → Actions dovresti vedere
   partire "Aggiorna orari e pubblica" (evento `workflow_dispatch`).

Il cron di GitHub resta attivo come riserva.
