import json, os, sys
B = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/"
for tag in sys.argv[1:]:
    p = B + "wide_harness_%s.json" % tag
    if not os.path.exists(p):
        print("%-22s 未产出" % tag); continue
    d = json.load(open(p)); pf = d.get("per_fold", [])
    print("%-22s resid=%.4f IR=%.2f raw=%.4f persist=%.3f" % (
        tag, d["mean_resid_rank_ic"], d.get("mean_resid_ic_ir") or 0,
        d["mean_raw_rank_ic"], d.get("mean_persistence") or 0))
    print("   folds=%s years=%s params=%s" % (
        d["per_fold_resid_ic"], [f.get("year") for f in pf],
        pf[0].get("n_params") if pf else None))
