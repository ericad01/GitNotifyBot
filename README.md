# Git Notify Bot

Il **Git Notify Bot** (o GitHub Commit Tracker Bot) è un bot Telegram progettato per monitorare in tempo reale l'attività di una o più repository GitHub, permettendoti quindi di ricevere notifiche automatiche ogni volta che vengono effettuate delle modifiche al codice.


## Funzionalità Principali

Il bot offre una serie di strumenti per restare sempre aggiornati sullo sviluppo dei progetti direttamente da Telegram:

* **Monitoraggio Repository:** aggiungi facilmente una o più repository (pubbliche o private) da tenere d'occhio.
* **Notifiche Push & Release:** ricevi avvisi automatici in caso di nuove push o quando viene pubblicata una nuova release.
* **Integrazione GitHub OAuth:** collega in modo sicuro il tuo account GitHub per autorizzare il bot ad accedere alle tue repository private.
* **Filtri per Branch:** scegli esattamente quale branch monitorare (es. `main`, `develop`, `release`) per concentrarti solo sugli aggiornamenti che ti interessano.


## Sistema di Notifiche Intelligente

Per evitare lo spam e l'eccesso di notifiche, il bot raggruppa le informazioni inviando messaggi chiari e concisi. Ogni notifica includerà:

* Un riepilogo dei nuovi commit effettuati.
* Gli autori coinvolti nelle modifiche.
* Link diretti ai commit su GitHub per una verifica rapida.


## Interfaccia

L’interazione con il bot è semplice e avviene interamente tramite comandi Telegram. Attraverso l'interfaccia potrai:

* Aggiungere o rimuovere rapidamente le repository dalla tua lista.
* Scegliere il branch specifico da monitorare per ogni repository.
* Gestire, attivare o disattivare le notifiche in base alle tue esigenze.


## Comandi disponibili
* `/start` | Mostra il menu principale con lo stato di autenticazione |
* `/login` | Avvia il flusso OAuth per collegare l'account GitHub |
* `/logout` | Disconnette l'account e rimuove tutti i monitoraggi |
* `/add owner/repo [branch]` | Inizia a monitorare un branch (default: `main`) |
* `/addrelease owner/repo` | Monitora le release di una repository |
* `/list` | Elenca tutte le repository e i branch monitorati |
* `/remove owner/repo [branch]` | Rimuove il monitoraggio (branch specifico o tutta la repo) |


## Requisiti

* Python 3.10 o superiore


## Configurazione

1. **Clona il repository:**

```bash
git clone https://github.com/<owner>/GitNotifyBot.git
cd GitNotifyBot
```

2. **Crea e attiva un ambiente virtuale (opzionale ma consigliato):**

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

3. **Installa le dipendenze:**

```bash
pip install -r requirements.txt
```

Per lo sviluppo e il testing installa anche:

```bash
pip install -r requirements_dev.txt
```

4. **Configura le variabili d'ambiente:**

Copia il file di esempio e compilalo con i tuoi valori:

```bash
cp .env.example .env
```

Modifica il file `.env`:

```env
TELEGRAM_TOKEN=il_tuo_token_telegram
GITHUB_CLIENT_ID=il_tuo_client_id_github
GITHUB_CLIENT_SECRET=il_tuo_client_secret_github
OAUTH_REDIRECT_URI=https://<tuo-dominio>/callback
```

| Variabile | Descrizione |
|---|---|
| `TELEGRAM_TOKEN` | Token del bot ottenuto da @BotFather |
| `GITHUB_CLIENT_ID` | Client ID dell'app OAuth GitHub |
| `GITHUB_CLIENT_SECRET` | Client Secret dell'app OAuth GitHub |
| `OAUTH_REDIRECT_URI` | URL di callback pubblico per GitHub OAuth |


## Avvio

Avvia il bot con:

```bash
python script.py
```

Il server OAuth Flask viene avviato automaticamente sulla porta `5000`. Assicurati che l'URL configurato in `OAUTH_REDIRECT_URI` punti al tuo server sulla rotta `/callback`.


## Testing e Qualità del Codice

Per eseguire i test:

```bash
pytest --cov=. --cov-report=term-missing
```

Per controllare la qualità del codice (gli stessi controlli eseguiti nella pipeline CI):

```bash
black --check .          # formattazione
isort --check-only .     # ordine degli import
pylint config.py oauth_server.py script.py
mypy config.py oauth_server.py script.py --ignore-missing-imports
```

Per applicare automaticamente la formattazione:

```bash
black .
isort .
```


## Team di Sviluppo

Questo progetto è sviluppato e mantenuto da:

* [@ericad01](https://github.com/ericad01)
* [@giuliopedicone02](https://github.com/giuliopedicone02)
* [@VincenzoVillanova](https://github.com/VincenzoVillanova)
* [@Ciccio1307](https://github.com/Ciccio1307)
