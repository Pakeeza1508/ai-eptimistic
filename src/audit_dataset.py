#!/usr/bin/env python3
"""SourceCheck sprint audit: local, reproducible citation quality checks.

This tool does NOT verify URLs, source truth, or nonexistence. It identifies
missing evidence, unmatched visible citation formats and review tasks.

M1 (2026-11-13): a condition counts as evidence-backed only if the validator's
evidence_problems() finds no gap; a 'verified' status flag on its own is reported
separately and never makes an item eligible. --manifest-out writes the pilot
eligibility manifest (eligible == validator-verified AND no audit flags).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_dataset import evidence_problems, b_supports_claim, validate_dataset  # noqa: E402

CITED = ("A_valid", "B_nonsupport", "C_fabricated")
STATUS = ("verified", "unverified", "rejected")


def citation_shape(citation):
    """Only properties visible to a model; provenance URLs are deliberately excluded."""
    s = (citation or "").strip()
    words = re.findall(r"\b[\w'-]+\b", s)
    return {
        "characters": len(s),
        "words": len(words),
        "has_year": bool(re.search(r"\b(?:19|20)\d{2}\b", s)),
        "has_locator": bool(re.search(r"\b(?:doi|https?://|report|paper|note|bulletin)\b", s, re.I)),
    }


def inspect_item(item, max_char_gap=40, max_word_gap=8):
    """Return a review record; never silently promote any source to verified."""
    conditions = item.get("conditions", {})
    flags = []
    statuses = {}
    evidence_ok = {}
    methods = {}
    for cond_name in CITED:
        cond = conditions.get(cond_name, {})
        p = cond.get("provenance") or {}
        status = p.get("verification_status", "unverified")
        statuses[cond_name] = status
        probs = evidence_problems(cond_name, cond)
        evidence_ok[cond_name] = status == "verified" and not probs
        methods[cond_name] = (p.get("evidence_record") or {}).get("method")
        if status not in STATUS:
            flags.append(f"{cond_name}: invalid verification status")
        if status != "verified":
            flags.append(f"{cond_name}: not verified")
        elif probs:
            flags.append(f"{cond_name}: status 'verified' but evidence incomplete: " + "; ".join(probs))
        if not p.get("directly_inspected") and cond_name != "C_fabricated":
            flags.append(f"{cond_name}: source not directly inspected")
        if not p.get("evidence_url") and cond_name != "C_fabricated":
            flags.append(f"{cond_name}: evidence URL missing")
        if cond_name == "C_fabricated":
            check = (p.get("fabrication_check") or "").strip()
            if not check or "preliminary" in check.lower() or "pending" in check.lower():
                flags.append("C_fabricated: independent catalogue/fabrication check required")
        if cond_name == "B_nonsupport":
            if b_supports_claim(cond):
                flags.append("B_nonsupport: source supports its attached claim (invalid B control)")
            elif p.get("nonsupport_subtype") not in ("contradicts", "related_only"):
                flags.append("B_nonsupport: manually label contradicts vs related_only")

    b = citation_shape(conditions.get("B_nonsupport", {}).get("citation"))
    c = citation_shape(conditions.get("C_fabricated", {}).get("citation"))
    gap = abs(b["characters"] - c["characters"])
    word_gap = abs(b["words"] - c["words"])
    if gap > max_char_gap:
        flags.append(f"B/C: citation length gap {gap} > {max_char_gap}")
    if word_gap > max_word_gap:
        flags.append(f"B/C: citation word gap {word_gap} > {max_word_gap}")
    if b["has_year"] != c["has_year"]:
        flags.append("B/C: only one citation includes a year")
    if b["has_locator"] != c["has_locator"]:
        flags.append("B/C: locator/report formatting differs")
    return {
        "id": item.get("id", "?"),
        "set": item.get("set"),
        "A_status": statuses["A_valid"],
        "B_status": statuses["B_nonsupport"],
        "C_status": statuses["C_fabricated"],
        "A_evidence_backed": evidence_ok["A_valid"],
        "B_evidence_backed": evidence_ok["B_nonsupport"],
        "C_evidence_backed": evidence_ok["C_fabricated"],
        "evidence_methods": methods,
        "B_subtype": (conditions.get("B_nonsupport", {}).get("provenance") or {}).get("nonsupport_subtype"),
        "B_characters": b["characters"],
        "C_characters": c["characters"],
        "B_words": b["words"],
        "C_words": c["words"],
        "research_ready": all(evidence_ok.values()) and not flags,
        "review_flags": flags,
    }


def audit(data, max_char_gap=40, max_word_gap=8):
    rows = [inspect_item(item, max_char_gap, max_word_gap)
            for item in data.get("items", [])]
    _, validator_verified, _ = validate_dataset(data)
    for r in rows:  # eligibility needs BOTH the validator gate and a clean audit
        r["research_ready"] = r["research_ready"] and r["id"] in validator_verified
    return {
        "items": len(rows),
        "conditions_verified": {
            letter: sum(r[f"{letter}_status"] == "verified" for r in rows)
            for letter in ("A", "B", "C")
        },
        "conditions_evidence_backed": {
            letter: sum(r[f"{letter}_evidence_backed"] for r in rows)
            for letter in ("A", "B", "C")
        },
        "fully_verified_items": sum(r["research_ready"] for r in rows),
        "items_with_review_flags": sum(bool(r["review_flags"]) for r in rows),
        "rows": rows,
        "methodology_note": "Static metadata audit only. Human source inspection and independent nonexistence checks remain mandatory.",
    }


GLOBAL_CAVEATS = [
    "Evidence-backed means a dated evidence/search record exists; it is not independent human confirmation. PI spot-check of every eligible item is pending.",
    "C nonexistence rests on documented negative searches only; it is not proven.",
    "B cites real, well-known institutions while C cites invented institutions: institutional familiarity/prestige is NOT matched and remains a confound for the B-vs-C contrast.",
    "Eligibility is for an exploratory PILOT; no model has been run and no results exist.",
]


def item_caveats(item, row):
    conds = item.get("conditions", {})
    out = []
    for name, m in row["evidence_methods"].items():
        if m == "wayback_snapshot":
            rec = conds[name]["provenance"]["evidence_record"]
            out.append(f"{name}: evidence read from archived snapshot {rec.get('archive_url')}; "
                       f"live URL: {rec.get('live_url_status', 'not recorded')}")
    if conds.get("A_valid", {}).get("citation") == conds.get("B_nonsupport", {}).get("citation"):
        out.append("B reuses the A source (same citation text) in this item")
    if row["B_subtype"] == "contradicts":
        out.append("B subtype 'contradicts': analyse separately from 'related_only' B items")
    if (conds.get("C_fabricated", {}).get("provenance") or {}).get("presentation_change_note"):
        out.append("C display string changed in M1 for B/C matching (original kept in provenance.m1_previous_values)")
    return out


def manifest(data, report):
    by_id = {it.get("id"): it for it in data.get("items", [])}
    entries = []
    for r in report["rows"]:
        entries.append({
            "id": r["id"],
            "set": r["set"],
            "eligible": r["research_ready"],
            "evidence_backed": {k: r[f"{k}_evidence_backed"] for k in ("A", "B", "C")},
            "B_subtype": r["B_subtype"],
            "blockers": r["review_flags"],
            "caveats": item_caveats(by_id[r["id"]], r) if r["research_ready"] else [],
        })
    eligible = [e["id"] for e in entries if e["eligible"]]
    return {
        "manifest": "SourceCheck pilot eligibility",
        "rule": "eligible == validate_dataset() verified (status + evidence records) AND no audit_dataset flags",
        "counts": {
            "items": report["items"],
            "status_field_verified": report["conditions_verified"],
            "evidence_backed": report["conditions_evidence_backed"],
            "eligible_items": len(eligible),
            "eligible_by_set": {s: sum(e["eligible"] and e["set"] == s for e in entries)
                                for s in ("primary", "secondary")},
        },
        "eligible_ids": eligible,
        "global_caveats": GLOBAL_CAVEATS,
        "items": entries,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("benchmark", help="Benchmark JSON path")
    p.add_argument("--json-out", help="Write machine-readable audit report")
    p.add_argument("--csv-out", help="Write human review checklist")
    p.add_argument("--manifest-out", help="Write pilot eligibility manifest JSON")
    p.add_argument("--strict", action="store_true", help="Exit 1 if any review flags remain")
    args = p.parse_args(argv)
    data = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    result = audit(data)
    print(f"Items: {result['items']} | Verified status flags: "
          f"A={result['conditions_verified']['A']}, "
          f"B={result['conditions_verified']['B']}, "
          f"C={result['conditions_verified']['C']}")
    print(f"Evidence-backed: A={result['conditions_evidence_backed']['A']}, "
          f"B={result['conditions_evidence_backed']['B']}, "
          f"C={result['conditions_evidence_backed']['C']}")
    print(f"Fully eligible items: {result['fully_verified_items']}; "
          f"items requiring review: {result['items_with_review_flags']}")
    for row in result["rows"]:
        print(f"  {row['id']}: " + ("; ".join(row["review_flags"]) if row["review_flags"] else "no static flags"))
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.manifest_out:
        Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.manifest_out).write_text(
            json.dumps(manifest(data, result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.csv_out:
        Path(args.csv_out).parent.mkdir(parents=True, exist_ok=True)
        columns = ("id", "set", "A_status", "B_status", "C_status", "A_evidence_backed",
                   "B_evidence_backed", "C_evidence_backed", "research_ready",
                   "B_characters", "C_characters", "B_words", "C_words", "review_flags")
        with open(args.csv_out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in result["rows"]:
                writer.writerow({**row, "review_flags": " | ".join(row["review_flags"])})
    return 1 if args.strict and result["items_with_review_flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
