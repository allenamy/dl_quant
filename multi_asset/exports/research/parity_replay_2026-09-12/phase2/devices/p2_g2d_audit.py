#!/usr/bin/env python3
"""G2-D causality audit (AMENDMENT 2 §A2.5, frozen) and G2-E red capability (AMENDMENT 1 / A2.5). The rule is RE-DERIVED here from the raw fold artefacts
(independent of p2_driver's king_admissible / f10_admissible, which are only cross-checked):
  king  : SLOW_v4 fold Y = anchor year (2024/2025/2026; none before 2024); label_end = last anchor of year < Y with >= 50 finite labels among meta members + 4h;
          admissible iff label_end < E - 30*86400.
  F10   : E >= 2025-01-01 -> monthly fold = month(E), label_end = fold config max_train_label_end; E < 2025 -> yearly V2MAIN fold year(E) (2023/2024; none in 2022),
          label_end = E_ext[first_te - 61] + 4h on the dlw_ext axis; admissible iff label_end < first instant of month(E).
Layer (a): every anchor of the research W_FULL axis (umask ts <= 2026-08-30 20Z): model, label_end, admissible, OOF row available; cross-check vs p2_driver.
Layer (b): every record of the S1 chains listed in argv: served ⇒ admissible under the re-derived rule; recorded admissible flag == re-derived flag.
Mode `--corrupt`: G2-E — the same audit applied with F10 fold 202503 label_end := 2025-03-15 00:00Z and king fold 2025 := 2025-02-15 00:00Z to the G2-E run records;
the audit MUST read RED for both models (red capability PASS iff it does).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B p2_g2d_audit.py PATH,HOME,LC_CTYPE [--corrupt] RUN_TAG [RUN_TAG ...]"""
import os, sys, json, time, hashlib, calendar, glob
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
args = sys.argv[2:]; CORRUPT = "--corrupt" in args; tags = [a for a in args if a != "--corrupt"]; assert tags
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; OUT = f"{P2}/receipts/{'G2E_red_capability' if CORRUPT else 'G2D_causality_audit'}.json"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def mstart(t): g = time.gmtime(int(t)); return calendar.timegm((g.tm_year, g.tm_mon, 1, 0, 0, 0))
T0 = time.time(); H4 = 14400; DAY = 86400
IN = {"king_meta_v4": ("/workspace/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"),
      "SLOW_v4": ("/workspace/review_scratch/king_v4/SLOW_v4.npy", "dde19142d017c37dd9bae564ab4a32a4b9b068f6aef8acc91e7ea329f4f1c8a6"),
      "dl_targets_v4raw": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
      "dl_targets_ext": ("/workspace/dlw_ext/data/dlw_targets.npz", "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9"),
      "f10_v4RAW_s42": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "58d64a6ff968458924f53193d2dac20c4541be65d267e108bb43445032bfbdcd"),
      "universe": (f"{P2}/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7")}
for k, (p, s) in IN.items(): assert sha(p) == s, k
M = np.load(IN["king_meta_v4"][0], allow_pickle=True); KE = M["E_ts"].astype(np.int64); MEM = M["members"]; Y4 = M["y4"]; KROW = {int(t): i for i, t in enumerate(KE)}
kyr = np.array([time.gmtime(int(t)).tm_year for t in KE])
KING_LE = {}
for Y in (2024, 2025, 2026):
    idx = np.where(kyr < Y)[0]
    for i in idx[::-1]:
        if np.isfinite(Y4[i, MEM[i]]).sum() >= 50: KING_LE[Y] = int(KE[i]) + H4; break
F_MON = {}
for cf in glob.glob("/workspace/f8_v4/mwf_v4b/RAW_s42/shard*/models/mE1cX7_*_config.json"):
    C = json.load(open(cf)); F_MON[int(C["fold"])] = calendar.timegm(time.strptime(C["max_train_label_end"], "%Y-%m-%d %H:%M"))
EX = np.load(IN["dl_targets_ext"][0], allow_pickle=True)["E_ts"].astype(np.int64)
F_YR = {Y: int(EX[int(np.searchsorted(EX, calendar.timegm((Y, 1, 1, 0, 0, 0)))) - 61]) + H4 for Y in (2023, 2024)}
if CORRUPT:
    F_MON[202503] = calendar.timegm((2025, 3, 15, 0, 0, 0)); KING_LE[2025] = calendar.timegm((2025, 2, 15, 0, 0, 0))
def king_rule(E):
    Y = time.gmtime(int(E)).tm_year
    if Y not in KING_LE: return None, None, False
    return f"SLOW_v4:fold{Y}", KING_LE[Y], bool(KING_LE[Y] < int(E) - 30 * DAY)
def f10_rule(E):
    g = time.gmtime(int(E))
    if int(E) >= calendar.timegm((2025, 1, 1, 0, 0, 0)):
        ym = g.tm_year * 100 + g.tm_mon
        if ym not in F_MON: return None, None, False
        return f"F10_mE1cX7_s42:fold{ym}", F_MON[ym], bool(F_MON[ym] < mstart(E))
    if g.tm_year not in F_YR: return None, None, False
    return f"F10_V2MAIN_s42:fold{g.tm_year}", F_YR[g.tm_year], bool(F_YR[g.tm_year] < mstart(E))
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "mode": "G2-E corrupted table" if CORRUPT else "G2-D",
     "inputs": {k: {"path": p, "sha256": s} for k, (p, s) in IN.items()}, "king_label_end": {str(k): iso(v) for k, v in KING_LE.items()},
     "f10_monthly_label_end": {str(k): iso(v) for k, v in sorted(F_MON.items())}, "f10_yearly_label_end": {str(k): iso(v) for k, v in F_YR.items()}, "utc": iso(T0)}
# layer (a)
if not CORRUPT:
    sys.path.insert(0, f"{P2}/devices"); import p2_driver as D
    kt = D.king_fold_table(IN["king_meta_v4"][0], "SLOW_v4"); ft = D.f10_fold_table("42")
    U = np.load(IN["universe"][0], allow_pickle=True); UTS = U["ts"].astype(np.int64); AX = [int(t) for t in UTS if int(t) <= calendar.timegm((2026, 8, 30, 20, 0, 0))]
    KO = np.load(IN["SLOW_v4"][0], mmap_mode="r"); DE = np.load(IN["dl_targets_v4raw"][0], allow_pickle=True)["E_ts"].astype(np.int64); FROW = {int(t): i for i, t in enumerate(DE)}
    FO = np.load(IN["f10_v4RAW_s42"][0], mmap_mode="r")
    xk = 0; xf = 0; kw = []; fw = []; k_served = 0; f_served = 0; k_viol = 0; f_viol = 0
    for E in AX:
        km, kle, kad = king_rule(E); fm, fle, fad = f10_rule(E)
        dm, dle, dad = D.king_admissible(kt, E); em, ele, ead = D.f10_admissible(ft, E)
        xk += (km, kle, kad) != (dm, dle, dad); xf += (fm, fle, fad) != (em, ele, ead)
        k_av = KROW.get(E) is not None and bool(np.isfinite(KO[KROW[E]]).any()); f_av = FROW.get(E) is not None and bool(np.isfinite(FO[FROW[E]]).any())
        ks = bool(km is not None and kad and k_av); fs = bool(fm is not None and fad and f_av)       # served under policy withhold
        k_served += ks; f_served += fs
        k_viol += bool(ks and not kad); f_viol += bool(fs and not fad)
        if km is not None and k_av and not kad: kw.append(E)
        if fm is not None and f_av and not fad: fw.append(E)
    yrs_w = {}
    for E in kw: yrs_w[time.gmtime(E).tm_year] = yrs_w.get(time.gmtime(E).tm_year, 0) + 1
    R["layer_a_full_axis"] = {"n_anchors": len(AX), "axis_first": iso(AX[0]), "axis_last": iso(AX[-1]), "cross_check_mismatch_king": int(xk), "cross_check_mismatch_f10": int(xf),
                              "king_served_withhold": int(k_served), "f10_served_withhold": int(f_served), "king_withheld_available_but_inadmissible": len(kw),
                              "king_withheld_by_year": {str(k): v for k, v in yrs_w.items()}, "king_withheld_first_last": [iso(kw[0]), iso(kw[-1])] if kw else None,
                              "f10_withheld_available_but_inadmissible": len(fw), "served_inadmissible_king": int(k_viol), "served_inadmissible_f10": int(f_viol)}
# layer (b)
recs_summary = {}; viol_b = []
for tag in tags:
    j = f"{P2}/receipts/RUN_{tag}.json"; d = json.load(open(j)); n = 0; nk = 0; nf = 0; mism = 0
    for r in d["records"]:
        E = int(r["anchor"]); km, kle, kad = king_rule(E); fm, fle, fad = f10_rule(E); n += 1
        ko = r.get("king_oof") or {}; fo = r.get("f10_oof") or {}
        if ko.get("served"):
            nk += 1
            if not kad: viol_b.append([tag, iso(E), "king served inadmissible", ko.get("model"), iso(kle) if kle else None])
        if fo.get("served"):
            nf += 1
            if not fad: viol_b.append([tag, iso(E), "f10 served inadmissible", fo.get("model"), iso(fle) if fle else None])
        if ko and (ko.get("admissible") != kad or ko.get("model") != km): mism += 1
        if fo and (fo.get("admissible") != fad or fo.get("model") != fm): mism += 1
    recs_summary[tag] = {"receipt": j, "sha256": sha(j), "driver_sha256": d.get("driver_sha256"), "serve_policy": d["arm"].get("serve_policy"), "n_records": n,
                         "n_king_served": nk, "n_f10_served": nf, "n_flag_or_model_mismatch_vs_rederived": mism}
R["layer_b_run_records"] = recs_summary; R["layer_b_violations_first50"] = viol_b[:50]; R["layer_b_n_violations"] = len(viol_b)
if CORRUPT:
    nk = sum(1 for v in viol_b if v[2].startswith("king")); nf = sum(1 for v in viol_b if v[2].startswith("f10"))
    R["audit_reading"] = "RED" if (nk >= 1 and nf >= 1) else "NOT_RED"; R["n_king_violations"] = nk; R["n_f10_violations"] = nf
    R["verdict"] = "PASS" if R["audit_reading"] == "RED" else "FAIL"
    print(f"G2E_VERDICT {R['verdict']} audit_reading={R['audit_reading']} king_violations={nk} f10_violations={nf}", flush=True)
else:
    la = R["layer_a_full_axis"]; mism_b = sum(v["n_flag_or_model_mismatch_vs_rederived"] for v in recs_summary.values())
    ok = (la["served_inadmissible_king"] == 0 and la["served_inadmissible_f10"] == 0 and la["cross_check_mismatch_king"] == 0 and la["cross_check_mismatch_f10"] == 0
          and len(viol_b) == 0 and mism_b == 0)
    R["verdict"] = "PASS" if ok else "RED"
    print(f"G2D_VERDICT {R['verdict']} axis={la['n_anchors']} king_withheld={la['king_withheld_available_but_inadmissible']} {la['king_withheld_by_year']} f10_withheld={la['f10_withheld_available_but_inadmissible']} "
          f"served_inadmissible=({la['served_inadmissible_king']},{la['served_inadmissible_f10']}) cross_check_mismatch=({la['cross_check_mismatch_king']},{la['cross_check_mismatch_f10']}) "
          f"records_violations={len(viol_b)} records_flag_mismatch={mism_b}", flush=True)
R["runtime_s"] = round(time.time() - T0, 1)
json.dump(R, open(OUT, "w"), indent=1)
