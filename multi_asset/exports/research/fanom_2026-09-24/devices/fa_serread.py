"""fa_serread.py — GENERAL arm readout from saved per-path series. No engine cell needed.

Why general rather than one device per arm: the per-arm readers (fa_b4read / fa_c3read / fa_ladread) each re-derive the
same segment handling, and a defect in it had to be fixed in each copy. This device is the class-shaped version: it
takes (label, variant series, baseline series) triples and reports the same frozen-caliber table for each.

CALIBER: the FROZEN news_stats.py (sha pinned below) is IMPORTED and CALLED -- dbar / seg_mask / full_days / boot.
Reimplementing it from its description is what produced correction W-1 (my version averaged across paths first; the
canonical dbar takes per-path daily differences THEN averages across paths).

SEGMENTS: frozen by lead in 6cd94f947. pre2026 takes the frozen SEG unchanged; "2026" = 2026-01-01 .. the axis's last
anchor; full window = pre2026 UNION that 2026. The SEG-TRUNCATED 2026 is reported BESIDE every reading, because
SEG['2026'] ends 2026-08-31 and the extended axis runs to 09-18 -- truncating silently drops the live-drawdown window
and has already been shown to FLIP a sign (+0.0767 vs -0.2949 on a same-axis stand-in).

NO VERDICT. This device reports member-level facts. Admission is the frozen family gate's business (n >= 8), and arms
the lead designated diagnostic never get one at all.

usage: ... fa_serread.py WL <out.json> <label>:<variant.npz>:<baseline.npz> [...]
"""
import os, sys, json, hashlib, time, calendar, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT, SPECS = sys.argv[2], sys.argv[3:]
ENG = "/dev/shm/news2_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
KEYS = ("pre2026", "2026_to_axis_end", "2026_SEG_truncated", "fullwin_to_axis_end")
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(os.path.join(ENG, "news_stats.py")) == NS_SHA, "news_stats.py is not the frozen caliber"
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL          # news_stats sets BT = DL = None at module level and wires them inside main()
assert NS.BT is not None and NS.DL is not None, "canonical globals not wired"
iso = lambda t: datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def paths(f):
    z = np.load(f)
    A = z["anchors"].astype(np.int64)
    r = z["r_per_path"]
    ch = {k: z[k + "_per_path"] for k in ("pnl", "car", "cst", "unk", "g")}
    return [{"A": A, "r": r[k]} for k in range(r.shape[0])], A, ch


rec = {"device": "fa_serread.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "caliber": {"news_stats.py": NS_SHA, "method": "frozen news_stats.dbar IMPORTED and CALLED, not reimplemented"},
       "segment_definition": {"frozen_by": "6cd94f947 (lead)", "2026": "2026-01-01 .. axis last anchor",
                              "fullwin": "pre2026 UNION that 2026",
                              "also_reported": "the frozen-SEG-truncated 2026, beside every reading"},
       "verdict_policy": "NONE — member-level facts only; admission is the family gate's business (n >= 8)",
       "arms": {}}

for spec in SPECS:
    label, vp, bp = spec.split(":")
    if not (os.path.exists(vp) and os.path.exists(bp)):
        rec["arms"][label] = {"status": "SERIES MISSING", "variant": vp, "baseline": bp}
        print("  %-16s SERIES MISSING" % label, flush=True); continue
    pv, A, chv = paths(vp)
    pb, Ab, chb = paths(bp)
    assert np.array_equal(A, Ab), f"{label}: variant and baseline axes differ"
    end = iso(A[-1])
    masks = {"pre2026": NS.seg_mask(A, *NS.SEG["pre2026"]),
             "2026_to_axis_end": NS.seg_mask(A, "2026-01-01T00:00:00Z", end),
             "2026_SEG_truncated": NS.seg_mask(A, *NS.SEG["2026"]),
             "fullwin_to_axis_end": NS.seg_mask(A, NS.SEG["2023H2"][0], end)}
    days = {k: NS.full_days(A, m) for k, m in masks.items()}
    a = {"variant": vp, "variant_sha256": sha(vp), "baseline": bp, "baseline_sha256": sha(bp),
         "axis": {"n": int(len(A)), "first": iso(A[0]), "last": end, "n_paths": len(pv)},
         "segment_note": {"2026_to_axis_end_anchors": int(masks["2026_to_axis_end"].sum()),
                          "2026_SEG_truncated_anchors": int(masks["2026_SEG_truncated"].sum()),
                          "anchors_SEG_would_drop": int(masks["2026_to_axis_end"].sum() - masks["2026_SEG_truncated"].sum())}}
    for k in KEYS:
        db, _ = NS.dbar(pv, pb, masks[k], days[k])
        a[k] = {"d_bps_per_day": float(1e4 * db.mean()), "n_days": int(len(db)),
                "n_windows": int(masks[k].sum()), "boot_ci95_bps": NS.boot(db, 30)["ci95_bps"]}
    a["2026_definition_effect"] = {
        "extended_minus_truncated": a["2026_to_axis_end"]["d_bps_per_day"] - a["2026_SEG_truncated"]["d_bps_per_day"],
        "sign_flips": bool((a["2026_to_axis_end"]["d_bps_per_day"] > 0) != (a["2026_SEG_truncated"]["d_bps_per_day"] > 0))}
    # channels, per segment. identity g = pnl - car - cst - unk (news_stats L134); car = funding PAID (L131, car>0 = paid)
    a["channels_bps"] = {}
    for k in ("pre2026", "2026_to_axis_end"):
        m = masks[k]; c = {}
        for f in ("pnl", "car", "cst", "unk", "g"):
            c[f] = float((chv[f].mean(0)[m] - chb[f].mean(0)[m]).sum())
        c["NET_price_minus_funding_paid"] = c["pnl"] - c["car"]
        c["identity_resid_g_minus_pnl_car_cst_unk"] = c["g"] - (c["pnl"] - c["car"] - c["cst"] - c["unk"])
        a["channels_bps"][k] = c
    rec["arms"][label] = a
    print("  %-16s pre2026 %+8.4f ci%s | 2026 %+8.4f (SEG-trunc %+8.4f%s) | full %+8.4f | Δfund_paid %+9.2f"
          % (label, a["pre2026"]["d_bps_per_day"], [round(x, 2) for x in a["pre2026"]["boot_ci95_bps"]],
             a["2026_to_axis_end"]["d_bps_per_day"], a["2026_SEG_truncated"]["d_bps_per_day"],
             " SIGNFLIP" if a["2026_definition_effect"]["sign_flips"] else "",
             a["fullwin_to_axis_end"]["d_bps_per_day"], a["channels_bps"]["2026_to_axis_end"]["car"]), flush=True)

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_SERREAD arms=%d out=%s" % (len(rec["arms"]), OUT), flush=True)
