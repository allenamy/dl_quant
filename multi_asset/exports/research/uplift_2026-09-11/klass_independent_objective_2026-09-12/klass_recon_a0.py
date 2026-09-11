"""ENV WHITELIST (E-0826-D) = EMPTY SET. Reconcile my A0 read against the brief's 0.6342 / 1.2912 / n=9138."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ]
import numpy as np, itertools
B="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/"
CAP=1788120000
for seat,seed in itertools.product(["dyn","fix"],["42","2027"]):
    p=f"{B}w10_ablation_series_V4_A0_{seat}_s{seed}.npz"
    try: a=np.load(p,allow_pickle=True)
    except Exception as e: print(seat,seed,"MISSING"); continue
    cols=list(a["cols"]); ci={c:i for i,c in enumerate(cols)}
    for key in ["S0_rec","d30_n2_c42_rec"]:
        r=a[key]; ts=r[:,ci["ts"]].astype(np.int64)
        k=(np.arange(len(ts))>=900)&(ts<=CAP)
        g=r[k,ci["net_ex"]]/r[k,ci["gross_total"]]
        print(f"{seat:3s} s{seed:4s} {key:16s} n={k.sum():5d} meang={g.mean():+.4f} SR={g.mean()/g.std(ddof=1)*np.sqrt(2190):+.4f}")
