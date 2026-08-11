import glob, json, sys
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.ic_monitor import xsec_rank_ic
src = PanelSource(panel=MA+"/exports/live/wide_dl_live.npz", king=MA+"/exports/live/king_pred_live.npz",
                  s2=MA+"/exports/live/s2_pred_live.npz")
tj={int(t):i for i,t in enumerate(src.ts)}; sym2j={s:j for j,s in enumerate(src.symbols)}
def go(files, getpos, label):
    out=[]
    for f in sorted(files):
        rec=json.load(open(f)); ti=tj.get(int(rec["anchor_ts_ms"]))
        if ti is None: continue
        ret=src.Y4[ti]
        if not np.isfinite(ret).any(): continue
        w=np.zeros(src.N)
        for s,wt in getpos(rec).items():
            if s in sym2j: w[sym2j[s]]=wt
        m=src.tradeable(ti)
        ic=xsec_rank_ic(w[m], ret[m])
        if np.isfinite(ic): out.append(ic)
    a=np.array(out); n=len(a); se30=a.std(ddof=1)/np.sqrt(30)
    print("%s  n=%d  mean %+.4f  sd %.4f" % (label, n, a.mean(), a.std(ddof=1)))
    print("   30 锚 SE %.4f (95%%带宽 ±%.4f)   末60均值 %.4f" % (se30, 1.96*se30, a[-60:].mean()))
    for tgt,lab in ((0.031,"2σ 分辨 0.062 vs 0.031"),):
        need=(a.std(ddof=1)/( (0.062-0.031)/2.0 ))**2
        print("   %s 所需 n ≈ %.0f 锚 (%.1f 天)   2.8σ 所需 n ≈ %.0f 锚 (%.1f 天)"
              % (lab, need, need/6, need*(2.8/2.0)**2, need*(2.8/2.0)**2/6))
FX=glob.glob(MA+"/exports/live/fixfunding/positions/positions_*.json")
CH=glob.glob(MA+"/exports/live/positions/positions_*.json")
go(FX, lambda r: r["positions"], "fixfunding 4leg (决策序列, engine 口径)")
go(CH, lambda r: r["curve"]["B_backfilled_4leg"]["positions"], "champion B_4leg (对照, engine 口径)")
