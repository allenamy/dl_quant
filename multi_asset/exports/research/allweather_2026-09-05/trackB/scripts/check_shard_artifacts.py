"""check_shard_artifacts.py — integrity of the mE1 seed-2027 shard artifacts after the 2026-09-05 ~15:08Z /workspace quota incident (loadability, sizes, sha, config, results json)."""
import numpy as np, json, torch, os, hashlib, sys, glob
B = "/workspace/review_scratch/allweather_trackB/mwf_s2027"
for k in range(4):
    d = f"{B}/shard{k}"; rf = f"{d}/results/f10_V2MAIN_mE1_s2027.json"; R = json.load(open(rf)) if os.path.exists(rf) else None
    for pf in sorted(glob.glob(f"{d}/preds_fold/mE1_*.npz")):
        ym = int(os.path.basename(pf)[4:10]); pt = f"{d}/models/mE1_{ym}.pt"; cf = f"{d}/models/mE1_{ym}_config.json"
        z = np.load(pf); P = z["P"]; C = json.load(open(cf)); st = torch.load(pt, map_location="cpu")
        print(f"shard{k} {ym}: npz {os.path.getsize(pf)} B P{P.shape} finite {int(np.isfinite(P).sum())} first_te {int(z['first_te'])} last_te {int(z['last_te'])} | pt {os.path.getsize(pt)} B tensors {len(st)} sha {hashlib.sha256(open(pt, 'rb').read()).hexdigest()[:12]} | config seed_fold {C['seed_fold']} causality {C['causality_ok']} finished {C['finished_utc']} wall {C['wall_clock_s']} | results json folds {list(R['folds']) if R else None} in_results {str(ym) in (R['folds'] if R else {})}")
    pr = f"{d}/preds/f10_V2MAIN_mE1_s2027.npy"
    if os.path.exists(pr): print(f"   shard{k} stitched partial {os.path.getsize(pr)} B finite rows {int(np.isfinite(np.load(pr)).any(1).sum())}")
print("CHECK_DONE")
