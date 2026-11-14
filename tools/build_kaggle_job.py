#!/usr/bin/env python3
"""Generate a self-contained, PRIVATE Kaggle GPU job from SourceCheck's verified subset.

This builder runs locally in VS Code (no Kaggle API calls, no GPU, no secrets).
It embeds only selected benchmark items and the frozen prompt strings.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from validate_dataset import validate_dataset
from audit_dataset import audit
from run_experiment import SYSTEM

TEMPLATE = ROOT / "kaggle" / "sourcecheck_template.py"
OUT = ROOT / "kaggle" / "sourcecheck"
USER = "pakeezakhalid"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ids", default="P01", help="comma-separated verified item IDs; default one smoke-test item")
    p.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="public HF instruction-model ID")
    p.add_argument("--seed-secondary", action="store_true")
    a = p.parse_args()
    data = json.loads((ROOT / "data" / "benchmark.json").read_text(encoding="utf-8"))
    errors, verified, _ = validate_dataset(data)
    if errors:
        sys.exit("Dataset invalid: " + "; ".join(errors))
    clean = {r["id"] for r in audit(data)["rows"] if r["research_ready"]}
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    if not ids or len(set(ids)) != len(ids):
        sys.exit("Provide unique IDs")
    if any(x not in clean or x not in verified for x in ids):
        sys.exit(f"Blocked: selected IDs must be evidence-backed and audit-clean: {ids}")
    selected = [x for x in data["items"] if x["id"] in ids]
    # Runtime needs only benchmark experiment fields (avoid shipping audit logs, URLs, prior values).
    safe = []
    for x in selected:
        safe.append({k: x[k] for k in
            ("id", "set", "push", "domain", "difficulty", "question",
             "correct_answer", "distractor", "answer_aliases")} |
            {"conditions": {name: {key: c.get(key) for key in
                ("claim", "citation", "citation_real", "supports_claim")}
                for name, c in x["conditions"].items()}})
    payload = {
        "model": a.model,
        "seed_secondary": a.seed_secondary,
        "items": safe,
        "system": SYSTEM,
        "revision_note": "Local build from validated SourceCheck benchmark; M1 PI spot-check still pending",
    }
    src = TEMPLATE.read_text(encoding="utf-8")
    if "__SOURCECHECK_PAYLOAD__" not in src:
        sys.exit("Template marker absent")
    src = src.replace("__SOURCECHECK_PAYLOAD__", repr(json.dumps(payload, ensure_ascii=False)))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sourcecheck_kaggle.py").write_text(src, encoding="utf-8")
    meta = {
        "id": f"{USER}/sourcecheck-research-pilot",
        "title": "SourceCheck Research Pilot",
        "code_file": "sourcecheck_kaggle.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": []
    }
    (OUT / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("Generated:", OUT)
    print("ID:", meta["id"])
    print("Model:", a.model)
    print("Items:", [x["id"] for x in selected])
    print("Expected inference calls:", sum(4 if a.seed_secondary and x["set"] == "secondary" else 5 for x in selected))
    print("Private Kaggle script; no credentials embedded. Not yet uploaded or run.")


if __name__ == "__main__":
    main()
