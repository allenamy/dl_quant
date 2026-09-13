#!/usr/bin/env python3
"""Phase 2 driver — production code path on history with out-of-fold predictions (PREREG_producer_parity_phase2_oos_2026-09-12 + AMENDMENT 2).

THE DEVICE IS NOT MODIFIED. The two Phase 1 devices are imported / executed byte-identical (sha256 asserted):
  shadow_loop_v3_replay.py  4d3bc157…  (production shadow_loop_v3.py e9c98374… + Phase 1's 2 replacements)
  combo_stage_replay.py     f5ba9a82…  (production fea171/combo_stage.py b5c698f9… + Phase 1's 3 replacements)
Every Phase 2 change is an INPUT the production code already takes as an argument, a file it reads, or a state attribute between anchors:
  I1 king score      `booster` argument of run_anchor -> OOFBooster.predict(X): reads the caller frame's `anchor` and `m` (members) and returns the OOF
                     prediction array row for (anchor, m) (float64, NaN where absent or where the admissibility rule withholds it). X is shape-checked only.
  I2 F10 score       combo stage's pipeline-skip branch (`need = False` when mini/data/f8_fea89.npz exists and dlw_targets E_ts[-1] >= A): the driver writes
                     mini/data/{dlw_targets,dlw_fea82,f8_fea89}.npz for anchor A (one row per member with a finite OOF score; column 0 = its average rank / 128,
                     other 170 columns 0) and an identity model file f10_live_s42_np.npz (mu 0, sd 1, w0 = e0, b0 = 13, w1 = 1, b1 = 0, w2 = 1, b2 = -13).
                     Exactness: x = rank/128 is a multiple of 1/256 in (0, 3.2]; gelu(z) = z exactly for z >= 13 (erf saturates to 1.0); (x + 13) - 13 == x in
                     float64 ⇒ the stage computes f10 == x and zf = rankdata(x) == rankdata(OOF) exactly (the stage uses f10 only through rankdata).
  I3 5m cache        st.cts/st.cd = the 11520 holefix2 rows ending at A, names outside symbols_live(A) set to NaN (the producer only fetches symbols_live);
                     combo stage reads state/rolling.npz = the last 2016 such rows (it reads only ai and the 2016-row qv4h window when the pipeline is skipped).
  I4 universe        st.live / st.live_mask / cfg["symbols_live"] = symbols_live(A) (PIT: umask_UPIT_CRYPTO row; PINS: live_pins 450).
  I5 base list       fx.base (exchangeInfo payload) = names with >=1 settlement in (A-24h, A]; st.base pre-seeded to sorted(that | symbols_live(A)) before the
                     anchor (declared deviation D3: the production >=300-name guard would otherwise freeze the base at its start value on 2022-2024 history).
  I6 funding rows    fx.ledger[s] = the settlement rows (ft, rate) the API would return for (last_ts, A+999 ms], capped at 100 (== the full-ledger ReplayFetcher),
                     from ledger_full.npz (data-vision zips U fund_aug API pull, union by second). iv / EMA are computed by the production code itself.
  I7 chain state     cold start at the first anchor: H = 0, LR = [] (no bundle leg_returns), prev_rec = None, ema = {}, ledger = {}; carried in memory after.
  I8 combo inputs    aux.json (prev_rec, ema, base_syms, H, ledger_tail LAST ROW per name — the stage indexes rows[-1] only), leg_returns_live.json = LR[-950:],
                     weights/{A-4h}.npz + state_H_{f10,kc,fc}_{A-4h}.npz from the chain itself; reader modules for the COMBO_LIVE self-validation from a copy of
                     dl_quant_live@918559f live/{external_book,book_config}.py under a replay HOME.
usage: see p2_run.py (arms) — this module has no __main__ side effects beyond the env whitelist assert when run directly."""
import os, sys, json, time, hashlib, importlib, shutil, subprocess, calendar, copy
import numpy as np

P2 = "/workspace/uplift_r2_2026-09-13/P2"
DEVDIR = f"{P2}/devices"
PIN = {"shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42",
       "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"}
SRC = {"cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
       "ledger": (f"{P2}/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
       "universe": (f"{P2}/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
       "king_meta_v4": ("/workspace/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"),
       "dl_targets_v4raw": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
       "dl_targets_ext": ("/workspace/dlw_ext/data/dlw_targets.npz", "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9")}
KING_OOF = {"SLOW_v4": ("/workspace/review_scratch/king_v4/SLOW_v4.npy", "dde19142d017c37dd9bae564ab4a32a4b9b068f6aef8acc91e7ea329f4f1c8a6"),
            "SLOW_v3_on_v4axis": ("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009")}
F10_OOF = {"v4RAW_s42": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "58d64a6ff968458924f53193d2dac20c4541be65d267e108bb43445032bfbdcd"),
           "v4RAW_s2027": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy", "47046ccd6dc7937ce39d9d9a880a34984ad4b6f966889505af0255da8adc136d"),
           "A0_s42": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", "ff109711f5526c68cebb23599e299041a2310caa7857b5ff9aa50464d2e6077b"),
           "A0_s2027": ("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy", "98bfe779261b550f15bbd511dc4637403b7341b25ccc2d4ee15521cb33787f18")}
MONTHLY_MERGE = {"42": "/workspace/f8_v4/mwf_v4b/RAW_s42/results/merge.json", "2027": "/workspace/f8_v4/mwf_v4b/RAW_s2027/results/merge.json"}
READER_SRC = {"external_book.py": "f875fe5411119e9ad852a30d452d2393b28564eca874d71026d9620a251a2c5f", "book_config.py": "a724406e831ec21828ff9475704559fede5693d5606ca99894b850a9e8c50bc5"}
FEA171_RO = {"xfer_ref.npz": "33eb713b72a67665faaf72fa071e0a13c7a7a60a9f732f6e99398ae43dd7bfc8"}
DAY = 86400; H4 = 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def under(p):
    assert os.path.realpath(p).startswith(P2 + "/"), f"write outside P2 root refused: {p}"
    return p
def month_start(t):
    g = time.gmtime(int(t)); return calendar.timegm((g.tm_year, g.tm_mon, 1, 0, 0, 0))


# ─────────────────────────── fold tables (G2-D) ───────────────────────────
def king_fold_table(meta_path, oof_name):
    """SLOW_v4 / SLOW_v3_on_v4axis = pod_export_bundle yearly folds: fold Y is fit on rows whose anchor year < Y (L49-51/L63-65 of the exporter); the
    gradient cutoff is the label end of the last anchor of year Y-1 that has >= 50 finite labels among members. Returns {year: label_end_ts}."""
    M = np.load(meta_path, allow_pickle=True); E = M["E_ts"].astype(np.int64); mem = M["members"]; y4 = M["y4"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E]); out = {}
    for Y in (2024, 2025, 2026):
        cand = [i for i in np.where(yrs < Y)[0][::-1][:400] if np.isfinite(y4[i, mem[i]]).sum() >= 50]
        out[Y] = int(E[max(cand)]) + H4
    return {"model": oof_name, "rule": "fold Y fit on anchor-year < Y; label end = last (year<Y, >=50 labels) anchor + 4h", "label_end": out}


def f10_fold_table(seed):
    """Monthly folds 202501..202608 from the merge receipt (max_train_label_end per fold, trainer causality assert); yearly V2MAIN folds 2023/2024 from
    pod_f10_train_ext.py L266: train = i < first_te - 60 (and year < Y) on the dlw_ext axis ⇒ label end <= E_ext[first_te - 61] + 4h (the >=50-row filter can
    only move it earlier; using the unfiltered bound is conservative for G2-D)."""
    J = json.load(open(MONTHLY_MERGE[seed])); m = J["merged"]; mon = {}
    import glob
    for cf in glob.glob(os.path.dirname(os.path.dirname(MONTHLY_MERGE[seed])) + "/shard*/models/mE1cX7_*_config.json"):
        C = json.load(open(cf)); t = calendar.timegm(time.strptime(C["max_train_label_end"], "%Y-%m-%d %H:%M")); mon[int(C["fold"])] = t
    assert sorted(mon) == sorted(int(k) for k in m["folds"]), "fold configs vs merge receipt"
    EX = np.load(SRC["dl_targets_ext"][0], allow_pickle=True)["E_ts"].astype(np.int64); yearly = {}
    for Y in (2023, 2024):
        fte = int(np.searchsorted(EX, calendar.timegm((Y, 1, 1, 0, 0, 0)))); yearly[Y] = int(EX[fte - 61]) + H4
    return {"seed": seed, "monthly_label_end": mon, "yearly_label_end": yearly, "splice_boundary": calendar.timegm((2025, 1, 1, 0, 0, 0))}


def king_admissible(kt, E):
    Y = time.gmtime(int(E)).tm_year
    if Y not in kt["label_end"]: return None, None, False
    le = kt["label_end"][Y]; return f"{kt['model']}:fold{Y}", le, bool(le < int(E) - 30 * DAY)


def f10_admissible(ft, E):
    g = time.gmtime(int(E))
    if int(E) >= ft["splice_boundary"]:
        ym = g.tm_year * 100 + g.tm_mon
        if ym not in ft["monthly_label_end"]: return None, None, False
        le = ft["monthly_label_end"][ym]; mid = f"F10_mE1cX7_s{ft['seed']}:fold{ym}"
    else:
        if g.tm_year not in ft["yearly_label_end"]: return None, None, False
        le = ft["yearly_label_end"][g.tm_year]; mid = f"F10_V2MAIN_s{ft['seed']}:fold{g.tm_year}"
    return mid, le, bool(le < month_start(E))


# ─────────────────────────── inputs ───────────────────────────
class Globals:
    def __init__(self, arm, verify_sha=True, load_cache=True):
        t0 = time.time(); self.arm = arm; self.shas = {}
        for k, (p, s) in SRC.items():
            if s is not None and verify_sha:
                got = sha(p); assert got == s, (k, got, s)
            self.shas[k] = s
        self.cfg_raw = json.load(open(SRC["bundle_config"][0]))
        self.SYMS = list(self.cfg_raw["symbols_panel"]); assert hashlib.sha256("\n".join(self.SYMS).encode()).hexdigest() == "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
        self.col = {s: j for j, s in enumerate(self.SYMS)}
        if load_cache:
            Z = np.load(SRC["cache"][0], allow_pickle=True); assert [str(s) for s in Z["symbols"]] == self.SYMS
            self.TS = Z["ts"].astype(np.int64); self.DATA = Z["data"]; self.row_of_ts = {int(t): i for i, t in enumerate(self.TS)}
        L = np.load(SRC["ledger"][0], allow_pickle=True); assert [str(s) for s in L["symbols"]] == self.SYMS
        self.L_off = L["off"]; self.L_ft = L["ft"]; self.L_rate = L["rate"]
        U = np.load(SRC["universe"][0], allow_pickle=True); assert [str(s) for s in U["symbols"]] == self.SYMS
        self.U_ts = U["ts"].astype(np.int64); self.U_row = {int(t): i for i, t in enumerate(self.U_ts)}
        self.U_pit = U["pit"]; self.U_tr24 = U["trading24"]; self.pins_list = [str(s) for s in U["pins_list"]]
        # king OOF
        kp, ks = KING_OOF[arm["king_oof"]]
        if verify_sha: assert sha(kp) == ks, ("king_oof", kp)
        self.KOOF = np.load(kp, mmap_mode="r"); self.shas["king_oof"] = ks
        KE = np.load(SRC["king_meta_v4"][0], allow_pickle=True)["E_ts"].astype(np.int64); assert self.KOOF.shape == (len(KE), 829)
        self.K_row = {int(t): i for i, t in enumerate(KE)}
        self.kt = king_fold_table(SRC["king_meta_v4"][0], arm["king_oof"])
        # F10 OOF
        fp, fs = F10_OOF[arm["f10_oof"]]
        if verify_sha: assert sha(fp) == fs, ("f10_oof", fp)
        self.FOOF = np.load(fp, mmap_mode="r"); self.shas["f10_oof"] = fs
        DE = np.load(SRC["dl_targets_v4raw"][0], allow_pickle=True)["E_ts"].astype(np.int64); assert self.FOOF.shape == (len(DE), 829)
        self.F_row = {int(t): i for i, t in enumerate(DE)}
        self.ft = f10_fold_table(arm["f10_seed"])
        if arm.get("fold_table_override"):          # G2-E red-capability control ONLY: replaces label ends in the audit table
            for k, v in arm["fold_table_override"].get("f10_monthly", {}).items(): self.ft["monthly_label_end"][int(k)] = int(v)
            for k, v in arm["fold_table_override"].get("king", {}).items(): self.kt["label_end"][int(k)] = int(v)
        self.load_s = round(time.time() - t0, 1)

    def live_names(self, A):
        if self.arm["universe"] == "pins": return list(self.pins_list)
        r = self.U_row[int(A)]; return [self.SYMS[j] for j in np.where(self.U_pit[r])[0]]

    def trading24(self, A):
        r = self.U_row[int(A)]; return [self.SYMS[j] for j in np.where(self.U_tr24[r])[0]]

    def ledger_rows(self, s, last_ts, A):
        j = self.col[s]; a, b = self.L_off[j], self.L_off[j + 1]; ft = self.L_ft[a:b]
        lo = np.searchsorted(ft, int(last_ts), side="right"); hi = np.searchsorted(ft, int(A), side="right")
        hi = min(hi, lo + 100)
        return [[int(ft[k]), float(self.L_rate[a + k])] for k in range(lo, hi)]


class OOFBooster:
    """`booster` argument replacement. predict(X) is called once per anchor at run_anchor's `pred = booster.predict(X)`; the caller frame holds `anchor`
    and `m`. Returns float64 OOF scores for (anchor, m); NaN where the OOF array has no value or where the admissibility rule withholds the model."""
    def __init__(self, G, policy):
        self.G = G; self.policy = policy; self.last = None
    def predict(self, X):
        f = sys._getframe(1)
        assert f.f_code.co_name == "run_anchor", f.f_code.co_name
        A = int(f.f_locals["anchor"]); m = np.asarray(f.f_locals["m"], np.int64)
        assert X.shape[0] == len(m), (X.shape, len(m))
        mid, le, adm = king_admissible(self.G.kt, A)
        r = self.G.K_row.get(A)
        out = np.full(len(m), np.nan)
        served = False
        if r is not None and mid is not None and (adm or self.policy == "serve_all"):
            out = self.G.KOOF[r, m].astype(np.float64); served = bool(np.isfinite(out).any())
        self.last = {"anchor": A, "n_members": int(len(m)), "n_finite": int(np.isfinite(out).sum()), "model": mid, "label_end": le, "admissible": adm, "served": served}
        return out


def run_stage_forked(script, cwd, env, log_path, timeout=600):
    """Execute the byte-identical stage script in a FORKED child of this process (numpy/scipy already imported), with os.environ replaced by `env`,
    cwd = `cwd`, stdout/stderr to `log_path`. Equivalent to `python -B script` with that env except that the interpreter is warm (measured equal
    bitwise against subprocess mode on the timing anchors: receipts/RUN_*forkcheck*). Returns (rc, stdout_lines, stderr_lines)."""
    import runpy, traceback, signal as _sig
    sys.stdout.flush(); sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644); os.dup2(fd, 1); os.dup2(fd, 2); os.close(fd)
            sys.stdout = os.fdopen(1, "w", buffering=1); sys.stderr = sys.stdout
            os.environ.clear(); os.environ.update(env); os.chdir(cwd)
            sys.argv = [script]
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
            os.kill(pid, _sig.SIGKILL); os.waitpid(pid, 0); return 124, [], ["TIMEOUT"]
        time.sleep(0.005)
    rc = os.waitstatus_to_exitcode(status)
    lines = open(log_path, errors="replace").read().strip().splitlines()
    return rc, lines, [l for l in lines if "Traceback" in l or "Error" in l][-4:]


def write_f10_injection(G, A, pm, fea_dir):
    """I2: pipeline-skip files + identity model. Returns (n_scored, model_id, label_end, admissible, served)."""
    mid, le, adm = f10_admissible(G.ft, A)
    r = G.F_row.get(int(A)); v = np.full(len(pm), np.nan)
    if r is not None and mid is not None and (adm or G.arm["serve_policy"] == "serve_all"):
        v = G.FOOF[r, pm].astype(np.float64)
    ok = np.isfinite(v); n = int(ok.sum())
    from scipy.stats import rankdata
    x = np.zeros(n, np.float32)
    if n:
        rk = rankdata(v[ok]); x = (rk / 128.0).astype(np.float32)
        assert np.all(x * 128.0 == rk) and x.max() <= 4.0, "rank encoding not exact"
    md = under(f"{fea_dir}/mini/data"); os.makedirs(md, exist_ok=True)
    X82 = np.zeros((max(n, 0), 82), np.float32); X82[:, 0] = x
    np.savez(f"{md}/dlw_targets.npz", E_ts=np.array([int(A)], np.int64))
    np.savez(f"{md}/dlw_fea82.npz", pair_a=np.zeros(n, np.int64), pair_s=pm[ok].astype(np.int64), X=X82)
    np.savez(f"{md}/f8_fea89.npz", X=np.zeros((n, 89), np.float32))
    return {"n_scored": n, "model": mid, "label_end": le, "admissible": adm, "served": bool(n > 0)}


def write_identity_model(fea_dir):
    p = under(f"{fea_dir}/f10_live_s42_np.npz")
    w0 = np.zeros((1, 171)); w0[0, 0] = 1.0
    np.savez(p, mu=np.zeros(171), sd_=np.ones(171), w0=w0, b0=np.array([13.0]), w1=np.array([[1.0]]), b1=np.array([0.0]), w2=np.array([[1.0]]), b2=np.array([-13.0]))
    return sha(p)


def selftest_identity_model(fea_dir):
    """Run the stage's own forward expressions (copied verbatim from combo_stage_replay.py L164-170) on a probe to show f10 == x exactly."""
    from scipy.special import erf
    M = np.load(f"{fea_dir}/f10_live_s42_np.npz")
    def gelu(x): return 0.5*x*(1+erf(x/np.sqrt(2)))
    rk = np.array([1.0, 2.0, 2.5, 2.5, 400.0, 399.5, 17.0]); x = (rk / 128.0).astype(np.float32)
    X171 = np.zeros((len(x), 171), np.float32); X171[:, 0] = x
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    f10 = (h @ M["w2"].T + M["b2"]).squeeze(-1)
    return bool(np.array_equal(f10, x.astype(np.float64)))


# ─────────────────────────── chain ───────────────────────────
def run_chain(arm, G, anchors, rh, out_path, record_from=None, stop_after=None, log_every=50):
    """Serial production-path chain over `anchors` (sorted, 4h grid). Records every anchor >= record_from."""
    import pickle
    os.environ["WIDE_SHADOW_HOME"] = under(rh); os.environ["WIDE_SHADOW_BUNDLE"] = "/workspace/shadow_bundle_v3"
    for d in ("state/weights", "state/target_live", "fea171/mini/data"): os.makedirs(under(f"{rh}/{d}"), exist_ok=True)
    for f, s in PIN.items(): assert sha(f"{DEVDIR}/{f}") == s, f
    sys.path.insert(0, DEVDIR)
    dev = importlib.import_module("shadow_loop_v3_replay")
    assert dev.STATE_DIR == f"{rh}/state" and dev.HOME == rh, (dev.STATE_DIR, dev.HOME)
    assert dev.REPLAY_META["production_sha256"] == "e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e"
    # replay home: bundle config (read-only symlink), fea171 refs, identity model, reader modules
    for lnk, tgt in ((f"{rh}/shadow_bundle", "/workspace/shadow_bundle_v3"),):
        if not os.path.islink(lnk): os.symlink(tgt, lnk)
    for f, s in FEA171_RO.items():
        src = f"{P2}/work/fea171_ro/{f}"; assert sha(src) == s, f; shutil.copy2(src, under(f"{rh}/fea171/{f}"))
    home = under(f"{rh}/home"); os.makedirs(f"{home}/dl_quant_live/live", exist_ok=True)
    for f, s in READER_SRC.items():
        src = f"{P2}/work/reader_ro/{f}"; assert sha(src) == s, f; shutil.copy2(src, f"{home}/dl_quant_live/live/{f}")
    idsha = write_identity_model(f"{rh}/fea171"); assert selftest_identity_model(f"{rh}/fea171"), "identity model selftest"
    cfg = copy.deepcopy(G.cfg_raw); cfg["_booster_sha"] = "OOF:" + arm["king_oof"]
    class ReplayState(dev.ShadowState):
        def save(self): pass
    st = ReplayState.__new__(ReplayState)
    st.syms = cfg["symbols_panel"]; st.NW = 829; st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    st.prev_close = {}; st.H = np.zeros(829); st.last_anchor = int(anchors[0]) - H4; st.ema = {}; st.ledger = {}; st.prev_rec = None
    st.LR = {"king": [], "rev24": [], "fund": []}
    fx = dev.ReplayFetcher([], {}); booster = OOFBooster(G, arm["serve_policy"])
    recs = []; vecs = {"anchor": [], "king": [], "kc": [], "fc": []}; t_start = time.time(); combo_env_base = {"PATH": "/usr/bin:/bin", "HOME": home, "WIDE_SHADOW_HOME": rh, "COMBO_LIVE": "1",
                                                         "COMBO_LIVE_DIR": f"{rh}/state/target_live_combo", "REPLAY_TRUNCATE_CACHE": "1",
                                                         "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    for k, A in enumerate(anchors):
        A = int(A); t0 = time.time(); tim = {}
        live = G.live_names(A); lmask = np.zeros(829, bool); lmask[[G.col[s] for s in live]] = True
        st.live = live; st.live_mask = lmask; cfg["symbols_live"] = live
        tr = G.trading24(A); st.base = sorted(set(tr) | set(live)); fx.base = tr
        fx.ledger = {s: G.ledger_rows(s, (st.ledger[s][-1][0] if st.ledger.get(s) else A - 40 * DAY), A) for s in st.base}
        ai = G.row_of_ts[A]; i0 = max(0, ai + 1 - dev.CACHE_ROWS)
        cd = np.array(G.DATA[i0:ai + 1]); cd[:, ~lmask, :] = np.nan
        st.cts = G.TS[i0:ai + 1].copy(); st.cd = cd; tim["cache"] = time.time() - t0
        for d_ in ("weights", "target_live"):
            for f in (f"{rh}/state/{d_}/{A}.json", f"{rh}/state/{d_}/{A}.json.sha256", f"{rh}/state/{d_}/{A}.npz"):
                if os.path.exists(f): os.remove(f)
        if os.path.exists(f"{rh}/shadow_log.jsonl"): os.remove(f"{rh}/shadow_log.jsonl")
        lr_len0 = len(st.LR["king"]); booster.last = None; t1 = time.time()
        dev.run_anchor(st, fx, cfg, booster, A); tim["king"] = time.time() - t1
        logrows = []
        if os.path.exists(f"{rh}/shadow_log.jsonl"):
            for l in open(f"{rh}/shadow_log.jsonl"):
                try: logrows.append(json.loads(l))
                except Exception: pass
        sig = [r for r in logrows if r.get("e") == "signal"]; skip = [r for r in logrows if r.get("e") == "anchor_skip"]
        rec = {"anchor": A, "utc": iso(A), "n_live": len(live), "n_base": len(st.base), "king_oof": booster.last, "signal": sig[-1] if sig else None,
               "skip": skip[-1] if skip else None, "lr_appended": len(st.LR["king"]) - lr_len0, "lr_len": len(st.LR["king"])}
        wrote = os.path.exists(f"{rh}/state/weights/{A}.npz")
        if wrote:
            nz = np.where(np.abs(st.H) > 1e-12)[0]; vk = (nz.astype(np.int32), st.H[nz].astype(np.float64))
            # ── combo stage inputs ──
            t2 = time.time()
            json.dump({"prev_close": {}, "H": {str(int(j)): float(st.H[j]) for j in np.where(np.abs(st.H) > 1e-9)[0]}, "last_anchor": st.last_anchor,
                       "ema": st.ema, "ledger_tail": {s: r[-1:] for s, r in st.ledger.items()}, "base_syms": list(st.base), "prev_rec": st.prev_rec},
                      open(under(f"{rh}/state/aux.json"), "w"))
            json.dump({leg: list(map(float, st.LR[leg][-950:])) for leg in st.LR}, open(under(f"{rh}/state/leg_returns_live.json"), "w"))
            j0 = max(0, cd.shape[0] - 2016)
            np.savez(under(f"{rh}/state/rolling.npz"), ts=st.cts[j0:], data=cd[j0:])
            pm = np.array(st.prev_rec["members"], np.int64)
            rec["f10_oof"] = write_f10_injection(G, A, pm, f"{rh}/fea171")
            for d_ in ("target_combo", "target_blend", "target_live_combo", "target_live_king", "weights_combo"):
                for f in (f"{rh}/state/{d_}/{A}.json", f"{rh}/state/{d_}/{A}.json.sha256", f"{rh}/state/{d_}/{A}.npz"):
                    if os.path.exists(f): os.remove(f)
            if os.path.exists(f"{rh}/state/combo_live_status.json"): os.remove(f"{rh}/state/combo_live_status.json")
            tim["combo_inputs"] = time.time() - t2; t3 = time.time()
            if arm.get("combo_launch", "fork") == "subprocess":
                p = subprocess.run([sys.executable, "-B", f"{DEVDIR}/combo_stage_replay.py"], cwd=f"{rh}/fea171", env=combo_env_base, capture_output=True, text=True, timeout=600)
                rc_, out_, err_ = p.returncode, p.stdout.strip().splitlines(), p.stderr.strip().splitlines()
            else:
                rc_, out_, err_ = run_stage_forked(f"{DEVDIR}/combo_stage_replay.py", f"{rh}/fea171", combo_env_base, under(f"{rh}/combo_stage.log"))
            tim["combo"] = time.time() - t3
            rec["combo_rc"] = rc_; rec["combo_tail"] = out_[-4:]; rec["combo_err"] = err_[-4:]
            has_states = os.path.exists(f"{rh}/fea171/state_H_kc_{A}.npz") and os.path.exists(f"{rh}/fea171/state_H_fc_{A}.npz")
            # KNOWN PRODUCTION CRASH (not a replay defect): combo_stage chain() returns None when a book's z is all zero (e.g. cold start: king leg empty and the
            # fund leg not yet fresh), and the state-saving loop `_nz = np.where(np.abs(_sm) > 1e-9)[0]` raises TypeError before kc/fc states are written.
            # Production behaviour after such a crash: no combo file for the anchor (the producer's king file stays = traded), next anchor warm-starts kc/fc.
            known_crash = (rc_ == 1 and not has_states and any("_nz = np.where(np.abs(_sm) > 1e-9)[0]" in l for l in out_)
                           and any("TypeError: bad operand type for abs(): 'NoneType'" in l for l in out_))
            if rc_ not in (0, 3) and not known_crash:
                recs.append(rec); _dump(out_path, arm, G, recs, vecs, idsha, fatal=f"combo_stage rc={rc_} at {iso(A)}: {out_[-6:]}")
                raise RuntimeError(f"combo_stage rc={rc_} at {iso(A)}: {out_[-6:]}")
            rec["combo_known_crash"] = "none_target_all_zero_z" if known_crash else None
            if has_states:
                kc = np.load(f"{rh}/fea171/state_H_kc_{A}.npz"); fc = np.load(f"{rh}/fea171/state_H_fc_{A}.npz")
                assert int(kc["anchor"]) == A and int(fc["anchor"]) == A
                vkc = (kc["idx"].astype(np.int32), kc["val"].astype(np.float64)); vfc = (fc["idx"].astype(np.int32), fc["val"].astype(np.float64))
                tc = json.load(open(f"{rh}/state/target_combo/{A}.json"))
                rec["combo_meta"] = {k_: tc.get(k_) for k_ in ("w3_masked", "kc_state_source", "fc_state_source", "gross", "kc_gross", "fc_gross", "n_f10_scored")}
                rec["ftrim"] = {k_: tc["ftrim"].get(k_) for k_ in ("n_kc", "n_fc", "rn8_coverage")}
            else:
                vkc = vfc = (np.zeros(0, np.int32), np.zeros(0)); rec["combo_meta"] = None; rec["ftrim"] = None
            stt = json.load(open(f"{rh}/state/combo_live_status.json")) if os.path.exists(f"{rh}/state/combo_live_status.json") else None
            rec["combo_live_status"] = stt
            tl = f"{rh}/state/target_live_combo/{A}.json"
            if has_states and stt and stt.get("ok") and os.path.exists(tl):
                w = json.load(open(tl))["weights"]; rec["traded_file"] = "combo"
                cr = np.zeros(829); cr[vkc[0]] += 0.55 * vkc[1]; cr[vfc[0]] += 0.45 * vfc[1]
                wv = np.zeros(829); wv[[G.col[s] for s in w]] = list(w.values())
                rec["combo_file_vs_states_Linf"] = float(np.abs(wv - np.where(np.abs(cr) > 1e-9, cr, 0.0)).max())
            else:
                rec["traded_file"] = "king"
            # prune files the next anchor does not read
            Ap = A - H4
            for f in (f"{rh}/state/weights/{Ap}.npz", f"{rh}/fea171/state_H_f10_{Ap}.npz", f"{rh}/fea171/state_H_kc_{Ap}.npz", f"{rh}/fea171/state_H_fc_{Ap}.npz",
                      f"{rh}/state/target_live/{Ap}.json", f"{rh}/state/target_live/{Ap}.json.sha256"):
                if os.path.exists(f): os.remove(f)
            for d_ in ("target_combo", "target_blend", "target_live_combo", "target_live_king", "weights_combo"):
                for f in (f"{rh}/state/{d_}/{Ap}.json", f"{rh}/state/{d_}/{Ap}.json.sha256", f"{rh}/state/{d_}/{Ap}.npz"):
                    if os.path.exists(f): os.remove(f)
        else:
            rec["combo_rc"] = None; rec["traded_file"] = "none(producer_skip)"; vk = vkc = vfc = (np.zeros(0, np.int32), np.zeros(0))
        tim["total"] = time.time() - t0; rec["timing_s"] = {k_: round(v_, 3) for k_, v_ in tim.items()}
        if record_from is None or A >= int(record_from):
            recs.append(rec); vecs["anchor"].append(A)
            for nm_, v_ in (("king", vk), ("kc", vkc), ("fc", vfc)): vecs[nm_].append(v_)
        if log_every and (k % log_every == 0 or k == len(anchors) - 1):
            print(json.dumps({"k": k, "anchor": iso(A), "t": rec["timing_s"], "live": len(live), "base": len(st.base), "members": (rec["signal"] or {}).get("members"),
                              "sel": (rec["signal"] or {}).get("sel"), "w3": (rec["signal"] or {}).get("w3"), "king_oof_finite": (booster.last or {}).get("n_finite"),
                              "f10": (rec.get("f10_oof") or {}).get("n_scored"), "combo_rc": rec.get("combo_rc"), "traded": rec["traded_file"],
                              "why": ((rec.get("combo_live_status") or {}).get("why") or "")[:80]}), flush=True)
        if stop_after and time.time() - t_start > stop_after: break
    _dump(out_path, arm, G, recs, vecs, idsha)
    return recs


def _dump(out_path, arm, G, recs, vecs, idsha, fatal=None):
    doc = {"arm": arm, "input_shas": G.shas, "identity_model_sha256": idsha, "king_fold_table": G.kt, "f10_fold_table": G.ft,
           "device_shas": PIN, "driver_sha256": sha(os.path.abspath(__file__)), "python": sys.version.split()[0], "numpy": np.__version__,
           "utc_written": iso(time.time()), "n_records": len(recs), "fatal": fatal, "records": recs}
    tmp = under(out_path + ".tmp"); json.dump(doc, open(tmp, "w")); os.replace(tmp, under(out_path))
    arrs = {"anchor": np.array(vecs["anchor"], np.int64)}
    for nm_ in ("king", "kc", "fc"):
        lens = [len(v[0]) for v in vecs[nm_]]; arrs[f"{nm_}_off"] = np.concatenate([[0], np.cumsum(lens)]).astype(np.int64)
        arrs[f"{nm_}_idx"] = np.concatenate([v[0] for v in vecs[nm_]]).astype(np.int32) if lens else np.zeros(0, np.int32)
        arrs[f"{nm_}_val"] = np.concatenate([v[1] for v in vecs[nm_]]).astype(np.float64) if lens else np.zeros(0)
    tmpz = under(out_path.replace(".json", "") + ".vec.tmp.npz"); np.savez_compressed(tmpz, **arrs); os.replace(tmpz, under(out_path.replace(".json", "") + ".vec.npz"))
