"""NEWS P5 data parity (Mac, read-only): the producer's archived live inputs at 2026-09-17T16Z..09-19T00Z vs the training build's inputs.
(1) rolling cache: the 450 fetched names' 7 channels, all 11520 rows, bitwise vs x0918r;
(2) funding: producer ledger_tail last row (ft, rate, iv) vs the training replay's last row; EMA acc relative differences;
(3) SPEC legal function (TRADABLE W24H: ≥1 bar with log_cnt>0 in (A−24h, A]; LIVE: ≥1 non-hole bar with finite log_qv in the window) applied to
    the x0918r slice (hole cells NaN) vs the x0918r legal mask, all 829 names — validates the function used for future-anchor checks;
(4) fund-leg rank base: producer base_syms with fresh EMA vs the training candidates with fresh EMA."""
import os, json, time, hashlib
import numpy as np
P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow"); PAR = f"{P}/parity"
ANCH = [1789660800 + 14400 * k for k in range(9)]


def legal_spec(block):
    """block: (288, N, 7) f16 rows (A−24h, A]; returns bool (N,)"""
    lc = block[:, :, 4].astype(np.float32); lq = block[:, :, 3].astype(np.float32)
    return (np.isfinite(lc) & (lc > 0)).any(0) & np.isfinite(lq).any(0)


def main():
    cfg = json.load(open(f"{P}/producer_copy/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    L450 = np.array([sidx[s] for s in cfg["symbols_live"]])
    X = np.load(f"{PAR}/parity_cache_slice.npz", allow_pickle=True); xts = X["ts"].astype(np.int64); xd = np.array(X["data"]); row0 = int(X["row0"])
    HZ = np.load(f"{PAR}/parity_holes_slice.npz"); xh = xd.copy(); xh[HZ["row"] - row0, HZ["col"], :] = np.nan
    MK = np.load(f"{PAR}/parity_mask_slice.npz"); mts = MK["ts"].astype(np.int64)
    FR = np.load(f"{PAR}/parity_fund_slice.npz"); fa = FR["anchors"].astype(np.int64)
    crypto = np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/news_2026-09-23/receipts/P1_members_2025H2on.npz")["crypto"]
    res = []
    for A in ANCH:
        d = f"{WS}/state/snap/{A}"; z = np.load(f"{d}/rolling.npz", allow_pickle=True); aux = json.load(open(f"{d}/aux.json"))
        rts = z["ts"].astype(np.int64); RD = z["data"]; xi = np.searchsorted(xts, rts); assert np.array_equal(xts[xi], rts)
        a = RD[:, L450, :].view(np.uint16); b = xd[xi][:, L450, :].view(np.uint16)
        fa_ = np.isfinite(RD[:, L450, :].astype(np.float32)); fb_ = np.isfinite(xd[xi][:, L450, :].astype(np.float32))
        ne = (a != b) & ~(~fa_ & ~fb_)
        i = int(np.searchsorted(fa, A)); led = aux["ledger_tail"]; ema = aux["ema"]
        lr_eq = lr_n = 0; rel = []
        for j in np.flatnonzero(FR["last_ft"][i] >= 0):
            s = syms[j]
            if s in led and led[s]:
                lr_n += 1; row = led[s][-1]
                lr_eq += int(int(row[0]) == int(FR["last_ft"][i, j]) and float(row[1]) == float(FR["last_rate"][i, j]) and float(row[2]) == float(FR["last_iv"][i, j]))
            if s in ema and np.isfinite(FR["ema_acc"][i, j]): rel.append(abs(ema[s]["acc"] - FR["ema_acc"][i, j]) / max(abs(FR["ema_acc"][i, j]), 1e-12))
        ia = int(np.searchsorted(xts, A)); blk = xh[ia - 287:ia + 1]
        ls = legal_spec(blk); lm = MK["mask"][int(np.searchsorted(mts, A))]
        cand = lm & crypto
        base_fresh = {s for s in aux["base_syms"] if led.get(s) and s in ema and A - led[s][-1][0] <= 43200}
        train_fresh = {syms[j] for j in np.flatnonzero(cand) if FR["last_ft"][i, j] >= 0 and A - FR["last_ft"][i, j] <= 43200 and np.isfinite(FR["ema_acc"][i, j])}
        r = {"anchor": A, "rolling_450_cells": int(ne.size), "rolling_450_diff_cells": int(ne.sum()),
             "ledger_last_row_equal": f"{lr_eq}/{lr_n}", "ema_rel_diff_median": float(np.median(rel)), "ema_rel_diff_max": float(np.max(rel)), "ema_exact": int(sum(1 for x in rel if x == 0)),
             "legal_spec_vs_mask_diff_names": [syms[j] for j in np.flatnonzero(ls != lm)],
             "fund_base_fresh": {"serving_n": len(base_fresh), "training_n": len(train_fresh), "serving_minus_training": sorted(base_fresh - train_fresh), "training_minus_serving": sorted(train_fresh - base_fresh)}}
        res.append(r); print(json.dumps(r)[:600], flush=True)
    json.dump({"device": os.path.abspath(__file__), "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "results": res},
              open(f"{PAR}/P5_DATA_PARITY.json", "w"), indent=1)


if __name__ == "__main__":
    main()
