#!/workspace/venv/bin/python
"""
markout_stats.py -- coverage.md for the CDN markout backfill.

Reads out/marks.json + input/pending_fills.json (+ out/archives.json, out/run_meta.json,
out/validation_20rows.txt) and writes out/coverage.md:
  * counts by ledger day x status, totals by status, archive-level status
  * mark_lag_s distribution (p50 / p90 / max), overall, by order_type, by day
  * parser validation excerpt (20 random rows, independent csv implementation)
  * PRELIMINARY markout read: sign convention buy => (mark-fill)/fill, sell => (fill-mark)/fill, in bps
    (positive = price moved in our favour after the fill; negative = adverse selection).
    Weights: EQUAL per fill.  The export carries no quantity/notional column, so notional
    weighting is impossible from this input (join to the ledger on trade_id to re-weight).
    CI: day-block bootstrap of the mean, 2000 resamples, numpy default_rng(20260905).
"""
import collections
import datetime as dt
import json
import os

import numpy as np
import pandas as pd

ROOT = "/workspace/review_scratch/markout_cdn"
SEED, NBOOT = 20260905, 2000


def block_boot_ci(df, col, nboot=NBOOT, seed=SEED):
    """Day-block bootstrap of the equal-weighted mean of df[col]; blocks = ledger day."""
    days = sorted(df["day"].unique())
    groups = {d: df.loc[df["day"] == d, col].to_numpy() for d in days}
    sums = np.array([groups[d].sum() for d in days])
    cnts = np.array([len(groups[d]) for d in days])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(nboot, len(days)))
    means = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), len(days)


def fmt(x, nd=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def sfmt(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.2f}"


def main():
    marks = json.load(open(f"{ROOT}/out/marks.json"))
    rows = json.load(open(f"{ROOT}/input/pending_fills.json"))["rows"]
    arch = json.load(open(f"{ROOT}/out/archives.json"))
    meta = json.load(open(f"{ROOT}/out/run_meta.json"))
    recs = []
    for r in rows:
        m = marks[str(r["trade_id"])]
        recs.append(dict(trade_id=str(r["trade_id"]), day=r["day"], symbol=r["symbol"], side=r["side"],
                         order_type=r["order_type"], fill_px=r["fill_px"], status=m["status"], mark_px=m["mark_px"],
                         mark_lag_s=m["mark_lag_s"], mark_px_5s=m["mark_px_5s"], mark_lag_5s=m["mark_lag_5s"]))
    df = pd.DataFrame(recs)
    sgn = np.where(df["side"] == "buy", 1.0, -1.0)
    df["mo_bps"] = sgn * (df["mark_px"] - df["fill_px"]) / df["fill_px"] * 1e4
    df["mo5_bps"] = sgn * (df["mark_px_5s"] - df["fill_px"]) / df["fill_px"] * 1e4
    ok = df[df["status"] == "ok"].copy()
    ok5 = ok[ok["mark_px_5s"].notna()].copy()

    L = []
    L.append("# CDN markout backfill -- coverage and preliminary markout read")
    L.append(f"> **创建:** 2026-09-05 | **Session:** review_caliber / markout_cdn (pod2, CPU only) | **状态:** data receipt, "
             f"preliminary read | **作废条件:** archives for 2026-09-05 published (rerun `--resume`), or the executor's own "
             f"API-path backfill supersedes these marks\n")
    L.append("## Device")
    L.append(f"- script `scripts/markout_cdn.py` self_sha256 `{meta['config']['self_sha256']}`; input `pending_fills.json` "
             f"sha256 `{meta['config']['input_sha256']}` ({meta['n_rows']} rows, 407 symbols, ledger days 2026-08-01 .. 2026-09-05)")
    L.append(f"- rule: target = fill_ts + {meta['config']['mark_delay_ms']/1000:.0f} s; mark = FIRST aggTrade with T >= target and "
             f"T <= target + {meta['config']['window_ms']/1000:.0f} s; strict variant recorded when lag <= {meta['config']['strict_ms']/1000:.0f} s; "
             f"none -> `no_trade_within_60s`; 404 -> `archive_missing`")
    L.append(f"- source: data.binance.vision daily aggTrades (futures/um), file chosen by the UTC day of target (0 rows cross midnight); "
             f"{meta['archives_fetched']} archives requested, {meta['bytes_fetched']/1e9:.2f} GB fetched in memory, elapsed {meta['elapsed_s']/60:.1f} min; "
             f"unsorted archives: {meta['n_unsorted_archives']}; header-less archives: {meta['n_headerless_archives']}")
    L.append(f"- archive status: {json.dumps(meta['archive_status_counts'])}; generated {meta['generated_utc']}\n")

    L.append("## Row status by ledger day")
    piv = df.pivot_table(index="day", columns="status", values="trade_id", aggfunc="count", fill_value=0)
    for c in ("ok", "no_trade_within_60s", "archive_missing", "download_error", "parse_error"):
        if c not in piv.columns:
            piv[c] = 0
    piv = piv[["ok", "no_trade_within_60s", "archive_missing", "download_error", "parse_error"]]
    piv["total"] = piv.sum(axis=1)
    lag = ok.groupby("day")["mark_lag_s"].agg(p50=lambda s: s.quantile(0.5), p90=lambda s: s.quantile(0.9), max="max")
    n5 = ok.groupby("day")["mark_px_5s"].count()
    L.append("| day | ok | no_trade_60s | archive_missing | dl_err | parse_err | total | ok% | lag p50 s | lag p90 s | lag max s | strict(<=5s) n |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for d, r in piv.iterrows():
        lg = lag.loc[d] if d in lag.index else None
        L.append(f"| {d} | {r['ok']} | {r['no_trade_within_60s']} | {r['archive_missing']} | {r['download_error']} | {r['parse_error']} | "
                 f"{r['total']} | {100*r['ok']/r['total']:.1f} | {fmt(lg['p50'] if lg is not None else None, 3)} | "
                 f"{fmt(lg['p90'] if lg is not None else None, 3)} | {fmt(lg['max'] if lg is not None else None, 3)} | {int(n5.get(d, 0))} |")
    tot = piv.sum()
    L.append(f"| **total** | {tot['ok']} | {tot['no_trade_within_60s']} | {tot['archive_missing']} | {tot['download_error']} | "
             f"{tot['parse_error']} | {tot['total']} | {100*tot['ok']/tot['total']:.1f} | {fmt(ok['mark_lag_s'].quantile(0.5), 3)} | "
             f"{fmt(ok['mark_lag_s'].quantile(0.9), 3)} | {fmt(ok['mark_lag_s'].max(), 3)} | {int(ok['mark_px_5s'].count())} |\n")
    L.append("Status totals: " + ", ".join(f"{k}={v}" for k, v in collections.Counter(df["status"]).most_common()))
    L.append("Status by order_type: " + "; ".join(
        f"{ot}: " + ", ".join(f"{k}={v}" for k, v in collections.Counter(df.loc[df['order_type'] == ot, 'status']).most_common())
        for ot in sorted(df["order_type"].unique())) + "\n")

    L.append("## mark_lag_s distribution (ok rows)")
    L.append("| slice | n | p50 | p90 | p99 | max | share lag<=5s | share lag<=1s |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, sub in [("all", ok)] + [(f"order_type={ot}", ok[ok["order_type"] == ot]) for ot in sorted(ok["order_type"].unique())]:
        s = sub["mark_lag_s"]
        L.append(f"| {name} | {len(s)} | {s.quantile(0.5):.3f} | {s.quantile(0.9):.3f} | {s.quantile(0.99):.3f} | {s.max():.3f} | "
                 f"{(s <= 5).mean():.3f} | {(s <= 1).mean():.3f} |")
    L.append("")
    L.append("`no_trade_within_60s` rows by symbol (top 15): " + ", ".join(
        f"{k}={v}" for k, v in collections.Counter(df.loc[df['status'] == 'no_trade_within_60s', 'symbol']).most_common(15)) + "\n")

    L.append("## Cross-check")
    L.append("The venue API cannot be called from here and the pending set contains no executor-marked fills by construction, "
             "so the check is on the parser: 20 random ok rows (seed 20260905) re-derived by an independent pure-`csv` streaming "
             "implementation (no pandas/numpy) that re-downloads the archive, re-verifies its sha256, and prints the 2 trades before "
             "the mark, the mark, and the 2 after.  Full printout: `out/validation_20rows.txt`.")
    vs_path = f"{ROOT}/out/validation_summary.json"
    if os.path.exists(vs_path):
        vs = json.load(open(vs_path))
        L.append(f"- result: **{vs['n_agree']}/{vs['n_checked']} agree** on (mark_ts, mark_px, archive sha256); mismatches: {vs['mismatches']}\n")
    else:
        L.append("- validation_summary.json not found (validation not yet run)")
    nt_path = f"{ROOT}/out/validation_no_trade_10rows.txt"
    if os.path.exists(nt_path):
        last = [l for l in open(nt_path).read().splitlines() if l.startswith("SUMMARY")]
        L.append("- `no_trade_within_60s` rows: 10 random ones (seed 20260905) re-scanned by the same pure-`csv` path, printing the last "
                 "trade before target and the first trade after the window (`out/validation_no_trade_10rows.txt`): "
                 + (last[0].replace("SUMMARY: ", "**") + "**" if last else "no summary line"))
    L.append("")

    L.append("## PRELIMINARY markout read (information only)")
    L.append("Sign: buy => (mark_px - fill_px)/fill_px, sell => (fill_px - mark_px)/fill_px, in bps; **positive = price moved in our "
             "favour after the fill, negative = adverse selection**.  Weights: **equal per fill** -- the export has no quantity column, "
             "so the notional-weighted number the brief asked for cannot be formed from this input (re-weight after joining the ledger "
             "on trade_id).  Uncertainty: day-block bootstrap of the mean only (blocks = ledger day, 2000 resamples, "
             "numpy default_rng(20260905)); no other CI, no cost netting, no fee/rebate, not a book-level number.")
    L.append("")
    L.append("| slice | n marks | mean bps | median bps | day-block 95% CI | days | mean 5s-variant bps (n) |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    slices = [("all", ok, ok5)]
    for ot in sorted(ok["order_type"].unique()):
        slices.append((f"order_type={ot}", ok[ok["order_type"] == ot], ok5[ok5["order_type"] == ot]))
    for ot in sorted(ok["order_type"].unique()):
        for sd in ("buy", "sell"):
            sub = ok[(ok["order_type"] == ot) & (ok["side"] == sd)]
            slices.append((f"{ot} / {sd}", sub, ok5[(ok5["order_type"] == ot) & (ok5["side"] == sd)]))
    head = {}
    for name, sub, sub5 in slices:
        lo, hi, nd = block_boot_ci(sub, "mo_bps")
        m5 = sub5["mo5_bps"].mean() if len(sub5) else float("nan")
        L.append(f"| {name} | {len(sub)} | {sub['mo_bps'].mean():+.2f} | {sub['mo_bps'].median():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {nd} | "
                 f"{m5:+.2f} ({len(sub5)}) |")
        head[name] = dict(n=int(len(sub)), mean_bps=float(sub["mo_bps"].mean()), median_bps=float(sub["mo_bps"].median()),
                          ci95=[lo, hi], days=nd, mean5_bps=(None if np.isnan(m5) else float(m5)), n5=int(len(sub5)))
    L.append("")
    L.append("### by ledger day (equal-weighted, no CI)")
    L.append("| day | n all | mean bps all | n maker | mean bps maker | n topup_taker | mean bps topup_taker | share of marks with markout<0 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for d, sub in ok.groupby("day"):
        mk = sub[sub["order_type"] == "maker"]
        tk = sub[sub["order_type"] == "topup_taker"]
        L.append(f"| {d} | {len(sub)} | {sub['mo_bps'].mean():+.2f} | {len(mk)} | {sfmt(mk['mo_bps'].mean() if len(mk) else None)} | "
                 f"{len(tk)} | {sfmt(tk['mo_bps'].mean() if len(tk) else None)} | {(sub['mo_bps'] < 0).mean():.3f} |")
    L.append("")
    L.append("### robustness of the equal-weighted mean (same marks, information only)")
    for name, sub in [("all", ok), ("maker", ok[ok["order_type"] == "maker"]), ("topup_taker", ok[ok["order_type"] == "topup_taker"])]:
        x = sub["mo_bps"]
        w = x.clip(x.quantile(0.01), x.quantile(0.99))
        dm = sub.groupby("day")["mo_bps"].mean()
        L.append(f"- {name}: mean {x.mean():+.2f} | winsorised 1/99 {w.mean():+.2f} | mean of daily means {dm.mean():+.2f} "
                 f"(sd across days {dm.std():.2f}, n days {len(dm)}) | std per fill {x.std():.1f} | share<0 {(x < 0).mean():.3f}")
    L.append("")
    L.append("## Files")
    L.append("- `out/marks.json` (trade_id -> record, every pending row), `out/archives.json` (per-archive status/sha256/rows), "
             "`out/run_meta.json` (device config + counts), `out/validation_20rows.txt`, `logs/run.log`, `logs/commands.txt`, "
             "`logs/SHA256SUMS.txt`")
    L.append("- rerun for the missing 2026-09-05 archives once published: "
             "`/workspace/venv/bin/python scripts/markout_cdn.py --resume` (keeps ok/no_trade rows, refetches the rest)")
    with open(f"{ROOT}/out/coverage.md", "w") as f:
        f.write("\n".join(L) + "\n")
    with open(f"{ROOT}/out/headline.json", "w") as f:
        json.dump(dict(seed=SEED, nboot=NBOOT, weights="equal per fill (no quantity in export)", slices=head), f, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
