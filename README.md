# SourceCheck — Can LLMs Resist Misleading Citations?

A small, controlled benchmark for the **Apart Research AI x Epistemics Research Sprint 2026, Track 1**.

**Question:** Do LLMs abandon a correct answer because a citation *looks* authoritative, even when the source is irrelevant or fabricated — and does genuine evidence validity change that?

See **`PROTOCOL.md`** for the frozen design. This README is how to run it.

## What's here

```
PROTOCOL.md            frozen experimental design, metrics, stats, related work
EXPANSION.md           how to grow the dataset to 40-50 and verify citations
data/benchmark.json    20 starter items (14 correct-start + 6 incorrect-start), 4 conditions each
prompts/templates.md   exact authority-controlled prompt strings
src/run_experiment.py  elicit initial answer + 4 condition rebuttals; log raw responses
src/score.py           classify answers correct/incorrect (alias or LLM-judge)
src/analyze.py         reversal rates, susceptibility, McNemar, bootstrap CIs
results/               output goes here
```

## v0.4 reliability update (pre-sprint)

Run both regression suites after pulling:

```bash
python tests/test_scoring.py
python tests/test_v04.py
python src/validate_dataset.py data/benchmark.json
```

**Research gate:** Non-mock runs reject a draft-only benchmark. Only verified items can enter a research run; `--allow-unverified-pilot` explicitly bypasses the gate for **exploratory debugging only**, not publishable results. The recorded A/B provenance has been reviewed; fabricated C citations remain unverified.

**Resume:** `--resume` reuses the initial answer and original run ID from existing records. A new `run_id` is used for new question trials. Inconsistent model, temperature or seeded mode causes an error rather than silently mixing sessions.

**Analysis:** Independent runs now receive separate summaries; question-level bootstrap respects repeated measurements and McNemar only compares repetition 0 in repeat experiments. These are exploratory uncertainty estimates; no real-model experiment has been completed.

## Sprint-day coding: citation audit (2026-11-13)

The first sprint-day feature is a **static citation audit** that reports blockers, rather than
claiming source verification was automatic.

```bash
python tests/test_audit.py
python src/audit_dataset.py data/benchmark.json
python src/audit_dataset.py data/benchmark.json --csv-out results/citation_review.csv --json-out results/citation_audit.json
```

The reports identify citation verification statuses, C-source negative-search limitations,
B's missing `nonsupport_subtype` (choose `contradicts` or `related_only` after manual
review), and B/C visible-citation length/year/locator imbalances. This checks only metadata;
it **does not browse the web, prove fabrication or count as a research experiment**.

**Verified-status audit (last recorded evidence pass):** A=20/20, B=19/20 (S04 rejected as invalid control), C=0/20;
thus no question is research-ready. Original 29-test suite and v0.4 suite should be rerun
locally after every pull. See `data/CITATION_AUDIT_2026-11-12.md` and
`PRE_SPRINT_DISCLOSURE.md` for evidence and attribution.

## Setup

```bash
pip install -r requirements.txt            # numpy required; anthropic/openai optional
```

> **Status: MOCK-READY.** The pipeline is verified end-to-end on synthetic mock data and all
> unit tests pass. It is **not** PILOT-READY until a real-model smoke test actually runs, and
> **not** RESEARCH-READY until all required citation conditions have verifiable provenance (C remains unverified). See
> CHANGELOG.md and the release verdict at the bottom.

## 0. Run the unit tests and dataset validation first

```bash
python tests/test_scoring.py                               # 29 assertions, must end "0 failed"
python src/validate_dataset.py data/benchmark.json         # structural check + draft/verified split
```
The model replies as JSON `{"final_answer","confidence","explanation"}`; the scorer reads the
`final_answer` field only and labels each trial correct/distractor/other_answer/hedged/refusal/
parse_error. Refusals and parse errors are never counted as reversals.

## 1. Test the pipeline offline (no API, no cost)

```bash
python src/run_experiment.py --backend mock --model mock-1 --out results/mock_run.jsonl --seed-secondary
python src/score.py    --in results/mock_run.jsonl        --out results/mock_run.scored.jsonl --method alias
python src/analyze.py  --in results/mock_run.scored.jsonl --out results/mock_run.summary.json
```

The mock emits **synthetic** answers so you can confirm scoring/stats work before spending budget.
Mock numbers are NOT evidence of model behaviour.

## 2. Real run — Model 1 (closed-book, priority)

```bash
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY
# Smoke test on 2 items first to confirm access + parsing:
python src/run_experiment.py --backend anthropic --model <MODEL_ID> \
       --out results/smoke.jsonl --temperature 0 --limit 2 --seed-secondary
# Full run (the runner refuses to overwrite an existing file; use a fresh name or --force):
python src/run_experiment.py --backend anthropic --model <MODEL_ID> \
       --out results/model1.jsonl --temperature 0 --sleep 0.3 --seed-secondary

# Score with alias matching first (free), then spot-check with the judge:
python src/score.py --in results/model1.jsonl --out results/model1.scored.jsonl --method alias
#   (recommended) re-label a random subset with an LLM judge and report agreement:
python src/score.py --in results/model1.jsonl --out results/model1.judged.jsonl \
       --method judge --backend anthropic --model <JUDGE_MODEL_ID>

python src/analyze.py --in results/model1.scored.jsonl --out results/model1.summary.json
```

## 3. Model 2 (do this BEFORE the verification-enabled stretch)

Same as above with a different `--model` / backend. A second model matters more for
credibility than the stretch goal.

## Cost / scale

20 items x 4 conditions = **80 Turn-2 calls + 20 Turn-1 calls = 100 calls per model**.
At 40-50 items that's ~200-250 calls per model. Budget two models before the stretch.
`--limit N` runs only the first N items for a quick smoke test on a real model.

## Output metrics (see analyze.py)

- **Unjustified reversal rate** per condition B/C/D (primary) + 95% bootstrap CI + counts
- **Condition A retention** (sanity that the model reads citations)
- **McNemar exact** for C-vs-B, C-vs-D, B-vs-D (paired by question)
- **Corrective update rate** per condition (secondary / selective correction)
- **Mean confidence change** per condition

## Release verdict (v0.3): **MOCK-READY**

| Gate | State |
|------|-------|
| Scoring validity (structured, tested) | PASS (29/29 unit tests) |
| Experimental controls (B/C matched, A as control, seeded labelled) | PASS |
| Mock end-to-end (benchmark -> runner -> scorer -> analysis) | PASS |
| Citation provenance verified | NOT DONE — all `unverified` (DRAFT only) |
| Real-model API execution | UNVERIFIED (no SDK/credentials in this environment) |

To reach **PILOT-READY**: install a backend SDK, set an API key, run a `--limit 2` smoke test,
confirm JSON parsing on the real model. To reach **RESEARCH-READY**: verify every citation
(fill `provenance`), re-run `validate_dataset.py --require-verified`, run >=1 real model, report
judge-vs-human agreement. Do not claim research results from mock data or unverified citations.

## Release gate — clear before any paid real run / before submission

- [ ] `python tests/test_scoring.py` prints ALL PASS.
- [ ] **Pilot difficulty** on the target model (do NOT outcome-select): drop items where the model never flips (floor) or is already wrong at baseline for the wrong reasons.
- [ ] Every A and B citation confirmed **real** and B confirmed **non-supporting**; fill each `verify_note` with URL/DOI + date.
- [ ] Every C citation confirmed **nonexistent** (search returns no match); fill `verify_note` with "no match found" + date.
- [ ] B and C confirmed **topic- and register-matched** per item (no off-topic B).
- [ ] Ground-truth answers double-checked; ambiguous items removed.
- [ ] Judge-vs-human agreement reported on a random subset (SycEval-style).
- [ ] Related-work bibliographic details verified (PROTOCOL.md §7).
- [ ] Report exact counts + bootstrap CIs; flag exploratory n; no over-generalisation.

See `CHANGELOG.md` for what the v0.2 audit fixed and what is still the researcher's job.

## Related work

SycEval (AIES 2025), SycoBench-600 (Findings ACL 2026), Ping et al. "Why LLMs Give In"
(Findings EMNLP 2026), "Stubborn or Sycophantic?" (NeurIPS 2026), CiteCheck (arXiv 2605.27700).
Positioning in PROTOCOL.md §7.
#   a i - e p t i m i s t i c  
 