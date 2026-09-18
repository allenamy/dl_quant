#!/usr/bin/env python3
"""FP3 P-B — SAME-CODE continuous replay of the production book (2026-09-18). Runs the production producer (`shadow_loop_v3.run_anchor`, byte-identical
copy) and the production combo stage (`combo_stage.py`, byte-identical, as a subprocess exactly like the daemon) anchor by anchor in a sandbox HOME on
pod2, with ONE injection: the venue `Fetcher` is replaced by `HistFetcher`, which answers the three endpoints from the research 5m cache (bitwise
identical to the producer's own panel on the overlap — receipt PA_PANEL_IDENTITY), the producer's own funding ledger (bundle seed ∪ snapshot ledger
tail) and a settlement-derived TRADING list. The state starts from the producer bundle's own bootstrap (offline trajectory weights at 08-30 20Z,
funding ledger seed, EMA state, 40-day cache tail, full leg-returns history) and is then carried forward BY THE REPLAY ITSELF. Per anchor the replayed
king target and combo target are compared with the archived production files (target_live_king/<A>.json, target_live/<A>.json) name by name.
usage: preplay_driver.py <sandbox_root> <anchor_start> <anchor_end> [--h-from-archive]
env WIDE_SHADOW_HOME/WIDE_SHADOW_BUNDLE are set here BEFORE importing the producer module; HOME is set for combo_stage."""
import os, sys, json, time, shutil, subprocess, hashlib, collections
import numpy as np
SB = os.path.abspath(sys.argv[1]); A0 = int(sys.argv[2]); A1 = int(sys.argv[3]); H_ARCH = "--h-from-archive" in sys.argv; ONE_STEP = "--one-step" in sys.argv; EMA_BUNDLE = "--ema-from-bundle" in sys.argv
SNAP_INIT = int(sys.argv[sys.argv.index("--init-from-snapshot") + 1]) if "--init-from-snapshot" in sys.argv else None   # exact production state (rolling/aux/leg_returns) of anchor A as the start
PRE = "/workspace/fp2_2026-09/preplay"; PROD = f"{PRE}/producer"; ARCH = f"{PRE}/archive"; CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"; PY = "/workspace/venv/bin/python"
WS = f"{SB}/wide_shadow"; os.makedirs(f"{WS}/state", exist_ok=True)
os.environ["WIDE_SHADOW_HOME"] = WS; os.environ["WIDE_SHADOW_BUNDLE"] = f"{PROD}/shadow_bundle"; os.environ["HOME"] = SB
if not os.path.isdir(f"{WS}/fea171"): shutil.copytree(f"{PROD}/fea171", f"{WS}/fea171", ignore=shutil.ignore_patterns("mini", "state_H_*", "__pycache__"))
if not os.path.exists(f"{WS}/shadow_bundle"): os.symlink(f"{PROD}/shadow_bundle", f"{WS}/shadow_bundle")
os.makedirs(f"{WS}/venv/bin", exist_ok=True)
if not os.path.exists(f"{WS}/venv/bin/python"): os.symlink(PY, f"{WS}/venv/bin/python")
os.makedirs(f"{SB}/dl_quant_live", exist_ok=True)
if not os.path.isdir(f"{SB}/dl_quant_live/live") and os.path.isdir(f"{PROD}/dl_quant_live/live"): shutil.copytree(f"{PROD}/dl_quant_live/live", f"{SB}/dl_quant_live/live", ignore=shutil.ignore_patterns("__pycache__"))
os.makedirs(f"{SB}/dl_quant_live/live", exist_ok=True)
open(f"{SB}/dl_quant_live/live/telegram_notify.py", "w").write("# PREPLAY STUB: never sends\nimport json, os, time\nclass TelegramNotifier:\n    def __init__(self, token=None, chat_id=None): pass\n    def alarm(self, sev, msg):\n        open(os.path.join(os.path.dirname(__file__), 'STUB_PAGES.log'), 'a').write(json.dumps({'utc': time.strftime('%FT%TZ', time.gmtime()), 'sev': sev, 'msg': msg}) + '\\n'); return {'status': 'STUBBED'}\n    def send(self, *a, **k): return self.alarm('INFO', str(a))\n")
open(f"{SB}/dl_quant_live/.env", "w").write('TELEGRAM_BOT_TOKEN="stub"\nTELEGRAM_CHAT_ID="0"\n')
for f in ("state_H_kc_1788120000.npz", "state_H_fc_1788120000.npz", "state_H_f10_1788120000.npz"):   # combo's recursive state at the start anchor (archived production files)
    if os.path.exists(f"{ARCH}/{f}") and not os.path.exists(f"{WS}/fea171/{f}"): shutil.copy2(f"{ARCH}/{f}", f"{WS}/fea171/{f}")
TIMELINE = "--timeline" in sys.argv     # pin producer code versions and state interventions to the anchors at which production had them
# production version timeline (Mac backups, sha8 / mtime): shadow_loop_v3 db326162 (pre-M1) through 2026-09-04 00Z, e9c98374 (M1) from 09-04 04Z;
# combo_stage ff5de5d8 (no FTRIM) through 09-02 08Z, b5c698f9 (FTRIM) 09-02 12Z … 09-17 12Z, 3520d363 from 09-17 16Z; seat seeding (leg_returns replaced) 09-05 12:20Z ⇒ from the 16Z anchor
SHADOW_VERSIONS = [(1788566400, f"{PROD}/shadow_loop_v3.py.pre_m1_20260904_backup.py"), (10**12, f"{PROD}/shadow_loop_v3.py")]   # the loader needs a .py suffix: a byte-identical copy of the backup
COMBO_VERSIONS = [(1788336000, f"{PROD}/combo_stage.py.pre_ftrim_20260902_backup"), (1789646400, f"{PROD}/combo_stage.py.pre_fp2-6b_20260917T1259Z_b5c698f9"), (10**12, f"{PROD}/fea171/combo_stage.py")]
SEAT_SEED_ANCHOR = 1788624000
def version_for(table, A): return next(path for until, path in table if A <= until)
import importlib.util
_mods = {}
def shadow_module(path):
    if path not in _mods:
        spec = importlib.util.spec_from_file_location("shadow_" + hashlib.sha256(path.encode()).hexdigest()[:8], path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); _mods[path] = m
    return _mods[path]
sys.path.insert(0, PROD); import shadow_loop_v3 as SL
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.0f}s]", *a, flush=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
# ── data sources ──
Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); CD = Z["data"]; CSYM = [str(s) for s in Z["symbols"]]; log("cache", CD.shape, "→", time.strftime("%FT%TZ", time.gmtime(int(CTS[-1]))))
# the research cache ends 2026-09-01; the producer's own panel snapshots (bitwise-identical on the overlap, receipt PA_PANEL_IDENTITY) extend it to the present:
# append the snapshot rows after the cache's last timestamp (live symbols only; the snapshot has NaN elsewhere, exactly as production)
SNAP_P = os.environ.get("PREPLAY_SNAPSHOT", f"{PRE}/archive/rolling_snapshot_latest.npz")
if os.path.exists(SNAP_P):
    S_ = np.load(SNAP_P, allow_pickle=True); sts = S_["ts"].astype(np.int64); sd = S_["data"]; ext = sts > CTS[-1]
    if ext.any(): CTS = np.concatenate([CTS, sts[ext]]); CD = np.concatenate([CD, sd[ext].astype(CD.dtype)]); log("cache extended with producer snapshot", os.path.basename(SNAP_P), "→", time.strftime("%FT%TZ", time.gmtime(int(CTS[-1]))), "rows added", int(ext.sum()))
LED = collections.defaultdict(dict)
for src in (f"{PROD}/shadow_bundle/funding_ledger_seed.json", f"{ARCH}/snap/1789646400/aux.json", f"{ARCH}/snap/1789689600/aux.json"):
    d = json.load(open(src)); tail = d.get("ledger_tail", d) if isinstance(d, dict) else d
    for s, rows in tail.items():
        for r in rows: LED[s][int(r[0])] = float(r[1])
LEDS = {s: sorted(v.items()) for s, v in LED.items()}; log("funding source names", len(LEDS), "rows", sum(len(v) for v in LEDS.values()))
class HistFetcher:
    def __init__(self): self.weight_used = 0; self.anchor = None; self.calls = collections.Counter()
    def get(self, path, params, weight):
        self.calls[path] += 1; self.weight_used += weight
        if path == "/fapi/v1/klines": return []                                   # 5m: pre-filled from the cache; 1h (tail score): 'unknown' path
        if path == "/fapi/v1/exchangeInfo":
            A = self.anchor; trading = [s for s, rows in LEDS.items() if any(A - 86400 < ft <= A for ft, _ in rows)]
            return {"symbols": [{"symbol": s, "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"} for s in trading]}
        if path == "/fapi/v1/fundingRate":
            s = params["symbol"]; st_, en = int(params["startTime"]), int(params["endTime"]); lim = int(params.get("limit", 100))
            rows = [{"fundingTime": ft * 1000, "fundingRate": str(rate)} for ft, rate in LEDS.get(s, []) if st_ <= ft * 1000 <= en]
            return rows[:lim]
        return {"_err": f"historical fetcher: unsupported {path}"}
def prefill(st, A):
    step = 300
    if A > int(st.cts[-1]):
        new_ts = np.arange(int(st.cts[-1]) + step, A + 1, step, dtype=np.int64); st.cts = np.concatenate([st.cts, new_ts]); st.cd = np.concatenate([st.cd, np.full((len(new_ts), st.NW, 7), np.nan, np.float16)])
    if len(st.cts) > SL.CACHE_ROWS: st.cts = st.cts[-SL.CACHE_ROWS:]; st.cd = st.cd[-SL.CACHE_ROWS:]
    lo = int(st.cts[0]); ci0 = np.searchsorted(CTS, lo); ci1 = np.searchsorted(CTS, A, side="right"); sub_ts = CTS[ci0:ci1]
    pos = {int(t): i for i, t in enumerate(st.cts)}; rows_c = np.array([pos.get(int(t), -1) for t in sub_ts]); okr = rows_c >= 0
    live_j = np.array([st.sym_idx[s] for s in st.live if s in st.sym_idx]); cache_j = np.array([CSYM.index(st.syms[j]) for j in live_j])
    blk = CD[ci0:ci1][:, cache_j, :]; tgt = st.cd[rows_c[okr]][:, live_j, :]
    nanmask = np.isnan(tgt[:, :, 3].astype(np.float32)); src = blk[okr]
    tgt[nanmask] = src[nanmask]; st.cd[np.ix_(rows_c[okr], live_j)] = tgt      # fill only rows that are NaN (the producer's own rule); float16 bytes unchanged
    return int(nanmask.sum())
def wdict(p):
    d = json.load(open(p)); return {k: float(v) for k, v in d["weights"].items()}, d
def cmp(a, b):
    names = set(a) | set(b); dif = {n: abs(a.get(n, 0.0) - b.get(n, 0.0)) for n in names}; s = sum(abs(v) for v in a.values())
    return {"n_arch": len(a), "n_rep": len(b), "only_arch": sum(1 for n in names if n in a and n not in b), "only_rep": sum(1 for n in names if n in b and n not in a), "max_abs_dw": max(dif.values()) if dif else 0.0, "l1_rel": (sum(dif.values()) / s) if s else None, "n_diff_gt_1e-6": sum(1 for v in dif.values() if v > 1e-6)}
if SNAP_INIT:
    sd_ = f"{PRE}/archive/snap/{SNAP_INIT}"
    for f_ in ("rolling.npz", "aux.json", "leg_returns_live.json"): shutil.copy2(f"{sd_}/{f_}", f"{WS}/state/{f_}")
    for k_ in ("kc", "fc", "f10"):
        sp_ = f"{ARCH}/state_H/state_H_{k_}_{SNAP_INIT}.npz"
        if os.path.exists(sp_): shutil.copy2(sp_, f"{WS}/fea171/state_H_{k_}_{SNAP_INIT}.npz")
    print("init from production snapshot", SNAP_INIT, flush=True)
cfg, booster, man = SL.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")               # as main() does
# production's LIVE leg-return extras as of the start anchor: the pre-seed backup (written 09-05 12Z) minus the entries appended after the start anchor
A_START = max(int(k) for k in json.load(open(f"{PROD}/shadow_bundle/parity_signals_aug.json")))
bk = f"{ARCH}/leg_returns_live.json.pre_seatseed_v3_20260905"; BK_LAST = 1788609600
if os.path.exists(bk) and not os.path.exists(f"{WS}/state/leg_returns_live.json") and not SNAP_INIT:
    ex = json.load(open(bk)); k = (BK_LAST - A_START) // 14400; ex = {leg: v[:-k] if k > 0 else v for leg, v in ex.items()}
    json.dump(ex, open(f"{WS}/state/leg_returns_live.json", "w")); log("leg_returns extras from production backup: dropped", k, "entries after", time.strftime("%FT%TZ", time.gmtime(A_START)), "kept", len(ex["king"]))
st = SL.ShadowState(cfg); log("bootstrap: last_anchor", time.strftime("%FT%TZ", time.gmtime(st.last_anchor)), "H nz", int((np.abs(st.H) > 1e-9).sum()), "LR len", len(st.LR["king"]), "ledger names", len(st.ledger), "cache rows", len(st.cts), "→", time.strftime("%FT%TZ", time.gmtime(int(st.cts[-1]))))
# (a) production never holds bars for symbols outside its live universe: NaN them out of the bootstrap tail (the tail came from the research cache with all 829 names)
if not SNAP_INIT: st.cd[:, ~st.live_mask, :] = np.nan
# (b) CAUSAL funding state at the start anchor: the bundle seed reaches 09-01 02Z (after the start); rebuild ledger + EMA from settlements ≤ start with the producer's own formulas
A0s = st.last_anchor; led_new = {}; ema_new = {}; ALLOWED = [1.0, 2.0, 4.0, 6.0, 8.0]
for s_, rows in LEDS.items():
    led = []; est = None
    for ft, rate in rows:
        if ft > A0s: break
        iv = (ft - led[-1][0]) / 3600.0 if led else 8.0; iv = float(min(ALLOWED, key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0)))); led.append([ft, rate, iv]); rn = rate * (8.0 / iv)
        if est is None: est = {"acc": rn, "last_ts": ft}
        else: a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0)); est = {"acc": est["acc"] + a * (rn - est["acc"]), "last_ts": ft}
    if led: led_new[s_] = led[-400:]; ema_new[s_] = est
if not SNAP_INIT: st.ledger = led_new; st.ema = (json.load(open(f"{PROD}/shadow_bundle/fund_ema_v1_state.json")) if EMA_BUNDLE else ema_new)
if not SNAP_INIT: log("ema source", "bundle fund_ema_v1_state.json (production lineage, built 09-01)" if EMA_BUNDLE else "causal rebuild", "| causal funding state at", time.strftime("%FT%TZ", time.gmtime(A0s)), "names", len(led_new), "latest settlement", time.strftime("%FT%TZ", time.gmtime(max(v[-1][0] for v in led_new.values()))))
if H_ARCH and not SNAP_INIT and os.path.exists(f"{ARCH}/weights/{st.last_anchor}.npz"):
    z = np.load(f"{ARCH}/weights/{st.last_anchor}.npz"); st.H = np.zeros(st.NW); st.H[z["idx"].astype(int)] = z["val"].astype(float); log("H overridden from archived weights", st.last_anchor, int((np.abs(st.H) > 1e-9).sum()))
PROD_SIG = {}
if os.path.exists(f"{ARCH}/shadow_log_prod.jsonl"):
    for l in open(f"{ARCH}/shadow_log_prod.jsonl"):
        r = json.loads(l)
        if r.get("e") == "signal": PROD_SIG[int(r["anchor_ts"])] = r
def sig_row(A):
    rows = [json.loads(l) for l in open(f"{WS}/shadow_log.jsonl") if l.strip()] if os.path.exists(f"{WS}/shadow_log.jsonl") else []
    rows = [r for r in rows if r.get("e") == "signal" and int(r.get("anchor_ts", 0)) == A]; return rows[-1] if rows else None
fx = HistFetcher(); out = []; recs_p = f"{SB}/PREPLAY_anchors.jsonl"; open(recs_p, "w").close()
for A in range(A0, A1 + 1, 14400):
    SLA = SL
    if TIMELINE:
        sp_ = version_for(SHADOW_VERSIONS, A); SLA = shadow_module(sp_) if sp_ != f"{PROD}/shadow_loop_v3.py" else SL
        cp_ = version_for(COMBO_VERSIONS, A); dst_ = f"{WS}/fea171/combo_stage.py"
        if hashlib.sha256(open(cp_, "rb").read()).hexdigest() != hashlib.sha256(open(dst_, "rb").read()).hexdigest(): shutil.copy2(cp_, dst_); log("combo_stage version →", os.path.basename(cp_), "for", time.strftime("%m-%d %HZ", time.gmtime(A)))
        if A == SEAT_SEED_ANCHOR and os.path.exists(f"{ARCH}/leg_returns_live.json"):
            seeded = json.load(open(f"{ARCH}/leg_returns_live.json")); k = (1789689600 - 1788609600) // 14400; lr0 = np.load(f"{PROD}/shadow_bundle/leg_returns.npz")
            for leg in ("king", "rev24", "fund"): st.LR[leg] = list(lr0[leg]) + list(map(float, seeded[leg][:-k] if k > 0 else seeded[leg]))
            log("seat seeding applied (production 09-05 12:20Z): LR extras replaced by the seeded series (", len(seeded["king"]) - k, "entries)")
    t1 = time.time(); fx.anchor = A; nfill = prefill(st, A); fx.calls.clear()
    if ONE_STEP:                                                              # one-step mode: producer holdings AND combo recursive state re-seeded from the ARCHIVES every anchor (no compounding)
        wp = f"{ARCH}/weights/{A - 14400}.npz"
        if os.path.exists(wp): z = np.load(wp); st.H = np.zeros(st.NW); st.H[z["idx"].astype(int)] = z["val"].astype(float)
        else: log("one-step: no archived weights for", A - 14400)
        for k_ in ("kc", "fc", "f10"):
            sp_ = f"{ARCH}/state_H/state_H_{k_}_{A - 14400}.npz"
            if os.path.exists(sp_): shutil.copy2(sp_, f"{WS}/fea171/state_H_{k_}_{A - 14400}.npz")
    SLA.run_anchor(st, fx, cfg, booster, A); tp = time.time() - t1; rec_ver = {"shadow": os.path.basename(version_for(SHADOW_VERSIONS, A)) if TIMELINE else "current", "combo": os.path.basename(version_for(COMBO_VERSIONS, A)) if TIMELINE else "current"}
    rec = {"anchor_ts": A, "utc": time.strftime("%m-%d %HZ", time.gmtime(A)), "prefilled_cells": nfill, "producer_s": round(tp, 1), "fetch_calls": dict(fx.calls), "last_anchor_after": st.last_anchor, "versions": rec_ver}
    sr = sig_row(A); pr = PROD_SIG.get(A)
    if sr: rec["signal"] = {k: sr.get(k) for k in ("w3", "sel", "members", "base_n", "fund_base_n", "fund_updates", "turnover", "gross_pos", "forced_exit_n", "coverage")}
    if pr: rec["signal_prod"] = {k: pr.get(k) for k in ("w3", "sel", "members", "base_n", "fund_base_n", "fund_updates", "turnover", "gross_pos", "forced_exit_n", "coverage")}
    if sr and pr and sr.get("w3") and pr.get("w3"): rec["w3_max_abs_diff"] = max(abs(float(a) - float(b)) for a, b in zip(sr["w3"], pr["w3"]))
    wa_ = f"{ARCH}/weights/{A}.npz"
    if st.prev_rec and st.prev_rec.get("anchor_ts") == A and os.path.exists(wa_):
        ma_ = set(np.load(wa_)["members"].astype(int).tolist()); mr_ = set(st.prev_rec["members"]); rec["members_symdiff_vs_archive"] = len(ma_ ^ mr_)
    kp = f"{WS}/state/target_live/{A}.json"
    if os.path.exists(kp):
        rk, dk = wdict(kp); rec["king_gross"] = dk["gross_norm"]; rec["king_n"] = dk["n_names"]
        ak = f"{ARCH}/target_live_king/{A}.json" if os.path.exists(f"{ARCH}/target_live_king/{A}.json") else (f"{ARCH}/target_live/{A}.json" if os.path.exists(f"{ARCH}/target_live/{A}.json") and "shadow_loop" in json.load(open(f"{ARCH}/target_live/{A}.json")).get("producer", "") else None)
        if ak: aa, _ = wdict(ak); rec["king_vs_archive"] = cmp(aa, rk); rec["king_archive_file"] = os.path.basename(os.path.dirname(ak)) + "/" + os.path.basename(ak)
        t2 = time.time(); env = dict(os.environ, HOME=SB, COMBO_LIVE="1", COMBO_LIVE_DIR=f"{WS}/state/target_live_PREPLAY", PATH=os.environ["PATH"])
        r = subprocess.run([PY, "-u", "combo_stage.py"], cwd=f"{WS}/fea171", env=env, capture_output=True, text=True); rec["combo_rc"] = r.returncode; rec["combo_s"] = round(time.time() - t2, 1); rec["combo_tail"] = r.stdout.strip().splitlines()[-2:] if r.stdout else r.stderr[-300:]
        cp = f"{WS}/state/target_live_PREPLAY/{A}.json"; ac = f"{ARCH}/target_live/{A}.json"
        if os.path.exists(cp) and os.path.exists(ac):
            rc_, dc = wdict(cp); ra, da = wdict(ac); rec["combo_gross"] = dc["gross_norm"]; rec["archive_producer"] = da.get("producer", "")[:20]
            if "combo" in da.get("producer", ""): rec["combo_vs_archive"] = cmp(ra, rc_)
            else: rec["combo_vs_archive"] = "archived target is king form (combo did not run in production)"
    else: rec["producer"] = "SKIPPED (no target written)"
    out.append(rec); open(recs_p, "a").write(json.dumps(rec) + "\n")
    log(rec["utc"], f"prod {tp:.0f}s combo {rec.get('combo_s')}s rc {rec.get('combo_rc')} | king L1 {(rec.get('king_vs_archive') or {}).get('l1_rel')} max {(rec.get('king_vs_archive') or {}).get('max_abs_dw')} | combo {str((rec.get('combo_vs_archive') or {}).get('l1_rel') if isinstance(rec.get('combo_vs_archive'), dict) else rec.get('combo_vs_archive'))[:60]} | w3 rep {(rec.get('signal') or {}).get('w3')} prod {(rec.get('signal_prod') or {}).get('w3')} | sel {(rec.get('signal') or {}).get('sel')}/{(rec.get('signal_prod') or {}).get('sel')} members {(rec.get('signal') or {}).get('members')}/{(rec.get('signal_prod') or {}).get('members')} base_n {(rec.get('signal') or {}).get('base_n')}/{(rec.get('signal_prod') or {}).get('base_n')} fund_updates {(rec.get('signal') or {}).get('fund_updates')}/{(rec.get('signal_prod') or {}).get('fund_updates')}")
summary = {"device": "preplay_driver.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "sandbox": SB, "anchors": [A0, A1, len(out)], "h_from_archive": H_ARCH, "one_step": ONE_STEP, "ema_from_bundle": EMA_BUNDLE, "init_from_snapshot": SNAP_INIT, "timeline": TIMELINE,
           "producer_sha256": {"shadow_loop_v3.py": sha(f"{PROD}/shadow_loop_v3.py"), "combo_stage.py": sha(f"{WS}/fea171/combo_stage.py"), "f10_live_s42_np.npz": sha(f"{WS}/fea171/f10_live_s42_np.npz"), "slow2026.txt": sha(f"{PROD}/shadow_bundle/slow2026.txt")}, "cache_sha256": sha(CACHE),
           "king_max_abs_dw": max((r.get("king_vs_archive") or {}).get("max_abs_dw", 0) for r in out), "combo_max_abs_dw": max(((r.get("combo_vs_archive") or {}) if isinstance(r.get("combo_vs_archive"), dict) else {}).get("max_abs_dw", 0) for r in out),
           "per_anchor": out}
json.dump(summary, open(f"{SB}/PREPLAY_SUMMARY.json", "w"), indent=1); log("PREPLAY_DONE", {k: summary[k] for k in ("anchors", "king_max_abs_dw", "combo_max_abs_dw")})
