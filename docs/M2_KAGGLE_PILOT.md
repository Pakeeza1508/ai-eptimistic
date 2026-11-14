# SourceCheck — VS Code → Kaggle private GPU pilot

Kaggle account: `pakeezakhalid`. Creates only a new private notebook
`sourcecheck-research-pilot`; never edits existing notebooks.
No token, API key, or Kaggle login data should be committed.

**Warning:** Kaggle interactive sessions are ephemeral. A script-based
`kernels push` creates a saved version; a **successful** version's
`/kaggle/working` outputs can be downloaded later. A failed/interrupted
version may lose partial files, even though records are flushed during
the run. Use one- or two-item batches and download each successful
version immediately; do not assume this is live remote checkpointing.

## 1. Update VS Code checkout

```powershell
git fetch origin
git switch --track origin/sprint/m2-kaggle-pilot
.\.venv\Scripts\Activate.ps1
```

If already tracking locally, use `git switch sprint/m2-kaggle-pilot`
then `git pull --ff-only`. The Kaggle CLI is invoked as
`python -m kaggle` because Windows policy blocks the kaggle.exe wrapper.

## 2. Verify data & build P01 one-question job (NO GPU calls)

```powershell
python tests/test_scoring.py
python tests/test_v04.py
python tests/test_audit.py
python src/validate_dataset.py data/benchmark.json --require-verified
python tools/build_kaggle_job.py --ids P01
```

This creates local `kaggle/sourcecheck/` with
`sourcecheck_kaggle.py` and `kernel-metadata.json`.
The model is the public `Qwen/Qwen2.5-1.5B-Instruct` open-weight
instruction model. It uses greedy decoding; reported weights, GPU,
package versions and raw token counts are stored in run metadata.
A model on a Kaggle GPU is different from an API-served model; do
not pool results across models/backends.

## 3. Create your new PRIVATE Kaggle notebook and RUN it

```powershell
python -m kaggle kernels push -p kaggle/sourcecheck
python -m kaggle kernels status pakeezakhalid/sourcecheck-research-pilot
```

`push` runs a remote notebook version. It requires access to Kaggle
GPU/Internet; account accelerator restrictions can cause failure.
Do not repeatedly push on an error; inspect status and log first.

After status becomes complete, download to a unique local folder:

```powershell
New-Item -ItemType Directory -Force results/kaggle/p01 | Out-Null
python -m kaggle kernels output pakeezakhalid/sourcecheck-research-pilot -p results/kaggle/p01
python -m kaggle kernels files pakeezakhalid/sourcecheck-research-pilot
```

The expected outputs are `sourcecheck_trials.jsonl` (4 conditions)
and `sourcecheck_run_metadata.json`; never submit findings until
you inspect raw JSON parsing, scoring and missing/error records.

## 4. Expand safely

After P01 results are **downloaded**, select two primary items and
publish a new saved Kaggle version:

```powershell
python tools/build_kaggle_job.py --ids P03,P07
python -m kaggle kernels push -p kaggle/sourcecheck
```

Wait for successful status, then download to a **different** local
folder (`results/kaggle/p03-p07`). Do NOT overwrite the P01 backup.
For secondary use `--seed-secondary`, e.g.:

```powershell
python tools/build_kaggle_job.py --ids S01,S03,S04 --seed-secondary
```

Every saved version replaces the Kaggle notebook's current code and
outputs, so separate downloaded folders are essential. You may also
create separately named Kaggle notebooks for independent versioned
records. The initial eight M1 items are only pilot-eligible by static
evidence gates; final human spot-check remains pending.

## 5. Scoring locally

After the first output download:

```powershell
python src/score.py --in results/kaggle/p01/sourcecheck_trials.jsonl --out results/kaggle/p01/scored.jsonl --method alias
python src/analyze.py --in results/kaggle/p01/scored.jsonl --out results/kaggle/p01/summary.json --boot 500
```

The first 1-item run is an engineering smoke test, **not** a
statistically meaningful empirical finding. Keep raw JSONL files
locally and record every model/hardware/revision setting.

## Privacy and limitations

- Notebook is **private**, but private notebooks still run on Kaggle's
  infrastructure. The selected questions and references are not
  secret; don't upload API keys, confidential customer data, or
  private account information.
- Hugging Face weights are downloaded from the public hub on first
  run. If network is unavailable, the job will fail; no fake results.
- Script flushes each trial and records a failure log if a Python
  error occurs, but only outputs of successful saved versions are
  reliably recoverable.
- Kaggle GPU quota, available hardware and Internet access vary by
  account. Neither a GPU reservation nor runtime is guaranteed.
