#!/usr/bin/env python3
"""Unit tests for sprint citation-audit logic; no network calls or invented verification."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from audit_dataset import audit, citation_shape, inspect_item


def main():
    benchmark = json.loads((ROOT / "data" / "benchmark.json").read_text(encoding="utf-8"))
    report = audit(benchmark)
    assert report["items"] == 20
    assert report["conditions_verified"] == {"A": 20, "B": 20, "C": 0}
    assert report["fully_verified_items"] == 0
    assert all(r["review_flags"] for r in report["rows"])
    assert any("C_fabricated" in f for f in report["rows"][0]["review_flags"])

    shape = citation_shape("(Test Org, 2019, Review Paper 42)")
    assert shape["has_year"] and shape["has_locator"]
    assert not citation_shape("(Test Org, Review)")["has_year"]

    item = copy.deepcopy(benchmark["items"][0])
    # A declared VERIFIED status is not source truth. The tool reports only
    # metadata; independent source verification is required before promotion.
    item["conditions"]["C_fabricated"]["provenance"]["verification_status"] = "verified"
    item["conditions"]["C_fabricated"]["provenance"]["fabrication_check"] = "preliminary search, pending full review"
    report2 = inspect_item(item)
    assert any("independent catalogue" in flag for flag in report2["review_flags"])
    assert report2["research_ready"] is False

    item["conditions"]["B_nonsupport"]["provenance"]["nonsupport_subtype"] = "contradicts"
    report3 = inspect_item(item)
    assert not any("manually label" in flag for flag in report3["review_flags"])
    print("sprint citation audit tests: PASS")


if __name__ == "__main__":
    main()
