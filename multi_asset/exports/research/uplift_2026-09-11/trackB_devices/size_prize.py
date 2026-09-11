import numpy as np, json, calendar
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1), T(2026,8,10,20)+1)
WIN={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026->0810":(T(2026,1,1),T(2026,8,10,20)+1),"FROZEN":FROZEN}
P="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_%s_%s_s%s.npz"
rows=[]
for arm in ("A0","A1"):
  for seat in ("dyn","fix"):
    for s in ("42","2027"):
      A=np.load(P%(arm,seat,s),allow_pickle=True); Rall=A["d30_n2_c42_rec"]
      tsa=np.round(Rall[:,0].astype(float)).astype(np.int64)
      for wn,(lo,hi) in WIN.items():
        if wn!="FROZEN" and not (arm=="A0" and seat=="dyn" and s=="42"): continue
        m=(tsa>=lo)&(tsa<hi); R=Rall[m]
        if m.sum()<10: continue
        gt=R[:,C["gross_total"]]; g=R[:,C["net_ex"]]/gt
        pnl=R[:,C["pnl_ex"]]/gt; car=R[:,C["carry_ex"]]/gt; cst=R[:,C["cost_ex"]]/gt
        tov=R[:,C["turnover"]]
        cpu = R[:,C["cost_ex"]].sum()/R[:,C["turnover"]].sum()
        sh=g.mean()/g.std(ddof=1)*np.sqrt(2190)
        print("%-14s [%-10s] n=%4d g=%+7.4f SR=%6.3f | pnl %+7.4f carry %+7.4f cost %+7.4f | cost/|net| %5.2f%% | tov %.5f gross %.4f tov/gross %.5f | cost_bps_per_unit_tov %.4f"%(
          arm+"_"+seat+"_s"+s, wn, m.sum(), g.mean(), sh, pnl.mean(), car.mean(), cst.mean(), abs(cst.mean()/g.mean())*100, tov.mean(), gt.mean(), (tov/gt).mean(), cpu))
