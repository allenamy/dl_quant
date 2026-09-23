"""NEWS P5-a (Mac, production venv): recompute the TRAINING-BUILD features of the parity anchors 2026-09-17T16Z..09-19T00Z with the
same device (news_hist_features.replay_anchor → producer source lines / dlw_features.py / f8 build, sha-asserted) on the Mac,
from the same x0918r slice / mask / holes / funding replay state that pod2 used. Output is compared bitwise with pod2's
NEWS_FEATURES rows (platform/library numerics check: pod2 x86-64 AVX-512 disabled vs the production machine).
Run only inside the quiet window; writes only under ~/cc_tmp/news_20260923/parity."""
import os, sys, json, time, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import news_hist_features as H

P = os.path.expanduser("~/cc_tmp/news_20260923")
H.W = f"{P}/parity"; H.PROD = f"{P}/producer_copy"
H.SHADOW_SRC = f"{H.PROD}/shadow_loop_v3.py"; H.COMBO_SRC = f"{H.PROD}/fea171/combo_stage.py"
H.DLW_SRC = f"{H.PROD}/fea171/dlw_features.py"; H.F8_SRC = f"{H.PROD}/fea171/f8_higher_order_features.py"
H.XSYMS = f"{H.PROD}/fea171/xfer_syms.npz"; H.XREF = f"{H.PROD}/fea171/xfer_ref.npz"
ANCH = [1789660800 + 14400 * k for k in range(9)]


def main():
    t0 = time.time()
    for f, s in ((H.SHADOW_SRC, H.SHADOW_SHA), (H.COMBO_SRC, H.COMBO_SHA), (H.DLW_SRC, H.DLW_SHA), (H.F8_SRC, H.F8_SHA)): assert H.sha(f) == s, f
    C = np.load(f"{P}/parity/parity_cache_slice.npz", allow_pickle=True); ts = C["ts"].astype(np.int64); D = C["data"]; row0 = int(C["row0"])
    syms = [str(s) for s in C["symbols"]]; chn = [str(c) for c in C["ch"]]
    hz = np.load(f"{P}/parity/parity_holes_slice.npz"); o = np.lexsort((hz["col"], hz["row"])); holes = (hz["row"][o].astype(np.int64) - row0, hz["col"][o].astype(np.int64))
    mk = np.load(f"{P}/parity/parity_mask_slice.npz"); mts = mk["ts"].astype(np.int64)
    fr = np.load(f"{P}/parity/parity_fund_slice.npz"); fa = fr["anchors"].astype(np.int64)
    crypto = np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/news_2026-09-23/receipts/P1_members_2025H2on.npz")["crypto"]
    cfg = json.load(open(f"{P}/producer_copy/shadow_bundle/config.json"))
    out = {}
    os.makedirs(f"{P}/parity/work", exist_ok=True)
    for A in ANCH:
        i = int(np.searchsorted(fa, A)); assert fa[i] == A
        cand = mk["mask"][int(np.searchsorted(mts, A))] & crypto
        ema = {syms[j]: {"acc": float(fr["ema_acc"][i, j])} for j in np.flatnonzero(np.isfinite(fr["ema_acc"][i]))}
        led = {syms[j]: [[int(fr["last_ft"][i, j]), float(fr["last_rate"][i, j]), float(fr["last_iv"][i, j])]] for j in np.flatnonzero(fr["last_ft"][i] >= 0)}
        t1 = time.time()
        r = H.replay_anchor(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{P}/parity/work", holes=holes, cols="members")
        bv = np.full(len(syms), np.nan)
        for s, v in r["base_vals"].items(): bv[syms.index(s)] = v
        out[A] = {"m": r["m"], "X78": r["king_X78"], "X82": r["X82"], "X89": r["X89"], "fe_v": r["fe_v"], "fn_v": r["fn_v"], "iv_v": r["iv_v"], "qvm": r["qvm"], "rev24": r["rev24"], "base_val": bv}
        print(time.strftime("%H:%M:%S", time.gmtime()), A, len(r["m"]), round(time.time() - t1, 1), flush=True)
    np.savez(f"{P}/parity/MAC_TRAINBUILD_FEATURES.npz", anchors=np.array(ANCH), **{f"{k}_{A}": v for A, d in out.items() for k, v in d.items()})
    json.dump({"device": os.path.abspath(__file__), "device_sha256": H.sha(os.path.abspath(__file__)), "news_hist_features_sha256": H.sha(os.path.join(HERE, "news_hist_features.py")),
               "python": sys.version, "numpy": np.__version__, "anchors": ANCH, "seconds": round(time.time() - t0, 1),
               "output_sha256": H.sha(f"{P}/parity/MAC_TRAINBUILD_FEATURES.npz")}, open(f"{P}/parity/MAC_TRAINBUILD_FEATURES.json", "w"), indent=1)
    print("MAC_P5A_DONE", round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
