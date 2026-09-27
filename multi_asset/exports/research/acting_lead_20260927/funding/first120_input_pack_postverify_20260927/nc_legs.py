"""NC legs / seats in the NEW-CONTRACT producer caliber (DESIGN §A3-3, §A5, §A6), for F10 training (Z24/ZFD/WL/ready) and the combo.
Same structure and readiness rules as NEW_S news_legs.py (6fb0…, AMENDMENT 1 §3.10); the three differences are the contract's:
  * seat returns y4v = 48-row sums of the RETURN CHANNEL rr (the researcher's R; = the producer's CDf[:, :, 0] after A3), float32
    arithmetic as the producer does it (np.where(fin, seg, 0).sum(0) on float32), >= 46 finite;
  * the fund rank base is the NC_FEATURES base_val row (legal ∧ crypto ∧ axis ∧ fresh known EMA, A6);
  * rn8 (FTRIM) is the nc_contract funding as-of rn8 (12 h freshness, known interval), not the ledger tail.
xz_in_base and xz are compiled from the patched tree's shadow_loop_v3.py (located by text, sha asserted).
usage: python nc_legs.py <NC_FEATURES.npz> <KING_OOF.npz> <out legs.npz>   (env NC_W, NC_TREE)"""
import os, sys, ast, json, time, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_hist_features as H

W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23"); TREE = os.environ.get("NC_TREE", f"{W}/tree"); CFG = os.environ.get("NC_CFG", f"{W}/inputs/bundle_config.json")


def prod_funcs():
    src = open(H.SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == H.REC["outputs"]["shadow_loop_v3.py"]
    t = ast.parse(src); t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "xz_in_base"]; assert len(t.body) == 1
    ns = {"np": np}; exec(compile(t, H.SHADOW_SRC, "exec"), ns)
    lines = src.decode().split("\n")
    b = [i for i, l in enumerate(lines) if l.strip() == "def xz(v):"]; assert len(b) == 1
    assert lines[b[0] + 4].strip() == "return out"
    exec("from scipy.stats import rankdata\n" + "\n".join(l[4:] for l in lines[b[0]:b[0] + 5]), ns)
    return ns["xz_in_base"], ns["xz"]


def main():
    t0 = time.time(); fpath, kpath, out = sys.argv[1:4]
    H.set_tree(TREE); xz_in_base, xz = prod_funcs(); NC = H._G["NC"]
    F = np.load(fpath); K = np.load(kpath); I = H.Inputs()
    a = F["anchors"].astype(np.int64); syms = [str(s) for s in F["symbols"]]; off = F["off"]; n, NW = len(a), len(syms)
    assert np.array_equal(K["E_ts"].astype(np.int64), a) and np.array_equal(I.anchors, a)
    P = json.load(open(CFG))["params"]
    cpos = np.full(NW, -1, np.int64); cpos[I.cols] = np.arange(len(I.cols))
    KZ = np.full((n, NW), np.nan, np.float32); Z24 = KZ.copy(); ZFD = KZ.copy(); QV = KZ.copy(); RN8 = KZ.copy()
    WL = np.full((n, 3), np.nan, np.float32); LRm = np.full((n, 3), np.nan); ready = np.zeros(n, bool)
    why = {}; LR = {"king": [], "rev24": [], "fund": []}; prev = None; last_anchor = None
    for i in range(n):
        A = int(a[i]); m = F["m"][off[i]:off[i + 1]].astype(np.int64)
        if len(m) < 50: why[A] = "members<50"; continue
        if prev is not None and prev["anchor_ts"] == last_anchor and A - last_anchor == 14400:
            ia = int(np.searchsorted(I.ts, A)); assert I.ts[ia] == A
            seg = np.full((48, NW), np.nan, np.float32); seg[:, I.cols] = I.R[ia - 47:ia + 1]     # rr rows (A-4h, A]
            fin = np.isfinite(seg)
            y4v = np.where(fin, seg, 0).sum(0); y4v[fin.sum(0) < 46] = np.nan
            pm = np.array(prev["members"])
            for leg in ("king", "rev24", "fund"):
                z = np.array(prev["legz"][leg])
                okl = np.isfinite(y4v[pm])
                zz = np.where(okl, z, 0.0)
                zz -= zz[okl].mean() if okl.sum() else 0
                g = np.abs(zz).sum()
                LR[leg].append(float((zz / g * np.nan_to_num(y4v[pm], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
            LRm[i - 1] = [LR[k][-1] for k in ("king", "rev24", "fund")]
        look = P["msharpe_look"]
        if len(LR["king"]) >= look:
            r = np.stack([np.array(LR[leg][-look:]) for leg in ("king", "rev24", "fund")])
            shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
            w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            w3 = np.array([1 / 3] * 3)
        pred = K["P"][i, m]
        bv = F["base_val"][i]; base_vals = {syms[j]: float(bv[j]) for j in np.flatnonzero(np.isfinite(bv))}
        fe_v = F["fe_v"][off[i]:off[i + 1]]; rev24 = F["rev24"][off[i]:off[i + 1]]; qvm = F["qvm"][off[i]:off[i + 1]]
        qv4h = np.expm1(np.clip(qvm, 0, 30)) * 48; sel = qv4h >= P["qv4h_min"]
        if sel.sum() < P["sel_min"]: why[A] = "sel<sel_min"; continue
        if not np.isfinite(pred).all(): why[A] = "king_oof_missing"; continue
        if len(base_vals) < 10: why[A] = "fund_base<10"; continue
        legz = {"king": xz(pred), "rev24": xz(-rev24), "fund": xz_in_base(fe_v, [syms[int(j)] for j in m], base_vals)}
        KZ[i, m] = legz["king"]; Z24[i, m] = legz["rev24"]; ZFD[i, m] = legz["fund"]; QV[i, m] = qv4h
        ema, led = I.funding(A)
        RN8[i, m] = [NC.funding_asof(ema.get(syms[j]), led[syms[j]][-1], A)[3] if syms[j] in led else np.nan for j in m]
        WL[i] = w3; ready[i] = True
        prev = {"anchor_ts": A, "members": [int(x) for x in m], "legz": {k: [float(x) for x in np.nan_to_num(v)] for k, v in legz.items()}}
        last_anchor = A
    np.savez_compressed(out, E_ts=a, symbols=np.array(syms), KZ=KZ, Z24=Z24, ZFD=ZFD, WL=WL, ready=ready, LR=LRm, QV=QV, RN8=RN8)
    import collections
    rec = {"status": "NC_PRODUCTION_CALIBER_LEGS_NOT_CASH_PNL", "output": out, "sha256": H.sha(out), "ready": int(ready.sum()), "not_ready": int((~ready).sum()),
           "not_ready_reasons": dict(collections.Counter(why.values())), "leg_returns": len(LR["king"]),
           "first_ready": int(a[np.argmax(ready)]) if ready.any() else None,
           "inputs": {"features": H.sha(fpath), "king_oof": H.sha(kpath), "fund_state": H.sha(f"{W}/work/fund_state.npz"), "R_crypto": H.sha(f"{W}/work/R_crypto.npy")},
           "source_sha": H.sha(os.path.abspath(__file__)), "tree_shadow_loop_sha256": H.REC["outputs"]["shadow_loop_v3.py"], "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(os.path.join(os.path.dirname(out), "NC_LEGS_RECEIPT.json"), "w"), indent=1)
    print("NC_LEGS_DONE", json.dumps({k: rec[k] for k in ("ready", "not_ready", "not_ready_reasons", "leg_returns")}), flush=True)


if __name__ == "__main__":
    main()
