"""事件日判官(FOMC 族, 2022-2026 全部 40 次决议日, 日期经 Fed 官网/多源核实)。
问题: 排期宏观事件日的书级 |PnL|/方差/尾部是否系统性更大 ⇒ 事前降 gross 是否有definable保费。
判据(冻结): 事件窗(决议日±6锚) vs 非事件, 若 σ 比值 <1.2 或事件窗均值为正且显著 ⇒ ②层关闭。
"""
import sys, json, datetime
import numpy as np
PD="/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0,PD)
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0,MA); sys.path.insert(0,MA+"/engine/live"); sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
import engine.replay_fullhist as RF
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz")
a,yr=RF._all_anchors(src)
# 找真实时间轴
cand=[x for x in dir(src) if 'ts' in x.lower() or 'time' in x.lower()]
print('src 时间属性候选:', cand)
ts=None
for c in cand:
    v=getattr(src,c)
    try:
        arr=np.asarray(v)
        if arr.ndim==1 and len(arr)>len(a) and arr.dtype.kind in 'if':
            ts=arr; print('用', c, len(arr), arr[0], arr[-1]); break
    except Exception: pass
assert ts is not None, '找不到时间轴'
tss=ts//1000 if ts[1]-ts[0]>=3600*1000 else ts
ats=np.array([tss[int(t)] if int(t)<len(tss) else -1 for t in a], dtype='int64')
dates=np.array([datetime.datetime.utcfromtimestamp(int(t)).date().toordinal() if t>0 else -1 for t in ats])
net=np.load(f'{PD}/net_S1.npy')
assert len(net)==len(dates), f'{len(net)} vs {len(dates)}'
FOMC=["2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14",
"2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13",
"2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18",
"2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10",
"2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29"]
ev=set()
for d in FOMC:
    o=datetime.date.fromisoformat(d).toordinal()
    ev.add(o); ev.add(o+1)   # 决议日+次日(4h锚跨时区)
is_ev=np.array([d in ev for d in dates])
print('事件锚数', int(is_ev.sum()), '/', len(dates))
res={}
for tag,mask in (('event',is_ev),('normal',~is_ev)):
    x=net[mask & (dates>0)]
    res[tag]={'n':int(len(x)),'mean':round(float(x.mean()),3),'sigma':round(float(x.std()),2),
              'p5':round(float(np.percentile(x,5)),1),'p1':round(float(np.percentile(x,1)),1),
              'ES5':round(float(np.sort(x)[:max(1,len(x)//20)].mean()),1)}
res['sigma_ratio']=round(res['event']['sigma']/res['normal']['sigma'],3)
res['mean_diff_t']=round(float((res['event']['mean']-res['normal']['mean'])/ (res['event']['sigma']/np.sqrt(res['event']['n']))),2)
# 逐年σ比
byy={}
for y in sorted(set(yr.tolist())):
    m=(yr==y)&(dates>0)
    e=net[m&is_ev]; nn=net[m&~is_ev]
    if len(e)>=12: byy[int(y)]={'n_ev':len(e),'sigma_ratio':round(float(e.std()/nn.std()),3),'mean_ev':round(float(e.mean()),3),'mean_norm':round(float(nn.mean()),3)}
res['by_year']=byy
print(json.dumps(res,ensure_ascii=False,indent=1))
json.dump(res,open(f'{PD}/event_day_judge.json','w'))
