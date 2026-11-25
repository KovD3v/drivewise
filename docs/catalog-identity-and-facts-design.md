# Identità dei veicoli e forma dei fatti: proposta di design

Data: 25 novembre 2026. Stato: proposta. Nessuna migrazione e nessuna modifica al
codice.

Questo documento decide cosa archivia il catalogo per un veicolo e a quale riga
appartiene ogni valore. Prosegue la
[revisione del modello dati](data-architecture-review.md) di settembre e ne cambia
un punto: la chiave del veicolo.

## Perché adesso

Il catalogo di produzione non contiene ancora auto reali. Cambiare l'identità oggi
tocca solo dati sintetici. Dopo il primo rilascio tocca annunci, fatti firmati e
link condivisi dagli utenti.

## Decisioni di prodotto da cui parte

Tommaso le ha prese il 25 novembre 2026.

| Punto | Decisione |
| --- | --- |
| Grana | L'utente sceglie un modello con il suo motore, non un allestimento. |
| Primo dataset | Solo auto nuove, nella generazione in vendita. |
| Usato | Non incluso. Il modello deve accoglierlo senza cambiare identità. |
| Sicurezza | Euro NCAP sostituisce "affidabilità" nella promessa del prodotto. |
| Valori calcolati | Neopatentati, costo al chilometro e bollo si calcolano. Non si archiviano. |
| Dotazioni | Rimandate a dopo il primo rilascio. |

## Dove il modello attuale non regge

Ogni punto cita il codice che lo dimostra.

### La generazione non si può curare dopo la pubblicazione

Gli open data pubblicano ogni veicolo con `generation_key`, `body_style` e
`model_year` vuoti (`apps/api/app/ingestion/open_data.py`). Tutti e tre fanno parte
della chiave unica `vehicles_identity_v2_key`.

Una prova sul codice reale mostra due esiti, entrambi sbagliati:

- Un bundle successivo con la stessa `canonical_key` e la generazione compilata
  fallisce con `Published identity differs at generation_key`.
- Un bundle successivo con una `canonical_key` nuova passa. Il catalogo contiene
  allora due righe per la stessa auto: una senza generazione e una con.

`_publish_identity` in `apps/api/app/ingestion/catalog_v2_writer.py` blocca ogni
correzione di identità. L'unica eccezione è la carrozzeria.

### I fatti appartengono solo alla variante

`fact_decisions.spec_id` è obbligatorio. Un valore che vale per tutta la
generazione non ha una riga a cui legarsi. La carrozzeria è già in questa
situazione, ed è risolta con un caso speciale:

- una colonna sul veicolo,
- una prova aggiunta in coda a `identity_evidence`,
- una regola di lettura che attribuisce la carrozzeria all'ultimo snapshot
  (`0014`, `_fills_body_style`).

Euro NCAP e gli anni di produzione chiederebbero altri due casi speciali.

### I valori sono solo numeri

`spec_observations.value_min` e `value_max` sono obbligatori e maggiori di zero.
Classe Euro, carrozzeria e dotazioni sono categorie. Oggi non si possono scrivere
come fatti.

### L'elenco delle metriche è ripetuto

La stessa lista compare in sei file: le migrazioni `0008`, `0010` e `0011`,
`catalog_v2.py`, `docs/catalog-v2.schema.json` e
`apps/web/src/api/schema.gen.ts`. Ogni migrazione che aggiunge una metrica riscrive
per intero il vincolo del dominio `catalog_metric` e il controllo delle unità.

Comando che rigenera il conteggio:

	grep -rl "dc_peak_charge_power_kw" apps docs --include=*.sql --include=*.py --include=*.json --include=*.ts | grep -v "tests\|fixtures"

## Proposta

### Una riga veicolo è una generazione di un modello in un mercato

La chiave diventa marca, modello, tipo di veicolo, generazione, mercato.

- La generazione è obbligatoria per pubblicare. Un veicolo senza generazione resta
  nello staging.
- Carrozzeria, fase e anno modello escono dalla chiave.
- La carrozzeria diventa un fatto della variante. Una generazione con berlina e
  station wagon ha varianti con carrozzerie diverse sotto lo stesso veicolo.
- Il restyling è un periodo di validità sulle varianti e sui fatti (`valid_from`,
  `valid_to`). Non crea un veicolo nuovo.
- L'anno appartiene all'annuncio usato, come anno di prima immatricolazione.

Ogni campo della nuova chiave è noto al momento dell'import, tranne la generazione.
Per questo la generazione entra nel file dei nomi rivisto a mano
(`data/open-data/car-names.it.json`), che già separa due modelli con lo stesso nome
tramite i numeri di omologazione.

La revisione di settembre teneva carrozzeria e anno modello nell'identità. Questa
proposta li toglie perché sono vuoti all'import, e una chiave che si compila dopo è
una chiave che cambia.

### Un fatto appartiene a una generazione oppure a una variante

Ogni metrica dichiara il suo ambito.

| Ambito | Esempi |
| --- | --- |
| Generazione | Euro NCAP, anno di inizio e di fine produzione |
| Variante | potenza, consumo, misure, bagagliaio, prezzo, carrozzeria, classe Euro |

Una variante legge i propri fatti e quelli della sua generazione. Tutti passano
dalle stesse regole: fonte autorizzata, snapshot, osservazione, decisione firmata.
`_fills_body_style` e la regola dell'ultimo snapshot si cancellano.

### Un valore è un numero oppure un codice

Ogni metrica dichiara il tipo del suo valore.

- **Numero.** Un intervallo con unità, come oggi.
- **Codice.** Un valore da una lista chiusa che la metrica dichiara. Esempi:
  `body_style`, `euro_emission_standard`, e in futuro una dotazione con i valori
  `standard`, `available`, `not_available`.

Non serve un tipo sì/no. Un sì/no è un codice con due valori.

### Un solo registro delle metriche

Un file versionato elenca ogni metrica con nome, tipo di valore, unità o lista dei
codici, ambito e contesto richiesto. Il validatore Python, lo schema JSON e i
vincoli SQL derivano da quel file. Un test fallisce quando una delle copie non
coincide con il file.

La revisione di settembre proponeva già questo file. Non è mai stato scritto.

### Metriche nuove

| Metrica | Tipo | Ambito | Serve a |
| --- | --- | --- | --- |
| `body_style` | codice | variante | sostituisce la colonna di identità |
| `production_start_year`, `production_end_year` | numero | generazione | agganciare un annuncio usato |
| `ncap_stars` e i quattro punteggi | numero | generazione | sicurezza |
| `euro_emission_standard` | codice | variante | accesso alle ZTL per l'usato |

Il contesto di un fatto Euro NCAP porta l'anno del protocollo di prova. Cinque
stelle del 2015 e cinque stelle del 2024 non sono lo stesso voto.

`euro_emission_standard` si definisce ora e si compila quando arriva l'usato. Tra
le auto nuove non distingue nulla.

## Cosa cambia per l'usato

- Più generazioni dello stesso modello sono righe distinte, ognuna con i suoi anni
  di produzione.
- Un annuncio si lega a una variante, quindi a una generazione.
- Un annuncio di cui non si conosce la generazione resta `unresolved_spec`. Non si
  lega mai al modello in generale.
- Un prezzo di listino conserva la sua data. Quando un'auto esce di listino,
  l'ultimo prezzo resta come riferimento.

## Ordine di consegna

Ogni passo finisce con una verifica e si può rilasciare da solo.

1. **Registro delle metriche.** Nessun cambio di comportamento. Verifica: il test
   di coerenza passa e la suite esistente resta verde.
2. **Valori a codice.** Verifica: un fatto `euro_emission_standard` si pubblica e
   si legge, e un codice fuori lista è rifiutato.
3. **Fatti di generazione.** Verifica: un fatto `ncap_stars` compare su ogni
   variante della generazione e su nessuna variante di un'altra.
4. **Nuova identità.** La carrozzeria diventa un fatto, la chiave si riduce,
   `_fills_body_style` sparisce. Verifica: un modello TLA+ del ciclo di vita di una
   riga veicolo, poi una migrazione di prova sul bundle reale di 100 modelli.
5. **Generazione nel file dei nomi.** Verifica: il bundle ricostruito non contiene
   veicoli senza generazione.
6. **Euro NCAP.** Richiede il permesso scritto di Euro NCAP. Verifica: source review
   firmata e un'auto reale con il voto.

La cura delle auto reali (prezzo, bagagliaio, carrozzeria) parte dopo il passo 5.

## Cosa resta fuori

- Dotazioni. Il passo 2 le rende possibili, ma non ne definisce nessuna.
- Generazioni passate e fonte degli annunci usati.
- Moto e scooter. Usano lo stesso modello e non richiedono scelte diverse.
- Affidabilità, costi di assicurazione e di manutenzione. Nessuna fonte aperta.

## Verifiche fatte e punti aperti

### Euro NCAP richiede un permesso scritto

I [termini del sito Euro NCAP](https://www.euroncap.com/terms-conditions/), letti il
25 novembre 2026, dicono: "Reproduction is not authorised for commercial purposes.
Prior permission from Euro NCAP must be obtained for the reproduction or use of
textual and multimedia information". Il passo 6 parte quindi da una richiesta di
permesso a Euro NCAP. Senza risposta, il voto non entra nel ranking.

### I numeri di omologazione separano le generazioni, ma non da soli

Sedici modelli hanno più omologazioni sotto lo stesso nome
([registro delle lacune](open-data-gaps.md)). Un controllo su RDW, immatricolazioni
2024, ne ha guardati cinque:

| Modello | Omologazioni | Prima immatricolazione di ciascuna | Cosa separano |
| --- | --- | --- | --- |
| Fiat 500 | 2 | 2017 e 2020 | due generazioni |
| Dacia Duster | 2 | 2017 e 2024 | due generazioni |
| Peugeot 3008 | 2 | 2016 e 2023 | due generazioni |
| Mini Cooper | 3 | tutte 2016 | tre carrozzerie della stessa generazione |
| Lancia Ypsilon | 1 | 2024 | nulla: la vecchia generazione non è immatricolata nei Paesi Bassi |

L'omologazione separa le generazioni nei tre casi in cui ce ne sono due. Separa
però anche le carrozzerie, quindi una persona deve dare il nome a ogni omologazione
nel file dei nomi. La data della prima immatricolazione di un'omologazione dà una
stima dell'anno di inizio produzione. Gli altri undici modelli non sono stati
controllati.

### Il catalogo servito oggi è solo sintetico

`https://drivewise-unified.vercel.app/api/vehicles` restituisce 16 veicoli, tutti
del bundle demo: 10 auto, 3 moto, 3 scooter. Il database Neon `ep-proud-flower`
non è stato interrogato direttamente.

### Formula neopatentati

La massa archiviata è "in ordine di marcia". La norma va letta prima di scrivere il
calcolo.
