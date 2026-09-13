#!/usr/bin/env python3
"""S2-D causality audit — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (sha bc57266e…) §A6.8, over the six S2 chains.
Rules are RE-DERIVED here from the raw fold artefacts, per arm (p2_driver's functions are not imported; the fold tables recorded in each RUN receipt
are only cross-checked):
  king (SLOW_v4 and SLOW_v3_on_v4axis, same exporter rule): fold Y = anchor year in {2024, 2025, 2026}; label_end = last anchor of year < Y with >= 50
       finite labels among wide_fea_v4_meta members, + 4h; admissible iff label_end < E - 30 days.
  F10 v4RAW_s{seed}: E >= 2025-01-01 -> monthly fold month(E), label_end = /workspace/f8_v4/mwf_v4b/RAW_s{seed} fold config max_train_label_end;
       E < 2025 -> yearly V2MAIN 2023/2024, label_end = E_ext[first_te - 61] + 4h (dlw_ext axis).
  F10 A0_s{seed}: yearly V2MAIN 2023..2026 by the same dlw_ext rule (A6.1). F10 admissible iff label_end < first instant of month(E).
Layer (a), chain axis (10,039 anchors): model / label_end / admissible / OOF row available; served under the arm's policy; withheld sets; recorded fold tables.
Layer (b), every record: served => admissible (withhold arms); recorded flag and model id == re-derived; serve_all: served-inadmissible ⊆ layer-(a) set.
Descriptive (no gate): per-year king served / withheld, F10 served, D10 coverage (king n_finite / n_members on served anchors; F10 n_scored / signal members).
Writes receipts/S2_causality_audit.json; prints one S2_AUDIT summary line; exit 0 iff PASS, else 3.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s2_audit.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, calendar, glob
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; PREREG_SHA = "bc57266e5abf103926b2231facb4b12b28137565760ea34b4e8fc49c2cf15769"
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
      "SLOW_v3_on_v4axis": ("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009"),
      "dl_targets_v4raw": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
      "dl_targets_ext": ("/workspace/dlw_ext/data/dlw_targets.npz", "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9"),
      "v4RAW_s42": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "58d64a6ff968458924f53193d2dac20c4541be65d267e108bb43445032bfbdcd"),
      "v4RAW_s2027": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy", "47046ccd6dc7937ce39d9d9a880a34984ad4b6f966889505af0255da8adc136d"),
      "A0_s42": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", "ff109711f5526c68cebb23599e299041a2310caa7857b5ff9aa50464d2e6077b"),
      "A0_s2027": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy", "98bfe779261b550f15bbd511dc4637403b7341b25ccc2d4ee15521cb33787f18")}
for k, (p, s) in IN.items(): assert sha(p) == s, ("input sha", k)
ARMS = {"S2_v4_s42": ("SLOW_v4", "v4RAW_s42", "42", "withhold"), "S2_v4_s2027": ("SLOW_v4", "v4RAW_s2027", "2027", "withhold"),
        "S2_A0pred_s42": ("SLOW_v3_on_v4axis", "A0_s42", "42", "withhold"), "S2_A0pred_s2027": ("SLOW_v3_on_v4axis", "A0_s2027", "2027", "withhold"),
        "S2_v4_s42_serveall": ("SLOW_v4", "v4RAW_s42", "42", "serve_all"), "S2_v4_s42_pins": ("SLOW_v4", "v4RAW_s42", "42", "withhold")}
AXIS = list(range(calendar.timegm((2022, 1, 31, 0, 0, 0)), calendar.timegm((2026, 8, 31, 0, 0, 0)) + 1, H4)); assert len(AXIS) == 10039
JAN = {E for Y in (2024, 2025, 2026) for E in range(calendar.timegm((Y, 1, 1, 0, 0, 0)), calendar.timegm((Y, 1, 31, 0, 0, 0)) + 1, H4)}; assert len(JAN) == 543
# king rule (re-derived)
M = np.load(IN["king_meta_v4"][0], allow_pickle=True); KE = M["E_ts"].astype(np.int64); MEM = M["members"]; Y4 = M["y4"]; KROW = {int(t): i for i, t in enumerate(KE)}
kyr = np.array([time.gmtime(int(t)).tm_year for t in KE]); KING_LE = {}
for Y in (2024, 2025, 2026):
    for i in np.where(kyr < Y)[0][::-1]:
        if np.isfinite(Y4[i, MEM[i]]).sum() >= 50: KING_LE[Y] = int(KE[i]) + H4; break
def king_rule(E, name):
    Y = time.gmtime(int(E)).tm_year
    if Y not in KING_LE: return None, None, False
    return f"{name}:fold{Y}", KING_LE[Y], bool(KING_LE[Y] < int(E) - 30 * DAY)
EX = np.load(IN["dl_targets_ext"][0], allow_pickle=True)["E_ts"].astype(np.int64)
F_YR = {Y: int(EX[int(np.searchsorted(EX, calendar.timegm((Y, 1, 1, 0, 0, 0)))) - 61]) + H4 for Y in (2023, 2024, 2025, 2026)}
F_MON = {}
for seed in ("42", "2027"):
    F_MON[seed] = {}
    for cf in glob.glob(f"/workspace/f8_v4/mwf_v4b/RAW_s{seed}/shard*/models/mE1cX7_*_config.json"):
        Cj = json.load(open(cf)); F_MON[seed][int(Cj["fold"])] = calendar.timegm(time.strptime(Cj["max_train_label_end"], "%Y-%m-%d %H:%M"))
    assert len(F_MON[seed]) == 20, (seed, sorted(F_MON[seed]))
def f10_rule(E, src):
    g = time.gmtime(int(E)); seed = src.split("_s")[1]
    if src.startswith("v4RAW") and int(E) >= calendar.timegm((2025, 1, 1, 0, 0, 0)):
        ym = g.tm_year * 100 + g.tm_mon
        if ym not in F_MON[seed]: return None, None, False
        return f"F10_mE1cX7_s{seed}:fold{ym}", F_MON[seed][ym], bool(F_MON[seed][ym] < mstart(E))
    Y = g.tm_year
    if Y not in F_YR or (src.startswith("v4RAW") and Y not in (2023, 2024)): return None, None, False
    return f"F10_V2MAIN_s{seed}:fold{Y}", F_YR[Y], bool(F_YR[Y] < mstart(E))
DE = np.load(IN["dl_targets_v4raw"][0], allow_pickle=True)["E_ts"].astype(np.int64); FROW = {int(t): i for i, t in enumerate(DE)}
R = dict(device="p2_s2_audit.py", self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, env=dict(os.environ), argv=sys.argv,
         inputs={k: dict(path=p, sha256=s) for k, (p, s) in IN.items()}, king_label_end={str(k): iso(v) for k, v in KING_LE.items()},
         f10_yearly_label_end={str(k): iso(v) for k, v in F_YR.items()}, f10_monthly_label_end={s: {str(k): iso(v) for k, v in sorted(F_MON[s].items())} for s in F_MON},
         utc=iso(T0), arms={})
OK = True
for tag, (kname, fsrc, seed, policy) in ARMS.items():
    KO = np.load(IN[kname][0], mmap_mode="r"); FO = np.load(IN[fsrc][0], mmap_mode="r")
    rp = f"{P2}/receipts/RUN_{tag}.json"; d = json.load(open(rp)); recs = d["records"]
    assert d["arm"]["king_oof"] == kname and d["arm"]["f10_oof"] == fsrc and d["arm"]["serve_policy"] == policy
    # layer (a)
    k_withheld = []; f_withheld = []; k_served_inadm = []; f_served_inadm = []; k_served = 0; f_served = 0
    for E in AXIS:
        km, kle, kad = king_rule(E, kname); fm, fle, fad = f10_rule(E, fsrc)
        k_av = KROW.get(E) is not None and bool(np.isfinite(KO[KROW[E]]).any()); f_av = FROW.get(E) is not None and bool(np.isfinite(FO[FROW[E]]).any())
        ks = bool(km is not None and k_av and (kad or policy == "serve_all")); fs = bool(fm is not None and f_av and (fad or policy == "serve_all"))
        k_served += ks; f_served += fs
        if km is not None and k_av and not kad: (k_served_inadm if ks else k_withheld).append(E)
        if fm is not None and f_av and not fad: (f_served_inadm if fs else f_withheld).append(E)
    rec_kt = {int(k): int(v) for k, v in d["king_fold_table"]["label_end"].items()}
    ft = d["f10_fold_table"]; rec_fy = {int(k): int(v) for k, v in ft["yearly_label_end"].items()}; rec_fm = {int(k): int(v) for k, v in ft["monthly_label_end"].items()}
    xk = rec_kt != KING_LE
    if fsrc.startswith("A0"):
        xf = (rec_fy != F_YR) or bool(rec_fm) or int(ft["splice_boundary"]) != 2 ** 62
    else:
        xf = (rec_fy != {Y: F_YR[Y] for Y in (2023, 2024)}) or (rec_fm != F_MON[seed]) or int(ft["splice_boundary"]) != calendar.timegm((2025, 1, 1, 0, 0, 0))
    la = dict(n_anchors=len(AXIS), king_served_under_policy=int(k_served), f10_served_under_policy=int(f_served),
              king_withheld_available_inadmissible=len(k_withheld), king_withheld_equals_jan543=bool(set(k_withheld) == JAN) if policy == "withhold" else None,
              king_served_inadmissible=len(k_served_inadm), king_served_inadmissible_subset_jan543=bool(set(k_served_inadm) <= JAN),
              f10_withheld_available_inadmissible=len(f_withheld), f10_served_inadmissible=len(f_served_inadm),
              recorded_fold_table_mismatch_king=bool(xk), recorded_fold_table_mismatch_f10=bool(xf))
    # layer (b)
    viol = []; mism = 0; nk = 0; nf = 0; by_year = {}; k_inadm_served_rec = set()
    for r in recs:
        E = int(r["anchor"]); Y = str(time.gmtime(E).tm_year); by = by_year.setdefault(Y, dict(n=0, king_called=0, king_served=0, king_withheld=0, f10_served=0,
                                                                                                   king_cov_sum=0.0, f10_cov_sum=0.0, f10_cov_n=0))
        by["n"] += 1
        km, kle, kad = king_rule(E, kname); fm, fle, fad = f10_rule(E, fsrc)
        ko = r.get("king_oof") or {}; fo = r.get("f10_oof") or {}
        if ko:
            by["king_called"] += 1
            if ko.get("model") != km or ko.get("admissible") != kad or ko.get("label_end") != kle: mism += 1
            if ko.get("served"):
                nk += 1; by["king_served"] += 1; by["king_cov_sum"] += ko["n_finite"] / max(ko["n_members"], 1)
                if not kad:
                    k_inadm_served_rec.add(E)
                    if policy != "serve_all": viol.append([iso(E), "king served inadmissible", ko.get("model")])
            elif km is not None and not kad:
                by["king_withheld"] += 1
        if fo:
            if fo.get("model") != fm or fo.get("admissible") != fad or fo.get("label_end") != fle: mism += 1
            if fo.get("served"):
                nf += 1; by["f10_served"] += 1
                if not fad: viol.append([iso(E), "f10 served inadmissible", fo.get("model")])
            mem = (r.get("signal") or {}).get("members")
            if isinstance(mem, int) and mem > 0: by["f10_cov_sum"] += fo.get("n_scored", 0) / mem; by["f10_cov_n"] += 1
    for Y, by in by_year.items():
        by["king_coverage_mean_on_served"] = (by.pop("king_cov_sum") / by["king_served"]) if by["king_served"] else None
        s_, n_ = by.pop("f10_cov_sum"), by.pop("f10_cov_n"); by["f10_coverage_mean"] = (s_ / n_) if n_ else None
    lb = dict(receipt=rp, receipt_sha256=sha(rp), n_records=len(recs), n_king_served=nk, n_f10_served=nf, n_violations=len(viol), violations_first20=viol[:20],
              n_flag_model_label_mismatch_vs_rederived=mism, serve_all_king_inadmissible_served_records=len(k_inadm_served_rec),
              serve_all_records_subset_jan543=bool(k_inadm_served_rec <= JAN))
    if policy == "withhold":
        ok = (la["king_served_inadmissible"] == 0 and la["f10_served_inadmissible"] == 0 and la["king_withheld_equals_jan543"] and la["f10_withheld_available_inadmissible"] == 0
              and not xk and not xf and len(viol) == 0 and mism == 0 and lb["serve_all_king_inadmissible_served_records"] == 0)
    else:
        ok = (la["king_served_inadmissible_subset_jan543"] and la["f10_served_inadmissible"] == 0 and not xk and not xf and len(viol) == 0 and mism == 0
              and lb["serve_all_records_subset_jan543"])
    R["arms"][tag] = dict(king_oof=kname, f10_oof=fsrc, seed=seed, policy=policy, layer_a=la, layer_b=lb, by_year=by_year, PASS=bool(ok))
    OK = OK and bool(ok)
    print(json.dumps({"arm": tag, "PASS": bool(ok), "king_withheld": la["king_withheld_available_inadmissible"], "king_served_inadm": la["king_served_inadmissible"],
                      "f10_served_inadm": la["f10_served_inadmissible"], "violations": len(viol), "mismatch": mism, "fold_table_mismatch": [bool(xk), bool(xf)]}), flush=True)
R["PASS"] = bool(OK); R["runtime_s"] = round(time.time() - T0, 1)
out = f"{P2}/receipts/S2_causality_audit.json"; assert os.path.realpath(out).startswith(P2 + "/")
json.dump(R, open(out + ".tmp", "w"), indent=1); os.replace(out + ".tmp", out)
print("S2_AUDIT verdict=%s arms=%s receipt_sha256=%s" % ("PASS" if OK else "RED", {t: v["PASS"] for t, v in R["arms"].items()}, sha(out)), flush=True)
sys.exit(0 if OK else 3)
