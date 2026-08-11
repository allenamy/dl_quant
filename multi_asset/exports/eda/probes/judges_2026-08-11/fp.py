"""面板指纹: 用确定性子采样算跨实现稳定的特征值, 与本机 panel_0731 对照。"""
import numpy as np, sys, os
p = sys.argv[1]
z = np.load(p, allow_pickle=True)
print("PATH", p)
print("KEYS", sorted(z.files))
CH = z["CH"]; print("CH", CH.shape, CH.dtype)
print("NCH", len(z["ch_names"]), "SYM", len(z["symbols"]), "T", len(z["ts"]))
print("TS0", int(z["ts"][0]), "TSN", int(z["ts"][-1]))
rows = np.arange(0, CH.shape[0], 97)
print("CH_SUB_MEAN %.8f" % float(np.nanmean(CH[rows])))
print("CH_SUB_STD  %.8f" % float(np.nanstd(CH[rows])))
for k in ("YR24", "Y24", "MEMBER110", "CL24"):
    if k in z.files:
        a = z[k]
        if a.dtype == bool:
            print("%s_MEAN %.8f" % (k, float(a.mean())))
        else:
            sub = a[rows]
            print("%s_FIN %.6f  %s_STD %.8f  %s_MEAN %.10f" % (
                k, float(np.isfinite(a).mean()), k, float(np.nanstd(sub)), k, float(np.nanmean(sub))))
print("BASELINE", [str(x) for x in z["baseline_cols"]] if "baseline_cols" in z.files else None)
