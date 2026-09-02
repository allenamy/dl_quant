import json, time
B=json.load(open('viz_backtest.json')); L=json.load(open('viz_live.json'))
# 精简回测序列(隔日采样以控体积)
def thin(s, k=1): return {kk:(v[::k] if isinstance(v,list) else v) for kk,v in s.items()}
data={"bt":{k:thin(v,1) for k,v in B["series"].items()},"yearly":B["yearly"],"regime":B["regime"],"lev":B["lev"],"sig":B["sig_fund_daily"],"live":L}
y=B["yearly"]; rg=B["regime"]; lev=B["lev"]
def f(v,nd=2): return "—" if v is None else f"{v:.{nd}f}"
yr_rows="".join(f"<tr><td>{Y}</td><td>{f(y['msharpe_base'][Y]['net'],3)}</td><td>{f(y['msharpe_ftrim'][Y]['net'],3)}</td><td>{f(y['msharpe_base'][Y]['sharpe'])} → {f(y['msharpe_ftrim'][Y]['sharpe'])}</td><td>{f(y['w3fix_base'][Y]['net'],3)}</td><td>{f(y['w3fix_ftrim'][Y]['net'],3)}</td><td>{f(y['w3fix_base'][Y]['sharpe'])} → {f(y['w3fix_ftrim'][Y]['sharpe'])}</td></tr>" for Y in ("2023","2024","2025","2026"))
lev_rows="".join(f"<tr><td>{Lx}×</td>"+"".join(f"<td>{lev[k][Lx]['ann']*100:+.1f}% / {lev[k][Lx]['maxdd']*100:.1f}% / {lev[k][Lx]['worst_day']*100:.2f}% / {lev[k][Lx]['days_le_m4']}</td>" for k in ("msharpe_base","msharpe_ftrim","w3fix_base","w3fix_ftrim"))+"</tr>" for Lx in ("1.5","2.0","2.5"))
live=L; an=live["anchors"]; last=an[-1] if an else {}
nav0=live["daily_nav"][0]["nav"] if live["daily_nav"] else None; nav1=live["daily_nav"][-1]["nav"] if live["daily_nav"] else None
sl_cum={k: round(sum(r[k][0]+r[k][1] for r in live["sleeve"] if k in r),1) for k in ('L|pos','S|pos','S|shallowneg','S|deepneg','L|neg')}
html=f"""<title>Wide-Book 评估图册</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#F5F7F8;--ink:#14202B;--mut:#66747E;--line:#D8DFE3;--panel:#FFFFFF;--acc:#1F6F78;--acc2:#B7791F;--acc3:#7A8C95;--good:#2E7D4F;--crit:#B23A3A;--band:rgba(31,111,120,.10)}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#10171A;--ink:#E3EAEE;--mut:#93A2AB;--line:#28333A;--panel:#171F24;--acc:#6FC2CB;--acc2:#E0B45E;--acc3:#8D9BA3;--good:#5FBF86;--crit:#E06565;--band:rgba(111,194,203,.12)}}}}
:root[data-theme="dark"]{{--bg:#10171A;--ink:#E3EAEE;--mut:#93A2AB;--line:#28333A;--panel:#171F24;--acc:#6FC2CB;--acc2:#E0B45E;--acc3:#8D9BA3;--good:#5FBF86;--crit:#E06565;--band:rgba(111,194,203,.12)}}
body{{background:var(--bg);color:var(--ink);font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:14px;line-height:1.5;margin:0;padding:24px 28px 48px}}
h1,h2,h3{{font-family:'IBM Plex Sans Condensed','IBM Plex Sans',sans-serif;text-wrap:balance;margin:0}} h1{{font-size:28px;font-weight:600}} h2{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:600;margin:28px 0 10px}} h3{{font-size:14px;font-weight:600;margin-bottom:6px}}
.sub{{color:var(--mut);margin-top:4px;max-width:70ch}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0 6px}} .kpi{{background:var(--panel);border:1px solid var(--line);padding:12px 14px}} .kpi .k{{color:var(--mut);font-size:12px;letter-spacing:.05em;text-transform:uppercase}} .kpi .v{{font-family:'IBM Plex Mono',monospace;font-size:22px;font-variant-numeric:tabular-nums;margin-top:4px}} .kpi .s{{color:var(--mut);font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}} .panel{{background:var(--panel);border:1px solid var(--line);padding:14px 16px}} .panel p{{color:var(--mut);font-size:12px;margin:6px 0 0}}
svg{{display:block;width:100%;height:auto}} .ax{{stroke:var(--line);stroke-width:1}} .tick{{font:11px 'IBM Plex Mono',monospace;fill:var(--mut)}} .lbl{{font:11px 'IBM Plex Sans',sans-serif;fill:var(--mut)}} .ev{{stroke:var(--mut);stroke-dasharray:3 3;opacity:.7}} .evt{{font:10px 'IBM Plex Sans Condensed',sans-serif;fill:var(--mut)}}
.lg{{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--mut);margin-top:6px}} .lg i{{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;font-size:12px}} th,td{{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}} th{{color:var(--mut);font-weight:500;font-family:'IBM Plex Sans',sans-serif}} td:first-child,th:first-child{{text-align:left}}
.note{{border-left:3px solid var(--acc2);padding:8px 12px;background:var(--panel);margin-top:10px;font-size:13px}} .muted{{color:var(--mut)}}
</style>
<h1>Wide-Book 评估图册</h1>
<p class="sub">Binance USDT-perp 宽宇宙市场中性(combo 书):回放 2023-01 → 2026-08 与实盘 2026-08-26 起。所有回放数字为执行者口径净额(含成本模型 3.52 bps/单位换手与 carry),简单收益;实盘为场所账本。生成 {time.strftime('%Y-%m-%d %H:%MZ',time.gmtime())}。</p>
<div class="kpis">
<div class="kpi"><div class="k">回放 2026 净额 · 基线</div><div class="v">{y['msharpe_base']['2026']['net']:.2f}</div><div class="s">bps/锚 of gross · 夏普 {y['msharpe_base']['2026']['sharpe']:.2f}</div></div>
<div class="kpi"><div class="k">FTRIM 改善(双口径)</div><div class="v">+{rg['msharpe']['total']:.3f} / +{rg['w3fix']['total']:.3f}</div><div class="s">bps/锚 · msharpe / 实盘席位 W3FIX</div></div>
<div class="kpi"><div class="k">2.0× 年化(2023+)</div><div class="v">{lev['w3fix_base']['2.0']['ann']*100:.0f}% → {lev['w3fix_ftrim']['2.0']['ann']*100:.0f}%</div><div class="s">实盘构成 W3FIX · msharpe {lev['msharpe_base']['2.0']['ann']*100:.0f}%→{lev['msharpe_ftrim']['2.0']['ann']*100:.0f}%</div></div>
<div class="kpi"><div class="k">实盘 NAV</div><div class="v">{f(nav1,0)}</div><div class="s">{live['daily_nav'][0]['day'] if live['daily_nav'] else ''} → {live['daily_nav'][-1]['day'] if live['daily_nav'] else ''} · 起 {f(nav0,0)}(含 08-27 入金)</div></div>
<div class="kpi"><div class="k">实盘锚数 / 最新</div><div class="v">{len(an)}</div><div class="s">{last.get('utc','')} · gross {f(last.get('realized_gross'),0)} · net/gross {f((last.get('net_over_gross') or 0)*100,2)}%</div></div>
</div>
<h2>A · 回放:权益与回撤(2.0× 常杠杆,日频)</h2>
<div class="grid">
<div class="panel"><h3>权益(起点 1.0,对数轴)— 四条:席位口径 × 有/无 FTRIM</h3><div id="eqchart"></div><div class="lg"><span><i style="background:var(--acc)"></i>msharpe 基线</span><span><i style="background:var(--acc2)"></i>msharpe + FTRIM</span><span><i style="background:var(--acc3)"></i>W3FIX 基线(实盘席位 0.21/0.79)</span><span><i style="background:var(--acc2);opacity:.5"></i>W3FIX + FTRIM</span></div><p>msharpe = 席位随 900 锚腿 Sharpe 漂(回放 2026 给 king 0.01);W3FIX = 席位钉在实盘当前值。两者都不是实盘真实历史,2026 段两者一致(4.07 vs 4.11 bps/锚),2023-24 分歧大。</p></div>
<div class="panel"><h3>回撤(2.0×)</h3><div id="ddchart"></div><p>W3FIX 的 −37% 回撤全在 2023-24 固定席位段(那两年实盘会 king 重仓);msharpe 路径最大回撤 13%。</p></div>
</div>
<h2>B · 回放:逐年、分 regime、分杠杆</h2>
<div class="grid">
<div class="panel"><h3>逐年净额(bps/锚)与夏普</h3><div class="tw"><table><thead><tr><th>年</th><th>msharpe 基线</th><th>+FTRIM</th><th>夏普</th><th>W3FIX 基线</th><th>+FTRIM</th><th>夏普</th></tr></thead><tbody>{yr_rows}</tbody></table></div><p>2026 一年主导全部年化;2024 型低离散年在实盘构成下 ≈0。</p></div>
<div class="panel"><h3>FTRIM 改善 Δ 按 regime(bps/锚)</h3><div id="regchart"></div><p>低离散 ≈0(不伤)、高离散 +0.4~0.6;W3FIX 口径下跌/平/涨锚全正 —— 增益 = 少付深负空头 carry,是尾部保险型。</p></div>
<div class="panel" style="grid-column:1/-1"><h3>分杠杆(2023+ 全程,常 gross 复利):年化 / 最大回撤 / 最差日 / ≤−4% 日数</h3><div class="tw"><table><thead><tr><th>杠杆</th><th>msharpe 基线</th><th>msharpe +FTRIM</th><th>W3FIX 基线</th><th>W3FIX +FTRIM</th></tr></thead><tbody>{lev_rows}</tbody></table></div><p>约束是 −4% 日亏自动平仓线:最差日触 −4% 的杠杆 = 基线 2.10× → FTRIM 后 2.33×(W3FIX)。维持 2.0×。</p></div>
</div>
<h2>C · 实盘(2026-08-26 起)</h2>
<div class="grid">
<div class="panel" style="grid-column:1/-1"><h3>账户权益(guard_twin 20 分钟读数)与事件</h3><div id="eqlive"></div><p>08-26 13:45Z 保护性平仓(E-0826-F)后分级重建;08-27 入金;09-01 双 v3 换装;09-02 12:00Z FTRIM 上线。曲线含入金跳变,评估看入金后段。</p></div>
<div class="panel"><h3>逐锚:实现 gross vs 目标 · 净/gross</h3><div id="grosschart"></div><p>gross 层每锚 ≈100% 到位;net/gross 带 ±1%。</p></div>
<div class="panel"><h3>sleeve 累计(USDT,价差+carry,按方向×费率桶)</h3><div id="sleevechart"></div><div class="lg"><span><i style="background:var(--acc)"></i>L|pos 正费率多头</span><span><i style="background:var(--good)"></i>S|pos 正费率空头</span><span><i style="background:var(--acc2)"></i>S|浅负</span><span><i style="background:var(--crit)"></i>S|深负</span><span><i style="background:var(--acc3)"></i>L|负费率</span></div><p>累计:{', '.join(f'{k} {v:+.0f}' for k,v in sl_cum.items())}。深负空头 sleeve 即 FTRIM 排除对象;口径 = 上锚持仓 × 锚间 mid 变化 + 账本 funding。</p></div>
<div class="panel"><h3>执行漏斗:maker 成交率 · maker 占比 · 费用 bps</h3><div id="funnelchart"></div><p>成交率 = maker 成交名义/意图名义;费用带 1.8~2.3 bps;chase 臂实发后 taker 份额略升。</p></div>
<div class="panel"><h3>日实现分型(USDT):REALIZED · FUNDING · 佣金</h3><div id="dailychart"></div><p>实现口径不含未实现;佣金以 BNB 支付故 COMMISSION ≈0,费用见漏斗 bps。</p></div>
</div>
<h2>D · regime 状态:费率离散度 σ_fund(8h 归一化,日均 bp)</h2>
<div class="panel"><div id="sigchart"></div><p>2024 均 3.0 · 2025 12.1 · 2026 16.7 bp;fund 腿 alpha 与它同涨落;仪表盘按历史百分位报当前位置。</p></div>
<div class="note"><b>读法边界。</b>回放 2026 +4.1 bps/锚 的年化(2.0× ≈ +480%)是已实现 regime 的回测;实盘 42 锚前向里实跑 36 锚为 +0.4 bps/锚(8 月末高离散洗盘 + 尺寸税 + 成交率 61%)。FTRIM 的 Δ 是成对差,可信度高于绝对水平。84 锚二读(09-09)是首个有效前向读数。</div>
<script>
const D={json.dumps(data)};
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
function svgEl(w,h){{const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);return s;}}
function el(n,a,t){{const e=document.createElementNS('http://www.w3.org/2000/svg',n);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e;}}
function lineChart(id,series,opts){{const w=880,h=opts.h||260,m={{l:56,r:16,t:12,b:28}};const s=svgEl(w,h);const xs=series[0].x.length;
 let ymin=Infinity,ymax=-Infinity;series.forEach(S=>S.y.forEach(v=>{{if(v==null||!isFinite(v))return;const vv=opts.log?Math.log(v):v;ymin=Math.min(ymin,vv);ymax=Math.max(ymax,vv);}}));if(opts.zero&&!opts.log){{ymin=Math.min(ymin,0);ymax=Math.max(ymax,0);}}
 const pad=(ymax-ymin)*0.06||1;ymin-=pad;ymax+=pad;const X=i=>m.l+(i/(xs-1))*(w-m.l-m.r);const Y=v=>{{const vv=opts.log?Math.log(v):v;return m.t+(1-(vv-ymin)/(ymax-ymin))*(h-m.t-m.b);}};
 const nt=5;for(let k=0;k<=nt;k++){{const vv=ymin+(ymax-ymin)*k/nt;const yy=m.t+(1-k/nt)*(h-m.t-m.b);s.appendChild(el('line',{{x1:m.l,x2:w-m.r,y1:yy,y2:yy,class:'ax'}}));const lab=opts.log?Math.exp(vv):vv;s.appendChild(el('text',{{x:m.l-6,y:yy+4,'text-anchor':'end',class:'tick'}},opts.fmt?opts.fmt(lab):lab.toFixed(2)));}}
 const labs=series[0].labels||series[0].x;const step=Math.max(1,Math.floor(xs/8));for(let i=0;i<xs;i+=step){{s.appendChild(el('text',{{x:X(i),y:h-8,'text-anchor':'middle',class:'tick'}},String(labs[i]).slice(opts.labslice||0,opts.labslice!=null?(opts.labslice+7):7)));}}
 if(opts.zero&&!opts.log){{s.appendChild(el('line',{{x1:m.l,x2:w-m.r,y1:Y(0),y2:Y(0),stroke:css('--mut'),'stroke-width':1}}));}}
 (opts.events||[]).forEach(ev=>{{const i=ev.i;if(i==null)return;s.appendChild(el('line',{{x1:X(i),x2:X(i),y1:m.t,y2:h-m.b,class:'ev'}}));s.appendChild(el('text',{{x:X(i)+3,y:m.t+10+(ev.k%4)*11,class:'evt'}},ev.t));}});
 series.forEach(S=>{{let d='';S.y.forEach((v,i)=>{{if(v==null||!isFinite(v))return;d+=(d?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1);}});s.appendChild(el('path',{{d,fill:'none',stroke:S.c,'stroke-width':S.w||1.6,'stroke-dasharray':S.dash||'','opacity':S.o||1}}));
  if(S.area){{let a='M'+X(0)+','+Y(0);S.y.forEach((v,i)=>{{a+='L'+X(i).toFixed(1)+','+Y(v).toFixed(1);}});a+='L'+X(xs-1)+','+Y(0)+'Z';s.appendChild(el('path',{{d:a,fill:S.c,opacity:.15}}));}}}});
 document.getElementById(id).appendChild(s);}}
function barChart(id,groups,opts){{const w=880,h=opts.h||220,m={{l:56,r:16,t:12,b:40}};const s=svgEl(w,h);const vals=groups.flatMap(g=>g.v);let ymin=Math.min(0,...vals),ymax=Math.max(0,...vals);const pad=(ymax-ymin)*.1||.1;ymin-=pad;ymax+=pad;
 const Y=v=>m.t+(1-(v-ymin)/(ymax-ymin))*(h-m.t-m.b);const gw=(w-m.l-m.r)/groups.length;
 for(let k=0;k<=4;k++){{const vv=ymin+(ymax-ymin)*k/4;const yy=Y(vv);s.appendChild(el('line',{{x1:m.l,x2:w-m.r,y1:yy,y2:yy,class:'ax'}}));s.appendChild(el('text',{{x:m.l-6,y:yy+4,'text-anchor':'end',class:'tick'}},vv.toFixed(2)));}}
 s.appendChild(el('line',{{x1:m.l,x2:w-m.r,y1:Y(0),y2:Y(0),stroke:css('--mut')}}));
 groups.forEach((g,gi)=>{{const n=g.v.length;const bw=gw*0.7/n;g.v.forEach((v,j)=>{{const x=m.l+gi*gw+gw*0.15+j*bw;s.appendChild(el('rect',{{x,y:Math.min(Y(v),Y(0)),width:bw-2,height:Math.abs(Y(v)-Y(0)),fill:opts.colors[j]}}));s.appendChild(el('text',{{x:x+bw/2-1,y:(v>=0?Y(v)-4:Y(v)+11),'text-anchor':'middle',class:'tick'}},v.toFixed(2)));}});s.appendChild(el('text',{{x:m.l+gi*gw+gw/2,y:h-14,'text-anchor':'middle',class:'lbl'}},g.l));}});
 document.getElementById(id).appendChild(s);}}
const bt=D.bt;const days=bt.msharpe_base.days;const yrIdx=[];days.forEach((d,i)=>{{if(i==0||d.slice(0,4)!==days[i-1].slice(0,4))yrIdx.push({{i,t:d.slice(0,4),k:0}});}});
lineChart('eqchart',[{{x:days,y:bt.msharpe_base.eq2x,c:css('--acc')}},{{x:days,y:bt.msharpe_ftrim.eq2x,c:css('--acc2')}},{{x:days,y:bt.w3fix_base.eq2x,c:css('--acc3')}},{{x:days,y:bt.w3fix_ftrim.eq2x,c:css('--acc2'),o:.5,dash:'4 3'}}],{{log:true,fmt:v=>v.toFixed(1)+'×',events:yrIdx}});
lineChart('ddchart',[{{x:days,y:bt.msharpe_base.dd2x,c:css('--acc'),area:true}},{{x:days,y:bt.w3fix_ftrim.dd2x,c:css('--acc2'),dash:'4 3'}}],{{zero:true,fmt:v=>(v*100).toFixed(0)+'%',h:200,events:yrIdx}});
const rg=D.regime;barChart('regchart',[{{l:'低离散',v:[rg.msharpe.disp_tercile[0],rg.w3fix.disp_tercile[0]]}},{{l:'中',v:[rg.msharpe.disp_tercile[1],rg.w3fix.disp_tercile[1]]}},{{l:'高离散',v:[rg.msharpe.disp_tercile[2],rg.w3fix.disp_tercile[2]]}},{{l:'跌锚',v:[rg.msharpe.market.down,rg.w3fix.market.down]}},{{l:'平',v:[rg.msharpe.market.flat,rg.w3fix.market.flat]}},{{l:'涨锚',v:[rg.msharpe.market.up,rg.w3fix.market.up]}}],{{colors:[css('--acc'),css('--acc2')]}});
const lv=D.live;const eqT=lv.equity.t,eqV=lv.equity.eq;const evs=lv.events.map((e,k)=>{{let i=null;for(let j=0;j<eqT.length;j++){{if(eqT[j]>=e[0]){{i=j;break;}}}}return {{i,t:e[1],k}};}});
lineChart('eqlive',[{{x:eqT,y:eqV,c:css('--acc'),w:1.8}}],{{fmt:v=>v.toFixed(0),events:evs,labslice:5,h:280}});
const an=lv.anchors;lineChart('grosschart',[{{x:an.map(a=>a.utc),y:an.map(a=>a.realized_gross),c:css('--acc'),w:1.8}},{{x:an.map(a=>a.utc),y:an.map(a=>a.target_gross),c:css('--acc2'),dash:'4 3'}}],{{fmt:v=>(v/1000).toFixed(1)+'k',h:220}});
const sl=lv.sleeve;const keys=['L|pos','S|pos','S|shallowneg','S|deepneg','L|neg'];const cols=[css('--acc'),css('--good'),css('--acc2'),css('--crit'),css('--acc3')];const cum={{}};keys.forEach(k=>cum[k]=[]);sl.forEach(r=>{{keys.forEach(k=>{{const prev=cum[k].length?cum[k][cum[k].length-1]:0;const v=r[k]?(r[k][0]+r[k][1]):0;cum[k].push(prev+v);}});}});
lineChart('sleevechart',keys.map((k,i)=>({{x:sl.map(r=>r.utc),y:cum[k],c:cols[i],w:1.6}})),{{zero:true,fmt:v=>v.toFixed(0),h:240}});
const fn=lv.funnel.filter(r=>r.fill_rate!=null);lineChart('funnelchart',[{{x:fn.map(r=>r.utc),y:fn.map(r=>r.fill_rate),c:css('--acc'),w:1.6}},{{x:fn.map(r=>r.utc),y:fn.map(r=>r.maker_share),c:css('--good'),dash:'4 3'}},{{x:fn.map(r=>r.utc),y:fn.map(r=>r.fee_bps/10),c:css('--acc2')}}],{{zero:true,fmt:v=>v.toFixed(2),h:220}});
document.getElementById('funnelchart').insertAdjacentHTML('beforeend','<div class="lg"><span><i style="background:var(--acc)"></i>maker 成交率</span><span><i style="background:var(--good)"></i>maker 占比</span><span><i style="background:var(--acc2)"></i>费用 bps ÷10</span></div>');
const dn=lv.daily_nav;barChart('dailychart',dn.map(d=>({{l:d.day.slice(4),v:[d.pnl||0,d.funding||0]}})),{{colors:[css('--acc'),css('--acc2')],h:220}});
document.getElementById('dailychart').insertAdjacentHTML('beforeend','<div class="lg"><span><i style="background:var(--acc)"></i>REALIZED_PNL</span><span><i style="background:var(--acc2)"></i>FUNDING_FEE</span></div>');
const sg=D.sig;const sgIdx=[];sg.days.forEach((d,i)=>{{if(i==0||d.slice(0,4)!==sg.days[i-1].slice(0,4))sgIdx.push({{i,t:d.slice(0,4),k:0}});}});lineChart('sigchart',[{{x:sg.days,y:sg.v,c:css('--acc'),w:1.4,area:true}}],{{zero:true,fmt:v=>v.toFixed(0)+'bp',h:220,events:sgIdx}});
</script>
"""
open('WIDEBOOK_ATLAS.html','w').write(html); print("html bytes", len(html))
