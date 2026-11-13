# Pre-sprint SourceCheck preparation — November 12, 2026

This directory is a prepared copy of SourceCheck v0.3 created before the AI x Epistemics Research Sprint (November 13–15, 2026).

**Origin:** User-provided `sourcecheck_v0.3.zip` (existing research/scaffold code). The `.gitignore` and this disclosure note were added to facilitate private version control. None of this should be represented as newly developed during the sprint.

**Current status:** MOCK-READY only, not scientifically validated. Benchmark citations remain unverified. Outstanding independent audit findings include: multi-run analyzer collision, resume baseline consistency, final-answer parsing edge cases, insufficient source provenance checks, and incomplete B/C citation matching. No verified-model findings are contained here.

For the final report and any sprint repository, clearly identify preexisting files and new work completed during the actual sprint. Retain original documentation and attribution.


## Sprint-day additions (November 13, 2026)

Work authored during the sprint in the private preparation repository:
- `src/audit_dataset.py`: automated audit of citation provenance records, missing
  fabrication checks, B non-support subtypes, and visible B/C citation matching.
- `tests/test_audit.py`: offline tests of the audit and its non-verification safeguards.
- README instructions for exporting per-item review checklists.

These are software validation tools, **not** scientific empirical results.
All previously existing dataset questions, prompt templates, runner, scorer,
analyzer and v0.4 reliability patches must remain disclosed as preexisting
work in the final sprint report. Cite original work and do not rebrand it as
sprint-day implementation.

Current remaining blockers: independently validate fabricated C references,
review and label B source subtypes, fix B/C matching, then conduct actual
model experiments. Reports of a verified field do not replace human evidence.

## Sprint-day additions: Milestone 1 pilot evidence (November 13, 2026)

Authored during the sprint (branch `sprint/m1-pilot-evidence`, AI-assisted, PI review pending):
- `data/PILOT_EVIDENCE_AUDIT_2026-11-13.md`, `data/pilot_manifest_m1.json`, `data/evidence/`:
  source re-inspection, fabricated-C search logs and the pilot eligibility manifest.
- `data/benchmark.json`: M1 evidence records added for 8 pilot items and for the S02, S05 and S06 B
  sources. S04 B replaced. Pilot C display strings re-formatted to match B. Every overwritten value
  is preserved in `m1_previous_values`. The question set, claims and answer keys are preexisting and unchanged.
- `src/validate_dataset.py`, `src/audit_dataset.py`: verification now requires evidence records.
  The original scaffold of both files is preexisting or from earlier sprint-day work.
- `tests/test_audit.py` (rewritten), and targeted edits to the preexisting `tests/test_scoring.py`
  (2 dataset checks) and `tests/test_v04.py` (gate fixture), so each still tests its original intent.

`PROTOCOL.md` (the frozen experimental protocol) was not modified. No model experiments have been run.

## Sprint-day M2 additions (13 November 2026)

- `src/adaption_backend.py`, model-listing helper, runner backend registration and `--ids` selection.
- `tests/test_adaption.py`, SDK requirement and `docs/M2_ADAPTION_PILOT.md`.
- All represent sprint-day integration only; no real-model results were produced.
