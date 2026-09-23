"""NC deploy seed pack / parity pack (pod2 -> Mac): everything the deployed producer state must inherit from the training replay, for the
rows / anchors / events up to the end of the research axis (2026-09-19T00:00Z). FREEZE amendment 1 §2.3, DESIGN §A2 / §A7 / §A9-3.
  cache rows    the last --rows rows of cache_crypto.npy (crypto columns; holes NaN in 7 channels; ch0 NaN where R is NaN), f16
  boundary      the sparse table cells inside those rows (bound raw + the researcher's gap fills)
  members       the member history (pass 1) of every anchor inside those rows
  funding       per crypto name: the last 400 events <= the axis end (ft, rate, iv under nc_contract) and the EMA state after them
  --per-event   (parity pack) also the EMA state after EVERY exported event (f_acc_ev, f_prev_ev; NaN / -1 = reset), so the state at any
                anchor inside the pack is recoverable
  --ref F --ref-anchors A,A,..  (parity pack) the training build's rows at those anchors from NC_FEATURES.npz F, prefixed ref_
Arrays are read ONCE (an NpzFile re-reads and decompresses the whole member on every key access).
usage: python nc_export_seed.py <out npz> [--rows 11521] [--per-event] [--ref NC_FEATURES.npz --ref-anchors A,A,..] [--receipt NAME]  (env NC_W)"""
import os, sys, json, hashlib, argparse
import numpy as np

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23"); WK = f"{W}/work"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--rows", type=int, default=11521)
    ap.add_argument("--per-event", action="store_true"); ap.add_argument("--ref"); ap.add_argument("--ref-anchors"); ap.add_argument("--receipt", default="NC_SEED_PACK")
    a = ap.parse_args(); out = a.out
    ax = np.load(f"{WK}/axes.npz", allow_pickle=True); ts = ax["ts"].astype(np.int64); cols = ax["crypto_cols"].astype(np.int64); syms = [str(s) for s in ax["symbols"]]
    C = np.load(f"{WK}/cache_crypto.npy", mmap_mode="r"); T = len(ts); r0 = T - a.rows; assert r0 >= 0
    rows = np.ascontiguousarray(C[r0:]); rts = ts[r0:]
    with np.load(f"{WK}/boundary.npz") as b:
        b_ts, b_col, b_raw = b["ts"], b["col"], b["raw"]
    k = b_ts >= rts[0]
    with np.load(f"{WK}/members_hist_all.npz") as mh:
        mA, mO, mI = mh["anchors"], mh["off"], mh["idx"]
    sel = np.flatnonzero(mA >= rts[0]); m_anch = mA[sel]; m_idx = [mI[mO[i]:mO[i + 1]] for i in sel]
    with np.load(f"{WK}/fund_state.npz") as f:
        F = {key: f[key] for key in ("ev_off", "ft", "rate", "iv", "ema", "prev")}
    off = F["ev_off"]; end = int(ts[-1])
    fe = {"sym": [], "n": [], "ft": [], "rate": [], "iv": [], "acc": [], "prev": [], "acc_ev": [], "prev_ev": []}
    for ci, j in enumerate(cols):
        b0, b1 = int(off[ci]), int(off[ci + 1]); t = F["ft"][b0:b1]; kk = int(np.searchsorted(t, end, side="right"))
        lo = max(0, kk - 400); fe["sym"].append(j); fe["n"].append(kk - lo)
        for key in ("ft", "rate", "iv"): fe[key].append(F[key][b0 + lo:b0 + kk])
        fe["acc_ev"].append(F["ema"][b0 + lo:b0 + kk]); fe["prev_ev"].append(F["prev"][b0 + lo:b0 + kk])
        fe["acc"].append(F["ema"][b0 + kk - 1] if kk else np.nan); fe["prev"].append(F["prev"][b0 + kk - 1] if kk else -1)
    arrs = dict(rts=rts, rows=rows, crypto_cols=cols, symbols=np.array(syms), axis_end=np.int64(end),
                bnd_ts=b_ts[k], bnd_col=b_col[k], bnd_raw=b_raw[k],
                m_anchors=m_anch, m_off=np.concatenate([[0], np.cumsum([len(x) for x in m_idx])]).astype(np.int64),
                m_idx=(np.concatenate(m_idx) if m_idx else np.zeros(0)).astype(np.int16),
                f_sym=np.array(fe["sym"], np.int64), f_n=np.array(fe["n"], np.int64), f_ft=np.concatenate(fe["ft"]), f_rate=np.concatenate(fe["rate"]),
                f_iv=np.concatenate(fe["iv"]), f_acc=np.array(fe["acc"], np.float64), f_prev=np.array(fe["prev"], np.int64))
    if a.per_event:
        arrs["f_acc_ev"] = np.concatenate(fe["acc_ev"]).astype(np.float64); arrs["f_prev_ev"] = np.concatenate(fe["prev_ev"]).astype(np.int64)
        assert len(arrs["f_acc_ev"]) == len(arrs["f_ft"])
    ref = None
    if a.ref:
        want = [int(x) for x in a.ref_anchors.split(",")]
        with np.load(a.ref, allow_pickle=True) as R:
            Rz = {key: R[key] for key in R.files}
        A = Rz["anchors"].astype(np.int64); o = Rz["off"].astype(np.int64); pos = {int(x): i for i, x in enumerate(A)}
        assert all(w in pos for w in want), ("ref anchors not in NC_FEATURES", [w for w in want if w not in pos])
        assert [str(s) for s in Rz["symbols"]] == syms
        ii = [pos[w] for w in want]; roff = np.concatenate([[0], np.cumsum([o[i + 1] - o[i] for i in ii])]).astype(np.int64)
        arrs["ref_anchors"] = np.array(want, np.int64); arrs["ref_off"] = roff
        for key in ("m", "X78", "X82", "X89", "fe_v", "fn_v", "iv_v", "qvm", "rev24"):
            arrs[f"ref_{key}"] = np.concatenate([Rz[key][o[i]:o[i + 1]] for i in ii])
        arrs["ref_base_val"] = np.stack([Rz["base_val"][i] for i in ii]); arrs["ref_btcv"] = np.array([Rz["btcv"][i] for i in ii])
        ref = {"features": a.ref, "features_sha256": sha(a.ref), "anchors": want, "pairs": int(roff[-1])}
    np.savez(out, **arrs)
    rec = {"output": out, "sha256": sha(out), "rows": [int(rts[0]), int(rts[-1]), int(len(rts))], "boundary_cells": int(k.sum()),
           "member_anchors": int(len(m_anch)), "funding_names": int(len(cols)), "funding_events": int(len(arrs["f_ft"])), "per_event": a.per_event, "ref": ref,
           "inputs": {p: sha(f"{WK}/{p}") for p in ("cache_crypto.npy", "boundary.npz", "members_hist_all.npz", "fund_state.npz", "axes.npz")},
           "device_sha256": sha(os.path.abspath(__file__))}
    os.makedirs(f"{W}/receipts", exist_ok=True)
    json.dump(rec, open(f"{W}/receipts/{a.receipt}.json", "w"), indent=1)
    print(a.receipt, json.dumps({k_: v for k_, v in rec.items() if k_ != "inputs"}), flush=True)


if __name__ == "__main__":
    main()
