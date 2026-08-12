# DriveWise Decision Engine – Calibration Report v0.4

**Nota:** calibrazione eseguita su scenari sintetici e dataset mock. Serve a calibrare il comportamento dell'MVP, non a validare raccomandazioni automotive reali.

## Metriche

| Metrica | v0.3 | v0.4 |
|---|---:|---:|
| Top-1 accuracy | 58.3% | 58.3% |
| Top-2 acceptance | 83.3% | 83.3% |
| MRR | 0.840 | 0.847 |

## Pesi calibrati

- `economics`: 0.267
- `practicality`: 0.178
- `reliability_safety`: 0.222
- `driving`: 0.111
- `technology`: 0.111
- `powertrain_fit`: 0.111

## Osservazioni

- Il benchmark usa più risposte accettabili in alcuni scenari: per questo Top-2 acceptance e MRR sono più significativi della sola Top-1.
- Il motore rimane deterministico: l'LLM non determina il ranking.
- La calibrazione reale dovrà essere ripetuta su dataset verificato e valutazioni umane raccolte da utenti/tester.

Il dettaglio finale e le correzioni che portano alla v1.0 sono documentati in `FINAL_CALIBRATION_REPORT.md`.
