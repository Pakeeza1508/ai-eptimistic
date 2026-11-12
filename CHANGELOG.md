## v0.4 — Reliability patch (2026-11-12)
- Analyzer separates independent runs by model and run ID; duplicate trial keys fail loudly.
- Bootstrap intervals resample question clusters (rather than treating repetitions as independent questions); McNemar uses rep=0 when there are repeated observations.
- Runner's resume reuses the original initial answer and run ID from saved trials; incompatible model/settings or conflicting starts fail.
- Non-mock research runs require a verified citation subset; draft-only datasets are blocked unless `--allow-unverified-pilot` is explicitly supplied.
- Ambiguous complex sentence-style `final_answer` strings are marked `hedged`, not forced into correct/distractor.
- Added `python tests/test_v04.py` regression checks.
- Still MOCK-READY only: citation sources are unverified, and real APIs have not been exercised.

# Changelog

## v0.3 — second-audit fixes (structured scoring, controls, provenance, production tests)

### FIX 1 — structured answer contract + reliable scoring (`src/score.py`, `src/run_experiment.py`)
- Model now replies as JSON `{"final_answer","confidence","explanation"}`; the scorer
  classifies the `final_answer` field ONLY (never the explanation).
- Labels are an explicit enum: `correct / distractor / other_answer / hedged / refusal /
  parse_error`. Non-JSON / missing field -> `parse_error`, never a silent wrong answer.
- Matching is negation-aware with word boundaries: "Canberra, not Sydney" -> correct,
  "Gd, not Au" -> distractor, "Australia" != "Au", refusals/hedges are not reversals.
- Confidence out of range is flagged, not clamped.
- `parse_judge_label()` is a single production function (INCORRECT never read as CORRECT);
  the tests import it instead of re-implementing it.

### FIX 2 — citation provenance + dataset validation (`data/benchmark.json`, `src/validate_dataset.py`, `src/migrate_provenance.py`)
- Each A/B/C citation carries a `provenance` block with `verification_status`
  (enum: unverified/verified/rejected), inspection flag, evidence URL, title/authors/year/DOI,
  support explanation, match notes, and (for C) a fabrication_check.
- ALL citations are `unverified` — nothing was auto-verified. `validate_dataset()` separates a
  RESEARCH-READY set (all citations verified) from the DRAFT set; currently 0 verified, 20 draft.
- B and C remain topic/register matched (from v0.2) so B-vs-C isolates existence.

### FIX 3 — seeded secondary honesty (`src/run_experiment.py`, `src/analyze.py`, docs)
- The imposed-wrong-start population is named **Seeded Prior-Answer Correction**; each row is
  `start_type="seeded"` with the `injected_answer` recorded. Seeded and natural starts are
  reported SEPARATELY and never combined. NOT presented as self-generated self-correction.

### FIX 4 — tests exercise production code (`tests/test_scoring.py`)
- 29 assertions calling the real `classify_answer`, `score_row`, `parse_judge_label`,
  `validate_dataset`. Covers all 12 required scoring cases, parse errors, refusals, seeded
  metadata, serialization, and malformed-data-cannot-produce-reversal.

### FIX 5 — analysis robustness (`src/analyze.py`)
- Grouped by model; rows keyed by `(id, rep)` so repeated runs are not overwritten and repeats
  are not treated as independent questions. Explicit eligible denominators; refusal/hedge/
  parse rates reported; missing McNemar pairs reported; mock runs flagged synthetic; no
  composite score.

### FIX 6 — runner reliability (`src/run_experiment.py`)
- Records: run_id, rep, model, condition, id, raw response, usage token metadata (no invented
  cost), api_error, start_type, injected_answer, timestamp. `--resume` (append, skip done),
  `--repeats`, `--force`, `--limit`. A failed request raises; it never becomes a refusal/answer.

### FIX 7 — documentation without overclaiming
- Closed-book results measure responses to citation CUES, not external verification; seeded
  starts are externally imposed; unverified items cannot back claims; mock = synthetic test.

### Not done (honestly)
- Real API execution UNVERIFIED (anthropic/openai SDKs not installed, no credentials here).
- No citations verified — dataset is DRAFT only.
- Benchmark kept at 20 items (no expansion), per instructions.

## v0.2 — audit fixes

An external audit of v0.1 found real bugs and a design confound. All the code-level and
design-level issues below are fixed. The remaining items are the researcher's verification
work (they cannot be automated honestly).

### Fixed — critical
- **Judge substring bug.** `"CORRECT" in out` matched inside `"INCORRECT"`, so the LLM judge
  labelled every wrong answer CORRECT. Now uses word-boundary regex; regression-tested in
  `tests/test_scoring.py`.
- **Reversal definition + refusals.** Unjustified reversal was `correct -> not correct`, which
  counted refusals/hedges as reversals and inflated the rate. Now reversal = `correct -> distractor`
  (active adoption of the wrong answer); refusals are labelled `other` and reported separately
  (`n_other_refusal`).
- **B-vs-C topical confound.** v0.1 used off-topic famous papers for B and on-topic plausible
  sources for C, so B vs C differed in topic as well as existence. v0.2 makes B a **real, on-topic,
  non-supporting** source matched in register to C, so B vs C isolates existence. Condition renamed
  `B_irrelevant` -> `B_nonsupport`.
- **Secondary incorrect-start.** The runner asked the question normally, so a capable model would
  answer correctly and empty the secondary analysis. Added `--seed-secondary`, which imposes a
  standardized wrong initial answer (documented as a limitation: imposed, not observed).

### Fixed — supporting
- Decision-span extraction: labels are taken from the answer before the `Confidence:` line and weight
  the last stated line, so a wrong answer merely mentioned in reasoning no longer misclassifies.
- Runner: `run_id` + `trial_index` on every record; automatic retries with backoff; refuses to
  overwrite an existing output file (`--force` to override); `--limit` for smoke tests.
- Dataset: removed the ambiguous "longest river" item (Nile/Amazon dispute) -> "largest ocean".
- Added `tests/test_scoring.py` (scoring unit tests incl. the judge-bug regression).

### Still the researcher's job (cannot be faked)
- **Citation verification.** `verify: true` / `fabricated: true` are TO-DO flags, not evidence.
  Confirm every A/B source is real (and B non-supporting), every C source nonexistent, and record
  each in `verify_note`.
- **Difficulty pilot.** Pilot on the target model before the main run; easy items risk a floor
  effect (the model never flips). Do not outcome-select items.
- **Judge-vs-human agreement** on a random subset.
- **Second model** before the verification-enabled stretch.
- Honest reporting: exact counts + bootstrap CIs, exploratory framing, no over-generalisation.

## v0.1 — initial starter repo
Protocol, 20-item benchmark, model-agnostic runner, scoring, analysis, mock pipeline.
