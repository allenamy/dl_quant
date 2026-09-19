#!/usr/bin/env python3
"""Object B history driver (PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19 §1–§3 S6; comparison type (1) historical recipe).
Production code path, byte-identical devices (sha asserted): producer shadow_loop_v3_replay.py 4d3bc157 (from e9c98374) and
combo_stage_replay_3520d363.py (from 3520d363). Every object-B change is an INPUT the production code already takes:
  king       FoldBooster('folds') as the `booster` argument (latest v3 fold with label_end < A − 30 d; predict on the producer's own X)
  F10        pass P2 (b_scorer.py) scores every producer member with the production 171 pipeline + the in-service-recipe yearly fold selected by
             the F10 rule; pass P3 injects those scores (rank/128 + identity model: zf bitwise = production zf of the same scores, G2-C′)
  cache      holefix2 AS-IS (R0, AMENDMENT 3 A3.3), then names outside symbols_live(A) NaN (S2 I3)
  base       exchangeInfo stand-in = trading24 ∩ COIN (G.base_names) ∪ symbols_live, pre-seeded into st.base (S2 D3 practice, AMENDMENT 3)
  universe   PIT (P2 universe.npz), funding rows = ledger_full (S2 I6), cold start 2022-01-31 00Z (S2 I7)
Passes: P1 producer only, records the scorer inputs per anchor (members, prev_rec, ema acc, last funding rate); P3 producer + combo with the
P2 scores injected, records member names, both COMBO_LIVE readings (B-scaled main, B-lit as coded) and the traded target per reading.
usage: see b_launch.py"""
import os, sys, json, time, math, copy, shutil, subprocess, importlib, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL

R = os.environ.get("OBJB_ROOT", "/workspace/object_b_2026-09-19")
PIN_DEV = {"shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42",
           "combo_stage_replay_3520d363.py": "92c49fa82d4c5c1bdb70c6155c0c3e7bfe3c5f012e1db0aeb686ef1fbcd6e1d8",
           "f10_scorer_3520d363.py": "1d249a5ebe662cda108436da02fd856ed08d7ed30f13d7d620de5661529f7c44"}
SRC = {"cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
       "ledger": ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
       "universe": ("/workspace/uplift_r2_2026-09-13/P2/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7"),
       "tradability": ("/workspace/fx_data_2026-09-13/out/trd/tradability_v1.npz", "54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302"),
       "upit": ("/workspace/review_scratch/health_check/masks/umask_UPIT.npz", "ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece"),
       "upit_crypto": ("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
       "bundle_leg_returns": ("/workspace/shadow_bundle_v3/leg_returns.npz", "6061af108e45fee5ea0257b37f35e9efd0783d494934cad398e003fd47de7c13"),
       "king_meta_v2ext": ("/workspace/data/wide_fea_v2ext_meta.npz", "4b1b6047107d25573244a84df69d45bc987ada89b6731e826c867a230e247082")}
ARM = os.environ.get("OBJB_ARM", "A0")    # AMENDMENT 5: "A0" = in-service recipe (default, unchanged); "V4" = v4 refit recipe
assert ARM in ("A0", "V4"), ARM
SRC["king_meta_v4"] = ("/workspace/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51")
if ARM == "A0":
    KING_FOLD_FILES = {2023: f"{R}/models/king_v3_fold2023.txt", 2024: f"{R}/models/king_v3_fold2024.txt", 2025: f"{R}/models/king_v3_fold2025.txt",
                       2026: "/workspace/shadow_bundle_v3/slow2026.txt"}
    KING_META_KEY = "king_meta_v2ext"
else:
    KING_FOLD_FILES = {2023: f"{R}/models/king_v4_fold2023.txt", 2024: f"{R}/models/king_v4_fold2024.txt", 2025: f"{R}/models/king_v4_fold2025.txt",
                       2026: "/workspace/shadow_bundle_v4/slow2026.txt"}
    KING_META_KEY = "king_meta_v4"
DATA = os.environ.get("OBJB_DATA", "holefix2")   # AMENDMENT 4 A4.4 extension segment: "x0918r" = cache x0918r + ledger/universe extended (mk_ext_inputs.py)
assert DATA in ("holefix2", "x0918r"), DATA
if DATA == "x0918r":
    # the only x0918r components read: the cache (variant-diff C1 PASS: 2,876,251,147 cells outside the replaced 08-31 rows bit-identical to x0918,
    # which is bit-identical to holefix2 on its 490,753 rows) and tradability (bebf69ab, identical in x0918 and x0918r, C3)
    SRC["cache"] = ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75")
    SRC["ledger"] = (f"{R}/work/ext_inputs/ledger_ext.npz", "155ce179652323a7567723b5f680fbfb938cbfd8ea7ecc277e7945a9c0027724")
    SRC["universe"] = (f"{R}/work/ext_inputs/universe_ext.npz", "3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f")
    SRC["tradability"] = ("/workspace/axis_0919/x0918r/trd/tradability_v1.npz", "bebf69ab9ddb3b05b49552e66dccf9b8cde3caee0593b14e1b3fe1a4c93c9db8")
KING_LIVE_FILE = "/workspace/shadow_bundle_v3/slow2026.txt"; KING_LIVE_SHA = "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"
F10_FOLD_FILES = {Y: f"{R}/models/f10_ins_fold{Y}_s42_np.npz" for Y in (2023, 2024, 2025, 2026)}
STAGE = f"{R}/gate_inputs"          # sha-verified copies of the production fea171 pipeline, xfer files, reader modules (manifest in STAGE_MANIFEST.json)
FEA171_NAMES = ("dlw_features.py", "f8_higher_order_features.py", "xfer_ref.npz", "xfer_syms.npz")
READER_NAMES = ("external_book.py", "book_config.py")
VENV_PY = "/workspace/venv/bin/python"
CACHE_ROWS = 11520


def assert_devices():
    for f, s in PIN_DEV.items():
        assert BL.sha(f"{HERE}/{f}") == s, f


def stage_sources():
    man = json.load(open(f"{STAGE}/STAGE_MANIFEST.json"))
    for rel, s in man["files"].items():
        assert BL.sha(f"{STAGE}/{rel}") == s, rel
    return {n: f"{STAGE}/fea171/{n}" for n in FEA171_NAMES}, {n: f"{STAGE}/reader/{n}" for n in READER_NAMES}, man


def f10_folds_registry():
    reg = {}
    if ARM == "A0":
        files = F10_FOLD_FILES
    else:   # AMENDMENT 5 A5.2: monthly FIX7 folds whose reproduction receipt PASSes (B_REPRO for 2025–2026, M_REPRO_V4 new folds for 2023–2024)
        files = {}
        b = json.load(open(f"{R}/receipts/B_REPRO.json")); assert b["B_REPRO_VERDICT"] == "PASS"
        for ym, f in b["folds"].items():
            if f["PASS"]: files[int(ym)] = f["np_export"]
        m = json.load(open(f"{R}/receipts/M_REPRO_V4.json"))
        for ym, f in m["new_folds"].items():
            if f.get("PASS"): files[int(ym)] = f["np_export"]
    for Y, p in files.items():
        if not os.path.exists(p): continue
        z = np.load(p); tt = int(z["trained_through"])
        reg[Y] = {"np": p, "sha256": BL.sha(p), "trained_through": tt, "label_end": tt + BL.H4}
    return reg


# ─────────────────────────── globals ───────────────────────────
class Globals:
    def __init__(self, load_cache=True):
        t0 = time.time(); self.shas = {}
        for k, (p, s) in SRC.items():
            got = BL.sha(p); self.shas[k] = got
            if s is not None: assert got == s, (k, got, s)
        self.cfg_raw = json.load(open(SRC["bundle_config"][0])); self.SYMS = list(self.cfg_raw["symbols_panel"])
        import hashlib
        assert hashlib.sha256("\n".join(self.SYMS).encode()).hexdigest() == "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
        self.col = {s: j for j, s in enumerate(self.SYMS)}
        self.LE = BL.LiveEquiv(SRC["tradability"][0], SRC["upit"][0], SRC["upit_crypto"][0], self.SYMS)
        # AMENDMENT 3 A3.3 (R0): the cache is used AS-IS (what production fetched); the live-equivalent rule is NOT applied (LE-A′ FAIL on record).
        # LiveEquiv is kept only for the non-COIN flag (base list) and the last-traded times (dead-name exposure reporting, never for blanking).
        self.le_changed = "R0: live-equivalent rule not applied (AMENDMENT 3 A3.3)"
        if load_cache:
            Z = np.load(SRC["cache"][0], allow_pickle=True); assert [str(s) for s in Z["symbols"]] == self.SYMS
            self.TS = Z["ts"].astype(np.int64); self.DATA = Z["data"]; del Z
            self.row_of_ts = {int(t): i for i, t in enumerate(self.TS)}
        L = np.load(SRC["ledger"][0], allow_pickle=True); assert [str(s) for s in L["symbols"]] == self.SYMS
        self.L_off = L["off"]; self.L_ft = L["ft"]; self.L_rate = L["rate"]
        U = np.load(SRC["universe"][0], allow_pickle=True); assert [str(s) for s in U["symbols"]] == self.SYMS
        self.U_ts = U["ts"].astype(np.int64); self.U_row = {int(t): i for i, t in enumerate(self.U_ts)}; self.U_pit = U["pit"]; self.U_tr24 = U["trading24"]
        self.king_label_end = BL.king_label_ends(SRC[KING_META_KEY][0]); self.arm = ARM
        if ARM == "V4":   # AMENDMENT 5: king files = the K-REPRO-v4 receipt's folds (2023–2025) + the in-service v4 bundle slow2026 (its input pin)
            kr = json.load(open(f"{R}/receipts/K_REPRO_v4.json")); assert kr["gate_ok_to_use"] is True
            want = {int(y): kr["folds"][str(y)]["model_sha256"] for y in (2023, 2024, 2025)}; want[2026] = kr["inputs_sha256"]["slow2026"]
            for y, f in KING_FOLD_FILES.items():
                assert BL.sha(f) == want[y], ("V4 king fold sha", y)
                assert self.king_label_end[y] == int(kr["folds"][str(y)]["label_end_ts"]), ("V4 king label_end", y)
        self.f10 = f10_folds_registry()
        self.load_s = round(time.time() - t0, 1)

    def base_names(self, A):
        """AMENDMENT 3 A3.3: exchangeInfo stand-in = S2 D3 proxy trading24 ((A−24h, A] has a settlement) minus non-COIN names; the caller adds
        symbols_live(A). Listed-but-untraded contracts keep settling funding, as production's exchangeInfo keeps them TRADING."""
        r = self.U_row[int(A)]; m = np.asarray(self.U_tr24[r], bool) & ~self.LE.noncoin
        return [self.SYMS[j] for j in np.where(m)[0]]

    def live_names(self, A):
        r = self.U_row[int(A)]; return [self.SYMS[j] for j in np.where(self.U_pit[r])[0]]

    def ledger_rows(self, s, last_ts, A):
        j = self.col[s]; a, b = self.L_off[j], self.L_off[j + 1]; ft = self.L_ft[a:b]
        lo = np.searchsorted(ft, int(last_ts), side="right"); hi = np.searchsorted(ft, int(A), side="right"); hi = min(hi, lo + 100)
        return [[int(ft[k]), float(self.L_rate[a + k])] for k in range(lo, hi)]

    def cache_tail(self, A, live_mask, rows=CACHE_ROWS):
        ai = self.row_of_ts[int(A)]; i0 = max(0, ai + 1 - rows)
        cd = np.array(self.DATA[i0:ai + 1]); cd[:, ~live_mask, :] = np.nan
        return self.TS[i0:ai + 1].copy(), cd


# ─────────────────────────── producer step (shared with the gate) ───────────────────────────
def import_producer(rh):
    os.environ["WIDE_SHADOW_HOME"] = rh
    os.environ.setdefault("WIDE_SHADOW_BUNDLE", "/workspace/shadow_bundle_v3")
    sys.path.insert(0, HERE)
    dev = importlib.import_module("shadow_loop_v3_replay")
    assert dev.STATE_DIR == f"{rh}/state" and dev.HOME == rh, (dev.STATE_DIR, dev.HOME)
    assert dev.REPLAY_META["production_sha256"] == "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"
    return dev


def producer_step(dev, st, fx, cfg, booster, A, rh):
    """run_anchor exactly as the producer; returns (wrote, signal_row, skip_row). Per-anchor output files of A are removed first."""
    for d_ in ("weights", "target_live"):
        for f in (f"{rh}/state/{d_}/{A}.json", f"{rh}/state/{d_}/{A}.json.sha256", f"{rh}/state/{d_}/{A}.npz"):
            if os.path.exists(f): os.remove(f)
    if os.path.exists(f"{rh}/shadow_log.jsonl"): os.remove(f"{rh}/shadow_log.jsonl")
    dev.run_anchor(st, fx, cfg, booster, A)
    rows = []
    if os.path.exists(f"{rh}/shadow_log.jsonl"):
        for l in open(f"{rh}/shadow_log.jsonl"):
            try: rows.append(json.loads(l))
            except Exception: pass
    sig = [r for r in rows if r.get("e") == "signal"]; skip = [r for r in rows if r.get("e") == "anchor_skip"]
    return os.path.exists(f"{rh}/state/weights/{A}.npz"), (sig[-1] if sig else None), (skip[-1] if skip else None)


def aux_doc(st):
    """the combo stage reads prev_rec, ema, ledger_tail (rows[-1] only), base_syms from aux.json (S2 A2.1 I8 practice)."""
    return {"prev_close": {}, "H": {str(int(j)): float(st.H[j]) for j in np.where(np.abs(st.H) > 1e-9)[0]}, "last_anchor": st.last_anchor,
            "ema": st.ema, "ledger_tail": {s: r[-1:] for s, r in st.ledger.items()}, "base_syms": list(st.base), "prev_rec": st.prev_rec}


def scorer_inputs(st):
    """exactly what the scorer prefix (combo_stage L13–16, L138–145) reads from aux: prev_rec; ema acc; last funding rate per name."""
    fe = {s: float(e["acc"]) for s, e in st.ema.items() if isinstance(e, dict) and "acc" in e}
    fn = {s: float(r[-1][1]) for s, r in st.ledger.items() if r}
    return copy.deepcopy(st.prev_rec), fe, fn


def run_stage_forked(script, cwd, env, log_path, timeout=900):
    """S2 p2_driver.run_stage_forked (bitwise-equal to subprocess mode on the S2 timing anchors): the byte-identical stage script in a forked
    child with os.environ replaced by env, cwd, stdout/stderr to log_path."""
    import runpy, traceback, signal as _sig
    sys.stdout.flush(); sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644); os.dup2(fd, 1); os.dup2(fd, 2); os.close(fd)
            sys.stdout = os.fdopen(1, "w", buffering=1); sys.stderr = sys.stdout
            os.environ.clear(); os.environ.update(env); os.chdir(cwd); sys.argv = [script]
            runpy.run_path(script, run_name="__main__"); code = 0
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except BaseException:
            traceback.print_exc(); code = 1
        finally:
            try: sys.stdout.flush()
            except Exception: pass
            os._exit(code)
    t0 = time.time()
    while True:
        wp, status = os.waitpid(pid, os.WNOHANG)
        if wp == pid: break
        if time.time() - t0 > timeout:
            os.kill(pid, _sig.SIGKILL); os.waitpid(pid, 0); return 124, ["TIMEOUT"]
        time.sleep(0.005)
    return os.waitstatus_to_exitcode(status), open(log_path, errors="replace").read().strip().splitlines()


def combo_env(rh, home):
    return {"PATH": "/usr/bin:/bin", "HOME": home, "WIDE_SHADOW_HOME": rh, "COMBO_LIVE": "1", "COMBO_LIVE_DIR": f"{rh}/state/target_live_combo",
            "REPLAY_TRUNCATE_CACHE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "LC_CTYPE": "C.UTF-8"}


def clear_combo_outputs(rh, A):
    for d_ in ("target_combo", "target_blend", "target_live_combo", "target_live_king", "weights_combo"):
        for f in (f"{rh}/state/{d_}/{A}.json", f"{rh}/state/{d_}/{A}.json.sha256", f"{rh}/state/{d_}/{A}.npz"):
            if os.path.exists(f): os.remove(f)
    if os.path.exists(f"{rh}/state/combo_live_status.json"): os.remove(f"{rh}/state/combo_live_status.json")


def combo_outcome(rh, A, rc, out, syms, pm, live_set):
    """parse one combo run: states, status, as-coded decision (the device's own COMBO_LIVE), B-scaled decision (PREREG §1 / AMENDMENT —),
    and the traded weights per reading. Weights: combo = target_live_combo file when the device wrote it, else 0.55·kc + 0.45·fc from the
    state files (|v| > 1e-9 each; |Δ| ≤ 1e-9 vs the in-memory combo_raw); king = the producer's own target_live file."""
    has_states = os.path.exists(f"{rh}/fea171/state_H_kc_{A}.npz") and os.path.exists(f"{rh}/fea171/state_H_fc_{A}.npz")
    known_crash = (rc == 1 and not has_states and any("_nz = np.where(np.abs(_sm) > 1e-9)[0]" in l for l in out)
                   and any("TypeError: bad operand type for abs(): 'NoneType'" in l for l in out))
    rec = {"combo_rc": rc, "known_crash": known_crash, "has_states": has_states}
    if rc not in (0, 3) and not known_crash:
        rec["fatal"] = out[-6:]; return rec, None, None, None
    kf = f"{rh}/state/target_live/{A}.json"
    king_w = BL.target_weights(kf)[1] if os.path.exists(kf) else None
    st_ = json.load(open(f"{rh}/state/combo_live_status.json")) if os.path.exists(f"{rh}/state/combo_live_status.json") else None
    rec["status"] = st_
    kc = fc = None; combo_w = None
    if has_states:
        kc = np.load(f"{rh}/fea171/state_H_kc_{A}.npz"); fc = np.load(f"{rh}/fea171/state_H_fc_{A}.npz")
        assert int(kc["anchor"]) == A and int(fc["anchor"]) == A
        tc = json.load(open(f"{rh}/state/target_combo/{A}.json"))
        rec["combo_meta"] = {k_: tc.get(k_) for k_ in ("w3_masked", "kc_state_source", "fc_state_source", "gross", "kc_gross", "fc_gross", "n_f10_scored")}
        rec["ftrim"] = {k_: tc["ftrim"].get(k_) for k_ in ("n_kc", "n_fc", "rn8_coverage")}
        cr = np.zeros(len(syms)); cr[kc["idx"].astype(np.int64)] += 0.55 * kc["val"].astype(np.float64); cr[fc["idx"].astype(np.int64)] += 0.45 * fc["val"].astype(np.float64)
        nz = np.where(np.abs(cr) > 1e-9)[0]
        tl = f"{rh}/state/target_live_combo/{A}.json"
        lit_ok = bool(st_ and st_.get("ok") and os.path.exists(tl))
        combo_w = BL.target_weights(tl)[1] if lit_ok else {syms[int(j)]: float(cr[j]) for j in nz}
        n = len(pm); okf = int(rec["combo_meta"]["n_f10_scored"]); g = float(np.abs(cr[nz]).sum()); nn = int(len(nz))
        inside = all(syms[int(j)] in live_set for j in nz); g_in = float(sum(abs(cr[j]) for j in nz if syms[int(j)] in live_set))
        n_in = int(sum(1 for j in nz if syms[int(j)] in live_set))
        f380 = math.ceil(380 * n / 400); f150 = math.ceil(150 * n / 400)
        pre = {"n_members": n, "n_f10_scored": okf, "gross": g, "n_names": nn, "outside_zero": inside, "n_in_universe": n_in, "gross_in": g_in,
               "floor380_scaled": f380, "floor150_scaled": f150}
        scaled = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= f150) and inside and (n_in >= f150) and (g_in > 0.4) and king_w is not None
        scaled_l333_only = (okf >= f380) and (0.4 <= g <= 1.2) and (nn >= 150) and inside and (n_in >= 150) and (g_in > 0.4) and king_w is not None
        # the as-coded floors are >= the scaled ones (n <= 400), so an as-coded pass implies a scaled pass; a recomputation that disagrees can only
        # come from the |v| > 1e-9 state-file reconstruction at a threshold edge ⇒ recorded, and the device's own pass is kept
        rec["preflight"] = pre; rec["lit_ok"] = lit_ok
        rec["scaled_calc_disagrees_with_lit_pass"] = bool(lit_ok and not scaled)
        rec["scaled_ok"] = bool(scaled or lit_ok); rec["scaled_l333_only_ok"] = bool(scaled_l333_only or lit_ok)
    else:
        rec["lit_ok"] = rec["scaled_ok"] = rec["scaled_l333_only_ok"] = False
    return rec, king_w, combo_w, (kc, fc)


# ─────────────────────────── the chain ───────────────────────────
def cold_state(dev, cfg, A0, lr_bundle_path=None):
    class ReplayState(dev.ShadowState):
        def save(self): pass
    st = ReplayState.__new__(ReplayState)
    st.syms = cfg["symbols_panel"]; st.NW = 829; st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    st.prev_close = {}; st.H = np.zeros(829); st.last_anchor = int(A0) - BL.H4; st.ema = {}; st.ledger = {}; st.prev_rec = None
    st.LR = {"king": [], "rev24": [], "fund": []}; st.base = []
    return st


def run_chain(mode, G, anchors, rh, out_prefix, scores=None, log_every=100, checkpoint_every=1000):
    """mode P1 (producer only, scorer inputs) or P3 (producer + combo with injected scores). scores: {A: (pm, f10, fold)} for P3."""
    assert mode in ("P1", "P3")
    assert_devices()
    fea_src, reader_src, man = stage_sources()
    os.makedirs(rh, exist_ok=True)
    for d in ("state/weights", "state/target_live", "fea171"): os.makedirs(f"{rh}/{d}", exist_ok=True)
    dev = import_producer(rh)
    if not os.path.islink(f"{rh}/shadow_bundle"): os.symlink("/workspace/shadow_bundle_v3", f"{rh}/shadow_bundle")
    home = f"{rh}/home"; os.makedirs(f"{home}/dl_quant_live/live", exist_ok=True)
    for n, p in reader_src.items(): shutil.copy2(p, f"{home}/dl_quant_live/live/{n}")
    if mode == "P3":
        for n, p in fea_src.items(): shutil.copy2(p, f"{rh}/fea171/{n}")
        idsha = BL.write_identity_model(f"{rh}/fea171/f10_live_s42_np.npz")
    cfg = copy.deepcopy(G.cfg_raw); cfg["_booster_sha"] = "OBJECT_B:king_v3_folds" if ARM == "A0" else "OBJECT_B:king_v4_folds"
    booster = BL.FoldBooster("folds", KING_FOLD_FILES, G.king_label_end)
    st = cold_state(dev, cfg, anchors[0]); fx = dev.ReplayFetcher([], {})
    recs = []; P1 = {"anchor": [], "pm": [], "legz": [], "sm": [], "sm_idx": [], "fe": [], "fn": []}
    VEC = {k: [] for k in ("anchor", "pm", "king", "kc", "fc", "king_file", "combo")}
    t_start = time.time()
    for k, A in enumerate(anchors):
        A = int(A); t0 = time.time()
        live = G.live_names(A); lmask = np.zeros(829, bool); lmask[[G.col[s] for s in live]] = True
        st.live = live; st.live_mask = lmask; cfg["symbols_live"] = live
        base = G.base_names(A); st.base = sorted(set(base) | set(live)); fx.base = base
        fx.ledger = {s: G.ledger_rows(s, (st.ledger[s][-1][0] if st.ledger.get(s) else A - 40 * BL.DAY), A) for s in st.base}
        st.cts, st.cd = G.cache_tail(A, lmask)
        wrote, sig, skip = producer_step(dev, st, fx, cfg, booster, A, rh)
        rec = {"anchor": A, "utc": BL.iso(A), "n_live": len(live), "n_base": len(st.base), "king": booster.last, "signal": sig, "skip": skip,
               "lr_len": len(st.LR["king"]), "wrote": wrote}
        if wrote:
            pm = np.array(st.prev_rec["members"], np.int64); rec["n_members"] = int(len(pm))
            if mode == "P1":
                pr, fe, fn = scorer_inputs(st)
                P1["anchor"].append(A); P1["pm"].append(pm.astype(np.int16))
                P1["legz"].append(np.stack([np.asarray(pr["legz"][l], np.float64) for l in ("king", "rev24", "fund")]))
                P1["sm"].append(np.asarray(pr["sm"], np.float64)); P1["sm_idx"].append(np.asarray(pr["sm_idx"], np.int16))
                fev = np.full(829, np.nan); fnv = np.full(829, np.nan)
                for s, v in fe.items():
                    if s in G.col: fev[G.col[s]] = v
                for s, v in fn.items():
                    if s in G.col: fnv[G.col[s]] = v
                P1["fe"].append(fev); P1["fn"].append(fnv)
                rec["fe_names_outside_panel"] = sorted(s for s in fe if s not in G.col)[:5]
            else:
                json.dump(aux_doc(st), open(f"{rh}/state/aux.json", "w"))
                json.dump({leg: list(map(float, st.LR[leg][-950:])) for leg in st.LR}, open(f"{rh}/state/leg_returns_live.json", "w"))
                j0 = max(0, st.cd.shape[0] - 2016); np.savez(f"{rh}/state/rolling.npz", ts=st.cts[j0:], data=st.cd[j0:])
                sc = scores.get(A)
                if sc is not None:
                    assert np.array_equal(np.asarray(sc["pm"], np.int64), pm), ("P2 scores were computed for a different member set", A)
                    n_inj = BL.write_f10_injection(f"{rh}/fea171", A, pm, sc["f10"]); rec["f10"] = {"fold": sc["fold"], "n_scored": n_inj, "model_sha": sc["model_sha"]}
                else:
                    n_inj = BL.write_f10_injection(f"{rh}/fea171", A, pm, np.full(len(pm), np.nan)); rec["f10"] = {"fold": None, "n_scored": 0}
                clear_combo_outputs(rh, A)
                rc, out = run_stage_forked(f"{HERE}/combo_stage_replay_3520d363.py", f"{rh}/fea171", combo_env(rh, home), f"{rh}/combo_stage.log")
                crec, king_w, combo_w, states = combo_outcome(rh, A, rc, out, G.SYMS, pm, set(live))
                rec["combo"] = crec
                rec["traded_lit"] = "combo" if crec.get("lit_ok") else "king"
                rec["traded_scaled"] = "combo" if crec.get("scaled_ok") else "king"
                rec["traded_scaled_l333_only"] = "combo" if crec.get("scaled_l333_only_ok") else "king"
                if crec.get("fatal"):
                    recs.append(rec); dump(mode, out_prefix, G, recs, P1, VEC, fatal=f"combo rc={rc} at {BL.iso(A)}: {crec['fatal']}")
                    raise RuntimeError(f"combo rc={rc} at {BL.iso(A)}")
                nzk = np.where(np.abs(st.H) > 1e-12)[0]
                VEC["anchor"].append(A); VEC["pm"].append(pm.astype(np.int16)); VEC["king"].append((nzk.astype(np.int16), st.H[nzk].astype(np.float64)))
                if states and states[0] is not None:
                    VEC["kc"].append((states[0]["idx"].astype(np.int16), states[0]["val"].astype(np.float64)))
                    VEC["fc"].append((states[1]["idx"].astype(np.int16), states[1]["val"].astype(np.float64)))
                else:
                    VEC["kc"].append((np.zeros(0, np.int16), np.zeros(0))); VEC["fc"].append((np.zeros(0, np.int16), np.zeros(0)))
                VEC["king_file"].append(sparse(king_w, G.col)); VEC["combo"].append(sparse(combo_w, G.col))
                # prune per-anchor files the next anchor does not read
                Ap = A - BL.H4
                for f in (f"{rh}/state/weights/{Ap}.npz", f"{rh}/fea171/state_H_f10_{Ap}.npz", f"{rh}/fea171/state_H_kc_{Ap}.npz", f"{rh}/fea171/state_H_fc_{Ap}.npz",
                          f"{rh}/state/target_live/{Ap}.json", f"{rh}/state/target_live/{Ap}.json.sha256"):
                    if os.path.exists(f): os.remove(f)
                clear_combo_outputs(rh, Ap)
        else:
            if mode == "P3":
                VEC["anchor"].append(A); VEC["pm"].append(np.zeros(0, np.int16))
                for kk in ("king", "kc", "fc", "king_file", "combo"): VEC[kk].append((np.zeros(0, np.int16), np.zeros(0)))
                rec["traded_scaled"] = rec["traded_lit"] = "hold(producer_skip)"
        if mode == "P1" and wrote:
            Ap = A - BL.H4
            for f in (f"{rh}/state/weights/{Ap}.npz", f"{rh}/state/target_live/{Ap}.json", f"{rh}/state/target_live/{Ap}.json.sha256"):
                if os.path.exists(f): os.remove(f)
        rec["t_s"] = round(time.time() - t0, 3); recs.append(rec)
        if log_every and (k % log_every == 0 or k == len(anchors) - 1):
            print(json.dumps({"k": k, "anchor": BL.iso(A), "t": rec["t_s"], "members": rec.get("n_members"), "king_fold": (booster.last or {}).get("fold"),
                              "f10": rec.get("f10"), "lit": (rec.get("combo") or {}).get("lit_ok"), "scaled": (rec.get("combo") or {}).get("scaled_ok"),
                              "elapsed_s": round(time.time() - t_start, 1)}), flush=True)
        if checkpoint_every and k and k % checkpoint_every == 0: dump(mode, out_prefix, G, recs, P1, VEC, partial=True)
    dump(mode, out_prefix, G, recs, P1, VEC)
    return recs


def sparse(w, col):
    if not w: return (np.zeros(0, np.int16), np.zeros(0))
    idx = np.array([col[s] for s in w], np.int64); o = np.argsort(idx)
    return (idx[o].astype(np.int16), np.array([w[s] for s in w], np.float64)[o])


def pack(lst):
    lens = [len(v[0]) if isinstance(v, tuple) else len(v) for v in lst]
    off = np.concatenate([[0], np.cumsum(lens)]).astype(np.int64)
    if lst and isinstance(lst[0], tuple):
        return off, (np.concatenate([v[0] for v in lst]) if lens and sum(lens) else np.zeros(0, np.int16)), (np.concatenate([v[1] for v in lst]) if sum(lens) else np.zeros(0))
    return off, (np.concatenate(lst) if sum(lens) else np.zeros(0))


def dump(mode, out_prefix, G, recs, P1, VEC, fatal=None, partial=False):
    tag = ".partial" if partial else ""
    doc = {"mode": mode, "arm": ARM, "data": DATA, "comparison_type": "(1) historical recipe — object B", "inputs_sha256": G.shas, "devices": PIN_DEV,
           "king_folds": {str(k): {"file": v, "sha256": BL.sha(v), "label_end": BL.iso(G.king_label_end[k])} for k, v in KING_FOLD_FILES.items()},
           "f10_folds": {str(k): {kk: (BL.iso(vv) if kk in ("label_end", "trained_through") else vv) for kk, vv in v.items()} for k, v in G.f10.items()},
           "live_equiv_changed_cells_by_year": G.le_changed, "python": sys.version.split()[0], "numpy": np.__version__,
           "utc_written": BL.iso(time.time()), "n_records": len(recs), "fatal": fatal, "records": recs}
    tmp = f"{out_prefix}{tag}.json.tmp"; json.dump(doc, open(tmp, "w")); os.replace(tmp, f"{out_prefix}{tag}.json")
    arrs = {}
    if mode == "P1":
        arrs["anchor"] = np.array(P1["anchor"], np.int64)
        for k in ("pm", "sm", "sm_idx"): arrs[k + "_off"], arrs[k] = pack(P1[k])
        arrs["legz_off"], arrs["legz"] = pack([l.reshape(-1) for l in P1["legz"]])
        arrs["fe"] = np.array(P1["fe"]) if P1["fe"] else np.zeros((0, 829)); arrs["fn"] = np.array(P1["fn"]) if P1["fn"] else np.zeros((0, 829))
    else:
        arrs["anchor"] = np.array(VEC["anchor"], np.int64); arrs["pm_off"], arrs["pm"] = pack(VEC["pm"])
        for k in ("king", "kc", "fc", "king_file", "combo"):
            arrs[k + "_off"], arrs[k + "_idx"], arrs[k + "_val"] = pack(VEC[k])
    tmpz = f"{out_prefix}{tag}.vec.tmp.npz"; np.savez_compressed(tmpz, **arrs); os.replace(tmpz, f"{out_prefix}{tag}.vec.npz")
