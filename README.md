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


## Team di Sviluppo

Questo progetto è sviluppato e mantenuto da:

* [@ericad01](https://github.com/ericad01)
* [@giuliopedicone02](https://github.com/giuliopedicone02)
* [@VincenzoVillanova](https://github.com/VincenzoVillanova)
* [@Ciccio1307](https://github.com/Ciccio1307)
