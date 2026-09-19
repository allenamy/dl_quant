#!/usr/bin/env python3
"""Phase-1 parity driver (PREREG_producer_parity_replay_2026-09-12): rebuild the producer state as of anchor A from the
producer's own recorded state, run the generated device's run_anchor(A) offline, and compare the king-stage outputs
with the recorded live files. READ-ONLY on ~/wide_shadow; all writes go to REPLAY_HOME.
Usage: python3 replay_driver.py <anchor_ts> [<anchor_ts> ...]   (each anchor is replayed independently from recorded state)"""
import os, sys, json, glob, math, hashlib, shutil, importlib, time
import numpy as np
WS = os.path.expanduser("~/wide_shadow"); HERE = os.path.dirname(os.path.abspath(__file__))
RH = os.path.join(os.path.dirname(HERE), "replay_home"); os.makedirs(RH + "/state", exist_ok=True)
os.environ["WIDE_SHADOW_HOME"] = RH; os.environ["WIDE_SHADOW_BUNDLE"] = f"{WS}/shadow_bundle"   # bundle read-only (load_bundle only reads)
sys.path.insert(0, HERE); dev = importlib.import_module("shadow_loop_v3_replay")
assert dev.STATE_DIR == RH + "/state" and dev.BUNDLE == f"{WS}/shadow_bundle", (dev.STATE_DIR, dev.BUNDLE)
dev.ShadowState.save = lambda self: None          # in-memory only; the driver saves what the gate needs

def jl(p):
    out = []
    for l in open(p, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
def sha_file(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def ema_state_before(anchor, ema_now, ledger_full):
    """Invert the producer's EMA recursion (run_anchor step 4) from the CURRENT state back to the state the live
    process held when run_anchor(anchor) started = after every settlement with ft <= anchor-14400.
    est_new = est + a*(rn-est), a = 1-0.5**(max(ft-last_ts,1)/(3*86400)), rn = rate*(8/iv)  =>  est = (est_new - a*rn)/(1-a)."""
    cut = anchor - 14400; out = {}
    for s, est in ema_now.items():
        rows = ledger_full.get(s, [])
        later = [r for r in rows if int(r[0]) > cut]          # rows applied AFTER the state we want
        acc = float(est["acc"]); last_ts = int(est["last_ts"])
        ok = True
        for r in reversed(later):
            ft, rate, iv = int(r[0]), float(r[1]), float(r[2])
            if ft != last_ts:                                   # ledger/EMA mismatch: cannot invert exactly
                ok = False; break
            rn = rate * (8.0 / iv)
            prev_rows = [q for q in rows if int(q[0]) < ft]
            if not prev_rows:                                   # this row created the EMA (est was None before it)
                acc = None; last_ts = None; break
            prev_ts = int(prev_rows[-1][0])
            a = 1 - 0.5 ** (max(ft - prev_ts, 1) / (3 * 86400.0))
            acc = (acc - a * rn) / (1 - a); last_ts = prev_ts
        if not ok: out[s] = ("MISMATCH", est); continue
        out[s] = None if acc is None else {"acc": acc, "last_ts": last_ts}
    return out

def roundtrip_check(anchor, ema_before, ema_now, ledger_full):
    """Re-apply the producer's forward recursion to ema_before over rows in (anchor-14400, now] and compare with ema_now."""
    worst = 0.0; n = 0
    for s, est in ema_before.items():
        if isinstance(est, tuple): continue
        rows = [r for r in ledger_full.get(s, []) if int(r[0]) > anchor - 14400]
        e = None if est is None else dict(est)
        for r in rows:
            ft, rate, iv = int(r[0]), float(r[1]), float(r[2]); rn = rate * (8.0 / iv)
            if e is None: e = {"acc": rn, "last_ts": ft}
            else:
                a = 1 - 0.5 ** (max(ft - e["last_ts"], 1) / (3 * 86400.0)); e = {"acc": e["acc"] + a * (rn - e["acc"]), "last_ts": ft}
        if e is not None and s in ema_now:
            worst = max(worst, abs(e["acc"] - float(ema_now[s]["acc"]))); n += 1
    return worst, n

def build_state(anchor, cfg, snap):
    """snap: dict with aux, lr_extra(list per leg), rolling path, weights dir, shadow_log rows."""
    st = dev.ShadowState.__new__(dev.ShadowState)
    st.syms = cfg["symbols_panel"]; st.live = cfg["symbols_live"]; st.NW = len(st.syms)
    st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    st.live_mask = np.zeros(st.NW, bool); st.live_mask[[st.sym_idx[s] for s in st.live if s in st.sym_idx]] = True
    z = np.load(snap["rolling"], allow_pickle=True); st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    aux = snap["aux"]
    # ★★ 2026-09-19 修复(G-P2 残差的机制): 上一版写 `st.prev_close = {}` —— **把快照里带着的
    #   prev_close(450 个名)直接丢掉**。其它每一个跨锚状态(H / ledger / ema / LR / base)都从
    #   快照重建了, 唯独这一个被静默置空。
    #
    #   后果与观察到的残差签名逐条吻合:
    #     · prev_close 填的是 5m 通道的 ret5(生产者 L251 注释原文「ret5 由 prev_close 补」,
    #       消费点 L283 `pc = st.prev_close.get(s)`)⇒ 置空后每个新取窗口的首根 bar ret5 = NaN;
    #     · ret5 只进 DL 横截面特征(fea82/fea89 用全部 live 名), **不进 king**(成员窗口)
    #       ⇒ 解释「残差只在 DL 腿, kc 状态 41 锚 L∞ 0.0」;
    #     · 链式模式下 prev_close 随链推进逐步填满 ⇒ 解释「越近的锚越一致, 最新锚精确」;
    #     · 快照起步模式下窗口短、影响小 ⇒ 解释「快照起步 3/3 精确 0.0」。
    #
    #   原先 RESULT §3 记的「唯一未闭合假说 = 缓存 5m 行的事后回填」**已被证伪**:
    #   backfill_probe 三对快照各 11,472 行, cells_filled_later / cells_lost /
    #   cells_changed_finite **全为 0**(收据 receipts/BACKFILL_probe_*.json)。
    st.prev_close = {k: float(v) for k, v in (aux.get("prev_close") or {}).items()}
    # H = holdings after the previous anchor = the producer's own weights file
    st.H = np.zeros(st.NW); wf = f"{WS}/state/weights/{anchor-14400}.npz"
    assert os.path.exists(wf), f"missing weights file {wf}"
    w = np.load(wf); st.H[w["idx"].astype(np.int64)] = w["val"].astype(np.float64)
    st.last_anchor = anchor - 14400
    # ledger as of the start of run_anchor(anchor): rows with ft <= anchor-14400 (the previous anchor fetched up to its own time)
    ledger_full = {s: [list(r) for r in rows] for s, rows in aux["ledger_tail"].items()}
    st.ledger = {s: [r for r in rows if int(r[0]) <= anchor - 14400] for s, rows in ledger_full.items()}
    ema_b = ema_state_before(anchor, aux["ema"], ledger_full)
    mism = [s for s, e in ema_b.items() if isinstance(e, tuple)]
    st.ema = {s: e for s, e in ema_b.items() if e is not None and not isinstance(e, tuple)}
    for s in mism: st.ema[s] = aux["ema"][s]        # fallback: current state (flagged)
    worst, n = roundtrip_check(anchor, ema_b, aux["ema"], ledger_full)
    st.prev_rec = None                                # step 6 skipped: LR comes from the record (below)
    st.base = list(aux.get("base_syms") or st.live)
    # LR: bundle leg_returns + live extra truncated to entries appended at anchors < anchor
    lr = np.load(f"{WS}/shadow_bundle/leg_returns.npz"); extra = snap["lr_extra"]
    # LR as the producer holds it at STEP 7 of run_anchor(anchor): step 6 (skipped here) has already appended the score entry
    # for anchor-14400, so keep entries whose score row anchor_ts <= anchor-14400 and drop those appended by later anchors.
    n_after = sum(1 for r in snap["log"] if r.get("e") == "score" and int(r.get("anchor_ts", 0)) >= anchor)
    st.LR = {leg: list(lr[leg]) + list(extra[leg][: len(extra[leg]) - n_after]) for leg in ("king", "rev24", "fund")}
    diag = {"prev_close_restored": len(st.prev_close), "ema_inverted": len(ema_b), "ema_mismatch_fallback": mism, "ema_roundtrip_worst_abs": worst, "ema_roundtrip_n": n,
            "lr_dropped_entries": n_after, "lr_len_before_anchor": len(st.LR["king"]), "base_n": len(st.base),
            "cache_rows": int(len(st.cts)), "cache_last": int(st.cts[-1])}
    return st, ledger_full, diag

def compare(anchor, out_state_dir):
    rep = np.load(f"{out_state_dir}/weights/{anchor}.npz"); liv = np.load(f"{WS}/state/weights/{anchor}.npz")
    NW = 829; a = np.zeros(NW); b = np.zeros(NW)
    a[rep["idx"].astype(int)] = rep["val"].astype(np.float64); b[liv["idx"].astype(int)] = liv["val"].astype(np.float64)
    d = np.abs(a - b); linf = float(d.max()); l1 = float(d.sum())
    def _csha(z): return hashlib.sha256(z["idx"].astype(np.int32).tobytes() + z["val"].astype(np.float32).tobytes()).hexdigest()
    content_sha_equal = _csha(rep) == _csha(liv)
    ulp = int((np.abs(a - b) > 0).sum())
    rj = json.load(open(f"{out_state_dir}/target_live/{anchor}.json")); lj = json.load(open(f"{WS}/state/target_live_king/{anchor}.json"))
    rw, lw = rj["weights"], lj["weights"]; keys = set(rw) | set(lw)
    jd = max(abs(rw.get(k, 0.0) - lw.get(k, 0.0)) for k in keys) if keys else 0.0
    return {"anchor": anchor, "weights_npz_Linf": linf, "weights_npz_L1": l1, "n_nonzero_replay": int((a != 0).sum()), "n_nonzero_live": int((b != 0).sum()),
            "target_live_json_Linf": jd, "n_names_replay": rj["n_names"], "n_names_live": lj["n_names"],
            "weights_sha_equal": rj["weights_sha"] == lj["weights_sha"], "universe_sha_equal": rj["universe_sha"] == lj["universe_sha"],
            "content_sha_equal": content_sha_equal, "n_names_differing_any": ulp,
            "worst_names": sorted(((float(d[j]), dev.load_bundle.__globals__["json"] and str(j)) for j in np.argsort(-d)[:5]), reverse=True)}

import subprocess
def _write_replay_state(A, st):
    """What combo_stage reads from WS/state: aux.json (prev_rec/ledger/ema/H/base), leg_returns_live.json, rolling.npz (symlink, read-only)."""
    os.makedirs(f"{RH}/state", exist_ok=True)
    json.dump({"prev_close": {}, "H": {str(int(j)): float(st.H[j]) for j in np.where(np.abs(st.H) > 1e-9)[0]}, "last_anchor": st.last_anchor,
               "ema": st.ema, "ledger_tail": {s: r[-400:] for s, r in st.ledger.items()}, "base_syms": list(st.base), "prev_rec": st.prev_rec},
              open(f"{RH}/state/aux.json", "w"))
    lr_bundle_n = len(np.load(f"{WS}/shadow_bundle/leg_returns.npz")["king"])
    json.dump({leg: list(map(float, st.LR[leg][lr_bundle_n:][-950:])) for leg in st.LR}, open(f"{RH}/state/leg_returns_live.json", "w"))
    rp = f"{RH}/state/rolling.npz"
    if not os.path.islink(rp): 
        if os.path.exists(rp): os.remove(rp)
        os.symlink(f"{WS}/state/rolling.npz", rp)

def run_combo_stage(A, st, first):
    """Run the generated combo_stage_replay.py against the replay home; on the first anchor seed the fea171 copy and the previous
    weights/states from the LIVE files (read-only copies); afterwards the chain's own outputs are used."""
    fe = f"{RH}/fea171"; os.makedirs(fe, exist_ok=True); os.makedirs(f"{RH}/state/weights", exist_ok=True); os.makedirs(f"{RH}/state/target_live_combo", exist_ok=True)
    vp = f"{RH}/venv"
    if not os.path.islink(vp):
        if os.path.exists(vp): shutil.rmtree(vp)
        os.symlink(f"{WS}/venv", vp)                   # combo_stage spawns {WS}/venv/bin/python for the 171 pipeline (read-only interpreter)
    sb = f"{RH}/shadow_bundle"
    if not os.path.islink(sb):
        if os.path.exists(sb): shutil.rmtree(sb)
        os.symlink(f"{WS}/shadow_bundle", sb)          # read-only: combo_stage only reads config.json
    # read-only copies of every model/reference/helper file the stage may open (NOT the per-anchor state_H_* chain state, logs, pids)
    for f in os.listdir(f"{WS}/fea171"):
        src = f"{WS}/fea171/{f}"; dst = f"{fe}/{f}"
        if f.startswith("state_H_") or f.endswith((".log", ".out", ".pid", ".bak_preE0825A")) or "backup" in f or f in ("combo_stage.py", "__pycache__", "combo_live_last_anchor"): continue
        if os.path.isdir(src):
            if not os.path.exists(dst): shutil.copytree(src, dst)
        elif not os.path.exists(dst): shutil.copy2(src, dst)
    if first:
        for tag in ("f10", "kc", "fc"):
            src = f"{WS}/fea171/state_H_{tag}_{A-14400}.npz"
            if os.path.exists(src): shutil.copy2(src, f"{fe}/state_H_{tag}_{A-14400}.npz")
        if os.path.exists(f"{WS}/state/weights/{A-14400}.npz"): shutil.copy2(f"{WS}/state/weights/{A-14400}.npz", f"{RH}/state/weights/{A-14400}.npz")
    _write_replay_state(A, st)
    shutil.rmtree(f"{fe}/mini/data", ignore_errors=True)      # force the 171 feature pipeline to recompute for THIS anchor (as live did)
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~"), "WIDE_SHADOW_HOME": RH, "COMBO_LIVE": "1", "COMBO_LIVE_DIR": f"{RH}/state/target_live_combo", "REPLAY_TRUNCATE_CACHE": "1"}
    t0 = time.time(); p = subprocess.run([sys.executable, os.path.join(HERE, "combo_stage_replay.py")], cwd=fe, env=env, capture_output=True, text=True, timeout=900)
    out = {"rc": p.returncode, "runtime_s": round(time.time() - t0, 1), "tail": p.stdout.strip().splitlines()[-3:] if p.stdout else [], "err": p.stderr.strip().splitlines()[-3:] if p.stderr else []}
    try:
        rc_ = json.load(open(f"{RH}/state/target_combo/{A}.json")); lc = json.load(open(f"{WS}/state/target_combo/{A}.json"))
        keys = set(rc_["weights"]) | set(lc["weights"]); out["target_combo_Linf"] = max(abs(rc_["weights"].get(k, 0.0) - lc["weights"].get(k, 0.0)) for k in keys)
        out["target_combo_n"] = (len(rc_["weights"]), len(lc["weights"])); out["w3m_equal"] = rc_["w3_masked"] == lc["w3_masked"]; out["ftrim_n"] = (rc_["ftrim"]["n_kc"], rc_["ftrim"]["n_fc"], lc["ftrim"]["n_kc"], lc["ftrim"]["n_fc"])
        rl = json.load(open(f"{RH}/state/target_live_combo/{A}.json")); ll = json.load(open(f"{WS}/state/target_live/{A}.json"))
        keys = set(rl["weights"]) | set(ll["weights"]); out["target_live_Linf"] = max(abs(rl["weights"].get(k, 0.0) - ll["weights"].get(k, 0.0)) for k in keys)
        out["target_live_n"] = (len(rl["weights"]), len(ll["weights"])); out["live_producer_tag"] = ll.get("producer", "")[:40]
    except Exception as e:
        out["compare_error"] = repr(e)[:200]
    return out

def build_state_from_snapshot(snapdir, cfg):
    """G-P3 forward mode: start from a producer state snapshot taken at anchor close (aux.json carries float64 H, EMA, ledger,
    base_syms, prev_rec, last_anchor; leg_returns_live.json; rolling.npz). No inversion, no float32 archive: bitwise parity is the target."""
    st = dev.ShadowState.__new__(dev.ShadowState)
    st.syms = cfg["symbols_panel"]; st.live = cfg["symbols_live"]; st.NW = len(st.syms)
    st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    st.live_mask = np.zeros(st.NW, bool); st.live_mask[[st.sym_idx[s] for s in st.live if s in st.sym_idx]] = True
    z = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)            # the CURRENT cache (rows for the next anchor are needed); rows <= snapshot anchor are identical by construction
    st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    aux = json.load(open(f"{snapdir}/aux.json"))
    st.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
    st.H = np.zeros(st.NW)
    for k, v in aux["H"].items(): st.H[int(k)] = float(v)
    st.last_anchor = int(aux["last_anchor"]); st.ema = aux["ema"]; st.ledger = {s: [list(r) for r in rows] for s, rows in aux["ledger_tail"].items()}
    st.prev_rec = aux.get("prev_rec"); st.base = list(aux.get("base_syms") or st.live)
    lr = np.load(f"{WS}/shadow_bundle/leg_returns.npz"); extra = json.load(open(f"{snapdir}/leg_returns_live.json"))
    st.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}
    return st

def main_snapshot(snapdir, anchors, cfg, booster, snap, receipts):
    st = build_state_from_snapshot(snapdir, cfg); assert anchors[0] == st.last_anchor + 14400, (anchors[0], st.last_anchor)
    ledger_full = {s: [list(r) for r in rows] for s, rows in json.load(open(f"{WS}/state/aux.json"))["ledger_tail"].items()}   # current ledger serves rows after the snapshot
    fx = dev.ReplayFetcher(st.base, ledger_full)
    for k, A in enumerate(anchors):
        for d_ in ("weights", "target_live", "target_live_combo", "target_combo", "target_blend", "target_live_king"):
            for f in (f"{RH}/state/{d_}/{A}.json", f"{RH}/state/{d_}/{A}.json.sha256", f"{RH}/state/{d_}/{A}.npz"):
                if os.path.exists(f): os.remove(f)
        if os.path.exists(f"{RH}/shadow_log.jsonl"): os.remove(f"{RH}/shadow_log.jsonl")
        t0 = time.time(); dev.run_anchor(st, fx, cfg, booster, A); dt = time.time() - t0
        cmp = compare(A, f"{RH}/state"); cmp["runtime_s"] = round(dt, 1); cmp["mode"] = "snapshot"; cmp["snapshot"] = snapdir
        if os.environ.get("REPLAY_COMBO", "1") == "1": cmp["combo"] = run_combo_stage(A, st, k == 0)
        receipts["anchors"].append(cmp); cb = cmp.get("combo") or {}
        print(json.dumps({"anchor": A, "king_Linf": cmp["weights_npz_Linf"], "content_sha_equal": cmp["content_sha_equal"], "ulp_names": cmp["n_names_differing_any"], "combo_rc": cb.get("rc"), "target_combo_Linf": cb.get("target_combo_Linf"), "target_live_Linf": cb.get("target_live_Linf"), "err": cb.get("err") or cb.get("compare_error")}), flush=True)

def main_chain(anchors, cfg, booster, snap, receipts):
    """CHAIN mode: rebuild state once (first anchor) and carry the float64 state forward; step 6 (score/LR append) runs
    from the replay's own prev_rec, so the appended LR entries are compared with the live leg_returns_live entries."""
    A0 = anchors[0]; st, ledger_full, diag0 = build_state(A0, cfg, snap); fx = dev.ReplayFetcher(st.base, ledger_full)
    live_extra = snap["lr_extra"]; n_after0 = sum(1 for r in snap["log"] if r.get("e") == "score" and int(r.get("anchor_ts", 0)) >= A0)
    receipts["chain_start_diag"] = diag0
    for k, A in enumerate(anchors):
        # keep the chain's previous-anchor files (combo_stage reads weights/{A-4h}.npz as H); only clear this anchor's outputs
        for d_ in ("weights", "target_live", "target_live_combo", "target_combo", "target_blend", "target_live_king"):
            for f in (f"{RH}/state/{d_}/{A}.json", f"{RH}/state/{d_}/{A}.json.sha256", f"{RH}/state/{d_}/{A}.npz"):
                if os.path.exists(f): os.remove(f)
        if os.path.exists(f"{RH}/shadow_log.jsonl"): os.remove(f"{RH}/shadow_log.jsonl")
        # cache rows for (last_anchor, A] are already in st.cd (producer's own rows); ledger stub serves (last_ts, A]
        lr_len_before = len(st.LR["king"])
        t0 = time.time(); dev.run_anchor(st, fx, cfg, booster, A); dt = time.time() - t0
        cmp = compare(A, f"{RH}/state"); cmp["runtime_s"] = round(dt, 1); cmp["mode"] = "chain"
        if os.environ.get("REPLAY_COMBO", "1") == "1":
            cmp["combo"] = run_combo_stage(A, st, k == 0)
        # LR parity: the entry appended by this anchor's step 6 (score for A-14400) vs the live file's entry at the same position
        if k > 0 and len(st.LR["king"]) == lr_len_before + 1:
            live_pos = len(live_extra["king"]) - n_after0 + k       # index in live extra list of the entry appended at anchor A
            lrd = {leg: (float(st.LR[leg][-1]), float(live_extra[leg][live_pos - 1]) if 0 <= live_pos - 1 < len(live_extra[leg]) else None) for leg in ("king", "rev24", "fund")}
            cmp["lr_entry_replay_vs_live"] = lrd; cmp["lr_entry_max_abs_diff"] = max(abs(a - b) for a, b in lrd.values() if b is not None)
        rep_sig = [r for r in jl(f"{RH}/shadow_log.jsonl") if r.get("e") == "signal"]; live_sig = [r for r in snap["log"] if r.get("e") == "signal" and int(r.get("anchor_ts", 0)) == A]
        cmp["signal_live"] = {kk: live_sig[-1].get(kk) for kk in ("members", "sel", "w3", "turnover", "gross_pos", "base_n", "fund_updates")} if live_sig else None
        cmp["signal_replay"] = {kk: rep_sig[-1].get(kk) for kk in ("members", "sel", "w3", "turnover", "gross_pos", "base_n", "fund_updates")} if rep_sig else None
        receipts["anchors"].append(cmp)
        cb = cmp.get("combo") or {}
        print(json.dumps({"anchor": A, "king_Linf": cmp["weights_npz_Linf"], "lr_diff": cmp.get("lr_entry_max_abs_diff"), "combo_rc": cb.get("rc"), "target_combo_Linf": cb.get("target_combo_Linf"), "target_live_Linf": cb.get("target_live_Linf"), "w3m_equal": cb.get("w3m_equal"), "ftrim_n": cb.get("ftrim_n"), "combo_s": cb.get("runtime_s"), "err": cb.get("err") or cb.get("compare_error")}), flush=True)

def main():
    snapdir = None
    argv = list(sys.argv[1:])
    if "--snapshot" in argv:
        i = argv.index("--snapshot"); snapdir = argv[i + 1]; del argv[i:i + 2]
    anchors = [int(x) for x in argv if x != "--chain"]; chain = "--chain" in argv
    cfg, booster, man = dev.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    if os.environ.get("REPLAY_ALPHA_OVERRIDE"):   # G-P4 red-capability control only
        cfg["params"]["alpha"] = float(os.environ["REPLAY_ALPHA_OVERRIDE"]); print("G-P4 CONTROL: alpha overridden to", cfg["params"]["alpha"], flush=True)
    snap = {"aux": json.load(open(f"{WS}/state/aux.json")), "lr_extra": json.load(open(f"{WS}/state/leg_returns_live.json")),
            "rolling": f"{WS}/state/rolling.npz", "log": jl(f"{WS}/shadow_log.jsonl")}
    receipts = {"device_sha256": sha_file(os.path.join(HERE, "shadow_loop_v3_replay.py")), "production_sha256": dev.REPLAY_META["production_sha256"],
                "bundle_manifest_sha256": sha_file(f"{WS}/shadow_bundle/MANIFEST.json"), "rolling_sha256": sha_file(snap["rolling"]),
                "aux_sha256": sha_file(f"{WS}/state/aux.json"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "anchors": []}
    if snapdir:
        main_snapshot(snapdir, anchors, cfg, booster, snap, receipts)
        tag = os.environ.get("REPLAY_RECEIPT_TAG", "GP3_snapshot")
        json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"PARITY_{tag}_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1); return
    if chain:
        main_chain(anchors, cfg, booster, snap, receipts)
        tag = os.environ.get("REPLAY_RECEIPT_TAG", "phase1_chain")
        json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"PARITY_{tag}_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1); return
    for A in anchors:
        for d_ in ("weights", "target_live"):
            shutil.rmtree(f"{RH}/state/{d_}", ignore_errors=True)
        if os.path.exists(f"{RH}/shadow_log.jsonl"): os.remove(f"{RH}/shadow_log.jsonl")
        st, ledger_full, diag = build_state(A, cfg, snap)
        fx = dev.ReplayFetcher(st.base, ledger_full)
        live_sig = [r for r in snap["log"] if r.get("e") == "signal" and int(r.get("anchor_ts", 0)) == A]
        t0 = time.time(); dev.run_anchor(st, fx, cfg, booster, A); dt = time.time() - t0
        rep_sig = [r for r in jl(f"{RH}/shadow_log.jsonl") if r.get("e") == "signal"]
        cmp = compare(A, f"{RH}/state")
        cmp.update({"diag": diag, "fetcher_calls": fx.calls, "runtime_s": round(dt, 1),
                    "signal_live": {k: live_sig[-1].get(k) for k in ("members", "sel", "w3", "turnover", "gross_pos", "weights_sha", "base_n", "fund_updates")} if live_sig else None,
                    "signal_replay": {k: rep_sig[-1].get(k) for k in ("members", "sel", "w3", "turnover", "gross_pos", "weights_sha", "base_n", "fund_updates")} if rep_sig else None})
        receipts["anchors"].append(cmp)
        print(json.dumps({k: cmp[k] for k in ("anchor", "weights_npz_Linf", "weights_npz_L1", "target_live_json_Linf", "content_sha_equal", "n_names_differing_any", "n_nonzero_replay", "n_nonzero_live", "runtime_s")}), flush=True)
        print("  diag:", json.dumps(diag)); print("  live  :", json.dumps(cmp["signal_live"])); print("  replay:", json.dumps(cmp["signal_replay"]))
    os.makedirs(os.path.join(os.path.dirname(HERE), "receipts"), exist_ok=True)
    tag = os.environ.get("REPLAY_RECEIPT_TAG", "phase1")
    json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"PARITY_{tag}_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1)
if __name__ == "__main__":
    main()
