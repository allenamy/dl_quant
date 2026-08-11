import glob, json, sys
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.ic_monitor import xsec_rank_ic

src = PanelSource(panel=MA + "/exports/live/wide_dl_live.npz",
                  king=MA + "/exports/live/king_pred_live.npz",
                  s2=MA + "/exports/live/s2_pred_live.npz")
tj = {int(t): i for i, t in enumerate(src.ts)}
sym2j = {s: j for j, s in enumerate(src.symbols)}

def run(files, getpos, label):
    rows = []
    for f in sorted(files):
        rec = json.load(open(f)); ti = tj.get(int(rec["anchor_ts_ms"]))
        if ti is None: continue
        ret = src.Y4[ti]
        if not np.isfinite(ret).any(): continue
        w = np.zeros(src.N)
        pos = getpos(rec)
        for s, wt in pos.items():
            if s in sym2j: w[sym2j[s]] = wt
        ic_all = xsec_rank_ic(w, ret)                       # monitor 口径: 全 N, 非成员钉 0
        m = src.tradeable(ti)                               # engine 口径: tradeable 集
        ic_mem = xsec_rank_ic(w[m], ret[m])
        # 被稀释进来的"零权重且 Y4 有限"的名字数
        nz = int(np.sum(np.isfinite(ret) & (w == 0.0)))
        n_ok_all = int(np.sum(np.isfinite(ret)))
        rows.append((rec["anchor_utc"][:10], ic_all, ic_mem, nz, n_ok_all, len(m), len(pos)))
    return label, rows

CH = glob.glob(MA + "/exports/live/positions/positions_*.json")
FX = glob.glob(MA + "/exports/live/fixfunding/positions/positions_*.json")
S = [run(CH, lambda r: r["curve"]["A_provisional_3leg"]["positions"], "champion A_3leg (监控读这条)"),
     run(CH, lambda r: r["curve"]["B_backfilled_4leg"]["positions"],  "champion B_4leg  as-trained"),
     run(FX, lambda r: r["positions"],                                "fixfunding 4leg  normfix")]

for label, rows in S:
    a = np.array([r[1] for r in rows]); m = np.array([r[2] for r in rows])
    ok = np.isfinite(a) & np.isfinite(m); a, m = a[ok], m[ok]; n = len(a); h = n // 2
    print(label)
    print("   monitor 口径(全N, 非成员钉0): 均值 %+.4f   前半 %+.4f -> 后半 %+.4f   末60均值 %.4f"
          % (a.mean(), a[:h].mean(), a[h:].mean(), a[-60:].mean()))
    print("   engine  口径(tradeable 集) : 均值 %+.4f   前半 %+.4f -> 后半 %+.4f   末60均值 %.4f"
          % (m.mean(), m[:h].mean(), m[h:].mean(), m[-60:].mean()))
    print("   稀释比 (monitor/engine): 全窗 %.3f   前半 %.3f   后半 %.3f"
          % (a.mean()/m.mean(), a[:h].mean()/m[:h].mean(), a[h:].mean()/m[h:].mean()))
    print()

_, rows = S[0]
nz = np.array([r[3] for r in rows]); nall = np.array([r[4] for r in rows])
nm = np.array([r[5] for r in rows]); npos = np.array([r[6] for r in rows])
print("零权重但被计入相关的名字数 nz: 均值 %.1f  首5 %s  末5 %s" % (nz.mean(), nz[:5].tolist(), nz[-5:].tolist()))
print("参与相关的总名字数 (Y4 有限): 均值 %.1f  首5 %s  末5 %s" % (nall.mean(), nall[:5].tolist(), nall[-5:].tolist()))
print("tradeable 集大小: 均值 %.1f  首5 %s  末5 %s" % (nm.mean(), nm[:5].tolist(), nm[-5:].tolist()))
print("positions 字典条目数: 均值 %.1f  首5 %s  末5 %s" % (npos.mean(), npos[:5].tolist(), npos[-5:].tolist()))
