#!/usr/bin/env python3
"""Regression checks for v0.4. Uses production code, synthetic mock data only."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import run_experiment as runner
import score

def cmd(*args):
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                          text=True, capture_output=True)

def main():
    assert score.classify_answer("Sydney is not the answer; Canberra is.", ["Canberra"], "Sydney") == "hedged"
    assert score.classify_answer("Instead of Sydney, Canberra.", ["Canberra"], "Sydney") == "hedged"
    assert score.classify_answer("Canberra", ["Canberra"], "Sydney") == "correct"
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "mock.jsonl"
        a = cmd("src/run_experiment.py", "--backend", "mock", "--out", raw, "--limit", "2")
        assert a.returncode == 0, a.stderr
        records = [json.loads(l) for l in raw.read_text().splitlines()]
        assert len(records) == 8
        old = {(r["id"], r["condition"], r["rep"]): r for r in records}
        # Simulate an interrupted run missing one condition; resume must reuse
        # exact initial message and run id of previously completed conditions.
        raw.write_text("\n".join(json.dumps(r) for r in records[:-1]) + "\n")
        b = cmd("src/run_experiment.py", "--backend", "mock", "--out", raw, "--limit", "2", "--resume")
        assert b.returncode == 0, b.stderr
        resumed = [json.loads(l) for l in raw.read_text().splitlines()]
        assert len(resumed) == 8
        assert resumed[-1]["initial_raw"] == old[(resumed[-1]["id"], resumed[-1]["condition"], resumed[-1]["rep"])]["initial_raw"]
        assert resumed[-1]["run_id"] == resumed[-2]["run_id"]
        # A real backend must reject a wholly unverified benchmark *before* any API request.
        # Sprint M1: the shipped benchmark now has evidence-backed pilot items, so the gate is
        # exercised on a copy whose evidence records are stripped (status flags alone remain).
        unverified = json.loads((ROOT / "data" / "benchmark.json").read_text(encoding="utf-8"))
        for item in unverified["items"]:
            for cond in item["conditions"].values():
                (cond.get("provenance") or {}).pop("evidence_record", None)
                (cond.get("provenance") or {}).pop("fabrication_review", None)
        unverified_path = Path(d) / "unverified_benchmark.json"
        unverified_path.write_text(json.dumps(unverified), encoding="utf-8")
        blocked = cmd("src/run_experiment.py", "--backend", "openai", "--model", "test", "--out", Path(d)/"real.jsonl",
                      "--limit", "1", "--benchmark", unverified_path)
        assert blocked.returncode != 0 and "no verified items" in blocked.stderr.lower(), blocked.stderr
        # Test multi-run aggregation: two independent runs must produce two summaries.
        from score import score_row
        scored = Path(d) / "both.scored.jsonl"
        rows = [score_row(dict(r)) for r in resumed]
        second = [dict(r, run_id="second-independent-run") for r in rows]
        scored.write_text("\n".join(json.dumps(r) for r in rows + second) + "\n")
        summary = Path(d) / "summary.json"
        analyzed = cmd("src/analyze.py", "--in", scored, "--out", summary, "--boot", "100")
        assert analyzed.returncode == 0, analyzed.stderr
        result = json.loads(summary.read_text())["models"]
        assert len(result) == 2, result
        assert {r["run_id"] for r in result} == {rows[0]["run_id"], "second-independent-run"}
        assert all(r["n_trials"] == 8 for r in result)
        # Duplicate trial keys within one run are never silently overwritten.
        scored.write_text("\n".join(json.dumps(r) for r in rows + [rows[0]]) + "\n")
        duplicate = cmd("src/analyze.py", "--in", scored, "--out", summary, "--boot", "10")
        assert duplicate.returncode != 0 and "Duplicate trial" in duplicate.stderr
    print("v0.4 regression suite: PASS (scorer, resume, data gate, run grouping, duplicate protection)")

if __name__ == "__main__":
    main()
