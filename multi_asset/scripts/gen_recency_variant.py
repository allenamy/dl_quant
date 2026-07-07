"""STEP-3 recency-lever variant generator (prepared; run after the beta-healthy baseline).
R4 showed recent windows lift specific months (2025-10 +0.095; 2026-02 recent-3mo > full). Test whether a
SHORTER recent train window (with patience10 to stay beta-healthy) lifts the beta-healthy baseline on the
months where recency helped -- leak-safe, same caliber, gated on beta-healthy + shuffle-null + net-of-cost.
Usage: python multi_asset/scripts/gen_recency_variant.py <YYYY-MM> <train_days>
Default train_days candidates to sweep: 120, 180, 250 (vs the baseline 450/550). patience10/epochs32 always.
Output -> configs/recency/rec_<YYYY_MM>_t<td>.json
"""
import json, sys, os
tm=sys.argv[1]; td=int(sys.argv[2]) if len(sys.argv)>2 else 180
y,mo=tm.split("-")
base=json.load(open(f"configs/walkforward/wf_{y}_{mo}.json"))
t=base["training"]
t["train_days"]=td; t["patience"]=10; t["epochs"]=32
base["model"]["_comment"]=f"STEP3 RECENCY variant: train_days={td} (recent window) + patience10. Test recency lift on beta-healthy baseline."
base["output_dir"]=f"experiments/recency/rec_{y}_{mo}_t{td}"
os.makedirs("configs/recency",exist_ok=True)
out=f"configs/recency/rec_{y}_{mo}_t{td}.json"
json.dump(base,open(out,"w"),indent=2)
print(out)
