# DriveWise Decision Engine v1.0 – Final Calibration Report

## Esito

La v1.0 introduce un **Preference Alignment Layer** esplicito.

Il Decision Score finale è composto da:

- **65% Structural Fit**: Economics, Practicality, Reliability & Safety, Driving, Technology, Powertrain Fit, hard/soft constraints e penalità.
- **35% Preference Fit**: corrispondenza diretta con le prime tre priorità dichiarate dall'utente, pesate 50% / 30% / 20%.

## Perché è stato introdotto

La calibrazione v0.4 evidenziava due scenari fuori Top-2:
- `premium_safety`
- `sport_technology`

Il problema non era nei dati di base ma nel fatto che le priorità espresse dall'utente influenzavano soprattutto i pesi dei Pillar e non abbastanza le metriche specifiche sottostanti.

Esempio:
- `performance` deve valorizzare direttamente `Vehicle DNA → sport`;
- `safety` deve valorizzare direttamente il safety score;
- `technology` deve valorizzare direttamente il Technology DNA.

## Risultati benchmark v1.0

- Top-1 accuracy: **66.7%**
- Top-2 acceptance: **100.0%**
- MRR: **0.958**

La Top-2 acceptance raggiunge il **100% sui 12 scenari sintetici di calibrazione**.

## Decisione sui due casi problematici

### Premium Safety
Non abbiamo forzato Volvo artificialmente al primo posto. Con i dati mock disponibili, Kia può ancora risultare molto competitiva, ma Volvo entra ora correttamente nel Top-2. Questo è più coerente con un motore decisionale che con una regola di marca.

### Sport & Technology
Tesla Model Y passa al primo posto perché `performance`, `technology` e `comfort` vengono ora confrontati direttamente contro le priorità espresse dall'utente.

## Nota sul caso High Mileage
Non abbiamo forzato BMW X1 Diesel al primo posto. Toyota rimane una scelta accettabile secondo il benchmark perché Economics e Reliability sono molto forti nei dati mock. Questo scenario andrà rivalutato con dati reali su consumi autostradali, manutenzione e TCO.

## Stato

Questa versione è **v1.0 MVP frozen** per architettura e contratto.

Non significa che i pesi siano universalmente validati. La prossima calibrazione dovrà avvenire con:
- dataset automotive reale;
- almeno 30–50 profili;
- valutazioni umane;
- benchmark per categoria e motorizzazione.

Fino a quel momento le formule restano euristiche di prodotto, ma sono deterministiche, testabili e spiegabili.
