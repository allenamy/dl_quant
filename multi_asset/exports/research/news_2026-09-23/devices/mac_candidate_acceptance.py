#!/usr/bin/env python3
"""Candidate-package acceptance (R10-B02) — the deploy copy of the producer, run forward from the SAME starting state as the evaluation,
checked item by item against the evaluation. Mac, production venv, quiet window only; no network (fake fetcher + sandbox-exec for
combo_stage); never writes ~/wide_shadow or ~/dl_quant_live. The candidate package is a PARAMETER (King model, F10 npz, manifest,
evaluation rows) so the same device accepts NEW_S or FRESH.

Deploy copy (sandbox) at the start anchor A0 = the candidate package installed exactly as the deploy manual does:
  producer file = --producer (patched, symbols_fetch aware) · bundle config + symbols_fetch (450 + --added) · King = --king · F10 = --f10 ·
  state = state/snap/<A0> + the added names' columns (x0918r stand-in for the backfill, hole cells NaN) · EMA re-seeded to the training
  replay at A0 (--replay) · seats seeded with the evaluation's leg-return series up to A0 · kc/fc chain state = the evaluation's at A0 ·
  prev_rec members/legz = the evaluation's at A0.
Then for A = A0+4h … A0+4h·n: the producer's run_anchor (fake fetcher: bars from state/snap/<A> + the added columns, funding rows and TRADING
base from state/snap/<A>/aux.json) followed by the REAL combo_stage.py (COMBO_LIVE=1, rehearsal output dir) under sandbox-exec.
Checked at every anchor against the evaluation rows (--eval): members; training features X78 / X82 / X89 recomputed with the producer code
on the deploy copy's actual state; King predictions (package booster, Mac) vs King OOF; King / rev24 / fund leg z; F10 numpy scores vs
the GPU OOF; seats w3 (masked, as written in target_combo); combo target (weights_combo = combo_raw) vs the evaluation raw; publish / HOLD.
A HOLD anchor is included (chain state zeroed at A0 on both sides ⇒ gross < 0.4 ⇒ both must HOLD).
Controls (each must turn RED): F10 = another seed's export; no symbols_fetch (and no added columns); EMA not re-seeded.
Any unexplained difference ⇒ FAIL; exit 0 only if the baseline passes, the HOLD anchor holds on both sides, and every control is red.
Differences with a NAMED, pre-declared cause are reported separately and do not count as unexplained:
  R2 fund-leg rank base: production base (exchangeInfo TRADING ∪ fetch) includes names outside the 829-name axis ⇒ fund z / combo;
     attributed by recomputing fund z with the base restricted to the axis — must then be bitwise equal.
  R4 F10 numerics: evaluation used GPU torch scores, serving uses numpy ⇒ |Δscore| must be ≤ 1e-5 (the export V1 bound) and the combo is
     attributed by recomputing combo_target.step on the served inputs (numpy scores) — must then be bitwise equal to the served combo_raw.
usage: ~/wide_shadow/venv/bin/python mac_candidate_acceptance.py --king F --f10 F --manifest F --eval F --replay F --added F --x0918r F
         --holes F --producer F --control-f10 F --start A0 --n N --out DIR
"""
import os, sys, json, time, shutil, hashlib, subprocess, importlib.util, argparse
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"
P = f"{HOME}/cc_tmp/news_20260923"
sys.path.insert(0, f"{P}/devices"); sys.path.insert(0, f"{P}/deploy")
import news_hist_features as H
import news_legs as NL
from test_fetchlist_split import FakeFetcher
# the training-build device reads the producer feature files from the local sha-identical copy (P5-0 / P5-a verified)
H.W = f"{P}/parity"; H.PROD = f"{P}/producer_copy"; H.SHADOW_SRC = f"{H.PROD}/shadow_loop_v3.py"; H.COMBO_SRC = f"{H.PROD}/fea171/combo_stage.py"
H.DLW_SRC = f"{H.PROD}/fea171/dlw_features.py"; H.F8_SRC = f"{H.PROD}/fea171/f8_higher_order_features.py"
H.XSYMS = f"{H.PROD}/fea171/xfer_syms.npz"; H.XREF = f"{H.PROD}/fea171/xfer_ref.npz"
F10_NUMERICS_TOL = 1e-5      # R4: numpy (serving) vs GPU torch (evaluation) F10 score difference allowed — same bound as the export V1 gate

PATCHED_SHA = "ed11d731ffc13ef1333c3fabe044bc209485ba237fd9b8ae11aeccb014be1ec9"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def bits_eq(a, b, dt):
    a = np.ascontiguousarray(np.asarray(a, dt)); b = np.ascontiguousarray(np.asarray(b, dt))
    if a.shape != b.shape: return False
    u = {np.float16: np.uint16, np.float32: np.uint32, np.float64: np.uint64}[dt]
    return bool(np.all((a.view(u) == b.view(u)) | (np.isnan(a.astype(np.float64)) & np.isnan(b.astype(np.float64)))))


def parse():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    for k in ("king", "f10", "manifest", "eval", "replay", "added", "x0918r", "holes", "producer", "control-f10", "out"): ap.add_argument("--" + k, required=True)
    ap.add_argument("--start", type=int, required=True); ap.add_argument("--n", type=int, required=True)
    a = ap.parse_args()          # unknown arguments ⇒ argparse error, exit 2
    return a


class Candidate:
    """a deploy copy of the producer in <root>, driven anchor by anchor"""
    def __init__(self, a, root, f10_file, fetchlist=True, reseed=True, zero_state=False):
        self.a, self.root, self.f10_file, self.fetchlist, self.reseed, self.zero_state = a, root, f10_file, fetchlist, reseed, zero_state
        self.ws = f"{root}/wide_shadow"; self.exe = f"{root}/dl_quant_live"
        self.E = np.load(a.eval, allow_pickle=True); self.syms = [str(s) for s in self.E["symbols"]]; self.sidx = {s: j for j, s in enumerate(self.syms)}
        self.added = json.load(open(a.added)); X = np.load(a.x0918r, allow_pickle=True); self.xts = X["ts"].astype(np.int64); self.xd = X["data"]; self.row0 = int(X["row0"])
        self.HZ = np.load(a.holes)

    def added_cols(self, rts):
        xi = np.searchsorted(self.xts, rts); assert np.array_equal(self.xts[xi], rts), "x0918r stand-in does not cover the window"
        pos = {int(v): q for q, v in enumerate(xi)}; cols = {}
        for s in self.added:
            j = self.sidx[s]; col = np.array(self.xd[xi, j, :], np.float16)
            for rr in (self.HZ["row"][self.HZ["col"] == j] - self.row0):
                if int(rr) in pos: col[pos[int(rr)]] = np.nan
            cols[j] = col
        return cols

    def rolling_at(self, A):
        z = np.load(f"{WS}/state/snap/{A}/rolling.npz", allow_pickle=True); ts = z["ts"].astype(np.int64); d = np.array(z["data"], np.float16)
        if self.fetchlist:
            for j, col in self.added_cols(ts).items(): d[:, j, :] = col
        return ts, d

    def build(self, A0):
        a = self.a; shutil.rmtree(self.root, ignore_errors=True); os.makedirs(f"{self.ws}/state"); os.makedirs(f"{self.ws}/fea171"); os.makedirs(f"{self.exe}")
        subprocess.run(["rsync", "-a", "--exclude", "__pycache__", "--exclude", ".env*", f"{LIVE}/live/", f"{self.exe}/live/"], check=True)
        open(f"{self.exe}/live/telegram_notify.py", "w").write('import json,os,time\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n'
                                                            '    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), "STUB_PAGES.log"), "a").write(json.dumps({"sev": sev, "msg": msg}) + "\\n"); return {"status": "STUBBED"}\n')
        shutil.copytree(f"{WS}/shadow_bundle", f"{self.ws}/shadow_bundle"); os.symlink(f"{WS}/venv", f"{self.ws}/venv")
        shutil.copy2(a.producer, f"{self.ws}/shadow_loop_v3.py")
        for f in ("combo_stage.py", "dlw_features.py", "f8_higher_order_features.py", "feature_cache_identity.py", "xfer_syms.npz", "xfer_ref.npz"): shutil.copy2(f"{WS}/fea171/{f}", f"{self.ws}/fea171/{f}")
        shutil.copytree(f"{WS}/fea171/combosnap", f"{self.ws}/fea171/combosnap")
        shutil.copy2(self.f10_file, f"{self.ws}/fea171/f10_live_s42_np.npz"); shutil.copy2(a.king, f"{self.ws}/shadow_bundle/slow2026.txt")
        cfg = json.load(open(f"{self.ws}/shadow_bundle/config.json"))
        if self.fetchlist: cfg["symbols_fetch"] = list(cfg["symbols_live"]) + sorted(self.added)
        raw = json.dumps(cfg).encode(); open(f"{self.ws}/shadow_bundle/config.json", "wb").write(raw)
        man = json.load(open(f"{self.ws}/shadow_bundle/MANIFEST.json")); man["config.json"] = hashlib.sha256(raw).hexdigest(); man["slow2026.txt"] = sha(a.king)
        json.dump(man, open(f"{self.ws}/shadow_bundle/MANIFEST.json", "w"), indent=1)
        # state at A0
        ts, d = self.rolling_at(A0); np.savez_compressed(f"{self.ws}/state/rolling.npz", ts=ts, data=d)
        aux = json.load(open(f"{WS}/state/snap/{A0}/aux.json")); E = self.E
        if self.reseed:
            R = np.load(a.replay); ia = int(np.flatnonzero(R["anchors"].astype(np.int64) == A0)[0])
            for j in np.flatnonzero(np.isfinite(R["ema_acc"][ia])):
                aux["ema"][self.syms[j]] = {"acc": float(R["ema_acc"][ia, j]), "last_ts": int(R["last_ft"][ia, j])}
        m = E[f"m_{A0}"].astype(int).tolist(); pr = aux["prev_rec"]
        pr.update({"members": m, "legz": {"king": [float(x) for x in np.nan_to_num(E[f"KZ_{A0}"])], "rev24": [float(x) for x in np.nan_to_num(E[f"Z24_{A0}"])],
                                            "fund": [float(x) for x in np.nan_to_num(E[f"ZFD_{A0}"])]}})
        aux["prev_rec"] = pr
        json.dump(aux, open(f"{self.ws}/state/aux.json", "w"))
        LR = E[f"LR_upto_{A0}"][-950:]
        json.dump({"king": LR[:, 0].tolist(), "rev24": LR[:, 1].tolist(), "fund": LR[:, 2].tolist()}, open(f"{self.ws}/state/leg_returns_live.json", "w"))
        for tag in ("kc", "fc"):
            v = np.zeros(len(self.syms)) if self.zero_state else E[f"{tag}_{A0}"]; nz = np.flatnonzero(np.abs(v) > 1e-9)
            np.savez(f"{self.ws}/fea171/state_H_{tag}_{A0}.npz", anchor=A0, idx=nz, val=v[nz])
        os.makedirs(f"{self.ws}/state/weights"); shutil.copy2(f"{WS}/state/weights/{A0}.npz", f"{self.ws}/state/weights/{A0}.npz")
        M = self.module(); M.atomic_json(f"{self.ws}/state/generation.json", M.build_generation_record(f"{self.ws}/state", A0))

    def module(self):
        os.environ["WIDE_SHADOW_HOME"] = self.ws; os.environ["WIDE_SHADOW_BUNDLE"] = f"{self.ws}/shadow_bundle"; os.environ["SHADOW_OFFSET_MIN"] = "12"
        spec = importlib.util.spec_from_file_location(f"sl_{abs(hash(self.ws))}_{np.random.randint(1 << 30)}", f"{self.ws}/shadow_loop_v3.py")
        M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M

    def step(self, A):
        M = self.module(); cfg, booster, man = M.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
        st = M.ShadowState(cfg)                                   # the producer's own loader: generation + checkpoint verification
        ts, d = self.rolling_at(A); st.cts, st.cd = ts, d        # bars ≤ A (live for the 450, x0918r stand-in for the added names)
        aux_A = json.load(open(f"{WS}/state/snap/{A}/aux.json")); M.run_anchor(st, FakeFetcher(aux_A), cfg, booster, A)
        sb = self.root
        prof = f"{sb}/offline.sb"
        open(prof, "w").write('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))\n'
                              '(deny file-read* file-write* (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE")) (regex #"(^|/)[.]env([^/]*$|/)"))\n')
        os.makedirs(f"{sb}/tmp", exist_ok=True); par = f"{self.ws}/state/target_live_PARITY"; os.makedirs(par, exist_ok=True)
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": f"{sb}/tmp", "WIDE_SHADOW_HOME": self.ws, "DL_QUANT_LIVE_ROOT": self.exe,
               "COMBO_LIVE": "1", "COMBO_LIVE_DIR": par, "HOME": HOME}
        r = subprocess.run(["/usr/bin/sandbox-exec", "-D", f"SANDBOX={sb}", "-D", f"SOURCE_STATE={WS}/state", "-D", f"SOURCE_LIVE={LIVE}", "-f", prof,
                            f"{WS}/venv/bin/python", "-u", f"{self.ws}/fea171/combo_stage.py"], env=env, cwd=f"{self.ws}/fea171", capture_output=True, text=True)
        open(f"{sb}/combo_{A}.log", "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
        status = json.load(open(f"{self.ws}/state/combo_live_status.json"))
        tc = json.load(open(f"{self.ws}/state/target_combo/{A}.json"))
        wc = f"{self.ws}/state/weights_combo/{A}.npz"
        raw = np.zeros(len(self.syms))
        if os.path.exists(wc) and status.get("ok"):
            z = np.load(wc); raw[z["idx"].astype(int)] = z["val"].astype(np.float64)
        aux = json.load(open(f"{self.ws}/state/aux.json"))
        return {"rc": r.returncode, "status": status, "target_combo": tc, "combo_raw_f32": raw, "prev_rec": aux["prev_rec"], "aux": aux, "cfg": cfg}


def serving_features(cand, A, served):
    """training-build features recomputed with the producer code on the deploy copy's ACTUAL state after the anchor"""
    ts, d = cand.rolling_at(A); cfg = served["cfg"]; aux = served["aux"]
    fetch = cfg.get("symbols_fetch") or cfg["symbols_live"]; F = np.zeros(len(cand.syms), bool); F[[cand.sidx[s] for s in fetch]] = True
    ema = {s: v for s, v in aux["ema"].items()}; led = aux["ledger_tail"]
    return H.replay_anchor(A, d, ts, cand.syms, ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"], F, ema, led, cfg["params"], cfg, f"{cand.root}/work", holes=None, cols="members")


def check_anchor(cand, A, served, a, king_booster, M10):
    E = cand.E; r = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "named": {}}
    xz_in_base, xz = NL.prod_funcs(); os.makedirs(f"{cand.root}/work", exist_ok=True)
    pr = served["prev_rec"]; m = np.array(pr["members"], int)
    r["members"] = bool(np.array_equal(np.sort(m), np.sort(E[f"m_{A}"].astype(int))))
    S = serving_features(cand, A, served)
    for k, dt, sk in (("X78", np.float32, "king_X78"), ("X82", np.float16, "X82"), ("X89", np.float32, "X89")): r[k] = r["members"] and bits_eq(S[sk], E[f"{k}_{A}"], dt)
    pk = king_booster.predict(S["king_X78"]) if r["members"] else None
    r["king_pred_vs_oof"] = r["members"] and bits_eq(pk, E[f"king_oof_{A}"], np.float64)
    for k, ek in (("king", "KZ"), ("rev24", "Z24"), ("fund", "ZFD")): r[f"legz_{k}"] = r["members"] and bits_eq(np.array(pr["legz"][k]), np.nan_to_num(E[f"{ek}_{A}"]), np.float64)
    if r["members"] and not r["legz_fund"]:          # R2 attribution: base restricted to the 829-name axis
        axis_base = {s: v for s, v in _fresh_base(served["aux"], A).items() if s in cand.sidx}
        fz = xz_in_base(S["fe_v"], [cand.syms[j] for j in m], axis_base)
        r["named"]["R2_fund_base_offaxis"] = {"offaxis_names": sorted(set(_fresh_base(served["aux"], A)) - set(axis_base)), "axis_base_recompute_bitwise": bits_eq(np.nan_to_num(fz), np.nan_to_num(E[f"ZFD_{A}"]), np.float64)}
    if r["members"]:
        X171 = np.concatenate([S["X82"].astype(np.float32), S["X89"]], 1)
        xz_in = np.nan_to_num(np.clip((X171 - M10["mu"]) / M10["sd_"], -5, 5)); from scipy.special import erf
        g = lambda x: 0.5 * x * (1 + erf(x / np.sqrt(2))); h = g(xz_in @ M10["w0"].T + M10["b0"]); h = g(h @ M10["w1"].T + M10["b1"]); f10 = (h @ M10["w2"].T + M10["b2"]).squeeze(-1)
        go = E[f"f10_oof_{A}"]; r["f10_numpy_vs_gpu"] = {"max_abs": float(np.abs(f10.astype(np.float64) - go).max()), "rank_mismatch": int((np.argsort(np.argsort(f10)) != np.argsort(np.argsort(go))).sum())}
    wl = E[f"WL_{A}"]; wm = np.array([wl[0], 0.0, wl[2]]); wm = wm / wm.sum()
    r["seats_w3_masked"] = [round(float(x), 6) for x in wm] == served["target_combo"]["w3_masked"]
    r["publish_served"] = bool(served["status"].get("ok")); r["publish_eval"] = bool(E[f"trade_mask_{A}"]); r["publish_equal"] = r["publish_served"] == r["publish_eval"]
    if r["publish_served"] and r["publish_eval"]:
        er = E[f"raw_{A}"].astype(np.float32).astype(np.float64)       # weights_combo stores combo_raw as float32 (combo_stage L376)
        r["combo_raw_f32_vs_eval"] = bits_eq(served["combo_raw_f32"], np.where(np.abs(er) > 1e-9, er, 0.0), np.float64)
        if not r["combo_raw_f32_vs_eval"] and r["members"]:          # R4 / R2 attribution with combo_target.step on the served inputs
            import combo_target as CT
            CT.ROOT = __import__("pathlib").Path(f"{cand.root}/ctroot"); os.makedirs(f"{cand.root}/ctroot/vendor_live/fea171", exist_ok=True)
            shutil.copy2(f"{cand.ws}/fea171/combo_stage.py", f"{cand.root}/ctroot/vendor_live/fea171/combo_stage.py")
            led = served["aux"]["ledger_tail"]
            rn8 = np.array([(float(led[cand.syms[j]][-1][1]) * (8.0 / (float(led[cand.syms[j]][-1][2]) or 8.0))) if led.get(cand.syms[j]) else np.nan for j in m])
            qv = np.expm1(np.clip(S["qvm"], 0, 30)) * 48; legal = np.array([s in set(served["cfg"]["symbols_live"]) for s in cand.syms])
            o = CT.step(np.array(pr["legz"]["king"]), f10, np.array(pr["legz"]["fund"]), wl, rn8, m, qv, legal, served["cfg"]["params"], E[f"kc_prev_{A}"], E[f"fc_prev_{A}"], "scaled_diagnostic")
            r["named"]["step_on_served_inputs_vs_served_raw"] = bits_eq(np.where(np.abs(o["raw"]) > 1e-9, o["raw"], 0).astype(np.float32).astype(np.float64), served["combo_raw_f32"], np.float64) if o["raw"] is not None else None
    return r


def _fresh_base(aux, A):
    led = aux["ledger_tail"]; ema = aux["ema"]
    return {s: float(ema[s]["acc"]) for s in aux["base_syms"] if led.get(s) and s in ema and A - led[s][-1][0] <= 43200}


def run_chain(a, tag, f10_file, n, fetchlist=True, reseed=True, zero_state=False):
    import lightgbm as lgb
    root = f"{a.out}/{tag}"; cand = Candidate(a, root, f10_file, fetchlist, reseed, zero_state); A0 = a.start; cand.build(A0)
    kb = lgb.Booster(model_file=a.king); M10 = np.load(f10_file); out = []
    for k in range(1, n + 1):
        A = A0 + 14400 * k; served = cand.step(A); r = check_anchor(cand, A, served, a, kb, M10); r["combo_rc"] = served["rc"]; out.append(r)
        print(tag, json.dumps({kk: vv for kk, vv in r.items() if kk not in ("named",)})[:700], flush=True)
        if zero_state: break
    return out


def unexplained(r):
    keys = ["members", "X78", "X82", "X89", "king_pred_vs_oof", "legz_king", "legz_rev24", "seats_w3_masked", "publish_equal"]
    bad = [k for k in keys if not r.get(k)]
    if "f10_numpy_vs_gpu" not in r or r["f10_numpy_vs_gpu"]["max_abs"] > F10_NUMERICS_TOL: bad.append("f10_scores")
    if not r.get("legz_fund") and not r.get("named", {}).get("R2_fund_base_offaxis", {}).get("axis_base_recompute_bitwise"): bad.append("legz_fund")
    if r.get("publish_served") and r.get("publish_eval") and not r.get("combo_raw_f32_vs_eval") and not r.get("named", {}).get("step_on_served_inputs_vs_served_raw"): bad.append("combo_raw")
    return bad


def main():
    a = parse(); os.makedirs(a.out, exist_ok=True)
    man = json.load(open(a.manifest))
    inputs = {k: {"path": getattr(a, k.replace("-", "_")), "sha256": sha(getattr(a, k.replace("-", "_")))} for k in ("king", "f10", "manifest", "eval", "replay", "added", "x0918r", "holes", "producer", "control-f10")}
    print("INPUTS", json.dumps({k: v["sha256"][:16] for k, v in inputs.items()}), "start", a.start, "n", a.n, flush=True)
    assert inputs["producer"]["sha256"] == PATCHED_SHA, "producer file is not the reviewed patch"
    dep = man["deploy"]; assert dep["slow2026.txt"]["sha256"] == inputs["king"]["sha256"] and dep["f10_live_s42_np.npz"]["sha256"] == inputs["f10"]["sha256"], "package files != manifest"
    rec = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "inputs": inputs, "start": a.start, "n": a.n}
    base = run_chain(a, "baseline", a.f10, a.n); rec["baseline"] = base
    rec["baseline_unexplained"] = {r["anchor"]: unexplained(r) for r in base}
    hold = run_chain(a, "hold_zero_state", a.f10, 1, zero_state=True)
    rec["hold_anchor"] = {"served_publish": hold[0]["publish_served"], "served_reason": None}
    # evaluation side for the zero-state start: combo_target.step with the evaluation inputs and zero kc/fc
    import combo_target as CT
    CT.ROOT = __import__("pathlib").Path(f"{a.out}/hold_zero_state/ctroot"); os.makedirs(f"{a.out}/hold_zero_state/ctroot/vendor_live/fea171", exist_ok=True)
    shutil.copy2(f"{WS}/fea171/combo_stage.py", f"{a.out}/hold_zero_state/ctroot/vendor_live/fea171/combo_stage.py")
    E = np.load(a.eval, allow_pickle=True); A1 = a.start + 14400; mm = E[f"m_{A1}"].astype(int); cfg = json.load(open(f"{WS}/shadow_bundle/config.json"))
    o = CT.step(E[f"KZ_{A1}"], E[f"f10_oof_{A1}"], E[f"ZFD_{A1}"], E[f"WL_{A1}"], E[f"RN8_{A1}"], mm, E[f"QV_{A1}"], E[f"book_legal_{A1}"], cfg["params"],
                np.zeros(len(E["symbols"])), np.zeros(len(E["symbols"])), "scaled_diagnostic")
    rec["hold_anchor"].update({"eval_accepted": bool(o["accepted"]), "eval_reason": o["reason"], "both_hold": (not hold[0]["publish_served"]) and (not o["accepted"])})
    ctl = {}
    for tag, kw in (("control_f10_other_seed", dict(f10_file=a.control_f10)), ("control_no_fetchlist", dict(f10_file=a.f10, fetchlist=False)), ("control_no_reseed", dict(f10_file=a.f10, reseed=False))):
        rr = run_chain(a, tag, kw.pop("f10_file"), min(2, a.n), **kw); ctl[tag] = {"results": rr, "unexplained": {r["anchor"]: unexplained(r) for r in rr}, "RED": any(unexplained(r) for r in rr)}
    rec["controls"] = ctl
    ok = all(not v for v in rec["baseline_unexplained"].values()) and rec["hold_anchor"]["both_hold"] and all(v["RED"] for v in ctl.values())
    rec["VERDICT"] = "ACCEPT" if ok else "REJECT"
    json.dump(rec, open(f"{a.out}/CANDIDATE_ACCEPTANCE.json", "w"), indent=1, default=str)
    print(f"CANDIDATE_ACCEPTANCE VERDICT={rec['VERDICT']} baseline_unexplained={rec['baseline_unexplained']} hold={rec['hold_anchor']['both_hold']} "
          f"controls_red={ {k: v['RED'] for k, v in ctl.items()} }", flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
