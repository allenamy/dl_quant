#!/usr/bin/env python3
"""AXIS: cost of deep smoothing (EMA a=0.1 + band 2.5e-4) and 4h cadence / N+24 latency.
READ-ONLY on ~/wide_shadow and ~/dl_quant_live. Writes only under exports/research/uplift_2026-09-11/.
Caliber: y4 = SUM of 5m SIMPLE returns over the 48 bars (pod/producer lineage, E-0904-F). NO expm1.
Scorer is bit-for-bit the producer's: shadow_loop_v3.py L428-441."""
import os, json, glob, time
import numpy as np

WS = "/Users/haosiyu/wide_shadow"; HERE = f"{WS}/fea171"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
os.makedirs(OUT, exist_ok=True)

cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); P = cfg["params"]
ALPHA = P["alpha"]; BAND = P["band"]
syms = cfg["symbols_panel"]
R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
rts = R["ts"].astype(np.int64); RD = R["data"]
CDf = RD[:, :, 0].astype(np.float32)          # ret5, simple
NW = CDf.shape[1]
row_of = {int(t): i for i, t in enumerate(rts)}

def y4_of(A):
    """producer caliber: seg = CDf[pi+1 : ai+1]; sum of finite; NaN if <46 finite."""
    pi = row_of.get(A); ai = row_of.get(A + 14400)
    if pi is None or ai is None: return None
    seg = CDf[pi + 1:ai + 1, :]
    fin = np.isfinite(seg)
    y = np.where(fin, seg, 0).sum(0).astype(np.float64)
    y[fin.sum(0) < 46] = np.nan
    return y

def seg_of(A):
    pi = row_of.get(A); ai = row_of.get(A + 14400)
    if pi is None or ai is None: return None
    return CDf[pi + 1:ai + 1, :].astype(np.float64)   # (48, NW)

def load_w(path):
    z = np.load(path); v = np.zeros(NW)
    v[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
    return v

kw = sorted(int(os.path.basename(p)[:-4]) for p in glob.glob(f"{WS}/state/weights/*.npz"))
cw = sorted(int(os.path.basename(p)[:-4]) for p in glob.glob(f"{WS}/state/weights_combo/*.npz"))
SMK = {A: load_w(f"{WS}/state/weights/{A}.npz") for A in kw}
SMC = {A: load_w(f"{WS}/state/weights_combo/{A}.npz") for A in cw}
SKC = {}; SFC = {}
for p in glob.glob(f"{HERE}/state_H_kc_*.npz"):
    A = int(os.path.basename(p)[len("state_H_kc_"):-4]); SKC[A] = load_w(p)
for p in glob.glob(f"{HERE}/state_H_fc_*.npz"):
    A = int(os.path.basename(p)[len("state_H_fc_"):-4]); SFC[A] = load_w(p)

print(f"king weights {len(kw)} anchors {time.strftime('%m-%d %H',time.gmtime(kw[0]))}..{time.strftime('%m-%d %H',time.gmtime(kw[-1]))}")
print(f"combo weights {len(cw)} anchors {time.strftime('%m-%d %H',time.gmtime(cw[0]))}..{time.strftime('%m-%d %H',time.gmtime(cw[-1]))}")
print(f"kc states {len(SKC)}  fc states {len(SFC)}")
print(f"params alpha={ALPHA} band={BAND} cap_mult={P['cap_mult']} qv4h_min={P['qv4h_min']}")
hl = np.log(0.5)/np.log(1-ALPHA)
print(f"EMA half-life = {hl:.3f} anchors = {hl*4:.2f} h ; mean lag = (1-a)/a = {(1-ALPHA)/ALPHA:.1f} anchors = {(1-ALPHA)/ALPHA*4:.0f} h")

# ---- 1. validate my scorer against the producer's own logged score events ----
score = {}
for ln in open(f"{WS}/shadow_log.jsonl"):
    try: d = json.loads(ln)
    except Exception: continue
    if d.get("e") == "score": score[int(d["anchor_ts"])] = d
mine, theirs, ats = [], [], []
for A in kw:
    if A not in score: continue
    y = y4_of(A)
    if y is None: continue
    g = float((SMK[A] * np.nan_to_num(y, nan=0.0)).sum() * 1e4)
    mine.append(g); theirs.append(score[A]["gross_bps"]); ats.append(A)
mine = np.array(mine); theirs = np.array(theirs)
d = mine - theirs
print(f"\n[VALIDATE] my scorer vs producer score events: n={len(mine)} max|diff|={np.abs(d).max():.4f} bps "
      f"median|diff|={np.median(np.abs(d)):.5f} corr={np.corrcoef(mine,theirs)[0,1]:.8f}")
print(f"           producer gross_bps mean={theirs.mean():.4f} sd={theirs.std(ddof=1):.3f}  mine mean={mine.mean():.4f}")
np.save(f"{OUT}/_validate_anchors.npy", np.array(ats))
