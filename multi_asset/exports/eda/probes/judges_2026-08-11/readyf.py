import json,glob
for f in sorted(glob.glob("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/wide_harness_*yf24*.json")):
    d=json.load(open(f))
    tag=f.split("wide_harness_")[1][:-5]
    print(f"{tag}: resid={d['mean_resid_rank_ic']}  folds={d['per_fold_resid_ic']}  raw={d['mean_raw_rank_ic']}")
