#!/usr/bin/env python3
"""Phase 2 chain launcher (one serial chain = one process). Writes only under /workspace/uplift_r2_2026-09-13/P2.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_run.py PATH,HOME,LC_CTYPE \
         --tag T --king SLOW_v4 --f10 v4RAW_s42 --seed 42 --universe pit --policy withhold --start 2025-03-01T00:00:00Z --n 12 [--record-from ISO] [--end ISO]"""
import os, sys, json, time, calendar, argparse, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 and "=" not in sys.argv[1] and not sys.argv[1].startswith("--") else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
ap = argparse.ArgumentParser()
for k in ("--tag", "--king", "--f10", "--seed", "--universe", "--policy", "--start"): ap.add_argument(k, required=True)
ap.add_argument("--n", type=int); ap.add_argument("--end"); ap.add_argument("--record-from"); ap.add_argument("--fold-override"); ap.add_argument("--combo-launch", default="fork")
a = ap.parse_args(sys.argv[2:])
assert a.universe in ("pit", "pins") and a.policy in ("withhold", "serve_all") and a.seed in ("42", "2027")
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"   # fork safety + one core per chain (set after the whitelist check, recorded)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import p2_driver as D
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
S = ts(a.start); assert S % 14400 == 0
E = ts(a.end) if a.end else S + (a.n - 1) * 14400
anchors = list(range(S, E + 1, 14400))
arm = {"tag": a.tag, "king_oof": a.king, "f10_oof": a.f10, "f10_seed": a.seed, "universe": a.universe, "serve_policy": a.policy,
       "start": D.iso(S), "end": D.iso(E), "n_anchors": len(anchors), "record_from": a.record_from, "combo_launch": a.combo_launch}
if a.fold_override: arm["fold_table_override"] = json.loads(a.fold_override)
rh = f"{D.P2}/work/runs/{a.tag}"; D.under(rh); os.makedirs(rh, exist_ok=True)
out = D.under(f"{D.P2}/receipts/RUN_{a.tag}.json")
t0 = time.time()
nv0 = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
G = D.Globals(arm); print(json.dumps({"globals_load_s": G.load_s, "arm": arm, "king_fold_table": {str(k): D.iso(v) for k, v in G.kt["label_end"].items()},
                                      "f10_yearly": {str(k): D.iso(v) for k, v in G.ft["yearly_label_end"].items()}}), flush=True)
recs = D.run_chain(arm, G, anchors, rh, out, record_from=ts(a.record_from) if a.record_from else None, log_every=1 if len(anchors) <= 50 else 50)
nv1 = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
doc = json.load(open(out)); doc["nvidia_smi_before_after"] = [nv0, nv1]; doc["wall_s"] = round(time.time() - t0, 1); doc["launcher_sha256"] = D.sha(os.path.abspath(__file__))
doc["argv"] = sys.argv; doc["env"] = dict(os.environ)
json.dump(doc, open(out + ".tmp", "w")); os.replace(out + ".tmp", out)
tt = [r["timing_s"]["total"] for r in recs]
print("P2_RUN_DONE", a.tag, "n", len(recs), "wall_s", doc["wall_s"], "per_anchor_total_s mean", round(float(np.mean(tt)), 3) if tt else None, flush=True)
