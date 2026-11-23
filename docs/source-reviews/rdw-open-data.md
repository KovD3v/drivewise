# Source review draft: RDW open data

Draft of the [catalog source review](../source-review.md). A ticked box is a fact
read from the source on the date given. An empty box waits for a person.

Do not infer permission from public availability. This draft was prepared by the
import's author on 2026-11-23. It is **not signed**: every unticked box needs a
person, and the source stays `manual_validation_only` until then.

## Source identity

- [x] `source_key`: `rdw-open-data`
- [x] Name: RDW open data: registered vehicles and type approvals
- [x] Canonical source URL: https://opendata.rdw.nl/
- [x] `source_type`: `public_dataset`
- [x] Market: NL (the Dutch vehicle register; values are matched to Italian
      variants by EU type-approval version)

## Licence and access review

- [x] Terms or licence URL reviewed: the dataset metadata at
      `https://opendata.rdw.nl/api/views/m9d7-ebf2.json` and
      `https://opendata.rdw.nl/api/views/gr7t-qfnb.json` (read 2026-11-23). Both
      declare licence "Public Domain" and attribution "Team Open Data RDW".
      `https://opendata.rdw.nl/api/views/8ys7-d773.json` (read 2026-11-23) also
      declares "Public Domain"; its attribution field is empty.
- [ ] Review date:
- [ ] Reviewer name:
- [ ] The terms permit Drivewise to store reviewed snapshots.
      Draft note: public domain places no restriction.
- [ ] The terms permit Drivewise to create and display derived rankings.
      Draft note: public domain places no restriction.
- [ ] Redistribution restrictions are documented: none declared in the metadata.
- [ ] Attribution is required: no (public domain). Naming RDW is still good
      practice.
- [ ] Required attribution text: none required; proposal "Dimensions: RDW open
      data".
- [ ] UI location where attribution will appear:
- [x] If access is automated, the robots policy and terms permit the planned
      access method: `https://opendata.rdw.nl/robots.txt` (read 2026-11-23) sets
      `Crawl-delay: 1` and disallows only filtered `/browse` pages. The import
      calls the documented `/resource/<dataset>.json` API.
- [ ] Licence plates in stored evidence are acceptable. Draft note: to tell mild
      from full hybrids the import reads up to five registered vehicles per
      hybrid version. Their Dutch licence plates are in the stored responses and
      in the request URLs, which the catalog stores as evidence. RDW publishes
      plates as open data; no owner data is read.
- [x] Automated-access notes, including rate limits: about 520 requests per run,
      one per second, no account or app token. The first run on 2026-11-23 went
      faster, at about 0.6 seconds per request; the pause is now one second.

## Metric trust

- [x] Metrics the source may support: `length_mm`, `body_width_mm`, `height_mm`,
      `seats` for cars; the same plus `mass_kg`, `engine_displacement_cc` and
      `engine_power_kw` for two-wheelers. It also decides one identity field: mild
      or full hybrid, from the electric motor's net power, by the rule in
      [open-data-import.md](../open-data-import.md).
- [x] Metrics the source must not support: prices (the Dutch catalogue price is
      not an Italian price), CO2 and consumption of cars (EEA is the Italian
      source), anything matched by approval number alone.
- [x] Method used to match source records to Drivewise vehicle and variant keys:
      the same approval number, variant and version as the EEA record, under the
      same make. See [open-data-import.md](../open-data-import.md).
- [x] Known completeness or accuracy limitations: whole centimetres. Checked
      against one manufacturer document only (Toyota Yaris Cross: RDW is 3 to
      5 mm higher on length, width and height); the other models are not checked.
      37 of 218 car variants have no Dutch registration of their exact version.
      For two-wheelers the Dutch best-selling version may differ from the
      Italian one.

## Freshness

- [ ] Planned re-observation frequency: proposal: with each yearly EEA import.
- [ ] Owner of re-observation:
- [ ] Expected delay between a source change and the next snapshot:
- [x] Process for marking missing or withdrawn listings inactive: not applicable.
      The source has registrations, not listings.

## Decision

- [x] Resulting `ranking_permission`: `manual_validation_only` (draft)
- [x] One-line rationale: public-domain data, but no person has signed the review.
- [ ] Reviewer name:
- [ ] Decision date:
- [ ] Next review date or trigger:
