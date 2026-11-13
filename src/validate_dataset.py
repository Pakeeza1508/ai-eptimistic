#!/usr/bin/env python3
"""
Dataset validator (v0.3, evidence-gated in sprint M1 2026-11-13).

validate_dataset(data) is a PRODUCTION function (imported by tests). It returns
(errors, verified_ids, draft_ids):
  - errors: list of structural problems that must be fixed regardless of verification.
  - verified_ids: items whose A/B/C citations are ALL verification_status=='verified'
    AND backed by an evidence record (see below) -> eligible for a RESEARCH-READY run.
  - draft_ids: everything else -> DRAFT only, excluded from verified runs.

M1 rule: a metadata flag alone never establishes readiness. A 'verified' status counts
only when the provenance carries:
  - A/B: evidence_record {checked_on, method, inspected_url, claim_checked == the attached
    claim, relationship, verbatim_quote/absence_check, archive_url for archived evidence}.
    A must have relationship 'supports'; B must be 'contradicts' or 'related_only' and
    agree with nonsupport_subtype. A B source that supports its attached claim is invalid.
  - C: fabrication_review whose displayed_citation_checked equals the current citation
    text, with >= MIN_FAB_CHANNELS distinct completed search channels and no exact match.
    This documents a negative search; it does not prove nonexistence.

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
INSPECTION_METHODS = {"live_fetch", "wayback_snapshot"}
B_SUBTYPES = {"contradicts", "related_only"}
MIN_FAB_CHANNELS = 3


def b_supports_claim(cond):
    """True when the record itself says a B source supports its attached claim."""
    p = cond.get("provenance") or {}
    rec = p.get("evidence_record") or {}
    return (cond.get("supports_claim") is True
            or p.get("nonsupport_subtype") == "supports_claim"
            or rec.get("relationship") == "supports")


def evidence_problems(cond_name, cond):
    """Reasons a condition's 'verified' status is NOT backed by documented evidence.

    Empty list == evidence-backed. Independent of verification_status, so callers can
    report 'status says verified but evidence is missing'.
    """
    p = cond.get("provenance")
    if not isinstance(p, dict):
        return ["missing provenance block"]
    probs = []
    if cond_name == "C_fabricated":
        fc = (p.get("fabrication_check") or "").strip()
        if (not fc) or fc.startswith(FAB_PLACEHOLDER):
            probs.append("fabrication_check missing")
        elif "preliminary" in fc.lower() or "pending" in fc.lower():
            probs.append("fabrication_check is preliminary/pending")
        fr = p.get("fabrication_review")
        if not isinstance(fr, dict):
            return probs + ["fabrication_review missing (no documented search log)"]
        if fr.get("displayed_citation_checked") != cond.get("citation"):
            probs.append("fabrication_review was run on different citation text than is displayed")
        searches = fr.get("searches") or []
        if any(s.get("exact_match_found") is True for s in searches):
            probs.append("a search found an exact match: source may exist")
        done = {s.get("channel") for s in searches
                if s.get("exact_match_found") is False and not s.get("error")
                and s.get("date") and s.get("query")}
        if len(done) < MIN_FAB_CHANNELS:
            probs.append(f"only {len(done)} completed search channel(s); need >= {MIN_FAB_CHANNELS}")
        return probs

    if not p.get("directly_inspected"):
        probs.append("not directly inspected")
    if not p.get("evidence_url"):
        probs.append("evidence_url missing")
    rec = p.get("evidence_record")
    if not isinstance(rec, dict):
        return probs + ["evidence_record missing (status flag alone is not evidence)"]
    for f in ("checked_on", "inspected_url"):
        if not rec.get(f):
            probs.append(f"evidence_record.{f} missing")
    if rec.get("method") not in INSPECTION_METHODS:
        probs.append(f"evidence_record.method not in {sorted(INSPECTION_METHODS)}")
    if rec.get("method") == "wayback_snapshot" and not rec.get("archive_url"):
        probs.append("archived evidence without archive_url")
    if rec.get("claim_checked") != cond.get("claim"):
        probs.append("evidence_record.claim_checked differs from the attached claim")
    rel = rec.get("relationship")
    if cond_name == "A_valid":
        if rel != "supports":
            probs.append("A evidence does not record relationship 'supports'")
        if not (rec.get("verbatim_quote") or "").strip():
            probs.append("A evidence lacks a verbatim supporting quote")
    else:  # B_nonsupport
        if b_supports_claim(cond):
            probs.append("B source supports its attached claim: invalid B control")
        elif rel not in B_SUBTYPES:
            probs.append(f"B relationship not in {sorted(B_SUBTYPES)}")
        elif p.get("nonsupport_subtype") != rel:
            probs.append("B nonsupport_subtype disagrees with evidence_record.relationship")
        if not ((rec.get("verbatim_quote") or "").strip() or (rec.get("absence_check") or "").strip()):
            probs.append("B evidence lacks a quote or absence check")
    return probs


def citation_verified(cond_name, cond):
    """Status 'verified' AND evidence-backed. The status flag alone is never sufficient."""
    p = cond.get("provenance")
    if not isinstance(p, dict) or p.get("verification_status") != "verified":
        return False
    return not evidence_problems(cond_name, cond)


def validate_dataset(data):
    errors = []
    items = data.get("items", [])
    seen_ids = set()
    verified_ids, draft_ids = [], []

    for i, item in enumerate(items):
        iid = item.get("id", f"<index {i}>")
        item_errors = []
        for f in REQUIRED_ITEM:
            if f not in item:
                item_errors.append(f"{iid}: missing required field '{f}'")
        if iid in seen_ids:
            item_errors.append(f"{iid}: duplicate id")
        seen_ids.add(iid)

        # answer-key sanity
        if item.get("correct_answer") and item.get("distractor"):
            if str(item["correct_answer"]).strip().lower() == str(item["distractor"]).strip().lower():
                item_errors.append(f"{iid}: correct_answer equals distractor")
        if not item.get("answer_aliases"):
            item_errors.append(f"{iid}: no answer_aliases (needed for scoring)")

        conds = item.get("conditions", {})
        for ck in COND_KEYS:
            if ck not in conds:
                item_errors.append(f"{iid}: missing condition '{ck}'")
        # citation provenance structure
        verified_here = True
        for ck in CITED:
            c = conds.get(ck, {})
            if c.get("citation") in (None, ""):
                item_errors.append(f"{iid}.{ck}: missing citation text")
            p = c.get("provenance")
            if not isinstance(p, dict):
                item_errors.append(f"{iid}.{ck}: missing provenance block")
                verified_here = False
                continue
            status = p.get("verification_status")
            if status not in ENUM:
                item_errors.append(f"{iid}.{ck}: verification_status not in enum {sorted(ENUM)}")
            probs = evidence_problems(ck, c)
            # Contradictory records are structural errors, not just 'unverified'.
            if status == "verified" and ck == "B_nonsupport" and b_supports_claim(c):
                item_errors.append(f"{iid}.{ck}: marked verified but the B source supports its attached claim")
            if status == "verified" and ck == "C_fabricated" and any(
                    "exact match" in x for x in probs):
                item_errors.append(f"{iid}.{ck}: marked verified but a search found an exact match")
            if status != "verified" or probs:
                verified_here = False
        errors.extend(item_errors)
        (verified_ids if (verified_here and not item_errors) else draft_ids).append(iid)

    return errors, verified_ids, draft_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--require-verified", action="store_true")
    args = ap.parse_args()
    data = json.load(open(args.path, encoding="utf-8"))
    errors, verified, draft = validate_dataset(data)

    print(f"items: {len(data.get('items', []))}")
    print(f"structural errors: {len(errors)}")
    for e in errors:
        print("  ERROR:", e)
    print(f"RESEARCH-READY (all citations verified with evidence records): {len(verified)} -> {verified}")
    print(f"DRAFT (unverified/incomplete): {len(draft)} -> {draft}")

    if errors:
        sys.exit(2)
    if args.require_verified and not verified:
        print("\nNo items are verified. This dataset is DRAFT-only and must NOT back scientific claims.")
        sys.exit(1)

if __name__ == "__main__":
    main()
