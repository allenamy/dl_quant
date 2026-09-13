#!/usr/bin/env python3
"""S2 gates — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (sha bc57266e…) §A6.8 / §A6.9. Independent of the S2 chains.
  S2-FN        executor sources (918559f copies) sha + AST line ranges + resolved conf                                  (blocking)
  S2-P-acc     members-caliber accounting on archived float32 W reproduces archived rec _ex columns, 10 series           (blocking)
               + full − members == independent complement sums                                                           (blocking)
  S2-BOOT      (i) boot() = judge_v4.py AST source; (ii) Δg CI from the ΔSharpe routine's idx == boot() bitwise;
               (iv) vectorised ΔSharpe == explicit re-draws                                                               (blocking)
  S2-BOOT-iii  JUDGE_v4.json cells reproduced                                                                             (NON-blocking)
  S2-DSR       T6 receipt A0 DSR entries reproduced                                                                       (blocking)
  S2-OVL-RED   synthetic overlay scenarios A-D equal the pre-written values of A6.9, cross-checked by an independent hand simulation (blocking)
Writes receipts/S2_GATES.json; prints one S2_GATES summary line; exit 0 iff all blocking gates pass, else 3.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s2_gates.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, math, hashlib, traceback
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p2_s2_lib as L
T0 = time.time()
LIB_SHA = L.sha(L.__file__); SELF_SHA = L.sha(os.path.abspath(__file__))
OUT = dict(device="p2_s2_gates.py", self_sha256=SELF_SHA, lib_sha256=LIB_SHA, prereg_sha256=L.PREREG_SHA, argv=sys.argv, env=dict(os.environ),
           python=sys.version.split()[0], numpy=np.__version__, utc_start=L.iso(time.time()))
def guard(name, fn):
    try:
        r = fn(); OUT[name] = r; return bool(r.get("PASS"))
    except Exception as e:
        OUT[name] = dict(PASS=False, exception=f"{type(e).__name__}: {e}", traceback=traceback.format_exc()[-3000:]); return False

# ───────────── S2-FN ─────────────
EX = CONF = None
def g_fn():
    global EX, CONF
    EX, CONF, info = L.load_executor(); return dict(PASS=True, **info)
FN_OK = guard("S2_FN", g_fn)

# ───────────── S2-P-acc ─────────────
A = L.Acct()
SERIES = [("A0_r3k_s42", "rec", "W"), ("A0_r3k_s2027", "rec", "W"), ("C0_s42", "S0_rec", "S0_W"), ("C0_s42", "d30_n2_c42_rec", "d30_n2_c42_W"),
          ("C0_s2027", "S0_rec", "S0_W"), ("C0_s2027", "d30_n2_c42_rec", "d30_n2_c42_W"), ("NW_s42", "S0_rec", "S0_W"), ("NW_s42", "d30_n2_c42_rec", "d30_n2_c42_W"),
          ("NW_s2027", "S0_rec", "S0_W"), ("NW_s2027", "d30_n2_c42_rec", "d30_n2_c42_W")]
TOL_BPS = 1e-4; TOL_GROSS = 1e-6; TOL_ID = 1e-9
def g_pacc():
    res = {}; ok = True
    for key, rk, wk in SERIES:
        s = L.archive_series(key, rk, wk)
        if s["cfg"] is not None:
            cfg = s["cfg"]; assert cfg["CAL"] == "log" and cfg["MEMBERS_TOPN"] == 829 and cfg["UMASK_SCOPE"] == "m1" and cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json"), cfg
        W64 = s["W"].astype(np.float64); X = np.stack([L.smr(W64[t]) for t in range(len(W64))]); gt = np.abs(W64).sum(1)
        acc = A.account(s["ts"], X, gt, "members"); rec = s["rec"]
        d = {c: float(np.max(np.abs(acc[:, j] - rec[:, L.C[c]]))) for j, c in enumerate(("pnl_ex", "carry_ex", "cost_ex", "net_ex"))}
        d["gross_total"] = float(np.max(np.abs(acc[:, 4] - rec[:, L.C["gross_total"]])))
        row = dict(archive=s["path"], sha256=s["sha256"], rec_key=rk, W_key=wk, maxabs=d, PASS=bool(all(d[c] <= TOL_BPS for c in ("pnl_ex", "carry_ex", "cost_ex", "net_ex")) and d["gross_total"] <= TOL_GROSS))
        if key.startswith("A0_r3k"):   # full − members == complement sums (independent sum set)
            full = A.account(s["ts"], X, gt, "full")
            comp = A.account(s["ts"], X, gt, "full", subset=lambda i, j: np.setdiff1d(A.ALL, A.members(i, j), assume_unique=True))
            ident = {c: float(np.max(np.abs((full[:, jj] - acc[:, jj]) - comp[:, jj]))) for jj, c in enumerate(("pnl_ex", "carry_ex", "cost_ex"))}
            row["full_minus_members_vs_complement_maxabs"] = ident; row["full_identity_PASS"] = bool(all(v <= TOL_ID for v in ident.values()))
            row["PASS"] = bool(row["PASS"] and row["full_identity_PASS"])
        res[f"{key}:{rk}"] = row; ok = ok and row["PASS"]
    return dict(PASS=ok, tol_bps=TOL_BPS, tol_gross=TOL_GROSS, tol_identity=TOL_ID, series=res)
PACC_OK = guard("S2_P_acc", g_pacc)

# ───────────── S2-BOOT (i)(ii)(iv) + iii ─────────────
BOOT, BOOT_INFO = L.load_judge_boot(); ST = L.Stats(BOOT)
def g_boot():
    res = dict(i=dict(PASS=True, **BOOT_INFO)); ii = {}; ok2 = True
    for seed in ("42", "2027"):
        x = L.archive_series(f"C0_s{seed}", "S0_rec"); y = L.archive_series(f"C0_s{seed}", "d30_n2_c42_rec"); W = L.windows(x["ts"])
        for wn, m in W.items():
            for k in (0, 9):
                lo, hi, p = BOOT((x["g"] - y["g"])[m], x["ts"][m] // 86400, np.random.default_rng([20260905, k]))
                q = ST.pair_same_idx(x["g"][m], y["g"][m], x["ts"][m] // 86400, k)
                same = bool(lo == q["dg_ci95"][0] and hi == q["dg_ci95"][1] and p == q["dg_p_gt0"])
                ii[f"s{seed}_{wn}_k{k}"] = dict(boot=[lo, hi, p], same_idx=[q["dg_ci95"][0], q["dg_ci95"][1], q["dg_p_gt0"]], bitwise=same); ok2 = ok2 and same
    res["ii"] = dict(PASS=ok2, cells=ii)
    x = L.archive_series("C0_s42", "S0_rec"); y = L.archive_series("C0_s42", "d30_n2_c42_rec"); m = L.windows(x["ts"])["W_FULL"]
    xa, ya, days = x["g"][m], y["g"][m], x["ts"][m] // 86400; q = ST.pair_same_idx(xa, ya, days, 0); r, inv = q["idx"], q["inv"]
    ud = np.unique(days); rows_of = [np.nonzero(inv == u)[0] for u in range(len(ud))]
    ud_, inv_ = np.unique(days, return_inverse=True)
    nd = len(ud_); c = np.bincount(inv_).astype(float); n = c[r].sum(1)
    def srb(v):
        s_ = np.bincount(inv_, v)[r].sum(1); q_ = np.bincount(inv_, v * v)[r].sum(1); mm = s_ / n; vv = (q_ - n * mm * mm) / (n - 1); return mm / np.sqrt(vv) * L.ANN
    vec = srb(xa) - srb(ya); mx = 0.0
    for b in range(20):
        rows = np.concatenate([rows_of[u] for u in r[b]]); mx = max(mx, abs((L.SR(xa[rows]) - L.SR(ya[rows])) - vec[b]))
    res["iv"] = dict(PASS=bool(mx <= 1e-9), max_abs_diff=float(mx), draws_checked=20)
    res["PASS"] = bool(res["i"]["PASS"] and res["ii"]["PASS"] and res["iv"]["PASS"])
    return res
BOOT_OK = guard("S2_BOOT", g_boot)
DEV_V4 = {"A0_dyn_s42": ("88283c5f05b5d6b5213ca45f20577a3060a4831f72c6169c6efea8588cea1419"), "A0_dyn_s2027": ("6b40d13ddf6b676a775214711f8520225c01c54018bbdaf6ea82c9e75f2acabd"),
          "A1_dyn_s42": ("ecc00b7bcd8f911963fef4bcaf5602e0a689ab1d7f843abf71349ec6a4818308"), "A1_dyn_s2027": ("8679a43a6cdd5ed6acbfaf9a68143733715e28ba9935c42243f3c5cc16a0c17d"),
          "A2_dyn_s42": ("fcc30b05e21207c559f82ef23ae6ee778f4b1764e03a5dd8e3809774966f1a94")}
def g_boot_iii():
    J = json.load(open(L.pinned("JUDGE_v4_json")))["contrasts"]; res = {}; ok = True
    FRZ = (L.ut(2025, 3, 1), L.ut(2026, 8, 10, 20) + 1)
    def load(tag):
        p = f"{L.HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{tag}.npz"; got = L.sha(p); assert got == DEV_V4[tag], (tag, got)
        R = np.load(p, allow_pickle=True)["d30_n2_c42_rec"]; t = np.round(R[:, 0]).astype(np.int64); return t, R[:, L.C["net_ex"]] / R[:, L.C["gross_total"]]
    for (a, b, s, ci) in (("A1", "A0", "42", 0), ("A1", "A0", "2027", 0), ("A2", "A0", "42", 1)):
        ta, ga = load(f"{a}_dyn_s{s}"); tb, gb = load(f"{b}_dyn_s{s}"); assert np.array_equal(ta, tb)
        m = (ta >= FRZ[0]) & (ta < FRZ[1]); d = (ga - gb)[m]; lo, hi, p = BOOT(d, ta[m] // 86400, np.random.default_rng([20260905, ci]))
        ref = J[f"{a}-{b}|dyn|s{s}"]; cell = dict(mine=dict(delta=float(d.mean()), ci95=[lo, hi], p_gt0=p, n=int(m.sum())), judge=ref,
                                                   PASS=bool(abs(float(d.mean()) - ref["delta"]) <= 1e-12 and abs(lo - ref["ci95"][0]) <= 1e-12 and abs(hi - ref["ci95"][1]) <= 1e-12 and p == ref["p_gt0"] and ref["rng"] == [20260905, ci]))
        res[f"{a}-{b}|dyn|s{s}"] = cell; ok = ok and cell["PASS"]
    return dict(PASS=ok, blocking=False, cells=res)
guard("S2_BOOT_iii_nonblocking", g_boot_iii)

# ───────────── S2-DSR ─────────────
PSR, SR0, T6_INFO = L.load_t6_dsr()
def g_dsr():
    R = json.load(open(L.pinned("t6_receipt")))["RESULTS"]; res = {}; ok = True
    FIELDS = ("SR_annual", "skew", "kurt", "SR0_annual_N_eff", "SR0_annual_N_300", "P_true_SR_gt_0_N_eff", "P_true_SR_gt_3_N_eff", "P_true_SR_gt_0_N_300", "P_true_SR_gt_3_N_300")
    for seed, wins in (("42", ("W_FULL", "FROZEN", "W_ALPHA")), ("2027", ("W_FULL", "FROZEN"))):
        s = L.archive_series(f"A0_r3k_s{seed}", "rec"); W = L.windows(s["ts"])
        for wn in wins:
            blk = R[f"F1_s{seed}"][wn]["DSR"]; ref = blk["A0"]; assert ref["member"].endswith(f"A0_PWR230k_s{seed}"), ref["member"]
            x = s["g"][W[wn]]; assert len(x) == blk["T"]
            mine = L.dsr_member(x, blk["V_SR_pp"], blk["N_eff"], PSR, SR0)
            diffs = {f: abs(mine[f] - ref[f]) for f in FIELDS}
            cell = dict(T=blk["T"], V_SR_pp=blk["V_SR_pp"], N_eff=blk["N_eff"], mine={f: mine[f] for f in FIELDS}, t6={f: ref[f] for f in FIELDS}, maxabs=max(diffs.values()),
                        PASS=bool(max(diffs.values()) <= 1e-9))
            res[f"F1_s{seed}_{wn}"] = cell; ok = ok and cell["PASS"]
    return dict(PASS=ok, tol=1e-9, t6=T6_INFO, cells=res)
DSR_OK = guard("S2_DSR", g_dsr)

# ───────────── S2-OVL-RED (A6.9) ─────────────
SY = ["N0", "N1", "N2", "N3", "N4", "N5"]; NA = 61; TS = np.array([L.ut(2025, 3, 1) + 14400 * t for t in range(NA)], np.int64)
WA_ = np.array([0.20, 0.15, 0.15, -0.20, -0.15, -0.15]); WC_ = np.array([1e-5, 0.35 - 1e-5, 0.15, -0.20, -0.15, -0.15])
def prices(kind):
    Y = np.zeros((NA, 6))
    if kind in ("A", "C", "D"): Y[2, 0] = -0.40
    if kind == "B": Y[2, 0] = -0.40; Y[3, 0] = 1.00
    return Y
def hand_A(variant):
    """Independent step-by-step simulation of scenario A (no executor code; per_name_stop / clamp / reshape semantics written out for this book only).
    Returns the expected accounting rows X (NA, 6)."""
    G = L.LEV * L.NAV_REF; Y = prices("A"); X = np.zeros((NA, 6))
    q0 = 0.0; avg0 = 0.0; P0 = 1.0; cnt = 0; stopped = False; cool_until = None
    rest_pop = WA_[1:] - WA_[1:].mean(); rest_pop = rest_pop / np.abs(rest_pop).sum()
    for t in range(NA):
        now = float(TS[t]); in_cool = cool_until is not None and cool_until > now
        # plan
        if variant == "STOP" and (stopped or in_cool):
            X[t, 0] = 0.0; X[t, 1:] = rest_pop
        elif variant == "PINNED" and stopped:
            v = WA_.copy(); v[0] = 0.0; v = v - v.mean(); v = v / np.abs(v).sum()
            cur = q0 * P0 / G; tgt = v[0]
            if tgt * cur > 0 and abs(tgt) <= abs(cur): x0 = tgt
            elif tgt * cur > 0: x0 = cur
            else: x0 = 0.0
            X[t] = v; X[t, 0] = x0
        else:
            X[t] = WA_
        # fill at P0
        N0 = X[t, 0] * G; newq = N0 / P0
        if newq != 0 and q0 != 0 and np.sign(newq) == np.sign(q0) and abs(newq) > abs(q0): avg0 = (q0 * avg0 + (newq - q0) * P0) / newq
        elif newq != 0 and (q0 == 0 or np.sign(newq) != np.sign(q0)): avg0 = P0
        elif newq == 0: avg0 = 0.0
        q0 = newq
        # readback: 1) stopped and flat -> cooldown  2) cooldown expiry  3) depth counting for names neither stopped nor cooling
        if stopped and abs(N0) < 5.0:
            stopped = False; cool_until = now + 7 * 86400.0
        if cool_until is not None and cool_until <= now:
            cool_until = None
        if not stopped and cool_until is None:
            if abs(N0) >= 5.0:
                depth = q0 * (P0 - avg0) / abs(N0)
                if depth <= -0.30:
                    cnt += 1
                    if cnt >= 2:
                        stopped = True; cnt = 0
                else:
                    cnt = 0
            else:
                cnt = 0
        P0 = P0 * (1.0 + Y[t, 0])
    return X
def g_ovl():
    res = {}; ok = True
    def runs(W_row, kind, conf):
        W = np.tile(W_row, (NA, 1)); Y = prices(kind); outs = {}
        for v in ("STOP", "PINNED"):
            ov = L.Overlay(EX, conf, SY, v, trace_names=("N0",)); X, gross, ev, tr = ov.run(TS, W, lambda t: Y[t]); outs[v] = (X, ev, tr)
        outs["NOSTOP"] = np.stack([L.smr(W[t]) for t in range(NA)])
        return outs
    tol = 1e-12
    # scenario A
    o = runs(WA_, "A", CONF); XS, evS, trS = o["STOP"]; XP, evP, trP = o["PINNED"]; XN = o["NOSTOP"]
    stop_anchor_S = [t for t in range(NA) if trS[t]["N0"]["stopped"] and (t == 0 or not trS[t - 1]["N0"]["stopped"])]
    stop_anchor_P = [t for t in range(NA) if trP[t]["N0"]["stopped"] and (t == 0 or not trP[t - 1]["N0"]["stopped"])]
    restS = np.array([0.25, 0.25, -4 / 19, -11 / 76, -11 / 76]); restP = np.array([11 / 48, 11 / 48, -5 / 24, -7 / 48, -7 / 48])
    chkA = dict(
        depth_t3=abs(trS[3]["N0"]["depth"] - (-0.40)) <= tol, depth_t4=abs(trS[4]["N0"]["depth"] - (-0.40)) <= tol, avg_t3=abs(trS[3]["N0"]["avg"] - 0.84) <= tol,
        stop_trigger_t4_STOP=stop_anchor_S == [4], stop_trigger_t4_PINNED=stop_anchor_P == [4],
        STOP_zero_t5_46=bool(np.all(XS[5:47, 0] == 0.0)), STOP_positive_t4_t47=bool(XS[4, 0] > 0 and XS[47, 0] > 0),
        STOP_rest_t5_46=bool(np.max(np.abs(XS[5:47, 1:] - restS)) <= tol), STOP_reentry_t47_equals_W=bool(np.max(np.abs(XS[47:] - WA_)) <= tol),
        STOP_one_cooldown=evS["cooldown_entries"] == 1 and evS["stop_triggers"] == 1 and evS["stop_long"] == 1,
        PINNED_x0_1_24_t5_60=bool(np.max(np.abs(XP[5:, 0] - 1 / 24)) <= tol), PINNED_rest=bool(np.max(np.abs(XP[5:, 1:] - restP)) <= tol),
        PINNED_never_cooldown=evP["cooldown_entries"] == 0 and evP["final_state"]["n_stopped"] == 1,
        NOSTOP_equals_W=bool(np.max(np.abs(XN - WA_)) <= tol), pre_trigger_equal=bool(np.max(np.abs(XS[:5] - XN[:5])) <= tol and np.max(np.abs(XP[:5] - XN[:5])) <= tol))
    hS = hand_A("STOP"); hP = hand_A("PINNED")
    chkA["hand_sim_STOP"] = bool(np.max(np.abs(hS - XS)) <= tol); chkA["hand_sim_PINNED"] = bool(np.max(np.abs(hP - XP)) <= tol)
    res["A"] = dict(checks=chkA, PASS=all(chkA.values()), stop_events=[evS["stop_events"], evP["stop_events"]], hand_maxabs=[float(np.max(np.abs(hS - XS))), float(np.max(np.abs(hP - XP)))])
    # scenario B
    o = runs(WA_, "B", CONF); XS, evS, trS = o["STOP"]; XP, evP, trP = o["PINNED"]; XN = o["NOSTOP"]
    chkB = dict(counter_t3=trS[3]["N0"]["counter"] == 1, counter_reset_t4=trS[4]["N0"]["counter"] is None, depth_t4=abs(trS[4]["N0"]["depth"] - 0.30) <= tol,
                no_stops=evS["stop_triggers"] == 0 and evP["stop_triggers"] == 0, equal=bool(np.max(np.abs(XS - XN)) <= tol and np.max(np.abs(XP - XN)) <= tol))
    res["B"] = dict(checks=chkB, PASS=all(chkB.values()))
    # scenario C (dust)
    o = runs(WC_, "C", CONF); XS, evS, trS = o["STOP"]; XP, evP, trP = o["PINNED"]; XN = o["NOSTOP"]
    chkC = dict(n0_notional_below_5=all(abs(tr["N0"]["N"]) < 5.0 for tr in trS), never_counted=all(tr["N0"]["counter"] is None for tr in trS + trP),
                no_stops=evS["stop_triggers"] == 0 and evP["stop_triggers"] == 0, equal=bool(np.max(np.abs(XS - XN)) <= tol and np.max(np.abs(XP - XN)) <= tol))
    res["C"] = dict(checks=chkC, PASS=all(chkC.values()))
    # scenario D (disabled)
    conf_off = dict(CONF); conf_off["enabled"] = False
    o = runs(WA_, "D", conf_off); XS, evS, _ = o["STOP"]; XP, evP, _ = o["PINNED"]; XN = o["NOSTOP"]
    chkD = dict(no_events=evS["stop_triggers"] == 0 and evP["stop_triggers"] == 0 and evS["cooldown_entries"] == 0, equal=bool(np.max(np.abs(XS - XN)) <= tol and np.max(np.abs(XP - XN)) <= tol))
    res["D"] = dict(checks=chkD, PASS=all(chkD.values()))
    return dict(PASS=all(res[k]["PASS"] for k in "ABCD"), tol=tol, scenarios=res)
OVL_OK = guard("S2_OVL_RED", g_ovl) if FN_OK else (OUT.__setitem__("S2_OVL_RED", dict(PASS=False, why="S2-FN failed; executor functions unavailable")) or False)

BLOCKING = dict(S2_FN=FN_OK, S2_P_acc=PACC_OK, S2_BOOT=BOOT_OK, S2_DSR=DSR_OK, S2_OVL_RED=OVL_OK)
OUT["blocking"] = BLOCKING; OUT["ALL_BLOCKING_PASS"] = bool(all(BLOCKING.values())); OUT["runtime_s"] = round(time.time() - T0, 1); OUT["utc_end"] = L.iso(time.time())
rp = L.P2 + "/receipts/S2_GATES.json"; assert os.path.realpath(rp).startswith(L.P2 + "/")
json.dump(OUT, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
pacc = OUT.get("S2_P_acc", {}).get("series", {})
worst = max((max(v["maxabs"][c] for c in ("pnl_ex", "carry_ex", "cost_ex", "net_ex")) for v in pacc.values()), default=float("nan"))
print("S2_GATES " + " ".join(f"{k}={'PASS' if v else 'RED'}" for k, v in BLOCKING.items()),
      "S2_BOOT_iii_nonblocking=%s" % ("PASS" if OUT.get("S2_BOOT_iii_nonblocking", {}).get("PASS") else "NOT_REPRODUCED"),
      "pacc_worst_maxabs_bps=%.3e" % worst, "ALL_BLOCKING_PASS=%s" % OUT["ALL_BLOCKING_PASS"], "runtime_s=%s" % OUT["runtime_s"], "receipt_sha256=%s" % L.sha(rp), flush=True)
sys.exit(0 if OUT["ALL_BLOCKING_PASS"] else 3)
