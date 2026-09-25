"""★★★ DEPRECATED 2026-09-25 — DO NOT USE FOR ANY NEW READING. Calling main() raises. ★★★

REASON: L80-81 of this file computes the combo kernel's RN8 from `fund_replay.npz`
(`last_rate` / `last_iv`), and that artefact is CONTAMINATED. Root cause (receipt FA_RN8CENSUS.json,
commit 9f9c8ac96; news2 2b87e8546):
  * the producer block compiled by the replay (shadow_loop_v3 as pinned, sha 6080073964) SKIPS the fetch when
    `anchor - last_ts < exp_iv*3600*0.9`. The LIVE producer (52baf979) L633-634 guards that same line with
    `not _bulk_ok` -- "NC A4: under bulk, never skip on the predicted interval". The pinned copy predates the
    guard and contains zero occurrences of `_bulk_ok` (news2 verified the three copies side by side).
  * in the replay that block is the SOLE POPULATOR of `led` (cold start), so the gate self-locks: once a name
    is recorded at iv=8 it is not looked at again for 7.2h, and every 1h spike settlement is skipped.
  * effect vs the clean NC legs: 404 of 2,644,794 cells differ, 43 SIGN FLIPS, 358 of them in 2026
    (TLMUSDT 2026-03-02: truth +0.0001, this file -0.02). Discriminator: gate active AND the ledger held
    settlements never fetched -- 360/404 differing vs 0/20,000 non-differing.

USE INSTEAD: the NC legs product `/dev/shm/news2_2026-09-23/work/legs.npz` (sha 9ee5886f...), whose RN8 is
bitwise equal to the exchange archive on every adjudicated diagnostic cell. Read it; do not re-derive the rule.
(lead ruling 2026-09-25: the replay is NOT fixed, it is RETIRED; research uses NC legs only.)

Original docstring follows.
"""

"""FRESH P3 legs/seats — news_legs.py with ONLY the roots changed (PREREG_fresh_models_newS_2026-09-23.md §1: the seat legs
and the combo are rebuilt from FRESH's own King OOF; everything else is byte-for-byte news_legs.py).
  inputs  : NEW_S root (READ-ONLY) for NEWS_FEATURES.npz / fund_replay.npz / cache_x0918r_* / bundle_config.json
            FRESH root for work/king/KING_OOF.npz
  outputs : FRESH root work/legs.npz, receipts/P3_LEGS.json
Producer source lines (xz_in_base, xz, leg-return recursion, msharpe w3) are taken from the same producer snapshot with the
same sha assertion, through news_hist_features (copied unchanged into this agent's devices).
"""
import os, sys, ast, json, time, hashlib
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_hist_features as H

W = "/dev/shm/fresh_2026-09-23"      # FRESH root (outputs, King OOF)
N = H.W                              # NEW_S root, READ-ONLY (frozen shared inputs); asserted below
assert N == "/dev/shm/news_2026-09-23"
CACHE_NPY = f"{N}/work/cache_x0918r_data.npy"


def prod_funcs():
    src = open(H.SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == H.SHADOW_SHA
    t = ast.parse(src); t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name == "xz_in_base"]; assert len(t.body) == 1
    ns = {"np": np}; exec(compile(t, H.SHADOW_SRC, "exec"), ns)
    lines = src.decode().split("\n")
    assert lines[597].strip() == "def xz(v):" and lines[601].strip() == "return out"
    exec("from scipy.stats import rankdata\n" + "\n".join(l[4:] for l in lines[597:602]), ns)
    return ns["xz_in_base"], ns["xz"]


def main():
    raise RuntimeError(
        "fresh_legs.py is DEPRECATED (2026-09-25) and must not produce new readings: its L80-81 RN8 comes "
        "from the contaminated fund_replay.npz (404 cells differ from the clean NC legs, 43 sign flips, 358 "
        "in 2026). Use /dev/shm/news2_2026-09-23/work/legs.npz (sha 9ee5886f) instead. "
        "See receipt FA_RN8CENSUS.json / commit 9f9c8ac96 and the file header for the root cause.")
    # --- unreachable below; kept verbatim so the archived product remains reproducible if ever re-authorised ---
    t0 = time.time(); xz_in_base, xz = prod_funcs()
    F = np.load(f"{N}/work/NEWS_FEATURES.npz"); K = np.load(f"{W}/work/king/KING_OOF.npz")
    a = F["anchors"].astype(np.int64); syms = [str(s) for s in F["symbols"]]; off = F["off"]; cnt = F["count"]; n, NW = len(a), len(syms)
    assert np.array_equal(K["E_ts"].astype(np.int64), a)
    cfg = json.load(open(f"{N}/inputs/bundle_config.json")); P = cfg["params"]
    fr = np.load(f"{N}/work/fund_replay.npz"); assert np.array_equal(fr["anchors"], a)
    ax = np.load(f"{N}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
    assert os.path.exists(CACHE_NPY), "NEW_S rolling cache .npy removed; rebuild from the npz into THIS root before rerunning"
    D = np.load(CACHE_NPY, mmap_mode="r")
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
           "first_ready": int(a[np.argmax(ready)]), "inputs": {"features": H.sha(f"{N}/work/NEWS_FEATURES.npz"), "king_oof": H.sha(f"{W}/work/king/KING_OOF.npz"),
           "fund_replay": H.sha(f"{N}/work/fund_replay.npz"), "rolling_cache_npy": H.sha(CACHE_NPY), "cache_axes": H.sha(f"{N}/work/cache_x0918r_axes.npz")},
           "source_sha": H.sha(os.path.abspath(__file__)), "producer": {H.SHADOW_SRC: H.SHADOW_SHA},
           "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
           "fresh_note": "identical to news_legs.py except the roots; King OOF is FRESH's monthly-fold OOF (PREREG §1 K/E)",
           "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(f"{W}/receipts/P3_LEGS.json", "w"), indent=1); print("LEGS_DONE", json.dumps({k: rec[k] for k in ("ready", "not_ready", "not_ready_reasons", "leg_returns")}), flush=True)


if __name__ == "__main__":
    main()
