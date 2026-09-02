"""T1/T2 扩展(只读): 旗标转移通知(Telegram INFO, 与守护 page() 同链) · 规则引擎(建议+受据+冷却, 不产生动作) · PENDING_RULINGS.md · HTML 渲染。由 regime_dash.py 末尾调用。"""
import json, os, time, html
HERE=os.path.dirname(os.path.abspath(__file__)); STATE_F=f'{HERE}/flag_state.json'; PEND=f'{HERE}/PENDING_RULINGS.md'; RECS=f'{HERE}/recommendations.jsonl'
COOLDOWN=24   # 锚
def _notify(sev, msg):
    try:
        import sys; sys.path.insert(0,'/Users/haosiyu/dl_quant_live/live'); import telegram_notify as TN
        tok=cid=None
        for ln in open('/Users/haosiyu/dl_quant_live/.env'):
            ln=ln.strip()
            if ln.startswith('TELEGRAM_BOT_TOKEN='): tok=ln.split('=',1)[1].strip().strip('"')
            elif ln.startswith('TELEGRAM_CHAT_ID='): cid=ln.split('=',1)[1].strip().strip('"')
        TN.TelegramNotifier(token=tok, chat_id=cid).alarm(sev, msg); return True
    except Exception as e:
        open(f'{HERE}/notify.err','a').write(f"{time.time()} {e}\n"); return False
def _cum_sleeve(rows, n):
    cum={}
    for r in rows[-n:]:
        for k,v in (r.get('sleeve_prev_interval_usdt') or {}).items():
            if isinstance(v,dict) and 'price' in v:
                c=cum.setdefault(k,[0.0,0.0,0]); c[0]+=v['price']; c[1]+=v['carry']; c[2]+=1
    return cum
def rules(rows, pct):
    """三条预注册决策规则 + 一条前兆规则 ⇒ 建议列表(不是动作)。"""
    recs=[]; cur=rows[-1]
    cum=_cum_sleeve(rows,30); lp=cum.get('L|pos'); sp=cum.get('S|pos')
    if lp and sp and lp[2]>=20 and sp[2]>=20 and lp[0]+lp[1]<0 and sp[0]+sp[1]<0:
        recs.append({"rule":"R1_双引擎同负","建议":"讨论降杠杆(唯一预注册的降杠杆形态)","受据":f"近30锚 L|pos {lp[0]+lp[1]:+.0f}U, S|pos {sp[0]+sp[1]:+.0f}U 同为负","归":"用户裁定; 冷却 24 锚"})
    sig=[r.get('sig_fund_bp') for r in rows[-42:] if r.get('sig_fund_bp') is not None]
    cf=[ (r.get('ftrim_counterfactual_prev') or {}).get('avoided_price_bps_of_gross') for r in rows[-30:]]; cf=[x for x in cf if x is not None]
    if len(sig)>=30 and sum(1 for x in sig if x<5.0)>=30 and len(cf)>=30 and sum(cf)<0:
        recs.append({"rule":"R2_FTRIM可撤","建议":"FTRIM 负费率排除进入可撤讨论(低离散 regime + 反事实为负)","受据":f"σ_fund<5bp {sum(1 for x in sig if x<5.0)}/{len(sig)} 锚; 近30锚反事实合计 {sum(cf):+.2f} bps","归":"用户裁定"})
    w=[r.get('w3_masked_fund') for r in rows[-12:]]
    if len(w)>=12 and all(x is not None and x<0.6 for x in w):
        recs.append({"rule":"R3_席位换季","建议":"fund 席位连续 12 锚 <0.6: 模型腿杠杆上升, L1SS/模型侧投入的前置条件松动","受据":f"w3_fund 近12锚 {min(w):.2f}~{max(w):.2f}","归":"研究排期(用户)"})
    if pct and len(rows)>=84:
        p25=pct['sig_fund']['p25']; low=[r.get('sig_fund_bp') for r in rows[-84:]]; low=[x for x in low if x is not None]
        if len(low)>=70 and sum(1 for x in low if x<p25)>=70:
            recs.append({"rule":"R4_引擎A退潮","建议":"费率离散度两周低于历史 p25: 复核 sleeve 与 FTRIM 反事实, 预期 fund 腿贡献回落到 2024 型","受据":f"σ_fund<p25({p25:.2f}bp) {sum(1 for x in low if x<p25)}/{len(low)} 锚","归":"信息"})
    return recs
def run(rows, row, pct, md_lines):
    st=json.load(open(STATE_F)) if os.path.exists(STATE_F) else {"flags":[],"last_sent":{},"init":False}
    A=row['anchor_ts']; flags=row.get('flags',[]); prev=set(st.get('flags',[])); now=set(flags)
    recs=rules(rows, pct); row['recommendations']=recs
    msgs=[]
    for f in sorted(now-prev): msgs.append(f"+旗标: {f}")
    for f in sorted(prev-now): msgs.append(f"−旗标消失: {f}")
    fired=[]
    for r in recs:
        last=st['last_sent'].get(r['rule'],-10**12)
        if A-last>=COOLDOWN*14400: fired.append(r); st['last_sent'][r['rule']]=A
    for r in fired:
        msgs.append(f"建议[{r['rule']}]: {r['建议']} | 受据: {r['受据']} | {r['归']}")
        with open(RECS,'a') as fh: fh.write(json.dumps({"anchor_ts":A,"anchor_utc":row['anchor_utc'],**r},ensure_ascii=False)+"\n")
        with open(PEND,'a') as fh: fh.write(f"- [{row['anchor_utc']}] **{r['rule']}** — {r['建议']}。受据: {r['受据']}。归: {r['归']}。(待并入 STATE §3)\n")
    if not st.get('init'):
        msgs.insert(0,"regime_dash T1/T2 上线: 旗标转移与预注册建议将以 INFO 页通知(每锚最多 1 条, 规则冷却 24 锚)"); st['init']=True
    sent=False
    if msgs:
        body="REGIME_DASH @"+row['anchor_utc']+"\n"+"\n".join(msgs)+f"\nσ_fund {row.get('sig_fund_bp')}bp({(row.get('pct') or {}).get('sig_fund')}) 深负空头gross {row.get('book_S_deepneg')} fund席位 {row.get('w3_masked_fund')}"
        sent=_notify("INFO", body[:3500])
    st['flags']=sorted(now); json.dump(st, open(STATE_F,'w'), indent=1)
    row['notify']={"msgs":msgs,"sent":sent}
    md_lines += ["", "## 决策支持(预注册规则 → 建议, 不是动作)"] + ([f"- **{r['rule']}**: {r['建议']} — 受据: {r['受据']} — 归: {r['归']}" for r in recs] or ["- 无触发(R1 双引擎同负 / R2 FTRIM 可撤 / R3 席位换季 / R4 引擎A退潮)"])
    return recs
def render_html(rows, row, pct, out):
    def f(v,nd=3):
        if v is None: return "—"
        try: return f"{float(v):.{nd}f}"
        except: return html.escape(str(v))
    hist=rows[-42:]
    def spark(key, w=220, h=44, scale=1.0):
        vals=[(r.get(key) if r.get(key) is not None else None) for r in hist]; xs=[i for i,v in enumerate(vals) if v is not None]
        if len(xs)<2: return "<svg width='%d' height='%d'></svg>"%(w,h)
        vs=[vals[i]*scale for i in xs]; lo,hi=min(vs),max(vs); rng=(hi-lo) or 1.0
        pts=" ".join(f"{6+ (i/(len(vals)-1))*(w-12):.1f},{h-6-((v-lo)/rng)*(h-12):.1f}" for i,v in zip(xs,vs))
        lx,ly=pts.split()[-1].split(",")
        return f"<svg viewBox='0 0 {w} {h}' width='{w}' height='{h}' class='spark'><polyline points='{pts}' fill='none' stroke='var(--acc)' stroke-width='1.6'/><circle cx='{lx}' cy='{ly}' r='2.6' fill='var(--acc)'/><text x='{w-4}' y='10' text-anchor='end' class='sv'>{vs[-1]:.2f}</text><text x='4' y='10' class='sv'>{lo:.2f}–{hi:.2f}</text></svg>"
    def pctchip(k):
        lab=(row.get('pct') or {}).get(k) or '—'; cls={'>=p95':'hi','<p95':'hi','<p75':'mid','<p50':'mid','<p25':'lo','<p5':'lo'}.get(lab,'mid'); return f"<span class='chip {cls}'>{html.escape(lab)}</span>"
    sl=row.get('sleeve_prev_interval_usdt') or {}; cum=_cum_sleeve(rows,30)
    order=['L|pos','S|pos','S|shallowneg','S|deepneg','L|neg']
    def bars(d, getter, title):
        items=[(k,getter(d[k])) for k in order if k in d and isinstance(d[k],(dict,list))]
        if not items: return f"<div class='panel'><h3>{title}</h3><p class='muted'>需连续两锚数据</p></div>"
        m=max(abs(v) for _,v in items) or 1.0
        rows_html="".join(f"<div class='brow'><span class='bl'>{k}</span><div class='btrack'><div class='bfill {'neg' if v<0 else 'pos'}' style='width:{abs(v)/m*50:.1f}%;{'right:50%' if v<0 else 'left:50%'}'></div></div><span class='bv'>{v:+.1f}</span></div>" for k,v in items)
        return f"<div class='panel'><h3>{title}</h3><div class='bars'>{rows_html}</div></div>"
    recs=row.get('recommendations') or []; flags=row.get('flags') or []
    comp=[('多头·正费率',row.get('book_L_pos')),('空头·正费率',row.get('book_S_pos')),('空头·浅负',row.get('book_S_shallowneg')),('空头·深负',row.get('book_S_deepneg')),('多头·负费率',row.get('book_L_neg'))]
    stack="".join(f"<div class='seg s{i}' style='width:{(v or 0)*100:.1f}%' title='{n} {f(v)}'></div>" for i,(n,v) in enumerate(comp))
    legend="".join(f"<span class='lg'><i class='s{i}'></i>{n} {f(v,3)}</span>" for i,(n,v) in enumerate(comp))
    ft=row.get('ftrim_names') or []; cf=row.get('ftrim_counterfactual_prev')
    tbl="".join(f"<tr><td>{r['anchor_utc'][5:]}</td><td>{f(r.get('sig_fund_bp'),1)}</td><td>{f(r.get('short_iv_share'),2)}</td><td>{f(r.get('deepneg_share'),3)}</td><td>{f(r.get('book_S_deepneg'),3)}</td><td>{f(r.get('w3_masked_fund'),2)}</td><td>{f(r.get('ic_fund_realized'),3)}</td><td>{f(r.get('ic_transient_realized'),3)}</td><td>{r.get('ftrim_n_kc','—')}</td><td>{(r.get('ftrim_counterfactual_prev') or {}).get('avoided_price_bps_of_gross','—')}</td></tr>" for r in rows[-24:][::-1])
    by=lambda k,y: f((pct.get(k,{}).get('by_year',{}) or {}).get(str(y)),2) if pct else '—'
    page=f"""<title>Regime Dash</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#F4F6F3;--ink:#17211D;--mut:#68766F;--line:#D9DFDA;--panel:#FFFFFF;--acc:#1F6F78;--good:#2E7D4F;--warn:#B7791F;--crit:#B23A3A;--s0:#3E8E7E;--s1:#7FB7A9;--s2:#D8A54C;--s3:#B23A3A;--s4:#9AA5A0}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#111716;--ink:#E4ECE7;--mut:#94A39B;--line:#2A3430;--panel:#18211E;--acc:#6FC2CB;--good:#5FBF86;--warn:#D9A548;--crit:#E06565;--s0:#4FA893;--s1:#8FCBBD;--s2:#E0B45E;--s3:#E06565;--s4:#7F8B86}}}}
:root[data-theme="dark"]{{--bg:#111716;--ink:#E4ECE7;--mut:#94A39B;--line:#2A3430;--panel:#18211E;--acc:#6FC2CB;--good:#5FBF86;--warn:#D9A548;--crit:#E06565;--s0:#4FA893;--s1:#8FCBBD;--s2:#E0B45E;--s3:#E06565;--s4:#7F8B86}}
body{{background:var(--bg);color:var(--ink);font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:14px;line-height:1.45;margin:0;padding:20px 24px 40px}}
h1,h2,h3{{font-family:'IBM Plex Sans Condensed','IBM Plex Sans',sans-serif;text-wrap:balance;margin:0}} h1{{font-size:26px;font-weight:600}} h2{{font-size:15px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);margin-bottom:8px}} h3{{font-size:14px;font-weight:600;margin-bottom:8px}}
.strip{{display:flex;flex-wrap:wrap;gap:10px 22px;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}} .strip .k{{color:var(--mut);font-size:12px;letter-spacing:.06em;text-transform:uppercase}} .strip .v{{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}}
.chip{{display:inline-block;padding:1px 8px;border-radius:999px;font-family:'IBM Plex Mono',monospace;font-size:12px;border:1px solid var(--line)}} .chip.hi{{color:var(--crit);border-color:var(--crit)}} .chip.mid{{color:var(--warn);border-color:var(--warn)}} .chip.lo{{color:var(--good);border-color:var(--good)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:18px}} .panel{{background:var(--panel);border:1px solid var(--line);padding:14px 16px}}
.kv{{display:grid;grid-template-columns:1fr auto auto;gap:6px 12px;align-items:center}} .kv .n{{color:var(--mut)}} .kv .val{{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;text-align:right}} .kv .ref{{color:var(--mut);font-size:12px;font-family:'IBM Plex Mono',monospace}}
.spark{{display:block;margin-top:4px}} .sv{{font:10px 'IBM Plex Mono',monospace;fill:var(--mut)}}
.stack{{display:flex;height:18px;border:1px solid var(--line);overflow:hidden;margin:6px 0 8px}} .seg{{height:100%}} .s0{{background:var(--s0)}} .s1{{background:var(--s1)}} .s2{{background:var(--s2)}} .s3{{background:var(--s3)}} .s4{{background:var(--s4)}}
.lg{{display:inline-flex;align-items:center;gap:6px;margin-right:12px;font-size:12px;color:var(--mut)}} .lg i{{display:inline-block;width:10px;height:10px}}
.bars{{display:grid;gap:6px}} .brow{{display:grid;grid-template-columns:110px 1fr 70px;align-items:center;gap:8px}} .bl{{color:var(--mut);font-size:12px}} .btrack{{position:relative;height:12px;background:var(--bg);border:1px solid var(--line)}} .bfill{{position:absolute;top:0;height:100%}} .bfill.pos{{background:var(--good)}} .bfill.neg{{background:var(--crit)}} .bv{{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;text-align:right}}
.flag{{border-left:3px solid var(--warn);padding:6px 10px;margin:6px 0;background:var(--panel)}} .rec{{border-left:3px solid var(--acc);padding:8px 10px;margin:6px 0;background:var(--panel)}} .muted{{color:var(--mut)}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;font-size:12px}} th,td{{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}} th{{color:var(--mut);font-weight:500}} td:first-child,th:first-child{{text-align:left}}
</style>
<h1>Regime Dash</h1>
<div class="strip"><span><span class="k">锚 </span><span class="v">{row['anchor_utc']}</span></span><span><span class="k">σ_fund </span><span class="v">{f(row.get('sig_fund_bp'),1)}bp</span> {pctchip('sig_fund')}</span><span><span class="k">短周期占比 </span><span class="v">{f(row.get('short_iv_share'),3)}</span> {pctchip('short_iv_share')}</span><span><span class="k">席位 king/fund </span><span class="v">{f(row.get('w3_masked_king'),2)} / {f(row.get('w3_masked_fund'),2)}</span></span><span><span class="k">FTRIM </span><span class="v">{row.get('ftrim_n_kc','—')} 名</span></span><span><span class="k">深负空头 gross </span><span class="v">{f(row.get('book_S_deepneg'))}</span></span><span class="muted">只读 · 每锚后 50 分刷新 · 旗标为信息</span></div>
<div class="grid">
<div class="panel"><h2>Regime 状态</h2><div class="kv">
<span class="n">σ_fund 8h(bp)</span><span class="val">{f(row.get('sig_fund_bp'),2)}</span><span class="ref">2024 {by('sig_fund',2024)} · 2026 {by('sig_fund',2026)}</span>
<span class="n">短周期名占比</span><span class="val">{f(row.get('short_iv_share'),3)}</span><span class="ref">{by('short_iv_share',2024)} · {by('short_iv_share',2026)}</span>
<span class="n">深负名占比 ≤−10bp</span><span class="val">{f(row.get('deepneg_share'),3)}</span><span class="ref">{by('deepneg_share',2024)} · {by('deepneg_share',2026)}</span>
<span class="n">浅负 / 正费率占比</span><span class="val">{f(row.get('shallowneg_share'),3)} / {f(row.get('pos_share'),3)}</span><span class="ref"></span>
<span class="n">费率 p5 / p95(bp)</span><span class="val">{f(row.get('fund_p5_bp'),1)} / {f(row.get('fund_p95_bp'),1)}</span><span class="ref"></span>
<span class="n">实现 IC fund / 瞬时</span><span class="val">{f(row.get('ic_fund_realized'),4)} / {f(row.get('ic_transient_realized'),4)}</span><span class="ref">噪声 ±0.03/锚, 看 30 锚</span></div>
<h3 style="margin-top:12px">σ_fund 近 42 锚</h3>{spark('sig_fund_bp')}<h3>深负空头 gross 近 42 锚</h3>{spark('book_S_deepneg')}</div>
<div class="panel"><h2>书构成(gross 占比)</h2><div class="stack">{stack}</div><div>{legend}</div><p class="muted" style="margin:10px 0 0">持仓名 {row.get('book_gross_names')} · 成员 {row.get('n_members')} · 费率覆盖 {f(row.get('rn8_coverage'),3)}</p>
<h3 style="margin-top:12px">FTRIM 排除名(本锚)</h3><p style="margin:0;font-family:'IBM Plex Mono',monospace;font-size:12px">{', '.join(ft) if ft else '— (部署前锚 / 无)'}</p><p class="muted" style="margin:6px 0 0">上锚排除名若持有的价差(反事实, bps of gross): {cf.get('avoided_price_bps_of_gross') if cf else '—'}</p></div>
{bars(sl, lambda v: v['price']+v['carry'], '上锚→本锚 sleeve 合计(USDT)')}
{bars(cum, lambda c: c[0]+c[1], '近 30 锚累计 sleeve(USDT)')}
</div>
<div class="grid"><div class="panel"><h2>旗标</h2>{''.join(f"<div class='flag'>{html.escape(x)}</div>" for x in flags) or "<p class='muted'>无</p>"}</div>
<div class="panel"><h2>决策支持(建议, 不是动作)</h2>{''.join(f"<div class='rec'><b>{r['rule']}</b> — {html.escape(r['建议'])}<br><span class='muted'>受据: {html.escape(r['受据'])} · 归: {html.escape(r['归'])}</span></div>" for r in recs) or "<p class='muted'>无触发 · R1 双引擎同负 / R2 FTRIM 可撤 / R3 席位换季 / R4 引擎A退潮</p>"}</div></div>
<div class="panel tw"><h2>近 24 锚</h2><table><thead><tr><th>锚</th><th>σ_fund</th><th>短周期</th><th>深负占比</th><th>书深负空头</th><th>fund 席位</th><th>IC_fund</th><th>IC_瞬时</th><th>FTRIM n</th><th>反事实</th></tr></thead><tbody>{tbl}</tbody></table></div>
<p class="muted" style="margin-top:14px">采集器 regime_dash.py · 基准 2023+ jpline B 面板 · 生成 {time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}</p>
"""
    open(out,'w').write(page)

def _creds():
    tok=cid=None
    for ln in open('/Users/haosiyu/dl_quant_live/.env'):
        ln=ln.strip()
        if ln.startswith('TELEGRAM_BOT_TOKEN='): tok=ln.split('=',1)[1].strip().strip('"')
        elif ln.startswith('TELEGRAM_CHAT_ID='): cid=ln.split('=',1)[1].strip().strip('"')
    return tok,cid
def send_document(path, caption, silent=True):
    """脚本触发的网页投递: 每锚把 REGIME_DASH.html 作为文件发到 Telegram(静默, 不响铃); 手机/电脑点开即最新仪表盘。不依赖 Claude 会话。"""
    import urllib.request, uuid
    try:
        tok,cid=_creds()
        if not tok or not cid: return False
        b=uuid.uuid4().hex; data=open(path,'rb').read(); fn=os.path.basename(path)
        parts=[]
        for k,v in (("chat_id",cid),("caption",caption[:1000]),("disable_notification","true" if silent else "false"),("parse_mode","")):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{fn}"\r\nContent-Type: text/html\r\n\r\n'.encode()+data+b'\r\n')
        body=b''.join(parts)+f'--{b}--\r\n'.encode()
        req=urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendDocument", data=body, headers={"Content-Type":f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=30) as r: ok=json.loads(r.read().decode()).get("ok",False)
        return bool(ok)
    except Exception as e:
        open(f'{HERE}/notify.err','a').write(f"{time.time()} sendDocument {e}\n"); return False
