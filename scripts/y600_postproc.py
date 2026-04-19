"""Post-processing pipeline for Y600 push final reporting.

Consumes test_preds.npz files from one or more experiment variants and
produces a pooled, regime-stratified, bootstrap-CI report comparing
baselines to stacked variants.

Unlike y600_final_eval.py (which takes a single 'final_stack/' dir), this
script accepts an explicit list of variant dirs and produces a side-by-side
comparison table. Used when the 12-hour push cannot run full training and
the only available variants are post-hoc (SWA weight averaging, rank
transform, XGB blend).

CLI
---
    python scripts/y600_postproc.py \\
        --variants baseline=experiments/v4_noattn_700d_y600 \\
                   swa=experiments/v4_noattn_700d_y600 \\
        --out-report docs/Y600_POSTPROC_REPORT.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import spearmanr


def _pearson(p: np.ndarray, t: np.ndarray) -> float:
    if len(p) < 2 or np.std(p) == 0 or np.std(t) == 0:
        return 0.0
    return float(np.corrcoef(p, t)[0, 1])


def _spearman(p: np.ndarray, t: np.ndarray) -> float:
    if len(p) < 2:
        return 0.0
    r = spearmanr(p, t)
    v = float(r.statistic if hasattr(r, "statistic") else r[0])
    return v if np.isfinite(v) else 0.0


def _diracc(p: np.ndarray, t: np.ndarray) -> float:
    return float(np.mean(np.sign(p) == np.sign(t)))


def metrics_block(p: np.ndarray, t: np.ndarray) -> Dict[str, float]:
    return {
        "n": int(len(p)),
        "pearson": _pearson(p, t),
        "spearman": _spearman(p, t),
        "composite": 0.5 * _pearson(p, t) + 0.5 * _spearman(p, t),
        "diracc": _diracc(p, t),
    }


def block_bootstrap_ci(
    p: np.ndarray, t: np.ndarray, stat_fn,
    n_boot: int = 2000, block_len: int = 60, seed: int = 42,
) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(p)
    if n < block_len * 2:
        return (0.0, 0.0)
    stats = []
    n_blocks = int(np.ceil(n / block_len))
    for _ in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx_blocks = [np.arange(s, s + block_len) % n for s in starts]
        idx = np.concatenate(idx_blocks)[:n]
        stats.append(stat_fn(p[idx], t[idx]))
    arr = np.asarray(stats)
    return float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))


def tail_metrics(p: np.ndarray, t: np.ndarray, mad_sigma: float, k: float = 2.0) -> Dict[str, Any]:
    # Targets in test_preds.npz are z-normalised (divided by y_sigma, clipped
    # to ±5). So the k-σ tail threshold is simply k, not k·sigma.
    thresh = k
    m = np.abs(t) > thresh
    n = int(m.sum())
    if n < 10:
        return {"n_tail": n, "diracc": None}
    return {
        "threshold_z": thresh,
        "threshold_bps_equiv": thresh * mad_sigma * 1e4,
        "k_sigma": k, "n_tail": n,
        "diracc": _diracc(p[m], t[m]),
        "pearson": _pearson(p[m], t[m]),
        "spearman": _spearman(p[m], t[m]),
    }


def regime_strat(p: np.ndarray, t: np.ndarray, timestamps: np.ndarray) -> Dict[str, Any]:
    if len(timestamps) != len(p) or len(t) < 50:
        return {}
    order = np.argsort(timestamps)
    p_s = p[order]; t_s = t[order]
    win = max(20, len(t_s) // 60)
    pad = win // 2
    t_padded = np.concatenate([t_s[:pad], t_s, t_s[-pad:]])
    vol = np.array([np.std(t_padded[i:i + win]) for i in range(len(t_s))])
    q = np.quantile(vol, [1/3, 2/3])
    buckets = {"low": vol <= q[0], "mid": (vol > q[0]) & (vol <= q[1]), "high": vol > q[1]}
    out = {}
    for name, mb in buckets.items():
        if mb.sum() < 10:
            out[name] = None
        else:
            out[name] = {
                "n": int(mb.sum()),
                "pearson": _pearson(p_s[mb], t_s[mb]),
                "spearman": _spearman(p_s[mb], t_s[mb]),
                "diracc": _diracc(p_s[mb], t_s[mb]),
                "vol_bps": float(np.mean(vol[mb]) * 1e4),
            }
    return out


def load_fold(path: Path, stride_every: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    d = np.load(path)
    preds = d["predictions"]
    p = preds[:, 1] if preds.ndim == 2 and preds.shape[-1] >= 3 else preds.ravel()
    t = d["targets"]; m = d["mask"]
    ts = d.get("timestamps", np.zeros(len(t), dtype=np.int64))
    ysig = float(d["y_sigma"])
    if stride_every and stride_every > 1:
        p = p[::stride_every]; t = t[::stride_every]; m = m[::stride_every]
        ts = ts[::stride_every]
    mb = m.astype(bool)
    return {"p": p[mb].astype(np.float64), "t": t[mb].astype(np.float64),
            "ts": ts[mb], "y_sigma": ysig}


def analyze_variant(exp_dir: Path, preds_name: str = "test_preds.npz") -> Dict[str, Any]:
    folds = sorted(p for p in exp_dir.glob("fold_*") if p.is_dir() and not p.name.endswith("_backup"))
    r: Dict[str, Any] = {"folds": {}}
    pc, tc, pcs = [], [], []  # clean
    pd_, td, pds = [], [], []  # dense
    sigmas = []
    for fd in folds:
        best = load_fold(fd / preds_name)
        clean = load_fold(fd / preds_name, stride_every=10)
        if best is None or clean is None:
            r["folds"][fd.name] = {"error": "missing preds"}
            continue
        r["folds"][fd.name] = {
            "dense": metrics_block(best["p"], best["t"]),
            "clean": metrics_block(clean["p"], clean["t"]),
            "y_sigma_bps": best["y_sigma"] * 1e4,
        }
        pc.append(clean["p"]); tc.append(clean["t"]); pcs.append(clean["ts"])
        pd_.append(best["p"]); td.append(best["t"]); pds.append(best["ts"])
        sigmas.append(best["y_sigma"])

    if not pd_:
        return r
    pp, pt, pts = np.concatenate(pd_), np.concatenate(td), np.concatenate(pds)
    ppc, ptc = np.concatenate(pc), np.concatenate(tc)
    avg_sigma = float(np.mean(sigmas))

    r["pooled"] = {"dense": metrics_block(pp, pt), "clean": metrics_block(ppc, ptc)}
    # bootstrap CIs on clean
    lp, hp = block_bootstrap_ci(ppc, ptc, _pearson)
    ls, hs = block_bootstrap_ci(ppc, ptc, _spearman)
    r["pooled"]["clean"]["pearson_ci95"] = [lp, hp]
    r["pooled"]["clean"]["spearman_ci95"] = [ls, hs]
    r["tail"] = tail_metrics(pp, pt, avg_sigma)
    r["regime"] = regime_strat(pp, pt, pts)
    return r


def blend_variants(variants: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Rank-average predictions across variants per fold (pooled clean metric)."""
    # Find first variant with fold dir; get fold list.
    # For simplicity: require all variants share identical folds; load raw
    # preds arrays from each variant's exp_dir (stored in variants[name]["exp_dir"]).
    names = list(variants.keys())
    if len(names) < 2:
        return None
    fold_names = None
    for n in names:
        f_dirs = sorted(Path(variants[n]["exp_dir"]).glob("fold_*"))
        fold_names = [fd.name for fd in f_dirs if fd.is_dir() and not fd.name.endswith("_backup")]
        break
    if not fold_names:
        return None

    pooled_p_clean, pooled_t_clean, pooled_ts_clean = [], [], []
    sigmas = []
    fold_rows: Dict[str, Any] = {}
    for fn in fold_names:
        preds_per_variant = []
        t = None; ts = None; ysig = None; m = None
        for n in names:
            fd_path = Path(variants[n]["exp_dir"]) / fn / variants[n].get("preds", "test_preds.npz")
            loaded = load_fold(fd_path, stride_every=10)
            if loaded is None:
                preds_per_variant = []
                break
            preds_per_variant.append(loaded["p"])
            if t is None:
                t = loaded["t"]; ts = loaded["ts"]; ysig = loaded["y_sigma"]
        if not preds_per_variant:
            continue
        # Rank-average: convert each variant's preds to ranks, average ranks.
        rank_preds = []
        for p_v in preds_per_variant:
            r = np.argsort(np.argsort(p_v)).astype(np.float64)
            rank_preds.append(r)
        avg_rank = np.mean(rank_preds, axis=0)
        fold_rows[fn] = metrics_block(avg_rank, t)
        pooled_p_clean.append(avg_rank); pooled_t_clean.append(t); pooled_ts_clean.append(ts)
        sigmas.append(ysig)

    if not pooled_p_clean:
        return None
    pp, pt = np.concatenate(pooled_p_clean), np.concatenate(pooled_t_clean)
    out = {"folds": fold_rows, "pooled": metrics_block(pp, pt)}
    lp, hp = block_bootstrap_ci(pp, pt, _pearson)
    ls, hs = block_bootstrap_ci(pp, pt, _spearman)
    out["pooled"]["pearson_ci95"] = [lp, hp]
    out["pooled"]["spearman_ci95"] = [ls, hs]
    return out


def format_md(results: Dict[str, Dict[str, Any]], blend: Optional[Dict[str, Any]] = None) -> str:
    lines: List[str] = ["# V4 y_600 — Post-processing Push Report\n"]
    lines.append("## Variants — pooled clean metrics\n")
    lines.append("| Variant | N | Pearson | Pearson CI95 | Spearman | Spearman CI95 | DirAcc |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, r in results.items():
        if "pooled" not in r:
            continue
        c = r["pooled"]["clean"]
        lo_p, hi_p = c.get("pearson_ci95", [0, 0])
        lo_s, hi_s = c.get("spearman_ci95", [0, 0])
        lines.append(f"| {name} | {c['n']} | {c['pearson']:+.4f} | [{lo_p:+.4f}, {hi_p:+.4f}] | "
                     f"{c['spearman']:+.4f} | [{lo_s:+.4f}, {hi_s:+.4f}] | {c['diracc']:.3f} |")
    if blend and "pooled" in blend:
        b = blend["pooled"]
        lo_p, hi_p = b.get("pearson_ci95", [0, 0])
        lo_s, hi_s = b.get("spearman_ci95", [0, 0])
        lines.append(f"| **rank_blend** | {b['n']} | {b['pearson']:+.4f} | [{lo_p:+.4f}, {hi_p:+.4f}] | "
                     f"{b['spearman']:+.4f} | [{lo_s:+.4f}, {hi_s:+.4f}] | {b['diracc']:.3f} |")
    lines.append("")

    # Per-fold breakdown
    lines.append("## Per-fold (clean)\n")
    header = "| Fold | " + " | ".join(f"{n} P" for n in results) + " | " + " | ".join(f"{n} S" for n in results) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (1 + 2 * len(results)))
    fold_names = set()
    for r in results.values():
        fold_names.update(r.get("folds", {}).keys())
    for fn in sorted(fold_names):
        row = [fn]
        for n, r in results.items():
            fd = r["folds"].get(fn)
            if not fd or "clean" not in fd:
                row.append("—")
            else:
                row.append(f"{fd['clean']['pearson']:+.4f}")
        for n, r in results.items():
            fd = r["folds"].get(fn)
            if not fd or "clean" not in fd:
                row.append("—")
            else:
                row.append(f"{fd['clean']['spearman']:+.4f}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Tail + regime (first variant that has it)
    for name, r in results.items():
        t = r.get("tail")
        if t and t.get("n_tail"):
            lines.append(f"## Tail DirAcc ({name})\n")
            lines.append(f"- threshold: |z| > {t.get('threshold_z', 2.0):.1f} ({t.get('threshold_bps_equiv', 0):.2f} bps equivalent), N tail: {t['n_tail']}")
            lines.append(f"- DirAcc: {t['diracc']:.3f}  Pearson: {t['pearson']:+.4f}  Spearman: {t['spearman']:+.4f}")
            lines.append("")
            break

    # Verdict
    best = None
    for name, r in results.items():
        if "pooled" not in r:
            continue
        c = r["pooled"]["clean"]
        score = c["pearson"] + c["spearman"]
        if best is None or score > best[1]:
            best = (name, score, c)
    if blend and "pooled" in blend:
        b = blend["pooled"]
        score = b["pearson"] + b["spearman"]
        if best is None or score > best[1]:
            best = ("rank_blend", score, b)
    if best:
        name, _, c = best
        passed = c["pearson"] >= 0.08 and c["spearman"] >= 0.08
        partial = (c["pearson"] >= 0.08) != (c["spearman"] >= 0.08)
        verdict = "PASS" if passed else ("PARTIAL" if partial else "FAIL")
        lines.append(f"## Verdict: {verdict}\n")
        lines.append(f"Winning variant: **{name}**  (P={c['pearson']:+.4f} S={c['spearman']:+.4f})\n")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", required=True,
                    help="name=exp_dir[:preds_name] entries")
    ap.add_argument("--out-report", default=None)
    ap.add_argument("--blend", action="store_true",
                    help="Additionally compute rank-blend across all variants")
    args = ap.parse_args()

    variants: Dict[str, Dict[str, Any]] = {}
    for spec in args.variants:
        name, rest = spec.split("=", 1)
        parts = rest.split(":", 1)
        exp_dir = parts[0]
        preds_name = parts[1] if len(parts) > 1 else "test_preds.npz"
        variants[name] = {"exp_dir": exp_dir, "preds": preds_name}

    results: Dict[str, Dict[str, Any]] = {}
    for name, info in variants.items():
        exp_dir = Path(info["exp_dir"])
        print(f"=== analyzing {name} at {exp_dir} ===")
        results[name] = analyze_variant(exp_dir, preds_name=info.get("preds", "test_preds.npz"))

    blend_r = blend_variants(variants) if args.blend else None

    md = format_md(results, blend_r)
    out_path = Path(args.out_report) if args.out_report else Path("docs/Y600_POSTPROC_REPORT.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"REPORT: {out_path}")

    # save raw json too
    json_path = out_path.with_suffix(".json")
    all_data = {"variants": results}
    if blend_r:
        all_data["rank_blend"] = blend_r
    with open(json_path, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"JSON: {json_path}")
    print()
    print(md)


if __name__ == "__main__":
    main()
