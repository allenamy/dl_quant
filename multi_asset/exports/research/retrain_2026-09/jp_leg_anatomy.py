"""腿解剖(回答: 高 IC 为何收益≈0; 成本假设是否是原因; F10 自己的腿收益是多少)。
对每条腿(king OOS 年折 / king 季度滚动 / F10 OOS 年折 / fund EMA), 2023-24 与 2025-26:
 (a) Spearman IC(rank-rank), (b) Pearson(rank(pred), y4)(=腿书收益的相关口径), (c) 纯价格腿收益 bps/锚 与夏普, (d) 腿收益按分位桶拆解: 顶/底 10% 名 vs 中间 80% 的贡献, (e) 极端收益名(|y4| 前 5%)对腿收益的贡献占比。
另: 书层成本敏感性 —— canonfix(0.21) vs canonpred(0) 的 2025-26 价格 pnl(未扣成本)夏普 与 扣成本后夏普。"""
import numpy as np, time
from scipy.stats import spearmanr, rankdata
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); mem=M["members"]; y4=M["y4"]; qvk=M["qvk"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}; FE=P["f_fund_ema_v1"]
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy"); ROLL=np.load(f"{PD}/slow_pred_rollq_splice.npy")
TG=np.load("dlw_2026-08-22/data/dlw_targets.npz",allow_pickle=True); Ed=TG["E_ts"].astype(np.int64); F10=np.load("f8_2026-08-22/preds/f10_V2MAIN_s42.npy"); drow={int(t):k for k,t in enumerate(Ed)}
def f10_at(i):
    k=drow.get(int(E[i])); return F10[k] if k is not None else None
yr=lambda t: time.gmtime(int(t)).tm_year
acc={}
for i,t in enumerate(E):
    y=yr(t)
    if y<2023: continue
    j=prow.get(int(t)); m=mem[i]
    if j is None: continue
    yy=y4[i,m]; ok=np.isfinite(yy)
    if ok.sum()<80: continue
    qv=np.expm1(np.clip(qvk[i,m],0,30))*48; sel=ok&(qv>=2.5e5)
    legs={"king_oos":SLOW[i,m],"king_roll":ROLL[i,m],"fund_ema":FE[j,m]}
    f=f10_at(i); legs["f10_oos"]=f[m] if f is not None else np.full(len(m),np.nan)
    per=("2023-24" if y<2025 else "2025-26")
    for nm,v in legs.items():
        o=sel&np.isfinite(v)
        if o.sum()<60: continue
        r=np.expm1(np.nan_to_num(yy,nan=0.0)); rk=rankdata(v[o]); z=np.zeros(len(m)); z[o]=rk/max(o.sum()-1,1)-0.5; z-=z[o].mean(); g=np.abs(z).sum(); w=z/g
        lr=float((w*r).sum()*1e4)
        d=acc.setdefault((per,nm),{"ic":[],"pear":[],"lr":[],"tails":[],"mid":[],"ext":[]})
        d["ic"].append(spearmanr(v[o],yy[o]).correlation); d["pear"].append(np.corrcoef(rk,r[o])[0,1]); d["lr"].append(lr)
        q=np.quantile(rk,[0.1,0.9]); tail=o.copy(); tail[o]=(rk<=q[0])|(rk>=q[1]); d["tails"].append(float((w[tail]*r[tail]).sum()*1e4)); d["mid"].append(float((w[o&~tail]*r[o&~tail]).sum()*1e4))
        ext=np.zeros(len(m),bool); thr=np.quantile(np.abs(r[o]),0.95); ext[o]=np.abs(r[o])>=thr; d["ext"].append(float((w[ext]*r[ext]).sum()*1e4))
print("期 | 腿 | Spearman IC | Pearson(rank,ret) | 腿收益 bps/锚 (夏普) | 顶/底10%名贡献 | 中间80%贡献 | |ret| 前5%名贡献 | 锚数")
for (per,nm),d in sorted(acc.items()):
    lr=np.array(d["lr"]); print(f"{per} | {nm:9s} | {np.mean(d['ic']):+.4f} | {np.mean(d['pear']):+.4f} | {lr.mean():+.2f} ({lr.mean()/lr.std()*np.sqrt(2190):.2f}) | {np.mean(d['tails']):+.2f} | {np.mean(d['mid']):+.2f} | {np.mean(d['ext']):+.2f} | {len(lr)}")
# 成本敏感性
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; g=lambda k: rec[:,cols.index(k)].astype(float); return rec[:,cols.index("ts")].astype(np.int64), g("pnl"), g("carry"), g("cost"), g("net_ex"), g("turnover")
print("\n书层成本敏感性(2025-26): 形态 | 价格 pnl 夏普(未扣成本) | 扣 carry 未扣成本 | 扣成本(net_ex) | 均换手 | 均成本 bps")
for tag,lab in (("canonfix_s42","king 0.21 固定"),("canonpred_s42","king 诚实(≈0)"),("uni2_N829T400F_fx_s42","FTRIM+M1 0.21"),("uni2_N829T400F_ms_s42","FTRIM+M1 诚实")):
    ts,pnl,ca,co,ne,to=load(tag); s=np.array([yr(t)>=2025 for t in ts]); sh=lambda x: x[s].mean()/(x[s].std()+1e-9)*np.sqrt(2190)
    print(f"  {lab:18s} | {sh(pnl):.2f} | {sh(pnl-ca):.2f} | {sh(ne):.2f} | {to[s].mean():.4f} | {co[s].mean():.2f}")
print("LEG_ANATOMY_DONE")
