# AstaPilot Mobile v1.0

Questa release è una Progressive Web App mobile-first installabile su iPhone e Android, servita dallo stesso backend FastAPI.

## Avvio locale

```bash
./run_local.sh
```

Aprire `http://localhost:8000`.

## Installazione su smartphone

In produzione servire l'app tramite HTTPS. Su iPhone: Safari → Condividi → Aggiungi alla schermata Home. Su Android: Chrome → Installa app/Aggiungi a schermata Home. Il manifest e il service worker sono già inclusi.

## Funzioni incluse

- UI mobile con bottom navigation e installazione PWA.
- Discovery e ricerca automatica delle aste dal motore AstaPilot esistente.
- Dettaglio asta con Asta Score, Confidence e Critical Flags.
- Registrazione/login con password PBKDF2 e session token server-side.
- Preferiti per utente.
- Piani Free, Plus, Investor, Pro ed entitlement model.
- Paywall per analisi avanzata e simulatore.
- Stripe Checkout via API REST senza dipendenza SDK.
- Webhook Stripe firmato e idempotente per attivazione/disattivazione piani.
- Offline app-shell caching per la PWA.
- Dockerfile e docker-compose per deployment.

## Produzione: valori obbligatori

Copiare `.env.example` in `.env` e impostare dominio HTTPS, chiavi Stripe e Price IDs. Configurare nel dashboard Stripe il webhook `https://DOMINIO/api/billing/webhook` con gli eventi `checkout.session.completed`, `customer.subscription.updated` e `customer.subscription.deleted`.

## App Store / Play Store

La codebase mobile è già adatta a essere wrappata con Capacitor/TWA. Per pubblicare sugli store servono account Apple/Google, certificati di firma, bundle identifier definitivo, privacy policy e asset store. Queste credenziali non sono incluse nel sorgente.

## Importante

La copertura nazionale dipende dall'attivazione di feed/API/accordi autorizzati con le fonti. Il codice mantiene il PVP come punto di integrazione ufficiale, ma non inventa endpoint privati.
