# AstaPilot Mobile v1.0

Prima release mobile-first installabile. Riunisce il motore AstaPilot v1 commerciale e una PWA smartphone pronta per deployment HTTPS.

## Nuovo
- Interfaccia mobile con bottom navigation.
- Installazione PWA iOS/Android.
- Auth reale server-side, sessioni e password PBKDF2.
- Preferiti persistenti per account.
- Piani Free / Plus / Investor / Pro.
- Stripe Checkout e webhook firmato/idempotente.
- Paywall e feature gating iniziale.
- Ricerca aste e dettaglio con Asta Score, Confidence e rischi.
- Docker deployment one-service.

## Scelte di prodotto
Le criticità C4 restano visibili anche ai Free. I dettagli proprietari, provenance, simulazioni e workflow avanzati sono monetizzabili. L'analisi documentale centrale è riutilizzata fra utenti per proteggere i margini.
