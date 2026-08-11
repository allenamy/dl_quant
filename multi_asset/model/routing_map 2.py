"""PRE-COMMITTED 10-month routing map (frozen tt-sign rule, 2026-07-04 spec).

Applies the FROZEN causal rule (15d-prior trailing tt_level sign) to every month's
test days BEFORE the trajectory preds exist = provable no-peek lock + coverage check.
Uses ONLY the state overlay (tt_level idx 11) + the fold windows — no model needed.
Reports per-month routing (Run1 net-long / Run2 net-short) + OOS routing diversity.
"""
from __future__ import annotations
import json, glob, os
import numpy as np
from multi_asset.train.train_dual_lob import _build_folds
from multi_asset.model.router_backtest import daily_ttlevel, DAY, LB, TT_THRESH

MONTHS = ["2025_08", "2025_09", "2025_10", "2025_11", "2025_12",
          "2026_01", "2026_02", "2026_03", "2026_04", "2026_05"]
BUILT = {"2025_10", "2026_01", "2026_04"}   # have preds (in-sample); the other 7 = OOS


def _utcday(datestr):
    return int((np.datetime64(datestr, "D") - np.datetime64("1970-01-01", "D"))
               / np.timedelta64(1, "D"))


def main():
    tt_all = daily_ttlevel(None)                       # {utc_day -> (datestr, tt_level)}
    days = sorted(tt_all.keys())
    di = {d: i for i, d in enumerate(days)}
    tt = np.array([tt_all[d][1] for d in days])
    npz_days = sorted(os.path.basename(f)[:-4] for f in glob.glob("data/npz_v2arch/*.npz")
                      if os.path.basename(f)[0].isdigit())

    print("==== PRE-COMMITTED 10-MONTH ROUTING MAP (frozen tt-sign, 15d-prior causal) ====")
    print(f"   FROZEN: lookback={LB}d, threshold={TT_THRESH} (tt<0 -> Run2-state / tt>=0 -> Run1-bugfix)")
    r1 = r2 = 0; oos = {"Run1": 0, "Run2": 0}
    for m in MONTHS:
        cfg = json.load(open(f"configs/d1gate/d1_{m}_run2.json"))
        fold = _build_folds(npz_days, cfg["training"], int(cfg["training"].get("embargo_days", 0)))[0]
        tt15, picks = [], {"Run1": 0, "Run2": 0}
        for ds in fold["test"]:
            ud = _utcday(ds)
            if ud not in di:
                continue
            i = di[ud]; w = tt[max(0, i - LB):i]        # strictly prior, causal
            if len(w) == 0:
                continue
            v = float(np.mean(w)); tt15.append(v)
            picks["Run1" if v >= TT_THRESH else "Run2"] += 1
        mean_tt = float(np.mean(tt15)) if tt15 else float("nan")
        month_pick = "Run1" if picks["Run1"] >= picks["Run2"] else "Run2"
        tag = "in-sample" if m in BUILT else "OOS"
        if month_pick == "Run1": r1 += 1
        else: r2 += 1
        if m not in BUILT:
            oos[month_pick] += 1
        print(f"   {m}  tt15={mean_tt:+.3f}  -> {month_pick:4s}  "
              f"({picks['Run1']}d R1 / {picks['Run2']}d R2)   [{tag}]")
    print(f"\n   TOTAL routing: {r1} months Run1 / {r2} months Run2 (of 10)")
    print(f"   OOS diversity (7 unseen): {oos['Run1']} Run1 / {oos['Run2']} Run2  "
          f"-> {'GOOD (both models exercised OOS)' if min(oos.values())>=1 else 'THIN (single-model OOS, weak test)'}")
    print("DONE_ROUTING_MAP.")


if __name__ == "__main__":
    main()
