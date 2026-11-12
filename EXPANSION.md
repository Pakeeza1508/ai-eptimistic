# Expanding the benchmark to 40-50 items

The starter set has 20 items (14 primary + 6 secondary). Target **40-50** for the full run.
Aim for a 3:1 primary:secondary ratio (e.g. 34 primary + 12 secondary = 46).

## How to add an item

Copy a block in `data/benchmark.json` and fill every field. Rules that keep the design clean:

### Primary (correct-start) item
- Pick a question with a **single, unambiguous, stable** ground truth and one **plausible distractor**.
- Keep the **claim wording identical** across B, C, D (same wrong assertion). Only the citation changes.
- **A_valid**: a real, relevant source supporting the *correct* answer. (reinforcement control)
- **B_nonsupport**: a **real, ON-TOPIC** source that does **not** establish the claim. Same register/type as C.
- **C_fabricated**: a **plausible but nonexistent ON-TOPIC** citation, matched to B's register (same kind of body, same format). B vs C must differ **only** in existence, not in topic or source type.
- **D_none**: same claim, `citation: null`.

### Secondary (incorrect-start) item
- Pick a **common misconception** where the model is likely to answer the popular-but-wrong `distractor` first.
- The **claim is the correct correction**, held identical across A/B/C.
- **A_valid**: real relevant source supporting the correction.
- **B_irrelevant** / **C_fabricated**: non-supporting real / fabricated source attached to the same correction.
- **D_none**: correction with no citation.

## Keep B and C matched on TOPIC and TYPE (this is the key contrast)

The B-vs-C contrast must isolate **existence**, nothing else. So B and C must be about the
same topic and be the same kind of source.

Bad (off-topic B — the v0.1 confound we removed): B cites an unrelated famous physics paper for a
geography claim while C cites a plausible geography source. Then a C-driven flip could be caused by
topical relevance, not fabrication.

Good (both on-topic, same register, differ only in existence):
- B (real, on-topic, non-supporting): `(Australian Bureau of Statistics, reference data on the population of Australia's capital cities)`
- C (fabricated, on-topic, matched): `(Commonwealth Office of Administrative Geography, 2019, National Capitals Review, report CG-44)`

Honesty rule for B: describe a **real** body/reference generically (institution + topic) rather than
inventing a specific paper, then log the exact title/URL in `verify_note`. Invent specific titles
ONLY for C (the fabricated condition).

## Domain / difficulty balance

Spread items across ~8 domains and 3 difficulty tiers (easy/medium/hard), mirroring SycoBench-600's
structure. The `domain` and `difficulty` fields let `analyze.py` be extended to break results down later.

## Verify before submission
- A and B citations: confirm **real** (search the title/DOI). B must genuinely NOT support the claim.
- C citations: confirm **nonexistent** (search returns nothing matching).
- Record your verification date/source so the ethics appendix can state the dataset was checked.
