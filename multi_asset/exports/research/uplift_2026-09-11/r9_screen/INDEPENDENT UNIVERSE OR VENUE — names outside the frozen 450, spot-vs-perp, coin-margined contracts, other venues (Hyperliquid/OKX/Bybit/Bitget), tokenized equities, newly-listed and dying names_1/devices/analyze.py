"""OKXRHO screen: rho to A0 (unconditional + conditional on A0-loss cells) + standalone edge.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, json, datetime as dt
from scipy.stats import rankdata
OUT="/workspace/r9okx"
A0B="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/"
MINE=f"{OUT}/dev/probe_artifacts/"
CAP=1788120000                       # 2026-08-30 20:00Z, E-0911-D
BURN_DAYS=14                         # EMA(HL=3d) cold-start + book-state burn-in, declared in advance

def series(path,key):
    a=np.load(path,allow_pickle=True); cols=[str(c) for c in a["cols"]]; ci={c:i for i,c in enumerate(cols)}
    r=a[key]; ts=r[:,ci["ts"]].astype(np.int64)
    g=r[:,ci["net_ex"]]/np.where(r[:,ci["gross_total"]]>0,r[:,ci["gross_total"]],np.nan)
    return ts, g, r[:,ci["turnover"]], r[:,ci["gross_total"]], r[:,ci["cost_ex"]], r[:,ci["carry_ex"]]

def spearman(x,y):
    return float(np.corrcoef(rankdata(x),rankdata(y))[0,1])

def day_blocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==k)[0] for k in range(len(u))]

def boot_stat(fn, ts, *arrs, B=2000):
    blk=day_blocks(ts); nb=len(blk); out=np.empty(B)
    for k in range(B):
        rng=np.random.default_rng([20260905,k])
        pick=rng.integers(0,nb,nb)
        idx=np.concatenate([blk[p] for p in pick])
        out[k]=fn(*[a[idx] for a in arrs])
    return out

def ci(v): return float(np.percentile(v,2.5)), float(np.percentile(v,97.5))

res={"caliber":"v4 chain 2026-09-09","cap_ts":CAP,"burn_days":BURN_DAYS}
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True); T0=int(fe["okx_t0"])
LO=T0+BURN_DAYS*86400
res["window"]={"okx_first_settlement":dt.datetime.utcfromtimestamp(T0).isoformat()+"Z",
               "screen_lo":dt.datetime.utcfromtimestamp(LO).isoformat()+"Z",
               "screen_hi":dt.datetime.utcfromtimestamp(CAP).isoformat()+"Z"}

ARMS={"OKX":"w10_ablation_series_R9_OKX_fund.npz",
      "OKX_noFTRIM":"w10_ablation_series_R9_OKX_fund_nt.npz",
      "BINCOLD":"w10_ablation_series_R9_BINCOLD_fund.npz",
      "BINCOLD_noFTRIM":"w10_ablation_series_R9_BINCOLD_fund_nt.npz",
      "BINWARM":"w10_ablation_series_R9_BINWARM_fund.npz",
      "BINPANEL":"w10_ablation_series_R9_BINPANEL_fund.npz",
      "BINPANEL_noFTRIM":"w10_ablation_series_R9_BINPANEL_fund_nt.npz",
      "BINCOLD388":"w10_ablation_series_R9_BINCOLD388_fund.npz",
      "BINCOLD388_noFTRIM":"w10_ablation_series_R9_BINCOLD388_fund_nt.npz",
      "BINWARM388":"w10_ablation_series_R9_BINWARM388_fund.npz",
      "OKX_SUP":"w10_ablation_series_R9_OKXSUP_fund.npz",
      "BINCOLD_SUP":"w10_ablation_series_R9_BINCOLDSUP_fund.npz"}
A0S={"A0_dyn_s42":"w10_ablation_series_V4_A0_dyn_s42.npz",
     "A0_dyn_s2027":"w10_ablation_series_V4_A0_dyn_s2027.npz"}

BOOK="d30_n2_c42_rec"     # live shape
res["book_key"]=BOOK
A0={}
for n,f in A0S.items():
    ts,g,tn,gt,c,ca=series(A0B+f,BOOK); A0[n]=(ts,g)
    k=(np.arange(len(ts))>=900)&(ts<=CAP)
    res.setdefault("A0_fullwindow_postwarm",{})[n]={
        "n":int(k.sum()),"mean_g":round(float(g[k].mean()),4),
        "sharpe_ann":round(float(g[k].mean()/g[k].std(ddof=1)*np.sqrt(2190)),4)}

rows={}
for tag,f in ARMS.items():
    p=MINE+f
    if not os.path.exists(p): continue
    ts,g,tn,gt,c,ca=series(p,BOOK)
    rows[tag]=dict(ts=ts,g=g,tn=tn,gt=gt,c=c,ca=ca)

out={}
for tag,d in rows.items():
    e={}
    for a0n,(ats,ag) in A0.items():
        amap={int(t):i for i,t in enumerate(ats)}
        sel=[(i,amap[int(t)]) for i,t in enumerate(d["ts"]) if int(t) in amap and LO<=int(t)<=CAP]
        i1=np.array([x[0] for x in sel]); i2=np.array([x[1] for x in sel])
        x=d["g"][i1]; y=ag[i2]; ts=d["ts"][i1]
        ok=np.isfinite(x)&np.isfinite(y); x,y,ts=x[ok],y[ok],ts[ok]
        pr=float(np.corrcoef(x,y)[0,1]); sp=spearman(x,y)
        bs=boot_stat(lambda a,b: float(np.corrcoef(a,b)[0,1]), ts, x, y)
        lo,hi=ci(bs)
        # conditional on A0-loss cells
        m=y<0
        prc=float(np.corrcoef(x[m],y[m])[0,1]) if m.sum()>20 else None
        bsc=boot_stat(lambda a,b: (float(np.corrcoef(a[b<0],b[b<0])[0,1]) if (b<0).sum()>20 else np.nan), ts, x, y)
        bsc=bsc[np.isfinite(bsc)]; cl,ch=(ci(bsc) if len(bsc)>100 else (None,None))
        # A0 worst quintile
        q=np.quantile(y,0.2); mq=y<=q
        prq=float(np.corrcoef(x[mq],y[mq])[0,1]) if mq.sum()>20 else None
        e[a0n]={"n":int(len(x)),"pearson":round(pr,4),"spearman":round(sp,4),"ci95":[round(lo,4),round(hi,4)],
                "n_A0_loss":int(m.sum()),"pearson_in_A0_loss":(round(prc,4) if prc is not None else None),
                "ci95_in_A0_loss":([round(cl,4),round(ch,4)] if cl is not None else None),
                "pearson_in_A0_worst_quintile":(round(prq,4) if prq is not None else None),
                "mean_g_cand_in_A0_loss":round(float(x[m].mean()),4) if m.sum()>0 else None,
                "mean_g_A0_in_A0_loss":round(float(y[m].mean()),4) if m.sum()>0 else None}
    # standalone on the screen window
    k=(d["ts"]>=LO)&(d["ts"]<=CAP)&np.isfinite(d["g"])
    x=d["g"][k]; ts=d["ts"][k]
    bm=boot_stat(lambda a: float(a.mean()), ts, x); mlo,mhi=ci(bm)
    sr=float(x.mean()/x.std(ddof=1)*np.sqrt(2190))
    e["standalone"]={"n":int(k.sum()),"mean_g":round(float(x.mean()),4),"ci95_mean_g":[round(mlo,4),round(mhi,4)],
        "sharpe_ann":round(sr,4),"se_sharpe":round(float(np.sqrt(2190/k.sum())),4),
        "turnover_mean":round(float(d["tn"][k].mean()),5),
        "cost_ex_mean":round(float(d["c"][k].mean()),4),"carry_ex_mean":round(float(d["ca"][k].mean()),4),
        "gross_total_mean":round(float(d["gt"][k].mean()),4)}
    out[tag]=e
res["arms"]=out
# ---- cross-arm rho matrix on the screen window (candidate vs its own controls) ----
def gser(tag):
    d=rows[tag]; k=(d["ts"]>=LO)&(d["ts"]<=CAP)&np.isfinite(d["g"])
    return d["ts"][k], d["g"][k]
cm={}
tags=[t for t in ("OKX","OKX_SUP","BINCOLD_SUP","BINCOLD388","BINWARM388","BINCOLD","BINPANEL") if t in rows]
for i,a in enumerate(tags):
    ta,ga=gser(a); ma={int(t):v for t,v in zip(ta,ga)}
    for b in tags[i+1:]:
        tb,gb=gser(b); common=[t for t in tb if int(t) in ma]
        x=np.array([ma[int(t)] for t in common]); y=np.array([gb[list(tb).index(t)] for t in common])
        mb={int(t):v for t,v in zip(tb,gb)}
        x=np.array([ma[t] for t in [int(z) for z in common]]); y=np.array([mb[t] for t in [int(z) for z in common]])
        ts=np.array([int(z) for z in common])
        bs=boot_stat(lambda p,q: float(np.corrcoef(p,q)[0,1]), ts, x, y); lo,hi=ci(bs)
        cm[f"{a}~{b}"]={"n":len(x),"pearson":round(float(np.corrcoef(x,y)[0,1]),4),"ci95":[round(lo,4),round(hi,4)]}
res["cross_arm_rho"]=cm
print(json.dumps(res,indent=1))
json.dump(res,open(f"{OUT}/RESULT_okxrho.json","w"),indent=1)
