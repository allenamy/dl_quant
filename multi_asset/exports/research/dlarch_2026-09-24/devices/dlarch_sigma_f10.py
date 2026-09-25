"""dlarch_sigma_f10.py -- sigma_hat_F10 per segment from the T0 family, and sd(d) once T3 cells exist.

TWO THINGS IT REFUSES TO DO, both because of mistakes made on 2026-09-25:

1. It does not identify a cell by its FILENAME. Each retention receipt is keyed by the `tag` IT reports,
   and the seed is parsed out of that tag. Reading six receipts in glob order and lining them up with a
   remembered seed order is exactly the shape that has bitten this project repeatedly.

2. It does not emit a single sigma_hat_F10. The measured values differ by 11x across segments
   (2025: 6.33, 2026: 0.57), so one number cannot be correct for more than one segment. The decision
   rule consumes a per-segment value; a scalar would silently be either ~5x too blunt or ~11x too sharp
   depending on where it was applied.

WHAT sd(d) IS, and why it is not sigma_hat_F10: the book gate tests the PAIRED difference between T3 and
T0 of the SAME seed. var(d) != var(T0 levels). d_k is recoverable even though the T0 PATH files have been
freed, because the frozen judge's dbar reads only a["A"] and a["r"] and the retained small series carries
both. Two independent routes are computed and required to agree:
  (i)  linearity:  d_k = dbar(T3_k - NC) - dbar(T0_k - NC)   [same pairing, same mask, so terms cancel]
  (ii) direct:     pair the two small series through the frozen dbar
Route (i) alone would be trusting an algebraic identity I asserted; route (ii) alone would be trusting one
reader. Requiring both is the only version that can catch a mistake in either.

usage: dlarch_sigma_f10.py <env-whitelist> <receipts-dir> <out.json>
"""
import os, sys, json, glob, time, hashlib, statistics as st

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
RDIR, OUT = sys.argv[2], sys.argv[3]
SEGS = ["2023H2", "2024", "2025", "pre2026", "2026", "2026_frozen_truncated", "full_window"]
T0_SEEDS = {42, 2027, 7, 11, 23, 101, 3, 5}
T3_SEEDS = {42, 2027, 7}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def collect(pattern, arm):
    """Key every cell by the tag the receipt REPORTS, never by its filename."""
    out = {}
    for d in sorted(glob.glob(os.path.join(RDIR, pattern))):
        fs = glob.glob(os.path.join(d, "RETAIN_*.json"))
        if not fs:
            continue
        r = json.load(open(fs[0]))
        tag = r["tag"]
        assert f"DLARCH_{arm}_s" in tag, f"receipt in {d} reports tag {tag}, which is not a {arm} cell"
        seed = int(tag.split(f"DLARCH_{arm}_s")[1].split("_")[0])
        assert seed not in out, f"two receipts report the same seed {seed} for arm {arm}"
        assert r["ALL_PRECONDITIONS_PASS"], f"{tag}: retention preconditions did NOT pass"
        out[seed] = {"tag": tag, "receipt": fs[0], "receipt_sha256": sha(fs[0]),
                     "dbar": {k: v["mean_bps_per_day"] for k, v in r["dbar_vs_control"].items()},
                     "control_tag": r["control_tag"]}
    return out


t0 = collect("RETAIN_s*_2026-09-25.json", "T0")
t3 = collect("RETAIN_T3_s*_2026-09-25.json", "T3_clamp")
assert set(t0) == T0_SEEDS, f"expected T0 seeds {sorted(T0_SEEDS)}, found {sorted(t0)}"
ctrl = {v["control_tag"] for v in list(t0.values()) + list(t3.values())}
assert len(ctrl) == 1, f"cells were judged against DIFFERENT controls, so their dbars are not comparable: {ctrl}"

sigma, levels = {}, {}
for g in SEGS:
    v = [t0[s]["dbar"][g] for s in sorted(t0)]
    levels[g] = {f"s{s}": t0[s]["dbar"][g] for s in sorted(t0)}
    sigma[g] = {"sigma_hat_F10": st.stdev(v), "mean": st.mean(v), "n": len(v),
                "se_of_mean": st.stdev(v) / (len(v) ** 0.5),
                "all_same_sign": all(x < 0 for x in v) or all(x > 0 for x in v)}

def route_ii(engine_dir):
    """d_k computed DIRECTLY: pair T3's small series against T0's through the frozen judge.

    Nothing about the segment policy is re-derived here. The bounds come from `segments_used` as each
    receipt RECORDS them, and both receipts must agree -- re-implementing "2026 extends to the axis last
    anchor" from its prose description is exactly the mistake this project keeps paying for.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dlarch_cell_retain as CR          # import the helpers, do not copy them
    NS, _BT, _DL = CR.load_frozen(engine_dir)   # returns (NS, BT, DL); unpacking it wrong is how route
                                                # (ii) failed on its first run -- and the device correctly
                                                # refused to quote sd(d) from route (i) alone rather than
                                                # silently falling back to one reader
    import numpy as np
    out = {}
    for seed in sorted(t3):
        rn = json.load(open(t3[seed]["receipt"])); ro = json.load(open(t0[seed]["receipt"]))
        assert rn["segments_used"] == ro["segments_used"], (
            f"seed {seed}: the T3 and T0 receipts record DIFFERENT segment bounds, so their dbars are "
            "not on the same population")
        pn = CR.paths_from_small(np.load(rn["small_series"]["path"], allow_pickle=False))
        po = CR.paths_from_small(np.load(ro["small_series"]["path"], allow_pickle=False))
        assert len(pn) == len(po), f"seed {seed}: path counts differ ({len(pn)} vs {len(po)})"
        A = pn[0]["A"]
        assert np.array_equal(A, po[0]["A"]), f"seed {seed}: T3 and T0 axes differ"
        per = {}
        for g, (lo, hi) in rn["segments_used"].items():
            m = NS.seg_mask(A, lo, hi); days = NS.full_days(A, m)
            db, _D = NS.dbar(pn, po, m, days)
            per[g] = float(1e4 * db.mean())
        out[seed] = per
    return out


sd_d = {}
if set(t3) == T3_SEEDS:
    ii = None
    try:
        ii = route_ii("/dev/shm/news2_2026-09-23/engine")
    except Exception as e:                    # record the failure; never silently fall back to one route
        ii = {"ERROR": f"{type(e).__name__}: {e}"}
    for g in SEGS:
        d1 = {f"s{s}": t3[s]["dbar"][g] - t0[s]["dbar"][g] for s in sorted(t3)}
        d = list(d1.values())
        row = {"d_per_seed_route_i": d1, "mean_d": st.mean(d), "sd_d": st.stdev(d), "n": len(d),
               "route_i": "linearity: dbar(T3-NC) - dbar(T0-NC), same pairing and mask so terms cancel"}
        if isinstance(ii, dict) and "ERROR" not in ii:
            d2 = {f"s{s}": ii[s][g] for s in sorted(t3)}
            worst = max(abs(d1[k] - d2[k]) for k in d1)
            row.update({"d_per_seed_route_ii": d2,
                        "sd_d_route_ii": st.stdev(list(d2.values())),
                        "max_abs_disagreement": worst,
                        "routes_agree": worst < 1e-6,
                        "route_ii": "direct: the two small series paired through the frozen dbar"})
        else:
            row["route_ii"] = ii
            row["routes_agree"] = False
        sd_d[g] = row
    if any(not sd_d[g].get("routes_agree") for g in SEGS):
        sd_d["WARNING"] = ("the two routes do NOT agree (or route ii failed); sd(d) must not be quoted "
                           "until they do -- a single route is one reader, not a check")
else:
    sd_d = {"status": f"T3 cells not complete: have {sorted(t3)}, need {sorted(T3_SEEDS)}",
            "note": "sd(d) is deliberately NOT estimated from a partial family"}

rec = {"device": "dlarch_sigma_f10.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "control": sorted(ctrl)[0], "t0_cells": {str(k): v for k, v in sorted(t0.items())},
       "t3_cells": {str(k): v for k, v in sorted(t3.items())},
       "levels_dbar_vs_control": levels, "sigma_hat_F10_per_segment": sigma, "sd_d": sd_d,
       "no_scalar_sigma": ("deliberately absent. Measured spread across segments is 11x (2025 6.33 vs "
                           "2026 0.57), so a single value would be ~5x too blunt or ~11x too sharp "
                           "depending on the segment it was applied to."),
       "sigma_is_not_sd_d": ("sigma_hat_F10 is the spread of T0 LEVELS against the common control; the "
                             "gate consumes sd of the PAIRED T3-minus-T0 difference. They are different "
                             "quantities and var(d) != var(levels)."),
       "baseline_caveat": ("T0 itself is below the in-service NC book in the 2026 segment on ALL eight "
                           "seeds (mean -1.442, se 0.200), so 'beats T0' in that segment may be 'loses to "
                           "NC by less'. Every T3 readout must carry both columns.")}
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, OUT)
assert json.load(open(OUT)) == rec, "receipt read back differs from what was written"

print("control: %s   T0 cells: %d   T3 cells: %d" % (sorted(ctrl)[0], len(t0), len(t3)))
print("%-24s %9s %9s %9s  %s" % ("segment", "mean", "sigma", "se", "all same sign"))
for g in SEGS:
    s = sigma[g]
    print("%-24s %9.3f %9.4f %9.3f  %s" % (g, s["mean"], s["sigma_hat_F10"], s["se_of_mean"],
                                           s["all_same_sign"]))
print()
if "status" in sd_d:
    print("sd(d):", sd_d["status"])
else:
    print("%-24s %26s %26s %14s %s" % ("segment", "d per seed (route i)", "d per seed (route ii)",
                                       "sd_d", "routes agree"))
    for g in SEGS:
        v = sd_d[g]
        r1 = ",".join("%+.3f" % x for x in v["d_per_seed_route_i"].values())
        r2 = ",".join("%+.3f" % x for x in v.get("d_per_seed_route_ii", {}).values()) or "FAILED"
        print("%-24s %26s %26s %14.4f %s" % (g, r1, r2, v["sd_d"], v.get("routes_agree")))
    if "WARNING" in sd_d:
        print("*** " + sd_d["WARNING"])
print("SIGMA_F10 OK receipt=%s sha256=%s" % (OUT, sha(OUT)[:16]))
