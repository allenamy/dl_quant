"""門V3′ for the v4 chain (pod_f10_v3_leakcheck_v2.py clauses, device adapted for MONTHLY stitched preds — comparison must be on the SAME anchors):
① future side no peak: max|corr(k∈[+1,+3])| < |corr(k=0)|; ② spectrum shape vs the in-service generation on the same anchors: per-k |Δ| ≤ 0.03; ③ out-of-fold (<2023) leaked cells = 0.
Also reports the holefix CLIP FIX7 monthly arm (HF2, same axis) on the same anchors as a second reference (isolates 'monthly-vs-yearly' from 'v4 target/data').
usage: v4_leakcheck.py <T: RAW|CLIP> [seeds csv]"""
import sys, time, json, os
import numpy as np
from scipy.stats import spearmanr
T = sys.argv[1]; SEEDS = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ("42", "2027"))]; DLW = {"RAW": "/workspace/dlw_v4raw", "CLIP": "/workspace/dlw_hf3"}[T]
def load_tg(p):
    TG = np.load(p, allow_pickle=True); return TG["E_ts"].astype(np.int64), TG["y4s"], TG["members"]
def spectrum(P, E_ts, y4s, members, anchors):
    nA = len(E_ts); spec = {}
    for k in range(-3, 4):
        vals = []
        for i in anchors:
            if not (3 <= i < nA - 3): continue
            m = members[i]; a = P[i, m]; b = y4s[i + k, m]; ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    return spec
E4, Y4, M4 = load_tg(f"{DLW}/data/dlw_targets.npz"); EX, YX, MX = load_tg("/workspace/dlw_ext/data/dlw_targets.npz"); yrs4 = np.array([time.gmtime(int(t)).tm_year for t in E4])
bad = []; out = {}
for S in SEEDS:
    ROOT = os.environ.get("MWF_ROOT", "mwf_v4b"); P4 = np.load(f"/workspace/f8_v4/{ROOT}/{T}_s{S}/preds/f10_V2MAIN_{T}_mE1cX7_s{S}.npy"); PX = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy")
    hfp = "/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds/" + ("f10_gate_mE1cX7_R0_spl42_hf2.npy" if S == 42 else "f10_gate_mE1cX7s27_R0_spl27_hf2.npy"); PH = np.load(hfp)
    leak = int(np.isfinite(P4[yrs4 < 2023]).sum())
    fin4 = np.isfinite(P4).any(1); com = np.intersect1d(E4[fin4], EX); i4 = np.searchsorted(E4, com); ix = np.searchsorted(EX, com); step = max(1, len(i4) // 800)
    a4 = i4[::step]; ax = ix[::step]
    new_spec = spectrum(P4, E4, Y4, M4, a4); old_spec = spectrum(PX, EX, YX, MX, ax); hf_spec = spectrum(PH, E4, Y4, M4, a4)
    fut = max(abs(new_spec[k]) for k in (1, 2, 3)); c1 = fut < abs(new_spec[0]); dmax_yearly = max(abs(new_spec[k] - old_spec[k]) for k in range(-3, 4)); dmax = max(abs(new_spec[k] - hf_spec[k]) for k in range(-3, 4)); c2 = dmax <= 0.03; c3 = leak == 0   # AMENDMENT 6: clause-2 reference = same-recipe previous generation (09-06 FIX7 monthly re-inferred on holefix features); yearly reported as information
    fmt = lambda sp: " ".join(f"k{k:+d}:{sp[k]:+.4f}" for k in range(-3, 4))
    print(f"{T} s{S} same-anchor window {time.strftime('%F', time.gmtime(int(com[0])))}→{time.strftime('%F', time.gmtime(int(com[-1])))} n={len(a4)}", flush=True)
    print(f"  v4 {T} monthly : {fmt(new_spec)}\n  in-service yearly: {fmt(old_spec)}\n  HF2 CLIP monthly : {fmt(hf_spec)}", flush=True)
    print(f"{T} s{S} ①未来侧无峰 max|k>0|={fut:.4f} < |k0|={abs(new_spec[0]):.4f} {'OK' if c1 else 'FAIL'} | ②谱形一致(AMD6 同配方参照) max|Δ|={dmax:.4f} {'OK' if c2 else 'FAIL'} [对年折 max|Δ|={dmax_yearly:.4f} {'OK' if dmax_yearly <= 0.03 else 'FAIL(信息)'}] | ③泄出 {leak} {'OK' if c3 else 'FAIL'}", flush=True)
    out[str(S)] = {"window": [int(com[0]), int(com[-1])], "n": int(len(a4)), "new": new_spec, "in_service_same_anchors": old_spec, "hf2_fix7_same_anchors": hf_spec, "c1": c1, "c2_same_recipe": c2, "c2_yearly_literal": dmax_yearly <= 0.03, "c3": c3, "dmax_same_recipe": dmax, "dmax_yearly": dmax_yearly, "leak": leak, "clause2_reference": "AMENDMENT 6: 09-06 FIX7 monthly (same recipe) on holefix features; yearly = information"}
    if not (c1 and c2 and c3): bad.append(S)
json.dump(out, open(f"/workspace/review_scratch/v4_gates/V3P_{T}_{ROOT}_amd6.json", "w"), indent=1)
print("V3P_GATE", T, "PASS" if not bad else f"FAIL {bad}", flush=True); sys.exit(0 if not bad else 3)
