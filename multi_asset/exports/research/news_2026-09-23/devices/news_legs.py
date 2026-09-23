"""NEWS P3 legs/seats in PRODUCTION caliber (AMENDMENT 1 §3.10), for F10 training (Z24/ZFD/WL/ready) and the combo.
Source lines used verbatim (compiled from shadow_loop_v3.py, sha asserted):
  xz_in_base (module-level function), xz (L598-602), leg-return recursion (L556-L572 formula), msharpe w3 (L589-596).
Readiness follows NEW's convention (no fabricated King score): an anchor is ready iff the producer would have produced a
record (members >= 50, sel >= sel_min) AND the NEWS King OOF score is finite for every member AND the fund base has >= 10 names.
Leg returns are appended only between consecutive ready anchors (the producer appends only when prev_rec is the previous anchor).
y4v uses the cache ret5 of (A-4h, A] for ALL names (the producer's rolling cache holds every fetched name), hole cells NaN.
"""
import os, sys, ast, json, time, hashlib
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_hist_features as H

W = H.W


def prod_funcs():
    src = open(H.SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == H.SHADOW_SHA
    t = ast.parse(src); t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "xz_in_base"]; assert len(t.body) == 1
    ns = {"np": np}; exec(compile(t, H.SHADOW_SRC, "exec"), ns)
    lines = src.decode().split("\n")
    assert lines[597].strip() == "def xz(v):" and lines[601].strip() == "return out"
    exec("from scipy.stats import rankdata\n" + "\n".join(l[4:] for l in lines[597:602]), ns)
    return ns["xz_in_base"], ns["xz"]


def main():
    t0 = time.time(); xz_in_base, xz = prod_funcs()
    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); K = np.load(f"{W}/work/king/KING_OOF.npz")
    a = F["anchors"].astype(np.int64); syms = [str(s) for s in F["symbols"]]; off = F["off"]; cnt = F["count"]; n, NW = len(a), len(syms)
    assert np.array_equal(K["E_ts"].astype(np.int64), a)
    cfg = json.load(open(f"{W}/inputs/bundle_config.json")); P = cfg["params"]
    fr = np.load(f"{W}/work/fund_replay.npz"); assert np.array_equal(fr["anchors"], a)
    ax = np.load(f"{W}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
    D = np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
    h = np.load("/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"); o = np.lexsort((h["col"], h["row"])); hr = h["row"][o].astype(np.int64); hc = h["col"][o].astype(np.int64)
    KZ = np.full((n, NW), np.nan, np.float32); Z24 = KZ.copy(); ZFD = KZ.copy(); QV = KZ.copy(); RN8 = KZ.copy()
    WL = np.full((n, 3), np.nan, np.float32); LRm = np.full((n, 3), np.nan); ready = np.zeros(n, bool); recorded = np.zeros(n, bool)
    why = {}; LR = {"king": [], "rev24": [], "fund": []}; prev = None; last_anchor = None
    for i in range(n):
        A = int(a[i]); m = F["m"][off[i]:off[i + 1]].astype(np.int64)
        if len(m) < 50: why[A] = "members<50"; continue          # production L510-512 returns before scoring
        # ---- previous-anchor scoring (production L557-572), before this anchor's legs ----
        if prev is not None and prev["anchor_ts"] == last_anchor and A - last_anchor == 14400:
            ia = int(np.searchsorted(ts, A)); seg = np.array(D[ia - 47:ia + 1, :, 0], np.float16)
            k0 = int(np.searchsorted(hr, ia - 47)); k1 = int(np.searchsorted(hr, ia + 1)); seg[hr[k0:k1] - (ia - 47), hc[k0:k1]] = np.nan
            seg = seg.astype(np.float32); fin = np.isfinite(seg)
            y4v = np.where(fin, seg, 0).sum(0); y4v[fin.sum(0) < 46] = np.nan
            pm = np.array(prev["members"])
            for li, leg in enumerate(("king", "rev24", "fund")):
                z = np.array(prev["legz"][leg])
                okl = np.isfinite(y4v[pm])
                zz = np.where(okl, z, 0.0)
                zz -= zz[okl].mean() if okl.sum() else 0
                g = np.abs(zz).sum()
                LR[leg].append(float((zz / g * np.nan_to_num(y4v[pm], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
            LRm[i - 1] = [LR[k][-1] for k in ("king", "rev24", "fund")]
        # ---- w3 (production L589-596) ----
        look = P["msharpe_look"]
        if len(LR["king"]) >= look:
            r = np.stack([np.array(LR[leg][-look:]) for leg in ("king", "rev24", "fund")])
            shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
            w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        else:
            w3 = np.array([1/3] * 3)
        pred = K["P"][i, m]
        bv = F["base_val"][i]; base_vals = {syms[j]: float(bv[j]) for j in np.flatnonzero(np.isfinite(bv))}
        fe_v = F["fe_v"][off[i]:off[i + 1]]; rev24 = F["rev24"][off[i]:off[i + 1]]; qvm = F["qvm"][off[i]:off[i + 1]]
        qv4h = np.expm1(np.clip(qvm, 0, 30)) * 48; sel = qv4h >= P["qv4h_min"]
        if sel.sum() < P["sel_min"]: why[A] = "sel<sel_min"; continue
        if not np.isfinite(pred).all(): why[A] = "king_oof_missing"; continue
        if len(base_vals) < 10: why[A] = "fund_base<10"; continue
        legz = {"king": xz(pred), "rev24": xz(-rev24), "fund": xz_in_base(fe_v, [syms[int(j)] for j in m], base_vals)}
        KZ[i, m] = legz["king"]; Z24[i, m] = legz["rev24"]; ZFD[i, m] = legz["fund"]; QV[i, m] = qv4h
        lr_ = fr["last_rate"][i, m]; li_ = fr["last_iv"][i, m]                                   # combo_stage L266-273 rn8 (ledger tail, no freshness)
        iv = np.where(np.isfinite(li_) & (li_ > 0), li_, 8.0); RN8[i, m] = np.where(np.isfinite(lr_), lr_ * (8.0 / iv), np.nan)
        WL[i] = w3; ready[i] = True; recorded[i] = True
        prev = {"anchor_ts": A, "members": [int(x) for x in m], "legz": {k: [float(x) for x in np.nan_to_num(v)] for k, v in legz.items()}}
        last_anchor = A
    out = f"{W}/work/legs.npz"
    np.savez_compressed(out, E_ts=a, symbols=np.array(syms), KZ=KZ, Z24=Z24, ZFD=ZFD, WL=WL, ready=ready, LR=LRm, QV=QV, RN8=RN8)
    import collections
    rec = {"status": "PRODUCTION_CALIBER_LEGS_NOT_CASH_PNL", "output": out, "sha256": H.sha(out), "ready": int(ready.sum()), "not_ready": int((~ready).sum()),
           "not_ready_reasons": dict(collections.Counter(why.values())), "leg_returns": len(LR["king"]),
           "first_ready": int(a[np.argmax(ready)]), "inputs": {"features": H.sha(f"{W}/work/NEWS_FEATURES.npz"), "king_oof": H.sha(f"{W}/work/king/KING_OOF.npz"),
           "fund_replay": H.sha(f"{W}/work/fund_replay.npz")}, "source_sha": H.sha(os.path.abspath(__file__)), "producer": {H.SHADOW_SRC: H.SHADOW_SHA},
           "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(f"{W}/receipts/P3_LEGS.json", "w"), indent=1); print("LEGS_DONE", json.dumps({k: rec[k] for k in ("ready", "not_ready", "not_ready_reasons", "leg_returns")}), flush=True)


if __name__ == "__main__":
    main()
