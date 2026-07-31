# Catalog source review

Complete this checklist before setting any catalog source to
`ranking_permission: "permitted"`. Keep the completed review with the source's
internal onboarding record and re-review it whenever the source terms or access
method changes.

## Source identity

- [ ] `source_key`:
- [ ] Name:
- [ ] Canonical source URL:
- [ ] `source_type` (`manual_seed`, `public_dataset`, or `curated_internal`):
- [ ] Market:

## Licence and access review

- [ ] Terms or licence URL reviewed:
- [ ] Review date:
- [ ] Reviewer name:
- [ ] The terms permit Drivewise to store reviewed snapshots.
- [ ] The terms permit Drivewise to create and display derived rankings.
- [ ] Redistribution restrictions are documented:
- [ ] Attribution is required: yes / no
- [ ] Required attribution text:
- [ ] UI location where attribution will appear:
- [ ] If access is automated, the robots policy and terms permit the planned
      access method.
- [ ] Automated-access notes, including rate limits:

Do not infer permission from public availability. If snapshot storage or
derived ranking rights are unclear, keep the source `not_permitted` until a
human resolves the ambiguity.

## Metric trust

List only metrics that the source is competent and permitted to support. These
become the exact `supported_metrics` values in provenance claims.

- [ ] Metrics the source may support:
- [ ] Metrics the source must not support:
- [ ] Method used to match source records to Drivewise vehicle and variant keys:
- [ ] Known completeness or accuracy limitations:

## Freshness

Advisor listings must be observed within the 30-day `FRESHNESS_DAYS` window.

- [ ] Planned re-observation frequency:
- [ ] Owner of re-observation:
- [ ] Expected delay between a source change and the next snapshot:
- [ ] Process for marking missing or withdrawn listings inactive:

## Decision

- [ ] Resulting `ranking_permission` (`permitted`, `not_permitted`, or
      `manual_validation_only`):
- [ ] One-line rationale:
- [ ] Reviewer name:
- [ ] Decision date:
- [ ] Next review date or trigger:

Sources marked `not_permitted` or `manual_validation_only` may still be imported
for human review. Their offers and provenance are deliberately excluded from
Advisor rankings.
