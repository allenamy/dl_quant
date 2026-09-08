import numpy as np, calendar, time
from scipy.stats import spearmanr
A=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)
E=A["E_ts"].astype(np.int64); MEM=A["members"]; Y=A["y4s"]; nA=len(E)
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
TF="/workspace/review_scratch/trainfrac/replay/dev_alt/probe_artifacts"
G_="/workspace/review_scratch/dl_monthly_gate/replay/dev_alt/probe_artifacts"
d="/workspace/review_scratch/allweather_trackB/replay/dev_alt/f8_2026-08-22/preds"
ARMS={"yearly_s42":(f"{G_}/w10_ablation_series_BASE_s42.npz",None),
      "CONST42":(f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz","f10_gate_mE1c_R0_spl42.npy"),
      "FIX7":(f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz","f10_gate_mE1cX7_R0_spl42.npy"),
      "X7FULL":(f"{TF}/w10_ablation_series_G_mE1x7full_R0_spl42.npz","f10_gate_mE1x7full_R0_spl42.npy"),
      "X6FULL":(f"{TF}/w10_ablation_series_G_mE1x6full_R0_spl42.npz","f10_gate_mE1x6full_R0_spl42.npy")}
D={};W={}
for k,(p,_) in ARMS.items():
    z=np.load(p,allow_pickle=True); R=z["d30_n2_c42_rec"]; D[k]={c:R[:,i] for i,c in enumerate(COLS)}; W[k]=z["d30_n2_c42_W"]
ts=D["FIX7"]["ts"].astype(np.int64); off=int(np.searchsorted(E,ts[0])); n=len(ts)
T=calendar.timegm((2025,3,1,0,0,0)); C=calendar.timegm((2026,8,10,20,0,0))
m=(ts>=T)&(ts<=C)
ym=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
is_first=np.zeros(n,bool)
for i in range(1,n):
    if ym[i]!=ym[i-1]: is_first[i]=True
print(f"冻结主窗 {m.sum()} 锚 | 其中月首锚 {int((is_first&m).sum())} 个 ({(is_first&m).sum()/m.sum()*100:.1f}%)")
print("\n=== ① 换手在月边界 vs 月内 (从存盘权重直接算 Σ|ΔW|/gross) ===")
print(f"{'臂':>11s} {'月首锚换手':>10s} {'月内换手':>9s} {'倍数':>6s} {'边界占总换手':>12s}")
for k in ARMS:
    Wk=W[k]; tn=np.array([np.abs(Wk[i]-Wk[i-1]).sum()/max(np.abs(Wk[i]).sum(),1e-12) for i in range(1,n)])
    mm=m[1:]; ff=is_first[1:]
    a=tn[mm&ff].mean(); b=tn[mm&~ff].mean()
    share=tn[mm&ff].sum()/tn[mm].sum()*100
    print(f"{k:>11s} {a:>10.5f} {b:>9.5f} {a/b:>6.2f}× {share:>11.1f}%")
print("\n=== ② 跨臂: 书层净额 vs 换手 vs IC(冻结主窗) ===")
def ic_of(pred):
    Q=np.full((nA,829),np.nan,np.float32); X=np.load(f"{d}/{pred}"); Q[:len(X)]=X
    out=[]
    for i in range(n):
        if not m[i]: continue
        g=off+i; mmb=MEM[g]; a=Q[g,mmb]; b=Y[g,mmb]; ok=np.isfinite(a)&np.isfinite(b)
        if ok.sum()>=30: out.append(spearmanr(a[ok],b[ok]).correlation)
    return float(np.mean(out))
rows=[]
for k,(p,pred) in ARMS.items():
    g=(D[k]["net_ex"]/D[k]["gross_total"])[m].mean()
    tg=(D[k]["turnover"]/D[k]["gross_total"])[m].mean()
    icv=ic_of(pred) if pred else float("nan")
    rows.append((k,g,tg,icv))
print(f"{'臂':>11s} {'书层净额':>9s} {'换手/gross':>11s} {'分数 IC':>9s}")
for k,g,tg,icv in rows: print(f"{k:>11s} {g:>+9.3f} {tg:>11.5f} {icv:>9.5f}")
net=[r[1] for r in rows]; tur=[r[2] for r in rows]; ics=[r[3] for r in rows]
print(f"\n  Spearman(书层净额, 换手)  = {spearmanr(net,tur).correlation:+.3f}   (n=5, 期望负)")
fin=[(a,b) for a,b in zip(net,ics) if np.isfinite(b)]
print(f"  Spearman(书层净额, 分数IC) = {spearmanr([a for a,b in fin],[b for a,b in fin]).correlation:+.3f}   (n={len(fin)})")
print("\n=== ③ Δpnl(X7FULL−FIX7) 是否集中在月边界 ===")
dp=np.array([np.nansum((W["X7FULL"][i]-W["FIX7"][i])*np.nan_to_num(Y[off+i]))*1e4 for i in range(n)])
print(f"  月首锚 {dp[m&is_first].sum()/m.sum():+.4f} bps/锚(占总 {dp[m&is_first].sum()/dp[m].sum()*100:.0f}%) | 月内 {dp[m&~is_first].sum()/m.sum():+.4f}")
