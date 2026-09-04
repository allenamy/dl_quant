"""默认路径逐位等价: 补丁后默认 env 运行(w10_ablation_series_w10_kc_eq_s42.npz) vs 正典基线(w10_canonpred_s42.npz): 两臂 rec 矩阵全等 + config 除 KSVOL 键外全等."""
import numpy as np, json
a=np.load("probe_artifacts/w10_ablation_series_w10_kc_eq_s42.npz",allow_pickle=True); b=np.load("probe_artifacts/w10_canonpred_s42.npz",allow_pickle=True)
ca=json.loads(str(a["config_json"])); cb=json.loads(str(b["config_json"]))
ca2={k:v for k,v in ca.items() if not k.startswith("KSVOL")}
print("config equal (ex KSVOL keys):", ca2==cb, "| diff:", {k:(ca2.get(k),cb.get(k)) for k in set(ca2)|set(cb) if ca2.get(k)!=cb.get(k)})
cols=[str(c) for c in a["cols"]]; print("cols equal:", cols==[str(c) for c in b["cols"]])
for arm in ("S0","d30_n2_c42"):
    ra=a[f"{arm}_rec"]; rb=b[f"{arm}_rec"]
    print(f"{arm}: shape {ra.shape} vs {rb.shape} | bitwise equal = {ra.shape==rb.shape and np.array_equal(np.nan_to_num(ra,nan=-9e9),np.nan_to_num(rb,nan=-9e9))}")
    if ra.shape==rb.shape:
        for c in ("net_ex","w3_king","turnover"):
            x=ra[:,cols.index(c)]; y=rb[:,cols.index(c)]; print(f"   {c}: max|Δ| = {np.nanmax(np.abs(x-y)):.3e}")
print("EQ_DONE")
