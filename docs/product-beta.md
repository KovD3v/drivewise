# Drivewise private beta contract

## Initial wedge

The first validation wedge is an Italian private buyer who is actively
choosing between reviewed new, used, or certified vehicle offers and needs to
turn a budget plus real usage constraints into a defensible shortlist.

This initial focus makes the beta testable. It does not permanently exclude
other vehicle goals from future Drivewise versions.

## Product promise

Drivewise turns budget, usage, and preferences into an evidence-backed
shortlist of exact vehicle variants and active offers, with visible
trade-offs, provenance, assumptions, and uncertainty.

The beta should let a buyer:

1. Identify 2–3 plausible offers.
2. Explain why the leading option fits and what its main compromise is.
3. Choose a concrete next action: inspect the offer, compare alternatives, or
   follow a purchase checklist.

## Explicit non-goals

- No purchase, financing, insurance, tax, legal, or mechanical guarantee.
- No dealer lead marketplace or paid placement.
- No ownership monitoring, upgrades/customization, maintenance planning, or
  resale workflow in this beta.
- No unreviewed source may affect ranking.
- No claim that synthetic fixtures prove market usefulness.
- No public launch until the prerequisites below are satisfied.

## Beta prerequisites

All of these prerequisites must be satisfied:

- Synthetic catalog coverage tests and the read-only `catalog_status.py` checks
  exist and pass.
- Written authorization exists for the selected marketplace source, and a
  completed disposable database pilot report is available.
- A user can reopen a recommendation run by URL.
- The selected beta dataset produces at least two eligible offers for each
  scenario used in a session.
- A reviewer has checked exact variant pairing, source permission, freshness,
  and metric provenance for every offer used in the beta scenarios.

Sessions conducted before every prerequisite is satisfied are internal
rehearsals, not evidence of public-beta readiness.

## Validation protocol

- Recruit 5 target users. Do not store names or contact details in the
  repository.
- Give each participant one scenario that matches a genuine near-term purchase
  need.
- Ask each participant to create a shortlist, explain the first result,
  identify one uncertainty, and choose a next action.
- The observer may clarify the task but must not explain the UI or the scoring.
- Record only anonymized outcomes using participant IDs `P01`–`P05`.

| Participant | Scenario | Non-empty shortlist | Chosen offer | Correct reason identified | Uncertainty identified | Next action chosen | Needed help | Trust-critical failure | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 |  |  |  |  |  |  |  |  |  |
| P02 |  |  |  |  |  |  |  |  |  |
| P03 |  |  |  |  |  |  |  |  |  |
| P04 |  |  |  |  |  |  |  |  |  |
| P05 |  |  |  |  |  |  |  |  |  |

## Pass and fail gates

- At least 4/5 participants reach a non-empty shortlist without observer help.
- At least 4/5 correctly identify one evidence-backed reason for the leading
  result.
- At least 4/5 identify one trade-off, gap, assumption, or uncertainty.
- At least 4/5 choose a concrete next action.
- At least 3/5 say the result reduced manual comparison work enough that they
  would use Drivewise during a real purchase.
- **Zero trust-critical failures.** A trust-critical failure is a wrong
  offer↔variant pairing, an unpermitted source affecting rank, unsupported
  provenance, a materially stale offer presented as current, or hidden missing
  data that changes the decision.

Apply this decision rule:

- If all gates pass, proceed to a larger private beta.
- If any trust-critical failure occurs, stop beta expansion and fix and
  reverify it.
- For other misses, revise the smallest responsible part of the journey, then
  rerun only the failed task with new participants.

## Evidence handling

- Commit only aggregate, anonymized outcomes.
- Keep recruitment details, recordings, and raw notes outside the repository.
- Never put secrets, private source snapshots, emails, phone numbers, names, or
  vehicle registration/VIN data in Git.
- A future analytics plan requires separate approval; this plan introduces no
  tracking.
