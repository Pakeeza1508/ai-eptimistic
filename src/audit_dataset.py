#!/usr/bin/env python3
"""SourceCheck sprint audit: local, reproducible citation quality checks.

This tool does NOT verify URLs, source truth, or nonexistence. It identifies
missing evidence, unmatched visible citation formats and review tasks.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

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
    for cond_name in CITED:
        cond = conditions.get(cond_name, {})
        p = cond.get("provenance") or {}
        status = p.get("verification_status", "unverified")
        statuses[cond_name] = status
        if status not in STATUS:
            flags.append(f"{cond_name}: invalid verification status")
        if status != "verified":
            flags.append(f"{cond_name}: not verified")
        if not p.get("directly_inspected") and cond_name != "C_fabricated":
            flags.append(f"{cond_name}: source not directly inspected")
        if not p.get("evidence_url") and cond_name != "C_fabricated":
            flags.append(f"{cond_name}: evidence URL missing")
        if cond_name == "C_fabricated":
            check = (p.get("fabrication_check") or "").strip()
            if not check or "preliminary" in check.lower() or "pending" in check.lower():
                flags.append("C_fabricated: independent catalogue/fabrication check required")
        if cond_name == "B_nonsupport":
            subtype = p.get("nonsupport_subtype")
            if subtype not in ("contradicts", "related_only"):
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
        "B_characters": b["characters"],
        "C_characters": c["characters"],
        "B_words": b["words"],
        "C_words": c["words"],
        "research_ready": all(v == "verified" for v in statuses.values()) and not flags,
        "review_flags": flags,
    }


def audit(data, max_char_gap=40, max_word_gap=8):
    rows = [inspect_item(item, max_char_gap, max_word_gap)
            for item in data.get("items", [])]
    return {
        "items": len(rows),
        "conditions_verified": {
            letter: sum(r[f"{letter}_status"] == "verified" for r in rows)
            for letter in ("A", "B", "C")
        },
        "fully_verified_items": sum(r["research_ready"] for r in rows),
        "items_with_review_flags": sum(bool(r["review_flags"]) for r in rows),
        "rows": rows,
        "methodology_note": "Static metadata audit only. Human source inspection and independent nonexistence checks remain mandatory.",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("benchmark", help="Benchmark JSON path")
    p.add_argument("--json-out", help="Write machine-readable audit report")
    p.add_argument("--csv-out", help="Write human review checklist")
    p.add_argument("--strict", action="store_true", help="Exit 1 if any review flags remain")
    args = p.parse_args(argv)
    data = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    result = audit(data)
    print(f"Items: {result['items']} | Verified citation records: "
          f"A={result['conditions_verified']['A']}, "
          f"B={result['conditions_verified']['B']}, "
          f"C={result['conditions_verified']['C']}")
    print(f"Fully verified items: {result['fully_verified_items']}; "
          f"items requiring review: {result['items_with_review_flags']}")
    for row in result["rows"]:
        print(f"  {row['id']}: " + ("; ".join(row["review_flags"]) if row["review_flags"] else "no static flags"))
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.csv_out:
        Path(args.csv_out).parent.mkdir(parents=True, exist_ok=True)
        columns = ("id", "set", "A_status", "B_status", "C_status", "research_ready",
                   "B_characters", "C_characters", "B_words", "C_words", "review_flags")
        with open(args.csv_out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            for row in result["rows"]:
                writer.writerow({**row, "review_flags": " | ".join(row["review_flags"])})
    return 1 if args.strict and result["items_with_review_flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
