"""Restate the replay P&L on the 195 anchors that hold >=1 clipped name, using official 4h klines.
★ SELF-CHECK FIRST (morphology #20): on the SAME anchors, names with NO clipped bar must reproduce the
recorded y4s from official prices to float16 precision. If that fails the window definition is wrong -> stop."""
import numpy as np, json, os, time, calendar, csv
D="/workspace/review_scratch/clip_kl"
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]; syms=[str(s) for s in F["symbols"]]; sidx={s:i for i,s in enumerate(syms)}
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz",allow_pickle=True)
mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mi={t:i for i,t in enumerate(mts)}
A=np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s42_ccal.npz",allow_pickle=True)
R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]; ats=R[:,0].astype(np.int64); gtv=R[:,5]
gi={t:i for i,t in enumerate(fts)}
CACHE={}
def closes(s,ym):
    k=(s,ym)
    if k in CACHE: return CACHE[k]
    p=os.path.join(D,"%s_%s.csv"%(s,ym)); d={}
    if os.path.exists(p):
        for row in csv.reader(open(p)):
            try: d[int(row[0])//1000]=float(row[4])
            except Exception: pass
    CACHE[k]=d; return d
def close_at(s,t):
    ym=time.strftime("%Y-%m",time.gmtime(t)); c=closes(s,ym)
    if t in c: return c[t]
    y,m=map(int,ym.split("-")); m-=1
    if m==0: y,m=y-1,12
    c2=closes(s,"%04d-%02d"%(y,m)); return c2.get(t)
def true_y4s(s,t):
    a=close_at(s,t); b=close_at(s,t-14400)
    return None if (a is None or b is None or b<=0) else a/b-1.0
# ---------- SELF-CHECK on unclipped names ----------
rng=np.random.default_rng(7); chk=[]
aff=[p for p,t in enumerate(ats) if t in gi and (has[gi[t]]&(np.abs(W[p])>0)).any()]
for p in aff[:60]:
    t=int(ats[p]); w=W[p]; hit=has[gi[t]]
    cand=np.where((np.abs(w)>0)&(~hit))[0]
    for j in rng.choice(cand,size=min(8,len(cand)),replace=False):
        s=syms[j]; ty=true_y4s(s,t)
        if ty is None: continue
        ry=float(y4[mi[t],j]) if t in mi else np.nan
        if np.isfinite(ry): chk.append(abs(ty-ry))
chk=np.array(chk)
print("SELF-CHECK unclipped names: n=%d  max|true-recorded|=%.3e  p99=%.3e  (float16 rel. eps ~1e-3)"%(len(chk),chk.max(),np.percentile(chk,99)))
assert len(chk)>=100 and chk.max()<5e-3, "window definition disagrees with the recorded series -> STOP"
# ---------- restate ----------
CUT=calendar.timegm((2026,8,10,20,0,0)); out=[]; nores=0
for p in aff:
    t=int(ats[p]); w=W[p].astype(np.float64); g=np.abs(w).sum()
    if g<=0 or t not in mi: continue
    hit=has[gi[t]]&(np.abs(w)>0); d=0.0; nres=0
    for j in np.where(hit)[0]:
        ty=true_y4s(syms[j],t); ry=float(y4[mi[t],j])
        if ty is None or not np.isfinite(ry): nores+=1; continue
        d+=w[j]*(ty-ry); nres+=1
    out.append((t,float(d/g*1e4),float(gtv[p]),nres,int(hit.sum()),float(np.abs(w[hit]).sum()/g)))
out=np.array(out,float); t=out[:,0].astype(np.int64); m=t<=CUT
yr=np.array([time.gmtime(int(x)).tm_year for x in t])
print("\nunresolved cells: %d"%nores)
print("\n== P&L restatement: (true - recorded) in bps/gross, on the %d affected anchors <=cut =="%int(m.sum()))
print("%6s %8s %14s %14s %14s"%("year","anchors","Sum delta","worst anchor","best anchor"))
for y in sorted(set(yr[m].tolist())):
    s=m&(yr==y); print("%6d %8d %14.2f %14.2f %14.2f"%(y,int(s.sum()),out[s,1].sum(),out[s,1].min(),out[s,1].max()))
print("%6s %8d %14.2f %14.2f %14.2f"%("ALL",int(m.sum()),out[m,1].sum(),out[m,1].min(),out[m,1].max()))
n_all=9918
print("\nspread over ALL %d anchors <=cut: mean shift = %.4f bps/anchor per gross"%(n_all,out[m,1].sum()/n_all))
o=np.argsort(out[m,1])[:12]; sub=out[m][o]
print("\n== 12 anchors the replay flattered most (true worse than recorded) ==")
print("%20s %12s %12s %8s %10s"%("anchor UTC","delta bps","clip names","resolved","gross% on clip"))
for r in sub: print("%20s %12.2f %12d %8d %9.3f%%"%(time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(int(r[0]))),r[1],int(r[4]),int(r[3]),100*r[5]))
np.savez_compressed("/workspace/review_scratch/clip_restate.npz",out=out)
