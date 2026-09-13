#!/usr/bin/env python3
"""T4b driver (PREREG_T4b_v2main_feature_skew_2026-09-13 §5), DERIVED from T4/devices/t4_replay_driver.py, itself derived from
parity_replay_2026-09-12/devices/replay_driver.py (sha f2ced820…); diffs: devices/t4b_replay_driver.diff (vs parity) and
devices/t4b_replay_driver_vs_t4.diff. Mode = G-P3 forward mode only: start from the producer's anchor-close snapshot
producer_state_snapshots/1789200000 (float64 state; no EMA inversion, no float32 archive). Changes marked "# T4b":
  (1) one replay home per arm under T4b/private/;  (2) the cache, the ledger rows after the snapshot, and every live file used for
  comparison are read from the frozen copy T4b/private/snapshot_live (SHA256SUMS verified at start), never from ~/wide_shadow/state;
  (3) --arm served | v2inj | v2v0 | seatK1: king stage = parity device for all arms; combo stage = parity combo device (served, seatK1)
  or the one-line device combo_stage_replay_v2col80.py (v2inj: fed the replay's own EMA acc; v2v0: fed the v0 feed) via T4B_COL80_NPZ;
  seatK1 replaces only the seat-history file (leg_returns_live) with the seeded-rows-K1 override;
  (4) per-anchor records: king X/pred (booster proxy), the combo stage's X171 rows and V2MAIN scores (recomputed from its own mini
  data with the combo stage's formula), panel row, chain states, targets;  (5) no bytecode written.
Usage: python3 -B t4b_replay_driver.py --arm <arm> --snapshot <producer snapshot dir> <anchor_ts> ..."""
import os, sys, json, glob, math, hashlib, shutil, importlib, time
import numpy as np
WS = os.path.expanduser("~/wide_shadow"); HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True   # T4b (5)
T4 = os.path.dirname(HERE); SNAP = T4 + "/private/snapshot_live"   # T4b (2): name T4 kept for the variable = this task's root (T4b/)
ARM = sys.argv[sys.argv.index("--arm") + 1] if "--arm" in sys.argv else None; assert ARM in ("served", "v2inj", "v2v0", "seatK1"), ARM   # T4b (3)
DEVMOD = "shadow_loop_v3_replay"
COMBO_FILE = {"served": "combo_stage_replay.py", "seatK1": "combo_stage_replay.py", "v2inj": "combo_stage_replay_v2col80.py", "v2v0": "combo_stage_replay_v2col80.py"}[ARM]
_fr = open(T4 + "/receipts/PREREG_FREEZE_sha.txt").readline().split(); assert _fr[0] == "PREREG_T4b_v2main_feature_skew_2026-09-13.md" and _fr[1] == "sha256", _fr
PREREG_SHA = _fr[2]; DEV_SHA = {"shadow_loop_v3_replay": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"}
COMBO_SHA = {"combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b", "combo_stage_replay_v2col80.py": "8d7e22dfbdb2305260913a0106007cb64517745556891aad768d89911cb39dfb"}
def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert _sha(T4 + "/PREREG_T4b_v2main_feature_skew_2026-09-13.md") == PREREG_SHA and _sha(f"{HERE}/{DEVMOD}.py") == DEV_SHA[DEVMOD] and _sha(f"{HERE}/{COMBO_FILE}") == COMBO_SHA[COMBO_FILE]
for _l in open(SNAP + "/SHA256SUMS.txt"):
    _h, _f = _l.split(None, 1); assert _sha(SNAP + "/" + _f.strip()[2:]) == _h, ("SNAPSHOT CHANGED", _f)
assert os.environ.get("REPLAY_COMBO", "1") == "1"
RH = T4 + f"/private/replay_home_{ARM}"; os.makedirs(RH + "/state", exist_ok=True)   # T4b (1)
os.environ["WIDE_SHADOW_HOME"] = RH; os.environ["WIDE_SHADOW_BUNDLE"] = f"{WS}/shadow_bundle"   # bundle read-only (load_bundle only reads)
sys.path.insert(0, HERE); dev = importlib.import_module(DEVMOD)
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
    st.prev_close = {}
    # H = holdings after the previous anchor = the producer's own weights file
    st.H = np.zeros(st.NW); wf = f"{SNAP}/state/weights/{anchor-14400}.npz"   # T4 (2)
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
    diag = {"ema_inverted": len(ema_b), "ema_mismatch_fallback": mism, "ema_roundtrip_worst_abs": worst, "ema_roundtrip_n": n,
            "lr_dropped_entries": n_after, "lr_len_before_anchor": len(st.LR["king"]), "base_n": len(st.base),
            "cache_rows": int(len(st.cts)), "cache_last": int(st.cts[-1])}
    return st, ledger_full, diag

def compare(anchor, out_state_dir):
    rep = np.load(f"{out_state_dir}/weights/{anchor}.npz"); liv = np.load(f"{SNAP}/state/weights/{anchor}.npz")   # T4 (2)
    NW = 829; a = np.zeros(NW); b = np.zeros(NW)
    a[rep["idx"].astype(int)] = rep["val"].astype(np.float64); b[liv["idx"].astype(int)] = liv["val"].astype(np.float64)
    d = np.abs(a - b); linf = float(d.max()); l1 = float(d.sum())
    def _csha(z): return hashlib.sha256(z["idx"].astype(np.int32).tobytes() + z["val"].astype(np.float32).tobytes()).hexdigest()
    content_sha_equal = _csha(rep) == _csha(liv)
    ulp = int((np.abs(a - b) > 0).sum())
    rj = json.load(open(f"{out_state_dir}/target_live/{anchor}.json")); lj = json.load(open(f"{SNAP}/state/target_live_king/{anchor}.json"))   # T4 (2)
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
        os.symlink(f"{SNAP}/state/rolling.npz", rp)   # T4 (2)

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
            src = f"{SNAP}/fea171/state_H_{tag}_{A-14400}.npz"   # T4 (2)
            if os.path.exists(src): shutil.copy2(src, f"{fe}/state_H_{tag}_{A-14400}.npz")
        if os.path.exists(f"{SNAP}/state/weights/{A-14400}.npz"): shutil.copy2(f"{SNAP}/state/weights/{A-14400}.npz", f"{RH}/state/weights/{A-14400}.npz")   # T4 (2)
    _write_replay_state(A, st)
    shutil.rmtree(f"{fe}/mini/data", ignore_errors=True)      # force the 171 feature pipeline to recompute for THIS anchor (as live did)
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~"), "WIDE_SHADOW_HOME": RH, "COMBO_LIVE": "1", "COMBO_LIVE_DIR": f"{RH}/state/target_live_combo", "REPLAY_TRUNCATE_CACHE": "1", "PYTHONDONTWRITEBYTECODE": "1"}   # T4 (5)
    if ARM in ("v2inj", "v2v0"): env["T4B_COL80_NPZ"] = t4b_write_col80(A, st)   # T4b (3)
    t0 = time.time(); p = subprocess.run([sys.executable, os.path.join(HERE, COMBO_FILE)], cwd=fe, env=env, capture_output=True, text=True, timeout=900)   # T4b (3)
    out = {"rc": p.returncode, "runtime_s": round(time.time() - t0, 1), "tail": p.stdout.strip().splitlines()[-3:] if p.stdout else [], "err": p.stderr.strip().splitlines()[-3:] if p.stderr else []}
    try:
        rc_ = json.load(open(f"{RH}/state/target_combo/{A}.json")); lc = json.load(open(f"{SNAP}/state/target_combo/{A}.json"))   # T4 (2)
        keys = set(rc_["weights"]) | set(lc["weights"]); out["target_combo_Linf"] = max(abs(rc_["weights"].get(k, 0.0) - lc["weights"].get(k, 0.0)) for k in keys)
        out["target_combo_n"] = (len(rc_["weights"]), len(lc["weights"])); out["w3m_equal"] = rc_["w3_masked"] == lc["w3_masked"]; out["ftrim_n"] = (rc_["ftrim"]["n_kc"], rc_["ftrim"]["n_fc"], lc["ftrim"]["n_kc"], lc["ftrim"]["n_fc"])
        rl = json.load(open(f"{RH}/state/target_live_combo/{A}.json")); ll = json.load(open(f"{SNAP}/state/target_live/{A}.json"))   # T4 (2)
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
    z = np.load(f"{SNAP}/state/rolling.npz", allow_pickle=True)            # T4b (2): frozen copy of the cache taken after the last replayed anchor
    st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    aux = json.load(open(f"{snapdir}/aux.json"))
    st.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
    st.H = np.zeros(st.NW)
    for k, v in aux["H"].items(): st.H[int(k)] = float(v)
    st.last_anchor = int(aux["last_anchor"]); st.ema = aux["ema"]; st.ledger = {s: [list(r) for r in rows] for s, rows in aux["ledger_tail"].items()}
    st.prev_rec = aux.get("prev_rec"); st.base = list(aux.get("base_syms") or st.live)
    lr = np.load(f"{WS}/shadow_bundle/leg_returns.npz"); extra = json.load(open(f"{snapdir}/leg_returns_live.json" if ARM != "seatK1" else T4 + "/private/seat_override/leg_returns_live.seatK1.json"))   # T4b (3)
    st.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}
    return st

def main_snapshot(snapdir, anchors, cfg, booster, snap, receipts):
    st = build_state_from_snapshot(snapdir, cfg); assert anchors[0] == st.last_anchor + 14400, (anchors[0], st.last_anchor)
    ledger_full = {s: [list(r) for r in rows] for s, rows in json.load(open(f"{SNAP}/state/aux.json"))["ledger_tail"].items()}   # T4b (2): frozen ledger serves rows after the snapshot
    fx = dev.ReplayFetcher(st.base, ledger_full); rb = RecBooster(booster); REC = []   # T4b (4)
    for k, A in enumerate(anchors):
        for d_ in ("weights", "target_live", "target_live_combo", "target_combo", "target_blend", "target_live_king"):
            for f in (f"{RH}/state/{d_}/{A}.json", f"{RH}/state/{d_}/{A}.json.sha256", f"{RH}/state/{d_}/{A}.npz"):
                if os.path.exists(f): os.remove(f)
        if os.path.exists(f"{RH}/shadow_log.jsonl"): os.remove(f"{RH}/shadow_log.jsonl")
        t0 = time.time(); rb.last = None; dev.run_anchor(st, fx, cfg, rb, A); dt = time.time() - t0   # T4b (4)
        cmp = compare(A, f"{RH}/state"); cmp["runtime_s"] = round(dt, 1); cmp["mode"] = "snapshot"; cmp["snapshot"] = snapdir
        if os.environ.get("REPLAY_COMBO", "1") == "1": cmp["combo"] = run_combo_stage(A, st, k == 0)
        REC.append(t4b_record(A, st, rb)); np.save(T4 + f"/private/replay_rec_{ARM}.npy", np.array(REC, dtype=object), allow_pickle=True)   # T4b (4)
        receipts["anchors"].append(cmp); cb = cmp.get("combo") or {}
        print(json.dumps({"anchor": A, "king_Linf": cmp["weights_npz_Linf"], "content_sha_equal": cmp["content_sha_equal"], "ulp_names": cmp["n_names_differing_any"], "combo_rc": cb.get("rc"), "target_combo_Linf": cb.get("target_combo_Linf"), "target_live_Linf": cb.get("target_live_Linf"), "err": cb.get("err") or cb.get("compare_error")}), flush=True)

class RecBooster:   # T4 (4): records the exact matrix the device feeds the booster and the returned scores; delegates unchanged
    def __init__(self, b): self.b = b; self.last = None
    def predict(self, X):
        p = self.b.predict(X); self.last = (np.array(X, dtype=np.float32, copy=True), np.array(p, dtype=np.float64, copy=True)); return p

def t4_record(A, st, rb):   # T4 (4): per-anchor outputs for the T4 live-window judge
    X, pred = rb.last; pr = st.prev_rec; m = np.array(pr["members"], np.int64)
    ivm = np.array([float(st.ledger[st.syms[j]][-1][2]) if st.ledger.get(st.syms[j]) else np.nan for j in m])
    kw = np.load(f"{RH}/state/weights/{A}.npz"); sig = [r for r in jl(f"{RH}/shadow_log.jsonl") if r.get("e") == "signal"]
    o = dict(anchor=int(A), members=m, X=X, pred=pred, legz_king=np.array(pr["legz"]["king"]), iv_last=ivm, king_idx=kw["idx"].astype(np.int64), king_val=kw["val"].astype(np.float64),
             w3=np.array(sig[-1]["w3"]) if sig else None)
    for d_ in ("target_live_combo", "target_combo"):
        f = f"{RH}/state/{d_}/{A}.json"
        if os.path.exists(f):
            J = json.load(open(f)); o[d_ + "_weights"] = J["weights"]
            if d_ == "target_combo": o["w3_masked"] = J["w3_masked"]; o["ftrim_n"] = (J["ftrim"]["n_kc"], J["ftrim"]["n_fc"])
    return o

def t4b_write_col80(A, st):   # T4b (3): the value the one-line device reads for column 80 of this anchor, in symbols_panel order
    if ARM == "v2inj":
        row = np.array([float(st.ema[s_]["acc"]) if isinstance(st.ema.get(s_), dict) else np.nan for s_ in st.syms])
    else:
        FEED = np.load(T4 + "/private/v0_feed_fwd.npz", allow_pickle=True); FA = {int(a): i for i, a in enumerate(FEED["anchors"])}
        assert [str(x) for x in FEED["symbols"]] == list(st.syms); row = FEED["V0"][FA[int(A)]].astype(np.float64)
    p = f"{RH}/t4b_col80_{A}.npz"; np.savez(p, **{"A%d" % A: row}); return p

def t4b_record(A, st, rb):   # T4b (4): per-anchor outputs for the T4b live-window judge
    o = t4_record(A, st, rb); fe = f"{RH}/fea171"
    T9 = np.load(f"{fe}/mini/data/dlw_targets.npz", allow_pickle=True); F82 = np.load(f"{fe}/mini/data/dlw_fea82.npz", allow_pickle=True); F89 = np.load(f"{fe}/mini/data/f8_fea89.npz", allow_pickle=True)
    ets = T9["E_ts"].astype(np.int64); a_i = int(np.where(ets == A)[0][0]); pa2 = F82["pair_a"].astype(np.int64); ps2 = F82["pair_s"].astype(np.int64); rowm = pa2 == a_i
    X171 = np.concatenate([F82["X"][rowm].astype(np.float32), F89["X"][rowm]], 1); scol = ps2[rowm]
    M = np.load(f"{fe}/f10_live_s42_np.npz")
    from scipy.special import erf
    def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5)); h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"]); f10 = (h @ M["w2"].T + M["b2"]).squeeze(-1)   # combo_stage.py L165-167
    P = np.load(f"{fe}/xfer_panel_live.npz")
    o.update(combo_X171=X171, combo_scol=scol, combo_f10=f10.astype(np.float64), panel_fe_last=P["f_fund_ema"][-1].astype(np.float32), panel_fn_last=P["f_fund_now"][-1].astype(np.float32),
             panel_hist_rows_all_zero=bool((P["f_fund_ema"][:-1] == 0).all() and (P["f_fund_now"][:-1] == 0).all()), n_panel_rows=int(P["f_fund_ema"].shape[0]))
    for tag in ("f10", "kc", "fc"):
        z = np.load(f"{fe}/state_H_{tag}_{A}.npz"); o[f"state_H_{tag}"] = (z["idx"].astype(np.int64), z["val"].astype(np.float64))
    return o

def main_chain(anchors, cfg, booster, snap, receipts):
    """CHAIN mode: rebuild state once (first anchor) and carry the float64 state forward; step 6 (score/LR append) runs
    from the replay's own prev_rec, so the appended LR entries are compared with the live leg_returns_live entries."""
    A0 = anchors[0]; st, ledger_full, diag0 = build_state(A0, cfg, snap); fx = dev.ReplayFetcher(st.base, ledger_full)
    rb = RecBooster(booster); REC = []   # T4 (4)
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
        t0 = time.time(); rb.last = None; dev.run_anchor(st, fx, cfg, rb, A); dt = time.time() - t0   # T4 (4)
        cmp = compare(A, f"{RH}/state"); cmp["runtime_s"] = round(dt, 1); cmp["mode"] = "chain"
        if os.environ.get("REPLAY_COMBO", "1") == "1":
            cmp["combo"] = run_combo_stage(A, st, k == 0)
        REC.append(t4_record(A, st, rb))   # T4 (4)
        # LR parity: the entry appended by this anchor's step 6 (score for A-14400) vs the live file's entry at the same position
        if k > 0 and len(st.LR["king"]) == lr_len_before + 1:
            live_pos = len(live_extra["king"]) - n_after0 + k       # index in live extra list of the entry appended at anchor A
            lrd = {leg: (float(st.LR[leg][-1]), float(live_extra[leg][live_pos - 1]) if 0 <= live_pos - 1 < len(live_extra[leg]) else None) for leg in ("king", "rev24", "fund")}
            cmp["lr_entry_replay_vs_live"] = lrd; cmp["lr_entry_max_abs_diff"] = max(abs(a - b) for a, b in lrd.values() if b is not None)
        rep_sig = [r for r in jl(f"{RH}/shadow_log.jsonl") if r.get("e") == "signal"]; live_sig = [r for r in snap["log"] if r.get("e") == "signal" and int(r.get("anchor_ts", 0)) == A]
        cmp["signal_live"] = {kk: live_sig[-1].get(kk) for kk in ("members", "sel", "w3", "turnover", "gross_pos", "base_n", "fund_updates")} if live_sig else None
        cmp["signal_replay"] = {kk: rep_sig[-1].get(kk) for kk in ("members", "sel", "w3", "turnover", "gross_pos", "base_n", "fund_updates")} if rep_sig else None
        receipts["anchors"].append(cmp)
        np.save(T4 + f"/private/replay_rec_{ARM}.npy", np.array(REC, dtype=object), allow_pickle=True)   # T4 (4): rewritten each anchor
        cb = cmp.get("combo") or {}
        print(json.dumps({"anchor": A, "king_Linf": cmp["weights_npz_Linf"], "lr_diff": cmp.get("lr_entry_max_abs_diff"), "combo_rc": cb.get("rc"), "target_combo_Linf": cb.get("target_combo_Linf"), "target_live_Linf": cb.get("target_live_Linf"), "w3m_equal": cb.get("w3m_equal"), "ftrim_n": cb.get("ftrim_n"), "combo_s": cb.get("runtime_s"), "err": cb.get("err") or cb.get("compare_error")}), flush=True)

def main():
    snapdir = None
    argv = list(sys.argv[1:])
    if "--snapshot" in argv:
        i = argv.index("--snapshot"); snapdir = argv[i + 1]; del argv[i:i + 2]
    if "--arm" in argv: i = argv.index("--arm"); del argv[i:i + 2]   # T4 (3)
    anchors = [int(x) for x in argv if x != "--chain"]; chain = "--chain" in argv
    assert snapdir and not chain, "T4b: snapshot-forward mode only"   # T4b
    cfg, booster, man = dev.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    if os.environ.get("REPLAY_ALPHA_OVERRIDE"):   # G-P4 red-capability control only
        cfg["params"]["alpha"] = float(os.environ["REPLAY_ALPHA_OVERRIDE"]); print("G-P4 CONTROL: alpha overridden to", cfg["params"]["alpha"], flush=True)
    snap = {"aux": json.load(open(f"{SNAP}/state/aux.json")), "lr_extra": json.load(open(f"{SNAP}/state/leg_returns_live.json")),
            "rolling": f"{SNAP}/state/rolling.npz", "log": jl(f"{SNAP}/shadow_log.jsonl")}   # T4b (2)
    receipts = {"device_sha256": sha_file(os.path.join(HERE, DEVMOD + ".py")), "production_sha256": dev.REPLAY_META["production_sha256"],   # T4 (3)
                "bundle_manifest_sha256": sha_file(f"{WS}/shadow_bundle/MANIFEST.json"), "rolling_sha256": sha_file(snap["rolling"]),
                "aux_sha256": sha_file(f"{SNAP}/state/aux.json"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "anchors": []}   # T4 (2)
    if snapdir:
        main_snapshot(snapdir, anchors, cfg, booster, snap, receipts)
        tag = f"T4B_REPLAY_{ARM}"   # T4b
        receipts.update(arm=ARM, king_device_sha256=DEV_SHA[DEVMOD], combo_device=COMBO_FILE, combo_device_sha256=COMBO_SHA[COMBO_FILE], prereg_sha256=PREREG_SHA, snapshot_live=SNAP,
                        snapshot_live_sums_sha256=_sha(SNAP + "/SHA256SUMS.txt"), producer_snapshot=snapdir, driver_sha256=_sha(os.path.abspath(__file__)),
                        env={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__)
        json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"{tag}_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1); return
    if chain:
        main_chain(anchors, cfg, booster, snap, receipts)
        tag = f"T4_REPLAY_{ARM}"   # T4
        receipts.update(arm=ARM, device_module=DEVMOD, device_file_sha256=DEV_SHA[DEVMOD], combo_device_sha256=COMBO_SHA, prereg_sha256=PREREG_SHA, snapshot=SNAP, snapshot_sums_sha256=_sha(SNAP + "/SHA256SUMS.txt"),
                        driver_sha256=_sha(os.path.abspath(__file__)), env={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__)
        json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"{tag}_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1); return
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
