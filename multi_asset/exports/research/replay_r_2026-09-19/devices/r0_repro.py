#!/usr/bin/env python3
"""r0_repro.py — stream R gate R0 (docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md §2 stream R; task brief item 1).

Before anything else: recompute S2's published P2 numbers from the S2 per-anchor sparse target vectors (RUN_S2_<arm>.vec.npz + RUN_S2_<arm>.json)
with S2's OWN accounting — the S2 library p2_s2_lib.py (sha c53f5c49…, the lib the published S2_TABLES.json 2f3c67f6… was built with) imported
read-only from its original location, and p2_s2_tables.py's book_series() logic (NOSTOP: X = smr(W), gross_total = Σ|W|, full-829 accounting;
STOP: L.Overlay(EX, CONF, syms, "STOP") with the 918559f executor functions) — and compare every published g (levels W_ALPHA / W_FULL / FROZEN
and per-year, W_FULL caliber) for S2_A0pred_s{42,2027} and S2_v4_s{42,2027}, books CMB / LIT / KING NOSTOP and (v4 only, as published) CMB STOP.
Gate: max |g_recomputed − g_published| ≤ 1e-6 bps/anchor/gross on every published cell of S2_A0pred_s42 and S2_v4_s42 (the two named in the
brief); s2027 cells are reported under the same rule. RED ⇒ exit 3, nothing downstream may run (r_prices / r_launch refuse without R0 PASS).

Side output (not a gate): the per-anchor S2 series of every book it recomputed, plus the S2-style STOP overlay for the A0pred arms (NOT
published by S2 — computed here with S2's own Overlay so the decomposition can compare like with like), written to
/workspace/replay_r_2026-09-19/work/S2_series.npz for r_tables.py.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r0_repro.py PATH,HOME
"""
import os, sys, json, time, hashlib, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
ROOT = "/workspace/replay_r_2026-09-19"; P2 = "/workspace/uplift_r2_2026-09-13/P2"
LIB = (P2 + "/devices/p2_s2_lib.py", "c53f5c495036727fcd7115bad6838229923c91f6b76bed955ebdb0f25d57c831")
PUB = (P2 + "/receipts/S2_TABLES.json", "2f3c67f6049ab538f4313dedadc6b1336e6727d6b6f69fc098c78a0ccd475bc1")
TOL = 1e-6
ARMS = ("S2_A0pred_s42", "S2_v4_s42", "S2_A0pred_s2027", "S2_v4_s2027")
GATED = ("S2_A0pred_s42", "S2_v4_s42")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


for p, s in (LIB, PUB):
    got = sha(p); assert got == s, ("pinned input", p, got, s)
spec = importlib.util.spec_from_file_location("p2_s2_lib", LIB[0]); L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
PUBD = json.load(open(PUB[0])); assert PUBD["lib_sha256"] == LIB[1], "published tables were not built with this lib"
A = L.Acct(); EXn, CONF, EXINFO = L.load_executor()
TS = L.AXIS; WIN = L.windows(TS); WN = ("W_ALPHA", "W_FULL", "FROZEN")
MI = np.array([A.mrow[int(t)] for t in TS])
def y4row(t): return A.y4[MI[t]]


def series(W, key, X=None, gt=None):
    """p2_s2_tables.py book_series(), same expressions"""
    if X is None:
        X = np.empty_like(W)
        for t in range(len(W)): X[t] = L.smr(W[t])
        gt = np.abs(W).sum(1)
    acc = A.account(TS, X, gt, "full"); g, nflat, nred = L.g_of(acc)
    assert nred == 0, f"A6.4 RED in {key}"
    tov = np.abs(np.diff(np.vstack([np.zeros(829), X]), axis=0)).sum(1)
    return dict(g=g, pnl=acc[:, 0], carry=acc[:, 1], cost=acc[:, 2], net=acc[:, 3], gross_total=gt, turnover=tov)


rec = dict(device="r0_repro.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__, python=sys.version.split()[0],
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs=dict(lib=dict(path=LIB[0], sha256=LIB[1]), published=dict(path=PUB[0], sha256=PUB[1])),
           tol_bps=TOL, gated_arms=list(GATED), runs={}, cells=[], executor=EXINFO)
OUTS = {}
for tag in ARMS:
    d, Vz, rsha, vsha = L.load_run(tag); V = {k: Vz[k] for k in Vz.files}
    rec["runs"][tag] = dict(json_sha256=rsha, vec_sha256=vsha, n_records=d["n_records"], fatal=d.get("fatal"), arm=d["arm"])
    Aax, B, fl = L.books(d, V); assert np.array_equal(Aax, TS)
    for bk in ("CMB", "LIT", "KING"):
        key = f"{tag}|{bk}|NOSTOP"; s = series(B[bk], key); OUTS[key] = s; log("series", key)
    OUTS[f"{tag}|CMB|has_states"] = dict(v=fl["has_states"].astype(np.int8))
    OUTS[f"{tag}|LIT|traded"] = dict(v=np.array([{"combo": 1, "king": 2}.get(x, 0) for x in fl["traded"]], np.int8))
    Xo, gro, ev, _ = L.Overlay(EXn, CONF, A.syms, "STOP").run(TS, B["CMB"], y4row)
    key = f"{tag}|CMB|STOP"; OUTS[key] = series(None, key, X=Xo, gt=gro); OUTS[key]["stop_triggers"] = np.array([ev["stop_triggers"]]); log("series", key, "stop_triggers", ev["stop_triggers"])
    del Xo, B
    for key in [k for k in OUTS if k.startswith(tag + "|") and not k.endswith(("has_states", "traded"))]:
        if key not in PUBD["levels"]:
            rec["cells"].append(dict(key=key, published=False)); continue
        g = OUTS[key]["g"]
        for w in WN:
            pg = PUBD["levels"][key][w]["g"]; mg = float(g[WIN[w]].mean())
            rec["cells"].append(dict(key=key, window=w, published=True, g_published=pg, g_recomputed=mg, absdiff=abs(mg - pg), gated=tag in GATED))
        for y, r in PUBD["per_year"][key].items():
            m = WIN["W_FULL"] & (L.YEAR_OF == int(y)); mg = float(g[m].mean())
            rec["cells"].append(dict(key=key, window=f"year {y}", published=True, g_published=r["g"], g_recomputed=mg, absdiff=abs(mg - r["g"]), gated=tag in GATED))

pc = [c for c in rec["cells"] if c.get("published")]
gc = [c for c in pc if c["gated"]]
rec["summary"] = dict(n_published_cells=len(pc), n_gated_cells=len(gc), max_absdiff_gated=max(c["absdiff"] for c in gc), max_absdiff_all=max(c["absdiff"] for c in pc),
                      n_gated_over_tol=sum(c["absdiff"] > TOL for c in gc), n_all_over_tol=sum(c["absdiff"] > TOL for c in pc),
                      unpublished_series_computed=[c["key"] for c in rec["cells"] if not c.get("published")])
rec["VERDICT"] = "PASS" if (rec["summary"]["n_gated_over_tol"] == 0 and len(gc) > 0) else "RED"
os.makedirs(ROOT + "/work", exist_ok=True)
sp = ROOT + "/work/S2_series.npz"
flat = {}
for key, s in OUTS.items():
    for c, v in s.items(): flat[f"{key}::{c}"] = np.asarray(v)
flat["ts"] = TS
np.savez(sp + ".tmp.npz", **flat); os.replace(sp + ".tmp.npz", sp)
rec["outputs"] = dict(S2_series=dict(path=sp, sha256=sha(sp), n_arrays=len(flat)))
rec["runtime_s"] = round(time.time() - T0, 1)
rp = ROOT + "/receipts/R0_REPRO.json"
json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
print("R0_REPRO VERDICT=%s gated_cells=%d max_absdiff_gated=%.3e all_cells=%d max_absdiff_all=%.3e receipt_sha256=%s" % (
    rec["VERDICT"], len(gc), rec["summary"]["max_absdiff_gated"], len(pc), rec["summary"]["max_absdiff_all"], sha(rp)), flush=True)
sys.exit(0 if rec["VERDICT"] == "PASS" else 3)
