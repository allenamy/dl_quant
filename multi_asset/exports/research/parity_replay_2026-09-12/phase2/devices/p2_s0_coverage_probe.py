#!/usr/bin/env python3
"""S0 plumbing statistic (no book number): on sampled historical anchors, how many PRODUCTION members (computed by the byte-identical device's own
membership code on the Phase 2 cache/universe inputs) have an out-of-fold king / F10 score in the research OOF arrays. Stateless per anchor: a fresh
ShadowState, run_anchor up to its `booster.predict(X)` call, where a probe booster records (anchor, members) and raises a sentinel (nothing after that
line executes; no weights/target files are written). Also reports overlap with the research king-meta member set.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_s0_coverage_probe.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, calendar, copy, importlib, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p2_driver as D
OUT = D.under(f"{D.P2}/receipts/S0_coverage_probe.json"); RH = D.under(f"{D.P2}/work/runs/s0_coverage_probe")
os.makedirs(f"{RH}/state/weights", exist_ok=True)
os.environ["WIDE_SHADOW_HOME"] = RH; os.environ["WIDE_SHADOW_BUNDLE"] = "/workspace/shadow_bundle_v3"
for f, s in D.PIN.items(): assert D.sha(f"{D.DEVDIR}/{f}") == s, f
sys.path.insert(0, D.DEVDIR); dev = importlib.import_module("shadow_loop_v3_replay")
T0 = time.time()
arm = {"king_oof": "SLOW_v4", "f10_oof": "v4RAW_s42", "f10_seed": "42", "universe": "pit", "serve_policy": "serve_all"}
G = D.Globals(arm)
MM = np.load(D.SRC["king_meta_v4"][0], allow_pickle=True); ME = MM["E_ts"].astype(np.int64); MROW = {int(t): i for i, t in enumerate(ME)}; MMEM = MM["members"]
class Sentinel(Exception): pass
class ProbeBooster:
    def predict(self, X):
        f = sys._getframe(1); assert f.f_code.co_name == "run_anchor"
        self.anchor = int(f.f_locals["anchor"]); self.m = np.asarray(f.f_locals["m"], np.int64); raise Sentinel()
start = calendar.timegm((2022, 1, 31, 0, 0, 0)); end = calendar.timegm((2026, 8, 30, 20, 0, 0))
anchors = list(range(start, end + 1, 7 * 86400))
cfg = copy.deepcopy(G.cfg_raw)
class ProbeState(dev.ShadowState):
    def save(self): pass
rows = {"pit": [], "pins": []}
for uni in ("pit", "pins"):
    G.arm["universe"] = uni
    for A in anchors:
        live = G.live_names(A); lmask = np.zeros(829, bool); lmask[[G.col[s] for s in live]] = True
        st = ProbeState.__new__(ProbeState); st.syms = cfg["symbols_panel"]; st.NW = 829; st.sym_idx = {s: j for j, s in enumerate(st.syms)}
        st.prev_close = {}; st.H = np.zeros(829); st.last_anchor = A - 14400; st.ema = {}; st.ledger = {}; st.prev_rec = None; st.LR = {"king": [], "rev24": [], "fund": []}
        st.live = live; st.live_mask = lmask; cfg["symbols_live"] = live
        tr = G.trading24(A); st.base = sorted(set(tr) | set(live))
        fx = dev.ReplayFetcher(tr, {}); fx.ledger = {s: G.ledger_rows(s, A - 40 * 86400, A) for s in st.base}
        ai = G.row_of_ts[A]; i0 = max(0, ai + 1 - dev.CACHE_ROWS); cd = np.array(G.DATA[i0:ai + 1]); cd[:, ~lmask, :] = np.nan
        st.cts = G.TS[i0:ai + 1].copy(); st.cd = cd
        pb = ProbeBooster(); pb.m = None
        try: dev.run_anchor(st, fx, cfg, pb, A)
        except Sentinel: pass
        if pb.m is None:
            rows[uni].append({"anchor": A, "utc": D.iso(A), "n_live": len(live), "skipped_before_predict": True}); continue
        m = pb.m; kr = G.K_row.get(A); fr = G.F_row.get(A); mr = MROW.get(A)
        kfin = np.isfinite(G.KOOF[kr, m]) if kr is not None else np.zeros(len(m), bool)
        ffin = np.isfinite(G.FOOF[fr, m]) if fr is not None else np.zeros(len(m), bool)
        meta = set(int(x) for x in MMEM[mr]) if mr is not None else set()
        inmeta = np.array([int(x) in meta for x in m])
        rows[uni].append({"anchor": A, "utc": D.iso(A), "n_live": len(live), "n_members": int(len(m)), "n_king_oof": int(kfin.sum()), "n_f10_oof": int(ffin.sum()),
                          "n_in_research_meta_members": int(inmeta.sum()), "n_king_oof_not_in_meta": int((kfin & ~inmeta).sum()), "n_research_meta_members": len(meta)})
    print(uni, "done", len(rows[uni]), round(time.time() - T0, 1), flush=True)
def summ(rs):
    out = {}
    for y in sorted({time.gmtime(r["anchor"]).tm_year for r in rs}):
        rr = [r for r in rs if time.gmtime(r["anchor"]).tm_year == y and not r.get("skipped_before_predict")]
        if not rr: continue
        f = lambda k: round(float(np.mean([r[k] for r in rr])), 1)
        out[str(y)] = {"n_sampled": len(rr), "live": f("n_live"), "members": f("n_members"), "king_oof": f("n_king_oof"), "f10_oof": f("n_f10_oof"),
                       "members_in_research_meta": f("n_in_research_meta_members"), "research_meta_members": f("n_research_meta_members"),
                       "share_anchors_f10_ge380": round(float(np.mean([r["n_f10_oof"] >= 380 for r in rr])), 3),
                       "share_members_without_king_oof_when_fold_exists": (round(float(np.mean([1 - r["n_king_oof"] / r["n_members"] for r in rr if r["n_king_oof"] > 0])), 4) if any(r["n_king_oof"] > 0 for r in rr) else None),
                       "share_members_without_f10_oof_when_fold_exists": (round(float(np.mean([1 - r["n_f10_oof"] / r["n_members"] for r in rr if r["n_f10_oof"] > 0])), 4) if any(r["n_f10_oof"] > 0 for r in rr) else None)}
    return out
doc = {"device": os.path.abspath(__file__), "self_sha256": D.sha(os.path.abspath(__file__)), "driver_sha256": D.sha(D.__file__), "env": dict(os.environ), "input_shas": G.shas,
       "sampling": "every 7 days at 00Z, 2022-01-31 .. 2026-08-30", "summary": {u: summ(rows[u]) for u in rows}, "rows": rows, "runtime_s": round(time.time() - T0, 1),
       "nvidia_smi": subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()}
json.dump(doc, open(OUT, "w"), indent=1)
print("S0_COVERAGE_PROBE_DONE", json.dumps(doc["summary"]), flush=True)
