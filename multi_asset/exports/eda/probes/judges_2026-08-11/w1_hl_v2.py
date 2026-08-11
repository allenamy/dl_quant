"""W1 v2 · 仪器修复版(ts单位实测/真4h锚/逐年/null=均值分布) + 双目标:
T1 币安 fwd 4h 收益(Y4) — 上轮带伤读数的正名
T2 币安下一期资金费(funding 通道 fwd 8h 变化) — carry 族的本职目标
判据: |IC|≥0.01 且逐年同号≥3/4 且 |IC| > 3×null_sd。判官入库(y24 案家规)。"""
import numpy as np, json
from scipy.stats import spearmanr
MA='/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset'
HL=np.load(f'{MA}/exports/hl_hourly.npz', allow_pickle=True)
P=np.load(f'{MA}/exports/wide_dl_full_corrfund_causal_0731.npz', allow_pickle=True)
assert list(HL['symbols'])==list(P['symbols'])
X,feats,ts=HL['X'],list(HL['feats']),HL['ts']
unit = 1000 if ts[1]-ts[0] >= 3600*1000 else 1
tss = ts//unit
print(f"ts 单位: {'ms' if unit==1000 else 's'}, 步长 {tss[1]-tss[0]}s")
Y4,MEM=P['Y4'],P['MEMBER110']
ch=list(P['ch_names']); FI=[i for i,c in enumerate(ch) if 'fund' in str(c).lower()]
FU=P['CH'][:,:,FI[0]] if FI else None
print("funding 通道:", ch[FI[0]] if FI else "无")
T,N=Y4.shape
hours=(tss//3600)%24
anchors=np.where(hours%4==0)[0]
import datetime
years=np.array([datetime.datetime.utcfromtimestamp(t).year for t in tss])
rng=np.random.default_rng(7)
def screen(F, tgt, name):
    ics, nulls, yr_ic = [], [], {}
    for t in anchors:
        if t+8>=T: continue
        y = tgt[t]
        m = np.isfinite(F[t]) & MEM[t].astype(bool) & np.isfinite(y)
        if m.sum()<30: continue
        ic = spearmanr(F[t][m], y[m]).statistic
        ics.append(ic); yr_ic.setdefault(int(years[t]),[]).append(ic)
        nulls.append(spearmanr(F[t][m], y[m][rng.permutation(int(m.sum()))]).statistic)
    if not ics: return None
    mean_ic = float(np.nanmean(ics)); null_sd = float(np.nanstd(nulls))/np.sqrt(len(nulls))
    yrs = {y: round(float(np.nanmean(v)),4) for y,v in sorted(yr_ic.items()) if len(v)>100}
    sign_ok = sum(1 for v in yrs.values() if v*mean_ic>0)
    g = abs(mean_ic)>=0.01 and sign_ok>=max(1,len(yrs)-1) and abs(mean_ic)>3*null_sd
    print(f"{name}: IC {mean_ic:+.4f} (null_se {null_sd:.4f}) 逐年{yrs} {'★PASS' if g else 'fail'} n={len(ics)}")
    return dict(ic=round(mean_ic,4), null_se=round(null_sd,5), by_year=yrs, g=bool(g), n=len(ics))
out={}
# T2 目标: 币安 funding 通道的 fwd 8h 变化(下一结算期资金费方向)
FWD_FU = None
if FU is not None:
    FWD_FU = np.full_like(FU, np.nan)
    FWD_FU[:-8] = FU[8:]
for fi,f in enumerate(feats):
    out[f"{f}__ret4h"] = screen(X[:,:,fi], Y4, f"{f} → 收益4h")
    if FWD_FU is not None:
        out[f"{f}__fund8h"] = screen(X[:,:,fi], FWD_FU, f"{f} → 资金费+8h")
json.dump(out, open('/mnt/storage/private/work_hsy/probe_artifacts/w1_hl_v2.json','w'), indent=1)
print("W1V2_DONE")
