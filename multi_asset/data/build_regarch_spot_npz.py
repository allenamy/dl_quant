"""SPOT-book twin of build_regarch_perp_npz.py — the clean reproduction of the
single-asset milestone's feature source.

WHY: the milestone REG_arch (P~0.0646) was trained on data/npz_v4, whose *book*
was binance SPOT (the "deprecated spot-book root"). The perp consolidation
(data/npz_perp, binance-futures book) gives only ~0.031 because perp-LOB features
are ~2x less predictive of the (same, corr 0.99) ~600s target — measured this
session (Ridge TRAIN: npz_v4 0.100 vs perp 0.055; DL: 0.065 vs 0.031). The Tardis
high-precision dir carries BOTH venues for all 1247 days, so this builder rebuilds
the SPOT-book feature set on CLEAN, full-period (2023-01..2026-05) data — the
faithful single-asset consolidation, extendable to 2026 OOS.

HOW: identical pipeline/windowing/schema to build_regarch_perp_npz (imported +
reused VERBATIM); the ONLY change is the venue the book/trades readers point at:
binance-futures -> binance. Monkeypatches the two reader names in the perp
builder's namespace, redirects OUT_DIR -> data/npz_spot, then reuses build_one_day
(atomic write + feature-schema assertion). Target y_* is the SPOT mid forward
return (build_npz_for_day computes it from the spot book mid) = spot->spot, the
clean twin of npz_v4.

USAGE:
  python multi_asset/data/build_regarch_spot_npz.py --days 2024-06-14 2024-03-15
  python multi_asset/data/build_regarch_spot_npz.py --all          # all 1247 days, skip existing
"""
import os
import os.path as p
import sys
import time
import argparse
from multiprocessing import Pool

_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, _REPO)

import pandas as pd  # noqa: E402
import multi_asset.data.build_regarch_perp_npz as B          # noqa: E402
from multi_asset.data.build_btc_feat64_perp import (          # noqa: E402
    _read_gz_csv_robust, _BOOK_COLS, PERP_BOOK_ROOT, PERP_TRADES_ROOT,
)

SPOT_VENUE = "binance"          # vs perp's "binance-futures"
# Output dir; override with SPOT_OUT_DIR (e.g. /dev/shm for contention-free
# parallel writes, then bulk-move to the storage cache).
OUT_DIR = os.environ.get("SPOT_OUT_DIR", p.join(_REPO, "data", "npz_spot"))


def spot_read_book(date_str: str) -> pd.DataFrame:
    path = p.join(PERP_BOOK_ROOT, date_str, SPOT_VENUE, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    return _read_gz_csv_robust(path, usecols=_BOOK_COLS)


def spot_read_trades(date_str: str) -> pd.DataFrame:
    # mirrors build_btc_feat64_perp.read_trades_day normalization, spot venue
    path = p.join(PERP_TRADES_ROOT, date_str, SPOT_VENUE, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    df = _read_gz_csv_robust(path)
    ren = {}
    if "amount" in df.columns and "size" not in df.columns:
        ren["amount"] = "size"
    if "id" in df.columns and "exec_id" not in df.columns:
        ren["id"] = "exec_id"
    if ren:
        df.rename(columns=ren, inplace=True)
    if "side" in df.columns:
        df["side"] = df["side"].astype(str).str.title()
    return df


# Redirect the perp builder's readers + output to SPOT (build_one_day/_resample
# call these by name in B's namespace).
B.read_book_day = spot_read_book
B.read_trades_day = spot_read_trades
B.OUT_DIR = OUT_DIR


def _one(date_str: str):
    out = p.join(OUT_DIR, f"{date_str}.npz")
    if p.exists(out):
        return ("skip", date_str)
    try:
        B.build_one_day(date_str, out)
        return ("ok", date_str)
    except Exception as e:
        return ("ERR", f"{date_str}: {type(e).__name__}: {e}")


def list_spot_days():
    root = p.join(PERP_BOOK_ROOT)
    days = []
    for name in sorted(os.listdir(root)):
        if len(name) == 10 and name[4] == "-" and p.isdir(p.join(root, name, SPOT_VENUE)):
            days.append(name)
    return days


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    days = args.days if args.days else (list_spot_days() if args.all else [])
    if args.nshards > 1:
        days = [d for i, d in enumerate(days) if i % args.nshards == args.shard]
    if not days:
        print("nothing to do (pass --days or --all)"); sys.exit(0)
    print(f"SPOT build: {len(days)} days -> {OUT_DIR}", flush=True)
    t0 = time.time(); ok = skip = err = 0; errs = []
    with Pool(args.workers) as pool:
        for i, (st, info) in enumerate(pool.imap_unordered(_one, days, chunksize=2)):
            if st == "ok": ok += 1
            elif st == "skip": skip += 1
            else: err += 1; errs.append(info)
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(days)} ok={ok} skip={skip} err={err} "
                      f"({(time.time()-t0)/(i+1):.1f}s/day)", flush=True)
    print(f"DONE ok={ok} skip={skip} err={err} in {(time.time()-t0)/60:.1f}min", flush=True)
    for e in errs[:15]:
        print(" ERR", e)
