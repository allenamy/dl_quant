"""fa_ladread.py — FRESH gap-carrier ladder readout. PREREG_fresh_gap_carrier_ladder_2026-09-25.md + amendment 1
(a9a5fe8a5). Read-only; consumes only the saved per-path series, so no engine cell is needed.

CALIBER (amendment 1 ruling 2): G and every d use the FROZEN news_stats.dbar -- per-path daily differences first, then
the mean across paths. The device IMPORTS news_stats and calls it, pinning its sha; it does not reimplement it. The old
path-mean-first caliber is computed too and reported AS REFERENCE ONLY, never in a gate.

SEGMENT DEFINITION: frozen by lead in 6cd94f947 (revision 3 of both decision-rule files), which matches what this
device already did and now cites: 2023H2 / 2024 / 2025 / pre2026 take the frozen SEG unchanged; "2026" means
2026-01-01 -> the extended axis last anchor (2026-09-18T20:00Z); full window = pre2026 UNION that 2026; every reading
also reports the frozen-SEG-truncated version beside it; the computation calls the frozen functions and only swaps the
mask.

⚠ SEGMENT TRAP, handled explicitly: news_stats.SEG['2026'] ends 2026-08-31T00:00:00Z, but this ladder runs on the
EXTENDED axis whose last anchor is 2026-09-18T20:00Z. Using SEG['2026'] unchanged would silently drop 09-01..09-18 --
the very window the live drawdown sits in. So the 2026 segment is defined here as 2026-01-01 .. the axis end, and the
SEG-truncated version is reported beside it so the difference is visible rather than hidden.

usage: ... fa_ladread.py WL <out.json>
"""
import os, sys, json, hashlib, time, calendar, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"
ENG = "/dev/shm/news_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
SIGMA = 1.0437          # amendment 1 ruling 3: King random_state perturbation SD, BORROWED as a scale here
ARMS = ("KZ", "WL", "F10", "KZWL")
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
assert NS.BT is not None, "canonical globals not wired"
ts = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
iso = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def paths(f):
    """rebuild the list of path-series dicts the canonical dbar expects, from a saved per-path series"""
    z = np.load(f)
    A = z["anchors"].astype(np.int64)
    r = z["r_per_path"]
    out = [{"A": A, "r": r[k]} for k in range(r.shape[0])]
    ch = {k: z[k + "_per_path"] for k in ("pnl", "car", "cst", "unk", "g")}
    return out, A, ch


rec = {"device": "fa_ladread.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_fresh_gap_carrier_ladder_2026-09-25.md", "amendment_1": "a9a5fe8a5"},
       "segment_definition": {"frozen_by": "6cd94f947 (lead, revision 3 of both decision-rule files)",
                              "2026": "2026-01-01 .. extended axis last anchor (2026-09-18T20:00Z)",
                              "fullwin": "pre2026 UNION the above 2026",
                              "also_reported": "the frozen-SEG-truncated 2026, side by side",
                              "method": "frozen news_stats functions called unchanged; only the mask is swapped"},
       "caliber": {"news_stats.py": NS_SHA, "gate_uses": "frozen news_stats.dbar (per-path daily diff, then mean)",
                   "old_caliber": "path-mean first, then daily compounding -- REFERENCE ONLY, never a gate"},
       "sigma_1.0437": {"source": "news2 4b8723720 PNOISE_DBAR_r1..r7.json",
                        "what_it_is": "sample SD of pre-2026 dbar over 7 King random_state perturbations",
                        "named_limitation": ("this ladder swaps KZ / WL / F10, NOT King's random_state, so this scale is "
                                             "BORROWED. It is not this arm's own noise scale.")},
       "seeds": {}}

for seed in ("42", "2027"):
    fb, A, chb = paths(f"{R}/SER_LAD_BASE_NEWS_s{seed}X.npz")          # baseline = NEW_S
    ff, Af, chf = paths(f"{R}/SER_LAD_BASE_FRESH_s{seed}X.npz")        # FRESH
    assert np.array_equal(A, Af), "FRESH and NEW_S axes differ"
    masks = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]),
             "2026_to_axis_end": NS.seg_mask(A, "2026-01-01T00:00:00Z", iso(A[-1]).replace(" ", "T").replace("Z", ":00Z")),
             "2026_SEG_truncated": NS.seg_mask(A, *NS.SEG["2026"]),
             "fullwin_to_axis_end": NS.seg_mask(A, NS.SEG["2023H2"][0], iso(A[-1]).replace(" ", "T").replace("Z", ":00Z"))}
    days = {k: NS.full_days(A, m) for k, m in masks.items()}
    s = {"axis": {"n": int(len(A)), "first": iso(A[0]), "last": iso(A[-1])},
         "segment_note": {"2026_to_axis_end_anchors": int(masks["2026_to_axis_end"].sum()),
                          "2026_SEG_truncated_anchors": int(masks["2026_SEG_truncated"].sum()),
                          "anchors_SEG_would_drop": int(masks["2026_to_axis_end"].sum() - masks["2026_SEG_truncated"].sum())},
         "G": {}, "arms": {}}

    def dbar_of(pn, po, key):
        db, _ = NS.dbar(pn, po, masks[key], days[key])
        return float(1e4 * db.mean()), int(len(db)), db

    for key in ("pre2026", "2026_to_axis_end", "fullwin_to_axis_end"):
        v, nd, db = dbar_of(ff, fb, key)
        s["G"][key] = {"frozen_dbar_bps_per_day": v, "n_days": nd}
        if key == "pre2026":
            s["G"][key]["boot"] = NS.boot(db, 30)
    # old caliber, reference only
    def old_cal(chA_r, chB_r, key):
        m = masks[key]
        ra = chA_r.mean(0)[m]; rb = chB_r.mean(0)[m]
        ua, da = BT.daily(A[m], ra); ub, dbb = BT.daily(A[m], rb)
        assert np.array_equal(ua, ub)
        return float(1e4 * (da - dbb).mean())
    s["G"]["pre2026_OLD_CALIBER_reference_only"] = old_cal(np.stack([p["r"] for p in ff]),
                                                           np.stack([p["r"] for p in fb]), "pre2026")
    G = s["G"]["pre2026"]["frozen_dbar_bps_per_day"]

    for arm in ARMS:
        f = f"{R}/SER_LAD_{arm}_s{seed}.npz"
        if not os.path.exists(f):
            s["arms"][arm] = {"status": "SERIES MISSING -- arm not run"}; continue
        pa, Aa, cha = paths(f)
        assert np.array_equal(Aa, A), f"{arm} axis differs"
        a = {"series_sha256": sha(f)}
        for key in ("pre2026", "2026_to_axis_end", "fullwin_to_axis_end"):
            v, nd, db = dbar_of(pa, fb, key)
            a[key] = {"d_bps_per_day": v, "n_days": nd}
            if key == "pre2026":
                a[key]["boot"] = NS.boot(db, 30)
        d = a["pre2026"]["d_bps_per_day"]
        a["ratio_d_over_G"] = (d / G) if G != 0 else None
        # frozen criteria, section 4 (lead-authored; applied mechanically)
        if a["ratio_d_over_G"] is not None and a["ratio_d_over_G"] >= 0.5 and abs(d) >= 2 * SIGMA:
            a["VERDICT"] = "CARRIES_MOST_OF_THE_GAP"
        elif abs(d) <= SIGMA:
            a["VERDICT"] = "DOES_NOT_CARRY"
        else:
            a["VERDICT"] = "INDISTINGUISHABLE"
        a["thresholds_used"] = {"d_over_G_ge": 0.5, "abs_d_ge": 2 * SIGMA, "abs_d_le": SIGMA}
        ch = {}
        m = masks["pre2026"]
        for k in ("pnl", "car", "cst", "unk", "g"):
            ch[k] = float((cha[k].mean(0)[m] - chb[k].mean(0)[m]).sum())
        ch["NET_price_minus_funding_paid"] = ch["pnl"] - ch["car"]
        a["channels_pre2026_bps"] = ch
        a["note"] = "a configuration the pipeline cannot produce; this arm is a measuring instrument only"
        s["arms"][arm] = a
    rec["seeds"][seed] = s

# seed reversal check on each arm
rec["seed_reversal"] = {}
for arm in ARMS:
    v = []
    for seed in ("42", "2027"):
        a = rec["seeds"][seed]["arms"].get(arm, {})
        if "pre2026" in a: v.append(a["pre2026"]["d_bps_per_day"])
    if len(v) == 2:
        rec["seed_reversal"][arm] = {"d_s42": v[0], "d_s2027": v[1],
                                     "opposite_sign": bool((v[0] > 0) != (v[1] > 0))}

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_LADREAD  (frozen news_stats.dbar; sigma 1.0437 BORROWED from King perturbation)", flush=True)
for seed in ("42", "2027"):
    s = rec["seeds"][seed]
    print("  s%-5s G(pre2026, frozen) = %+8.4f bps/d  [old caliber %+8.4f, reference only] | 2026 seg would lose %d anchors under SEG"
          % (seed, s["G"]["pre2026"]["frozen_dbar_bps_per_day"], s["G"]["pre2026_OLD_CALIBER_reference_only"],
             s["segment_note"]["anchors_SEG_would_drop"]), flush=True)
    for arm in ARMS:
        a = s["arms"].get(arm, {})
        if a.get("status"):
            print("     %-5s %s" % (arm, a["status"])); continue
        print("     %-5s d=%+8.4f  d/G=%+6.3f  ci95=%s  2026=%+8.4f  NET=%+8.2f  -> %s"
              % (arm, a["pre2026"]["d_bps_per_day"], a["ratio_d_over_G"],
                 [round(x, 2) for x in a["pre2026"]["boot"]["ci95_bps"]],
                 a["2026_to_axis_end"]["d_bps_per_day"], a["channels_pre2026_bps"]["NET_price_minus_funding_paid"],
                 a["VERDICT"]), flush=True)
for arm, v in rec["seed_reversal"].items():
    if v["opposite_sign"]:
        print("  NOTE %s: 又一次按种子翻转 (d = %+.4f vs %+.4f)" % (arm, v["d_s42"], v["d_s2027"]), flush=True)
