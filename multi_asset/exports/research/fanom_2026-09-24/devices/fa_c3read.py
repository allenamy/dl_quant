"""fa_c3read.py — C3 readout. PREREG_step1_C3_rn8_threshold_zero_2026-09-25.md (841240faa); criteria = frozen family
gate b0a3a96cb, so NO VERDICT until n >= 8. This device reports MEMBER-LEVEL facts only.

The item that matters most here is prereg section 2's mandatory one: C3 removes exactly the q0 (most-negative-funding)
shorts, which A2 measured as the HIGHEST-mean bucket over full history. So "the tail improved" must not be reported
without "the expectation was cut". This device therefore measures THE ACTUAL RETURN OF THE REMOVED EXPOSURE:
    removed_w = base_weight - c3_weight   (per anchor, per name)
    realised  = removed_w * Y4            (panel caliber, declared)
bucketed by the funding quintile, so the cost side is a measurement rather than an inference from A2's long-run table.

Two effects point OPPOSITE ways and are reported SEPARATELY (lead 2026-09-25):
  (i)  short exposure removed  -> expected cost
  (ii) preflight gate bites less (publication up) -> overlaps the B1/C2/B3 equivalence class
Net book return alone blends them, so it is never presented alone.

Segment definition frozen by 6cd94f947. dbar is the frozen news_stats.dbar, imported and sha-pinned.

usage: ... fa_c3read.py WL <out.json>
"""
import os, sys, json, hashlib, time, calendar, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"; NC = "/dev/shm/news2_2026-09-23"
ENG = f"{NC}/engine"; PANEL = "/workspace/axis_0919/x0918r/panels/wide_panel_4h_rawbuild_x0918r.npz"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(os.path.join(ENG, "news_stats.py")) == NS_SHA, "news_stats.py is not the frozen caliber"
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL
iso = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def paths(f):
    z = np.load(f)
    A = z["anchors"].astype(np.int64); r = z["r_per_path"]
    return [{"A": A, "r": r[k]} for k in range(r.shape[0])], A, {k: z[k + "_per_path"] for k in ("pnl", "car", "cst", "unk", "g")}


P = np.load(PANEL, allow_pickle=True)
pt = P["ts"].astype(np.int64); Y4 = P["Y4"]; psym = [str(s) for s in P["symbols"]]
pl = {int(t): i for i, t in enumerate(pt)}

rec = {"device": "fa_c3read.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_step1_C3_rn8_threshold_zero_2026-09-25.md", "commit": "841240faa"},
       "criteria": "frozen family gate b0a3a96cb -- NO VERDICT until n >= 8; this file is member-level facts only",
       "segment_definition_frozen_by": "6cd94f947",
       "caliber": {"dbar": "frozen news_stats.dbar (sha pinned)", "per_name_return": "panel Y4 (panel caliber)",
                   "never_mixed": "panel-caliber exposure numbers are never combined with engine g in one statement"},
       "two_effects_reported_separately": {"i": "short exposure removed -> expected cost",
                                           "ii": "gate bites less, publication up -> overlaps B1/C2/B3"},
       "members": {}}

for seed in ("42", "2027"):
    fc = f"{R}/SER_C3_s{seed}.npz"; fb = f"{R}/SER_EXT_NEWS2_s{seed}X.npz"
    if not os.path.exists(fc):
        rec["members"][seed] = {"status": "C3 SERIES MISSING -- arm not run"}; continue
    pv, A, chv = paths(fc); pb, Ab, chb = paths(fb)
    assert np.array_equal(A, Ab), "C3 and baseline axes differ"
    masks = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]),
             "2026": NS.seg_mask(A, "2026-01-01T00:00:00Z", iso(A[-1])),
             "2026_SEG_truncated": NS.seg_mask(A, *NS.SEG["2026"])}
    masks["fullwin"] = masks["pre2026"] | masks["2026"]
    days = {k: NS.full_days(A, m) for k, m in masks.items()}
    m = {"series": {"c3": sha(fc), "baseline": sha(fb)}, "segments": {}, "channels": {}}
    for k in ("fullwin", "pre2026", "2026", "2026_SEG_truncated"):
        db, _ = NS.dbar(pv, pb, masks[k], days[k])
        e = {"d_bps_per_day": float(1e4 * db.mean()), "n_days": int(len(db)), "n_windows": int(masks[k].sum())}
        if k in ("fullwin", "pre2026"):
            e["boot"] = NS.boot(db, 30)
        m["segments"][k] = e
    m["segments"]["2026_definition_effect"] = {
        "extended_minus_truncated": m["segments"]["2026"]["d_bps_per_day"] - m["segments"]["2026_SEG_truncated"]["d_bps_per_day"],
        "sign_flips": bool((m["segments"]["2026"]["d_bps_per_day"] > 0) != (m["segments"]["2026_SEG_truncated"]["d_bps_per_day"] > 0)),
        "reading_near_zero_caveat": "if |reading| <= ~0.3 neither boundary may be cited alone"}
    for k in ("fullwin", "pre2026", "2026"):
        msk = masks[k]
        ch = {c: float((chv[c].mean(0)[msk] - chb[c].mean(0)[msk]).sum()) for c in ("pnl", "car", "cst", "unk", "g")}
        ch["NET_price_minus_funding_paid"] = ch["pnl"] - ch["car"]
        m["channels"][k] = ch

    # ---- mandatory: the ACTUAL realised return of the exposure C3 removes, by funding quintile ----
    CB = np.load(f"{NC}/work/combo_s{seed}/scaled_diagnostic.npz", allow_pickle=True)
    CV = np.load(f"/dev/shm/fanom_2026-09-24/c3/C3_s{seed}/scaled_diagnostic.npz", allow_pickle=True)
    ce = CB["E_ts"].astype(np.int64)
    assert np.array_equal(ce, CV["E_ts"].astype(np.int64)), "combo axes differ"
    L = np.load(f"{NC}/work/legs.npz"); lt = L["E_ts"].astype(np.int64); RN8 = L["RN8"]
    lpos = {int(t): i for i, t in enumerate(lt)}
    wb = np.asarray(CB["weights"], float); wv = np.asarray(CV["weights"], float)
    QB = 5
    agg = {q: {"n": 0, "removed_abs_w": 0.0, "realised_bps": 0.0, "n_pos": 0} for q in range(QB)}
    n_anch = 0
    t0 = calendar.timegm(time.strptime(NS.SEG["pre2026"][0], "%Y-%m-%dT%H:%M:%SZ"))
    for i, t in enumerate(ce):
        if int(t) < t0: continue
        j = lpos.get(int(t)); k = pl.get(int(t))
        if j is None or k is None: continue
        dw = wb[i] - wv[i]                      # exposure C3 removed (positive where base was long, negative where short)
        sel = np.abs(dw) > 1e-12
        if not sel.any(): continue
        n_anch += 1
        r8 = RN8[j]; y = Y4[k]
        ok = sel & np.isfinite(r8) & np.isfinite(y)
        if ok.sum() < QB: continue
        rr = r8[ok]
        q = np.argsort(np.argsort(rr)) * QB // max(1, ok.sum())
        contrib = dw[ok] * y[ok] * 1e4          # realised bps of the removed exposure (panel caliber)
        for b in range(QB):
            s_ = q == b
            if not s_.any(): continue
            a = agg[b]
            a["n"] += int(s_.sum()); a["removed_abs_w"] += float(np.abs(dw[ok][s_]).sum())
            a["realised_bps"] += float(contrib[s_].sum()); a["n_pos"] += int((contrib[s_] > 0).sum())
    m["removed_exposure_pre2026"] = {
        "anchors_with_removal": n_anch,
        "note": ("realised = (base_weight - C3_weight) * panel Y4, in bps. POSITIVE means the removed exposure WAS "
                 "making money, i.e. C3 gave up profit. q0 = most negative funding rate."),
        "buckets": {str(b): ({"n_cells": agg[b]["n"], "removed_abs_weight": agg[b]["removed_abs_w"],
                              "realised_bps": agg[b]["realised_bps"],
                              "realised_bps_per_cell": agg[b]["realised_bps"] / agg[b]["n"],
                              "frac_cells_profitable": agg[b]["n_pos"] / agg[b]["n"]}
                             if agg[b]["n"] else {"n_cells": 0}) for b in range(QB)}}
    m["removed_exposure_pre2026"]["total_realised_bps"] = sum(agg[b]["realised_bps"] for b in range(QB))
    rec["members"][seed] = m

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_C3READ (member-level only; family gate needs n>=8 -> NO VERDICT)", flush=True)
for seed, m in rec["members"].items():
    if m.get("status"): print("  s%-5s %s" % (seed, m["status"])); continue
    s = m["segments"]; c = m["channels"]
    print("  s%-5s fullwin d=%+8.4f ci95=%s | pre2026 %+8.4f | 2026 %+8.4f (SEG-trunc %+8.4f%s)"
          % (seed, s["fullwin"]["d_bps_per_day"], [round(x, 2) for x in s["fullwin"]["boot"]["ci95_bps"]],
             s["pre2026"]["d_bps_per_day"], s["2026"]["d_bps_per_day"], s["2026_SEG_truncated"]["d_bps_per_day"],
             " FLIP" if s["2026_definition_effect"]["sign_flips"] else ""), flush=True)
    print("        channels pre2026 (bps): dPrice %+8.1f  dFundPaid %+8.1f  dFee %+7.1f  NET %+8.1f  dG %+8.1f"
          % (c["pre2026"]["pnl"], c["pre2026"]["car"], c["pre2026"]["cst"],
             c["pre2026"]["NET_price_minus_funding_paid"], c["pre2026"]["g"]), flush=True)
    re_ = m["removed_exposure_pre2026"]
    print("        REMOVED EXPOSURE, realised bps by funding quintile (q0 = most negative; + means C3 gave up profit):", flush=True)
    for b in range(5):
        v = re_["buckets"][str(b)]
        if not v.get("n_cells"): continue
        print("          q%d n=%8d  realised %+10.1f bps  (%+.5f /cell)  frac profitable %.3f"
              % (b, v["n_cells"], v["realised_bps"], v["realised_bps_per_cell"], v["frac_cells_profitable"]), flush=True)
    print("          TOTAL removed-exposure realised: %+.1f bps over %d anchors" % (re_["total_realised_bps"], re_["anchors_with_removal"]), flush=True)
