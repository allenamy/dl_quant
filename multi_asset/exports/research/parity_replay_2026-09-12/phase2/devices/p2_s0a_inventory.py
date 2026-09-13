#!/usr/bin/env python3
"""Phase 2 S0(a) inventory (PREREG_producer_parity_phase2_oos_2026-09-12, lead task S0a). READ-ONLY on every input.
Records path / size / sha256 / shape / axis range / finite coverage by calendar year for every artefact Phase 2 would consume,
plus the fold metadata needed by G2-D. No book-level number is computed. Writes exactly one file: <P2>/receipts/S0a_inventory.json.
usage (pod2): env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s0a_inventory.py PATH,HOME,LC_CTYPE"""
import os, sys, json, glob, gzip, hashlib, time, zipfile, calendar, platform, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; OUT = f"{P2}/receipts/S0a_inventory.json"
assert os.path.realpath(OUT).startswith(P2 + "/"), OUT
T0 = time.time()
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def fstat(p):
    st = os.stat(p); return {"path": p, "realpath": os.path.realpath(p), "size": st.st_size, "mtime_utc": iso(st.st_mtime), "sha256": sha(p)}
def npz_header(p, key):
    with zipfile.ZipFile(p) as z:
        with z.open(key + ".npy") as fh:
            ver = np.lib.format.read_magic(fh)
            shape, fortran, dtype = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    return {"shape": list(shape), "dtype": str(dtype)}
def years_of(E): return np.array([time.gmtime(int(t)).tm_year for t in E])
def cover_by_year(P, E):
    yr = years_of(E); fin_rows = np.isfinite(P).any(1); out = {}
    for y in sorted(set(yr.tolist())):
        s = yr == y; out[str(y)] = {"anchors": int(s.sum()), "rows_with_any_finite": int(fin_rows[s].sum()),
                                   "mean_finite_per_row_when_any": round(float(np.isfinite(P[s][fin_rows[s]]).sum(1).mean()), 2) if fin_rows[s].any() else 0.0}
    fr = np.where(fin_rows)[0]
    return {"by_year": out, "first_finite_row": iso(E[fr[0]]) if len(fr) else None, "last_finite_row": iso(E[fr[-1]]) if len(fr) else None}
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "utc_start": iso(T0),
     "host": platform.node(), "python": sys.version.split()[0], "numpy": np.__version__}
R["nvidia_smi_before"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
R["protected_pids_before"] = subprocess.run(["ps", "-o", "pid,stat,etime,args", "-p", "333197,339489"], capture_output=True, text=True).stdout.strip().splitlines()

# ── A. 5m channel caches ──
C = {}
for tag, p in (("holefix2", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"), ("holefix2_x0910", "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz")):
    z = np.load(p, allow_pickle=True); ts = z["ts"].astype(np.int64); sy = [str(s) for s in z["symbols"]]; ch = [str(c) for c in z["ch"]] if "ch" in z.files else None
    d = np.diff(ts)
    C[tag] = {**fstat(p), "keys": z.files, "data_header": npz_header(p, "data"), "ts_first": iso(ts[0]), "ts_last": iso(ts[-1]), "n_rows": int(len(ts)),
              "step_s_unique": sorted(set(int(x) for x in np.unique(d)))[:10], "n_symbols": len(sy),
              "symbols_sha256": hashlib.sha256("\n".join(sy).encode()).hexdigest(), "channels": ch}
    del z
C["holefix2_x0910_vs_holefix2_same_symbols"] = C["holefix2"]["symbols_sha256"] == C["holefix2_x0910"]["symbols_sha256"]
R["A_cache"] = C

# ── B. funding sources ──
FD = "/workspace/wide_multisrc/funding"; syms_dirs = sorted(os.listdir(FD))
nz_months = {}; n404 = 0
for s in syms_dirs:
    ms = sorted(os.path.basename(x)[:7] for x in glob.glob(f"{FD}/{s}/*.zip"))
    n404 += len(glob.glob(f"{FD}/{s}/*.zip.404")); nz_months[s] = ms
allm = sorted({m for v in nz_months.values() for m in v})
B = {"funding_dir": FD, "n_symbol_dirs": len(syms_dirs), "n_zip_files": int(sum(len(v) for v in nz_months.values())), "n_404_markers": n404,
     "month_range": [allm[0], allm[-1]] if allm else None, "n_symbols_with_any_zip": int(sum(1 for v in nz_months.values() if v)),
     "symbols_dirs_sha256": hashlib.sha256("\n".join(syms_dirs).encode()).hexdigest()}
# zip content sample: header + first rows of BTCUSDT last zip (column semantics are needed for the ledger rebuild)
bz = sorted(glob.glob(f"{FD}/BTCUSDT/*.zip"))[-1]
with zipfile.ZipFile(bz) as zf:
    with zf.open(zf.namelist()[0]) as fh: B["zip_sample"] = {"file": bz, "first_lines": [l.decode().strip() for l, _ in zip(fh, range(4))]}
# per-symbol zip digest (names x months) so the rebuild can bind to exactly this set
B["zip_set_sha256"] = hashlib.sha256(json.dumps(nz_months, sort_keys=True).encode()).hexdigest()
AUGP = "/workspace/fund_aug.json.gz"; AUG = json.loads(gzip.open(AUGP, "rt").read())
tmin = min(int(r[0]) for v in AUG.get("rates", {}).values() for r in v) if AUG.get("rates") else None
tmax = max(int(r[0]) for v in AUG.get("rates", {}).values() for r in v) if AUG.get("rates") else None
B["fund_aug"] = {**fstat(AUGP), "keys": sorted(AUG.keys()), "n_symbols_rates": len(AUG.get("rates", {})), "n_rows": int(sum(len(v) for v in AUG.get("rates", {}).values())),
                 "t_min": iso(tmin // 1000) if tmin else None, "t_max": iso(tmax // 1000) if tmax else None, "n_intervals": len(AUG.get("intervals") or {}),
                 "other_meta": {k: AUG[k] for k in AUG if k not in ("rates", "intervals") and not isinstance(AUG[k], (dict, list))}}
CC = "/workspace/fund_state_canoncont.json"; cc = json.load(open(CC))
B["fund_state_canoncont"] = {**fstat(CC), "n": len(cc), "max_last_ts": iso(max(int(v["last_ts"]) for v in cc.values()))}
LP = "/workspace/live_pins.json"; lp = json.load(open(LP))
B["live_pins"] = {**fstat(LP), "keys": sorted(lp.keys()), "n_symbols_live": len(lp.get("symbols_live", [])),
                  "symbols_live_sha256_orderpreserving_compact": hashlib.sha256(json.dumps(list(lp.get("symbols_live", [])), separators=(",", ":")).encode()).hexdigest()}
R["B_funding"] = B

# ── C. king OOF prediction arrays ──
KM4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); E4 = KM4["E_ts"].astype(np.int64)
KM3 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); E3 = KM3["E_ts"].astype(np.int64)
K = {"king_meta_v4": {**fstat("/workspace/data/wide_fea_v4_meta.npz"), "n_anchors": int(len(E4)), "E_first": iso(E4[0]), "E_last": iso(E4[-1]), "names_n": int(len(KM4["names"]))},
     "king_meta_v2ext": {**fstat("/workspace/data/wide_fea_v2ext_meta.npz"), "n_anchors": int(len(E3)), "E_first": iso(E3[0]), "E_last": iso(E3[-1])}}
arrs = {}
for tag, p, E in (("SLOW_v4", "/workspace/review_scratch/king_v4/SLOW_v4.npy", E4), ("SLOW_v3_on_v4axis", "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", E4),
                  ("SLOW_v4e", "/workspace/review_scratch/king_v4/SLOW_v4e.npy", E4), ("slow_pred_pinned_run1_v2extpanel", "/workspace/review_scratch/king_v4/slow_pred_pinned_run1_v2extpanel.npy", E4),
                  ("bundle_v4_slow_pred_pinned", "/workspace/shadow_bundle_v4/slow_pred_pinned.npy", E4), ("bundle_v3_slow_pred_pinned", "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", E3)):
    P = np.load(p); arrs[tag] = P
    K[tag] = {**fstat(p), "shape": list(P.shape), "dtype": str(P.dtype), **(cover_by_year(P, E) if P.shape[0] == len(E) else {"axis_mismatch": [int(P.shape[0]), int(len(E))]})}
K["SLOW_v4_equals_bundle_v4_pinned"] = bool(np.array_equal(arrs["SLOW_v4"], arrs["bundle_v4_slow_pred_pinned"], equal_nan=True))
if not K["SLOW_v4_equals_bundle_v4_pinned"]:
    a, b = arrs["SLOW_v4"], arrs["bundle_v4_slow_pred_pinned"]; fa, fb = np.isfinite(a), np.isfinite(b)
    K["SLOW_v4_vs_bundle_v4_pinned_diff"] = {"finite_pattern_equal": bool(np.array_equal(fa, fb)), "maxabs_common": float(np.abs(a[fa & fb] - b[fa & fb]).max()) if (fa & fb).any() else None,
                                             "rows_differing": int((~np.all((a == b) | (~fa & ~fb), 1)).sum())}
r3 = {int(t): i for i, t in enumerate(E3)}; S3 = np.full((len(E4), 829), np.nan, np.float32)
for k, t in enumerate(E4):
    i = r3.get(int(t))
    if i is not None: S3[k] = arrs["bundle_v3_slow_pred_pinned"][i]
K["SLOW_v3_on_v4axis_equals_realign_of_bundle_v3_pinned"] = bool(np.array_equal(S3, arrs["SLOW_v3_on_v4axis"], equal_nan=True))
K["bundle_v4_config_provenance"] = json.load(open("/workspace/shadow_bundle_v4/config.json")).get("provenance")
K["bundle_v3_config_provenance"] = json.load(open("/workspace/shadow_bundle_v3/config.json")).get("provenance")
man4 = json.load(open("/workspace/shadow_bundle_v4/MANIFEST.json")); K["bundle_v4_manifest_vs_disk"] = {f: (man4[f] == sha(f"/workspace/shadow_bundle_v4/{f}")) for f in man4}
man3 = json.load(open("/workspace/shadow_bundle_v3/MANIFEST.json")); K["bundle_v3_manifest_vs_disk"] = {f: (man3[f] == sha(f"/workspace/shadow_bundle_v3/{f}")) for f in man3}
# per-fold booster files: do any exist?
K["per_fold_king_booster_files_found"] = sorted(set(glob.glob("/workspace/**/slow20[0-9][0-9]*.txt", recursive=False) + glob.glob("/workspace/*/slow20[0-9][0-9]*.txt") + glob.glob("/workspace/*/*/slow20[0-9][0-9]*.txt")))
R["C_king"] = K; del arrs

# ── D. F10 / V2MAIN OOF prediction arrays ──
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True); ED = TG["E_ts"].astype(np.int64)
EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
F = {"dl_axis_v4raw_targets": {**fstat("/workspace/dlw_v4raw/data/dlw_targets.npz"), "n_anchors": int(len(ED)), "E_first": iso(ED[0]), "E_last": iso(ED[-1])},
     "dl_axis_ext_targets": {"path": "/workspace/dlw_ext/data/dlw_targets.npz", "n_anchors": int(len(EX)), "E_first": iso(EX[0]), "E_last": iso(EX[-1])}}
PD = "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"
for tag in ("f10_v4RAW_s42", "f10_v4RAW_s2027", "f10_A0_s42", "f10_A0_s2027", "f10_v4CLIP_s42", "f10_v4CLIP_s2027"):
    p = f"{PD}/{tag}.npy"; P = np.load(p)
    F[tag] = {**fstat(p), "shape": list(P.shape), "dtype": str(P.dtype), **(cover_by_year(P, ED) if P.shape[0] == len(ED) else {"axis_mismatch": [int(P.shape[0]), int(len(ED))]})}
    if tag.startswith("f10_v4RAW"):
        sd = tag.split("_s")[-1]; Y = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{sd}.npy"); rmap = {int(t): i for i, t in enumerate(EX)}
        i25 = int(np.searchsorted(ED, calendar.timegm((2025, 1, 1, 0, 0, 0))))
        yal = np.full((i25, 829), np.nan, np.float32)
        for k in range(i25):
            i = rmap.get(int(ED[k]))
            if i is not None: yal[k] = Y[i]
        ST = np.load(f"/workspace/f8_v4/mwf_v4b/RAW_s{sd}/preds/f10_V2MAIN_RAW_mE1cX7_s{sd}.npy")
        F[tag]["splice_check"] = {"pre2025_equals_yearly_aligned": bool(np.array_equal(P[:i25], yal, equal_nan=True)), "post2025_equals_monthly_stitched": bool(np.array_equal(P[i25:], ST[i25:], equal_nan=True)),
                                  "yearly_src": {**fstat(f"/workspace/f8_ext/preds/f10_V2MAIN_s{sd}.npy")}, "monthly_stitched": {**fstat(f"/workspace/f8_v4/mwf_v4b/RAW_s{sd}/preds/f10_V2MAIN_RAW_mE1cX7_s{sd}.npy")},
                                  "splice_boundary_utc": iso(ED[i25])}
    del P
folds = {}
for sd in ("42", "2027"):
    J = json.load(open(f"/workspace/f8_v4/mwf_v4b/RAW_s{sd}/results/merge.json")); m = J["merged"]
    folds[f"RAW_s{sd}_monthly"] = {"merge_json": fstat(f"/workspace/f8_v4/mwf_v4b/RAW_s{sd}/results/merge.json"), "trainer": m["trainer"], "trainer_sha256_recorded": m["trainer_sha256"], "gate": m["gate"],
                                   "folds": {k: {kk: v.get(kk) for kk in ("n_train", "n_val", "n_test", "cutoff", "embargo_anchors", "causality_ok", "best_epoch", "best_epoch_rule", "self_sha256", "pt_sha256")} for k, v in sorted(m["folds"].items())}}
    for cf in sorted(glob.glob(f"/workspace/f8_v4/mwf_v4b/RAW_s{sd}/shard*/models/mE1cX7_*_config.json")):
        C_ = json.load(open(cf)); YM = str(C_["fold"])
        folds[f"RAW_s{sd}_monthly"]["folds"][YM].update({kk: C_.get(kk) for kk in ("first_test", "last_test", "max_train_idx", "max_train_label_end")})
    Yj = json.load(open(f"/workspace/f8_ext/results/f10_V2MAIN_s{sd}.json"))
    folds[f"V2MAIN_s{sd}_yearly"] = {"report": fstat(f"/workspace/f8_ext/results/f10_V2MAIN_s{sd}.json"), "self_sha256": Yj.get("self_sha256"), "embargo": Yj.get("embargo"), "folds": {k: {"n_test": v.get("n_test"), "best_va": v.get("best_va"), "argmax_epoch": int(np.argmax(v["va_curve"]))} for k, v in Yj["folds"].items()}}
F["fold_metadata"] = folds
F["trainers_on_disk"] = {p: (sha(p) if os.path.exists(p) else None) for p in ("/workspace/pod_f10_train_ext.py", "/workspace/review_scratch/pod_f10_train_monthly_v4.py")}
R["D_f10"] = F

# ── E. research replay A0 / r18 arms + devices + accounting inputs ──
Rr = {}
for tag, p in (("A0_PWR230k_s42", "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz"), ("A0_PWR230k_s2027", "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s2027.npz"),
               ("r18_C0_s42", "/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s42.npz"), ("r18_NW_s42", "/workspace/uplift_2026-09-11/r18_foundation/arms/NW_s42.npz"),
               ("r18_C0_s2027", "/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s2027.npz"), ("r18_NW_s2027", "/workspace/uplift_2026-09-11/r18_foundation/arms/NW_s2027.npz")):
    z = np.load(p, allow_pickle=True); d = {**fstat(p), "keys": z.files}
    for k in z.files:
        if k.endswith("_rec") or k == "rec":
            rec = z[k]; d["rec_key"] = k; d["rec_shape"] = list(rec.shape); ts = rec[:, 0].astype(np.int64); d["rec_ts_first"] = iso(ts[0]); d["rec_ts_last"] = iso(ts[-1])
        if k.endswith("_cols") or k == "cols": d["cols"] = [str(c) for c in z[k]]
        if k.endswith("_W") or k == "W": d["W_key"] = k; d["W_shape"] = list(z[k].shape)
    Rr[tag] = d
for tag, p in (("w10_sleeve_pinned_r2_solve2023_copy", "/workspace/uplift_2026-09-11/r2_solve2023/w10_sleeve.py"), ("w10_sleeve_r18", "/workspace/uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py"),
               ("meta_newprod_v4", "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"), ("umask_UPIT_CRYPTO", "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"),
               ("costb_PWR_G230k", "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"), ("panel_v2ext", "/workspace/data/wide_panel_4h_v2ext.npz")):
    Rr[tag] = fstat(p)
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True); EM = MN["E_ts"].astype(np.int64)
Rr["meta_newprod_v4"].update({"keys": MN.files, "n_anchors": int(len(EM)), "E_first": iso(EM[0]), "E_last": iso(EM[-1]), "y4_shape": list(MN["y4"].shape)})
UM = np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
Rr["umask_UPIT_CRYPTO"].update({"keys": UM.files, **{k: list(UM[k].shape) for k in UM.files if hasattr(UM[k], "shape")}})
R["E_research_replay"] = Rr

R["nvidia_smi_after"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
R["protected_pids_after"] = subprocess.run(["ps", "-o", "pid,stat,etime,args", "-p", "333197,339489"], capture_output=True, text=True).stdout.strip().splitlines()
R["runtime_s"] = round(time.time() - T0, 1); R["utc_end"] = iso(time.time())
json.dump(R, open(OUT, "w"), indent=1, default=str)
print("S0A_INVENTORY_DONE", OUT, "runtime_s", R["runtime_s"], flush=True)
