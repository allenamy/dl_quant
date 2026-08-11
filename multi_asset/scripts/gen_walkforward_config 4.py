"""Generate an adaptive walk-forward config for one test month.
Picks cache by month: npzv4_dual (<=2025-09, X=72 base adaptive) else npz_v2arch (X=88 base).
Rolling train ~700d before the test month, embargo 1d, patience 6. Output -> configs/walkforward/wf_<YYYY_MM>.json
"""
import json, sys, os
tm=sys.argv[1]  # e.g. 2024-06
y,mo=tm.split("-")
# cache + base template selection
if tm <= "2025-09":
    base="configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json"; npz="data/npzv4_dual"; trainer="train_v2arch"
else:
    base="configs/v2arch/dp32_adaptive_2026_05.json"; npz="data/npz_v2arch"; trainer="train_dual_lob"
d=json.load(open(base))
d["data"]["npz_dir"]=npz
t=d["training"]
t["fold_test_starts"]=[f"{tm}-10"]      # test starts mid-month (consistent w/ the fold configs)
t["train_days"]=700; t["val_days"]=45; t["test_days"]=28; t["patience"]=6; t["embargo_days"]=1
t["num_workers"]=0; t["preload"]=True
d["model"]["_comment"]=f"WALK-FORWARD adaptive: rolling-train 700d before {tm}, test {tm}. cache={npz}."
d["output_dir"]=f"experiments/walkforward/wf_{y}_{mo}"
os.makedirs("configs/walkforward",exist_ok=True)
out=f"configs/walkforward/wf_{y}_{mo}.json"
json.dump(d,open(out,"w"),indent=2)
print(f"{out} | cache={npz} | trainer={trainer} | test={tm}-10")
