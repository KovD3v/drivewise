# Source review draft: EEA CO2 monitoring of new passenger cars

Draft of the [catalog source review](../source-review.md). A ticked box is a fact
read from the source on the date given. An empty box waits for a person.

Do not infer permission from public availability. This draft was prepared by the
import's author on 2026-11-23. It is **not signed**: every unticked box needs a
person, and the source stays `manual_validation_only` until then.

## Source identity

- [x] `source_key`: `eea-co2-cars`
- [x] Name: EEA: CO2 emissions from new passenger cars
- [x] Canonical source URL: https://co2cars.apps.eea.europa.eu/
- [x] `source_type`: `public_dataset`
- [x] Market: EU (the import reads only records reported by Italy)

## Licence and access review

- [x] Terms or licence URL reviewed: https://www.eea.europa.eu/en/legal-notice
      (read 2026-11-23). It says EEA material "may be re-used without prior
      permission, free of charge, for commercial or non-commercial purposes,
      provided that the EEA is always acknowledged as the original source of the
      material and that the original meaning or message of the content is not
      distorted".
- [ ] Review date:
- [ ] Reviewer name:
- [ ] The terms permit Drivewise to store reviewed snapshots.
      Draft note: the notice allows "reproduction, adaptation and/or
      distribution, irrespective of the means and/or the format used".
- [ ] The terms permit Drivewise to create and display derived rankings.
      Draft note: adaptation is allowed; the message must not be distorted.
- [ ] Redistribution restrictions are documented: the notice says some data "may
      be subject to different conditions". Confirm that the dataset page carries
      no such mark.
- [x] Attribution is required: yes
- [ ] Required attribution text: proposal "Source: European Environment Agency
      (EEA), CO2 emissions from new passenger cars, 2024 final data".
- [ ] UI location where attribution will appear: **none exists yet**. This blocks
      `permitted`.
- [x] If access is automated, the robots policy and terms permit the planned
      access method: the host serves no `robots.txt` (read 2026-11-23); the
      endpoint is the one the public data viewer itself calls.
- [x] Automated-access notes, including rate limits: about 100 aggregation
      requests per run, one per second, one run per data year.

## Metric trust

- [x] Metrics the source may support: `mass_kg` (mass in running order),
      `engine_power_kw` and `engine_displacement_cc` (not for electric cars),
      `co2_g_km`, `liquid_consumption_l_100km`,
      `electric_consumption_kwh_100km`, `electric_range_km` (electric cars only).
- [x] Metrics the source must not support: prices, dimensions, seats, cargo
      volume, power of electric cars, electric range of plug-in hybrids, CO2 and
      consumption of bi-fuel cars, hybrid type (mild or full).
- [x] Method used to match source records to Drivewise vehicle and variant keys:
      hand-reviewed name table, then the most-registered type-approval version
      per powertrain. See [open-data-import.md](../open-data-import.md).
- [x] Known completeness or accuracy limitations: values are typed by national
      authorities and contain errors; values held by under 2% of a version's
      registrations are dropped. One variant stands for a whole powertrain. See
      [open-data-gaps.md](../open-data-gaps.md).

## Freshness

- [ ] Planned re-observation frequency: proposal: once a year, when the EEA
      publishes the final data of the previous year.
- [ ] Owner of re-observation:
- [ ] Expected delay between a source change and the next snapshot:
- [x] Process for marking missing or withdrawn listings inactive: not applicable.
      The source has registrations, not listings.

## Decision

- [x] Resulting `ranking_permission`: `manual_validation_only` (draft)
- [x] One-line rationale: the licence looks compatible, but no person has signed
      the review and the product has no place for the required attribution.
- [ ] Reviewer name:
- [ ] Decision date:
- [ ] Next review date or trigger: when the attribution has a UI location.
