import numpy as np, json, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r3_integrate")
from integrate import D, SPANS, series, common, sr, dayblocks, boot_sr, report
def show(res):
    print("--- %s | span %s | n=%d ---"%(res["label"],res["span"],res["n"]))
    ks=res["keys"]
    print("  SR      :", " ".join("%s=%+.3f"%(k,res["SR"][k]) for k in ks))
    print("  mean g  :", " ".join("%s=%+.4f"%(k,res["mean_g"][k]) for k in ks))
    print("  corr:")
    print("        "+" ".join("%10s"%k[:10] for k in ks))
    for i,k in enumerate(ks):
        print("  %-10s"%k[:10]+" ".join("%10.4f"%res["corr"][i][j] for j in range(len(ks))))
    print("  N_eff = %.3f of %d"%(res["N_eff"],len(ks)))
    print("  w_opt(|w| sum=1):", " ".join("%s=%+.3f"%(k,res["w_opt"][k]) for k in ks))
    print("  SR_opt = %.4f  CI95 %s   SE=%.3f"%(res["SR_opt"],res["SR_opt_CI95"],res["SE"]))
    print("  SR_equalvol = %.4f  CI95 %s"%(res["SR_equalvol"],res["SR_equalvol_CI95"]))
    print("  SR_zero_corr_ideal = %.4f"%res["SR_zero_corr_ideal"])
    print()
OUT={}
SETS=[
 ("A0+AMI+RS (STD)", ["A0_s42","AMI_lag","RS_s42"], "F23"),
 ("A0+AMI+RS (X1 honest)", ["A0_s42_X1","AMI_lag_X1","RS_s42_X1"], "F23"),
 ("XIB+RS (STD)", ["XIB_s42","RS_s42"], "F23"),
 ("XIB+RS (X1 honest)", ["XIB_s42_X1","RS_s42_X1"], "F23"),
 ("A0+AMI full cycle postwarm (STD)", ["A0_s42","AMI_lag"], "FULL"),
 ("A0+AMI full cycle postwarm (X1)", ["A0_s42_X1","AMI_lag_X1"], "FULL"),
 ("XIB alone vs A0 full (STD)", ["A0_s42","XIB_s42"], "FULL"),
 ("A0+AMI+RS s2027 (X1)", ["A0_s2027_X1","AMI_lag_X1","RS_s2027_X1"], "F23"),
 ("XIB+RS s2027 (X1)", ["XIB_s2027_X1","RS_s2027_X1"], "F23"),
 ("A0+AMI+RS (X2)", ["A0_s42_X2","AMI_lag_X2","RS_s42_X2"], "F23"),
 ("A0+AMI+RS (X3)", ["A0_s42_X3","AMI_lag_X3","RS_s42_X3"], "F23"),
 ("XIB+RS (X2)", ["XIB_s42_X2","RS_s42_X2"], "F23"),
 ("XIB+RS (X3)", ["XIB_s42_X3","RS_s42_X3"], "F23"),
 ("A0+AMI+RS frozen (X1)", ["A0_s42_X1","AMI_lag_X1","RS_s42_X1"], "FROZEN"),
]
for lab,keys,span in SETS:
    try:
        r=report(keys,span,postwarm=True,label=lab); OUT[lab]=r; show(r)
    except Exception as e:
        print("ERR",lab,e)
json.dump(OUT,open("/workspace/uplift_2026-09-11/r3_integrate/PORTFOLIO.json","w"),indent=1)
