#!/usr/bin/env python3
"""c0_supp.py — stream C0 SUPPLEMENT (added AFTER §1 was frozen and AFTER the §2 cohort numbers of c0_attrib.py ec8de310 were seen;
labelled as such in docs/RESULT_c0_attribution_2026-09-19.md §3). It changes no frozen cohort, window or accounting; it only splits the
frozen per-name price term into a market part and a selection part, because the §2 side totals turned out to be dominated by the common
market move (e.g. 2025-02 long −6.30 / short +6.57), so "which side failed" is unreadable without it.

Split (exact identity per name and anchor; members m, device accounting of c0_lib.per_name):
  ybar_E       = equal-weight mean of y4 over the anchor's members with finite y4 (the member universe's 4h return)
  market_k     = smr_k · ybar_E · 1e4            (the name's position times the universe move)
  selection_k  = smr_k · (y4_k − ybar_E) · 1e4   (the name's return relative to the universe, signed by the position)
  names with NaN y4 (price 0 in the device) get market = selection = 0  ⇒  price_k = market_k + selection_k exactly.
Per side the market parts sum to ybar · (Σ_side smr) (long > 0, short < 0), so long market + short market = ybar · net exposure.
Basket returns (per anchor, then window mean, bps per 4h): r_long = Σ_long smr·y / Σ_long smr; r_short = Σ_short |smr|·y / Σ_short |smr|
(the average 4h return of the names the book is SHORT: positive = shorted names rose); ybar; and both minus ybar.
Same windows, cohorts and units as c0_attrib.py (judge units: ÷ gross_total, mean over the window's anchors); both seeds.
Also: per-name selection concentration for 2026-04/06/07/08 and 2026H1 (worst 10, best 10, body = the rest); per-UTC-day market / selection /
carry / fee / net for 2026-07 and 2026-08; and ONE post-hoc cut, chosen after reading the August day series (so it is description, not a
test): August split into RALLY6 = 2026-08-19..08-24 (the six consecutive negative-selection days that hold the month's whole universe move)
and REST, selection by side × frozen cohort and the worst / best 10 names of each part.
usage: python c0_supp.py <OUT_DIR> <CHARS_NPZ>
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c0_lib as L

T0 = time.time(); OUT = sys.argv[1]; CHARS = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
CHARS_SHA = "403957a21ff7d4be7f06c1c1a038a2b841bb14a567fade1181b3faa29d89c5be"
chk = L.Checks(T0)
rec = {"device": "c0_supp.py", "self_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": L.utc(time.time())}
rec["inputs"] = L.verify_inputs(chk, L.INPUTS)
got = L.sha(CHARS); rec["inputs"]["CHARS"] = {"path": CHARS, "sha256": got}; chk("input_sha.CHARS", got == CHARS_SHA)
# the frozen labelling functions are imported from the committed attribution device text, not re-typed
ATT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c0_attrib.py"); rec["attrib_device_sha256"] = L.sha(ATT)
chk("attrib_device_is_the_frozen_ec8de310", rec["attrib_device_sha256"].startswith("ec8de310"))
if chk.fails:
    json.dump(rec | {"checks": chk.rows, "failed": chk.fails, "VERDICT": "REFUSED"}, open(f"{OUT}/RECEIPT_c0_supp.json", "w"), indent=1); sys.exit(3)
src = open(ATT).read(); a0 = src.index("def lab_fixed_age"); a1 = src.index("CHAR_DEF = {")
C = L.load_common(chk)
Z = np.load(CHARS, allow_pickle=True); AX = Z["ts"].astype(np.int64); NA_ = len(AX); MEMB = Z["member"]
ns = {"np": np, "MEMB": MEMB}; exec(src[a0:a1], ns)
CHAR_DEF = {"AGE": (ns["lab_fixed_age"](Z["AGE"].astype(np.float64)), ["<90d", "90-180d", "180-365d", "365-730d", ">=730d"]),
            "FUND": (ns["lab_fund"](Z["RN8"].astype(np.float64)), ["<=-10bp", "(-10,0)bp", "[0,base)", "base 1bp", "(base,5]bp", ">5bp"]),
            "MOM7": (ns["lab_terc"](Z["MOM7"]), ["L", "M", "H"]), "MOM30": (ns["lab_terc"](Z["MOM30"]), ["L", "M", "H"]),
            "LIQ": (ns["lab_terc"](Z["LIQ"]), ["L", "M", "H"]), "TBF": (ns["lab_terc"](Z["TBF"]), ["L", "M", "H"]),
            "FSIG": (ns["lab_fsig"](Z["FSIG"].astype(np.float64)), ["bottom", "mid", "top"])}
mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in AX]); months = sorted(set(mon.tolist()))
WINDOWS = {**{m_: mon == m_ for m_ in months}, "2025": np.char.startswith(mon, "2025"), "2026H1": np.isin(mon, ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]),
           "ALL": np.ones(NA_, bool)}
res = {"definitions": __doc__, "seeds": {}}
for seed in L.SEEDS:
    A = L.load_arm(seed, chk); R = A["R"]; cols = A["cols"]; ts = R[:, 0].astype(np.int64); col = lambda n: R[:, cols.index(n)]
    rows = np.nonzero((ts >= AX[0]) & (ts <= AX[-1]))[0]; chk(f"s{seed}.axis", bool(np.array_equal(ts[rows], AX)))
    keep = np.zeros(len(ts), bool); keep[rows] = True; keep[rows[0] - 1] = True
    P, S = L.per_name(A, C, keep_rows=keep)
    smr_all = P["smr"]; prev_side = np.sign(smr_all[0]); smr = smr_all[1:]; inm = P["inm"][1:]
    gt = col("gross_total")[rows]
    Y = np.full((NA_, L.NW), np.nan)
    for a, E in enumerate(AX):
        i = C["mrow"][int(E)]; Y[a] = np.where(inm[a], C["y4"][i].astype(np.float64), np.nan)
    fin = np.isfinite(Y) & inm
    ybar = np.array([Y[a, fin[a]].mean() if fin[a].any() else 0.0 for a in range(NA_)])
    MK = np.where(fin, smr * ybar[:, None] * 1e4, 0.0) / gt[:, None]
    SEL = np.where(fin, smr * (np.where(fin, Y, 0.0) - ybar[:, None]) * 1e4, 0.0) / gt[:, None]
    Pn = P["price"][1:] / gt[:, None]
    d = np.abs(MK + SEL - Pn); chk(f"s{seed}.identity_price_eq_market_plus_selection", bool((d <= 1e-9 * np.maximum(1, np.abs(Pn))).all()), {"max_abs": float(d.max())})
    sgn = np.sign(smr); prv = np.vstack([prev_side[None, :], np.sign(smr[:-1])]); sgn = np.where(sgn == 0, prv, sgn); valid = inm & (sgn != 0)
    LONG = valid & (sgn > 0); SHORT = valid & (sgn < 0)
    # basket returns per anchor (bps per 4h)
    wl = np.where(fin & (smr > 0), smr, 0.0); ws = np.where(fin & (smr < 0), -smr, 0.0); Yz = np.where(fin, Y, 0.0)
    with np.errstate(all="ignore"):
        rL = (wl * Yz).sum(1) / wl.sum(1) * 1e4; rS = (ws * Yz).sum(1) / ws.sum(1) * 1e4
    sr = {"windows": {}}
    for wn, W in WINDOWS.items():
        N = int(W.sum())
        w = {"N": N, "ybar_bps_per_4h": float(ybar[W].mean() * 1e4), "r_long_basket": float(np.nanmean(rL[W])), "r_short_basket": float(np.nanmean(rS[W])),
             "r_long_minus_ybar": float(np.nanmean(rL[W] - ybar[W] * 1e4)), "r_short_minus_ybar": float(np.nanmean(rS[W] - ybar[W] * 1e4)),
             "net_exposure_over_gross": float((np.where(valid, smr, 0).sum(1) / gt)[W].mean()),
             "sides": {sd: {"price": float(np.where(M_ & W[:, None], Pn, 0).sum() / N), "market": float(np.where(M_ & W[:, None], MK, 0).sum() / N),
                            "selection": float(np.where(M_ & W[:, None], SEL, 0).sum() / N)} for sd, M_ in (("long", LONG), ("short", SHORT))}, "chars": {}}
        for cn, (lab, names) in CHAR_DEF.items():
            t = {"codes": ["NA"] + names}
            for nm, X in (("market", MK), ("selection", SEL)):
                t[nm] = {}
                for sd, M_ in (("long", LONG), ("short", SHORT)):
                    ko = M_ & W[:, None]
                    t[nm][sd] = (np.bincount((lab.astype(np.int64) + 1)[ko], weights=X[ko], minlength=len(names) + 1) / N).tolist()
            w["chars"][cn] = t
        sr["windows"][wn] = w
    # August per-name selection concentration (short side and long side)
    for wn in ("2026-04", "2026-06", "2026-07", "2026-08", "2026H1"):
        W = WINDOWS[wn]; N = int(W.sum())
        for sd, M_ in (("long", LONG), ("short", SHORT)):
            v = np.where(M_ & W[:, None], SEL, 0).sum(0) / N; s_ = np.sort(v)
            sr["windows"][wn][f"{sd}_selection_per_name"] = {"total": float(v.sum()), "worst10": float(s_[:10].sum()), "best10": float(s_[-10:].sum()), "body_ex_worst10_best10": float(v.sum() - s_[:10].sum() - s_[-10:].sum()),
                                                            "n_neg": int((v < 0).sum()), "n_pos": int((v > 0).sum()),
                                                            "worst10_names": [[C["SYM"][k], float(v[k])] for k in np.argsort(v)[:10]]}
    # per UTC day (contribution to the month mean, like c0_attrib days): market and selection by side, carry, net — 2026-07 and 2026-08
    dayv = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in AX])
    Cn = P["carry"][1:] / gt[:, None]; Fn = P["fee"][1:] / gt[:, None]
    sr["days"] = {}
    for wn in ("2026-07", "2026-08"):
        W = WINDOWS[wn]; N = int(W.sum()); dd = {}
        for dy in sorted(set(dayv[W].tolist())):
            Wd = (W & (dayv == dy))[:, None]
            dd[dy] = {"ybar_bps_per_4h": float(ybar[W & (dayv == dy)].mean() * 1e4),
                      **{f"{nm}_{sd}": float(np.where(M_ & Wd, X, 0).sum() / N) for nm, X in (("market", MK), ("selection", SEL)) for sd, M_ in (("long", LONG), ("short", SHORT))},
                      "carry": float(np.where(valid & Wd, Cn, 0).sum() / N), "fee": float(np.where(valid & Wd, Fn, 0).sum() / N),
                      "net": float(np.where(valid & Wd, Pn - Cn - Fn, 0).sum() / N)}
        sr["days"][wn] = dd
    # POST-HOC cut (chosen AFTER reading the August day series: 6 consecutive negative-selection days that hold the whole month's universe move):
    # 2026-08 split into RALLY6 = 2026-08-19..08-24 and REST = the other August days; values are contributions to the AUGUST mean (the two sum to August)
    WA = WINDOWS["2026-08"]; NA8 = int(WA.sum()); r6 = WA & (dayv >= "2026-08-19") & (dayv <= "2026-08-24"); rest = WA & ~r6
    sr["aug_split_posthoc"] = {"definition": "RALLY6 = UTC days 2026-08-19..2026-08-24 (post hoc); REST = other 2026-08 days; contributions to the August mean", "n_anchors": {"RALLY6": int(r6.sum()), "REST": int(rest.sum())}}
    for pn, Wp in (("RALLY6", r6), ("REST", rest)):
        dct = {"ybar_bps_per_4h": float(ybar[Wp].mean() * 1e4), "chars": {}}
        for cn, (lab, names) in CHAR_DEF.items():
            dct["chars"][cn] = {"codes": ["NA"] + names, **{sd: (np.bincount((lab.astype(np.int64) + 1)[M_ & Wp[:, None]], weights=SEL[M_ & Wp[:, None]], minlength=len(names) + 1) / NA8).tolist()
                                                           for sd, M_ in (("long", LONG), ("short", SHORT))}}
        for sd, M_ in (("long", LONG), ("short", SHORT)):
            v = np.where(M_ & Wp[:, None], SEL, 0).sum(0) / NA8; o = np.argsort(v)
            dct[f"{sd}_selection_total"] = float(v.sum()); dct[f"{sd}_worst10"] = [[C["SYM"][k], float(v[k])] for k in o[:10]]; dct[f"{sd}_best10"] = [[C["SYM"][k], float(v[k])] for k in o[::-1][:10]]
            dct[f"{sd}_worst10_sum"] = float(v[o[:10]].sum()); dct[f"{sd}_best10_sum"] = float(v[o[::-1][:10]].sum())
        sr["aug_split_posthoc"][pn] = dct
    res["seeds"][f"A0_s{seed}"] = sr
    chk.log("seed done", seed)
json.dump(res, open(f"{OUT}/C0_SUPP.json", "w"), indent=0, default=float)
f2 = lambda x: f"{x:+.2f}"
Lm = [f"# C0 supplement (POST-FREEZE, c0_supp.py {rec['self_sha256'][:8]}): price = market + selection; basket returns", "",
      "market = position × universe 4h return (equal-weight member mean ybar); selection = position × (own return − ybar). Judge units (÷ gross_total, window mean).",
      "Basket returns: bps per 4h, average return of the names held long / held short (positive r_short = shorted names ROSE).", ""]
for sk, sr in res["seeds"].items():
    Lm += [f"## {sk}", "", "| window | N | ybar | r_long | r_short | r_long−ybar | r_short−ybar | net exp/gross | long price | long market | long selection | short price | short market | short selection |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for wn, w in sr["windows"].items():
        l_ = w["sides"]["long"]; s_ = w["sides"]["short"]
        Lm.append(f"| {wn} | {w['N']} | {f2(w['ybar_bps_per_4h'])} | {f2(w['r_long_basket'])} | {f2(w['r_short_basket'])} | {f2(w['r_long_minus_ybar'])} | {f2(w['r_short_minus_ybar'])} | {w['net_exposure_over_gross']:+.3f} | "
                  f"{f2(l_['price'])} | {f2(l_['market'])} | {f2(l_['selection'])} | {f2(s_['price'])} | {f2(s_['market'])} | {f2(s_['selection'])} |")
    Lm.append("")
    for cn in CHAR_DEF:
        codes = sr["windows"]["ALL"]["chars"][cn]["codes"]; hdr = [f"L:{c}" for c in codes] + [f"S:{c}" for c in codes]
        Lm += [f"### {sk} · {cn} · selection", "", "| window | " + " | ".join(hdr) + " |", "|---|" + "---|" * len(hdr)]
        for wn, w in sr["windows"].items():
            t = w["chars"][cn]["selection"]; Lm.append(f"| {wn} | " + " | ".join(f2(v) for v in t["long"] + t["short"]) + " |")
        Lm.append("")
    Lm += [f"### {sk} · per-name selection concentration", "", "| window.side | total | worst10 | best10 | body (total − worst10 − best10) | names <0 | names >0 | worst 10 names |", "|---|---|---|---|---|---|---|---|"]
    for wn in ("2026H1", "2026-04", "2026-06", "2026-07", "2026-08"):
        for sd in ("long", "short"):
            c_ = sr["windows"][wn][f"{sd}_selection_per_name"]
            Lm.append(f"| {wn}.{sd} | {f2(c_['total'])} | {f2(c_['worst10'])} | {f2(c_['best10'])} | {f2(c_['body_ex_worst10_best10'])} | {c_['n_neg']} | {c_['n_pos']} | " + ", ".join(f"{n} {v:+.2f}" for n, v in c_["worst10_names"]) + " |")
    Lm.append("")
    for wn, dd in sr["days"].items():
        Lm += [f"### {sk} · {wn} by day (contribution to the month mean)", "", "| day | ybar bps/4h | market long | market short | selection long | selection short | carry | fee | net |", "|---|---|---|---|---|---|---|---|---|"]
        for dy, v in dd.items():
            Lm.append(f"| {dy} | {f2(v['ybar_bps_per_4h'])} | {f2(v['market_long'])} | {f2(v['market_short'])} | {f2(v['selection_long'])} | {f2(v['selection_short'])} | {f2(v['carry'])} | {f2(v['fee'])} | {f2(v['net'])} |")
        Lm.append("")
    ap = sr["aug_split_posthoc"]
    Lm += [f"### {sk} · POST-HOC August split: RALLY6 (08-19..08-24, {ap['n_anchors']['RALLY6']} anchors) vs REST ({ap['n_anchors']['REST']} anchors); selection, contributions to the August mean", "",
           f"ybar bps/4h: RALLY6 {f2(ap['RALLY6']['ybar_bps_per_4h'])} · REST {f2(ap['REST']['ybar_bps_per_4h'])}; selection long/short: RALLY6 {f2(ap['RALLY6']['long_selection_total'])} / {f2(ap['RALLY6']['short_selection_total'])} · REST {f2(ap['REST']['long_selection_total'])} / {f2(ap['REST']['short_selection_total'])}", ""]
    for cn in CHAR_DEF:
        codes = ap["RALLY6"]["chars"][cn]["codes"]; hdr = [f"L:{c}" for c in codes] + [f"S:{c}" for c in codes]
        Lm += [f"| {cn} part | " + " | ".join(hdr) + " |", "|---|" + "---|" * len(hdr)]
        for pn in ("RALLY6", "REST"):
            t = ap[pn]["chars"][cn]; Lm.append(f"| {pn} | " + " | ".join(f2(v) for v in t["long"] + t["short"]) + " |")
        Lm.append("")
    for pn in ("RALLY6", "REST"):
        for sd in ("long", "short"):
            Lm.append(f"- {pn} {sd}: worst10 {f2(ap[pn][sd + '_worst10_sum'])} (" + ", ".join(f"{n} {v:+.2f}" for n, v in ap[pn][sd + "_worst10"]) + f"); best10 {f2(ap[pn][sd + '_best10_sum'])} (" + ", ".join(f"{n} {v:+.2f}" for n, v in ap[pn][sd + "_best10"]) + ")")
    Lm.append("")
open(f"{OUT}/C0_SUPP_TABLES.md", "w").write("\n".join(Lm) + "\n")
rec["outputs"] = {k: {"path": f"{OUT}/{k}", "sha256": L.sha(f"{OUT}/{k}")} for k in ("C0_SUPP.json", "C0_SUPP_TABLES.md")}
rec.update({"checks": chk.rows, "n_checks": len(chk.rows), "failed": chk.fails, "VERDICT": "PASS" if not chk.fails else "FAIL", "runtime_s": round(time.time() - T0, 1), "utc_end": L.utc(time.time())})
json.dump(rec, open(f"{OUT}/RECEIPT_c0_supp.json", "w"), indent=1, default=str)
chk.log("VERDICT", rec["VERDICT"], "failed", chk.fails)
sys.exit(0 if not chk.fails else 3)
