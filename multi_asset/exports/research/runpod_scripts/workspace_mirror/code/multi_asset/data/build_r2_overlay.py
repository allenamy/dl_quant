"""R2 DL overlay (tv_feats) = perp_book KEY-diff SEQUENCE (16, per-timestep) +
long-context block (13, per-window broadcast). Concatenated to the R2 base cache
(npz_spot2perp_clean: spot book + spot trades + perp y) by the dataset's
tv_overlay_dir mechanism -> X becomes (N,600,64+29=93). Faithful DL form of the
Ridge R2 winner (base + perp_book_block + long_block, ADDITIVE — no regime gating).

KEY perp-book cols (orthogonal book-venue info), per-timestep diff perp - spot:
  obi_{L1,L5,L10,L25}, {bid,ask}_depth_{L5,L25}, spread_bps, microprice_dev_bps,
  book_pressure_imbalance, {bid,ask}_slope_L10, weighted_price_{bid,ask}_L10,
  depth_ratio_L5  (16 cols)
LONG block (13, per-window, broadcast across the 600 timesteps): from mid_cache,
  trailing {600,1800,3600}s [spot_ret, perp_ret, spot_rvol, perp_rvol] + basis_bps.

All <= t: per-timestep book diff is contemporaneous (<=t each step); long is the
window's pred-second trailing summary broadcast (the window's own <=t context).

Output: data/r2_overlay/<day>.npz  key 'tv_feats' (N,600,29) f32.

Usage: python multi_asset/data/build_r2_overlay.py --range 2024-04-01 2026-05-31 --procs 6
"""
from __future__ import annotations
import argparse, datetime as dt, os, os.path as p, sys, time
import numpy as np
_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, _REPO)

SPOT = p.join(_REPO, "data", "npz_spot")          # spot 64-feat sequence (book+spot trades)
PERP = p.join(_REPO, "data", "npz_perp")          # perp 64-feat sequence
MID = p.join(_REPO, "data", "mid_cache")
OUT = p.join(_REPO, "data", "r2_overlay")
US = 1_000_000

KEY = ["obi_L1", "obi_L5", "obi_L10", "obi_L25", "bid_depth_L5", "ask_depth_L5",
       "bid_depth_L25", "ask_depth_L25", "spread_bps", "microprice_dev_bps",
       "book_pressure_imbalance", "bid_slope_L10", "ask_slope_L10",
       "weighted_price_bid_L10", "weighted_price_ask_L10", "depth_ratio_L5"]


def _long_window(day, pred_secs):
    """(N,13) per-window long-context summary at each pred second (<= t)."""
    fmid = p.join(MID, f"{day}.npz")
    if not p.exists(fmid):
        return None
    zm = np.load(fmid)
    sec = zm["sec"].astype(np.int64)
    sm = zm["spot_mid"].astype(np.float64); pm = zm["perp_mid"].astype(np.float64)
    lsm = np.log(np.clip(sm, 1e-9, None)); lpm = np.log(np.clip(pm, 1e-9, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    basis = np.clip((pm - sm) / np.where(sm > 0, sm, 1.0) * 1e4, -50, 50)
    cs_s = np.concatenate([[0.0], np.cumsum(sret)]); cs_p = np.concatenate([[0.0], np.cumsum(pret)])
    cs_s2 = np.concatenate([[0.0], np.cumsum(sret * sret)]); cs_p2 = np.concatenate([[0.0], np.cumsum(pret * pret)])
    pos = np.searchsorted(sec, pred_secs, side="right") - 1
    ok = pos >= 0
    feats = []
    for W in (600, 1800, 3600):
        lo = np.clip(pos - W, 0, None); pidx = np.clip(pos + 1, 0, sec.size)
        n = (pidx - 1 - lo).astype(np.float64); n[n < 1] = 1.0
        sw = cs_s[pidx] - cs_s[lo]; pw = cs_p[pidx] - cs_p[lo]
        srv = np.sqrt(np.clip((cs_s2[pidx] - cs_s2[lo]) / n - (sw / n) ** 2, 0, None))
        prv = np.sqrt(np.clip((cs_p2[pidx] - cs_p2[lo]) / n - (pw / n) ** 2, 0, None))
        feats += [np.clip(sw, -0.05, 0.05), np.clip(pw, -0.05, 0.05), srv, prv]
    feats.append(basis[np.clip(pos, 0, sec.size - 1)])
    M = np.column_stack(feats); M[~ok] = 0.0
    return np.nan_to_num(M, nan=0.0, posinf=0.0, neginf=0.0)


def build_day(day):
    fs = p.join(SPOT, f"{day}.npz"); fp = p.join(PERP, f"{day}.npz")
    if not (p.exists(fs) and p.exists(fp)):
        return ("skip-missing", day)
    zs = np.load(fs, allow_pickle=True); zp = np.load(fp, allow_pickle=True)
    ts = zs["timestamps"].astype(np.int64); tp = zp["timestamps"].astype(np.int64)
    if ts.shape != tp.shape or not np.array_equal(ts, tp):
        # base (npz_spot2perp_clean) uses spot ts; perp must align by position
        if ts.shape != tp.shape:
            return ("skip-misalign", day)
    names = [str(x) for x in zs["features"]]
    fi = {n: i for i, n in enumerate(names)}
    ki = [fi[k] for k in KEY]
    Xs = zs["X"][:, :, ki].astype(np.float32)        # (N,600,16) spot book KEY seq
    Xp = zp["X"][:, :, ki].astype(np.float32)        # (N,600,16) perp book KEY seq
    book_diff = (Xp - Xs)                             # (N,600,16) per-timestep book-venue diff
    pred_secs = ts // US
    lw = _long_window(day, pred_secs)                # (N,13)
    if lw is None:
        return ("skip-nomid", day)
    N, T, _ = book_diff.shape
    long_seq = np.broadcast_to(lw[:, None, :].astype(np.float32), (N, T, lw.shape[1]))
    tv = np.concatenate([book_diff, long_seq], axis=-1).astype(np.float32)  # (N,600,29)
    tv = np.nan_to_num(tv, nan=0.0, posinf=0.0, neginf=0.0)
    os.makedirs(OUT, exist_ok=True)
    tmp = p.join(OUT, f"{day}.npz.t{os.getpid()}.npz")
    np.savez_compressed(tmp, tv_feats=tv)
    os.replace(tmp, p.join(OUT, f"{day}.npz"))
    return ("ok", day, tv.shape[-1])


def _worker(d):
    out = p.join(OUT, f"{d}.npz")
    if p.exists(out):
        return ("skip-exist", d)
    try:
        return build_day(d)
    except Exception as e:
        return ("fail", d, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", nargs=2, required=True)
    ap.add_argument("--procs", type=int, default=6)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    d0 = dt.date.fromisoformat(args.range[0]); d1 = dt.date.fromisoformat(args.range[1])
    days = []
    while d0 <= d1:
        days.append(d0.isoformat()); d0 += dt.timedelta(days=1)
    print(f"[r2_overlay] {len(days)} days -> {OUT} (procs={args.procs})", flush=True)
    t0 = time.time(); ok = sk = nf = 0
    import multiprocessing as mp
    with mp.Pool(args.procs) as pool:
        for i, r in enumerate(pool.imap_unordered(_worker, days, chunksize=2)):
            if r[0] == "ok": ok += 1
            elif r[0].startswith("skip"): sk += 1
            else: nf += 1; print("  fail", r[1:], flush=True)
            if (i + 1) % 60 == 0:
                print(f"  [{i+1}/{len(days)}] ok={ok} skip={sk} fail={nf} ({(time.time()-t0)/60:.1f}min)", flush=True)
    print(f"[r2_overlay] DONE ok={ok} skip={sk} fail={nf} in {(time.time()-t0)/60:.1f}min", flush=True)
