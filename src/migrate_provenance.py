#!/usr/bin/env python3
"""
One-off migration: add provenance scaffolding to each citation-bearing condition (A/B/C)
in data/benchmark.json. It sets verification_status = 'unverified' for every citation.

IMPORTANT: this script does NOT verify anything. It only creates the fields the researcher
must fill. No citation is ever marked 'verified' automatically.

Run: python src/migrate_provenance.py data/benchmark.json
"""
import json, sys, datetime

SUPPORT_DEFAULT = {
    "A_valid": "Authoritative on-topic source expected to state the correct answer; SHOULD support the claim.",
    "B_nonsupport": "Real on-topic reference, same register as C; SHOULD NOT establish the asserted claim.",
    "C_fabricated": "Fabricated on-topic source, same register as B; NO such source should exist.",
}

def prov(cond_key):
    return {
        "verification_status": "unverified",   # enum: unverified | verified | rejected
        "directly_inspected": False,
        "verification_date": None,
        "evidence_url": None,
        "source_title": None,
        "authors_or_institution": None,
        "year": None,
        "doi_or_url": None,
        "support_explanation": SUPPORT_DEFAULT[cond_key],
        "match_notes": "B and C are intended to match on topic and register and differ only in existence.",
        "fabrication_check": ("How nonexistence was checked (fill before use). Exhaustive proof of "
                              "nonexistence is impossible; record the searches performed and their date.")
                             if cond_key == "C_fabricated" else None,
    }

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/benchmark.json"
    data = json.load(open(path))
    data["benchmark"] = "SourceCheck v0.3"
    data["verification_policy"] = {
        "enum": ["unverified", "verified", "rejected"],
        "rule": "An item is research-ready only if ALL of its A/B/C citations are 'verified' "
                "(and C additionally has a documented fabrication_check). Unverified/rejected "
                "items stay in the DRAFT set and must be excluded from verified runs.",
        "note": "Closed-book models cannot know whether a citation truly exists; this benchmark "
                "measures responses to supplied citation CUES, not external verification of truth.",
    }
    for item in data["items"]:
        for ck in ("A_valid", "B_nonsupport", "C_fabricated"):
            c = item["conditions"][ck]
            if "provenance" not in c:
                c["provenance"] = prov(ck)
    data["_migrated"] = datetime.datetime.utcnow().isoformat() + "Z"
    json.dump(data, open(path, "w"), indent=2)
    n = len(data["items"])
    print(f"Migrated {n} items (3 citation conditions each) -> all citations verification_status='unverified'")

if __name__ == "__main__":
    main()
