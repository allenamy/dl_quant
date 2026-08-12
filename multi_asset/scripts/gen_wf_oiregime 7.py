"""Generate an OI-REGIME walk-forward config for one test month (TARGET WINDOW 2025-08..2026-05).

Optimized arch per the 2026-06-26 root-cause dig: base adaptive (REG_arch + perp residual +
regime FiLM + regime bias) PLUS use_oi_regime (causal positioning features funding/OI/L/S ->
regime FiLM, d_prior=14). Addresses the LOCATED root cause: transfer failure across the
positioning-regime inversion (funding/OI/L/S flip 2026-02+).

Cache: OI-augmented (regime_prior 6->14). <=2025-09 -> npzv4_dual_oi (trainer train_v2arch),
2025-10+ -> npz_v2arch_oi (trainer train_dual_lob).

train_days configurable (R4: recency is a conditional lever). Usage:
  python multi_asset/scripts/gen_wf_oiregime.py <YYYY-MM> [train_days]
Default train_days=700.  Output -> configs/wf_oi/wfoi_<YYYY_MM>[_t<days>].json
"""
import json, sys, os
tm=sys.argv[1]
train_days=int(sys.argv[2]) if len(sys.argv)>2 else 700
y,mo=tm.split("-")
if tm <= "2025-09":
    base="configs/npzv4_dual/perp_dp32_a02_adaptive_2025_04.json"; npz="data/npzv4_dual_oi"; trainer="train_v2arch"
else:
    base="configs/v2arch/dp32_adaptive_2026_05.json"; npz="data/npz_v2arch_oi"; trainer="train_dual_lob"
d=json.load(open(base))
d["data"]["npz_dir"]=npz
d["data"]["include_regime_prior"]=True
m=d["model"]
m["d_prior"]=14
m["use_regime_film"]=True
m["use_rich_regime"]=True      # rebuild FiLM to accept wider regime input
m["use_oi_regime"]=True        # regime FiLM ALSO consumes regime_prior[14] (positioning)
m["use_regime_bias"]=True
m["_comment"]=(f"WF OI-REGIME: rolling-train {train_days}d before {tm}, test {tm}. "
              f"cache={npz}. use_oi_regime (positioning FiLM) addresses regime-inversion transfer failure.")
t=d["training"]
t["fold_test_starts"]=[f"{tm}-10"]
t["train_days"]=train_days; t["val_days"]=45; t["test_days"]=28
t["patience"]=10; t["embargo_days"]=1   # patience 10: sigma-gate crossing slower on perp (memory note)
t["num_workers"]=0; t["preload"]=True
tag=f"{y}_{mo}" + (f"_t{train_days}" if train_days!=700 else "")
d["output_dir"]=f"experiments/wf_oi/wfoi_{tag}"
os.makedirs("configs/wf_oi",exist_ok=True)
out=f"configs/wf_oi/wfoi_{tag}.json"
json.dump(d,open(out,"w"),indent=2)
print(f"{out} | cache={npz} | trainer={trainer} | test={tm}-10 | train_days={train_days}")
