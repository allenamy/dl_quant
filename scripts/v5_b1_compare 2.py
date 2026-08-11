"""V5 B.1 backbone screen comparison.

Aggregates fold-0 metrics from all available backbones in experiments/v5_screen/B1/
and produces a comparison table + winner selection per V5 gates.

Usage:
  python scripts/v5_b1_compare.py
  python scripts/v5_b1_compare.py --out exports/v5_b1_summary.md
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v5_eval_comprehensive import compute_v5_metrics, check_v5_gates, load_fold


CANDIDATES = ["v4base", "attention", "mamba", "emapool"]
CKPTS = ["test_preds.npz", "ema_test_preds.npz", "swa_test_preds.npz"]


def evaluate_run(run_dir: Path) -> dict:
    """Try BEST then EMA then SWA, return first available metrics."""
    out = {}
    for ckpt in CKPTS:
        npz = run_dir / "fold_0" / ckpt
        if not npz.exists():
            continue
        ckpt_label = ckpt.replace("_test_preds.npz", "").upper() or "BEST"
        try:
            data = load_fold(npz)
            m = compute_v5_metrics(data["y_lr"], data["yp_lr"], data["mask"])
            m["ckpt"] = ckpt_label
            out[ckpt_label] = m
        except Exception as e:
            print(f"  [WARN] {npz.name}: {e}")
    return out


def winner_score(m: dict) -> float:
    """Weighted score for backbone ranking.

    Prioritize σ_ŷ/σ_y (level expression) heavily — that's the V5 thesis.
    Penalize β deviation. Bonus for top-decile spread.
    """
    if not m or m.get("n", 0) < 30:
        return -999
    P = m.get("P", 0)
    sigma_ratio = m.get("sigma_ratio", 0)
    beta_dev = abs(m.get("beta", 0) - 1.0)
    spread = m.get("top_minus_bottom_bps", 0) or 0
    bin_S = m.get("bin_S", 0)
    # composite: P contributes most (statistical signal), σ_ratio second (level)
    score = 0.4 * P + 0.3 * min(sigma_ratio, 0.30) + 0.15 * (1.0 / max(beta_dev + 0.1, 0.1)) * 0.1 + 0.1 * (spread / 5.0) + 0.05 * bin_S
    return score


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-base", default="experiments/v5_screen/B1")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    base = Path(args.exp_base)
    results = {}  # name -> {ckpt -> metrics}
    for name in CANDIDATES:
        run_dir = base / name
        if not run_dir.exists():
            print(f"[SKIP] {name}: no run dir")
            continue
        results[name] = evaluate_run(run_dir)
        if not results[name]:
            print(f"[INCOMPLETE] {name}: no test_preds.npz yet")

    # Console table — best ckpt per backbone
    headers = ["backbone", "ckpt", "n", "P", "S", "β", "σŷ/σy", "bin_S", "topE[y]bps", "spread_bps", "score", "G_pass"]
    print()
    print(" | ".join(f"{h:>12}" for h in headers))
    print("-" * 12 * len(headers))

    rows = []
    for name in CANDIDATES:
        if name not in results or not results[name]:
            print(f" {name:>11} | (no data)")
            continue
        # Pick best ckpt by score
        best_ckpt = max(results[name].keys(), key=lambda k: winner_score(results[name][k]))
        m = results[name][best_ckpt]
        gates = check_v5_gates(m)
        n_g = sum(gates[k] for k in gates if k.startswith("G"))
        score = winner_score(m)
        rows.append({
            "name": name,
            "ckpt": best_ckpt,
            "n": m.get("n", 0),
            "P": m.get("P", float("nan")),
            "S": m.get("S", float("nan")),
            "beta": m.get("beta", float("nan")),
            "sigma_ratio": m.get("sigma_ratio", float("nan")),
            "bin_S": m.get("bin_S", float("nan")),
            "top_E_y": m.get("top_decile_y_bps", float("nan")),
            "spread": m.get("top_minus_bottom_bps", float("nan")),
            "score": score,
            "gates_passed": f"{n_g}/6",
        })
        print(f" {name:>12} | {best_ckpt:>4} | {m.get('n', 0):>5} | "
              f"{m.get('P', float('nan')):>+.4f} | {m.get('S', float('nan')):>+.4f} | "
              f"{m.get('beta', float('nan')):>+.3f} | {m.get('sigma_ratio', float('nan')):>.3f} | "
              f"{m.get('bin_S', float('nan')):>+.3f} | {m.get('top_decile_y_bps', float('nan')):>+.3f} | "
              f"{m.get('top_minus_bottom_bps', float('nan')):>+.3f} | {score:>+.4f} | {n_g}/6")

    # Winner
    if rows:
        rows_sorted = sorted(rows, key=lambda r: r["score"], reverse=True)
        winner = rows_sorted[0]
        print(f"\n=== Winner: {winner['name']} (ckpt={winner['ckpt']}, score={winner['score']:+.4f}, gates={winner['gates_passed']}) ===")
    else:
        print("\nNo complete runs yet")
        winner = None

    # Markdown report
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        lines = ["# V5 B.1 backbone screen comparison\n"]
        lines.append("## Summary\n")
        lines.append("| backbone | ckpt | N | P | S | β | σŷ/σy | bin_S | top E[y] (bps) | spread (bps) | score | gates |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            lines.append(f"| {r['name']} | {r['ckpt']} | {r['n']:,} | "
                         f"{r['P']:+.4f} | {r['S']:+.4f} | {r['beta']:+.3f} | "
                         f"{r['sigma_ratio']:.3f} | {r['bin_S']:+.3f} | "
                         f"{r['top_E_y']:+.3f} | {r['spread']:+.3f} | "
                         f"{r['score']:+.4f} | {r['gates_passed']} |")
        if winner:
            lines.append(f"\n## Winner: **{winner['name']}** (ckpt={winner['ckpt']})\n")
            lines.append(f"Score: {winner['score']:+.4f}, Gates: {winner['gates_passed']}\n")
        # Per-ckpt breakdown
        lines.append("\n## Per-ckpt breakdown (BEST/EMA/SWA per backbone)\n")
        lines.append("| backbone | ckpt | P | S | β | σŷ/σy | top_E[y] |")
        lines.append("|---|---|---|---|---|---|---|")
        for name in CANDIDATES:
            if name not in results:
                continue
            for ckpt, m in results[name].items():
                if not m or m.get("n", 0) < 30:
                    continue
                lines.append(f"| {name} | {ckpt} | "
                             f"{m.get('P', float('nan')):+.4f} | "
                             f"{m.get('S', float('nan')):+.4f} | "
                             f"{m.get('beta', float('nan')):+.3f} | "
                             f"{m.get('sigma_ratio', float('nan')):.3f} | "
                             f"{m.get('top_decile_y_bps', float('nan')):+.3f} |")
        Path(args.out).write_text("\n".join(lines))
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
