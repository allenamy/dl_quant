"""verify_artifacts.py — dl_monthly_wf: load-check every fold artifact (after the 2026-09-05 08:0xZ /workspace quota incident, and before the final report).
For each variant: per fold config json / model .pt / preds_fold .npz must load; P rows == nA − first_te; finite rows in the test month == n_test; first_te/last_te match the
calendar month; results json folds == the set of complete folds; the stitched ext-grid npy rows of each finished month must be bitwise equal to the fold's P rows.
Partial/corrupt artifacts are reported (and deleted with --fix so the trainer's resume re-runs that fold). Exit 0 = consistent."""
import os, sys, json, time, glob
import numpy as np, torch
R = "/workspace/review_scratch/dl_monthly_wf"; FIX = "--fix" in sys.argv
E = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64); nA = len(E)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E])
MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
bad = 0; summary = {}
for tag in ("mE60", "mE1"):
    done = []; partial = []
    for m in MONTHS:
        te = np.where(ym == m)[0]; f0, l0 = int(te[0]), int(te[-1])
        paths = {"cfg": f"{R}/models/{tag}_{m}_config.json", "pt": f"{R}/models/{tag}_{m}.pt", "npz": f"{R}/preds_fold/{tag}_{m}.npz"}
        ex = {k: os.path.exists(p) for k, p in paths.items()}
        if not any(ex.values()): continue
        ok = True; msg = []
        try:
            cfg = json.load(open(paths["cfg"])); assert cfg["fold"] == m and cfg["causality_ok"] and cfg["n_test"] == len(te), cfg.get("fold"); msg.append(f"cfg ok wall {cfg['wall_clock_s']}s")
        except Exception as e: ok = False; msg.append(f"cfg BAD {type(e).__name__}: {str(e)[:50]}")
        try:
            sd = torch.load(paths["pt"], map_location="cpu"); assert len(sd) == 7 and all(torch.isfinite(v).all() for v in sd.values()); msg.append("pt ok")
        except Exception as e: ok = False; msg.append(f"pt BAD {type(e).__name__}: {str(e)[:50]}")
        try:
            z = np.load(paths["npz"]); P = z["P"]; ft, lt = int(z["first_te"]), int(z["last_te"])
            assert ft == f0 and lt == l0 and P.shape == (nA - f0, 829), (ft, lt, P.shape)
            fin_month = int(np.isfinite(P[:l0 - f0 + 1]).any(1).sum()); assert fin_month == len(te), fin_month
            msg.append(f"npz ok P {P.shape} test-month finite rows {fin_month}/{len(te)}")
        except Exception as e: ok = False; msg.append(f"npz BAD {type(e).__name__}: {str(e)[:50]}")
        (done if ok else partial).append(m); print(f"{tag} {m}: {'OK' if ok else 'PARTIAL/BAD'} | " + "; ".join(msg))
        if not ok and FIX:
            for k, p in paths.items():
                if os.path.exists(p): os.remove(p); print(f"  removed {p}")
    rp = f"{R}/results/f10_V2MAIN_{tag}_s42.json"; rj = None
    try: rj = json.load(open(rp)); rf = sorted(int(k) for k in rj["folds"])
    except Exception as e: rf = None; print(f"{tag}: results json BAD/MISSING ({type(e).__name__})")
    sp = f"{R}/preds/f10_V2MAIN_{tag}_s42.npy"; stitched_ok = None
    try:
        S = np.load(sp); assert S.shape == (nA, 829)
        eqs = []
        for m in done:
            te = np.where(ym == m)[0]; f0, l0 = int(te[0]), int(te[-1]); z = np.load(f"{R}/preds_fold/{tag}_{m}.npz"); eqs.append(bool(np.array_equal(S[f0:l0 + 1], z["P"][:l0 - f0 + 1], equal_nan=True)))
        other = np.ones(nA, bool)
        for m in done: other[ym == m] = False
        stitched_ok = all(eqs) and not np.isfinite(S[other]).any()
        print(f"{tag}: stitched npy rows==fold P for {sum(eqs)}/{len(eqs)} finished months; no finite rows outside finished months: {not np.isfinite(S[other]).any()}")
    except Exception as e: print(f"{tag}: stitched npy BAD/MISSING ({type(e).__name__}: {str(e)[:60]})")
    consistent = (rf == sorted(done)) and (stitched_ok is True) and not partial
    if rf is not None and rf != sorted(done):
        print(f"{tag}: results json folds {rf} != complete folds {sorted(done)}")
        if FIX and rj is not None:
            rj["folds"] = {str(m): rj["folds"][str(m)] for m in done if str(m) in rj["folds"]}; json.dump(rj, open(rp, "w"), indent=1); print(f"  results json trimmed to {sorted(done)}")
    summary[tag] = {"complete": done, "partial": partial, "results_json_folds": rf, "stitched_consistent": stitched_ok, "consistent": consistent}
    bad += 0 if consistent else 1
    print(f"{tag}: complete {len(done)} folds {done[0] if done else None}..{done[-1] if done else None}; partial {partial}; CONSISTENT={consistent}")
json.dump(summary, open(f"{R}/logs/verify_artifacts_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json", "w"), indent=1)
print("VERIFY", "OK" if bad == 0 else f"PROBLEMS {bad}"); sys.exit(0 if bad == 0 else 1)
