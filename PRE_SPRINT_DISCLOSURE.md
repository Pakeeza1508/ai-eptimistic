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
