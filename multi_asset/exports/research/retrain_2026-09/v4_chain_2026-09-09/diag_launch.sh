#!/bin/bash
cd /workspace/review_scratch; L=/workspace/diag_legs/logs; mkdir -p $L /workspace/diag_legs/mwf_D2 /workspace/diag_legs/mwf_D3
/workspace/venv/bin/python diag_legs_setup.py > $L/setup.log 2>&1 && /workspace/venv/bin/python -m py_compile pod_f10_train_monthly_diag.py && echo "diag compiles" >> $L/setup.log || { echo SETUP_FAIL >> $L/setup.log; exit 1; }
D2="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_hf3 F10_OUT=/workspace/diag_legs F10_GATE_JSON=SKIP MWF_OUT=/workspace/diag_legs/mwf_D2 EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 MONTHS=202507 /workspace/venv/bin/python /workspace/review_scratch/pod_f10_train_monthly_diag.py"
D3="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext F10_GATE_JSON=SKIP MWF_OUT=/workspace/diag_legs/mwf_D3 EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 MONTHS=202507 /workspace/venv/bin/python /workspace/review_scratch/pod_f10_train_monthly_diag.py"
echo "CMD[DIAG D2 v4data+extlegs 202507] $(date -u +%FT%TZ): $D2" >> v4_commands.txt; nohup $D2 > $L/D2.log 2>&1 & echo "PID[DIAG D2] $!" >> v4_commands.txt
echo "CMD[DIAG D3 extdata 202507] $(date -u +%FT%TZ): $D3" >> v4_commands.txt; nohup $D3 > $L/D3.log 2>&1 & echo "PID[DIAG D3] $!" >> v4_commands.txt
/workspace/venv/bin/python - > $L/quickstats.log 2>&1 <<PY
import numpy as np, time
from scipy.stats import spearmanr
TG=np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True); E=TG["E_ts"].astype(np.int64); Y=TG["y4s"]; M=TG["members"]; yrs=np.array([time.gmtime(int(t)).tm_year for t in E])
R4=np.load("/workspace/f8_v4/mwf/RAW_s42/preds/f10_V2MAIN_RAW_mE1cX7_s42.npy"); C4=np.load("/workspace/f8_v4/mwf/CLIP_s42/preds/f10_V2MAIN_CLIP_mE1cX7_s42.npy")
H42=np.load("/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds/f10_gate_mE1cX7_R0_spl42_hf2.npy"); H27=np.load("/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds/f10_gate_mE1cX7s27_R0_spl27_hf2.npy")
idx=np.where(yrs>=2025)[0][::4]; cc=[];hh=[];k42=[];k27=[];kr=[];kc=[]
for i in idx:
    m=M[i]; y=Y[i,m]; a=R4[i,m]; b=C4[i,m]; h=H42[i,m]; g=H27[i,m]; ok=np.isfinite(y)&np.isfinite(a)&np.isfinite(b)&np.isfinite(h)&np.isfinite(g)
    if ok.sum()<30: continue
    cc.append(spearmanr(a[ok],b[ok]).correlation); hh.append(spearmanr(h[ok],g[ok]).correlation); k42.append(spearmanr(h[ok],y[ok]).correlation); k27.append(spearmanr(g[ok],y[ok]).correlation); kr.append(spearmanr(a[ok],y[ok]).correlation); kc.append(spearmanr(b[ok],y[ok]).correlation)
print(f"2025+ (n={len(cc)}): corr(v4RAW,v4CLIP) {np.mean(cc):+.3f} | corr(HF2 s42, HF2 s2027) {np.mean(hh):+.3f} | k0 IC: HF2 s42 {np.mean(k42):+.4f} HF2 s2027 {np.mean(k27):+.4f} v4RAW {np.mean(kr):+.4f} v4CLIP {np.mean(kc):+.4f}")
print("QUICKSTATS_DONE")
PY
