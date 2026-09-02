"""D1 书层拆解: canon vs fund 腿残差化 — 逐年 leg_fund / pnl(价差) / carry / cost / net_ex; 以及 IC 层的尾部检验: 十分位多空价差(raw vs resid, y4)。"""
import numpy as np, time, collections
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def yr(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    g=lambda k: rec[:,cols.index(k)].astype(float); ts=rec[:,cols.index("ts")].astype(np.int64)
    y=np.array([time.gmtime(int(t)).tm_year for t in ts])
    return {Y:{k:g(k)[y==Y].mean() for k in ("leg_fund","leg_king","pnl_ex","carry_ex","cost_ex","net_ex","turnover","w3_fund")} for Y in (2023,2024,2025,2026)}
a=yr("w10_canonpred_s42"); b=yr("w10_seat_fundresid")
print("书层逐年(bps/锚) canon → 残差化: leg_fund | pnl价差 | carry | cost | net_ex | w3_fund")
for Y in (2023,2024,2025,2026):
    A=a[Y]; Bq=b[Y]
    print(f"  {Y}: {A['leg_fund']:+.3f}→{Bq['leg_fund']:+.3f} | {A['pnl_ex']:+.3f}→{Bq['pnl_ex']:+.3f} | {A['carry_ex']:+.3f}→{Bq['carry_ex']:+.3f} | {A['cost_ex']:+.3f}→{Bq['cost_ex']:+.3f} | {A['net_ex']:+.3f}→{Bq['net_ex']:+.3f} | {A['w3_fund']:.2f}→{Bq['w3_fund']:.2f}")
# 尾部检验(IC 层): 十分位多空(等权) raw S vs resid, 同一样本(残差可用名)
z=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); ts=z["ts"].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
S=z["f_fund_ema_v1"]; Y4=z["Y4"]; EL=z["elig"].astype(bool); FR=np.load(f"{PD}/femat_resid_v1.npz")["fe"]
FN=z["f_fund_now"]; IV=z["f_fund_iv"]; ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
rows=collections.defaultdict(list)
for i in range(0,len(ts),2):
    ok=EL[i]&np.isfinite(S[i])&np.isfinite(FR[i])&np.isfinite(Y4[i])&(FR[i]!=S[i])   # 只取真被残差化的名
    if ok.sum()<80: continue
    y=Y4[i][ok]
    for nm,v in (("raw",S[i][ok]),("res",FR[i][ok])):
        o=np.argsort(v); k=max(1,len(o)//10)
        rows[(yrs[i],nm+"_ls")].append(y[o[-k:]].mean()-y[o[:k]].mean())
        rows[(yrs[i],nm+"_top")].append(y[o[-k:]].mean()); rows[(yrs[i],nm+"_bot")].append(y[o[:k]].mean())
        # 尾部名的费率水平(8h bp): 多头端/空头端 = 书要付的 carry 代理
        f=FN8[i][ok]; rows[(yrs[i],nm+"_ftop")].append(np.nanmean(f[o[-k:]])*1e4); rows[(yrs[i],nm+"_fbot")].append(np.nanmean(f[o[:k]])*1e4)
    rows[(yrs[i],"n")].append(int(ok.sum()))
def m(y,k): v=np.array(rows[(y,k)],float); v=v[np.isfinite(v)]; return v.mean() if len(v) else np.nan
print("IC 层尾部(十分位多空 4h 收益 bp, 等权): 年 | raw LS | resid LS | raw top/bot | resid top/bot | 尾部费率 raw(top,bot) | resid(top,bot) | 名/锚")
for y in sorted(set(a_ for a_,_ in rows)):
    print(f"  {y}: {m(y,'raw_ls')*1e4:+.1f} | {m(y,'res_ls')*1e4:+.1f} | {m(y,'raw_top')*1e4:+.1f}/{m(y,'raw_bot')*1e4:+.1f} | {m(y,'res_top')*1e4:+.1f}/{m(y,'res_bot')*1e4:+.1f} | ({m(y,'raw_ftop'):+.1f},{m(y,'raw_fbot'):+.1f}) | ({m(y,'res_ftop'):+.1f},{m(y,'res_fbot'):+.1f}) | {m(y,'n'):.0f}")
print("D1_BOOK_DECOMP_DONE")
