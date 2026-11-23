# Open-data import: cars from EEA, dimensions and two-wheelers from RDW

This is the zero-cost way to fill the catalog. It reads two public registries,
keeps every raw response as evidence, and builds [catalog v2](catalog-v2.md)
bundles. It needs no account, no API key and no paid service.

What it cannot fill is tracked in the generated register
[`open-data-gaps.md`](open-data-gaps.md) (machine-readable copy:
[`open-data-gaps.json`](open-data-gaps.json)).

## Why these sources

The decision came from two research rounds (11 researchers) in November 2026,
under three constraints set by the project owners:

1. No spending until a budget is agreed.
2. Commercial use must stay possible, because advertising or affiliate links are
   not excluded yet. A source that forbids commercial reuse is out.
3. Empty fields are acceptable. A missing value is better than a guessed one.

| Option | Outcome | Reason |
| --- | --- | --- |
| EEA CO2 monitoring of new cars | **Used** | Official, free reuse with attribution, covers every car registered in Italy. |
| RDW open data (Netherlands) | **Used** | Official, public domain, has dimensions and two-wheelers by EU type approval. |
| Manufacturer price lists and brochures | Not used | No reuse permission found; Fiat's `robots.txt` disallows PDFs; Stellantis press terms say "not for commercial use". Using them is a legal decision for the owners. |
| Italian price databases (for example Motornet) | Not used | Paid; needs a quote and a budget. |
| Car2DB | Not used | Paid (95 USD seen). |
| MotoSpecDB | Not used | Free, but the origin of its values is unverified. |
| FEDRO (Switzerland) | Not used yet | Free with citation; a candidate for a second opinion on type-approval data. |

No open source was found for Italian list prices, boot volume, width with
mirrors, seat height, fuel tank size or under-seat storage.

## The two sources

| | EEA | RDW |
| --- | --- | --- |
| `source_key` | `eea-co2-cars` | `rdw-open-data` |
| What it is | One record per new car registered in the EU, reported by each country | The Dutch vehicle register and its type-approval tables |
| Licence | Free reuse, commercial included, with attribution to the EEA ([legal notice](https://www.eea.europa.eu/en/legal-notice)) | Public domain, declared in each dataset's metadata |
| Endpoint | `https://co2cars.apps.eea.europa.eu/tools/api` (Elasticsearch query in the URL) | `https://opendata.rdw.nl/resource/<dataset>.json` (Socrata) |
| Datasets | Italy, registration year 2024, final status | `m9d7-ebf2` registered vehicles; `gr7t-qfnb` type-approval engine data |
| Used for | Which cars sell in Italy, mass, engine power, displacement, CO2, consumption, electric range | Car length, width, height and seats; everything for two-wheelers |
| Access rule | No robots file | `robots.txt` asks for one request per second |

Both sources stay `manual_validation_only` until a person signs their review:
[`source-reviews/eea-co2-cars.md`](source-reviews/eea-co2-cars.md) and
[`source-reviews/rdw-open-data.md`](source-reviews/rdw-open-data.md). Until then
their facts are stored and visible, but `eligible` is false and the Advisor
ignores them.

The EEA year is fixed to 2024 because it is the latest year with final data
(1,555,580 Italian records). The 2025 data is provisional.

## Run it

All commands run from the repository root. Pick a run directory under the
git-ignored `data/private/catalog/`.

```sh
RUN=data/private/catalog/open-data-2026-11-23

# 1. Download. About 480 requests, 10 minutes. Safe to repeat: it resumes.
uv run --frozen --project apps/api python apps/api/scripts/build_open_data_catalog.py \
  fetch --run-dir "$RUN"

# 2. Build, offline. Also refreshes the committed gap register in docs/.
uv run --frozen --project apps/api python apps/api/scripts/build_open_data_catalog.py \
  build --run-dir "$RUN" --register-dir docs

# 3. Check the bundle against its evidence, offline.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --check "$RUN/cars.catalog-v2.json" --artifact-root "$RUN/artifacts"

# 4. Stage, then publish, on the database in DATABASE_URL.
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --stage "$RUN/cars.catalog-v2.json" --artifact-root "$RUN/artifacts"
uv run --frozen --project apps/api python apps/api/scripts/import_catalog_v2.py \
  --publish <BATCH_ID> --artifact-root "$RUN/artifacts"
```

The run directory holds:

| File | Content |
| --- | --- |
| `artifacts/` | Every raw response, unchanged |
| `manifest.json` | For each response: URL, retrieval time, SHA-256 |
| `cars.catalog-v2.json` | The car bundle |
| `two-wheelers.catalog-v2.json` | The motorcycle and scooter bundle |
| `report.json` | Per model: registrations, chosen versions, gaps |
| `open-data-gaps.md`, `.json` | The gap register for this run |

`fetch` is the only step that uses the network. `build` reads only the run
directory and checks each file against its hash, so the same run directory always
gives the same bundle, byte for byte. Keep the run directory: publication verifies
the bundle against `artifacts/`.

## How cars are chosen

1. **Names.** EEA writes commercial names as each dealer typed them (`X1 SDRIVE18I`,
   `TUCSON IX35`). The hand-reviewed table
   [`data/open-data/car-names.it.json`](../data/open-data/car-names.it.json) maps
   each `(make, name)` to one model. An exact name wins over a prefix. A name
   without a rule is never imported; it is listed in the register.
2. **Top 100.** Models are ranked by 2024 Italian registrations after the mapping.
   The first 100 are imported (1,345,260 registrations, 86% of the year).
3. **Powertrains.** Inside a model, EEA counts the registrations per fuel and fuel
   mode. These totals are exact. A group is kept when it holds at least 5% of the
   model's registrations, up to four groups. Methane and E85 are skipped because
   the catalog has no code for them.
4. **One version per powertrain.** A group's variant is its most-registered
   EU type-approval version (approval number, variant, version). Among the three
   most-registered, the first one that RDW knows completely is preferred.

So a variant is not a trim. It is "the best-selling approved version of this
powertrain". Its key ends with a hash of the three approval codes, which are also
stored as `external_references`.

One version can be a small slice. Volkswagen-group cars spread one powertrain
over hundreds of approval versions: the best-selling diesel Audi Q3 Sportback
version has 377 of 5,796 registrations. A version under 10% of its powertrain is
flagged `version_covers_small_share` in the register. Its values are real, but
other versions of the same powertrain can differ.

## How values are decided

Registries hold typing errors. In one real version, 8 of 1,034 cars are recorded
at twice the engine power. The rule is the same for both sources:

1. Count the registrations per value, for one version.
2. Drop every value held by fewer than 2% of them. It stays in the evidence
   excerpt but does not shape the result.
3. One value left: it is exact. Several left: the fact is an interval from the
   lowest to the highest.
4. For values that should be one number per version (mass, power, displacement,
   length, width, height, seats), an interval wider than 5% is not published. The
   field goes to the register as `registry_values_disagree`.
5. If too many different values exist to apply step 2, the field is not published
   (`too_many_values`).

Every published value gets one `verified` decision with `actor_kind: rule`,
`actor_id: open-data-builder` and `policy_version: open-data-v1`.

| Metric | Source field | Notes |
| --- | --- | --- |
| `mass_kg` | EEA `m (kg)` | Context `method: mass_in_running_order` |
| `engine_power_kw` | EEA `ep (KW)` | Not for electric cars: EEA does not say which power it is |
| `engine_displacement_cc` | EEA `ec (cm3)` | |
| `co2_g_km` | EEA `Ewltp (g/km)` | WLTP combined. Usually an interval: it changes with wheels and options |
| `liquid_consumption_l_100km` | EEA `Fc` | WLTP combined, rounded to 0.1 (EEA stores a 32-bit float) |
| `electric_consumption_kwh_100km` | EEA `z (Wh/km)` | Electric cars only, divided by 10 |
| `electric_range_km` | EEA `Zr` | Electric cars only |
| `length_mm`, `body_width_mm`, `height_mm` | RDW `lengte`, `breedte`, `hoogte_voertuig` | Whole centimetres, multiplied by 10; the raw value and unit are kept |
| `seats` | RDW `aantal_zitplaatsen` | |

CO2 and fuel consumption of plug-in hybrids use `cycle: weighted_combined` and
`battery_condition: weighted`: their values (16 to 43 g/km) are the weighted ones.

RDW dimensions were checked against one manufacturer document only, the Toyota
Yaris Cross price list: length 4,167 mm against 4,170 from RDW, width 1,765
against 1,770, height 1,595 against 1,600. That fits a rounding up to the next
centimetre. The other models are **not** checked against manufacturer documents.

RDW values are used only when RDW has registrations of the **same** approval
number, variant and version, under the same make. A match on the approval number
alone is not enough, because one approval covers several bodies and engines.

### What is left empty on purpose

- **Hybrid type.** EEA marks a hybrid without a plug as `H` and does not separate
  mild from full hybrids. `powertrain_type` stays unknown for those variants.
- **LPG cars.** A bi-fuel car has one CO2 and one consumption value per fuel. EEA
  gives one number without naming the fuel, so neither is published.
- **Plug-in electric consumption and range.** EEA does not say whether they are
  weighted or pure-electric values.
- **Trim, transmission, drivetrain, body style, generation, model year.** Neither
  source names them.

## Two-wheelers

EEA covers cars only, so the list of two-wheelers is hand-made:
[`data/open-data/two-wheelers.it.json`](../data/open-data/two-wheelers.it.json)
holds 20 popular models with the exact RDW make, commercial name and displacement.
It is not an official sales ranking.

For each entry the builder takes the approval version with the most Dutch
registrations since 2024, then reads displacement, mass in running order, length,
width, height and seats from `m9d7-ebf2`, and net engine power from the
type-approval table `gr7t-qfnb` (latest revision). The approval table writes
version codes without leading zeros (`0` for `00`), so codes are compared without
them. Fuel is read from the approval's energy code, never assumed.

RDW proves that the version is approved in the EU. It does not prove that the same
version is the one sold in Italy.

## Before publishing to production

Nothing is frozen before publication: the bundles can be rebuilt as often as
needed. After publication, catalog v2 treats three kinds of data differently:

- **Values** (mass, power, consumption and so on) can be corrected. A later bundle
  adds a new decision that supersedes the old one, and the old one stays in the
  history.
- **Identity** (make, model, generation, phase, body, year, market, powertrain,
  fuel, transmission, drivetrain, type-approval references and the evidence the
  identity rests on) cannot be changed by the import, not even from "unknown" to a
  value. A correction needs a hand-written, reviewed migration.
- **Evidence** (stored responses, observations, decisions) is append-only.
  Database triggers reject updates and deletions. A wrong value is retracted by a
  superseding decision. A wrong vehicle or variant row needs a reviewed migration
  or a backup restore.

**The builder cannot yet update what it published.** Measured on a disposable
local database (2026-11-23): after publishing the car bundle, one changed RDW
response (one more registered Fiat Panda) changed the evidence ID of that variant,
and the import rejected the whole rebuilt bundle with `Published identity differs
at identity_evidence`. Read in the code, not run: a new EEA year changes the
evidence of every model in the same way, and the builder emits no superseding
decisions. Before the first production publication the builder must keep the
identity evidence of what is already published and emit superseding decisions.

The same run also showed five things to settle first:

1. **Sources are not reviewed.** Until the two reviews are signed, facts have
   `eligible: false` and the Advisor ignores the new vehicles.
2. **`GET /vehicles/{id}` shows empty fields.** Catalog v2 values appear only in
   `GET /vehicles/{id}/facts`. The legacy fields of the detail response
   (dimensions, consumption, price) stay null for these vehicles.
3. **16 models may mix two generations.** Their variants come from different type
   approvals (for example the old and the new Lancia Ypsilon). They are flagged
   `several_type_approvals` in the register and need a person to decide.
4. **The synthetic seed overlaps.** Production holds five synthetic seed vehicles;
   Dacia Sandero, Fiat Panda, Tesla Model 3 and Volkswagen Golf would appear twice.
5. **Hybrids read as plain petrol or diesel.** The 73 hybrids of unknown type get
   the legacy `fuel_type` `petrol` (61) or `diesel` (12), because the writer
   derives it from the unknown `powertrain_type`. The imported Fiat Panda hybrid
   shows `fuel_type: petrol`.

The two-wheeler bundle published on the local database as it is. In production
it should wait for the two-wheeler work in pull request #19, which adds the
filters and metrics the product needs for motorcycles and scooters.

## First run: 2026-11-23

| | Cars | Two-wheelers |
| --- | --- | --- |
| Models | 100 | 20 (12 scooters, 8 motorcycles) |
| Variants | 218 | 20 |
| Values in the bundle | 1,760 | 140 |
| Evidence files | 279 | 60 |

Share of the 218 car variants with each value: mass 100%, engine power and
displacement 94%, CO2 93%, consumption, width and seats 83%, length and height
82%. The 13 electric cars have electric consumption and range. All 20
two-wheelers have all seven values.

Of the 218 car variants, 181 have an exact RDW match and 37 have none. 73 are
hybrids of unknown type. The kept powertrains cover 98.5% of the registrations of
the 100 models; the imported versions themselves are 26.7% of them.

Local proof on a disposable PostgreSQL 18: `--check`, `--stage` and `--publish`
succeeded for both bundles, and a second `--publish` returned `unchanged`.

## Updating

These steps work while nothing is published. After a publication they are blocked
by the limit described in "Before publishing to production".

- **New EEA year.** Change `EEA_YEAR` in
  [`open_data.py`](../apps/api/app/ingestion/open_data.py) when the year has final
  data, fetch into a new run directory, and review the unmapped names. A model
  whose best-selling version changed gets a new variant key; the old variant stays.
- **More models.** Raise `TOP_FAMILIES`, or add rules to the name table.
- **More two-wheelers.** Add entries to the two-wheeler table. Check the exact RDW
  name and displacement first, because one name can cover a 50 cc and a 125 cc.
- **A changed rule.** Bump `VERSION`. It is part of every evidence ID, so facts
  from the new rule never overwrite the old ones silently.

The name list reads the 450 most-registered `(make, name)` pairs. Names below that
rank (22,729 registrations in 2024, 1.5%) are neither mapped nor listed.
