import json
B="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/"
for tag in ("rb32_yr24_s42","ch53_yr24_s42"):
    d=json.load(open(B+f"wide_harness_{tag}.json"))
    print(f"{tag}: resid={d['mean_resid_rank_ic']}  IR={d['mean_resid_ic_ir']}  raw={d['mean_raw_rank_ic']}  persist={d.get('mean_persistence')}")
    print(f"   per-fold resid: {d['per_fold_resid_ic']}")
