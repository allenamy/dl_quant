import numpy as np, os, time, calendar, csv, json
D="/workspace/review_scratch/clip_kl"
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]; syms=[str(s) for s in F["symbols"]]
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz",allow_pickle=True)
mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mi={t:i for i,t in enumerate(mts)}
A=np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s42_ccal.npz",allow_pickle=True)
R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]; ats=R[:,0].astype(np.int64)
gi={t:i for i,t in enumerate(fts)}; ai={t:i for i,t in enumerate(ats)}
T=calendar.timegm((2025,10,10,20,0,0))
p=ai[T]; w=W[p].astype(np.float64); g=np.abs(w).sum(); hit=has[gi[T]]
print("anchor 2025-10-10 20:00Z  gross_total=%.4f  held names=%d"%(R[p,5],int((np.abs(w)>0).sum())))
print("clipped names in universe: %d ; HELD and clipped: %d ; gross share held&clipped: %.3f%%"
      %(int(hit.sum()), int((hit&(np.abs(w)>0)).sum()), 100*np.abs(w[hit&(np.abs(w)>0)]).sum()/g))
print("gross share of w over ALL clipped(universe incl. unheld): %.3f%%"%(100*np.abs(w[hit]).sum()/g))
CACHE={}
def closes(s,ym):
    k=(s,ym)
    if k in CACHE: return CACHE[k]
    fp=os.path.join(D,"%s_%s.csv"%(s,ym)); d={}
    if os.path.exists(fp):
        for row in csv.reader(open(fp)):
            try: d[int(row[0])//1000]=float(row[4])
            except Exception: pass
    CACHE[k]=d; return d
def close_at(s,t):
    ym=time.strftime("%Y-%m",time.gmtime(t)); c=closes(s,ym)
    if t in c: return c[t]
    y,m=map(int,ym.split("-")); m-=1
    if m==0: y,m=y-1,12
    return closes(s,"%04d-%02d"%(y,m)).get(t)
idx=np.where(hit&(np.abs(w)>0))[0]
rows=[]
for j in idx:
    s=syms[j]; a=close_at(s,T); b=close_at(s,T-14400)
    if a is None or b is None: rows.append((s,w[j],float(y4[mi[T],j]),None)); continue
    rows.append((s,w[j],float(y4[mi[T],j]),a/b-1.0))
res=[r for r in rows if r[3] is not None]
print("resolved %d/%d"%(len(res),len(rows)))
dr=sum(r[1]*(r[3]-r[2]) for r in res)/g*1e4
print("Δ(true-recorded) on this anchor = %+.2f bps/gross"%dr)
rec=sum(r[1]*r[2] for r in res)/g*1e4; tru=sum(r[1]*r[3] for r in res)/g*1e4
print("  recorded contribution from these names %+.2f bps ; true %+.2f bps"%(rec,tru))
lw=[r for r in res if r[1]>0]; sw=[r for r in res if r[1]<0]
print("  LONG  %d names: recorded %+.2f  true %+.2f  Δ %+.2f"%(len(lw),sum(r[1]*r[2] for r in lw)/g*1e4,sum(r[1]*r[3] for r in lw)/g*1e4,sum(r[1]*(r[3]-r[2]) for r in lw)/g*1e4))
print("  SHORT %d names: recorded %+.2f  true %+.2f  Δ %+.2f"%(len(sw),sum(r[1]*r[2] for r in sw)/g*1e4,sum(r[1]*r[3] for r in sw)/g*1e4,sum(r[1]*(r[3]-r[2]) for r in sw)/g*1e4))
res.sort(key=lambda r: r[1]*(r[3]-r[2]))
print("\n%-14s %9s %10s %10s %10s"%("symbol","weight","recorded","true","Δcontrib bps"))
for r in res[:10]+res[-6:]:
    print("%-14s %9.5f %9.2f%% %9.2f%% %10.2f"%(r[0],r[1],100*r[2],100*r[3],r[1]*(r[3]-r[2])/g*1e4))
