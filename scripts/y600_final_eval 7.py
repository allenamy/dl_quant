"""Final robustness evaluation for Y600 push final stack.

Takes a fold directory (one or more) with test_preds.npz files and
produces pooled + per-fold + regime-stratified + tail + bootstrap-CI
metrics. Writes a markdown report.

CLI
---
    python scripts/y600_final_eval.py \\
        --stack-dir experiments/y600_push/final_stack \\
        --baseline-file experiments/y600_push/_baseline_frozen.json \\
        --out-report docs/Y600_PUSH_REPORT.md \\
        --bootstrap-b 2000 --block-len 60
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import spearmanr


# -----------------------------------------------------------------------------
# Metric helpers
# -----------------------------------------------------------------------------

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


def _metrics_block(p: np.ndarray, t: np.ndarray) -> Dict[str, float]:
    return {
        "n": int(len(p)),
        "pearson": _pearson(p, t),
        "spearman": _spearman(p, t),
        "diracc": _diracc(p, t),
    }


# -----------------------------------------------------------------------------
# Bootstrap CI
# -----------------------------------------------------------------------------

def block_bootstrap_ci(
    p: np.ndarray,
    t: np.ndarray,
    stat_fn,
    n_boot: int = 2000,
    block_len: int = 60,
    seed: int = 42,
) -> Tuple[float, float]:
    """Stationary block bootstrap for IC-like statistics. Returns 95% CI."""
    rng = np.random.default_rng(seed)
    n = len(p)
    if n < block_len * 2:
        return (0.0, 0.0)
    stats = []
    n_blocks = int(np.ceil(n / block_len))
    for _ in range(n_boot):
        # random start offsets wrap-around
        starts = rng.integers(0, n, size=n_blocks)
        idx_blocks = [np.arange(s, s + block_len) % n for s in starts]
        idx = np.concatenate(idx_blocks)[:n]
        stats.append(stat_fn(p[idx], t[idx]))
    stats_arr = np.asarray(stats)
    return float(np.percentile(stats_arr, 2.5)), float(np.percentile(stats_arr, 97.5))


# -----------------------------------------------------------------------------
# Tail + regime stratification
# -----------------------------------------------------------------------------

def tail_diracc(p: np.ndarray, t: np.ndarray, mad_sigma: float, k: float = 2.0) -> Dict[str, Any]:
    thresh = k * mad_sigma
    tail_mask = np.abs(t) > thresh
    n_tail = int(tail_mask.sum())
    if n_tail < 10:
        return {"threshold_bps": thresh * 1e4, "n_tail": n_tail, "diracc": None}
    p_tail = p[tail_mask]; t_tail = t[tail_mask]
    return {
        "threshold_bps": thresh * 1e4,
        "k_sigma": k,
        "n_tail": n_tail,
        "diracc": _diracc(p_tail, t_tail),
        "pearson": _pearson(p_tail, t_tail),
        "spearman": _spearman(p_tail, t_tail),
    }


def regime_stratified(
    p: np.ndarray, t: np.ndarray, timestamps: np.ndarray,
    window_sec: int = 3600,
) -> Dict[str, Any]:
    """Split by realized vol computed on rolling windows. Report per-bucket IC."""
    if len(timestamps) != len(p) or len(t) < 50:
        return {"error": "insufficient data or mismatched timestamps"}
    # Realized vol proxy: rolling std of targets (as a stand-in for realized vol)
    # Sort by timestamp to produce stable buckets
    order = np.argsort(timestamps)
    p_s = p[order]; t_s = t[order]
    # Rolling std over ~1h worth of samples (assuming stride=180 → 20 samples/hr)
    win = max(20, len(t_s) // 60)
    pad = win // 2
    t_padded = np.concatenate([t_s[:pad], t_s, t_s[-pad:]])
    vol = np.array([
        np.std(t_padded[i:i + win])
        for i in range(len(t_s))
    ])
    # Split into terciles
    q = np.quantile(vol, [1 / 3, 2 / 3])
    low = vol <= q[0]; mid = (vol > q[0]) & (vol <= q[1]); high = vol > q[1]
    out = {}
    for name, m in [("low_vol", low), ("mid_vol", mid), ("high_vol", high)]:
        if m.sum() < 10:
            out[name] = None
        else:
            out[name] = {
                "n": int(m.sum()),
                "pearson": _pearson(p_s[m], t_s[m]),
                "spearman": _spearman(p_s[m], t_s[m]),
                "diracc": _diracc(p_s[m], t_s[m]),
                "avg_vol_bps": float(np.mean(vol[m]) * 1e4),
            }
    return out


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def _load_pred(path: Path, stride_every: Optional[int] = None) -> Optional[Dict[str, np.ndarray]]:
    if not path.exists():
        return None
    d = np.load(path)
    preds = d["predictions"]
    p = preds[:, 1] if preds.ndim == 2 and preds.shape[-1] >= 3 else preds.ravel()
    t = d["targets"]; m = d["mask"]
    ts = d.get("timestamps", np.zeros(len(t), dtype=np.int64))
    ysig = float(d["y_sigma"])
    if stride_every is not None and stride_every > 1:
        p = p[::stride_every]; t = t[::stride_every]; m = m[::stride_every]
        ts = ts[::stride_every]
    mbool = m.astype(bool)
    return {
        "p": p[mbool].astype(np.float64),
        "t": t[mbool].astype(np.float64),
        "ts": ts[mbool],
        "y_sigma": ysig,
    }


def run(stack_dir: Path, baseline_file: Optional[Path],
        bootstrap_b: int, block_len: int) -> Dict[str, Any]:
    folds = sorted(p for p in stack_dir.glob("fold_*") if p.is_dir())
    if not folds:
        raise RuntimeError(f"no fold_* under {stack_dir}")

    report: Dict[str, Any] = {"folds": {}}
    pool_p_clean, pool_t_clean, pool_ts_clean = [], [], []
    pool_p_dense, pool_t_dense, pool_ts_dense = [], [], []
    sigmas = []

    for fd in folds:
        ffd: Dict[str, Any] = {}
        # try test_preds.npz first; fall back to ema_test_preds.npz
        best = _load_pred(fd / "test_preds.npz")
        if best is None:
            best = _load_pred(fd / "ema_test_preds.npz")
        if best is None:
            ffd["error"] = "no preds"
            report["folds"][fd.name] = ffd
            continue
        clean = _load_pred(fd / "test_preds.npz", stride_every=10) or _load_pred(
            fd / "ema_test_preds.npz", stride_every=10
        )
        ffd["dense"] = _metrics_block(best["p"], best["t"])
        ffd["clean"] = _metrics_block(clean["p"], clean["t"])
        ffd["y_sigma_bps"] = best["y_sigma"] * 1e4
        report["folds"][fd.name] = ffd

        pool_p_dense.append(best["p"]); pool_t_dense.append(best["t"]); pool_ts_dense.append(best["ts"])
        pool_p_clean.append(clean["p"]); pool_t_clean.append(clean["t"]); pool_ts_clean.append(clean["ts"])
        sigmas.append(best["y_sigma"])

    if not pool_p_dense:
        return report

    pp = np.concatenate(pool_p_dense); pt = np.concatenate(pool_t_dense); pts = np.concatenate(pool_ts_dense)
    ppc = np.concatenate(pool_p_clean); ptc = np.concatenate(pool_t_clean); ptsc = np.concatenate(pool_ts_clean)
    avg_sigma = float(np.mean(sigmas))

    # pooled metrics
    report["pooled"] = {
        "dense": _metrics_block(pp, pt),
        "clean": _metrics_block(ppc, ptc),
    }

    # bootstrap CI on clean Pearson + Spearman
    low_p, high_p = block_bootstrap_ci(ppc, ptc, _pearson, n_boot=bootstrap_b, block_len=block_len)
    low_s, high_s = block_bootstrap_ci(ppc, ptc, _spearman, n_boot=bootstrap_b, block_len=block_len)
    report["pooled"]["clean"]["pearson_ci95"] = [low_p, high_p]
    report["pooled"]["clean"]["spearman_ci95"] = [low_s, high_s]

    # tail + regime (on dense for statistical power)
    report["tail"] = tail_diracc(pp, pt, mad_sigma=avg_sigma, k=2.0)
    report["regime"] = regime_stratified(pp, pt, pts)

    # baseline comparison
    if baseline_file and Path(baseline_file).exists():
        baseline = json.loads(Path(baseline_file).read_text())
        if "pooled" in baseline and "clean_stride10" in baseline["pooled"]:
            bp = baseline["pooled"]["clean_stride10"]
            report["baseline_comparison"] = {
                "baseline_pooled_clean": bp,
                "delta": {
                    "pearson": report["pooled"]["clean"]["pearson"] - bp["pearson"],
                    "spearman": report["pooled"]["clean"]["spearman"] - bp["spearman"],
                },
            }

    return report


def format_md(rep: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# V4 y_600 12-Hour Push — Final Report\n")
    if "baseline_comparison" in rep:
        bc = rep["baseline_comparison"]["baseline_pooled_clean"]
        c = rep["pooled"]["clean"]
        lines.append("## Headline\n")
        lines.append(f"| | Pearson | Spearman | DirAcc |")
        lines.append(f"|---|---:|---:|---:|")
        lines.append(f"| Baseline (frozen) | {bc['pearson']:+.4f} | {bc['spearman']:+.4f} | {bc.get('diracc', 0):.3f} |")
        lines.append(f"| Final stack | {c['pearson']:+.4f} | {c['spearman']:+.4f} | {c['diracc']:.3f} |")
        lines.append(f"| Δ | {rep['baseline_comparison']['delta']['pearson']:+.4f} | {rep['baseline_comparison']['delta']['spearman']:+.4f} | |")
        lines.append("")

    # per-fold
    lines.append("## Per-fold (clean / dense)\n")
    lines.append(f"| Fold | Clean N | Clean P | Clean S | Clean Dir | Dense N | Dense P | Dense S |")
    lines.append(f"|---|---:|---:|---:|---:|---:|---:|---:|")
    for fname, row in rep["folds"].items():
        if "error" in row:
            lines.append(f"| {fname} | — | — | — | — | — | — | — |")
            continue
        c = row["clean"]; d = row["dense"]
        lines.append(f"| {fname} | {c['n']} | {c['pearson']:+.4f} | {c['spearman']:+.4f} | {c['diracc']:.3f} | "
                     f"{d['n']} | {d['pearson']:+.4f} | {d['spearman']:+.4f} |")
    lines.append("")

    # pooled
    c = rep["pooled"]["clean"]; d = rep["pooled"]["dense"]
    lines.append("## Pooled\n")
    lines.append(f"- **Clean** (stride_every=10): N={c['n']}  "
                 f"P={c['pearson']:+.4f} (95% CI [{c.get('pearson_ci95', [0, 0])[0]:+.4f}, {c.get('pearson_ci95', [0, 0])[1]:+.4f}])  "
                 f"S={c['spearman']:+.4f} (95% CI [{c.get('spearman_ci95', [0, 0])[0]:+.4f}, {c.get('spearman_ci95', [0, 0])[1]:+.4f}])  "
                 f"Dir={c['diracc']:.3f}")
    lines.append(f"- **Dense**: N={d['n']}  P={d['pearson']:+.4f}  S={d['spearman']:+.4f}  Dir={d['diracc']:.3f}")
    lines.append("")

    # tail
    t = rep.get("tail", {})
    if t.get("n_tail"):
        lines.append("## Tail (|y| > 2·MAD-σ)\n")
        lines.append(f"- threshold: {t['threshold_bps']:.2f} bps")
        lines.append(f"- N tail: {t['n_tail']}")
        lines.append(f"- DirAcc: {t.get('diracc', 0):.3f}  (gate: ≥ 0.52)")
        lines.append(f"- Pearson: {t.get('pearson', 0):+.4f}")
        lines.append(f"- Spearman: {t.get('spearman', 0):+.4f}")
        lines.append("")

    # regime
    r = rep.get("regime", {})
    if isinstance(r, dict) and "low_vol" in r:
        lines.append("## Regime (vol terciles)\n")
        lines.append("| Bucket | N | Pearson | Spearman | DirAcc | Avg vol bps |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for bucket in ("low_vol", "mid_vol", "high_vol"):
            v = r.get(bucket)
            if v is None:
                lines.append(f"| {bucket} | — | — | — | — | — |")
                continue
            lines.append(f"| {bucket} | {v['n']} | {v['pearson']:+.4f} | {v['spearman']:+.4f} | {v['diracc']:.3f} | {v['avg_vol_bps']:.2f} |")
        lines.append("")

    # verdict
    if "pooled" in rep:
        c = rep["pooled"]["clean"]
        passed_pearson = c["pearson"] >= 0.08
        passed_spearman = c["spearman"] >= 0.08
        if passed_pearson and passed_spearman:
            verdict = "PASS"
        elif passed_pearson or passed_spearman:
            verdict = "PARTIAL"
        else:
            verdict = "FAIL"
        lines.append(f"## Verdict: **{verdict}**\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack-dir", required=True)
    ap.add_argument("--baseline-file", default=None)
    ap.add_argument("--out-report", default=None)
    ap.add_argument("--bootstrap-b", type=int, default=2000)
    ap.add_argument("--block-len", type=int, default=60)
    args = ap.parse_args()

    stack_dir = Path(args.stack_dir)
    baseline_file = Path(args.baseline_file) if args.baseline_file else None
    rep = run(stack_dir, baseline_file, args.bootstrap_b, args.block_len)

    # always write json next to stack
    json_path = stack_dir / "final_eval.json"
    with open(json_path, "w") as f:
        json.dump(rep, f, indent=2)
    print(f"JSON: {json_path}")

    md = format_md(rep)
    md_path = Path(args.out_report) if args.out_report else (stack_dir / "REPORT.md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md)
    print(f"REPORT: {md_path}")
    print()
    print(md)


if __name__ == "__main__":
    main()
