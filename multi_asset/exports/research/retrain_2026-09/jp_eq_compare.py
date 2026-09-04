"""默认路径逐位等价: 补丁后默认 env 运行 vs 正典基线, net_ex/w3 列全等."""
import numpy as np, sys
a=np.load("probe_artifacts/w10_kc_eq_s42.npz",allow_pickle=True); b=np.load("probe_artifacts/w10_canonpred_s42.npz",allow_pickle=True)
same_ts=np.array_equal(a["ts"],b["ts"]); print("ts equal:",same_ts, len(a["ts"]), len(b["ts"]))
ca=[str(c) for c in a["cols"]]; cb=[str(c) for c in b["cols"]]; print("cols equal:",ca==cb)
ra=a["d30_n2_c42_rec"]; rb=b["d30_n2_c42_rec"]
for c in ("net_ex","w3_king","gross","turn"):
    if c in ca and c in cb:
        x=ra[:,ca.index(c)]; y=rb[:,cb.index(c)]; print(f"{c}: bitwise equal = {np.array_equal(x,y)} | max|Δ| = {np.nanmax(np.abs(x-y)):.3e}")
print("EQ_DONE")
