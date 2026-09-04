"""月度 IC(fund EMA / king SLOW → y4)与回放书 2026 逐月表现、腿相关、广度 @jpline(审计 live vs replay, 2026-09-04)。"""
import numpy as np, json, time, os
from scipy.stats import spearmanr
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]; qvk=M["qvk"]; mem=M["members"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]; FE=P["f_fund_ema_v1"]; prow={int(t):j for j,t in enumerate(pts)}
SLOW=np.load(f"{B}/slow_pred_hist_oos.npy")
live450=set(json.load(open("live_pins.json"))["symbols_live"]) if os.path.exists("live_pins.json") else None
l450=np.array([s in live450 for s in syms]) if live450 else None
def ym(t): g=time.gmtime(int(t)); return g.tm_year*100+g.tm_mon
res={}
for i,t in enumerate(E):
    if t<1735689600: continue
    j=prow.get(int(t)); m=mem[i]
    if j is None: continue
    qv=np.expm1(np.clip(qvk[i,m],0,30))*48; sel=m[(qv>=2.5e5)&np.isfinite(y4[i,m])]
    if len(sel)<80: continue
    yv=y4[i,sel]; fe=FE[j,sel]; sk=SLOW[i,sel]; ok=np.isfinite(fe); ok2=np.isfinite(sk)
    r=res.setdefault(ym(t),{"icf":[],"ick":[],"n":[],"icf450":[]})
    if ok.sum()>50: r["icf"].append(spearmanr(fe[ok],yv[ok]).correlation)
    if ok2.sum()>50: r["ick"].append(spearmanr(sk[ok2],yv[ok2]).correlation)
    r["n"].append(len(sel))
    if l450 is not None:
        s2=sel[l450[sel]]; f2=FE[j,s2]; y2=y4[i,s2]; o2=np.isfinite(f2)
        if o2.sum()>50: r["icf450"].append(spearmanr(f2[o2],y2[o2]).correlation)
def fm(a): return f"{np.mean(a):+.4f}" if a else "  —  "
print("月 | IC_fund(EMA→y4, 合格名) | IC_fund(冻结450∩合格) | IC_king(SLOW) | 均合格名数 | 锚数")
for k in sorted(res):
    r=res[k]; print(f"{k} | {fm(r['icf'])} | {fm(r['icf450'])} | {fm(r['ick'])} | {np.mean(r['n']):.0f} | {len(r['n'])}")
for tag in ("canonfix_s42","canonpred_s42"):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; ts=rec[:,cols.index("ts")].astype(np.int64)
    g=lambda k: rec[:,cols.index(k)].astype(float); ne=g("net_ex"); lk=g("leg_king"); lf=g("leg_fund"); ns=g("nsel"); yms=np.array([ym(t) for t in ts])
    print(f"\n[{tag}] 2026 逐月: 月 | net_ex 均(bps/锚) | 月夏普(年化) | leg_king 均 | leg_fund 均 | corr(king,fund) | nsel 均")
    for k in sorted(set(yms[yms>=202601])):
        s=yms==k; c=np.corrcoef(lk[s],lf[s])[0,1] if s.sum()>10 else np.nan
        print(f"  {k} | {ne[s].mean():+.2f} | {ne[s].mean()/(ne[s].std()+1e-9)*np.sqrt(2190):.2f} | {lk[s].mean():+.2f} | {lf[s].mean():+.2f} | {c:+.2f} | {ns[s].mean():.0f}")
    for y in (2023,2024,2025,2026):
        s=(yms//100)==y; print(f"  {y} 全年: corr(king,fund) {np.corrcoef(lk[s],lf[s])[0,1]:+.2f} | leg_king {lk[s].mean():+.2f} leg_fund {lf[s].mean():+.2f} | net_ex 均 {ne[s].mean():+.2f} 夏普 {ne[s].mean()/(ne[s].std()+1e-9)*np.sqrt(2190):.2f} | nsel {ns[s].mean():.0f}")
print("MONTHLY_IC_DONE")
