import json, os, glob
R = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
print("=== #5 甲 PRODUCTION_FOLD_PROVENANCE (receipt) ===")
d = json.load(open(R + "/wideA_s2_y24_PRODFOLD_corrfund_v1_val30/PRODUCTION_FOLD_PROVENANCE.json"))
for k, v in d.items():
    if k == "harness_metrics_are_not_oos":
        continue
    s = json.dumps(v, ensure_ascii=False)
    print("  %-28s %s" % (k, s[:200] + ("…" if len(s) > 200 else "")))
print("\n  files:", sorted(os.listdir(R + "/wideA_s2_y24_PRODFOLD_corrfund_v1_val30")))
print("\n=== embargo sensitivity: clean s2 emb8 vs emb10 ===")
for tag in ("s2_y24_5yr_corrfund_v1", "s2_y24_5yr_corrfund_emb10"):
    f = R + "/wide_harness_%s.json" % tag
    if not os.path.exists(f):
        cand = glob.glob(R + "/wide_harness_*%s*.json" % tag.split("_")[-1])
        f = cand[0] if cand else None
    if not f:
        print("  %-30s (json not found)" % tag); continue
    j = json.load(open(f))
    print("  %-30s ens_resid_ic=%.4f  resid_rank_ic=%.4f  IR=%.2f  persist=%.4f  raw_rank=%.4f"
          % (tag, j["mean_ensemble_resid_ic"], j["mean_resid_rank_ic"], j["mean_resid_ic_ir"],
             j["mean_persistence"], j["mean_raw_rank_ic"]))
