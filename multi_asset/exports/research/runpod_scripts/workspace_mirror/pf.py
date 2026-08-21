import json, sys, os
B = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/"
for tag in sys.argv[1:]:
    p = B + "wide_harness_%s.json" % tag
    if not os.path.exists(p):
        print("%-20s 未产出" % tag); continue
    d = json.load(open(p))
    print("== %s  mean=%.4f" % (tag, d["mean_resid_rank_ic"]))
    for f in d.get("per_fold", []):
        print("   year=%-6s best_ep=%-3s best_val=%-8s test_resid=%-8s persist=%-6s" % (
            f.get("year"), f.get("best_epoch"), f.get("best_val_maxic"),
            f.get("resid_rank_ic"), f.get("persistence")))
