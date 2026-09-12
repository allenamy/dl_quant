"""r20 STEP 3 — falsifiability matrix for v4e_gate_export_v2.py (gate mode + require mode) on an ISOLATED synthetic world.

The world is built once: a small panel/meta/predictions on which the ORIGINAL E1–E4 code passes by construction (fold-IC base := the
re-derived ICs; the v1iv replay Sharpe is bisected into the frozen band by scaling y4), four judged books per arm and four baseline
(A0-role) books whose arrays satisfy the replay device's exact identities, a cost json / mask / king file / FEMAT with real shas, a
BOUND signal receipt written by gate_signal_parity_v2.py, and an ISOLATED contract = the frozen contract + the PROPOSED2 BUNDLE_export
fill with THIS world's shas. The frozen contract, the live tree and every real receipt are untouched.

Every case copies the world, applies ONE mutation, runs the gate CLI (subprocess, explicit env) and/or the require CLI, and records
PASS/FAIL + the NAMED failing checks. Expectations are asserted; the receipt records observed vs expected for every row.
ENV (whitelist): R20_ROOT (scratch root), R20_OUT (receipt dir), R20_KEEP=1 (keep case dirs). Exit 0 iff every row meets expectation.
"""
import os, sys, json, time, shutil, hashlib, subprocess, calendar, gzip
from pathlib import Path
import numpy as np

REPO = Path("/Users/haosiyu/Desktop/quant_research")
INFRA2 = REPO / "multi_asset/exports/research/uplift_2026-09-11/infra2"
CHAIN = REPO / "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
GATE_V2 = INFRA2 / "v4e_gate_export_v2.py"; SIG_V2 = INFRA2 / "gate_signal_parity_v2.py"
ROOT = Path(os.environ.get("R20_ROOT", Path.home() / "cc_tmp/r20_matrix"))
OUT = Path(os.environ.get("R20_OUT", REPO / "multi_asset/exports/research/uplift_2026-09-11/r20_gate_closure/receipts"))
KEEP = os.environ.get("R20_KEEP") == "1"
ENV_WHITELIST = {k: os.environ.get(k) for k in ("R20_ROOT", "R20_OUT", "R20_KEEP")}
PY = sys.executable
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0, str(INFRA2)); import v4e_gate_export_v2 as G  # noqa: E402  (importing the module runs nothing: main is guarded)

COLS = G.COLS; C = G.C; NS = 120; ARM_F = "ARMX"; ARM_N = "ARMY"; BASE_ARM = "A0"
DEV_SHA = "8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d"
TIERS = [[1.8001, 4.5001, 0.8511], [1.799, 4.4988, 0.9246], [1.7998, 4.5002, 0.921]]
BOOK_ENV = {"CAL": "log", "LEGS": "101", "PHI": 0.45, "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "FTRIM": "zero", "UMASK_SCOPE": "m1",
            "REF_SKIP": 0, "KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "TRADE_TOPN": 0}
THRESHOLDS = {"guard_band": [2.27, 2.57], "n_frozen": 3168, "frozen_window_utc": ["2025-03-01T00:00Z", "2026-08-10T20:00Z"],
              "ic_tol": {"2024": 0.004, "2025": 0.004, "2026": 0.006}, "sharpe_claim_tol": 0.005, "identity_tol": 1e-9, "w_gross_tol": 1e-6,
              "turnover_tol": 1e-6, "netlong_tol": 1e-6, "gross_max": 1.000001, "gross_ratio_band": [0.6, 1.6], "gross_ratio_median_band": [0.8, 1.25]}
SIG_THRESHOLDS = {"NEW_rankdata_rows_failing_rerank_identity_max": 0, "OLD_argsort_rows_failing_rerank_identity_min": 1,
                  "NEW_float32_roundtrip_rows_failing_max": 0, "femat_ts_aligned": True, "femat_symbols_aligned": True, "rows_min": 1}
WORLD = ROOT / "world"; ACTIVE = ROOT / "case_active"           # config_json paths point through the ACTIVE symlink -> current case dir
T = G.T


def grid(t0, t1): return np.arange(t0, t1, 14400, dtype=np.int64)


# ------------------------------------------------------------------------------------------------------------- world
def build_world():
    if ROOT.exists(): shutil.rmtree(ROOT)
    for d in ("v4chain", "data", "bundle", "hc/dev_v4/probe_artifacts", "hc/calib", "hc/masks", "hc/king", "sig"): (WORLD / d).mkdir(parents=True)
    rng = np.random.default_rng(20260912); info = {}
    syms = [f"S{k:03d}" for k in range(NS)]
    # --- panel + meta + predictions (E3/E4 world) ---
    ts = grid(T(2024, 1, 1), T(2026, 9, 1)); nA = len(ts)
    base_y = rng.normal(0, 0.01, (nA, NS)); PRED = (base_y + rng.normal(0, 0.02, (nA, NS))).astype(np.float32)
    R24 = -0.5 * base_y + rng.normal(0, 0.01, (nA, NS)); FE = np.round(0.5 * base_y + rng.normal(0, 0.01, (nA, NS)), 3)   # ties -> the ORDINAL ranker fails (S_BITWISE needs OLD>0)
    FN = rng.normal(0, 1e-4, (nA, NS)); IV = np.full((nA, NS), 8.0)
    members = np.empty(nA, dtype=object)
    for i in range(nA): members[i] = np.arange(NS)
    qvk = np.full((nA, NS), 12.0); names = [f"f{k:03d}" for k in range(60)] + ["ret5_sum_48_x", "ret5_sum_288_x"]
    PW = {"ts": ts, "symbols": np.array(syms), "f_rev_24h": R24, "f_fund_ema_v1": FE, "f_fund_now": FN, "f_fund_iv": IV}
    # bisect the y4 scale so the replay Sharpe(2024on) lands in the frozen band (a fixture that passes the ORIGINAL E4 code by construction)
    def sharpe_at(s):
        MT = {"E_ts": ts, "members": members, "y4": s * base_y, "qvk": qvk}
        return G.e4_sharpe(PRED, MT, PW)[0]
    lo, hi = 1e-3, 3.0; s_lo, s_hi = sharpe_at(lo), sharpe_at(hi); assert s_lo < 2.27 < 2.57 < s_hi, (s_lo, s_hi)
    for _ in range(40):
        mid = (lo * hi) ** 0.5; sm = sharpe_at(mid)
        if 2.30 <= sm <= 2.54: break
        if sm < 2.42: lo = mid
        else: hi = mid
    s_star = mid; y4 = s_star * base_y; MT = {"E_ts": ts, "members": members, "y4": y4, "qvk": qvk}
    sh = G.e4_sharpe(PRED, MT, PW)[0]; ic = G.e3_ic(PRED, MT); info.update({"y4_scale": s_star, "sharpe_2024on": sh, "ic": {str(k): v for k, v in ic.items()}, "n_anchors_panel": nA})
    np.savez(WORLD / "data/wide_fea_v4_meta.npz", E_ts=ts, members=members, y4=y4, qvk=qvk, names=np.array(names))
    np.savez(WORLD / "data/wide_panel_4h_v3splice.npz", **PW)
    np.save(WORLD / "data/wide_fea_v4.npy", np.zeros((4, 4), np.float32)); np.savez(WORLD / "data/cache.npz", ts=ts[:5])
    with gzip.open(WORLD / "data/fund_aug.json.gz", "wt") as f: json.dump({"rates": {}, "intervals": {}}, f)
    json.dump({"ic": {str(k): float(v) for k, v in ic.items()}}, open(WORLD / "data/slow_scorer_v4base.json", "w"))
    keep_names = [n for n in names if not (n.startswith("ret5_sum_48") or n.startswith("ret5_sum_288"))]
    pins = {"keep_names": keep_names, "symbols_live": syms[:50]}; json.dump(pins, open(WORLD / "data/live_pins.json", "w"), indent=1)
    # --- bundle ---
    B = WORLD / "bundle"; np.save(B / "slow_pred_pinned.npy", PRED)
    (B / "slow2026.txt").write_text("tree\nversion=v4\n"); np.savez(B / "cache_tail_40d.npz", ts=ts[-5:]); np.savez(B / "leg_returns.npz", ts=ts[:5])
    json.dump({s: {"acc": 0.0, "last_ts": 0} for s in syms[:3]}, open(B / "fund_ema_v1_state.json", "w")); json.dump({}, open(B / "funding_ledger_seed.json", "w")); json.dump({}, open(B / "parity_signals_aug.json", "w"))
    json.dump({"symbols_panel": syms, "symbols_live": pins["symbols_live"], "keep_idx": list(range(60)), "keep_names": keep_names, "params": dict(G.FROZEN_PARAMS),
               "provenance": {"built_utc": "fixture", "generation": "fixture", "base_ic": {str(k): float(v) for k, v in ic.items()},
                              "fold_ic_2024": round(ic[2024], 4), "fold_ic_2025": round(ic[2025], 4), "pinned_ic2026": round(ic[2026], 4), "pinned_sharpe_full_b": round(sh, 2)}},
              open(B / "config.json", "w"), indent=1)
    man = {f: sha(B / f) for f in sorted(os.listdir(B)) if f != "MANIFEST.json"}; json.dump(man, open(B / "MANIFEST.json", "w"), indent=1)
    # --- cost json / mask / king / femat ---
    json.dump({"tiers": [{"name": f"tier{i}", "maker_bps": t[0], "taker_bps": t[1], "maker_share": t[2]} for i, t in enumerate(TIERS)], "source": "fixture = pinned costb_fee_steady tiers"},
              open(WORLD / "hc/calib/costb.json", "w"), indent=1)
    np.savez(WORLD / "hc/masks/umask.npz", mask=np.ones((5, NS), bool)); np.save(WORLD / "hc/king/SLOW.npy", PRED)
    ZF = G.xz(FE[0])[None, :]; ZF = np.vstack([G.xz(FE[i]) for i in range(nA)])
    np.savez(WORLD / "sig/femat.npz", symbols=np.array(syms), ts=ts, mat=ZF.astype(np.float64))
    # --- books: baseline (A0 role) + two arms (with / without FEMAT) satisfying the device identities ---
    bts = grid(T(2025, 2, 26), T(2026, 8, 31, 4)); nb = len(bts); info["n_book_rows"] = nb
    def w_path(r, g_level):
        W = np.zeros((nb, NS)); w = np.zeros(NS)
        for t in range(nb):
            tgt = r.normal(0, 1, NS); tgt -= tgt.mean(); tgt /= np.abs(tgt).sum(); g = g_level * (1 + 0.25 * np.sin(t / 97.0))
            w = w + 0.35 * (g * tgt - w); W[t] = w
        return W.astype(np.float32)
    def rec_from(W, r):
        W64 = W.astype(np.float64); sw = np.abs(W64).sum(1); to = np.abs(np.diff(W64, axis=0)).sum(1); to = np.concatenate([[sw[0]], to])
        R = np.zeros((nb, len(COLS))); R[:, C["ts"]] = bts; R[:, C["gross_total"]] = sw; R[:, C["gross_member"]] = sw; R[:, C["gross_sel"]] = sw
        R[:, C["nsel"]] = 100; R[:, C["nmember"]] = NS; R[:, C["turnover"]] = to; R[:, C["netlong"]] = W64.sum(1) / sw
        R[:, C["w3_king"]] = 0.3; R[:, C["w3_fund"]] = 0.7
        cost = to * 2.10; cex = cost * 0.98; pnl = r.normal(1.5, 4, nb); pex = pnl + r.normal(0, 0.1, nb); car = r.normal(0.5, 0.3, nb); cex_ = car + r.normal(0, 0.05, nb)
        R[:, C["cost"]] = cost; R[:, C["cost_ex"]] = cex; R[:, C["pnl"]] = pnl; R[:, C["pnl_ex"]] = pex; R[:, C["carry"]] = car; R[:, C["carry_ex"]] = cex_
        R[:, C["net"]] = pnl - car - cost; R[:, C["net_ex"]] = pex - cex_ - cex
        for k in ("leg_king", "leg_rev24", "leg_fund"): R[:, C[k]] = r.normal(0, 1, nb)
        return R
    def cfg(seat, seed, femat):
        return {"COSTB_JSON": str(ACTIVE / "hc/calib/costb.json"), "COST_B": TIERS, **{k: BOOK_ENV[k] for k in BOOK_ENV},
                "FEMAT_NPZ": (str(ACTIVE / "sig/femat.npz") if femat else None), "SLOW_NPY": str(ACTIVE / "hc/king/SLOW.npy"),
                "W3FIX": ("0.21,0,0.79" if seat == "fix" else None), "UMASK_NPZ": str(ACTIVE / "hc/masks/umask.npz"), "FSEED": seed, "FPRED": f"f10_fixture_s{seed}.npy",
                "HEALTH": {"device": "fixture (device string not checked; sha is)", "device_sha256": DEV_SHA}}
    P = WORLD / "hc/dev_v4/probe_artifacts"; base_sha = {}
    for si, (seat, seed) in enumerate(G.SEATS):
        rb = np.random.default_rng(100 + si); Wb = w_path(rb, 0.75 if seat == "fix" else 0.65); Rb = rec_from(Wb, rb)
        pb = P / f"w10_ablation_series_V4_{BASE_ARM}_{seat}_s{seed}.npz"
        np.savez(pb, cols=np.array(COLS), symbols=np.array(syms), config_json=np.array(json.dumps(cfg(seat, seed, False))), d30_n2_c42_rec=Rb, d30_n2_c42_W=Wb)
        base_sha[f"{seat}_s{seed}"] = sha(pb)
        ratio = 1 + 0.08 * np.sin(np.arange(nb) / 41.0 + si)                     # legitimate arm: per-anchor gross ratio in [0.92, 1.08]
        Wa = (Wb.astype(np.float64) * ratio[:, None]).astype(np.float32); ra = np.random.default_rng(200 + si); Ra = rec_from(Wa, ra)
        for arm, fem in ((ARM_F, True), (ARM_N, False)):
            np.savez(P / f"w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz", cols=np.array(COLS), symbols=np.array(syms), config_json=np.array(json.dumps(cfg(seat, seed, fem))), d30_n2_c42_rec=Ra, d30_n2_c42_W=Wa)
    # --- isolated contract: frozen + PROPOSED2-style BUNDLE_export fill with THIS world's shas ---
    shutil.copy(CHAIN / "v4_gate_common.py", WORLD / "v4chain/v4_gate_common.py")
    contract = json.load(open(CHAIN / "ELIGIBILITY_CONTRACT.json"))
    contract["gates"]["BUNDLE_export"] = {
        "source": "v4e_gate_export_v2.py", "approved_source_sha256": [sha(GATE_V2)],
        "approved_baseline": {"device_sha256": DEV_SHA, "costb_json_sha256": sha(WORLD / "hc/calib/costb.json"), "costb_tiers": TIERS,
                              "umask_npz_sha256": sha(WORLD / "hc/masks/umask.npz"), "live_pins_sha256": sha(WORLD / "data/live_pins.json"),
                              "bundle_base_sha256": sha(WORLD / "data/slow_scorer_v4base.json"), "baseline_arm": BASE_ARM, "baseline_books_sha256": base_sha,
                              "book_env": BOOK_ENV, "thresholds": THRESHOLDS,
                              "signal_gates": {"S_BITWISE_signal": {"source": "gate_signal_parity_v2.py", "approved_source_sha256": [sha(SIG_V2)], "thresholds": SIG_THRESHOLDS}}},
        "note": "ISOLATED TEST CONTRACT (r20 fixture world) — not the frozen file, not the PROPOSED2 file"}
    json.dump(contract, open(WORLD / "v4chain/ELIGIBILITY_CONTRACT.json", "w"), indent=1)
    # --- bound signal receipt for the FEMAT arm (real gate_signal_parity_v2.py run) ---
    env = {**os.environ, "SIG_PANEL": str(WORLD / "data/wide_panel_4h_v3splice.npz"), "SIG_FEMAT": str(WORLD / "sig/femat.npz"), "SIG_ARM": ARM_F,
           "V4CHAIN_DIR": str(WORLD / "v4chain"), "SIGGATE_OUT": str(WORLD / "sig/GATE_signal.json")}
    r = subprocess.run([PY, str(SIG_V2)], env=env, capture_output=True, text=True); info["signal_gate_rc"] = r.returncode
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    info["signal_receipt"] = {k: json.load(open(WORLD / "sig/GATE_signal.json")).get(k) for k in ("gate", "arm", "PASS", "self_sha256", "stats")}
    return info


# ------------------------------------------------------------------------------------------------------------- harness
def gate_env(case, arm, extra=None, tag=""):
    e = {"EXPORT_ARM": arm, "BUNDLE_OUT": str(ACTIVE / "bundle"), "BUNDLE_FEA": str(ACTIVE / "data/wide_fea_v4.npy"), "BUNDLE_META": str(ACTIVE / "data/wide_fea_v4_meta.npz"),
         "BUNDLE_BASE": str(ACTIVE / "data/slow_scorer_v4base.json"), "EXPORT_PANEL": str(ACTIVE / "data/wide_panel_4h_v3splice.npz"), "BUNDLE_CACHE": str(ACTIVE / "data/cache.npz"),
         "FUND_AUG": str(ACTIVE / "data/fund_aug.json.gz"), "LIVE_PINS": str(ACTIVE / "data/live_pins.json"), "JUDGE_HC": str(ACTIVE / "hc"), "V4CHAIN_DIR": str(ACTIVE / "v4chain"),
         "SIGNAL_RECEIPT": str(ACTIVE / "sig/GATE_signal.json"), "EXPORT_GATE_OUT": str(case / f"receipt_{arm}{tag}.json"), "OMP_NUM_THREADS": "2"}
    if extra: e.update(extra)
    return e


def run_gate(case, arm, extra=None, tag=""):
    """tag: a re-gate after a mutation writes receipt_<arm><tag>.json so the POSITIVE receipt is never overwritten (harness defect found in run 2)."""
    env = gate_env(case, arm, extra, tag); r = subprocess.run([PY, str(GATE_V2)], env={**{k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}, **env}, capture_output=True, text=True)
    rp = Path(env["EXPORT_GATE_OUT"]); rec = json.load(open(rp)) if rp.exists() else None
    return {"rc": r.returncode, "PASS": (rec or {}).get("PASS"), "failed_checks": (rec or {}).get("failed_checks"), "receipt": str(rp) if rec else None,
            "stdout_tail": r.stdout[-600:], "stderr_tail": r.stderr[-600:], "env": env}, rec


def run_require(case, arm, receipt_path, extra=None):
    env = gate_env(case, arm, extra); env["REQUIRE_OUT"] = str(case / f"require_{arm}.json")
    r = subprocess.run([PY, str(GATE_V2), "require", receipt_path], env={**{k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}, **env}, capture_output=True, text=True)
    ro = Path(env["REQUIRE_OUT"]); out = json.load(open(ro)) if ro.exists() else {}
    return {"rc": r.returncode, "REQUIRE_OK": out.get("REQUIRE_OK"), "identity_why": (out.get("identity_and_inputs") or {}).get("why"), "content_failed": out.get("content_failed"),
            "stdout_tail": r.stdout[-600:], "stderr_tail": r.stderr[-400:]}


def new_case(name):
    case = ROOT / "cases" / name
    if case.exists(): shutil.rmtree(case)
    shutil.copytree(WORLD, case, symlinks=False)
    if ACTIVE.is_symlink() or ACTIVE.exists(): ACTIVE.unlink()
    ACTIVE.symlink_to(case, target_is_directory=True)
    return case


def book(case, arm, seat, seed): return case / f"hc/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz"


def edit_book(path, fn_rec=None, fn_W=None, fn_cfg=None):
    A = dict(np.load(path, allow_pickle=True)); R = np.asarray(A["d30_n2_c42_rec"], float); W = np.asarray(A["d30_n2_c42_W"], np.float32); cj = json.loads(str(A["config_json"]))
    if fn_W: W = fn_W(W, R)
    if fn_rec: R = fn_rec(R, W)
    if fn_cfg: cj = fn_cfg(cj)
    A["d30_n2_c42_rec"] = R; A["d30_n2_c42_W"] = W; A["config_json"] = np.array(json.dumps(cj)); np.savez(path, **A)


def all_books(case, arm, **kw):
    for seat, seed in G.SEATS: edit_book(book(case, arm, seat, seed), **kw)


def consistent_rec(R, W):
    """Recompute every W-derived column from W (what a careful forger would do): gross, turnover, netlong; keep net identities."""
    W64 = W.astype(np.float64); sw = np.abs(W64).sum(1); to = np.concatenate([[sw[0]], np.abs(np.diff(W64, axis=0)).sum(1)])
    R = R.copy(); R[:, C["gross_total"]] = sw; R[:, C["gross_member"]] = sw; R[:, C["gross_sel"]] = sw; R[:, C["turnover"]] = to
    with np.errstate(all="ignore"): R[:, C["netlong"]] = np.where(sw > 0, W64.sum(1) / np.where(sw > 0, sw, 1), 0)
    R[:, C["cost"]] = to * 2.10; R[:, C["cost_ex"]] = R[:, C["cost"]] * 0.98
    R[:, C["net"]] = R[:, C["pnl"]] - R[:, C["carry"]] - R[:, C["cost"]]; R[:, C["net_ex"]] = R[:, C["pnl_ex"]] - R[:, C["carry_ex"]] - R[:, C["cost_ex"]]
    return R


def frozen_row(R):
    ts = np.round(R[:, 0]).astype(np.int64); return int(np.nonzero(ts == T(2025, 6, 1))[0][0])


def sig_edit(case, fn):
    p = case / "sig/GATE_signal.json"; s = json.load(open(p)); s = fn(s); json.dump(s, open(p, "w"), indent=1)


# ------------------------------------------------------------------------------------------------------------- matrix
def main():
    t0 = time.time(); info = build_world(); print("world built", json.dumps(info, default=str)[:600], flush=True)
    rows = []

    def row(name, kind, expect, observed, expect_fail_names=None, note=None):
        ok = (observed.get("PASS") if kind == "gate" else observed.get("REQUIRE_OK")) is expect if kind != "refuse" else observed.get("rc") == 2
        named = observed.get("failed_checks") if kind == "gate" else observed.get("content_failed")
        if ok and expect is False and expect_fail_names and kind == "gate": ok = all(n in (named or []) for n in expect_fail_names)
        if ok and expect is False and kind == "require": ok = (observed.get("REQUIRE_OK") is False) and (observed.get("rc") == 3)
        rows.append({"case": name, "mode": kind, "expected": ("REFUSE rc=2" if kind == "refuse" else ("PASS" if expect else "FAIL")), "observed_PASS": observed.get("PASS") if kind == "gate" else observed.get("REQUIRE_OK"),
                     "rc": observed.get("rc"), "failing_checks_named": named, "identity_why": observed.get("identity_why"), "expected_failing_checks": expect_fail_names, "meets_expectation": bool(ok), "note": note})
        print(("  ✓ " if ok else "  ✗ ") + f"{name:44s} {kind:7s} exp={rows[-1]['expected']:12s} obs PASS={rows[-1]['observed_PASS']} rc={observed.get('rc')} named={named} {observed.get('identity_why') or ''}"[:260], flush=True)
        if not ok: print("     stdout:", observed.get("stdout_tail", "")[-500:], "\n     stderr:", observed.get("stderr_tail", "")[-300:], flush=True)
        return ok

    def finish(case):
        if not KEEP: shutil.rmtree(case, ignore_errors=True)

    # ---- positives ----
    case = new_case("P1_positive_no_femat"); g, rec = run_gate(case, ARM_N); row("P1_positive_no_femat (A1-like, FEMAT None)", "gate", True, g)
    pos_n_receipt = OUT / "RECEIPT_v2_fixture_positive_no_femat.json"; OUT.mkdir(parents=True, exist_ok=True)
    if rec: json.dump(rec, open(pos_n_receipt, "w"), indent=1)
    rq = run_require(case, ARM_N, g["receipt"]); row("P1_positive_no_femat require", "require", True, rq); finish(case)

    case = new_case("P2_positive_with_femat"); g, rec = run_gate(case, ARM_F); row("P2_positive_with_femat (XIB-like, bound signal receipt)", "gate", True, g)
    if rec: json.dump(rec, open(OUT / "RECEIPT_v2_fixture_positive_with_femat.json", "w"), indent=1)
    rq = run_require(case, ARM_F, g["receipt"]); row("P2_positive_with_femat require", "require", True, rq)
    # ---- reviewer probe 6 + new N1 on the SAME positive receipt: mutate shipped files AFTER the receipt, require must FAIL ----
    pred = case / "bundle/slow_pred_pinned.npy"; P0 = np.load(pred); P1 = P0.copy(); P1[7, 3] += np.float32(1e-3); np.save(pred, P1)
    rq = run_require(case, ARM_F, g["receipt"]); row("N1_pred_one_cell_changed require (reviewer probe 6 form)", "require", False, rq, note="the SHIPPED prediction is now a registered input")
    g2, _ = run_gate(case, ARM_F, tag="_regate1"); row("N1_pred_one_cell_changed re-gate", "gate", False, g2, ["E1_manifest"], note="E3 IC tolerance cannot see one cell; MANIFEST closure does")
    np.save(pred, np.full_like(P0, np.nan)); rq = run_require(case, ARM_F, g["receipt"]); row("R6_unbound_shipped_bundle: pred->NaN after receipt, require", "require", False, rq)
    np.save(pred, P0); rq = run_require(case, ARM_F, g["receipt"]); row("R6 control: pred restored bytewise, require", "require", True, rq)
    # femat mutated after the signal receipt and the export receipt
    fz = dict(np.load(case / "sig/femat.npz", allow_pickle=True)); fz["mat"][5, 0] = np.nan; np.savez(case / "sig/femat.npz", **fz)
    rq = run_require(case, ARM_F, g["receipt"]); row("N8_femat_mutated_after_receipts require", "require", False, rq)
    g2, _ = run_gate(case, ARM_F, tag="_regate2"); row("N8_femat_mutated_after_signal_receipt re-gate", "gate", False, g2, ["E7_signal_receipt"])
    finish(case)

    # ---- receipt written by the ORIGINAL gate source (identity) ----
    case = new_case("N11_receipt_from_original_gate_sha"); g, rec = run_gate(case, ARM_F)
    rec["self_sha256"] = "f814c728938482b876cbcaa31f200832d207a0f89387d58ed3e2d0d45448e214"; json.dump(rec, open(g["receipt"], "w"))
    rq = run_require(case, ARM_F, g["receipt"]); row("N11_receipt_self_sha=original_gate require", "require", False, rq, note="original sha is not approved for BUNDLE_export in the isolated contract"); finish(case)

    # ---- reviewer probes 1–5 as GATE negatives ----
    case = new_case("R1_bare_PASS_wrong_signal_gate"); json.dump({"PASS": True, "gate": "NOT_A_SIGNAL_GATE"}, open(case / "sig/GATE_signal.json", "w"))
    g, _ = run_gate(case, ARM_F); row("R1_bare_PASS_wrong_signal_gate", "gate", False, g, ["E7_signal_receipt"]); finish(case)

    case = new_case("R2a_signal_FAIL_negative_control"); sig_edit(case, lambda s: {**s, "PASS": False, "stats": {**s["stats"], "NEW_rankdata_rows_failing_rerank_identity": 7}})
    g, _ = run_gate(case, ARM_F); row("R2a_signal_receipt_PASS_false", "gate", False, g, ["E7_signal_receipt"]); finish(case)

    case = new_case("R2b_signal_PASS_word_but_stats_fail"); sig_edit(case, lambda s: {**s, "stats": {**s["stats"], "NEW_rankdata_rows_failing_rerank_identity": 7}})
    g, _ = run_gate(case, ARM_F); row("R2b_signal_receipt_says_PASS_but_stats_violate_thresholds", "gate", False, g, ["E7_signal_receipt"], note="PASS re-derived from stats, the word is not trusted"); finish(case)

    case = new_case("R3_different_cost_and_ftrim"); all_books(case, ARM_F, fn_cfg=lambda c: {**c, "COST_B": [[0, 0, 1]] * 3, "FTRIM_TH": -0.1})
    g, _ = run_gate(case, ARM_F); row("R3_different_cost_and_ftrim (COST_B zero + injected FTRIM_TH key)", "gate", False, g, ["E6_books_config"]); finish(case)

    case = new_case("R4_zero_W_and_infinite_pnl")
    def z_rec(R, W): R = R.copy(); R[:, C["net_ex"]] = np.inf; return R
    all_books(case, ARM_F, fn_W=lambda W, R: np.zeros_like(W), fn_rec=z_rec)
    g, _ = run_gate(case, ARM_F); row("R4_zero_W_and_infinite_pnl", "gate", False, g, ["E5_books_shape", "E8_books_content"]); finish(case)

    case = new_case("R5_bad_fixed_PIN_PHI099"); all_books(case, ARM_F, fn_cfg=lambda c: {**c, "PHI": 0.99})
    g, _ = run_gate(case, ARM_F); row("R5_bad_fixed_PIN (PHI 0.99, the one probe the original caught)", "gate", False, g, ["E6_books_config"]); finish(case)

    # ---- new counter-examples ----
    case = new_case("N2a_W_one_anchor_x2_gross_updated")
    def x2_partial(W, R): W = W.copy(); i = frozen_row(R); W[i] *= 2; return W
    def x2_gross_only(R, W): R = R.copy(); i = frozen_row(R); R[i, C["gross_total"]] = np.abs(W[i].astype(np.float64)).sum(); return R
    all_books(case, ARM_F, fn_W=x2_partial, fn_rec=x2_gross_only)
    g, _ = run_gate(case, ARM_F); row("N2a_W_one_anchor_x2 (gross_total updated, turnover not)", "gate", False, g, ["E8_books_content"], note="K2 turnover identity"); finish(case)

    case = new_case("N2b_W_one_anchor_x2_fully_consistent"); all_books(case, ARM_F, fn_W=x2_partial, fn_rec=consistent_rec)
    g, _ = run_gate(case, ARM_F); row("N2b_W_one_anchor_x2 (every W-derived column recomputed)", "gate", False, g, ["E9_gross_band_vs_baseline"], note="only the baseline band sees a self-consistent forgery"); finish(case)

    case = new_case("N10_W_all_x2_fully_consistent"); all_books(case, ARM_F, fn_W=lambda W, R: W * 2, fn_rec=consistent_rec)
    g, _ = run_gate(case, ARM_F); row("N10_W_all_anchors_x2 (fully consistent)", "gate", False, g, ["E8_books_content", "E9_gross_band_vs_baseline"], note="K6 gross<=1 and the band"); finish(case)

    case = new_case("N3_cost_json_one_tier_rate_changed"); cj = json.load(open(case / "hc/calib/costb.json")); cj["tiers"][1]["maker_bps"] = 1.9; json.dump(cj, open(case / "hc/calib/costb.json", "w"), indent=1)
    g, _ = run_gate(case, ARM_F); row("N3_cost_json_one_tier_rate_changed (books' COST_B untouched)", "gate", False, g, ["E6_books_config"], note="costb sha + resolves_to_approved_tiers"); finish(case)

    case = new_case("N3b_cost_json_reformatted_same_tiers"); cj = json.load(open(case / "hc/calib/costb.json")); json.dump(cj, open(case / "hc/calib/costb.json", "w"))   # whitespace only
    g, _ = run_gate(case, ARM_F); row("N3b_cost_json_same_tiers_but_different_bytes", "gate", False, g, ["E6_books_config"], note="the file the book was built from is identified by sha, not by what it says"); finish(case)

    case = new_case("N4_zero_cost")
    def zero_cost(R, W): R = R.copy(); R[:, C["cost"]] = 0; R[:, C["cost_ex"]] = 0; R[:, C["net"]] = R[:, C["pnl"]] - R[:, C["carry"]]; R[:, C["net_ex"]] = R[:, C["pnl_ex"]] - R[:, C["carry_ex"]]; return R
    all_books(case, ARM_F, fn_rec=zero_cost); g, _ = run_gate(case, ARM_F); row("N4_zero_cost (identities kept)", "gate", False, g, ["E8_books_content"], note="K7"); finish(case)

    case = new_case("N5_manifest_extra_file"); (case / "bundle/extra_note.txt").write_text("unlisted"); g, _ = run_gate(case, ARM_F); row("N5_manifest_unlisted_file", "gate", False, g, ["E1_manifest"]); finish(case)

    case = new_case("N6_baseline_book_swapped"); shutil.copy(book(case, BASE_ARM, "dyn", "2027"), book(case, BASE_ARM, "dyn", "42"))
    g, _ = run_gate(case, ARM_F); row("N6_baseline_A0_book_replaced_by_another_cell", "gate", False, g, ["E9_gross_band_vs_baseline"], note="approved baseline identity"); finish(case)

    case = new_case("N7_signal_receipt_other_arm"); sig_edit(case, lambda s: {**s, "arm": "OTHER"}); g, _ = run_gate(case, ARM_F); row("N7_signal_receipt_bound_to_other_arm", "gate", False, g, ["E7_signal_receipt"]); finish(case)

    case = new_case("N9_env_guard_band_override"); g, _ = run_gate(case, ARM_F, {"BUNDLE_GUARD_LO": "0.0"}); row("N9_env_BUNDLE_GUARD_LO=0.0", "refuse", None, g, note="thresholds are not the caller's"); finish(case)

    case = new_case("N12_contract_without_baseline_block"); c = json.load(open(case / "v4chain/ELIGIBILITY_CONTRACT.json")); del c["gates"]["BUNDLE_export"]["approved_baseline"]; json.dump(c, open(case / "v4chain/ELIGIBILITY_CONTRACT.json", "w"))
    g, _ = run_gate(case, ARM_F); row("N12_contract_missing_approved_baseline", "refuse", None, g); finish(case)

    case = new_case("N13_live_pins_reformatted"); p = json.load(open(case / "data/live_pins.json")); json.dump(p, open(case / "data/live_pins.json", "w"))
    g, _ = run_gate(case, ARM_F); row("N13_live_pins_same_content_different_bytes", "gate", False, g, ["E2b_pins_identity"], note="E2 content parity passes; identity (d) fails"); finish(case)

    case = new_case("N14_book_seed_swapped"); edit_book(book(case, ARM_F, "dyn", "42"), fn_cfg=lambda c: {**c, "FSEED": "2027"})
    g, _ = run_gate(case, ARM_F); row("N14_book_dyn_s42_declares_FSEED_2027", "gate", False, g, ["E6_books_config"]); finish(case)

    case = new_case("N15_wrong_arm_books_for_receipt"); g, rec = run_gate(case, ARM_F)
    rq = run_require(case, ARM_N, g["receipt"]); row("N15_require_ARMX_receipt_against_ARMY_books", "require", False, rq, note="book inputs differ by sha"); finish(case)

    case = new_case("N16_umask_swapped"); np.savez(case / "hc/masks/umask.npz", mask=np.zeros((5, NS), bool)); g, _ = run_gate(case, ARM_F); row("N16_umask_npz_replaced", "gate", False, g, ["E6_books_config"]); finish(case)

    if ACTIVE.is_symlink(): ACTIVE.unlink()
    allok = all(r["meets_expectation"] for r in rows)
    receipt = {"device": "test_matrix_v2.py", "self_sha256": sha(__file__), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seconds": round(time.time() - t0, 1),
               "env_whitelist": ENV_WHITELIST, "python": sys.version.split()[0], "numpy": np.__version__,
               "sources": {"v4e_gate_export_v2.py": sha(GATE_V2), "gate_signal_parity_v2.py": sha(SIG_V2), "v4_gate_common.py": sha(CHAIN / "v4_gate_common.py"),
                           "frozen_contract_read_only": sha(CHAIN / "ELIGIBILITY_CONTRACT.json"), "isolated_world_contract": sha(WORLD / "v4chain/ELIGIBILITY_CONTRACT.json")},
               "world": info, "ALL_ROWS_MEET_EXPECTATION": allok, "n_rows": len(rows), "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True); json.dump(receipt, open(OUT / "RECEIPT_test_matrix_v2.json", "w"), indent=1, default=str)
    print(f"\nMATRIX {'ALL OK' if allok else 'MISMATCH'} rows={len(rows)} in {time.time() - t0:.0f}s"); sys.exit(0 if allok else 3)


if __name__ == "__main__": main()
