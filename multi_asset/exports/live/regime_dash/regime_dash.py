#!/usr/bin/env python3
"""Regime 仪表盘(只读采集器, 每锚一行; 2026-09-02 用户令建立)。
读: ~/wide_shadow/state/aux.json(费率账本尾/EMA/上锚成员与权重) · shadow_log(w3/信号) · state/target_combo(FTRIM 记录) · dl_quant_live pilot_log(锚中价向量/持仓/资金费)
写: regime_dash.jsonl(追加) + REGIME_DASH.md(最新快照 + 近 12 锚 + 旗标)。不改任何实盘文件。历史基准: regime_hist_pct.json(jpline B 面板 2023+)。"""
import json, os, glob, time, sys, re
import numpy as np
WS=os.path.expanduser('~/wide_shadow'); PL=os.path.expanduser('~/dl_quant_live/state/live/pilot_log'); HERE=os.path.dirname(os.path.abspath(__file__))
OUT_J=f'{HERE}/regime_dash.jsonl'; OUT_M=f'{HERE}/REGIME_DASH.md'
def spearman(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    ra=np.argsort(np.argsort(a[ok])); rb=np.argsort(np.argsort(b[ok])); return float(np.corrcoef(ra,rb)[0,1])
aux=json.load(open(f'{WS}/state/aux.json')); pr=aux['prev_rec']; A=int(pr['anchor_ts']); pm=np.array(pr['members'],np.int64)
syms=[str(s) for s in np.load(f'{WS}/fea171/xfer_ref.npz',allow_pickle=True)['symbols']]; NW=len(syms); col={s:j for j,s in enumerate(syms)}
rn8=np.full(NW,np.nan); ema=np.full(NW,np.nan); ivv=np.full(NW,np.nan)
for s_,rows_ in aux['ledger_tail'].items():
    j=col.get(s_)
    if j is not None and rows_:
        r=rows_[-1]; iv=float(r[2]) if len(r)>2 and r[2] else 8.0; ivv[j]=iv; rn8[j]=float(r[1])*(8.0/(iv if iv>0 else 8.0))
for s_,est in aux['ema'].items():
    j=col.get(s_)
    if j is not None and isinstance(est,dict) and 'acc' in est: ema[j]=float(est['acc'])
sm=np.zeros(NW); sm[np.array(pr['sm_idx'],np.int64)]=np.array(pr['sm'],np.float64); g=np.abs(sm).sum()
live=np.array(sorted(set(int(x) for x in pm)))   # 当锚成员
f=rn8[live]; fin=np.isfinite(f)
row={"anchor_ts":A,"anchor_utc":time.strftime('%Y-%m-%dT%H:%MZ',time.gmtime(A)),"n_members":int(len(live)),"rn8_coverage":round(float(fin.mean()),4)}
ff=f[fin]; row.update({"sig_fund_bp":round(float(np.std(ff)*1e4),2),"short_iv_share":round(float((ivv[live][fin]<8).mean()),4),
    "deepneg_share":round(float((ff<=-0.0010).mean()),4),"shallowneg_share":round(float(((ff>-0.0010)&(ff<0)).mean()),4),"pos_share":round(float((ff>=0).mean()),4),
    "fund_p5_bp":round(float(np.percentile(ff,5)*1e4),1),"fund_p95_bp":round(float(np.percentile(ff,95)*1e4),1)})
# 书构成: 按方向×费率桶的 gross 占比
def share(mask): return round(float(np.abs(sm[mask]).sum()/g),4) if g>0 else np.nan
S_=sm<0; L_=sm>0; deep=np.isfinite(rn8)&(rn8<=-0.0010); shal=np.isfinite(rn8)&(rn8>-0.0010)&(rn8<0); posf=np.isfinite(rn8)&(rn8>=0)
row.update({"book_S_deepneg":share(S_&deep),"book_S_shallowneg":share(S_&shal),"book_S_pos":share(S_&posf),"book_L_pos":share(L_&posf),"book_L_neg":share(L_&(deep|shal)),"book_gross_names":int((np.abs(sm)>1e-9).sum())})
# w3(shadow_log signal)
w3=None
for fpath in sorted(glob.glob(f'{WS}/shadow_log*.jsonl')):
    for l in open(fpath):
        if '"e": "signal"' in l and f'"anchor_ts": {A}' in l:
            try: w3=json.loads(l).get('w3')
            except: pass
if w3: w3m=[w3[0]/(w3[0]+w3[2]),0.0,w3[2]/(w3[0]+w3[2])]; row.update({"w3_raw":[round(x,4) for x in w3],"w3_masked_king":round(w3m[0],4),"w3_masked_fund":round(w3m[2],4)})
# FTRIM 记录(部署后)
tc=f'{WS}/state/target_combo/{A}.json'
if os.path.exists(tc):
    ft=json.load(open(tc)).get('ftrim') or {}
    if ft: row.update({"ftrim_n_kc":ft.get('n_kc'),"ftrim_n_fc":ft.get('n_fc'),"ftrim_names":sorted(set(ft.get('names_kc',{}))|set(ft.get('names_fc',{})))})
# 实现 IC: 上锚 fund 分数(legz fund, 成员序) vs 本锚实现 4h 收益(pilot_log mid 向量: 上锚→本锚)
def mids():
    M={}
    for fpath in sorted(glob.glob(f'{PL}/2026*/anchors.jsonl')):
        for l in open(fpath):
            try: d=json.loads(l)
            except: continue
            a=d.get('anchor_ts'); mv=d.get('mid_at_anchor_vector')
            if a is None or not mv: continue
            a=int(round(float(a)/14400)*14400) if float(a)%14400>600 else int(float(a))   # 锚墙钟→名义锚
            M[int(round(float(a)/14400)*14400)]=mv
    return M
M=mids(); prevA=A-14400
ic_fund=np.nan; ic_tr=np.nan; cf_ftrim=None
if A in M and prevA in M:
    m1=M[A]; m0=M[prevA]
    if isinstance(m1,dict) and isinstance(m0,dict):
        names=[s for s in m1 if s in m0 and m0[s] and m1[s]]; ret={s:float(m1[s])/float(m0[s])-1 for s in names}
        # 上锚 legz 在 aux.prev_rec 是"本锚"的成员分数(用于本锚建仓) — 实现 IC 需上锚分数: 从上锚 dash 行取(若有)
        prev_rows=[json.loads(l) for l in open(OUT_J)] if os.path.exists(OUT_J) else []
        pz=next((r for r in reversed(prev_rows) if r.get('anchor_ts')==prevA and 'fund_score' in r), None)
        if pz:
            fz=pz['fund_score']; tz=pz.get('tr_score',{})
            common=[s for s in fz if s in ret]; ic_fund=spearman([fz[s] for s in common],[ret[s] for s in common])
            common2=[s for s in tz if s in ret]; ic_tr=spearman([tz[s] for s in common2],[ret[s] for s in common2]) if common2 else np.nan
        # FTRIM 反事实: 上锚被排除名若按上锚权重持有, 本锚价差(不含 carry)
        ptc=f'{WS}/state/target_combo/{prevA}.json'
        if os.path.exists(ptc):
            pft=(json.load(open(ptc)).get('ftrim') or {}); ex=set(pft.get('names_kc',{}))|set(pft.get('names_fc',{}))
            if ex:
                pw=json.load(open(f'{WS}/state/target_live/{prevA}.json')).get('weights',{}) if os.path.exists(f'{WS}/state/target_live/{prevA}.json') else {}
                cf=[-abs(float(pw.get(s,0)))*ret[s] for s in ex if s in ret]   # 空头: 收益 = −w·ret; 排除避免的 = 其相反数
                cf_ftrim={"n":len(cf),"avoided_price_bps_of_gross":round(-float(np.sum(cf))*1e4,3)} if cf else None
row.update({"ic_fund_realized":None if np.isnan(ic_fund) else round(ic_fund,4),"ic_transient_realized":None if np.isnan(ic_tr) else round(ic_tr,4),"ftrim_counterfactual_prev":cf_ftrim})
# 存本锚 fund 分数与瞬时分量(供下锚算实现 IC)
legz=pr['legz']; fs={syms[int(pm[k])]:float(legz['fund'][k]) for k in range(len(pm)) if np.isfinite(legz['fund'][k])}
def cz(v):
    v=np.asarray(v,float); ok=np.isfinite(v); r=np.full(v.shape,np.nan)
    if ok.sum()>3: x=v[ok]; r[ok]=(x-x.mean())/(x.std()+1e-12)
    return r
trz=cz(rn8[pm])-cz(ema[pm]); ts_={syms[int(pm[k])]:float(trz[k]) for k in range(len(pm)) if np.isfinite(trz[k])}
row["fund_score"]=fs; row["tr_score"]=ts_
# 历史百分位
pct=json.load(open(f'{HERE}/regime_hist_pct.json')) if os.path.exists(f'{HERE}/regime_hist_pct.json') else {}
def pctile(k,v):
    p=pct.get(k); 
    if not p or v is None: return None
    for lab,q in (("<p5","p5"),("<p25","p25"),("<p50","p50"),("<p75","p75"),("<p95","p95")):
        if v<p[q]: return lab
    return ">=p95"
row["pct"]={"sig_fund":pctile("sig_fund",row.get("sig_fund_bp")),"short_iv_share":pctile("short_iv_share",row.get("short_iv_share")),"deepneg_share":pctile("deepneg_share",row.get("deepneg_share"))}
# 旗标(信息, 不触发动作)
flags=[]
if pct and row.get("sig_fund_bp") is not None and row["sig_fund_bp"]<pct["sig_fund"]["p25"]: flags.append("σ_fund<p25: 引擎A(费率离散)退潮观察")
if pct and row.get("short_iv_share") is not None and row["short_iv_share"]<0.5: flags.append("短周期占比<50%: 场所放大器减弱")
if row.get("book_S_deepneg") is not None and row["book_S_deepneg"]>0.10: flags.append("深负空头 gross>10%(FTRIM 部署后应趋 0)")
if row.get("w3_masked_fund") is not None and row["w3_masked_fund"]<0.6: flags.append("fund 席位<0.6: 席位在换季")
row["flags"]=flags
# 追加 + 渲染
rows=[json.loads(l) for l in open(OUT_J)] if os.path.exists(OUT_J) else []
rows=[r for r in rows if r.get('anchor_ts')!=A]+[row]; rows.sort(key=lambda r:r['anchor_ts'])
with open(OUT_J,'w') as fh:
    for r in rows: fh.write(json.dumps(r,ensure_ascii=False)+"\n")
def fmt(v,nd=3): return "—" if v is None or (isinstance(v,float) and np.isnan(v)) else (f"{v:.{nd}f}" if isinstance(v,(int,float)) and not isinstance(v,bool) else str(v))
lines=[f"# REGIME DASH(只读)— 最新锚 {row['anchor_utc']}", "", f"> 生成 {time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())} · 采集器 regime_dash.py · 历史基准 regime_hist_pct.json(2023+, jpline B 面板)· 旗标只作信息", "",
 "## 最新快照", "| 量 | 值 | 历史位 | 2024 均 / 2026 均(基准) |", "|---|---|---|---|"]
for k,lab in (("sig_fund_bp","σ_fund 8h(bp)"),("short_iv_share","短周期名占比"),("deepneg_share","深负名占比(≤−10bp)"),("shallowneg_share","浅负占比"),("pos_share","正费率占比")):
    hk={"sig_fund_bp":"sig_fund"}.get(k,k); p=pct.get(hk,{}); by=p.get("by_year",{})
    lines.append(f"| {lab} | {fmt(row.get(k))} | {row['pct'].get(hk) or '—'} | {fmt(by.get('2024'))} / {fmt(by.get('2026'))} |")
lines += ["", "## 书构成(gross 占比)", f"- 空头: 深负 {fmt(row['book_S_deepneg'])} · 浅负 {fmt(row['book_S_shallowneg'])} · 正费率 {fmt(row['book_S_pos'])} ; 多头: 正费率 {fmt(row['book_L_pos'])} · 负费率 {fmt(row['book_L_neg'])} ; 持仓名 {row['book_gross_names']}",
 f"- 席位(掩码后) king {fmt(row.get('w3_masked_king'))} / fund {fmt(row.get('w3_masked_fund'))}", f"- FTRIM: kc {row.get('ftrim_n_kc','—')} / fc {row.get('ftrim_n_fc','—')} 名 {row.get('ftrim_names','')}", f"- 实现 IC(上锚分数→本锚 4h): fund {fmt(row['ic_fund_realized'],4)} · 瞬时 {fmt(row['ic_transient_realized'],4)} ; FTRIM 反事实(上锚排除名若持有的价差, bps of gross) {row['ftrim_counterfactual_prev']}",
 "", "## 旗标", *( [f"- {x}" for x in flags] or ["- 无"]), "", "## 近 12 锚", "| 锚 | σ_fund | 短周期 | 深负占比 | 书深负空头 | fund 席位 | IC_fund | IC_瞬时 | FTRIM n | 反事实 |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows[-12:]:
    cf=r.get('ftrim_counterfactual_prev'); lines.append(f"| {r['anchor_utc'][5:]} | {fmt(r.get('sig_fund_bp'),1)} | {fmt(r.get('short_iv_share'),2)} | {fmt(r.get('deepneg_share'),3)} | {fmt(r.get('book_S_deepneg'),3)} | {fmt(r.get('w3_masked_fund'),2)} | {fmt(r.get('ic_fund_realized'),3)} | {fmt(r.get('ic_transient_realized'),3)} | {r.get('ftrim_n_kc','—')} | {cf['avoided_price_bps_of_gross'] if cf else '—'} |")
open(OUT_M,'w').write("\n".join(lines)+"\n")
print(json.dumps({k:v for k,v in row.items() if k not in ('fund_score','tr_score')},ensure_ascii=False)[:900])
