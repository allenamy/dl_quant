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
    st.prev_close = {}
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
    diag = {"ema_inverted": len(ema_b), "ema_mismatch_fallback": mism, "ema_roundtrip_worst_abs": worst, "ema_roundtrip_n": n,
            "lr_dropped_entries": n_after, "lr_len_before_anchor": len(st.LR["king"]), "base_n": len(st.base),
            "cache_rows": int(len(st.cts)), "cache_last": int(st.cts[-1])}
    return st, ledger_full, diag

def compare(anchor, out_state_dir):
    rep = np.load(f"{out_state_dir}/weights/{anchor}.npz"); liv = np.load(f"{WS}/state/weights/{anchor}.npz")
    NW = 829; a = np.zeros(NW); b = np.zeros(NW)
    a[rep["idx"].astype(int)] = rep["val"].astype(np.float64); b[liv["idx"].astype(int)] = liv["val"].astype(np.float64)
    d = np.abs(a - b); linf = float(d.max()); l1 = float(d.sum())
    rj = json.load(open(f"{out_state_dir}/target_live/{anchor}.json")); lj = json.load(open(f"{WS}/state/target_live_king/{anchor}.json"))
    rw, lw = rj["weights"], lj["weights"]; keys = set(rw) | set(lw)
    jd = max(abs(rw.get(k, 0.0) - lw.get(k, 0.0)) for k in keys) if keys else 0.0
    return {"anchor": anchor, "weights_npz_Linf": linf, "weights_npz_L1": l1, "n_nonzero_replay": int((a != 0).sum()), "n_nonzero_live": int((b != 0).sum()),
            "target_live_json_Linf": jd, "n_names_replay": rj["n_names"], "n_names_live": lj["n_names"],
            "weights_sha_equal": rj["weights_sha"] == lj["weights_sha"], "universe_sha_equal": rj["universe_sha"] == lj["universe_sha"],
            "worst_names": sorted(((float(d[j]), dev.load_bundle.__globals__["json"] and str(j)) for j in np.argsort(-d)[:5]), reverse=True)}

def main():
    anchors = [int(x) for x in sys.argv[1:]]
    cfg, booster, man = dev.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    snap = {"aux": json.load(open(f"{WS}/state/aux.json")), "lr_extra": json.load(open(f"{WS}/state/leg_returns_live.json")),
            "rolling": f"{WS}/state/rolling.npz", "log": jl(f"{WS}/shadow_log.jsonl")}
    receipts = {"device_sha256": sha_file(os.path.join(HERE, "shadow_loop_v3_replay.py")), "production_sha256": dev.REPLAY_META["production_sha256"],
                "bundle_manifest_sha256": sha_file(f"{WS}/shadow_bundle/MANIFEST.json"), "rolling_sha256": sha_file(snap["rolling"]),
                "aux_sha256": sha_file(f"{WS}/state/aux.json"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "anchors": []}
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
        print(json.dumps({k: cmp[k] for k in ("anchor", "weights_npz_Linf", "weights_npz_L1", "target_live_json_Linf", "weights_sha_equal", "n_nonzero_replay", "n_nonzero_live", "runtime_s")}), flush=True)
        print("  diag:", json.dumps(diag)); print("  live  :", json.dumps(cmp["signal_live"])); print("  replay:", json.dumps(cmp["signal_replay"]))
    os.makedirs(os.path.join(os.path.dirname(HERE), "receipts"), exist_ok=True)
    json.dump(receipts, open(os.path.join(os.path.dirname(HERE), "receipts", f"PARITY_phase1_{anchors[0]}_{anchors[-1]}.json"), "w"), indent=1)
if __name__ == "__main__":
    main()
