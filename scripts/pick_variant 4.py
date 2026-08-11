"""Pick best among {best_model, ema_best} per fold by pooled composite metric.

Reads test_preds.npz (from best_model.pt eval) and ema_test_preds.npz
(from ema_best.pt eval) for each fold in an experiment directory, computes
pooled clean and dense Pearson + Spearman + composite, and writes a
winners.json plus a variant_summary.json that drops the losing variant.

Usage
-----
    python scripts/pick_variant.py \\
        --exp-dir experiments/y600_push/baseline_plus \\
        --out experiments/y600_push/baseline_plus/variant_summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from scipy.stats import spearmanr


def _metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
    m = mask.astype(bool)
    p = pred[m]
    t = target[m]
    if len(p) < 10:
        return {"n": 0, "pearson": 0.0, "spearman": 0.0, "composite": 0.0, "diracc": 0.0}
    pear = float(np.corrcoef(p, t)[0, 1])
    spear = float(spearmanr(p, t).statistic)
    diracc = float(np.mean(np.sign(p) == np.sign(t)))
    return {
        "n": int(len(p)),
        "pearson": pear,
        "spearman": spear,
        "composite": 0.5 * pear + 0.5 * spear,
        "diracc": diracc,
    }


def _load_preds(path: Path) -> Optional[Dict[str, np.ndarray]]:
    if not path.exists():
        return None
    d = np.load(path)
    preds = d["predictions"]
    p = preds[:, 1] if preds.ndim == 2 and preds.shape[-1] >= 3 else preds.ravel()
    return {
        "p": p,
        "t": d["targets"],
        "m": d["mask"],
    }


def _pooled(arrays_p, arrays_t, arrays_m):
    p = np.concatenate(arrays_p)
    t = np.concatenate(arrays_t)
    m = np.concatenate(arrays_m)
    return _metrics(p, t, m)


def pick(exp_dir: Path) -> Dict[str, Any]:
    folds = sorted(p for p in exp_dir.glob("fold_*") if p.is_dir())
    if not folds:
        raise RuntimeError(f"no fold_* dirs under {exp_dir}")

    result: Dict[str, Any] = {"folds": {}, "variants_considered": []}

    variants = {
        "best": ("test_preds.npz", None),
        "ema": ("ema_test_preds.npz", None),
    }

    # discover which variants actually exist
    present = {}
    for name, (preds_name, _) in variants.items():
        any_found = False
        for fd in folds:
            if (fd / preds_name).exists():
                any_found = True
                break
        if any_found:
            present[name] = preds_name
    result["variants_considered"] = list(present.keys())

    variant_pool: Dict[str, Dict[str, list]] = {
        name: {"p_clean": [], "t_clean": [], "m_clean": [],
                "p_dense": [], "t_dense": [], "m_dense": []}
        for name in present
    }

    for fd in folds:
        fold_name = fd.name
        fd_row: Dict[str, Any] = {}
        for name, preds_name in present.items():
            preds = _load_preds(fd / preds_name)
            if preds is None:
                fd_row[name] = None
                continue
            p, t, m = preds["p"], preds["t"], preds["m"]
            dense = _metrics(p, t, m)
            p10 = p[::10]; t10 = t[::10]; m10 = m[::10]
            clean = _metrics(p10, t10, m10)
            fd_row[name] = {"dense": dense, "clean": clean}
            variant_pool[name]["p_dense"].append(p); variant_pool[name]["t_dense"].append(t); variant_pool[name]["m_dense"].append(m)
            variant_pool[name]["p_clean"].append(p10); variant_pool[name]["t_clean"].append(t10); variant_pool[name]["m_clean"].append(m10)
        result["folds"][fold_name] = fd_row

    # pooled per variant
    pooled: Dict[str, Dict[str, Any]] = {}
    for name, pool in variant_pool.items():
        if pool["p_dense"]:
            pooled[name] = {
                "dense": _pooled(pool["p_dense"], pool["t_dense"], pool["m_dense"]),
                "clean": _pooled(pool["p_clean"], pool["t_clean"], pool["m_clean"]),
            }
    result["pooled"] = pooled

    # winner = highest pooled CLEAN composite (matches training selector)
    if pooled:
        winner = max(pooled.items(), key=lambda kv: kv[1]["clean"]["composite"])
        result["winner"] = {
            "name": winner[0],
            "pooled_clean": winner[1]["clean"],
            "pooled_dense": winner[1]["dense"],
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    exp_dir = Path(args.exp_dir)
    r = pick(exp_dir)

    out_path = Path(args.out) if args.out else exp_dir / "variant_summary.json"
    with open(out_path, "w") as f:
        json.dump(r, f, indent=2)

    print("=" * 68)
    print(f"VARIANT PICKER: {exp_dir}")
    print("=" * 68)
    print(f"variants considered: {r['variants_considered']}")
    print()
    for fname, row in r["folds"].items():
        print(f"--- {fname} ---")
        for vname, m in row.items():
            if m is None:
                print(f"  {vname}: MISSING")
                continue
            c = m["clean"]; d = m["dense"]
            print(f"  {vname}: dense N={d['n']} P={d['pearson']:+.4f} S={d['spearman']:+.4f} C={d['composite']:+.4f} "
                  f"| clean N={c['n']} P={c['pearson']:+.4f} S={c['spearman']:+.4f} C={c['composite']:+.4f}")
    print()
    print("POOLED:")
    for vname, pv in r.get("pooled", {}).items():
        c = pv["clean"]; d = pv["dense"]
        print(f"  {vname}: dense N={d['n']} P={d['pearson']:+.4f} S={d['spearman']:+.4f} C={d['composite']:+.4f} "
              f"| clean N={c['n']} P={c['pearson']:+.4f} S={c['spearman']:+.4f} C={c['composite']:+.4f}")
    w = r.get("winner")
    if w:
        print()
        print(f"WINNER: {w['name']}  (pooled clean composite {w['pooled_clean']['composite']:+.4f})")
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
