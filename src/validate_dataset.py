#!/usr/bin/env python3
"""
Dataset validator (v0.3).

validate_dataset(data) is a PRODUCTION function (imported by tests). It returns
(errors, verified_ids, draft_ids):
  - errors: list of structural problems that must be fixed regardless of verification.
  - verified_ids: items whose A/B/C citations are ALL verification_status=='verified'
    (and C has a non-placeholder fabrication_check) -> eligible for a RESEARCH-READY run.
  - draft_ids: everything else -> DRAFT only, excluded from verified runs.

CLI:
  python src/validate_dataset.py data/benchmark.json            # report
  python src/validate_dataset.py data/benchmark.json --require-verified   # exit 1 if 0 verified
"""
import argparse, json, sys

REQUIRED_ITEM = ["id", "set", "push", "question", "correct_answer", "distractor", "conditions"]
COND_KEYS = ["A_valid", "B_nonsupport", "C_fabricated", "D_none"]
CITED = ["A_valid", "B_nonsupport", "C_fabricated"]
ENUM = {"unverified", "verified", "rejected"}
FAB_PLACEHOLDER = "How nonexistence was checked"

def _citation_provenance_ok(cond, is_fabricated):
    p = cond.get("provenance")
    if not isinstance(p, dict):
        return False
    if p.get("verification_status") != "verified":
        return False
    if not p.get("directly_inspected"):
        return False
    if not p.get("evidence_url"):
        return False
    if is_fabricated:
        fc = p.get("fabrication_check") or ""
        if (not fc) or fc.startswith(FAB_PLACEHOLDER):
            return False
    return True

def validate_dataset(data):
    errors = []
    items = data.get("items", [])
    seen_ids = set()
    verified_ids, draft_ids = [], []

    for i, item in enumerate(items):
        iid = item.get("id", f"<index {i}>")
        for f in REQUIRED_ITEM:
            if f not in item:
                errors.append(f"{iid}: missing required field '{f}'")
        if iid in seen_ids:
            errors.append(f"{iid}: duplicate id")
        seen_ids.add(iid)

        # answer-key sanity
        if item.get("correct_answer") and item.get("distractor"):
            if str(item["correct_answer"]).strip().lower() == str(item["distractor"]).strip().lower():
                errors.append(f"{iid}: correct_answer equals distractor")
        if not item.get("answer_aliases"):
            errors.append(f"{iid}: no answer_aliases (needed for scoring)")

        conds = item.get("conditions", {})
        for ck in COND_KEYS:
            if ck not in conds:
                errors.append(f"{iid}: missing condition '{ck}'")
        # citation provenance structure
        verified_here = True
        for ck in CITED:
            c = conds.get(ck, {})
            if ck == "D_none":
                continue
            if c.get("citation") in (None, ""):
                errors.append(f"{iid}.{ck}: missing citation text")
            p = c.get("provenance")
            if not isinstance(p, dict):
                errors.append(f"{iid}.{ck}: missing provenance block")
                verified_here = False
                continue
            if p.get("verification_status") not in ENUM:
                errors.append(f"{iid}.{ck}: verification_status not in enum {sorted(ENUM)}")
            if not _citation_provenance_ok(c, is_fabricated=(ck == "C_fabricated")):
                verified_here = False
        (verified_ids if (verified_here and not any(iid in e for e in errors)) else draft_ids).append(iid)

    return errors, verified_ids, draft_ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--require-verified", action="store_true")
    args = ap.parse_args()
    data = json.load(open(args.path))
    errors, verified, draft = validate_dataset(data)

    print(f"items: {len(data.get('items', []))}")
    print(f"structural errors: {len(errors)}")
    for e in errors:
        print("  ERROR:", e)
    print(f"RESEARCH-READY (all citations verified): {len(verified)} -> {verified}")
    print(f"DRAFT (unverified/incomplete): {len(draft)} -> {draft}")

    if errors:
        sys.exit(2)
    if args.require_verified and not verified:
        print("\nNo items are verified. This dataset is DRAFT-only and must NOT back scientific claims.")
        sys.exit(1)

if __name__ == "__main__":
    main()
