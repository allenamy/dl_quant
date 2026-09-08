import numpy as np, json, calendar, time
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
def L(p):
    z=np.load(p,allow_pickle=True); cfg=json.loads(str(z["config_json"]))
    return {c:z["d30_n2_c42_rec"][:,i] for i,c in enumerate(COLS)}, z["d30_n2_c42_W"], cfg
B,WB,cb=L(f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz")
C,WC,cc=L(f"{PA}/w10_ablation_series_G_FIX7_UCRYPTO.npz")
print("=== 配置对账(必须只差 UMASK_NPZ) ===")
diff={k:(cb.get(k),cc.get(k)) for k in set(cb)|set(cc) if cb.get(k)!=cc.get(k)}
for k,v in diff.items(): print(f"  {k}: BASE={str(v[0])[:70]}  CRYPTO={str(v[1])[:70]}")
print(f"  ⇒ 差异键数 {len(diff)}")
ts=B["ts"].astype(np.int64)
assert np.array_equal(ts, C["ts"].astype(np.int64)), "锚轴不同"
print(f"  锚轴逐位相同 n={len(ts)}")
T25=calendar.timegm((2025,1,1,0,0,0)); T26=calendar.timegm((2026,1,1,0,0,0))
early=ts<T25
print("\n=== ★ 冻结自检 §A3.3-3: 2022-2024 必须逐位相等 ===")
ok=True
for c in ("net_ex","pnl_ex","carry_ex","cost_ex","gross_total","turnover","nsel"):
    d=float(np.nanmax(np.abs(np.nan_to_num(B[c][early])-np.nan_to_num(C[c][early]))))
    if d!=0.0: ok=False
    print(f"  {c:12s} maxabs {d:.3e}")
dW=float(np.nanmax(np.abs(np.nan_to_num(WB[early])-np.nan_to_num(WC[early]))))
print(f"  {'权重 W':12s} maxabs {dW:.3e}")
print(f"  ⇒ 自检3 {'PASS' if ok and dW==0.0 else '★ FAIL — 停止, 不报书层数字'}")
print("\n=== 2025 段(mask 亦相同, 应同样逐位相等) ===")
m25=(ts>=T25)&(ts<T26)
d25=float(np.nanmax(np.abs(np.nan_to_num(B["net_ex"][m25])-np.nan_to_num(C["net_ex"][m25]))))
print(f"  net_ex maxabs {d25:.3e}  ⇒ {'一致' if d25==0.0 else '★ 不一致'}")
print("\n=== 2026 段(应有差异) ===")
m26=ts>=T26
d26=float(np.nanmax(np.abs(np.nan_to_num(B["net_ex"][m26])-np.nan_to_num(C["net_ex"][m26]))))
print(f"  net_ex maxabs {d26:.3e} | 非零锚 {int((np.abs(np.nan_to_num(B['net_ex'][m26])-np.nan_to_num(C['net_ex'][m26]))>0).sum())}/{int(m26.sum())}")
print(f"  nsel 均: BASE {B['nsel'][m26].mean():.1f} vs CRYPTO {C['nsel'][m26].mean():.1f}")
