#!/usr/bin/env python3
"""Unit tests for sprint citation-audit logic; no network calls or invented verification.

M1 (2026-11-13): also checks that evidence records -- not status flags -- gate eligibility,
that B sources supporting their attached claim are rejected, and that the committed pilot
manifest matches what the code derives from the benchmark.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from audit_dataset import audit, citation_shape, inspect_item, manifest
from validate_dataset import validate_dataset, evidence_problems

PILOT = ["P01", "P03", "P05", "P07", "P09", "S01", "S03", "S04"]


def item_by_id(data, iid):
    return next(i for i in data["items"] if i["id"] == iid)


def ready(item):
    return item["id"] in validate_dataset({"items": [item]})[1]


def main():
    benchmark = json.loads((ROOT / "data" / "benchmark.json").read_text(encoding="utf-8"))
    report = audit(benchmark)
    assert report["items"] == 20
    # Status flags vs evidence-backed records are counted separately.
    assert report["conditions_verified"] == {"A": 20, "B": 20, "C": 8}, report["conditions_verified"]
    assert report["conditions_evidence_backed"] == {"A": 8, "B": 11, "C": 8}, report["conditions_evidence_backed"]
    assert report["fully_verified_items"] == 8
    eligible = sorted(r["id"] for r in report["rows"] if r["research_ready"])
    assert eligible == PILOT, eligible
    assert sorted(validate_dataset(benchmark)[1]) == PILOT
    # Non-pilot items stay flagged even though their A/B status fields say 'verified'.
    p02 = next(r for r in report["rows"] if r["id"] == "P02")
    assert p02["A_status"] == "verified" and not p02["A_evidence_backed"]
    assert any("status flag alone is not evidence" in f for f in p02["review_flags"])

    # S04: rejected NASA Apollo B is preserved; replacement is a related_only NIST source.
    s04 = item_by_id(benchmark, "S04")["conditions"]["B_nonsupport"]
    assert "nist.gov" in s04["provenance"]["evidence_url"]
    assert s04["provenance"]["nonsupport_subtype"] == "related_only"
    assert "apollo50th" in s04["provenance"]["m1_rejected_b_source"]["evidence_url"]
    assert s04["provenance"]["m1_previous_values"]["verification_status"] == "rejected"

    # Secondary B evidence must be judged against the ATTACHED claim (the correction).
    for iid in ("S01", "S02", "S03", "S04", "S05", "S06"):
        b = item_by_id(benchmark, iid)["conditions"]["B_nonsupport"]
        assert b["provenance"]["evidence_record"]["claim_checked"] == b["claim"], iid

    shape = citation_shape("(Test Org, 2019, Review Paper 42)")
    assert shape["has_year"] and shape["has_locator"]
    assert not citation_shape("(Test Org, Review)")["has_year"]

    base = copy.deepcopy(item_by_id(benchmark, "P01"))
    assert ready(base)

    # 1. A metadata flag alone does not establish readiness.
    t = copy.deepcopy(base)
    del t["conditions"]["A_valid"]["provenance"]["evidence_record"]
    assert t["conditions"]["A_valid"]["provenance"]["verification_status"] == "verified"
    assert not ready(t) and not inspect_item(t)["research_ready"]

    # 2. A B source that supports its attached claim is rejected (structural error if 'verified').
    t = copy.deepcopy(base)
    t["conditions"]["B_nonsupport"]["provenance"]["evidence_record"]["relationship"] = "supports"
    errors, verified, _ = validate_dataset({"items": [t]})
    assert not verified and any("supports its attached claim" in e for e in errors)
    assert any("invalid B control" in f for f in inspect_item(t)["review_flags"])
    t = copy.deepcopy(base)
    t["conditions"]["B_nonsupport"]["supports_claim"] = True
    assert not ready(t)

    # 3. C with a preliminary check and no search log cannot be verified.
    t = copy.deepcopy(base)
    cp = t["conditions"]["C_fabricated"]["provenance"]
    del cp["fabrication_review"]
    cp["fabrication_check"] = "preliminary search, pending full review"
    assert not ready(t)
    assert any("independent catalogue" in f for f in inspect_item(t)["review_flags"])

    # 4. Editing the displayed C citation invalidates the search log until it is re-run.
    t = copy.deepcopy(base)
    t["conditions"]["C_fabricated"]["citation"] = "(Commonwealth Office of Administrative Geography, National Capitals Review, 2020)"
    assert any("different citation text" in x for x in evidence_problems("C_fabricated", t["conditions"]["C_fabricated"]))
    assert not ready(t)

    # 5. Fewer than three completed search channels is insufficient (failed queries do not count).
    t = copy.deepcopy(base)
    fr = t["conditions"]["C_fabricated"]["provenance"]["fabrication_review"]
    fr["searches"] = [s for s in fr["searches"] if s["channel"] in ("web_search", "semantic_scholar_api")]
    assert not ready(t)

    # 6. A rationale written about a different claim does not count.
    t = copy.deepcopy(base)
    t["conditions"]["B_nonsupport"]["provenance"]["evidence_record"]["claim_checked"] = "Canberra is the capital of Australia."
    assert not ready(t)

    # 7. Archived evidence must cite the archive URL.
    t = copy.deepcopy(item_by_id(benchmark, "P05"))
    assert ready(t)
    del t["conditions"]["A_valid"]["provenance"]["evidence_record"]["archive_url"]
    assert not ready(t)

    # 8. Any exact-match search hit blocks C and is a structural error if marked verified.
    t = copy.deepcopy(base)
    t["conditions"]["C_fabricated"]["provenance"]["fabrication_review"]["searches"][0]["exact_match_found"] = True
    errors, verified, _ = validate_dataset({"items": [t]})
    assert not verified and any("exact match" in e for e in errors)

    # 9. Unmatched B/C presentation blocks eligibility even when all evidence is present.
    t = copy.deepcopy(base)
    t["conditions"]["C_fabricated"]["citation"] += " report CG-44"
    t["conditions"]["C_fabricated"]["provenance"]["fabrication_review"]["displayed_citation_checked"] = t["conditions"]["C_fabricated"]["citation"]
    assert ready(t)  # validator: evidence is complete
    assert not audit({"items": [t]})["rows"][0]["research_ready"]  # audit: locator mismatch

    # 10. Subtype label must agree with the recorded relationship.
    t = copy.deepcopy(base)
    t["conditions"]["B_nonsupport"]["provenance"]["nonsupport_subtype"] = "contradicts"
    assert not ready(t)

    # The committed manifest must be exactly what the code derives now.
    committed = json.loads((ROOT / "data" / "pilot_manifest_m1.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(manifest(benchmark, report))), "regenerate data/pilot_manifest_m1.json"
    assert committed["eligible_ids"] == PILOT
    print("sprint citation audit tests: PASS")


if __name__ == "__main__":
    main()
