# F1 — Curare le prime 12 auto in produzione

Questo è il percorso operativo che sblocca ADR-017. Il dominio pubblico passa alla
build unificata quando il modulo auto raccomanda le prime 12 auto in produzione.
Ogni passo dice chi lo fa, cosa produce e come si verifica.

Fonti delle regole: [DECISIONS.md](DECISIONS.md) (ADR-013, ADR-015, ADR-017,
ADR-018), [catalog-v2.md](catalog-v2.md), [open-data-import.md](open-data-import.md),
[source-review.md](source-review.md).

## 0. Le 12 auto

ADR-015 dice "le dodici auto dell'attuale sito pubblico". Il repository non le
elenca da nessuna parte, quindi la lista va scritta qui prima di iniziare.
Andrea e Tommaso la copiano dal sito pubblico attuale e la firmano.

| # | Marca | Modello | `canonical_key` nel catalogo | Varianti curate |
| --- | --- | --- | --- | --- |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |
| 11 | | | | |
| 12 | | | | |

Ogni auto deve già esistere nel bundle open data (`cars.catalog-v2.json`). Se
manca, si aggiunge prima a `data/open-data/car-names.it.json` e si ricostruisce il
bundle, come spiega [open-data-import.md](open-data-import.md).

## 1. Campi richiesti

### Bloccanti per il go-live

L'Advisor esclude una variante senza tipo di carrozzeria, posti, bagagliaio o
consumo (`_SPEC_EXCLUSION_CASES` in `apps/api/app/repositories/advisor.py`).
Senza offerta autorizzata la valuta al prezzo di listino (ADR-013), quindi senza
prezzo la esclude con `missing_list_price`. Posti e consumo arrivano dagli open
data. Questi tre campi invece vanno curati:

| Campo | Regola | Fonte |
| --- | --- | --- |
| `list_price_eur` | Prezzo di listino pubblico IVA inclusa, non chiavi in mano. Ogni osservazione porta i `ListPriceTerms` di ADR-015: `printed_amount_eur`, `printed_basis` (`incl_vat`, `excl_vat` o `turnkey`), `vat_rate_percent` quando il listino è senza IVA, la messa su strada quando è chiavi in mano, `trim_label`, `price_list_valid_from` e `substitute_note` quando la versione immatricolata non è più a listino. | Listino ufficiale del costruttore |
| `cargo_volume_liters` | Contesto obbligatorio `method = "VDA"` e `seating_configuration = "all_seats_up"`. Gli altri contesti si salvano ma non arrivano mai al catalogo letto. | Scheda tecnica ufficiale del costruttore |
| `body_style` del veicolo | Gli open data lo danno a 1 veicolo su 100 ([open-data-gaps.md](open-data-gaps.md)). Un bundle successivo lo riempie aggiungendo all'identità del veicolo lo snapshot che lo dichiara (migrazione `0014`, [catalog-v2.md](catalog-v2.md)). | Scheda tecnica o listino del costruttore |

Il valore calcolato (da listino senza IVA o da chiavi in mano) resta marcato come
calcolato, e l'interfaccia lo dice. Il validatore e il vincolo SQL di `0011`
controllano già i termini: un bundle con termini incompleti non passa `--check`.

### Dopo il go-live: larghezza per il garage

Garage Fit dell'Advisor (`services/advisor/garage.py`) e il controllo garage del
flusso guidato (`services/guided_decisions/engine.py`) confrontano la porta del
garage con `width_mirrors_folded_mm`. Oggi questa metrica non esiste nel dominio
`catalog_metric`: esiste solo `width_with_mirrors_mm` (specchi aperti). Per
questo la porta resta senza verdetto (`insufficient_data`), anche quando
lunghezza, larghezza carrozzeria (`body_width_mm`) e altezza sono note.

Serve una decisione di prodotto di Andrea e Tommaso, prima di toccare il codice:

1. **Regola dell'intervallo (consigliata).** La larghezza a specchi chiusi sta tra
   `body_width_mm` e `width_with_mirrors_mm`. Se la porta supera
   `width_with_mirrors_mm`, l'auto passa. Se la porta è sotto `body_width_mm`,
   l'auto non passa. In mezzo, il verdetto resta `insufficient_data` e il report
   lo spiega. Non serve una nuova fonte e non si inventa nessun valore.
2. **Nuova metrica.** Si aggiunge `width_mirrors_folded_mm` al dominio e alle
   regole di unità, e la si cura dalle schede tecniche. È più precisa, ma pochi
   costruttori italiani la pubblicano.

Questa decisione non blocca ADR-017: il go-live richiede solo i due campi sopra.

### Già coperti dagli open data

Dimensioni, potenza, cilindrata, posti, consumo e CO2 arrivano da EEA e RDW. Dalla
migrazione `0015` il catalogo letto (`catalog_read_specs`) pubblica anche
lunghezza, larghezza carrozzeria, altezza, cilindrata e potenza delle varianti v2,
quindi la pagina veicolo e l'Advisor leggono gli stessi valori. Un consumo dato
come intervallo si pubblica al valore superiore (ADR-018).

## 2. Firmare le source review

Una fonte influenza il ranking solo con `ranking_permission = "permitted"`, e solo
dopo una review firmata. Le tre bozze esistono già, ma nessuna è firmata.

EEA e RDW non servono solo per i loro valori. L'identità di ogni veicolo open data
(marca, modello, variante) poggia sui loro snapshot, e un fatto è idoneo solo se
tutta l'identità viene da fonti `permitted` (`catalog_identity_eligibility`,
migrazione `0009`). Finché EEA e RDW restano `manual_validation_only`, anche un
listino firmato non porta nessuna delle 12 auto nel ranking.

Per ognuna di [eea-co2-cars.md](source-reviews/eea-co2-cars.md),
[rdw-open-data.md](source-reviews/rdw-open-data.md) e
[motospecdb.md](source-reviews/motospecdb.md):

1. Rileggere i termini di licenza alla data di oggi e scrivere la data.
2. Spuntare le caselle su archiviazione degli snapshot e ranking derivati.
3. Scrivere il testo di attribuzione richiesto.
4. Indicare il punto dell'interfaccia in cui appare l'attribuzione. Per EEA questo
   punto manca ancora e blocca `permitted`: va creato nel frontend (Andrea).
5. Decidere frequenza e responsabile della nuova osservazione.
6. Scrivere decisione, nome del revisore, data e prossimo trigger di review.

MotoSpecDB riguarda le due ruote, che restano senza punteggio (ADR-017). La sua
firma non blocca F1.

Per i listini e le schede tecniche dei costruttori serve una review nuova:

1. Copiare [source-review.md](source-review.md) in
   `docs/source-reviews/manufacturer-price-lists.md`, una sezione per costruttore.
2. Per ogni costruttore annotare l'URL del listino, i termini d'uso del sito e la
   data di lettura.
3. Indicare le metriche ammesse: `list_price_eur` e `cargo_volume_liters`, nient'altro.
4. Firmare la decisione. Senza firma, la fonte resta `manual_validation_only` e i
   prezzi non entrano nel ranking.

### Come una fonte diventa `permitted`

Il publish inserisce una fonte solo se la sua `source_key` non esiste ancora
(`ON CONFLICT DO NOTHING` in `catalog_v2_writer.py`). Quindi:

1. **Fonte nuova** (il listino di un costruttore): scrivere
   `"ranking_permission": "permitted"` nel record `sources` del bundle solo dopo la
   firma. Il primo publish fissa il permesso.
2. **Fonte già pubblicata** (EEA e RDW, che il builder open data scrive come
   `manual_validation_only`): reimportare non cambia niente. Dopo la firma, una
   persona esegue sul database, solo per le fonti con la review firmata:

   ```sql
   UPDATE sources SET ranking_permission = 'permitted'
   WHERE source_key IN ('eea-co2-cars', 'rdw-open-data');
   ```

   La revoca è lo stesso comando con `manual_validation_only`, e ha effetto alla
   lettura successiva, senza ripubblicare.

## 3. Sequenza CLI

### Chi produce il bundle F1

Il bundle aggiunge prezzi, bagagliaio e carrozzeria alle varianti già pubblicate
dal bundle open data. Ci sono due strade:

1. **A mano (costo zero, consigliata per 12 auto).** Si scrive il JSON v2 seguendo
   [catalog-v2.md](catalog-v2.md): uno snapshot per documento, un'osservazione e
   una decisione `verified` per valore, con estratto e posizione nel documento.
2. **Agente di raccolta** (`apps/api/scripts/scrape_catalog.py`,
   [scraping.md](scraping.md)). Produce un bundle e un report delle lacune, ma
   richiede chiavi OpenRouter e Tinyfish a pagamento: serve prima il via libera di
   Andrea sul budget.

In entrambi i casi il bundle deve riusare le identità già pubblicate. Il publish
sul database di prova (che ha già il bundle open data) lo verifica: il numero di
veicoli non deve cambiare, e le 12 auto devono avere i nuovi valori.

### Comandi

Si lancia dalla radice del repository. I file originali (PDF dei listini, pagine
delle schede) stanno in `data/private/catalog/`, che Git ignora. Il bundle si
pubblica prima su un database di prova, poi su Neon di produzione.

```sh
ROOT=data/private/catalog
BUNDLE=$ROOT/f1-twelve-cars/cars.catalog-v2.json

# 1. Controllo offline del contratto e degli hash di ogni artefatto.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --check "$BUNDLE" --artifact-root "$ROOT"

# 2. Migrazioni sul database in DATABASE_URL (prima la prova, poi produzione).
uv run --frozen --project apps/api python apps/api/scripts/migrate.py

# 3. Stage: valida di nuovo e salva il bundle, senza toccare il catalogo.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --stage "$BUNDLE" --artifact-root "$ROOT"

# 4. Publish: sostituire BATCH_ID con l'UUID stampato dallo stage.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --publish BATCH_ID --artifact-root "$ROOT"
```

Lo stage è idempotente e un secondo publish dello stesso batch risponde
`unchanged`. Un errore annulla tutta la pubblicazione e il batch resta in stage.
`migrate.py` prende un advisory lock: due deploy concorrenti non applicano due
volte la stessa migrazione.

## 4. Verifiche dopo il publish

Ogni verifica gira su produzione e il suo risultato va annotato qui, con la data.

1. **Versione dello schema.** `GET /api/version` deve riportare
   `schema_version = "0015_catalog_v2_read_view_pivot.sql"` (o una migrazione più
   recente) e lo `scoring_version` atteso.
2. **Campi bloccanti.** Questa query deve restituire 12 righe, tutte con
   `ready = true`:

   ```sql
   SELECT v.canonical_key,
          bool_or(s.list_price_eur IS NOT NULL AND s.cargo_volume_liters IS NOT NULL) AS ready
   FROM vehicles v
   JOIN catalog_read_specs s ON s.vehicle_id = v.id
   WHERE v.canonical_key = ANY(ARRAY['...'])  -- le 12 chiavi della tabella al punto 0
   GROUP BY v.canonical_key
   ORDER BY v.canonical_key;
   ```

3. **Piano di lettura.** Prendere l'`id` di una delle 12 auto ed eseguire:

   ```sql
   EXPLAIN (ANALYZE, BUFFERS)
   SELECT * FROM catalog_read_specs WHERE vehicle_id = '<vehicle_id>';
   ```

   Il piano deve mostrare `Index Cond: (spec_id = s.id)` dentro il `WindowAgg` e
   `One-Time Filter: (s.catalog_version = 2)`. Un `Seq Scan` su `fact_decisions`
   senza quella condizione vuol dire che il filtro per variante non scende nella
   vista: fermarsi e aprire un issue.
4. **Raccomandazione 12 su 12.** Questo controllo è in sola lettura. Passare le 12
   chiavi della tabella al punto 0:

   ```sh
   uv run --frozen --project apps/api python - KEY1 KEY2 ... KEY12 <<'EOF'
   import os, sys
   from collections import defaultdict
   import psycopg
   from psycopg.rows import dict_row
   from app.repositories.advisor import AdvisorRepository

   keys = set(sys.argv[1:])
   with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
       conn.execute("SET TRANSACTION READ ONLY")
       repository = AdvisorRepository(conn)
       found = defaultdict(set)
       for candidate in repository.list_candidates():
           if candidate["vehicle"]["canonical_key"] in keys:
               found[candidate["vehicle"]["canonical_key"]].add(candidate["price_basis"])
       print(f"rankable: {len(found)}/{len(keys)}")
       for key in sorted(keys):
           print(key, sorted(found[key]) or "MISSING")
       print(repository.count_excluded_candidates())
   EOF
   ```

   Deve stampare `rankable: 12/12`. Senza offerte, ogni auto compare con
   `list_price`. Un motivo `source_not_permitted` o `missing_list_price` indica una
   review non firmata o un prezzo senza termini. Non usare
   `scripts/catalog_status.py` per questo controllo: oggi conta solo le offerte e
   si interrompe sulle alternative a prezzo di listino.
5. **Flusso pubblico.** Su `drivewise-italia.com` percorrere `/app/start` →
   `/app/report` → `/app/vehicle/$id` → `/app/compare` con budget e usi diversi,
   finché tutte le 12 auto sono comparse almeno una volta. Ogni fonte deve aprirsi
   su un URL reale `https://`, mai `example.test`.

## 5. Quando passare a un feed commerciale

Motornet e Infocar vendono listini e schede italiane con licenza. Costano, quindi
la scelta spetta ad Andrea e Tommaso insieme. Dopo la validazione della fase 1
(le 12 auto in produzione), proporre il passaggio quando vale almeno una di
queste condizioni, misurata e scritta qui. Le soglie sono una proposta, da
confermare con Andrea e Tommaso:

1. **Costo di curazione.** Curare e aggiornare una variante richiede in media più
   di 30 minuti di lavoro umano per listino.
2. **Ampiezza.** Il prodotto deve raccomandare più di 50 modelli, oppure tutte le
   versioni a listino invece della sola versione più immatricolata.
3. **Freschezza.** I listini cambiano più spesso di quanto la curazione riesca a
   seguire: più del 20% dei prezzi pubblicati è superato da un listino più recente.
4. **Diritti.** Un costruttore vieta il riuso del suo listino, oppure una source
   review non può essere firmata.
5. **Campi mancanti.** Servono campi che i documenti pubblici non danno in modo
   uniforme, come `width_mirrors_folded_mm`, la massa a vuoto o le versioni uscite
   di listino.

Prima di firmare un contratto: chiedere una licenza di prova, importare le stesse
12 auto e confrontare valore per valore con la curazione manuale. Il feed entra
come nuova fonte, con la sua source review, accanto alle fonti esistenti.
