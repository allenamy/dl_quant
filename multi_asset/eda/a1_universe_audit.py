"""A1 — Universe & data-quality audit.

For each of the 14 symbols, scan across history (sampled ~1 day/week) and compute:
  (a) listing/activation date = first sampled day where median(tdQtyBuy+tdQtySell)>0
      AND median(bidsz+asksz)>0. We ALSO report a more lenient activation based on
      a daily trade-fraction (frac of seconds with a trade > 0.05) since several thin
      assets trade <50% of seconds and would fail the strict median>0 test.
  (b) zero-volume fraction (frac of bars with tdQtyBuy+tdQtySell == 0), averaged over active days.
  (c) frozen-mid: max run-length of consecutive diff(mid)==0; flag days with run>300s.
  (d) constant-period days (mid.std()==0 over the day).

Output: per-symbol JSON + markdown table + recommended point-in-time valid start date.

Read-only. Sampling stated in output.
"""
from __future__ import annotations

import json
import os.path as p

import numpy as np

from _eda_common import (SYMBOLS, list_all_days, sample_days, col, day_exists,
                         ensure_export_dir)


def max_zero_run(d: np.ndarray) -> int:
    """Max run length of consecutive True in boolean array d."""
    if d.size == 0:
        return 0
    best = cur = 0
    for v in d:
        if v:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def audit():
    all_days = list_all_days()
    # ~1 day / week => step 7
    days = sample_days(all_days, step=7)
    days = [d for d in days if day_exists(d)]
    print(f"# A1 — Universe & data-quality audit")
    print(f"Sampling: every 7th calendar day (~1/week), {len(days)} days "
          f"from {days[0]} to {days[-1]} (full history {all_days[0]}..{all_days[-1]}).\n")

    # accumulators
    acc = {s: {
        "active_days_strict": [],     # day ints where median(td)>0 AND median(bsz+asz)>0
        "active_days_lenient": [],    # day ints where trade_frac>0.05 AND book present
        "zero_vol_frac": [],          # per active(lenient) day frac bars td==0
        "frozen_run_max": [],         # per active day max frozen-mid run (s)
        "frozen_gt300_days": [],      # day ints with frozen run > 300
        "constant_days": [],          # day ints with mid.std()==0 (and book present)
        "trade_frac": [],             # per active day frac seconds with a trade
    } for s in SYMBOLS}

    for di, d in enumerate(days):
        try:
            from multi_asset.data.bar_loader import load_day_panel
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] day {d} load failed: {e}")
            continue
        for s in SYMBOLS:
            mid = col(dp, s, "mid")
            tb = col(dp, s, "tdQtyBuy")
            tsell = col(dp, s, "tdQtySell")
            bsz = col(dp, s, "bidsz")
            asz = col(dp, s, "asksz")
            td = tb + tsell
            book = bsz + asz

            valid = np.isfinite(mid)
            nvalid = int(valid.sum())
            if nvalid < 100:
                continue  # essentially empty day for this symbol

            med_td = np.nanmedian(td)
            med_book = np.nanmedian(book)
            td_pos = np.isfinite(td) & (td > 0)
            trade_frac = float(td_pos.sum()) / max(nvalid, 1)
            book_present = np.isfinite(book) & (book > 0)
            book_frac = float(book_present.sum()) / max(nvalid, 1)

            strict_active = (med_td > 0) and (med_book > 0)
            lenient_active = (trade_frac > 0.05) and (book_frac > 0.5)

            if strict_active:
                acc[s]["active_days_strict"].append(d)
            if lenient_active:
                acc[s]["active_days_lenient"].append(d)
                acc[s]["trade_frac"].append(trade_frac)
                # zero-vol frac over valid bars
                zv = float((np.isfinite(td) & (td == 0)).sum()) / max(nvalid, 1)
                acc[s]["zero_vol_frac"].append(zv)
                # frozen mid run (on finite mid)
                mv = mid[valid]
                if mv.size > 1:
                    frozen = np.diff(mv) == 0
                    run = max_zero_run(frozen)
                else:
                    run = 0
                acc[s]["frozen_run_max"].append(run)
                if run > 300:
                    acc[s]["frozen_gt300_days"].append(d)
                # constant period (whole-day mid flat)
                if mv.size > 1 and np.std(mv) == 0.0:
                    acc[s]["constant_days"].append(d)

    # build per-symbol summary
    out = {}
    for s in SYMBOLS:
        a = acc[s]
        strict = sorted(a["active_days_strict"])
        lenient = sorted(a["active_days_lenient"])
        # recommended valid start = first lenient-active day (point-in-time); we add a
        # small buffer: require the symbol to be active from that day onward consistently.
        # Use first lenient day where the NEXT 3 sampled active days are also active.
        rec_start = None
        if lenient:
            lset = set(lenient)
            # first day such that >=3 of the following 4 sampled days are also lenient-active
            day_idx = {d: i for i, d in enumerate(days)}
            for d in lenient:
                i = day_idx[d]
                fwd = days[i + 1: i + 5]
                hits = sum(1 for f in fwd if f in lset)
                if len(fwd) < 4 or hits >= 3:
                    rec_start = d
                    break
            if rec_start is None:
                rec_start = lenient[0]
        out[s] = {
            "activation_strict": strict[0] if strict else None,
            "activation_lenient": lenient[0] if lenient else None,
            "recommended_valid_start": rec_start,
            "n_active_days_lenient": len(lenient),
            "n_sampled_days": len(days),
            "active_coverage_frac": round(len(lenient) / len(days), 4),
            "mean_trade_frac": round(float(np.mean(a["trade_frac"])), 4) if a["trade_frac"] else None,
            "mean_zero_vol_frac": round(float(np.mean(a["zero_vol_frac"])), 4) if a["zero_vol_frac"] else None,
            "median_frozen_run_s": int(np.median(a["frozen_run_max"])) if a["frozen_run_max"] else None,
            "max_frozen_run_s": int(np.max(a["frozen_run_max"])) if a["frozen_run_max"] else None,
            "n_days_frozen_gt300": len(a["frozen_gt300_days"]),
            "n_constant_days": len(a["constant_days"]),
            "junk_flag": None,  # filled below
        }
        # junk heuristic: low coverage OR very high zero-vol OR many frozen days
        junk = []
        if out[s]["active_coverage_frac"] < 0.5:
            junk.append("low_coverage")
        if (out[s]["mean_zero_vol_frac"] or 0) > 0.95:
            junk.append("mostly_zero_vol")
        if out[s]["n_days_frozen_gt300"] > 0.2 * max(len(lenient), 1):
            junk.append("frequent_frozen")
        out[s]["junk_flag"] = ",".join(junk) if junk else "ok"

    result = {
        "analysis": "A1_universe_audit",
        "sampling": f"every 7th day, {len(days)} days, {days[0]}..{days[-1]}",
        "activation_strict_def": "median(tdQtyBuy+tdQtySell)>0 AND median(bidsz+asksz)>0",
        "activation_lenient_def": "trade_frac(td>0)>0.05 AND book_present_frac>0.5",
        "per_symbol": out,
    }

    ed = ensure_export_dir()
    with open(p.join(ed, "a1_universe_audit.json"), "w") as f:
        json.dump(result, f, indent=2)

    # markdown table
    print("| sym | act_strict | act_lenient | rec_start | cov | trade_frac | zero_vol | "
          "med_frozen_s | max_frozen_s | days_frozen>300 | const_days | flag |")
    print("|-----|-----------|-------------|-----------|-----|-----------|----------|"
          "-------------|--------------|-----------------|-----------|------|")
    for s in SYMBOLS:
        o = out[s]
        print(f"| {s} | {o['activation_strict']} | {o['activation_lenient']} | "
              f"{o['recommended_valid_start']} | {o['active_coverage_frac']} | "
              f"{o['mean_trade_frac']} | {o['mean_zero_vol_frac']} | "
              f"{o['median_frozen_run_s']} | {o['max_frozen_run_s']} | "
              f"{o['n_days_frozen_gt300']} | {o['n_constant_days']} | {o['junk_flag']} |")
    print(f"\nWrote {p.join(ed, 'a1_universe_audit.json')}")


if __name__ == "__main__":
    audit()
