"""The list-price fact of a spec and its price-list terms, read the same way by the
Advisor and by vehicle detail (ADR-013, ADR-015)."""

from typing import Any

# The current list-price fact of spec `s`, already limited by catalog_scalar_facts
# to eligible evidence from permitted, sourced and licensed sources, with its
# price-list terms and the licence of the source that printed it.
LIST_PRICE_FACT_JOIN = """LEFT JOIN LATERAL (
              SELECT fact.id AS decision_id,
                     fact.selected_observation_id AS observation_id,
                     fact.source_name,
                     fact.source_url,
                     list_price_source.license AS source_license,
                     fact.retrieved_at,
                     observation.list_price AS terms
              FROM catalog_scalar_facts AS fact
              JOIN spec_observations AS observation
                ON observation.id = fact.selected_observation_id
              JOIN source_snapshots AS list_price_snapshot
                ON list_price_snapshot.id = observation.snapshot_id
              JOIN sources AS list_price_source
                ON list_price_source.id = list_price_snapshot.source_id
              WHERE fact.spec_id = s.id
                AND fact.legacy_metric = 'list_price_eur'
            ) AS list_price ON true
"""

LIST_PRICE_COLUMNS = """              list_price.decision_id AS list_price_decision_id,
              list_price.observation_id AS list_price_observation_id,
              list_price.source_name AS list_price_source_name,
              list_price.source_url AS list_price_source_url,
              list_price.source_license AS list_price_source_license,
              list_price.retrieved_at AS list_price_observed_at,
              list_price.terms AS list_price_terms,
"""

_DERIVATIONS = {
    "incl_vat": "printed",
    "excl_vat": "computed_from_excl_vat",
    "turnkey": "computed_from_turnkey",
}


def list_price_block(row: dict[str, Any]) -> dict[str, Any]:
    """The list-price block of a row selected with LIST_PRICE_COLUMNS."""
    terms = row.get("list_price_terms") or {}
    return {
        "price_eur": row["list_price_eur"],
        "computed_from_excl_vat": terms.get("printed_basis") == "excl_vat",
        "derivation": _DERIVATIONS.get(terms.get("printed_basis")),
        "printed_amount_eur": terms.get("printed_amount_eur"),
        "printed_basis": terms.get("printed_basis"),
        "vat_rate_percent": terms.get("vat_rate_percent"),
        "on_road_charge_eur": terms.get("on_road_charge_eur"),
        "on_road_charge_includes_vat": terms.get("on_road_charge_includes_vat"),
        "trim_label": terms.get("trim_label"),
        "price_list_valid_from": terms.get("price_list_valid_from"),
        "substitute_note": terms.get("substitute_note"),
        "source_name": row.get("list_price_source_name"),
        "source_url": row.get("list_price_source_url"),
        "source_license": row.get("list_price_source_license"),
        "observed_at": row.get("list_price_observed_at"),
        "decision_id": row.get("list_price_decision_id"),
        "observation_id": row.get("list_price_observation_id"),
    }
