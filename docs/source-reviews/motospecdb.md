# Source review draft: MotoSpecDB

Draft of the [catalog source review](../source-review.md). A ticked box is a fact
read from the source on the date given. An empty box waits for a person.

Do not infer permission from public availability. This draft was prepared by the
import's author on 2026-11-24. It is **not signed**: every unticked box needs a
person, and the source stays `manual_validation_only` until then.

## Source identity

- [x] `source_key`: `motospecdb`
- [x] Name: MotoSpecDB open specification dataset
- [x] Canonical source URL: https://motospecdb.com/en/open-data/
- [x] `source_type`: `public_dataset`
- [x] Market: none. It is a worldwide dataset published from Korea; the bundle
      records the source market as `GLOBAL`.

## Licence and access review

- [x] Terms or licence URL reviewed: https://motospecdb.com/en/open-data/ and
      https://motospecdb.com/en/terms/ (read 2026-11-24). Both say the structured
      spec data is licensed under Creative Commons Attribution 4.0 (CC BY 4.0).
      The terms add that "wholesale mirror scraping without attribution is
      prohibited". The JSON file itself declares
      `"license": "CC BY 4.0 — Attribute MotoSpecDB (https://motospecdb.com)"`.
- [ ] Review date:
- [ ] Reviewer name:
- [ ] The terms permit Drivewise to store reviewed snapshots.
      Draft note: CC BY 4.0 allows copying and storing, commercial use included.
- [ ] The terms permit Drivewise to create and display derived rankings.
      Draft note: CC BY 4.0 allows adaptation, commercial use included.
- [ ] Redistribution restrictions are documented: attribution only.
- [ ] Attribution is required: yes.
- [ ] Required attribution text: the open-data page asks to attribute cited
      specifications to "MotoSpecDB (https://motospecdb.com)" with a direct link
      to the corresponding model page. Each imported value keeps that page's URL
      in its evidence excerpt (`model_page`).
- [ ] UI location where attribution will appear:
- [x] If access is automated, the robots policy and terms permit the planned
      access method: `https://motospecdb.com/robots.txt` (read 2026-11-24) allows
      every path for all agents except search and filter pages. The import makes
      one plain request per run for `/api/v1/bikes.json`, the endpoint the
      open-data page publishes.
- [x] Automated-access notes, including rate limits: one request per run, about
      2.8 MB, no account or key.

## Metric trust

- [x] Metrics the source may support: `seat_height_mm`, `mass_kg` with
      `method: wet`, `fuel_tank_capacity_liters`, for motorcycles and scooters.
- [x] Metrics the source must not support: every field the publisher estimates
      (`est_*`, `seat_arch_factor`), and every identity field.
- [x] Method used to match source records to Drivewise vehicle and variant keys:
      a hand-checked link in
      [`two-wheelers.it.json`](../../data/open-data/two-wheelers.it.json), then
      rules the builder applies: same make; the entry names one variant (no
      "A / B" model and at most one chassis code); its years cover the Dutch
      registrations read, or its chassis code equals the Dutch commercial name.
      See [open-data-import.md](../open-data-import.md).
- [x] Known completeness or accuracy limitations: the provenance of the values is
      unknown beyond the publisher's own citation of owner's manuals; nothing was
      checked against a manual. The SH125i and SH150i entries carry identical
      seat height, wet weight and tank, which is plausible for two engines of one
      body but unverified. 3 of the 20 two-wheelers match; 11 links are refused
      because the entry joins variants or generations, and 6 models have no
      entry (Piaggio, Kymco, Benelli and Voge are not in the dataset; the only
      Africa Twin entries are DCT versions).

## Freshness

- [ ] Planned re-observation frequency: proposal: with each import run.
- [ ] Owner of re-observation:
- [ ] Expected delay between a source change and the next snapshot:
- [x] Process for marking missing or withdrawn listings inactive: not applicable.
      The source has specifications, not listings.

## Decision

- [x] Resulting `ranking_permission`: `manual_validation_only` (draft)
- [x] One-line rationale: an open licence that allows commercial reuse, but values
      of unverified origin and no signed review.
- [ ] Reviewer name:
- [ ] Decision date:
- [ ] Next review date or trigger:
