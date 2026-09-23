"""NC deploy seed pack (pod2 -> Mac): everything the deployed producer state must inherit from the training replay, for the rows / anchors /
events up to the end of the research axis (2026-09-19T00:00Z). FREEZE amendment 1 §2.3, DESIGN §A2 / §A7.
  cache rows    the last 11,521 rows of cache_crypto.npy (crypto columns; holes NaN in 7 channels; ch0 NaN where R is NaN), f16
  boundary      the sparse table cells inside those rows (bound raw + the researcher's gap fills)
  members       the member history (pass 1) of every anchor inside those rows
  funding       per crypto name: the last 400 events <= the axis end (ft, rate, iv under nc_contract) and the EMA state after them
usage: python nc_export_seed.py <out npz>   (env NC_W)"""
import os, sys, json, hashlib
import numpy as np

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23"); WK = f"{W}/work"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    out = sys.argv[1]
    ax = np.load(f"{WK}/axes.npz", allow_pickle=True); ts = ax["ts"].astype(np.int64); cols = ax["crypto_cols"].astype(np.int64); syms = [str(s) for s in ax["symbols"]]
    C = np.load(f"{WK}/cache_crypto.npy", mmap_mode="r"); T = len(ts); r0 = T - 11521
    rows = np.ascontiguousarray(C[r0:]); rts = ts[r0:]
    b = np.load(f"{WK}/boundary.npz"); k = b["ts"] >= rts[0]
    mh = np.load(f"{WK}/members_hist_all.npz"); a = mh["anchors"]; sel = np.flatnonzero(a >= rts[0])
    m_anch = a[sel]; m_idx = [mh["idx"][mh["off"][i]:mh["off"][i + 1]] for i in sel]
    f = np.load(f"{WK}/fund_state.npz"); off = f["ev_off"]; end = int(ts[-1])
    fe = {"sym": [], "n": [], "ft": [], "rate": [], "iv": [], "acc": [], "prev": []}
    for ci, j in enumerate(cols):
        b0, b1 = int(off[ci]), int(off[ci + 1]); t = f["ft"][b0:b1]; kk = int(np.searchsorted(t, end, side="right"))
        lo = max(0, kk - 400); fe["sym"].append(j); fe["n"].append(kk - lo)
        for key in ("ft", "rate", "iv"): fe[key].append(f[key][b0 + lo:b0 + kk])
        fe["acc"].append(f["ema"][b0 + kk - 1] if kk else np.nan); fe["prev"].append(f["prev"][b0 + kk - 1] if kk else -1)
    np.savez(out, rts=rts, rows=rows, crypto_cols=cols, symbols=np.array(syms), axis_end=np.int64(end),
             bnd_ts=b["ts"][k], bnd_col=b["col"][k], bnd_raw=b["raw"][k],
             m_anchors=m_anch, m_off=np.concatenate([[0], np.cumsum([len(x) for x in m_idx])]).astype(np.int64),
             m_idx=(np.concatenate(m_idx) if m_idx else np.zeros(0)).astype(np.int16),
             f_sym=np.array(fe["sym"], np.int64), f_n=np.array(fe["n"], np.int64), f_ft=np.concatenate(fe["ft"]), f_rate=np.concatenate(fe["rate"]),
             f_iv=np.concatenate(fe["iv"]), f_acc=np.array(fe["acc"], np.float64), f_prev=np.array(fe["prev"], np.int64))
    rec = {"output": out, "sha256": sha(out), "rows": [int(rts[0]), int(rts[-1]), int(len(rts))], "boundary_cells": int(k.sum()),
           "member_anchors": int(len(m_anch)), "funding_names": int(len(cols)),
           "inputs": {p: sha(f"{WK}/{p}") for p in ("cache_crypto.npy", "boundary.npz", "members_hist_all.npz", "fund_state.npz", "axes.npz")},
           "device_sha256": sha(os.path.abspath(__file__))}
    json.dump(rec, open(f"{W}/receipts/NC_SEED_PACK.json", "w"), indent=1)
    print("NC_SEED_PACK", json.dumps({k_: v for k_, v in rec.items() if k_ != "inputs"}), flush=True)


if __name__ == "__main__":
    main()
