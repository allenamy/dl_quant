#!/usr/bin/env python3
"""neutral_step0.py — ZERO-RETURN step 0 of docs/DESIGN_net_neutrality_fix_2026-09-27.md (lead 11:1xZ: step 0 only; F0 must reproduce the stored
weights bit for bit). Committed before it is run. No price or return array is read.

What it does, per seed (42, 2027), on the NC combo replay (news2_combo.py -> continuous_combo.evolve -> combo_target.step, scaled_diagnostic policy):
  1 replays the combo with an INSTRUMENTED copy of the producer chain (combo_stage.py fb5a9407 lines of def chain, copied verbatim, plus accounting);
    identity control A: at every call the instrumented chain's output == the producer chain's output (np.array_equal; the producer chain is compiled
    from the pinned source by combo_target.source_kernels);
    identity control B: the replayed weights / trade_mask / kc / fc == the stored combo_s{seed}/scaled_diagnostic.npz arrays (np.array_equal).
  2 exact linear attribution of each chain state's sum (kc and fc separately): sum(final) = (1-alpha)*sum(H) + alpha*sum(tgt) + band_eff + exit_eff,
    with sum(tgt) = the post-clip net (the demean step makes the pre-clip net 0), band_eff = sum(smv_band - smv_ema), exit_eff = sum(smv_exit - smv_band),
    and the state serialisation truncation (|x| <= 1e-9 -> 0) as its own term; components are carried with the same (1-alpha) recursion, and the sum of
    components must equal the state's sum (assert |diff| < 1e-9). The published book's skew (short - long)/gross = -sum(raw)/sum|raw| with raw =
    0.55 kc + 0.45 fc is attributed to CLIP / BAND / EXIT / TRUNC by the same linear map.
  3 target-level candidates (DESIGN §2): F1a additive re-demean over non-zero names after the exit step; F1b shrink the heavier side to the lighter;
    F1c grow the lighter side to the heavier; F2 iterate (demean -> renormalise -> clip -> renormalise) after the clip until |sum| < 1e-12 (<= 50 rounds).
    Each fix sits INSIDE the chain (so the state carries it). Reported per year: skew of published weights, gross, turnover sum|w_pub(i) - w_held(i-1)|,
    names, sign flips vs F0 at the same anchor, publication acceptance vs F0.
Outputs /dev/shm/alloc_2026-09-26/neutral/NEUTRAL_STEP0.json (sha from the written bytes); marker lines on stdout.
usage (pod2): /workspace/venv/bin/python -B neutral_step0.py
"""
import os, sys, json, time, hashlib, pathlib, collections
import numpy as np
from scipy.stats import rankdata
W = pathlib.Path("/dev/shm/news2_2026-09-23"); DEV = W / "devices"; OUT = pathlib.Path("/dev/shm/alloc_2026-09-26/neutral")
sys.path.insert(0, str(DEV))
import combo_target                                   # sha-checked producer kernels (EXPECTED fb5a9407)
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
PINS = {"continuous_combo.py": "1501c9f63641bf447c4cb33661d08da25ced0948f9fae63cebb44cdfd1995d21",
        "combo_target.py": "d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544",
        "book_universe.py": "90e332cc27cf8f34aabcac13f9829f84e463ffa900efbe554e17c07436e8dcca"}
STORED = {"42": "f4630a20f796bce26590aedeadfc28791be7eeecee8c14789f418b5a08de4388", "2027": "fe09d81744030e3fc7da3367ed7da8668d390a68d1db66764be4cc74f40b00ce"}
FIXES = ("F0", "F1a", "F1b", "F1c", "F2")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""): h.update(b)
    return h.hexdigest()


for f, s in PINS.items(): assert sha(DEV / f) == s, ("source pin", f)
PROD = combo_target.source_kernels()                  # producer chain + exec_reshape (sha asserted inside)


def chain_i(zc, P, NW, pm, sel, LIVE_MASK, H, fix):
    """verbatim copy of combo_stage.py def chain (fb5a9407) + accounting + optional fix. Returns (smv, acct) or (None, None)."""
    w = np.where(sel, zc, 0.0)
    w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w)
    g = np.abs(w).sum()
    if g < 1e-9: return None, None
    w = w / g
    capw = P["cap_mult"] / max(int(sel.sum()), 1)
    w = np.clip(w, -capw, capw)
    g2 = np.abs(w).sum()
    if g2 > 1e-9: w = w / g2
    if fix == "F2":
        for _ in range(50):
            if abs(w.sum()) < 1e-12: break
            w = np.where(sel, w - (w[sel].mean() if sel.any() else 0), w); w = w / np.abs(w).sum(); w = np.clip(w, -capw, capw); w = w / np.abs(w).sum()
    tgt = np.zeros(NW); tgt[pm] = w
    smv = H + P["alpha"] * (tgt - H)
    trade = smv - H
    smv_b = np.where(np.abs(trade) < P["band"], H, smv)
    _keep_liq = np.zeros(NW, bool); _keep_liq[pm[sel]] = True
    keep = (LIVE_MASK.copy() if LIVE_MASK is not None else np.ones(NW, bool))
    if LIVE_MASK is not None:
        _mm = np.zeros(NW, bool); _mm[pm] = True
        keep &= _mm
    keep &= _keep_liq
    leave = (~keep) & (np.abs(smv_b) > 1e-12)
    smv_e = np.where(leave, 0.0, smv_b)
    out = smv_e
    if fix == "F1a":
        nz = np.abs(out) > 1e-12; out = out.copy()
        if nz.any(): out[nz] = out[nz] - out[nz].mean()
    elif fix in ("F1b", "F1c"):
        pos = out.clip(min=0).sum(); neg = -out.clip(max=0).sum(); out = out.copy()
        if pos > 1e-12 and neg > 1e-12:
            if (neg > pos) == (fix == "F1b"): out = np.where(out < 0, out * (pos / neg), out)
            else: out = np.where(out > 0, out * (neg / pos), out)
    acct = {"sum_tgt": float(tgt.sum()), "sum_H": float(H.sum()), "band": float(smv_b.sum() - smv.sum()), "exit": float(smv_e.sum() - smv_b.sum()),
            "fix": float(out.sum() - smv_e.sum()), "final": float(out.sum())}
    return out, acct


def step_i(king_rank, f10_score, fund_rank, seats, rn8, members, qv, legal, params, kc_prev, fc_prev, fix, check):
    """verbatim logic of combo_target.step (d7577e82), scaled_diagnostic policy, calling chain_i; check=True asserts chain_i == producer chain."""
    m = np.asarray(members, int); nw = len(kc_prev); n = len(m)
    if not np.isfinite(king_rank).all(): return {"accepted": False, "kc": kc_prev.copy(), "fc": fc_prev.copy(), "raw": None, "acct": None}
    okf = np.isfinite(f10_score); zf = np.full(n, np.nan)
    zf[okf] = rankdata(np.asarray(f10_score)[okf]) / max(okf.sum() - 1, 1) - .5
    w = np.array([seats[0], 0., seats[2]], float); w = w / w.sum() if w.sum() > 1e-12 else np.array([.5, 0., .5])
    zkc = w[0] * np.nan_to_num(king_rank, nan=0.) + w[2] * np.nan_to_num(fund_rank, nan=0.)
    zfc = w[0] * np.nan_to_num(zf, nan=0.) + w[2] * np.nan_to_num(fund_rank, nan=0.)
    zkc = np.where((zkc < 0) & np.isfinite(rn8) & (rn8 <= -.001), 0., zkc)
    zfc = np.where((zfc < 0) & np.isfinite(rn8) & (rn8 <= -.001), 0., zfc)
    sel = np.isfinite(qv) & (np.asarray(qv) >= params["qv4h_min"]); LM = np.asarray(legal, bool)
    kc, ak = chain_i(zkc, params, nw, m, sel, LM, kc_prev, fix); fc, af = chain_i(zfc, params, nw, m, sel, LM, fc_prev, fix)
    if check:
        PROD.update(P=params, NW=nw, pm=m, sel=sel, LIVE_MASK=LM)
        PROD["H"] = kc_prev; kp = PROD["chain"](zkc); PROD["H"] = fc_prev; fp = PROD["chain"](zfc)
        assert (kc is None) == (kp is None) and (fc is None) == (fp is None), "identity A (None)"
        if kc is not None: assert np.array_equal(kc, kp) and np.array_equal(fc, fp), "identity A (chain output)"
    if kc is None or fc is None: return {"accepted": False, "kc": kc_prev.copy(), "fc": fc_prev.copy(), "raw": None, "acct": None}
    raw = .55 * kc + .45 * fc; gross = float(np.abs(raw).sum()); names = int((np.abs(raw) > 1e-9).sum())
    ok = okf.sum() >= int(np.ceil(.95 * n)) and .4 <= gross <= 1.2 and names >= int(np.ceil(.375 * n))
    return {"accepted": bool(ok), "kc": kc, "fc": fc, "raw": raw, "acct": (ak, af)}


def run(seed, inp, fix):
    a, KZ, P10, ZFD, WL, RN8, mem, QV, legal, ready, params = inp
    n, w = KZ.shape; kc = np.zeros(w); fc = np.zeros(w); alpha = params["alpha"]
    comp = {c: {k: 0.0 for k in ("CLIP", "BAND", "EXIT", "FIX", "TRUNC")} for c in ("kc", "fc")}
    res = {"weights": np.zeros((n, w)), "trade_mask": np.zeros(n, bool), "kc": np.zeros((n, w)), "fc": np.zeros((n, w)), "attr": np.full((n, 5), np.nan)}
    maxdiff = 0.0
    for i in range(n):
        if not ready[i]:
            res["kc"][i] = kc; res["fc"][i] = fc; continue
        m = np.asarray(mem[i], int)
        r = step_i(KZ[i, m], P10[i, m], ZFD[i, m], WL[i], RN8[i, m], m, QV[i, m], legal[i], params, kc, fc, fix, check=(fix == "F0"))
        if r["acct"] is not None:
            for c, ac in zip(("kc", "fc"), r["acct"]):
                d = comp[c]
                for k in d: d[k] *= (1 - alpha)
                # band/exit are applied to the whole vector incl. the carried part; the identity below is exact: final = (1-a)H + a*tgt + band + exit + fix
                d["CLIP"] += alpha * ac["sum_tgt"]; d["BAND"] += ac["band"]; d["EXIT"] += ac["exit"]; d["FIX"] += ac["fix"]
        kc_new = np.where(np.abs(r["kc"]) > 1e-9, r["kc"], 0.); fc_new = np.where(np.abs(r["fc"]) > 1e-9, r["fc"], 0.)
        if r["acct"] is not None:
            comp["kc"]["TRUNC"] += float(kc_new.sum() - r["kc"].sum()); comp["fc"]["TRUNC"] += float(fc_new.sum() - r["fc"].sum())
            for c, st in (("kc", kc_new), ("fc", fc_new)):
                maxdiff = max(maxdiff, abs(sum(comp[c].values()) - float(st.sum())))
        kc, fc = kc_new, fc_new; res["kc"][i] = kc; res["fc"][i] = fc
        if r["accepted"]:
            res["trade_mask"][i] = True; res["weights"][i] = np.where(np.abs(r["raw"]) > 1e-9, r["raw"], 0.)
            g = float(np.abs(r["raw"]).sum())
            res["attr"][i] = [-(.55 * comp["kc"][k] + .45 * comp["fc"][k]) / g for k in ("CLIP", "BAND", "EXIT", "FIX", "TRUNC")]
    assert maxdiff < 1e-9, ("attribution identity", maxdiff)
    res["attr_maxdiff"] = maxdiff
    return res


def load(seed):
    F = np.load(W / "work/NEWS_FEATURES.npz"); leg = np.load(W / "work/legs.npz"); score = np.load(W / f"work/f10_s{seed}/F10_OOF.npz")
    a = F["anchors"].astype(np.int64); syms = F["symbols"]
    for z in (leg, score): assert np.array_equal(z["E_ts"], a) and np.array_equal(z["symbols"], syms)
    mk = np.load("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"); assert np.array_equal(mk["ts"].astype(np.int64), a)
    crypto = np.load(W / "receipts/P1_members_2025H2on.npz")["crypto"]; cand = mk["mask"] & crypto[None, :]
    off = F["off"]; mm = F["m"]; members = [mm[off[i]:off[i + 1]].astype(np.int64) for i in range(len(a))]
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA; universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    params = json.loads((W / "inputs/bundle_config.json").read_text())["params"]
    mem_u = [members[i] for i in np.flatnonzero(use)]
    return (au, leg["KZ"][use].astype(np.float64), score["P"][use].astype(np.float64), leg["ZFD"][use].astype(np.float64), leg["WL"][use].astype(np.float64),
            leg["RN8"][use].astype(np.float64), mem_u, leg["QV"][use].astype(np.float64), book_legal, leg["ready"][use], params), syms


def summarise(res, f0, years):
    Wt = res["weights"]; tm = res["trade_mask"]; held = np.zeros(Wt.shape[1]); prev = np.zeros(Wt.shape[1]); rows = collections.defaultdict(list)
    for i in range(len(tm)):
        if not tm[i]: continue
        w = Wt[i]; g = np.abs(w).sum(); y = int(years[i])
        rows[y].append({"skew": float(-w.sum() / g), "gross": float(g), "turnover": float(np.abs(w - held).sum()), "names": int((np.abs(w) > 0).sum()),
                        "flips": int(((np.sign(w) * np.sign(f0["weights"][i])) < 0).sum()) if f0["trade_mask"][i] else None,
                        "attr": res["attr"][i].tolist()})
        held = w
    out = {}
    for y, rs in sorted(rows.items()):
        sk = np.array([r["skew"] for r in rs]); at = np.array([r["attr"] for r in rs])
        fl = [r["flips"] for r in rs if r["flips"] is not None]
        out[y] = {"published": len(rs), "skew_mean": float(sk.mean()), "skew_abs_median": float(np.median(np.abs(sk))), "share_short_heavy": float((sk > 0).mean()),
                  "gross_mean": float(np.mean([r["gross"] for r in rs])), "turnover_mean": float(np.mean([r["turnover"] for r in rs])),
                  "names_mean": float(np.mean([r["names"] for r in rs])), "sign_flips_vs_F0_mean": float(np.mean(fl)) if fl else None,
                  "skew_attr_mean": dict(zip(("CLIP", "BAND", "EXIT", "FIX", "TRUNC"), [float(x) for x in np.nanmean(at, 0)]))}
    out["accepted_vs_F0"] = {"both": int((tm & f0["trade_mask"]).sum()), "only_fix": int((tm & ~f0["trade_mask"]).sum()), "only_F0": int((~tm & f0["trade_mask"]).sum())}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"device": "neutral_step0.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "zero_returns": True, "pins": PINS, "producer_chain": "combo_stage.py fb5a9407 via combo_target.source_kernels", "per_seed": {}}
    for seed in ("42", "2027"):
        inp, syms = load(seed); years = np.array([time.gmtime(int(t)).tm_year for t in inp[0]])
        St = np.load(W / f"work/combo_s{seed}/scaled_diagnostic.npz"); assert sha(W / f"work/combo_s{seed}/scaled_diagnostic.npz") == STORED[seed]
        f0 = run(seed, inp, "F0")
        idB = {k: bool(np.array_equal(f0[k], St[k])) for k in ("weights", "trade_mask", "kc", "fc")}
        print("IDENTITY_B", seed, json.dumps(idB), flush=True)
        if not all(idB.values()):
            rec["per_seed"][seed] = {"identity_B": idB, "STOP": "F0 does not reproduce the stored arrays"}; break
        rec["per_seed"][seed] = {"identity_A": "asserted at every chain call", "identity_B": idB, "F0": summarise(f0, f0, years), "attr_maxdiff_F0": f0["attr_maxdiff"]}
        for fx in FIXES[1:]:
            r = run(seed, inp, fx); rec["per_seed"][seed][fx] = summarise(r, f0, years); rec["per_seed"][seed][fx + "_attr_maxdiff"] = r["attr_maxdiff"]
            print("FIX_DONE", seed, fx, flush=True)
    rec["STOP"] = next((v["STOP"] for v in rec["per_seed"].values() if "STOP" in v), None)
    b = json.dumps(rec, indent=1).encode(); p = OUT / "NEUTRAL_STEP0.json"
    with open(str(p) + ".tmp", "wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(str(p) + ".tmp", p); assert sha(p) == hashlib.sha256(b).hexdigest()
    print("NEUTRAL_STEP0", "STOP" if rec["STOP"] else "DONE", hashlib.sha256(b).hexdigest()[:16], flush=True)
    sys.exit(2 if rec["STOP"] else 0)


if __name__ == "__main__":
    main()
