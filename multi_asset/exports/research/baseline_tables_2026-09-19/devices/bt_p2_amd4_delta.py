#!/usr/bin/env python3
"""bt_p2_amd4_delta.py — reconciles the PRE-FIX reading-P2 receipts (commit ec00bbb75) against the AMENDMENT 4 ones, and produces the
"which published numbers moved, and by how much" table.

Two jobs, and the first one gates the second:

  REPRODUCTION (must pass, or the delta table means nothing) — the fix must not have changed any arithmetic, only the reading:
    R1  per path: wherever the new device says the path HAS a measurement, its window-end return must equal the old one bit for bit;
        wherever it says the path has NONE, the old receipt must have carried exactly 0.0 there — that substitution IS E-0920-C, and
        this check pins it as the whole of the difference.
    R2  per (run, base, H): the old summary mean must equal the new W_CARRY `whole_population` mean bit for bit — i.e. the old caliber
        is exactly "W_CARRY with the flat-book convention", now labelled instead of implicit.
    R3  the same for every quarterly start.
    R4  the old breach counts must equal the new W_CARRY counts (old counted an unmeasured path as "did not breach"; the new receipt
        reports it as not-applicable, so old n_true must equal new n_true and old 32 must equal new n_asked + n_not_applicable).

  DELTA — for every published cell, the OLD number, the MAIN reading now (W_ENTRY, measured subset) and the difference in percentage
    points, plus the size of the no-measurement subset that caused it.

usage: /usr/bin/python3 bt_p2_amd4_delta.py <old_dir> <new_dir> <out.json>
       (old_dir / new_dir each hold BT_P2_READING_{A0,A0ext,V4}.json)
"""
import json, os, sys, time, hashlib

def CUTCELL(cell):
    """E-0921-B: the quarterly-start cell now holds BOTH readings. This delta compares against the PRE-AMENDMENT-4 device,
    whose single number was the one truncated at the configured breach_by, so the like-for-like operand is the cutoff
    reading. A cell that predates the split is returned unchanged so an old receipt still compares."""
    k = [x for x in cell if x.startswith("breach_by_")]
    return cell[k[0]] if k else cell



T0 = time.time()
OLD, NEW, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]
ARMS = ("A0", "A0ext", "V4")
RES, DELTA = [], []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def one_value(x):
    """a single published statistic: since 2026-09-21 (round-7 G-05) it is a bt_agg.one_value_block carrying its own n_eff, and
    before that it was a bare scalar. Both shapes compare, so this delta still reads receipts written on either side of that fix."""
    return x.get("value") if isinstance(x, dict) else x


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    if not cond: print("FAIL " + name, json.dumps(detail, default=str)[:300], flush=True)


def eq(a, b):
    if a is None or b is None: return a is b or a == b
    return a == b


for arm in ARMS:
    o = json.load(open(os.path.join(OLD, f"BT_P2_READING_{arm}.json")))
    n = json.load(open(os.path.join(NEW, f"BT_P2_READING_{arm}.json")))
    ok(f"{arm}.the two receipts describe the same runs", sorted(o["runs"]) == sorted(n["runs"]), {"old": sorted(o["runs"]), "new": sorted(n["runs"])})
    for lbl in o["runs"]:
        O, N = o["runs"][lbl], n["runs"][lbl]
        ok(f"{arm}.{lbl}.same window and path count", O["window"] == N["window"] and O["n_paths"] == N["n_paths"],
           {"old": [O["window"], O["n_paths"]], "new": [N["window"], N["n_paths"]]})
        for bn in O["bases"]:
            for H in O["bases"][bn]:
                op, np_ = O["bases"][bn][H]["per_path"], N["bases"][bn][H]["W_CARRY"]["per_path"]
                bad = []
                for a, b in zip(sorted(op, key=lambda x: x["seed"]), sorted(np_, key=lambda x: x["seed"])):
                    if b["has_measurement"]:
                        if not eq(a["end_return_P2"], b["end_return_P2"]): bad.append({"seed": a["seed"], "old": a["end_return_P2"], "new": b["end_return_P2"]})
                    elif a["end_return_P2"] != 0.0:
                        bad.append({"seed": a["seed"], "old": a["end_return_P2"], "new": None, "note": "old was not the 0.0 substitution"})
                ok(f"R1 {arm}.{lbl}.{bn}.H={H}: every path reproduces, and every unmeasured one was exactly the old 0.0", not bad, bad[:4])
                om = O["bases"][bn][H]["summary"]["end_return_P2"]["mean"]
                nm = N["bases"][bn][H]["W_CARRY"]["summary"]["end_return_P2"]["whole_population"]["mean"]
                ok(f"R2 {arm}.{lbl}.{bn}.H={H}: the old published mean IS the new W_CARRY whole-population mean", eq(om, nm), {"old": om, "new": nm})
                oc = O["bases"][bn][H]["summary"]["paths_that_hit_cum25"]
                nc = N["bases"][bn][H]["W_CARRY"]["summary"]["paths_that_hit_cum25"]
                ok(f"R4 {arm}.{lbl}.{bn}.H={H}: breach counts reconcile", oc == nc["n_true"] and len(op) == nc["n_asked"] + nc["not_applicable"]["n"],
                   {"old_n_true": oc, "new": {"n_true": nc["n_true"], "n_asked": nc["n_asked"], "na": nc["not_applicable"]["n"]}})
                # R5..R8: EVERY OTHER published column of the rendered table, not just the headline mean
                oS, nS = O["bases"][bn][H]["summary"], N["bases"][bn][H]["W_CARRY"]["summary"]
                ok(f"R5 {arm}.{lbl}.{bn}.H={H}: day-stop path count unchanged",
                   oS["paths_that_hit_the_day_stop"] == nS["paths_that_hit_the_day_stop"]["n_true"],
                   {"old": oS["paths_that_hit_the_day_stop"], "new": nS["paths_that_hit_the_day_stop"]["n_true"]})
                ok(f"R6 {arm}.{lbl}.{bn}.H={H}: withheld-anchor quantiles unchanged",
                   all(eq(oS["anchors_withheld"][k], nS["anchors_withheld"]["measured"][k]) for k in ("mean", "median", "p05", "p95")),
                   {"old": oS["anchors_withheld"], "new": nS["anchors_withheld"]["measured"]})
                ok(f"R7 {arm}.{lbl}.{bn}.H={H}: no-halt window-end quantiles unchanged",
                   all(eq(oS["end_return_no_halt"][k], nS["end_return_no_halt"]["measured"][k]) for k in ("mean", "median", "p05", "p95")),
                   {"old": oS["end_return_no_halt"], "new": nS["end_return_no_halt"]["measured"]})
                omp, nmp = O["bases"][bn][H]["mean_path"], N["bases"][bn][H]["W_CARRY"]["mean_path"]
                ok(f"R8 {arm}.{lbl}.{bn}.H={H}: mean-path window end and median breach anchor unchanged",
                   (eq(omp["end_return_P2"], nmp["end_return_P2"]) if nmp["has_measurement"] else omp["end_return_P2"] == 0.0)
                   and eq(oS["cum25_anchor_median"], one_value(nS["cum25_anchor_median_utc"])),
                   {"old_meanpath": omp["end_return_P2"], "new_meanpath": nmp["end_return_P2"], "new_has_measurement": nmp["has_measurement"],
                    "old_median_anchor": oS["cum25_anchor_median"], "new_median_anchor": one_value(nS["cum25_anchor_median_utc"])})
                # DELTA: the main reading vs what was published
                E = N["bases"][bn][H]["W_ENTRY"]["summary"]
                DELTA.append({"arm": arm, "run": lbl, "scope": "base " + bn, "H": str(H),
                              "published_old": om, "main_now_W_ENTRY_measured": E["end_return_P2"]["measured"]["mean"],
                              "delta_pp": (None if (om is None or E["end_return_P2"]["measured"]["mean"] is None)
                                           else 100.0 * (E["end_return_P2"]["measured"]["mean"] - om)),
                              "W_CARRY_measured": N["bases"][bn][H]["W_CARRY"]["summary"]["end_return_P2"]["measured"]["mean"],
                              "n_unmeasured_under_W_CARRY": N["bases"][bn][H]["W_CARRY"]["summary"]["end_return_P2"]["no_measurement"]["n"],
                              "published_breach": oc, "main_now_breach": f'{E["paths_that_hit_cum25"]["n_true"]}/{E["paths_that_hit_cum25"]["n_asked"]}',
                              "meanpath_published_old": O["bases"][bn][H]["mean_path"]["end_return_P2"],
                              "meanpath_main_now": N["bases"][bn][H]["W_ENTRY"]["mean_path"]["end_return_P2"]})
        for st in O["p_start"]:
            if not O["p_start"][st].get("in_window"): continue
            for H in [k for k in O["p_start"][st] if k != "in_window"]:
                om = O["p_start"][st][H]["end_return_P2"]["mean"]
                nm = CUTCELL(N["p_start"][st][H]["W_CARRY"])["end_return_P2"]["whole_population"]["mean"]
                ok(f"R3 {arm}.{lbl}.start {st[:10]}.H={H}: the old published mean IS the new W_CARRY whole-population mean", eq(om, nm),
                   {"old": om, "new": nm})
                ok(f"R9 {arm}.{lbl}.start {st[:10]}.H={H}: day-stop count, breach count and mean path unchanged",
                   O["p_start"][st][H]["paths_day_stopped"] == CUTCELL(N["p_start"][st][H]["W_CARRY"])["paths_that_hit_the_day_stop"]["n_true"]
                   and O["p_start"][st][H]["paths_cum25"] == CUTCELL(N["p_start"][st][H]["W_CARRY"])["paths_that_hit_cum25"]["n_true"]
                   and ((eq(O["p_start"][st][H]["mean_path"]["end_return_P2"], CUTCELL(N["p_start"][st][H]["W_CARRY"])["mean_path"]["end_return_P2"]))
                        if CUTCELL(N["p_start"][st][H]["W_CARRY"])["mean_path"]["has_measurement"] else O["p_start"][st][H]["mean_path"]["end_return_P2"] == 0.0),
                   {"old": [O["p_start"][st][H]["paths_day_stopped"], O["p_start"][st][H]["paths_cum25"], O["p_start"][st][H]["mean_path"]["end_return_P2"]],
                    "new": [CUTCELL(N["p_start"][st][H]["W_CARRY"])["paths_that_hit_the_day_stop"]["n_true"],
                            CUTCELL(N["p_start"][st][H]["W_CARRY"])["paths_that_hit_cum25"]["n_true"],
                            CUTCELL(N["p_start"][st][H]["W_CARRY"])["mean_path"]["end_return_P2"]]})
                E = CUTCELL(N["p_start"][st][H]["W_ENTRY"])
                DELTA.append({"arm": arm, "run": lbl, "scope": "start " + st[:10], "H": str(H), "published_old": om,
                              "main_now_W_ENTRY_measured": E["end_return_P2"]["measured"]["mean"],
                              "delta_pp": (None if (om is None or E["end_return_P2"]["measured"]["mean"] is None)
                                           else 100.0 * (E["end_return_P2"]["measured"]["mean"] - om)),
                              "W_CARRY_measured": CUTCELL(N["p_start"][st][H]["W_CARRY"])["end_return_P2"]["measured"]["mean"],
                              "n_unmeasured_under_W_CARRY": CUTCELL(N["p_start"][st][H]["W_CARRY"])["end_return_P2"]["no_measurement"]["n"],
                              "published_breach": O["p_start"][st][H]["paths_cum25"],
                              "main_now_breach": f'{E["paths_that_hit_cum25"]["n_true"]}/{E["paths_that_hit_cum25"]["n_asked"]}',
                              "meanpath_published_old": O["p_start"][st][H]["mean_path"]["end_return_P2"],
                              "meanpath_main_now": E["mean_path"]["end_return_P2"]})

moved = [d for d in DELTA if d["delta_pp"] is None or abs(d["delta_pp"]) > 0.005]
fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_p2_amd4_delta.py", self_sha256=sha(os.path.abspath(__file__)), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           old_dir=OLD, new_dir=NEW,
           old_sha256={a: sha(os.path.join(OLD, f"BT_P2_READING_{a}.json")) for a in ARMS},
           new_sha256={a: sha(os.path.join(NEW, f"BT_P2_READING_{a}.json")) for a in ARMS},
           checks=RES, failed=fails, n_checks=len(RES), delta=DELTA, moved_cells=moved, n_delta_cells=len(DELTA), n_moved=len(moved),
           VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=float)
print("BT_P2_AMD4_DELTA VERDICT: " + ("ALL PASS %d/%d reproduction checks (the pre-fix numbers come back bit for bit as W_CARRY / "
                                      "whole_population; %d of %d published cells move under the main reading)"
                                      % (len(RES), len(RES), len(moved), len(DELTA))
                                      if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails[:5])), flush=True)
sys.exit(0 if not fails else 3)
