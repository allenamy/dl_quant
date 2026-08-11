"""Export production adaptive predictions (all folds, RAW perp y) to one CSV for backtest."""
from __future__ import annotations
import numpy as np, glob, csv, os, sys
FOLDS=[("npzv4_dual","perp_dp32_a02_adaptive_2024_10","2024-10"),
       ("npzv4_dual","perp_dp32_a02_adaptive_2025_04","2025-04"),
       ("npzv4_dual","perp_dp32_a02_adaptive_2025_08","2025-08"),
       ("v2arch_dp32","dp32_adaptive_2025_12","2025-12"),
       ("v2arch_dp32","dp32_adaptive_2026_02","2026-02"),
       ("v2arch_dp32","dp32_adaptive_2026_05","2026-05")]
out=sys.argv[1] if len(sys.argv)>1 else "exports/adaptive_production_allfolds.csv"
os.makedirs(os.path.dirname(out),exist_ok=True)
rows=0
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["fold","timestamp_us","pred_q50_raw","target_raw","ckpt"])
    for sub,name,fold in FOLDS:
        for ck in ["test_preds.npz","ema_test_preds.npz"]:
            pth=f"experiments/{sub}/{name}/fold_0/{ck}"
            if not os.path.exists(pth): continue
            z=np.load(pth); pr=z["predictions"]; q=(pr[:,1] if pr.ndim==2 else pr)
            ys=z.get("y_sigma",np.array(1.0)); ym=z.get("y_median",np.array(0.0))
            qr=q*float(ys)+float(ym); tr=z["targets"]*float(ys)+float(ym)
            m=z["mask"].astype(bool) if "mask" in z else np.ones(q.shape,bool)
            ts=z["timestamps"] if "timestamps" in z else np.zeros(q.shape,np.int64)
            tag="ema" if "ema" in ck else "best"
            for i in np.where(m)[0]:
                w.writerow([fold,int(ts[i]),f"{qr[i]:.8e}",f"{tr[i]:.8e}",tag]); rows+=1
print(f"wrote {out} ({rows} rows)")
