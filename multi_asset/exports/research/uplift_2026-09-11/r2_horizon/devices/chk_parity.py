import numpy as np
A=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
B=np.load("/workspace/uplift_2026-09-11/r2_horizon/out/E0_PARITY.npz",allow_pickle=True)
for ka,kb in [("d30_n2_c42_rec","rec"),("d30_n2_c42_W","W")]:
    x=np.asarray(A[ka]); y=np.asarray(B[kb])
    bw = x.shape==y.shape and x.dtype==y.dtype and x.tobytes()==y.tobytes()
    print(kb,x.shape,x.dtype,"BITWISE" if bw else "DIFF mean|d|=%.6g max=%.6g"%(np.nanmean(np.abs(x-y)),np.nanmax(np.abs(x-y))))
