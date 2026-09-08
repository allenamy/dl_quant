"""judge_costdose.py — PREREG_dl_path_cost_dose_2026-09-08 (sha ce7a6be927a4c31284e58b3db1d682eb89a59903f7b3a2cc16ce0d1c23728d96).
WRITTEN BEFORE ANY BOOK-LAYER NUMBER OF THIS FAMILY EXISTS (training done, replay not yet run at authoring time).
All readings (§3.0 gate0, §3.1 primary, §3.2 dose, §3.3 pre-committed conditional, §3.4 attribution, §3.5 NI, §3.6 secondaries)
are transcribed VERBATIM from the prereg and may not be edited after numbers are seen.
Device lineage identical to judge_trainfrac.py: d30_n2_c42, g = net_ex/gross_total per anchor, UTC-day block 2000 seed 20260905."""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
TF="/workspace/review_scratch/trainfrac/replay/dev_alt/probe_artifacts"
CD="/workspace/review_scratch/costdose/replay/dev_alt/probe_artifacts"
G_="/workspace/review_scratch/dl_monthly_gate/replay/dev_alt/probe_artifacts"
PRD="/workspace/review_scratch/allweather_trackB/replay/dev_alt/f8_2026-08-22/preds"
OUT="/workspace/review_scratch/costdose/results"; os.makedirs(OUT,exist_ok=True)
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
ARM="d30_n2_c42"; NB=2000; SEED=20260905; DELTA=0.05
CUT=calendar.timegm((2026,8,10,20,0,0)); T25=calendar.timegm((2025,1,1,0,0,0))
T2503=calendar.timegm((2025,3,1,0,0,0)); T26=calendar.timegm((2026,1,1,0,0,0))
EXPECT={"LEGS":"101","CAL":"log","LOOK":900,"WRULE":"msharpe","MEMBERS_TOPN":829,"TRADE_TOPN":0,"FTRIM":"zero","UMASK_SCOPE":"m1","W3FIX":None,"SLOW_NPY":"/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
ARMS={"yearly_s42":(f"{G_}/w10_ablation_series_BASE_s42.npz",None,None),
      "FIX7":      (f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz","f10_gate_mE1cX7_R0_spl42.npy",3.52),
      "C2_85":     (f"{CD}/w10_ablation_series_G_mE1c2f85_R0_spl42.npz","f10_gate_mE1c2f85_R0_spl42.npy",7.04),
      "C4_85":     (f"{CD}/w10_ablation_series_G_mE1c4f85_R0_spl42.npz","f10_gate_mE1c4f85_R0_spl42.npy",14.08),
      "X7FULL":    (f"{TF}/w10_ablation_series_G_mE1x7full_R0_spl42.npz","f10_gate_mE1x7full_R0_spl42.npy",3.52),
      "C2_FULL":   (f"{CD}/w10_ablation_series_G_mE1c2full_R0_spl42.npz","f10_gate_mE1c2full_R0_spl42.npy",7.04),
      "C4_FULL":   (f"{CD}/w10_ablation_series_G_mE1c4full_R0_spl42.npz","f10_gate_mE1c4full_R0_spl42.npy",14.08)}
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()
D={};W={};META={}
for k,(p,_,_) in ARMS.items():
    assert os.path.exists(p), f"MISSING ARM ARTIFACT {k}: {p} — judge refuses to run on a partial arm set"
    z=np.load(p,allow_pickle=True); cfg=json.loads(str(z["config_json"]))
    assert [str(c) for c in z["cols"]]==COLS,k
    for kk,v in EXPECT.items(): assert cfg.get(kk)==v,(k,kk,cfg.get(kk),v)
    assert cfg["FSEED"]=="42" and abs(cfg["PHI"]-0.45)<1e-12 and cfg.get("PHIDYN",0)==0,k
    R=z[f"{ARM}_rec"]; D[k]={c:R[:,i] for i,c in enumerate(COLS)}; W[k]=z[f"{ARM}_W"]
    META[k]={"artifact":p,"sha256_16":sha(p)[:16],"FPRED":cfg["FPRED"],"n":int(len(R))}
ks=list(D); ts0=D["FIX7"]["ts"].astype(np.int64)
for k in ks: assert np.array_equal(D[k]["ts"].astype(np.int64),ts0),k
days=ts0//86400
months=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts0])
yrs=np.array([time.gmtime(int(t)).tm_year for t in ts0])
WIN={"FROZEN":(ts0>=T2503)&(ts0<=CUT),"2026<=cut":(ts0>=T26)&(ts0<=CUT),"FULL":(ts0>=T25)&(ts0<=CUT)}
PW,W26,FW="FROZEN","2026<=cut","FULL"
G={k:D[k]["net_ex"]/D[k]["gross_total"] for k in ks}
TPG={k:D[k]["turnover"]/D[k]["gross_total"] for k in ks}
rng=np.random.default_rng(SEED)
def boot(x,m):
    v=x[m]; d=days[m]; ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    s=np.bincount(inv,weights=v,minlength=nd); c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); mn=s[idx].sum(1)/c[idx].sum(1)
    return {"n":int(m.sum()),"mean":float(v.mean()),"lo":float(np.percentile(mn,2.5)),"hi":float(np.percentile(mn,97.5)),"P>0":float((mn>0).mean())}
def sharpe(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
def maxdd(x): c=np.cumsum(x); return float(np.max(np.maximum.accumulate(c)-c))
T=[]
def p(s=""): T.append(s); print(s)
O={"prereg_sha256":"ce7a6be927a4c31284e58b3db1d682eb89a59903f7b3a2cc16ce0d1c23728d96","arm":ARM,"delta":DELTA,"arms":META,"bootstrap":{"blocks":"UTC day","n":NB,"seed":SEED},"levels":{},"deltas":{},"reading":{}}
p(f"<!-- judge_costdose.py (written before any book number of this family) prereg ce7a6be927a4c312; n={len(ts0)}; UTC-day block {NB} seed {SEED}; delta={DELTA} -->")
p("## CD-1 · Levels per gross (bps/anchor)")
p("| arm | COST | FROZEN [CI95] | S | maxDD | **turn/gross** | 2026<=cut | FULL |"); p("|---|---|---|---|---|---|---|---|")
for k in ks:
    row={}
    for w,m in WIN.items():
        x=G[k][m]; row[w]={"n":int(m.sum()),"mean":float(x.mean()),"sharpe":sharpe(x),"maxDD_bps":maxdd(x),"turn":float(TPG[k][m].mean()),"boot":boot(G[k],m)}
    O["levels"][k]=row; a=row[PW]
    p(f"| {k} | {ARMS[k][2]} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} | **{a['turn']:.5f}** | {row[W26]['mean']:+.3f} | {row[FW]['mean']:+.3f} |")
# ── §3.0 GATE 0: turnover monotone in dose within each recipe (replay caliber) ──
p("\n## CD-2 · §3.0 门 0(机制是否咬住): 换手/gross 须随剂量单调下降")
g0={}
for fam,arms in (("85%",["FIX7","C2_85","C4_85"]),("FULL",["X7FULL","C2_FULL","C4_FULL"])):
    t=[O["levels"][a][PW]["turn"] for a in arms]
    mono=bool(t[0]>t[1]>t[2]); g0[fam]={"arms":arms,"turnover":t,"monotone_down":mono}
    p(f"  {fam}: {arms[0]} {t[0]:.5f} > {arms[1]} {t[1]:.5f} > {arms[2]} {t[2]:.5f}  ⇒ 单调下降 = **{mono}**")
GATE0=bool(g0["85%"]["monotone_down"] and g0["FULL"]["monotone_down"])
p(f"\n**GATE 0 = {GATE0}**" + ("" if GATE0 else "  ⇒ ★ 旋钮未咬住, 按 §3.0 本轮不得作任何书层结论"))
O["reading"]["gate0"]=g0; O["reading"]["gate0_pass"]=GATE0
PAIRS=[("C2_FULL","FIX7","C2_FULL − FIX7 [§3.1 primary d=7.04]"),("C4_FULL","FIX7","C4_FULL − FIX7 [§3.1 primary d=14.08]"),
       ("C2_85","FIX7","C2_85 − FIX7 [§3.2 dose 85%]"),("C4_85","FIX7","C4_85 − FIX7 [§3.2 dose 85%]"),
       ("C2_FULL","X7FULL","C2_FULL − X7FULL [§3.2 dose FULL]"),("C4_FULL","X7FULL","C4_FULL − X7FULL [§3.2 dose FULL]"),
       ("C2_85","yearly_s42","C2_85 − yearly_s42 [§3.5 NI]"),("C4_85","yearly_s42","C4_85 − yearly_s42 [§3.5 NI]"),
       ("C2_FULL","yearly_s42","C2_FULL − yearly_s42 [§3.5 NI]"),("C4_FULL","yearly_s42","C4_FULL − yearly_s42 [§3.5 NI]"),
       ("X7FULL","FIX7","X7FULL − FIX7 [device integrity: must reproduce −0.058 [−0.212,+0.103]]")]
p("\n## CD-3 · Paired Δ per gross (两侧臂名同行打印 — E-0907-E)")
p("| contrast | **FROZEN** | **2026≤cut** | FULL | Δturn% | maxDD ref→x | Δ w/o best month |"); p("|---|---|---|---|---|---|---|")
for kx,ky,name in PAIRS:
    dg=G[kx]-G[ky]; res={w:boot(dg,WIN[w]) for w in WIN}
    mc={str(mo):float(dg[(months==mo)&WIN[PW]].sum()) for mo in sorted(set(months[WIN[PW]].tolist()))}
    best=max(mc,key=mc.get); drop=boot(dg,WIN[PW]&(months!=int(best)))
    tx,ty=O["levels"][kx][PW]["turn"],O["levels"][ky][PW]["turn"]
    O["deltas"][name]={"x":kx,"ref":ky,"windows":res,"dturn_pct":(tx/ty-1)*100,"drop_best_month":drop,"best_month":best,
                       "maxDD_ref":O["levels"][ky][PW]["maxDD_bps"],"maxDD_x":O["levels"][kx][PW]["maxDD_bps"]}
    f=lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}"
    p(f"| {name} | **{f(PW)}** | **{f(W26)}** | {f(FW)} | {(tx/ty-1)*100:+.1f}% | {O['levels'][ky][PW]['maxDD_bps']:.0f}→{O['levels'][kx][PW]['maxDD_bps']:.0f} | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] (best {best}) |")
# ── §3.1 primary ──
d2=O["deltas"]["C2_FULL − FIX7 [§3.1 primary d=7.04]"]; d4=O["deltas"]["C4_FULL − FIX7 [§3.1 primary d=14.08]"]
A_d2=bool(d2["windows"][PW]["lo"]>0 and d2["windows"][W26]["mean"]>=0)
A_d4=bool(d4["windows"][PW]["lo"]>0 and d4["windows"][W26]["mean"]>=0)
A=bool(A_d2 or A_d4); B=bool(d2["windows"][PW]["hi"]<0 and d4["windows"][PW]["hi"]<0)
verdict=("(A) PATH-2 SUPPORTED" if A else ("(B) PATH-2 REFUTED" if B else "(C) UNDECIDED")) if GATE0 else "(GATE-0 FAIL) 不作书层结论"
p("\n## CD-4 · §3.1 主门(逐字转录)")
p("| 剂量 | CI 下界 > 0 | 2026 点估计 ≥ 0 | (A) 该剂量成立 |"); p("|---|---|---|---|")
p(f"| 7.04 | {d2['windows'][PW]['lo']:+.4f} → {d2['windows'][PW]['lo']>0} | {d2['windows'][W26]['mean']:+.4f} → {d2['windows'][W26]['mean']>=0} | **{A_d2}** |")
p(f"| 14.08 | {d4['windows'][PW]['lo']:+.4f} → {d4['windows'][PW]['lo']>0} | {d4['windows'][W26]['mean']:+.4f} → {d4['windows'][W26]['mean']>=0} | **{A_d4}** |")
p(f"| (B) 两剂量 CI 上界均 < 0 | {d2['windows'][PW]['hi']:+.4f} / {d4['windows'][PW]['hi']:+.4f} | | **{B}** |")
p(f"\n**VERDICT: {verdict}**")
O["reading"]["primary"]={"A_d2":A_d2,"A_d4":A_d4,"A":A,"B":B,"verdict":verdict}
# ── §3.3 pre-committed conditional ──
c2=O["deltas"]["C2_85 − FIX7 [§3.2 dose 85%]"]; c4=O["deltas"]["C4_85 − FIX7 [§3.2 dose 85%]"]
trig=bool(c2["windows"][PW]["lo"]>0 or c4["windows"][PW]["lo"]>0)
p("\n## CD-5 · §3.3 预先承诺的条件动作")
p(f"  C2_85 − FIX7 CI 下界 {c2['windows'][PW]['lo']:+.4f} | C4_85 − FIX7 CI 下界 {c4['windows'][PW]['lo']:+.4f}")
p(f"  **触发 = {trig}** — 若 True: 本轮发现是关于 COST 的, 不是关于近期标签的; **不得把满窗写成候选**, 满窗维持 RESULT_dl_full_gradient_window 的 (C) 判决。")
O["reading"]["conditional_action_triggered"]=trig
# ── §3.4 attribution: score IC, weight IC, ledger split ──
A_t=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)
E=A_t["E_ts"].astype(np.int64); MEM=A_t["members"]; Y=A_t["y4s"]; nA=len(E)
off=int(np.searchsorted(E,ts0[0])); mfz=WIN[PW]
def ext(fn):
    Q=np.full((nA,829),np.nan,np.float32); X=np.load(f"{PRD}/{fn}"); Q[:len(X)]=X; return Q
p("\n## CD-6 · §3.4 归因: 分数层 IC / 权重层 IC / 账本分项")
p("| arm | 分数 IC | 权重 IC | Δ价格 vs 同族基线 | Δcarry | Δ费用 |"); p("|---|---|---|---|---|---|")
IC={}
for k in ks:
    fn=ARMS[k][1]
    if fn is None: IC[k]=(float("nan"),float("nan")); continue
    Q=ext(fn); si=[]; wi=[]
    for i in range(len(ts0)):
        if not mfz[i]: continue
        g=off+i; mm=MEM[g]; y=Y[g,mm]; a=Q[g,mm]; wv=W[k][i,mm]
        ok=np.isfinite(y)&np.isfinite(a)
        if ok.sum()>=30: si.append(spearmanr(a[ok],y[ok]).correlation)
        o2=np.isfinite(y)&np.isfinite(wv)
        if o2.sum()>=30 and np.std(wv[o2])>0: wi.append(spearmanr(wv[o2],y[o2]).correlation)
    IC[k]=(float(np.mean(si)),float(np.mean(wi)))
BASE={"C2_85":"FIX7","C4_85":"FIX7","C2_FULL":"X7FULL","C4_FULL":"X7FULL"}
for k in ks:
    if ARMS[k][1] is None: continue
    b=BASE.get(k)
    if b:
        dp=((D[k]["pnl_ex"]/D[k]["gross_total"]-D[b]["pnl_ex"]/D[b]["gross_total"])[mfz]).mean()
        dc=((D[k]["carry_ex"]/D[k]["gross_total"]-D[b]["carry_ex"]/D[b]["gross_total"])[mfz]).mean()
        dk=((D[k]["cost_ex"]/D[k]["gross_total"]-D[b]["cost_ex"]/D[b]["gross_total"])[mfz]).mean()
        s=f"{dp:+.5f} | {dc:+.5f} | {dk:+.5f}"
    else: s="— | — | —"
    p(f"| {k} | {IC[k][0]:+.5f} | {IC[k][1]:+.5f} | {s} |")
O["reading"]["ic"]={k:{"score":IC[k][0],"weight":IC[k][1]} for k in IC}
# ── §3.5 NI leg, proper form ──
p(f"\n## CD-7 · §3.5 非劣腿 vs yearly_s42 — **正确形式 (E-0907-F): pass ⇔ CI 下界 > −δ**, δ={DELTA}")
p("| arm − ref | window | Δ | CI95 | **CI 下界** | −δ | **NI PASS?** | 旧决策规则 |"); p("|---|---|---|---|---|---|---|---|")
ni={}
for nm in [x[2] for x in PAIRS if "§3.5" in x[2]]:
    for w in (PW,W26):
        r=O["deltas"][nm]["windows"][w]
        ok=bool(r["lo"]>-DELTA); old=bool(r["mean"]>=-DELTA and ((r["lo"]<=0<=r["hi"]) or r["lo"]>0))
        ni[f"{nm}|{w}"]={"delta":DELTA,"mean":r["mean"],"lo":r["lo"],"ni_pass":ok,"old_rule":old}
        p(f"| {nm.split(' [')[0]} | {w} | {r['mean']:+.4f} | [{r['lo']:+.4f},{r['hi']:+.4f}] | **{r['lo']:+.4f}** | {-DELTA:+.2f} | **{ok}** | {old} |")
O["reading"]["non_inferiority"]=ni
p("> 措辞纪律(E-0907-F): 只有 NI PASS 为 True 才可写「非劣于年折」; 仅满足旧规则的只能写「未过冻结决策规则的否决线」, 且 δ 与下界须同行印出。")
# ── §3.6 full-cycle yearly (E-0904-B) ──
p("\n## CD-8 · §3.6 全周期逐年表(E-0904-B; 负年份显式; 2025 前为 spl42 拼接自 yearly, 非本配方)")
p("| 窗 | " + " | ".join(ks) + " |"); p("|" + "---|"*(len(ks)+1))
for lab,mm in [(f"{y} 全年",(yrs==y)&(ts0<=CUT)) for y in (2022,2023,2024,2025)]+[("2026≤cut",WIN[W26]),("★冻结",WIN[PW]),("全史≤cut",ts0<=CUT)]:
    cells=[]
    for k in ks:
        x=G[k][mm]; cells.append(f"{x.mean():+.3f}/{sharpe(x):+.2f}" if len(x)>10 else "—")
    p(f"| {lab} (n={int(mm.sum())}) | " + " | ".join(cells) + " |")
json.dump(O,open(f"{OUT}/judge_costdose.json","w"),indent=1,default=float)
open(f"{OUT}/costdose_tables.md","w").write("\n".join(T)+"\n")
print(f"\nwrote {OUT}/judge_costdose.json + costdose_tables.md")
