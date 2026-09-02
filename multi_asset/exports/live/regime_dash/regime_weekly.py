#!/usr/bin/env python3
"""Regime 周报(只读, 每周日 09:00 local): 近 42 锚(7 天)与 180 锚(30 天)的 sleeve 累计、σ_fund/短周期/深负 百分位漂移、FTRIM 累计反事实、席位轨迹、旗标/建议史。写 REGIME_WEEKLY_<date>.md 并 INFO 页摘要。"""
import json, os, time
HERE=os.path.dirname(os.path.abspath(__file__)); rows=[json.loads(l) for l in open(f'{HERE}/regime_dash.jsonl')] if os.path.exists(f'{HERE}/regime_dash.jsonl') else []
pct=json.load(open(f'{HERE}/regime_hist_pct.json')) if os.path.exists(f'{HERE}/regime_hist_pct.json') else {}
def cum(rs):
    c={}
    for r in rs:
        for k,v in (r.get('sleeve_prev_interval_usdt') or {}).items():
            if isinstance(v,dict) and 'price' in v: a=c.setdefault(k,[0.0,0.0,0]); a[0]+=v['price']; a[1]+=v['carry']; a[2]+=1
    return c
def mean(xs): xs=[x for x in xs if x is not None]; return sum(xs)/len(xs) if xs else None
def pline(k,vals):
    m=mean(vals); p=pct.get(k,{})
    if m is None or not p: return f"- {k}: —"
    pos=sum(1 for q in ('p5','p25','p50','p75','p95') if m>=p[q]); return f"- {k}: 均 {m:.3f} · 历史位 ≥p{[0,5,25,50,75,95][pos]} · 2024 均 {p['by_year'].get('2024',float('nan')):.3f} / 2026 均 {p['by_year'].get('2026',float('nan')):.3f}"
w=rows[-42:]; m=rows[-180:]; date=time.strftime('%Y-%m-%d',time.gmtime())
L=[f"# REGIME 周报 {date}(只读; 锚 {w[0]['anchor_utc'] if w else '—'} → {w[-1]['anchor_utc'] if w else '—'}, n={len(w)})","",
   "## regime 位置(近 7 天均值 vs 历史)", pline('sig_fund',[r.get('sig_fund_bp') for r in w]), pline('short_iv_share',[r.get('short_iv_share') for r in w]), pline('deepneg_share',[r.get('deepneg_share') for r in w]),
   f"- 席位 fund 均 {mean([r.get('w3_masked_fund') for r in w]) or float('nan'):.3f}(30 天 {mean([r.get('w3_masked_fund') for r in m]) or float('nan'):.3f})",
   f"- 实现 IC fund 均 {mean([r.get('ic_fund_realized') for r in w]) or float('nan'):.4f} · 瞬时 {mean([r.get('ic_transient_realized') for r in w]) or float('nan'):.4f}", "",
   "## sleeve 累计(USDT 价差/carry/合计/锚数)"]
for tag,rs in (("7 天",w),("30 天",m)):
    c=cum(rs); L.append(f"**{tag}**"); L += [f"- {k}: {v[0]:+.1f} / {v[1]:+.1f} / {v[0]+v[1]:+.1f} / {v[2]}" for k,v in sorted(c.items())] or ["- —"]
cf=[(r.get('ftrim_counterfactual_prev') or {}).get('avoided_price_bps_of_gross') for r in w]; cf=[x for x in cf if x is not None]
L += ["", f"## FTRIM 反事实累计(7 天): {sum(cf):+.2f} bps of gross over {len(cf)} 锚(正 = 排除避免了亏损)" if cf else "## FTRIM 反事实: 尚无数据",
      "", "## 旗标 / 建议史(7 天)"] + ([f"- {r['anchor_utc']}: {', '.join(r.get('flags') or [])} {'| 建议: '+'; '.join(x['rule'] for x in r.get('recommendations') or []) if r.get('recommendations') else ''}" for r in w if r.get('flags') or r.get('recommendations')] or ["- 无"])
out=f'{HERE}/REGIME_WEEKLY_{date}.md'; open(out,'w').write("\n".join(L)+"\n"); print(out)
try:
    import importlib.util as iu; sp=iu.spec_from_file_location('rde', f'{HERE}/regime_dash_ext.py'); rde=iu.module_from_spec(sp); sp.loader.exec_module(rde)
    rde._notify("INFO", "REGIME 周报 "+date+"\n"+"\n".join(L[2:8])[:1500])
except Exception as e: print("notify fail", e)
