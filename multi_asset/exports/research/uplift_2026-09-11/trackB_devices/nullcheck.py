import numpy as np
A=np.load("/workspace/uplift_2026-09-11/dev_tb/probe_artifacts/w10_ablation_series_NULL_A1_dyn_s42.npz",allow_pickle=True)
B=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A1_dyn_s42.npz",allow_pickle=True)
bad=0
for k in ("d30_n2_c42_rec","d30_n2_c42_W","S0_rec","S0_W","legs_king","legs_fund","legs_rev24","legs_ts"):
    if k not in A.files or k not in B.files: print("MISSING",k); bad+=1; continue
    a,b=np.asarray(A[k]),np.asarray(B[k])
    eq=(a.shape==b.shape) and np.array_equal(a,b)
    print(f"{k:18s} shape {str(a.shape):14s} bitwise_equal={eq}" + ("" if eq else f"  maxabs={np.max(np.abs(a-b)):.3e}"))
    bad += (not eq)
print("NULL TEST", "PASS (bitwise identical)" if bad==0 else f"FAIL ({bad})")
