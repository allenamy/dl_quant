#!/usr/bin/env python3
"""G2-B″ in-window recursion parity + D17 fund-z impact measurement (PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 3, lead, committed e1f341a7
before this device existed). READ-ONLY; writes only /workspace/uplift_r2_2026-09-13/P2/receipts/G2Bpp_inwindow_recursion.json.
GATE G2-B″: start = Phase 1 reference state at 1788624000 (`ema_state_before`, verbatim AST from replay_driver.py f2ced820…, on snapshot 1789200000 aux.json);
forward the production recursion (shadow_loop_v3.py L341-349, iv from the settlement gap, validated in receipt 2) along the snapshot ledger rows; at EVERY one of the
41 anchors A compare the forwarded state after rows ft <= A-14400 with ref(A): per name |d acc| <= 1e-15 and last_ts equal; names with a valid ref(A) only. Red => stop.
DESCRIPTIVE (not a gate): on the same 41 anchors, fund z computed by the device's own `xz_in_base` (byte-identical shadow_loop_v3_replay.py 4d3bc157…) from
(a) live EMA = ref(A+14400) (state after rows ft <= A) and (b) the G2-B full-history rebuild after rows ft <= A, on the producer's members (weights/{A}.npz
`members`, read-only copies) with the producer's freshness rule (last settlement <= 12h) and base = snapshot base_syms; per anchor Spearman, number of members that
change fund-leg top-decile / bottom-decile membership, and z differences for the 7 D17 names.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_g2bpp_inwindow.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, ast, bisect, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
from scipy.stats import spearmanr
P2 = "/workspace/uplift_r2_2026-09-13/P2"; OUT = f"{P2}/receipts/G2Bpp_inwindow_recursion.json"
assert os.path.realpath(OUT).startswith(P2 + "/")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time()
ANCH = [1788624000 + 14400 * k for k in range(41)]; A0 = ANCH[0]
IN = {"ledger_full": (f"{P2}/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
      "snapshot_aux_1789200000": (f"{P2}/work/snapshots/1789200000/aux.json", "5e825c2f791bb860e9a1d6fb50817719de4acbe54594c9940392bb0640a0260e"),
      "phase1_replay_driver": (f"{P2}/work/phase1_ro/replay_driver.py", "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec"),
      "device_shadow_loop_v3_replay": (f"{P2}/devices/shadow_loop_v3_replay.py", "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"),
      "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
      "prereg": (f"{P2}/work/prereg_ro/PREREG_producer_parity_phase2_oos_2026-09-12.md", None)}
for k, (p, s) in IN.items():
    if s is not None: got = sha(p); assert got == s, (k, got, s)
W_SHA = {}
for A in ANCH:
    p = f"{P2}/work/live_ro/state/weights/{A}.npz"; W_SHA[str(A)] = sha(p)
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "inputs": {k: {"path": p, "sha256": sha(p)} for k, (p, s) in IN.items()},
     "live_weights_sha256": W_SHA, "python": sys.version.split()[0], "numpy": np.__version__, "utc_start": iso(T0)}
R["nvidia_smi_before"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
src = open(IN["phase1_replay_driver"][0]).read(); tree = ast.parse(src)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ema_state_before"]; assert len(fn) == 1
ns = {}; exec(compile(ast.Module(body=fn, type_ignores=[]), "replay_driver.py:ema_state_before", "exec"), ns); ema_state_before = ns["ema_state_before"]
sys.path.insert(0, f"{P2}/devices"); os.environ.setdefault("WIDE_SHADOW_HOME", f"{P2}/work/runs/g2bpp_import_only")
import importlib; dev = importlib.import_module("shadow_loop_v3_replay"); xz_in_base = dev.xz_in_base
AUX = json.load(open(IN["snapshot_aux_1789200000"][0])); assert int(AUX["last_anchor"]) == 1789200000
EMA = AUX["ema"]; LED = {s: [list(r) for r in rows] for s, rows in AUX["ledger_tail"].items()}; BASE = list(AUX["base_syms"])
ALLOWED = [1.0, 2.0, 4.0, 6.0, 8.0]
def snap_iv(gap_s):
    iv = gap_s / 3600.0
    return float(min(ALLOWED, key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))
def step(est, ft, rate, iv):
    rn = rate * (8.0 / iv)
    if est is None: return {"acc": rn, "last_ts": ft}
    a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0))
    return {"acc": est["acc"] + a * (rn - est["acc"]), "last_ts": ft}

# ── GATE G2-B″ ──
ref0 = ema_state_before(A0, EMA, LED)
FW = {}      # s -> (fts, states) forwarded from ref0 along snapshot rows with ft > A0-14400
n_mism0 = 0
for s, est in ref0.items():
    if isinstance(est, tuple): n_mism0 += 1; continue
    e = None if est is None else dict(est); rows = LED.get(s, []); fts = []; sts = []
    for k, r in enumerate(rows):
        if int(r[0]) <= A0 - 14400: continue
        iv = snap_iv(int(r[0]) - int(rows[k - 1][0])) if k else 8.0
        e = step(e, int(r[0]), float(r[1]), iv); fts.append(int(r[0])); sts.append((e["acc"], e["last_ts"]))
    FW[s] = (est, fts, sts)
def fw_state(s, cut):
    est0, fts, sts = FW[s]; k = bisect.bisect_right(fts, cut) - 1
    if k < 0: return None if est0 is None else dict(est0)
    return {"acc": sts[k][0], "last_ts": sts[k][1]}
g_pairs = 0; g_worst = 0.0; g_viol = []; per_anchor = []; n_none = 0; n_mism = 0
for A in ANCH:
    ref = ema_state_before(A, EMA, LED); cut = A - 14400; wA = 0.0; vA = 0
    for s, est in ref.items():
        if est is None: n_none += 1; continue
        if isinstance(est, tuple): n_mism += 1; continue
        if s not in FW: g_viol.append([A, s, "no_forward_state"]); vA += 1; continue
        f = fw_state(s, cut); g_pairs += 1
        if f is None: g_viol.append([A, s, "forward_none"]); vA += 1; continue
        d = abs(f["acc"] - float(est["acc"])); wA = max(wA, d); g_worst = max(g_worst, d)
        if d > 1e-15 or int(f["last_ts"]) != int(est["last_ts"]):
            vA += 1
            if len(g_viol) < 200: g_viol.append([A, s, d, int(f["last_ts"]) == int(est["last_ts"])])
    per_anchor.append({"anchor": A, "utc": iso(A), "worst_abs": wA, "n_violations": vA})
n_viol = sum(p["n_violations"] for p in per_anchor)
R["gate_G2Bpp"] = {"threshold": 1e-15, "n_anchors": len(ANCH), "n_pairs_compared": g_pairs, "worst_abs": g_worst, "n_violation_pairs": n_viol, "violations_first200": g_viol,
                   "n_reference_none": n_none, "n_reference_mismatch": n_mism, "n_ref0_mismatch": n_mism0, "per_anchor": per_anchor,
                   "verdict": "PASS" if (n_viol == 0 and g_pairs > 0) else "RED"}
print(f"G2Bpp_VERDICT {R['gate_G2Bpp']['verdict']} pairs={g_pairs} worst_abs={g_worst:.3e} violation_pairs={n_viol} ref_none={n_none} ref_mismatch={n_mism}", flush=True)

# ── DESCRIPTIVE: D17 fund-z impact on the 41 anchors (not a gate) ──
L = np.load(IN["ledger_full"][0], allow_pickle=True); SY = [str(s) for s in L["symbols"]]; col = {s: j for j, s in enumerate(SY)}
off = L["off"]; FT = L["ft"]; RT = L["rate"]
cfg = json.load(open(IN["bundle_config"][0])); SYMS = cfg["symbols_panel"]; LIVE = cfg["symbols_live"]; assert SYMS == SY
REB = {}
for s in set(EMA) | set(BASE):
    rows = {}
    if s in col:
        j = col[s]
        for k in range(off[j], off[j + 1]): rows[int(FT[k])] = float(RT[k])
    for r in LED.get(s, []): rows[int(r[0])] = float(r[1])
    fts = sorted(rows); sts = []; e = None; prev = None
    for t in fts:
        iv = snap_iv(t - prev) if prev is not None else 8.0
        e = step(e, t, rows[t], iv); sts.append((e["acc"], e["last_ts"])); prev = t
    REB[s] = (fts, sts)
def rb_state(s, cut):
    if s not in REB: return None
    fts, sts = REB[s]; k = bisect.bisect_right(fts, cut) - 1
    return None if k < 0 else {"acc": sts[k][0], "last_ts": sts[k][1]}
def last_settle(s, A):
    rows = [int(r[0]) for r in LED.get(s, []) if int(r[0]) <= A]
    return rows[-1] if rows else None
D17 = ["PROMUSDT", "ACEUSDT", "DEXEUSDT", "ERAUSDT", "BANKUSDT", "ESPORTSUSDT", "1000XECUSDT"]
live_set = set(LIVE); desc = []
for A in ANCH:
    live_state = ema_state_before(A + 14400, EMA, LED)     # state after rows ft <= A (what run_anchor(A) holds after step 4)
    W = np.load(f"{P2}/work/live_ro/state/weights/{A}.npz"); m = W["members"].astype(np.int64); names_m = [SYMS[int(j)] for j in m]
    fe_live = np.full(len(m), np.nan); fe_rb = np.full(len(m), np.nan); bv_live = {}; bv_rb = {}
    for s in BASE:
        ls_ = last_settle(s, A)
        if ls_ is None or A - ls_ > 12 * 3600: continue
        el = live_state.get(s); er = rb_state(s, A)
        if isinstance(el, dict): bv_live[s] = float(el["acc"])
        if er is not None: bv_rb[s] = float(er["acc"])
    for i, s in enumerate(names_m):
        if s not in live_set: continue
        ls_ = last_settle(s, A)
        if ls_ is None or A - ls_ > 12 * 3600: continue
        el = live_state.get(s); er = rb_state(s, A)
        if isinstance(el, dict): fe_live[i] = float(el["acc"])
        if er is not None: fe_rb[i] = float(er["acc"])
    zl = xz_in_base(fe_live, names_m, bv_live); zr = xz_in_base(fe_rb, names_m, bv_rb)
    ok = np.isfinite(zl) & np.isfinite(zr)
    rho = float(spearmanr(zl[ok], zr[ok]).correlation) if ok.sum() > 10 else None
    def dec(z, top):
        okz = np.isfinite(z); q = np.nanquantile(z[okz], 0.9 if top else 0.1)
        return set(np.where(okz & ((z >= q) if top else (z <= q)))[0].tolist())
    top_ch = len(dec(zl, True) ^ dec(zr, True)); bot_ch = len(dec(zl, False) ^ dec(zr, False))
    zd = {s: (float(zr[names_m.index(s)] - zl[names_m.index(s)]) if (s in names_m and np.isfinite(zl[names_m.index(s)]) and np.isfinite(zr[names_m.index(s)])) else None) for s in D17}
    desc.append({"anchor": A, "utc": iso(A), "n_members": int(len(m)), "n_z_both_finite": int(ok.sum()), "n_z_finite_live": int(np.isfinite(zl).sum()), "n_z_finite_rebuild": int(np.isfinite(zr).sum()),
                 "base_vals_live": len(bv_live), "base_vals_rebuild": len(bv_rb), "spearman": rho, "max_abs_z_diff": float(np.nanmax(np.abs(zr - zl))) if ok.any() else None,
                 "n_names_z_changed": int((ok & (zr != zl)).sum()), "top_decile_symdiff": top_ch, "bottom_decile_symdiff": bot_ch, "z_diff_D17": zd})
rhos = [d["spearman"] for d in desc if d["spearman"] is not None]
R["descriptive_D17_fund_z_impact"] = {"NOT_A_GATE": True, "definition": "fund z via device xz_in_base; live = ref(A+4h) state; rebuild = full-history cold start (receipt 2 recursion); members = producer weights npz; base = snapshot base_syms; freshness <= 12h",
                                      "per_anchor": desc, "spearman_min": min(rhos) if rhos else None, "spearman_median": float(np.median(rhos)) if rhos else None,
                                      "top_decile_symdiff_max": max(d["top_decile_symdiff"] for d in desc), "bottom_decile_symdiff_max": max(d["bottom_decile_symdiff"] for d in desc)}
R["runtime_s"] = round(time.time() - T0, 1)
R["nvidia_smi_after"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
json.dump(R, open(OUT, "w"), indent=1)
print("D17_IMPACT spearman_min", R["descriptive_D17_fund_z_impact"]["spearman_min"], "median", R["descriptive_D17_fund_z_impact"]["spearman_median"],
      "top_decile_symdiff_max", R["descriptive_D17_fund_z_impact"]["top_decile_symdiff_max"], "bottom_decile_symdiff_max", R["descriptive_D17_fund_z_impact"]["bottom_decile_symdiff_max"], flush=True)
