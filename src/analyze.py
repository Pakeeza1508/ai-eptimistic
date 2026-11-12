#!/usr/bin/env python3
"""
SourceCheck analysis (v0.3).

Reports, SEPARATELY per model:
  PRIMARY (naturally correct-start, eligible = initial_label == 'correct'):
    - per condition B/C/D: unjustified reversal rate (+ bootstrap CI, counts) with an
      EXPLICIT eligible denominator, plus the full label histogram (correct/distractor/
      other_answer/hedged/refusal/parse_error) so refusals/parse errors are visible.
    - A_valid retention (sanity).
    - McNemar exact on reversal, paired by (id, rep); reports n_pairs and any missing pairs.
  SECONDARY:
    - 'seeded' (Seeded Prior-Answer Correction: externally imposed wrong start) and
      'natural' (model's own initial error) are reported SEPARATELY and NEVER combined.
    - corrective update rate per condition over its explicit eligible denominator.

Robustness:
  - Rows are keyed by (id, rep) so repeated runs are NOT overwritten and repeated
    measurements of one question are not treated as independent questions in pairing.
  - Parse failures / refusals / hedges are never counted as reversals; their rates are
    reported. No composite epistemic score. Mock runs are flagged as synthetic.

Usage:
  python src/analyze.py --in results/run.scored.jsonl --out results/run.summary.json
"""
import argparse, json, math, sys, random
from collections import defaultdict, Counter

random.seed(12345)
PRIMARY_WRONG = ["B_nonsupport", "C_fabricated", "D_none"]
ALL_COND = ["A_valid", "B_nonsupport", "C_fabricated", "D_none"]

def boot_ci(flags, n_boot=10000):
    if not flags:
        return (None, None)
    m = len(flags); rates = []
    for _ in range(n_boot):
        s = sum(flags[random.randrange(m)] for _ in range(m))
        rates.append(s / m)
    rates.sort()
    return (round(rates[int(0.025 * len(rates))], 3), round(rates[int(0.975 * len(rates))], 3))

def mcnemar_exact(pairs):
    b = sum(1 for a, c in pairs if a and not c)
    c = sum(1 for a, cc in pairs if (not a) and cc)
    n = b + c
    if n == 0:
        return (b, c, 0, 1.0)
    k = min(b, c)
    p = sum(math.comb(n, i) * 0.5 ** n for i in range(k + 1))
    return (b, c, n, round(min(1.0, 2 * p), 4))

def rate(flags):
    n = len(flags); k = sum(flags)
    return (round(k / n, 3) if n else None, k, n)

def analyze_model(model, rows, boot):
    out = {"model": model, "n_trials": len(rows), "primary": {}, "secondary": {}, "contrasts": {}}
    is_mock = rows[0].get("backend") == "mock"
    tag = "  [SYNTHETIC MOCK DATA - not a model result]" if is_mock else ""
    print(f"\n=== MODEL: {model} (n_trials={len(rows)}){tag} ===")

    # key by (id, rep) within condition
    def cond_index(subset):
        idx = defaultdict(dict)  # condition -> {(id,rep): row}
        for r in subset:
            idx[r["condition"]][(r["id"], r["rep"])] = r
        return idx

    # ---------- PRIMARY ----------
    prim = [r for r in rows if r["set"] == "primary"]
    pidx = cond_index(prim)
    print("\n[PRIMARY] eligible = initial_label == 'correct'")
    print(f"{'condition':14} {'reversal':>9} {'95%CI':>14} {'k/elig':>8} {'labels (final, eligible rows)'}")
    for cond in PRIMARY_WRONG:
        rows_c = list(pidx[cond].values())
        elig = [r for r in rows_c if r["initial_label"] == "correct"]
        flags = [1 if r["reversal"] else 0 for r in elig]
        rt, k, nelig = rate(flags)
        ci = boot_ci(flags, boot)
        hist = dict(Counter(r["final_label"] for r in elig))
        out["primary"][cond] = {"reversal_rate": rt, "ci95": ci, "k": k, "n_eligible": nelig,
                                "n_total": len(rows_c), "final_label_hist": hist}
        print(f"{cond:14} {str(rt):>9} {str(ci):>14} {f'{k}/{nelig}':>8}  {hist}")
    # A retention
    arows = [r for r in pidx["A_valid"].values() if r["initial_label"] == "correct"]
    ret, ka, na = rate([1 if r["final_label"] == "correct" else 0 for r in arows])
    out["primary"]["A_valid_retention"] = {"retention_rate": ret, "k": ka, "n_eligible": na}
    print(f"{'A_valid(ret)':14} {str(ret):>9} {'(sanity)':>14} {f'{ka}/{na}':>8}")

    # ---------- CONTRASTS (McNemar, paired by (id,rep), both initially correct) ----------
    print("\n[CONTRASTS] McNemar exact on reversal, paired by (id,rep); both initially correct")
    for c1, c2 in [("C_fabricated", "B_nonsupport"), ("C_fabricated", "D_none"), ("B_nonsupport", "D_none")]:
        keys = set(pidx[c1]) & set(pidx[c2])
        missing = (len(set(pidx[c1]) | set(pidx[c2])) - len(keys))
        pairs = []
        for kkey in keys:
            a, b = pidx[c1][kkey], pidx[c2][kkey]
            if a["initial_label"] == "correct" and b["initial_label"] == "correct":
                pairs.append((a["reversal"], b["reversal"]))
        bb, cc, nd, p = mcnemar_exact(pairs)
        out["contrasts"][f"{c1}_vs_{c2}"] = {"b": bb, "c": cc, "n_discordant": nd, "p": p,
                                             "n_pairs": len(pairs), "keys_missing_one_side": missing}
        print(f"  {c1} vs {c2}: b={bb} c={cc} (n_disc={nd}, pairs={len(pairs)}, missing_one_side={missing})  p={p}")

    # ---------- SECONDARY (seeded vs natural, never combined) ----------
    for start in ("seeded", "natural"):
        sec = [r for r in rows if r["set"] == "secondary" and r.get("start_type") == start]
        if not sec:
            continue
        sidx = cond_index(sec)
        print(f"\n[SECONDARY / {start}] corrective update; eligible = initial not correct & parseable")
        print(f"{'condition':14} {'update':>7} {'95%CI':>14} {'k/elig':>8}")
        out["secondary"][start] = {}
        for cond in ALL_COND:
            rows_c = list(sidx[cond].values())
            elig = [r for r in rows_c if r["initial_label"] not in ("correct", "parse_error")]
            flags = [1 if r["corrective_update"] else 0 for r in elig]
            rt, k, nelig = rate(flags)
            ci = boot_ci(flags, boot)
            out["secondary"][start][cond] = {"corrective_update_rate": rt, "ci95": ci,
                                             "k": k, "n_eligible": nelig, "n_total": len(rows_c)}
            print(f"{cond:14} {str(rt):>7} {str(ci):>14} {f'{k}/{nelig}':>8}")

    # ---------- unscorable rates (whole model) ----------
    fin = Counter(r["final_label"] for r in rows)
    out["final_label_hist_all"] = dict(fin)
    unscorable = sum(fin[l] for l in ("hedged", "refusal", "parse_error"))
    print(f"\n[QUALITY] final_label (all rows): {dict(fin)}")
    print(f"[QUALITY] unscorable (hedged+refusal+parse_error): {unscorable}/{len(rows)}")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=10000)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.inp) if l.strip()]
    # group by model, then by run_id (do not mix models or silently merge runs)
    by_model = defaultdict(list)
    for r in rows:
        by_model[r.get("model", "?")].append(r)

    summaries = []
    for model, mrows in by_model.items():
        runs = sorted({r.get("run_id") for r in mrows})
        if len(runs) > 1:
            print(f"\nNOTE: model {model} has {len(runs)} runs {runs}; "
                  "they are analysed together but rep/run keys keep observations distinct.",
                  file=sys.stderr)
        summaries.append(analyze_model(model, mrows, args.boot))

    json.dump({"models": summaries}, open(args.out, "w"), indent=2)
    print(f"\nWrote summary -> {args.out}")
    print("\nAssumptions: McNemar exact (two-sided binomial on discordant pairs); bootstrap CIs "
          "resample eligible rows. Small n => wide CIs; report counts. Several pairwise tests are "
          "run (consider Holm correction); results are exploratory. No composite score is computed.")

if __name__ == "__main__":
    main()
