#!/usr/bin/env python3
"""ens_stats.py — prereg docs/PREREG_f10_seed_ensemble_book_2026-09-23.md (45aba1f3f, sha 56acd832) §3 E1–E4 and §4 reports, exactly as pinned in
receipts/ENS_OPERATIONALISATION.json (written before any number). Reads the per-path files of the certified launcher: NEW_ENS (this task) and
Stage 1's NEW_s42 / NEW_s2027 (READ ONLY, not re-run). The per-path metric functions are ovn_stats.py's (1208eb43) verbatim, on the certified table
device bt_tables.py (892ba66b); no new simulator.
Preconditions (each failure raises; nothing is filled):
  P0  each arm has exactly the 32 seed files of its main run; json npz_sha256 == file; bt_driver_lib.audits_clean; seed field == k.
  P1  identity: Stage 1 configs sha == 162239b6 / 54afef27; NEW_ENS config sha == its make-config receipt; every PATH json 'run' == its config's
      main run; NEW_ENS run dict vs NEW_s42 run dict differ only in arm / tag / role / targets.arm / targets.sources; calibration_params_used
      identical across all 96 paths; cost_cell None; Stage 1 launch receipt config sha checked if present.
  P2  one window axis for all arms; identical day axes in every comparison; no NaN; no empty segment.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ens_stats.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, time, math, hashlib, calendar, glob, datetime, collections

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_tables as BT
import bt_driver_lib as DL

OUT = sys.argv[2]
H4 = 14400; DAY = 86400; B = 10000; RNG = (20260923, 2); BLOCK_MAIN = 30; BLOCK_SENS = 5; NPATH = 32
PCT97_5 = (1.25, 98.75); PCT95 = (2.5, 97.5)
E1_LB = -0.5; E2_TOL = 0.05; E3_MULT = 1.05; E4_TOL = 0.01
DEV = {"bt_tables.py": "892ba66b9e8040ff04caede02272556dec5a71eb4632cbe7a2a13f46bd35f389", "bt_driver_lib.py": "ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb"}
S1 = "/workspace/old_vs_new_2026-09-23"; S1RUNS = "/dev/shm/ovn_2026-09-23/runs"; S1REC = "/dev/shm/ovn_2026-09-23/receipts"
ME = "/workspace/f10_ens_2026-09-23"; MERUNS = "/dev/shm/f10_ens_2026-09-23/runs"
ARMS = {"NEW_ENS": (MERUNS, "F10ENS_NEW_ENS_scaled_rule_raw_UAFE"), "NEW_s42": (S1RUNS, "OVN_NEW_s42_scaled_rule_raw_UAFE"),
        "NEW_s2027": (S1RUNS, "OVN_NEW_s2027_scaled_rule_raw_UAFE")}
CFG = {"NEW_s42": (f"{S1}/RUN_CONFIG_OVN_NEW_s42_2026-09-23.json", "162239b6e397c0aa2b017109b90e59a5cd1b54227ccae6b2321045f977f4533b"),
       "NEW_s2027": (f"{S1}/RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json", "54afef27a4d7988ac02eb981af4075fff0ddd2919005eba5127c5fa138c8cfd5"),
       "NEW_ENS": (f"{ME}/RUN_CONFIG_F10ENS_NEW_ENS_2026-09-23.json", None)}
COMBO = {"NEW_ENS": (f"{ME}/work/combo_ENS/scaled_diagnostic.npz", None),
         "NEW_s42": (f"{S1}/new_targets/combo_s42/scaled_diagnostic.npz", "4dec6b38b08f8cc857c8f58659e846fea686c02c2959c622ea248c7ef5b22afa"),
         "NEW_s2027": (f"{S1}/new_targets/combo_s2027/scaled_diagnostic.npz", "98797d491486335e692b7028b50308250e037bbbbc8c74d43cba7e7c28cf9fca")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(iso): return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


for f, s in DEV.items(): assert sha(os.path.join(HERE, f)) == s, f"device sha {f}"
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"), "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"), "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
JUDGE = ("2023H2", "2024", "2025")
rec = {"device": "ens_stats.py", "self_sha256": sha(os.path.abspath(__file__)), "devices": DEV, "utc_start": iso(time.time()), "arms": ARMS, "rng": list(RNG), "B": B,
       "blocks": {"main": BLOCK_MAIN, "sensitivity": BLOCK_SENS}, "segments": SEG, "operationalisation": "receipts/ENS_OPERATIONALISATION.json",
       "prereg": {"path": "docs/PREREG_f10_seed_ensemble_book_2026-09-23.md", "commit": "45aba1f3f", "sha256": "56acd8320eae43450ba8a6ddfc7a3808bf0f742bcbe76c5d9890be6da6976d92"},
       "preconditions": {}}


# ─────────── ovn_stats.py (1208eb43) functions, verbatim ───────────
def load_cell(d, tag_dir, certified_dir=None):
    """→ list of 32 series (bt_tables.series_from_path) + file facts; P0 (+ P1 when certified_dir is given)"""
    stems = [os.path.join(d, f"PATH_{tag_dir}_seed_{k:02d}") for k in range(NPATH)]
    miss = [s for s in stems if not (os.path.exists(s + ".npz") and os.path.exists(s + ".json"))]
    if miss: raise FileNotFoundError(f"{tag_dir}: {len(miss)} path files missing, first {os.path.basename(miss[0])}")
    paths, facts = [], []
    for k, s in enumerate(stems):
        J = json.load(open(s + ".json")); h = sha(s + ".npz")
        if J["npz_sha256"] != h: raise ValueError(f"{tag_dir} seed {k}: npz sha != its json")
        if not DL.audits_clean(J["audits"]): raise ValueError(f"{tag_dir} seed {k}: audits not clean")
        if int(J["seed"]) != k: raise ValueError(f"{tag_dir} seed field {J['seed']} != {k}")
        f = {"seed": k, "npz_sha256": h, "status_counts": J["status_counts"], "events": J["events_fired_counts"], "target_stats": J["target_stats"],
             "_run": J["run"], "_cal": J["calibration_params_used"], "_cost_cell": J.get("cost_cell", "<absent>")}
        facts.append(f); paths.append(BT.series_from_path(np.load(s + ".npz")))
    A = paths[0]["A"]
    for p in paths:
        if not np.array_equal(p["A"], A): raise ValueError(f"{tag_dir}: window axes differ across seeds")
        for key in ("r", "pnl", "car", "cst", "unk", "g"):
            if not np.all(np.isfinite(p[key])): raise ValueError(f"{tag_dir}: non-finite {key}")
    return paths, facts


def seg_mask(A, a, b):
    m = (A >= ts(a)) & (A <= ts(b))
    if not m.any(): raise ValueError(f"empty segment {a}..{b}")
    return m


def full_days(A, m):
    """days whose 6 anchors (00..20Z) all lie in the mask"""
    d = (A[m] // DAY) * DAY; ud, c = np.unique(d, return_counts=True); return ud[c == 6]


def daily_on(A, r, days):
    ud, rd = BT.daily(A, r); pos = np.searchsorted(ud, days); assert np.all(ud[pos] == days); return rd[pos]


def path_metrics(p, m, days):
    A = p["A"]; r = p["r"][m]; rd = daily_on(A[m], r, days)
    tr = float(np.prod(1.0 + r) - 1.0); nw = int(m.sum())
    return {"n_windows": nw, "n_full_days": int(len(days)), "total_return": tr, "cagr": float((1.0 + tr) ** (2190.0 / nw) - 1.0) if tr > -1 else -1.0,
            "sharpe": BT.sharpe(rd), "worst_day": float(rd.min()), "maxdd_5m": BT.maxdd_5m(p, m),
            "g": float(p["g"][m].mean()), "price": float(p["pnl"][m].mean()), "funding_paid": float(p["car"][m].mean()), "fee": float(p["cst"][m].mean()),
            "unknown_excluded": float(p["unk"][m].mean()), "turnover_over_gross": float(p["tau"][m].mean()),
            "day_stop_flattens": float(p["dstop"][m].sum()), "per_name_stops": float(p["nstop"][m].sum()), "halt_anchors": float(p["halt"][m].sum()),
            "hold_anchors": float(p["hold"][m].sum()), "g_identity_max_err": float(np.max(np.abs(p["g"][m] - (p["pnl"][m] - p["car"][m] - p["cst"][m] - p["unk"][m]))))}


KEYS = ("total_return", "cagr", "sharpe", "worst_day", "maxdd_5m", "g", "price", "funding_paid", "fee", "unknown_excluded", "turnover_over_gross",
        "day_stop_flattens", "per_name_stops", "halt_anchors", "hold_anchors")


def summarise(per):
    out = {"n_paths": len(per), "n_windows": per[0]["n_windows"], "n_full_days": per[0]["n_full_days"]}
    for k in KEYS:
        v = [x[k] for x in per]
        if any(x is None for x in v): out[k] = {"UNAVAILABLE": f"{sum(x is None for x in v)} paths undefined"}; continue
        v = np.array(v, float); out[k] = {"path_mean": float(v.mean()), "p2.5": float(np.percentile(v, 2.5)), "p97.5": float(np.percentile(v, 97.5)), "n_eff": int(len(v))}
    out["g_identity_max_err"] = max(x["g_identity_max_err"] for x in per); assert out["g_identity_max_err"] <= 1e-9, "g identity"
    return out


def mean_path_metrics(paths, m, days):
    mp = BT.series_mean(paths); rd = daily_on(mp["A"][m], mp["r"][m], days); tr = float(np.prod(1.0 + mp["r"][m]) - 1.0)
    return {"total_return": tr, "sharpe": BT.sharpe(rd), "maxdd_5m": BT.maxdd_5m(mp, m), "worst_day": float(rd.min()), "note": "certified MEAN PATH (descriptive only)"}


def dbar(pn, po, m, days):
    """d̄(t) over the given full days: mean over seeds k of r_NEW,k(t) − r_OLD,k(t)"""
    D = np.stack([daily_on(a["A"][m], a["r"][m], days) - daily_on(b["A"][m], b["r"][m], days) for a, b in zip(pn, po)])
    if not np.all(np.isfinite(D)): raise ValueError("non-finite daily difference")
    return D.mean(0), D


def boot(x, block):
    n = len(x); idx = BT.mbb_indices(n, block, B, RNG); mb = x[idx].mean(1)
    return {"block_days": block, "n_days": n, "B": B, "rng": list(RNG), "ci97.5_two_sided_bps": [float(1e4 * np.percentile(mb, PCT97_5[0])), float(1e4 * np.percentile(mb, PCT97_5[1]))],
            "ci95_bps": [float(1e4 * np.percentile(mb, PCT95[0])), float(1e4 * np.percentile(mb, PCT95[1]))], "draws_defined": int(np.isfinite(mb).sum())}
# ─────────── end verbatim ───────────


# ─────────── load + P0 ───────────
S = {}
for arm, (root, tag_dir) in ARMS.items():
    S[arm] = load_cell(os.path.join(root, tag_dir), tag_dir)
rec["preconditions"]["P0"] = {arm: {"n_paths": len(S[arm][0]), "npz_sha256_first": S[arm][1][0]["npz_sha256"]} for arm in S}

# ─────────── P1 identity ───────────
P1 = {}
C = {}
for arm, (p, want) in CFG.items():
    got = sha(p)
    if want is not None and got != want: raise ValueError(f"P1 {arm} config sha {got[:16]} != {want[:16]}")
    C[arm] = json.load(open(p)); P1[f"config_sha_{arm}"] = got
mc = json.load(open(f"{ME}/receipts/ENS_CONFIG_DIFF.json"))
if mc["config"]["sha256"] != P1["config_sha_NEW_ENS"]: raise ValueError("P1 NEW_ENS config sha != make-config receipt")
if mc["template"]["sha256"] != CFG["NEW_s42"][1]: raise ValueError("P1 NEW_ENS template is not the Stage 1 NEW_s42 config")
main_run = {arm: [r for r in C[arm]["runs"] if r["book"] == "scaled" and not r.get("cost_cell")] for arm in C}
for arm in C:
    if len(main_run[arm]) != 1: raise ValueError(f"P1 {arm}: main run not unique")
    main_run[arm] = main_run[arm][0]
    for f in S[arm][1]:
        if f["_run"] != main_run[arm]: raise ValueError(f"P1 {arm} seed {f['seed']}: PATH run dict != config main run")
        if f["_cost_cell"] is not None: raise ValueError(f"P1 {arm} seed {f['seed']}: cost_cell {f['_cost_cell']}")


def strip(r):
    x = json.loads(json.dumps(r)); [x.pop(k) for k in ("arm", "tag", "role")]; x["targets"].pop("arm"); x["targets"].pop("sources"); return x


for a2 in ("NEW_s2027", "NEW_ENS"):
    if strip(main_run[a2]) != strip(main_run["NEW_s42"]): raise ValueError(f"P1 {a2} main run differs from NEW_s42 beyond arm/tag/role/targets.arm/targets.sources")
cal0 = S["NEW_s42"][1][0]["_cal"]
for arm in S:
    for f in S[arm][1]:
        if f["_cal"] != cal0: raise ValueError(f"P1 {arm} seed {f['seed']}: calibration_params_used differs")
cfg_level = {}
for a2 in ("NEW_s2027", "NEW_ENS"):
    X = json.loads(json.dumps(C[a2])); Y = json.loads(json.dumps(C["NEW_s42"]))
    for Z in (X, Y):
        for k in ("config", "status", "created_utc", "object", "pending", "new_lineage", "f10ens"): Z.pop(k, None)
        Z["ovn"].pop("role", None); Z["paths"].pop("pod_root", None); Z["runs"] = [strip(r) for r in Z["runs"]]
    cfg_level[a2] = (X == Y)
    if not cfg_level[a2]: raise ValueError(f"P1 {a2} config differs from NEW_s42 beyond labels / targets / run naming / lineage / pod_root")
lr = {}
for p in sorted(glob.glob(f"{S1REC}/BT_LAUNCH_*.json")):
    try:
        J = json.load(open(p)); cp = J["config"]["path"]
        for arm in ("NEW_s42", "NEW_s2027"):
            if os.path.basename(cp) == os.path.basename(CFG[arm][0]): lr[arm] = {"receipt": p, "config_sha256": J["config"]["sha256"], "equal": J["config"]["sha256"] == CFG[arm][1]}
    except Exception as e:
        continue
for arm in ("NEW_s42", "NEW_s2027"):
    if arm in lr and not lr[arm]["equal"]: raise ValueError(f"P1 Stage 1 launch receipt config sha differs for {arm}")
P1.update({"path_run_dict_equals_config_main_run": "asserted, 3 x 32 paths", "main_run_dicts_equal_modulo_naming_and_targets": True,
           "config_level_equal_modulo_labels_targets_pod_root": cfg_level, "calibration_params_used_identical_96_paths": True, "cost_cell_none": True,
           "stage1_launch_receipts": lr if lr else "not yet written by Stage 1 (checked by pod2 config sha + per-path run dicts instead)"})
rec["preconditions"]["P1_identity"] = P1

# ─────────── P2 axes ───────────
A = S["NEW_s42"][0][0]["A"]
for arm in S:
    if not np.array_equal(S[arm][0][0]["A"], A): raise ValueError(f"P2 {arm}: window axis differs")
masks = {s: seg_mask(A, a, b) for s, (a, b) in SEG.items()}
days = {s: full_days(A, masks[s]) for s in SEG}
for s in SEG:
    if len(days[s]) == 0: raise ValueError(f"P2 no full day in {s}")
rec["preconditions"]["P2_common_axis"] = {"first": iso(A[0]), "last": iso(A[-1]), "n": int(len(A))}
rec["days"] = {s: {"n_full_days": int(len(days[s])), "first": iso(days[s][0]), "last": iso(days[s][-1]), "n_windows": int(masks[s].sum())} for s in SEG}

# ─────────── §4.1 per arm, per segment ───────────
T = {}
for arm, (paths, facts) in S.items():
    T[arm] = {}
    for s in SEG:
        per = [path_metrics(p, masks[s], days[s]) for p in paths]
        T[arm][s] = {"paths": summarise(per), "mean_path": mean_path_metrics(paths, masks[s], days[s]),
                     "per_path": [{k: x[k] for k in ("sharpe", "total_return", "maxdd_5m", "turnover_over_gross", "day_stop_flattens")} for x in per]}
rec["tables"] = T


def pm(arm, s, k):
    v = T[arm][s]["paths"][k]
    if "path_mean" not in v: raise ValueError(f"undefined {k} for {arm} {s}: {v}")
    return v["path_mean"]


# ─────────── §3 E1–E4 ───────────
V = {}
pe = S["NEW_ENS"][0]
e1 = {}
for k in ("NEW_s42", "NEW_s2027"):
    db, D = dbar(pe, S[k][0], masks["pre2026"], days["pre2026"])
    if len(db) == 0: raise ValueError("E1 empty")
    est = float(1e4 * db.mean()); b30 = boot(db, BLOCK_MAIN); b5 = boot(db, BLOCK_SENS)
    dp = np.concatenate([[ts("2023-06-30T00:00:00Z")], days["pre2026"]])
    ud_all = lambda p: BT.daily(p["A"][masks["pre2026"]], p["r"][masks["pre2026"]])
    Dp = np.stack([ud_all(a)[1] - ud_all(b)[1] for a, b in zip(pe, S[k][0])]); assert np.array_equal(ud_all(pe[0])[0], dp)
    b30p = boot(Dp.mean(0), BLOCK_MAIN)
    segm = {}
    for s in JUDGE + ("2026",):
        x, _ = dbar(pe, S[k][0], masks[s], days[s]); segm[s] = {"mean_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
    lb = b30["ci97.5_two_sided_bps"][0]
    e1[k] = {"PASS": bool(lb > E1_LB), "estimate_bps_per_day": est, "boot_30d": b30, "boot_5d_sensitivity": b5, "n_days": int(len(db)), "n_paths": int(D.shape[0]),
             "segment_means": segm, "sensitivity_partial_first_day_included": {"estimate_bps_per_day": float(1e4 * Dp.mean()), "boot_30d": b30p,
                                                                                  "changes_E1": bool((b30p["ci97.5_two_sided_bps"][0] > E1_LB) != (lb > E1_LB))}}
V["E1"] = {"PASS": all(e1[k]["PASS"] for k in e1), "per_single_seed": e1, "gate": "for each k: lower bound of the 97.5% two-sided interval (30-day blocks) of mean dbar(ENS - k) > -0.5 bps/day"}
sh = {arm: {s: pm(arm, s, "sharpe") for s in JUDGE} for arm in S}
e2 = {s: {"ENS": sh["NEW_ENS"][s], "s42": sh["NEW_s42"][s], "s2027": sh["NEW_s2027"][s], "floor": min(sh["NEW_s42"][s], sh["NEW_s2027"][s]) - E2_TOL,
          "PASS": bool(sh["NEW_ENS"][s] >= min(sh["NEW_s42"][s], sh["NEW_s2027"][s]) - E2_TOL)} for s in JUDGE}
V["E2"] = {"PASS": all(e2[s]["PASS"] for s in JUDGE), "segments": e2, "gate": "each of 2023H2/2024/2025: pathmean Sharpe(ENS) >= min(s42, s2027) - 0.05"}
tv = {arm: pm(arm, "pre2026", "turnover_over_gross") for arm in S}
lim3 = E3_MULT * (tv["NEW_s42"] + tv["NEW_s2027"]) / 2
V["E3"] = {"PASS": bool(tv["NEW_ENS"] <= lim3), "turnover_over_gross_pre2026": tv, "limit_1.05x_mean_single": lim3, "gate": "ENS <= 1.05 x mean(s42, s2027)"}
dd = {arm: pm(arm, "pre2026", "maxdd_5m") for arm in S}
lim4 = min(dd["NEW_s42"], dd["NEW_s2027"]) - E4_TOL
V["E4"] = {"PASS": bool(dd["NEW_ENS"] >= lim4), "maxdd_5m_pre2026_path_mean": dd, "floor": lim4, "gate": "ENS >= min(s42, s2027) - 0.01"}
verdict = "PASS" if all(V[e]["PASS"] for e in ("E1", "E2", "E3", "E4")) else "FAIL"
rec["criteria"] = V; rec["VERDICT"] = verdict
rec["verdict_rule"] = "PASS iff E1..E4 all pass; else FAIL (prereg §3)"

# ─────────── §4.2 capital-level 50/50 ───────────
mix = {}
for s in SEG:
    m = masks[s]; dd_ = days[s]; per_mix = []; per_ens = []
    Dm = []
    for pe_j, p42_j, p27_j in zip(pe, S["NEW_s42"][0], S["NEW_s2027"][0]):
        r42 = daily_on(p42_j["A"][m], p42_j["r"][m], dd_); r27 = daily_on(p27_j["A"][m], p27_j["r"][m], dd_); ren = daily_on(pe_j["A"][m], pe_j["r"][m], dd_)
        rmx = 0.5 * r42 + 0.5 * r27; Dm.append(ren - rmx)
        for rr, lst in ((rmx, per_mix), (ren, per_ens)):
            lst.append({"sharpe": BT.sharpe(rr), "total_return_full_days": float(np.prod(1 + rr) - 1), "worst_day": float(rr.min()),
                        "maxdd_daily": BT.maxdd_nav(np.concatenate([[1.0], np.cumprod(1 + rr)]))})
    agg = lambda L: {k: {"path_mean": float(np.mean([x[k] for x in L])), "n_eff": len(L)} for k in L[0]}
    Dm = np.stack(Dm); x = Dm.mean(0)
    mix[s] = {"MIX_50_50": agg(per_mix), "ENS_same_quantities": agg(per_ens), "dbar_ENS_minus_MIX_bps_per_day": float(1e4 * x.mean()), "n_days": int(len(x))}
    if s == "pre2026": mix[s]["dbar_ENS_minus_MIX_boot_30d"] = boot(x, BLOCK_MAIN)
rec["report_capital_50_50"] = mix


# ─────────── §4.3 target distance, §4.4 publication ───────────
TG = {}
for arm, (p, want) in COMBO.items():
    h = sha(p)
    if want is not None and h != want: raise ValueError(f"combo target sha {arm}")
    Z = np.load(p, allow_pickle=False); TG[arm] = {k: Z[k] for k in ("E_ts", "raw", "weights", "trade_mask", "reason")}; TG[arm]["sha256"] = h
ens_rec = json.load(open(f"{ME}/work/combo_ENS/TARGET_RECEIPT.json"))
if ens_rec["policies"]["scaled_diagnostic"]["sha"] != TG["NEW_ENS"]["sha256"]: raise ValueError("ENS combo sha vs its receipt")
Ec = TG["NEW_s42"]["E_ts"]
for arm in TG:
    if not np.array_equal(TG[arm]["E_ts"], Ec): raise ValueError("combo axes differ")
yrs = np.array([datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).year for t in Ec])
pre = (Ec >= ts(SEG["pre2026"][0])) & (Ec <= ts(SEG["pre2026"][1]))
dist = {}
for x_, y_ in (("NEW_ENS", "NEW_s42"), ("NEW_ENS", "NEW_s2027"), ("NEW_s42", "NEW_s2027")):
    rx, ry = TG[x_]["raw"], TG[y_]["raw"]; ok = (np.abs(rx).sum(1) > 0) & (np.abs(ry).sum(1) > 0)
    l1 = np.abs(rx - ry).sum(1); gm_ = 0.5 * (np.abs(rx).sum(1) + np.abs(ry).sum(1))
    wx, wy = TG[x_]["weights"], TG[y_]["weights"]; okp = TG[x_]["trade_mask"] & TG[y_]["trade_mask"]; l1p = np.abs(wx - wy).sum(1)
    row = {}
    for lab, sel in [(str(y), yrs == y) for y in np.unique(yrs)] + [("pre2026", pre)]:
        a_ = sel & ok; b_ = sel & okp
        row[lab] = {"raw_L1_mean": float(l1[a_].mean()) if a_.any() else None, "raw_mean_gross": float(gm_[a_].mean()) if a_.any() else None,
                    "raw_L1_over_gross": float(l1[a_].mean() / gm_[a_].mean()) if a_.any() else None, "n_eff_raw": int(a_.sum()),
                    "published_both_L1_mean": float(l1p[b_].mean()) if b_.any() else None, "n_eff_published_both": int(b_.sum())}
    dist[f"{x_}|{y_}"] = row
rec["report_target_distance"] = dist
PSEG = {"2023H1_pre_window": ("2023-01-01T00:00:00Z", "2023-06-30T00:00:00Z"), "2023H2": SEG["2023H2"], "2024": SEG["2024"], "2025": SEG["2025"],
        "2026_to_0831": SEG["2026"], "2026-08-31T04Z_to_axis_end": ("2026-08-31T04:00:00Z", iso(Ec[-1]))}
pub = {}
for s, (a0, a1) in PSEG.items():
    sel = (Ec >= ts(a0)) & (Ec <= ts(a1))
    pub[s] = {"anchors": int(sel.sum()), **{f"published_{arm}": int(TG[arm]["trade_mask"][sel].sum()) for arm in TG},
              "differ_ENS_vs_s42": int((TG["NEW_ENS"]["trade_mask"] != TG["NEW_s42"]["trade_mask"])[sel].sum()),
              "differ_ENS_vs_s2027": int((TG["NEW_ENS"]["trade_mask"] != TG["NEW_s2027"]["trade_mask"])[sel].sum()),
              "differ_s42_vs_s2027": int((TG["NEW_s42"]["trade_mask"] != TG["NEW_s2027"]["trade_mask"])[sel].sum()),
              "ENS_reasons": dict(collections.Counter(TG["NEW_ENS"]["reason"][sel].tolist()))}
rec["report_publication"] = pub
er = json.load(open(f"{ME}/receipts/ENS_BUILD.json"))
rec["report_one_seed_only_names"] = er["one_seed_only_names"]
rec["utc_end"] = iso(time.time())
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
for k in ("NEW_s42", "NEW_s2027"):
    x = e1[k]; print(f"ENS_STATS E1 vs {k}: {'PASS' if x['PASS'] else 'FAIL'} est {x['estimate_bps_per_day']:+.3f} bps/d 97.5%CI30 [{x['boot_30d']['ci97.5_two_sided_bps'][0]:+.3f}, {x['boot_30d']['ci97.5_two_sided_bps'][1]:+.3f}] n_days {x['n_days']}", flush=True)
print("ENS_STATS E2 " + ("PASS" if V["E2"]["PASS"] else "FAIL") + " " + " ".join(f"{s}:ENS {e2[s]['ENS']:.3f}/floor {e2[s]['floor']:.3f}" for s in JUDGE), flush=True)
print(f"ENS_STATS E3 {'PASS' if V['E3']['PASS'] else 'FAIL'} ENS {tv['NEW_ENS']:.5f} limit {lim3:.5f}", flush=True)
print(f"ENS_STATS E4 {'PASS' if V['E4']['PASS'] else 'FAIL'} ENS {dd['NEW_ENS']:.4f} floor {lim4:.4f}", flush=True)
print(f"ENS_STATS VERDICT={verdict} receipt_sha256={sha(OUT)}", flush=True)
