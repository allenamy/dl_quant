"""fa_a1a2.py — PREREG docs/PREREG_fresh_rootcause_A_2026-09-24.md (f646c57ed). Read-only, no engine, no GPU."""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
SER = "/dev/shm/fanom_2026-09-24/receipts/FA_ANCHOR_SERIES.npz"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")
Q33, Q67 = 0.5725596881282329, 0.7810047984528542
HS = (6, 42, 180); B = 10000; RNG = (20260923, 1); BLOCK_DAYS = 30; DAY = 86400

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 30: return None
    rx = np.argsort(np.argsort(x[ok])).astype(float); ry = np.argsort(np.argsort(y[ok])).astype(float)
    if rx.std() == 0 or ry.std() == 0: return None
    return float(np.corrcoef(rx, ry)[0, 1])

def boot_spear(x, y, days, rs):
    ud = np.unique(days); blk = BLOCK_DAYS; starts = np.arange(max(1, len(ud) - blk + 1))
    nb = int(np.ceil(len(ud) / blk)); out = []
    for _ in range(B):
        pick = rs.choice(starts, size=nb, replace=True)
        sel = np.concatenate([ud[s:s + blk] for s in pick])
        m = np.isin(days, sel)
        r = spear(x[m], y[m])
        if r is not None: out.append(r)
    o = np.array(out)
    return ([float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))], int(len(o))) if len(o) > 100 else ([None, None], int(len(o)))

def main():
    rec = {"device": "fa_a1a2.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_rootcause_A_2026-09-24.md", "commit": "f646c57ed"}}
    S = np.load(SER); ax = S["anchors"].astype(np.int64); dpx = S["price_diff_D_minus_A_bps"]; pre_e = S["in_pre2026"].astype(bool)
    LF = np.load(f"{F}/work/legs.npz"); LN = np.load(f"{N}/work/legs.npz")
    le = LF["E_ts"].astype(np.int64)
    rs_ = np.random.default_rng(RNG)
    # ---- A1 ----
    a1 = {"H_anchors": list(HS), "note": "Spearman(seat_king[i], sum of King leg return over the NEXT H anchors)"}
    prem = (le >= ts(PRE[0])) & (le <= ts(PRE[1]))
    for arm, L in (("FRESH", LF), ("NEWS", LN)):
        lr = L["LR"][:, 0].astype(np.float64); seat = L["WL"][:, 0].astype(np.float64)
        a1[arm] = {}
        for H in HS:
            fwd = np.full(len(le), np.nan)
            cs = np.nancumsum(np.nan_to_num(lr, nan=0.0))
            for i in range(len(le) - H):
                fwd[i] = cs[i + H] - cs[i]
            m = prem & np.isfinite(seat) & np.isfinite(fwd)
            r = spear(seat[m], fwd[m])
            ci, nd = boot_spear(seat[m], fwd[m], le[m] // DAY, np.random.default_rng(RNG))
            a1[arm][H] = {"spearman": r, "ci95": ci, "n_anchors": int(m.sum()), "boot_draws": nd,
                          "ci_upper_lt_0": bool(ci[1] is not None and ci[1] < 0),
                          "ci_crosses_or_positive": bool(ci[0] is None or ci[0] <= 0 <= ci[1] or ci[0] > 0)}
    fr = a1["FRESH"]; nw = a1["NEWS"]
    hits = [H for H in HS if fr[H]["spearman"] is not None and fr[H]["spearman"] < 0 and fr[H]["ci_upper_lt_0"]]
    ctrl_ok = all(nw[H]["ci_crosses_or_positive"] for H in hits) if hits else False
    a1["VERDICT"] = ("SUPPORTED" if (len(hits) >= 2 and ctrl_ok) else ("REFUTED" if len(hits) == 0 else "UNDECIDED"))
    a1["H_meeting_fresh_condition"] = hits; a1["control_not_negative_on_those_H"] = ctrl_ok
    rec["A1"] = a1
    # ---- A2 ----
    T = np.load(LAB, allow_pickle=True); te = T["E_ts"].astype(np.int64); y = T["y4s"]
    lpos = {int(v): i for i, v in enumerate(te)}
    CF = np.load(f"{F}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    CN = np.load(f"{N}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
    ce = CF["E_ts"].astype(np.int64); assert np.array_equal(ce, CN["E_ts"].astype(np.int64))
    rows = np.array([lpos.get(int(t), -1) for t in ce]); hit = rows >= 0
    Y = np.zeros((len(ce), y.shape[1])); Y[hit] = np.nan_to_num(y[rows[hit]].astype(np.float64), nan=0.0)
    prem_c = (ce >= ts(PRE[0])) & (ce <= ts(PRE[1])) & hit
    kcF, fcF, rawF = CF["kc"], CF["fc"], CF["raw"]; kcN, fcN, rawN = CN["kc"], CN["fc"], CN["raw"]
    proxF = (rawF * Y).sum(1); proxN = (rawN * Y).sum(1); dprox = proxF - proxN
    # (a) calibration of the proxy against the engine price channel
    epos = {int(t): i for i, t in enumerate(ax)}
    ei = np.array([epos.get(int(t), -1) for t in ce]); eok = ei >= 0
    cal_m = prem_c & eok
    dpx_on_c = np.full(len(ce), np.nan); dpx_on_c[eok] = dpx[ei[eok]]
    cal = {"n": int(cal_m.sum()), "spearman_proxy_vs_engine": spear(dprox[cal_m], dpx_on_c[cal_m]),
           "mean_proxy_bps_per_anchor": float(1e4 * np.nanmean(dprox[cal_m])),
           "mean_engine_bps_per_anchor": float(np.nanmean(dpx_on_c[cal_m])),
           "note": "prereg §2(a): if the correlation is weak, the decomposition describes the PROXY layer only"}
    # (b) exact additive split at the raw layer
    dkc = ((kcF - kcN) * Y).sum(1); dfc = ((fcF - fcN) * Y).sum(1)
    seatF = LF["WL"][:, 0].astype(np.float64)
    spos = {int(t): i for i, t in enumerate(le)}; si = np.array([spos[int(t)] for t in ce])
    seat_c = seatF[si]
    terc = np.where(seat_c <= Q33, 0, np.where(seat_c <= Q67, 1, 2))
    def split(mask, tag):
        tot = float(np.nansum(dprox[mask])); a = 0.55 * float(np.nansum(dkc[mask])); b = 0.45 * float(np.nansum(dfc[mask]))
        resid = tot - (a + b)
        pos = rawF > 0; neg = rawF < 0
        ls = float(np.nansum(((rawF * Y) * pos)[mask]) - np.nansum(((rawN * Y) * (rawN > 0))[mask]))
        ss = float(np.nansum(((rawF * Y) * neg)[mask]) - np.nansum(((rawN * Y) * (rawN < 0))[mask]))
        return {"population": tag, "n_anchors": int(mask.sum()), "delta_proxy_total": tot,
                "kc_part_0.55": a, "fc_part_0.45": b, "identity_residual": resid,
                "IDENTITY_CLOSES": bool(abs(resid) <= 1e-9 * max(1.0, abs(tot))),
                "share_kc": (a / tot if tot else None), "share_fc": (b / tot if tot else None),
                "long_side": ls, "short_side": ss, "long_plus_short_residual": tot - (ls + ss)}
    hi = prem_c & (terc == 2); rest = prem_c & (terc != 2)
    dec = {"high_seat": split(hi, "high seat tercile"), "rest": split(rest, "other anchors"), "all_pre2026": split(prem_c, "all")}
    for k, v in dec.items(): assert v["IDENTITY_CLOSES"], f"{k}: raw-layer identity does not close, residual {v['identity_residual']}"
    # (c) seat weights, reported not attributed
    wl = LF["WL"][si]; wsum = np.where(wl[:, 0] + wl[:, 2] > 1e-12, wl[:, 0] + wl[:, 2], np.nan)
    w0 = wl[:, 0] / wsum; w2 = wl[:, 2] / wsum
    def q(v, m): 
        vv = v[m]; vv = vv[np.isfinite(vv)]
        return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75))} if len(vv) else None
    wts = {"high_seat": {"w0_king": q(w0, hi), "w2_fund": q(w2, hi)}, "rest": {"w0_king": q(w0, rest), "w2_fund": q(w2, rest)},
           "note": "prereg §2(c): funding's WEIGHT only; its return contribution is NOT separable at the raw layer"}
    # (d) distributions
    KF = np.load(f"{F}/work/king/KING_OOF.npz"); GF = np.load(f"{F}/work/f10_s42/F10_OOF.npz")
    kpos = {int(t): i for i, t in enumerate(KF["E_ts"].astype(np.int64))}; ki = np.array([kpos[int(t)] for t in ce])
    disagree = np.full(len(ce), np.nan)
    for j in range(len(ce)):
        if not prem_c[j]: continue
        a_ = KF["P"][ki[j]]; b_ = GF["P"][ki[j]]
        ok = np.isfinite(a_) & np.isfinite(b_)
        if ok.sum() >= 30:
            ra = np.argsort(np.argsort(a_[ok])).astype(float); rb = np.argsort(np.argsort(b_[ok])).astype(float)
            if ra.std() > 0 and rb.std() > 0: disagree[j] = float(np.corrcoef(ra, rb)[0, 1])
    grossF = np.abs(rawF).sum(1); holdF = ~np.asarray(CF["trade_mask"]).astype(bool)
    breadth = np.where(Y != 0, Y > 0, np.nan)
    br = np.array([np.nanmean(breadth[j]) if prem_c[j] else np.nan for j in range(len(ce))])
    dist = {}
    for nm, m in (("high_seat", hi), ("rest", rest)):
        dist[nm] = {"king_f10_rank_corr": q(disagree, m), "raw_gross": q(grossF, m),
                    "hold_fraction": float(holdF[m].mean()), "breadth_frac_positive": q(br, m), "n": int(m.sum())}
    rec["A2"] = {"calibration": cal, "decomposition": dec, "seat_weights": wts, "distributions": dist}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print("FA_A1 VERDICT=%s hits=%s ctrl_ok=%s | FRESH=%s | NEWS=%s"
          % (a1["VERDICT"], hits, ctrl_ok,
             {H: (round(fr[H]["spearman"], 4), [round(c, 3) if c is not None else None for c in fr[H]["ci95"]]) for H in HS},
             {H: (round(nw[H]["spearman"], 4), [round(c, 3) if c is not None else None for c in nw[H]["ci95"]]) for H in HS}), flush=True)
    print("FA_A2 calib_spearman=%s proxy=%.4f engine=%.4f bps/anchor | high_seat: kc_share=%.3f fc_share=%.3f closes=%s | "
          "disagree(med) high=%.4f rest=%.4f | gross(med) high=%.4f rest=%.4f | hold high=%.3f rest=%.3f"
          % (("%.4f" % cal["spearman_proxy_vs_engine"]) if cal["spearman_proxy_vs_engine"] is not None else "None",
             cal["mean_proxy_bps_per_anchor"], cal["mean_engine_bps_per_anchor"],
             dec["high_seat"]["share_kc"], dec["high_seat"]["share_fc"], dec["high_seat"]["IDENTITY_CLOSES"],
             dist["high_seat"]["king_f10_rank_corr"]["median"], dist["rest"]["king_f10_rank_corr"]["median"],
             dist["high_seat"]["raw_gross"]["median"], dist["rest"]["raw_gross"]["median"],
             dist["high_seat"]["hold_fraction"], dist["rest"]["hold_fraction"]), flush=True)

if __name__ == "__main__":
    main()
    assert os.path.exists(OUT), f"device finished without writing {OUT}"
