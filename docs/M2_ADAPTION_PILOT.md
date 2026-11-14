# Milestone 2 — Adaption real-model pilot (13 November 2026)

This sprint-day code is an **unexecuted integration** for Adaption's Responses API,
not empirical research. Prior code and citation evidence remain attributed under
`PRE_SPRINT_DISCLOSURE.md`. Research protocol is unchanged.

## Official documentation

- Python SDK setup: https://docs.adaptionlabs.ai/inference-stacks/quickstart/
- Responses API: https://docs.adaptionlabs.ai/api/python/resources/responses/methods/create
- Available hosted models: https://docs.adaptionlabs.ai/api/python/resources/models/methods/list

Adaption's official SDK uses `ADAPTION_API_KEY`, `client.models.list(type="hosted")`,
and `client.responses.create(...)`. The SourceCheck adapter uses `instructions=SYSTEM`,
transmits ordered roles/messages, and requests `temperature=0`, `tools=[]`,
`tool_choice="none"`, `agentic_memory=False`, and `store=False` to preserve
the closed-book protocol. Note that support for each optional parameter depends on
the account's hosted model: unsupported parameters should fail visibly, never be
silently dropped without recording a protocol amendment.

## Local account setup (Windows PowerShell)

1. Open the organizer's Adaption referral link to sign up:
   https://adaptionlabs.ai/app/auth/referral?ref=ai-epistemics-research-sprint
2. Check whether the promised sprint Builder plan / 1,250 credits are actually
   present in your account; an email offer is **not proof** that credits are applied,
   available to hosted-model inference, or sufficient for this experiment.
3. In Adaption dashboard: Settings → API keys → create a key. Never send it in chat,
   record it in results, or commit it.
4. Activate your Python virtual environment and install:
   `python -m pip install "adaption>=0.16.0"`
5. Set the key **for this PowerShell session only** (you will be prompted without
   echoing the secret on screen):

```powershell
$SecureKey = Read-Host "Adaption API key" -AsSecureString
$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
try { $env:ADAPTION_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR) }
Remove-Variable SecureKey, BSTR
```

6. List **your own** available model IDs (this calls the provider and requires a key):

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from adaption_backend import list_available_hosted_models; print(list_available_hosted_models())"
```

Pick a **hosted base-model ID**, not an agent/inference stack that might have
uncontrolled tools or memory. Document model ID and provider in the run report.

## Offline regression tests (zero API calls)

```powershell
python tests/test_scoring.py
python tests/test_v04.py
python tests/test_audit.py
python tests/test_adaption.py
python src/validate_dataset.py data/benchmark.json --require-verified
```

## Smallest real API pilot

Replace `YOUR_HOSTED_MODEL_ID` with an ID from the model list. For an initial
integration smoke test, one primary question is sufficient (1 initial answer
plus four rebuttal calls):

```powershell
python src/run_experiment.py --backend adaption --model YOUR_HOSTED_MODEL_ID --temperature 0 --ids P01 --limit 1 --out results/adaption_p01.jsonl
python src/score.py --in results/adaption_p01.jsonl --out results/adaption_p01.scored.jsonl --method alias
python src/analyze.py --in results/adaption_p01.scored.jsonl --out results/adaption_p01.summary.json --boot 500
```

Then manually inspect all five model responses before expanding. This is a
**smoke test, not a research finding**. `results/` is gitignored.

The 8 selected items are P01, P03, P05, P07, P09, S01, S03, S04.
For a pilot across primary and secondary:
```powershell
python src/run_experiment.py --backend adaption --model YOUR_HOSTED_MODEL_ID --temperature 0 --ids P01,P07,S01 --seed-secondary --out results/adaption_small.jsonl
```
This performs 12 condition-level evaluations, with one baseline call per
primary question. Do not rerun into the same `--out` without deliberate
`--resume` or `--force`.

## Research interpretation

- No trial has run at the time this guide was written.
- The human spot-check of M1 evidence remains pending; treat initial runs as
  **exploratory** until reviewed.
- B real/well-known institutions and C invented institutions differ in
  familiarity, not only existence. P03 B contradicts and reuses A, unlike most
  related-only B items; report subtypes separately.
- The small 5-primary/3-secondary pilot is underpowered; avoid causal or
  general-population claims from these results.
- A real model's failure to emit expected JSON is an observed parse error,
  not permission to fabricate or silently repair its response.
- Record actual request count, outputs and token usage; don't invent costs.

## Limited-credit safety checklist (14 November 2026)

**Adaption inference prices / credit-to-token conversion were not verifiable from public docs.**
Do not mistake credit estimates for dataset adaptation or training for hosted inference pricing.
Before a paid inference, read actual account credit balance and the selected hosted
model's per-token credit charge (or ask Adaption support). Model listing may not
show billing rates. An unverified 1,250-credit promotional offer is not a budget.

The runner performs five requests for one natural-start primary item (one initial,
four rebuttals); four requests for one seeded-secondary item. For the eight
pilot items with `--seed-secondary`: 5*5+3*4 = **37 provider calls** without
errors. Fully natural starts require **40**. These numbers exclude retries.

To minimize accidental expenditure:

1. The Adaption SDK client uses `max_retries=0`; runner defaults to exactly
   `--retries 1` with Adaption (one attempt, no extra attempt after error).
2. Check credits and per-model charges **before** invoking the runner.
3. Run `--ids P01 --limit 1 --retries 1` into a unique output file, then review
   actual usage and account balance. Stop if either usage or billing differs from
   expectations. Every model response is capped at 512 output tokens, not a
   guarantee about cost or actual consumption.
4. Do not use `--repeats` until cost and model quality have been measured.
5. Do not use `--force` on an existing output; it would rerun and rebill.
6. An authentication or parameter failure must be fixed offline; do not
   continuously retry on credit-limited accounts.

**Study caveat:** this code has not made a real Adaption inference call. A live
API smoke test is needed to confirm that the selected model accepts the SDK
options, including `temperature=0`, `store=False` and `tool_choice='none'`.
