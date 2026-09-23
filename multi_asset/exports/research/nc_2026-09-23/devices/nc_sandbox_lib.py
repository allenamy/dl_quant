"""Shared sandbox machinery for the NC rehearsal devices (test_nc_rollback_rehearsal.py, nc_timing_gate.py). Mac, production venv.
Never writes ~/wide_shadow or ~/dl_quant_live: every producer / combo_stage run happens in a sandbox root under ~/cc_tmp, combo_stage under
sandbox-exec (network denied, writes only inside the sandbox, the production state / executor trees unreadable) — the pattern of
~/cc_tmp/news_20260923/devices/mac_candidate_acceptance.py Candidate.build / Candidate.step.
Fake fetcher: exchangeInfo = the archived anchor's TRADING base (snap/<A>/aux.json base_syms); fundingRate per symbol AND the
symbol-less bulk form = the archived ledger rows in [startTime, endTime] (ascending, limit honoured); K-lines of the per-anchor form
(limit, endTime) = [] (the bars <= A are pre-filled from snap/<A>/rolling.npz, the producer only fills NaN rows); K-lines of the backfill
form (startTime paging) = [] unless a synthetic generator is attached for that symbol; 1h K-lines = error (tail scoring not replayed)."""
import os, sys, json, time, shutil, hashlib, subprocess, importlib.util, threading
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"
OLD_PRODUCER = f"{HOME}/cc_tmp/news_20260923/producer_copy/shadow_loop_v3.py"
PIN = {"old_shadow": "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61",
       "old_combo": "fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8",
       "old_dlw": "29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76",
       "old_f8": "2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f"}
CRYPTO_NPZ = f"{HOME}/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz"
BOUND16 = float(np.float16(0.3))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


class NCFake:
    def __init__(self, aux_A, synth=None):
        self.led = aux_A["ledger_tail"]; self.base = list(aux_A.get("base_syms") or []); self.weight_used = 0
        self.calls = {}; self.synth = synth or {}; self._lk = threading.Lock(); self.emulate_parse = None
    def diagnostics(self):
        return {"fake": True, "calls": dict(self.calls), "used_weight_1m_max": None}
    def get(self, path, params, weight=1):
        k = path + ("#bulk" if path == "/fapi/v1/fundingRate" and "symbol" not in params else "")
        with self._lk: self.calls[k] = self.calls.get(k, 0) + 1
        if path == "/fapi/v1/exchangeInfo":
            return {"symbols": [{"symbol": s, "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"} for s in self.base]}
        if path == "/fapi/v1/fundingRate":
            lo, hi, lim = int(params["startTime"]), int(params["endTime"]), int(params.get("limit", 100))
            if "symbol" in params:
                rows = [(int(r[0]) * 1000, params["symbol"], float(r[1])) for r in self.led.get(params["symbol"], [])]
            else:
                rows = [(int(r[0]) * 1000, s, float(r[1])) for s, rr in self.led.items() for r in rr]
            rows = sorted(x for x in rows if lo <= x[0] <= hi)[:lim]
            return [{"symbol": s, "fundingTime": t, "fundingRate": repr(v)} for t, s, v in rows]
        if path == "/fapi/v1/klines":
            if params.get("interval") != "5m": return {"_err": "fake: tail scoring not replayed"}
            if "startTime" in params and params["symbol"] in self.synth:
                return self.synth[params["symbol"]](int(params["startTime"]), int(params["endTime"]), int(params.get("limit", 500)))
            if "startTime" not in params and self.emulate_parse is not None:     # timing gate only: per-anchor rows to give the parse loop its cost
                e = int(params["endTime"]); lim = int(params["limit"])
                return self.emulate_parse(e + 1 - lim * 300000, e, lim)
            return []
        return {"_err": "fake: unsupported"}


def synth_klines_factory(seed):
    """Synthetic 5m K-lines (open_ms, o, h, l, c, v, close_ms, qv, cnt, tbv, tbqv, "0") — a deterministic random walk (one generator per call,
    so concurrent workers are safe); used ONLY to give the backfill / parse paths their processing cost in the timing gate (the values are
    never compared with anything)."""
    def gen(start_ms, end_ms, limit):
        rng = np.random.default_rng([seed, int(start_ms) // 300000])
        t0 = -(-int(start_ms) // 300000) * 300000
        n = max(0, min(limit, (int(end_ms) - t0) // 300000 + 1))
        out = []; c = 1.0 + (t0 // 300000 % 997) / 1000
        for i in range(n):
            o = c; c = o * (1 + rng.normal(0, 0.002)); h = max(o, c) * 1.001; l = min(o, c) * 0.999
            v = 1000 + rng.random() * 100; qv = v * c; cnt = int(50 + rng.integers(0, 50)); tbv = v * 0.5
            out.append([t0 + i * 300000, f"{o:.6f}", f"{h:.6f}", f"{l:.6f}", f"{c:.6f}", f"{v:.3f}", t0 + i * 300000 + 299999,
                        f"{qv:.3f}", cnt, f"{tbv:.3f}", f"{tbv * c:.3f}", "0"])
        return out
    return gen


def crypto_axis_json(symbols_panel):
    z = np.load(CRYPTO_NPZ, allow_pickle=True); cr = z["crypto"].astype(bool)
    assert [str(x) for x in z["symbols"]] == list(symbols_panel), "crypto npz axis differs from symbols_panel"
    return {"symbols": list(symbols_panel), "crypto": [bool(x) for x in cr], "rule": "P1 frozen crypto rule (AMENDMENT 1 §3.2)"}


def build_bundle(dst):
    """Sandbox bundle: small files copied, large ones symlinked (read-only), + crypto_axis.json and its MANIFEST entry. Never the production bundle."""
    os.makedirs(dst)
    for f in os.listdir(f"{WS}/shadow_bundle"):
        s = f"{WS}/shadow_bundle/{f}"
        if os.path.getsize(s) > 5_000_000: os.symlink(s, f"{dst}/{f}")
        else: shutil.copy2(s, f"{dst}/{f}")
    cfg = json.load(open(f"{dst}/config.json"))
    raw = json.dumps(crypto_axis_json(cfg["symbols_panel"])).encode(); open(f"{dst}/crypto_axis.json", "wb").write(raw)
    man = json.load(open(f"{dst}/MANIFEST.json")); man["crypto_axis.json"] = hashlib.sha256(raw).hexdigest()
    json.dump(man, open(f"{dst}/MANIFEST.json", "w"), indent=1)


def build_sandbox(root, kind, tree=None):
    """kind 'new' (tree = the patched NC tree) or 'old' (6080073b / fb5a9407). Returns (ws, exe)."""
    ws = f"{root}/wide_shadow"; exe = f"{root}/dl_quant_live"
    shutil.rmtree(root, ignore_errors=True); os.makedirs(f"{ws}/state"); os.makedirs(f"{ws}/fea171"); os.makedirs(exe)
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", "--exclude", ".env*", f"{LIVE}/live/", f"{exe}/live/"], check=True)
    open(f"{exe}/live/telegram_notify.py", "w").write('import json,os,time\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n'
                                                     '    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), "STUB_PAGES.log"), "a").write(json.dumps({"sev": sev, "msg": msg}) + "\\n"); return {"status": "STUBBED"}\n')
    build_bundle(f"{ws}/shadow_bundle"); os.symlink(f"{WS}/venv", f"{ws}/venv")
    if kind == "new":
        shutil.copy2(f"{tree}/shadow_loop_v3.py", f"{ws}/shadow_loop_v3.py")
        for f in os.listdir(f"{tree}/fea171"):
            if os.path.isfile(f"{tree}/fea171/{f}"): shutil.copy2(f"{tree}/fea171/{f}", f"{ws}/fea171/{f}")
    else:
        assert sha(OLD_PRODUCER) == PIN["old_shadow"]; shutil.copy2(OLD_PRODUCER, f"{ws}/shadow_loop_v3.py")
        for f, key in (("combo_stage.py", "old_combo"), ("dlw_features.py", "old_dlw"), ("f8_higher_order_features.py", "old_f8")):
            assert sha(f"{WS}/fea171/{f}") == PIN[key], f"production {f} is not the pinned old file"
            shutil.copy2(f"{WS}/fea171/{f}", f"{ws}/fea171/{f}")
        for f in ("feature_cache_identity.py", "xfer_syms.npz", "xfer_ref.npz"): shutil.copy2(f"{WS}/fea171/{f}", f"{ws}/fea171/{f}")
    shutil.copy2(f"{WS}/fea171/f10_live_s42_np.npz", f"{ws}/fea171/f10_live_s42_np.npz")
    return ws, exe


def load_producer(ws, tag):
    os.environ["WIDE_SHADOW_HOME"] = ws; os.environ["WIDE_SHADOW_BUNDLE"] = f"{ws}/shadow_bundle"; os.environ["SHADOW_OFFSET_MIN"] = "12"
    spec = importlib.util.spec_from_file_location(f"sl_{tag}_{abs(hash(ws))}_{time.time_ns()}", f"{ws}/shadow_loop_v3.py")
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M


def prefill(st, A, nc_rule, cols_new=None):
    """Bars (st.last_anchor, A] from the archived snap/<A>/rolling.npz appended to the state's own rolling; rows the state already holds keep
    the state's values. cols_new (NC): only these columns take the archived bars in the NEW rows (the NC producer fetches the dynamic list
    only; production also fetched non-crypto names). nc_rule: channel 0 NaN where the previous row has no bar (NC no-cross-gap ingestion)."""
    z = np.load(f"{WS}/state/snap/{A}/rolling.npz", allow_pickle=True); ts = z["ts"].astype(np.int64); d = np.array(z["data"], np.float16)
    assert int(ts[-1]) == A
    pos = {int(t): i for i, t in enumerate(st.cts)}
    keep = None
    if cols_new is not None:
        keep = np.zeros(d.shape[1], bool); keep[np.asarray(cols_new, np.int64)] = True
    cd = np.full((len(ts), d.shape[1], 7), np.nan, np.float16); new_rows = 0
    for k, t in enumerate(ts):
        i = pos.get(int(t))
        if i is not None: cd[k] = st.cd[i]
        else:
            cd[k] = d[k]; new_rows += 1
            if keep is not None: cd[k, ~keep, :] = np.nan
            if nc_rule and k > 0:
                m = ~np.isfinite(cd[k - 1, :, 3].astype(np.float32)) & np.isfinite(cd[k, :, 0].astype(np.float32))
                cd[k, m, 0] = np.nan
    assert new_rows > 0, "prefill added no rows: the state already holds this anchor"
    st.cts, st.cd = ts, cd
    return new_rows


def last_diag(ws, A):
    out = None
    p = f"{ws}/shadow_log.jsonl"
    if os.path.exists(p):
        for l in open(p):
            if '"anchor_diagnostics"' in l:
                r = json.loads(l)
                if r.get("anchor_ts") == A: out = r
    return out


def run_producer(ws, A, fake, nc_rule, tag, cols_new=None):
    """Load the sandbox producer, its own ShadowState (generation verification included), prefill bars, run_anchor(A). Returns dict;
    an exception from ShadowState / run_anchor propagates (callers record it)."""
    M = load_producer(ws, tag)
    cfg, booster, man = M.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    t0 = time.time(); st = M.ShadowState(cfg); t_load = time.time() - t0
    new_rows = prefill(st, A, nc_rule, cols_new)
    la0 = os.getloadavg(); t0 = time.time()
    M.run_anchor(st, fake, cfg, booster, A)
    wall = time.time() - t0; la1 = os.getloadavg()
    tl = f"{ws}/state/target_live/{A}.json"
    return {"module": M, "state": st, "wall_s": round(wall, 2), "load_s": round(t_load, 2), "prefill_rows": new_rows, "loadavg_before": la0, "loadavg_after": la1,
            "target_live_written": os.path.exists(tl), "diag": last_diag(ws, A)}


def run_combo(root, ws, exe, tag, script=None, extra_env=None):
    """The sandbox's combo_stage.py under sandbox-exec (COMBO_LIVE=1 into a rehearsal dir, network denied), as Candidate.step does.
    script: another entry file inside the sandbox (the parity gate's wrapper that exec's combo_stage.py); extra_env: added variables."""
    sb = root; prof = f"{sb}/offline.sb"
    open(prof, "w").write('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))\n'
                          '(deny file-read* file-write* (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE")) (regex #"(^|/)[.]env([^/]*$|/)"))\n')
    os.makedirs(f"{sb}/tmp", exist_ok=True); par = f"{ws}/state/target_live_PARITY"; os.makedirs(par, exist_ok=True)
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": f"{sb}/tmp", "WIDE_SHADOW_HOME": ws, "DL_QUANT_LIVE_ROOT": exe,
           "COMBO_LIVE": "1", "COMBO_LIVE_DIR": par, "HOME": HOME, **(extra_env or {})}
    la0 = os.getloadavg(); t0 = time.time()
    r = subprocess.run(["/usr/bin/sandbox-exec", "-D", f"SANDBOX={sb}", "-D", f"SOURCE_STATE={WS}/state", "-D", f"SOURCE_LIVE={LIVE}", "-f", prof,
                        f"{WS}/venv/bin/python", "-u", script or f"{ws}/fea171/combo_stage.py"], env=env, cwd=f"{ws}/fea171", capture_output=True, text=True)
    wall = time.time() - t0; la1 = os.getloadavg()
    open(f"{sb}/combo_{tag}.log", "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    st_p = f"{ws}/state/combo_live_status.json"
    status = json.load(open(st_p)) if os.path.exists(st_p) else None
    return {"rc": r.returncode, "wall_s": round(wall, 2), "loadavg_before": la0, "loadavg_after": la1, "ok": bool(status and status.get("ok")),
            "status_step": (status or {}).get("step"), "status_why": (status or {}).get("why"), "stderr_tail": r.stderr[-400:], "log": f"{sb}/combo_{tag}.log"}


def carry_prior(ws, A_prev, src_ws=WS):
    """combo_stage's prior-anchor inputs for anchor A_prev+4h: state/weights/<A_prev>.npz and fea171/state_H_{f10,kc,fc}_<A_prev>.npz,
    copied from src_ws (default: production, read-only). Returns the list of copied files; a missing one is listed, never faked."""
    got, miss = [], []
    for src, dst in [(f"{src_ws}/state/weights/{A_prev}.npz", f"{ws}/state/weights/{A_prev}.npz")] + \
                    [(f"{src_ws}/fea171/state_H_{t}_{A_prev}.npz", f"{ws}/fea171/state_H_{t}_{A_prev}.npz") for t in ("f10", "kc", "fc")]:
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); got.append(os.path.basename(dst))
        else: miss.append(src)
    return {"copied": got, "missing": miss}


def phase_key_check(tree):
    """static: every diag.phase("<name>") called in the producer must be a key of _AnchorTiming.phase_s (else KeyError on the next phase)."""
    import re, ast
    src = open(f"{tree}/shadow_loop_v3.py").read()
    called = sorted(set(re.findall(r'diag\.phase\("([a-z_]+)"\)', src)))
    m = re.search(r'self\.phase_s = \{k: None for k in (\((?:[^()]*)\))\}', src, re.S)
    keys = list(ast.literal_eval(m.group(1))) if m else None
    return {"called": called, "keys": keys, "missing": (sorted(set(called) - set(keys)) if keys is not None else "phase_s tuple not found")}


def harness_phase_fix(tree, dst):
    """HARNESS-ONLY workaround (not a deliverable): a copy of the tree whose _AnchorTiming.phase_s also has the missing keys."""
    chk = phase_key_check(tree); shutil.copytree(tree, dst)
    src = open(f"{dst}/shadow_loop_v3.py").read(); old = 'for k in ("setup", "klines",'
    assert src.count(old) == 1 and chk["missing"] == ["exchange_info"], chk
    open(f"{dst}/shadow_loop_v3.py", "w").write(src.replace(old, 'for k in ("setup", "exchange_info", "klines",'))
    return {"patched_tree": dst, "missing_before": chk["missing"], "after": phase_key_check(dst), "sha_before": sha(f"{tree}/shadow_loop_v3.py"),
            "sha_after": sha(f"{dst}/shadow_loop_v3.py"), "edit": 'phase_s keys: ("setup", "klines", ...) -> ("setup", "exchange_info", "klines", ...)'}


def quiet_window_guard(min_remaining_min):
    sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
    from venue_quiet_window import quiet_window_status
    q = quiet_window_status()
    if not q.get("open") or float(q.get("remaining_min", 0)) < min_remaining_min:
        raise SystemExit(f"Mac heavy-work window [N+1:00, N+3:40] not open with >= {min_remaining_min} min: {json.dumps(q)}")
    return q


def copy_state(src, dst):
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if os.path.isfile(f"{src}/{f}"): shutil.copy2(f"{src}/{f}", f"{dst}/{f}")
    for d in ("weights",):
        if os.path.isdir(f"{src}/{d}"): shutil.copytree(f"{src}/{d}", f"{dst}/{d}", dirs_exist_ok=True)


def synthetic_nc_state(tree, A0, out_state):
    """MACHINERY DRY RUN ONLY (not a seeded state): an NC-layout state built from snap/<A0> without the seed pack — production rolling and
    ledger as they are, empty sparse table, EMPTY member history, one crypto name's EMA forced to a reset and one ledger interval to None
    (so the downgrade converter has something to convert). Signed by the patched producer's build_generation_record."""
    os.makedirs(out_state)
    snap = f"{WS}/state/snap/{A0}"
    for f in ("rolling.npz", "leg_returns_live.json"): shutil.copy2(f"{snap}/{f}", f"{out_state}/{f}")
    aux = json.load(open(f"{snap}/aux.json")); cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
    cr = crypto_axis_json(syms)["crypto"]; tb = set(aux.get("base_syms") or [])
    fetch = [s for j, s in enumerate(syms) if s in tb and cr[j]]
    z = np.load(f"{out_state}/rolling.npz", allow_pickle=True); ts = z["ts"].astype(np.int64); fq = np.isfinite(z["data"][:, :, 3].astype(np.float32))
    sidx = {s: j for j, s in enumerate(syms)}
    pct = {}
    for s in fetch:
        f_ = np.flatnonzero(fq[:, sidx[s]])
        if len(f_) and s in aux["prev_close"]: pct[s] = int(ts[f_[-1]])
    # EMA reset victim: an ema entry the NC producer never touches (not in the dynamic list), so the None survives to the downgrade
    v_ema = sorted(s for s in aux["ema"] if s not in set(fetch) and s in tb)[0]
    v_iv = [s for s in fetch if s in aux["ema"] and aux["ledger_tail"].get(s)][1]
    aux["ema"][v_ema] = {"acc": None, "last_ts": None}
    aux["ledger_tail"][v_iv][-1] = [aux["ledger_tail"][v_iv][-1][0], aux["ledger_tail"][v_iv][-1][1], None]
    aux.update({"fetch_syms": fetch, "prev_close_ts": pct, "nc_backfill_residual": []})
    json.dump(aux, open(f"{out_state}/aux.json", "w"))
    np.savez(f"{out_state}/boundary_raw.npz", ts=np.zeros(0, np.int64), col=np.zeros(0, np.int32), raw=np.zeros(0, np.float32))
    np.savez(f"{out_state}/members_hist.npz", anchors=np.zeros(0, np.int64), off=np.zeros(1, np.int64), idx=np.zeros(0, np.int16))
    if os.path.exists(f"{WS}/state/weights/{A0}.npz"):
        os.makedirs(f"{out_state}/weights", exist_ok=True); shutil.copy2(f"{WS}/state/weights/{A0}.npz", f"{out_state}/weights/{A0}.npz")
    os.environ["WIDE_SHADOW_HOME"] = os.path.dirname(out_state)
    spec = importlib.util.spec_from_file_location(f"nc_sign_{time.time_ns()}", f"{tree}/shadow_loop_v3.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.atomic_json(f"{out_state}/generation.json", M.build_generation_record(out_state, int(aux["last_anchor"])))
    return {"synthetic": True, "from_snapshot": A0, "fetch_n": len(fetch), "forced_ema_reset": v_ema, "forced_iv_none": v_iv}
