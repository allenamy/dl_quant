import numpy as np, hashlib, json
H="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_%s_s%s.npz"
G="/workspace/uplift_2026-09-11/r2_learned/dev/probe_artifacts/w10_ablation_series_GP_A0_%s_s%s.npz"
out={}
for form in ("dyn","fix"):
    for s in ("42","2027"):
        A=np.load(H%(form,s),allow_pickle=True); B=np.load(G%(form,s),allow_pickle=True)
        r={}
        for key in ("d30_n2_c42_rec","d30_n2_c42_W"):
            if key not in A.files or key not in B.files:
                r[key]="ABSENT a=%s b=%s"%(key in A.files, key in B.files); continue
            a=np.asarray(A[key]); b=np.asarray(B[key])
            if a.shape!=b.shape: r[key]="SHAPE %s vs %s"%(a.shape,b.shape); continue
            ident = a.tobytes()==b.tobytes()
            d=np.abs(np.nan_to_num(a)-np.nan_to_num(b))
            r[key]={"bitwise":bool(ident),"shape":list(a.shape),"maxabsdiff":float(d.max()),
                    "sha_a":hashlib.sha256(a.tobytes()).hexdigest()[:16],
                    "sha_b":hashlib.sha256(b.tobytes()).hexdigest()[:16]}
        out["%s_s%s"%(form,s)]=r
print(json.dumps(out,indent=1))
