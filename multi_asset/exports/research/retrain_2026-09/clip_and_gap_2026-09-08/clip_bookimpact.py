"""Book-level exposure to the clipped cells. Read-only.
Uses the health-check artifact weights (d30_n2_c42_W, 829-col symbol axis) x the meta y4s the replay actually scored."""
import numpy as np, json, time, calendar, sys
H="/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_%s.npz"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]; fsym=[str(s) for s in F["symbols"]]
# lo/hi split
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); r5=Z["data"][:,:,0].astype(np.float32); fin=np.isfinite(r5)
HI=np.float32(np.float16(0.3)); LO=np.float32(np.float16(-0.3))
CSlo=np.concatenate([np.zeros((1,len(fsym)),np.int32),np.cumsum((r5==LO)&fin,0,dtype=np.int32)])
CShi=np.concatenate([np.zeros((1,len(fsym)),np.int32),np.cumsum((r5==HI)&fin,0,dtype=np.int32)])
grid=np.where(CTS%14400==0)[0]; grid=grid[(grid>=8640)&(grid+288<=r5.shape[0])]
nlo=CSlo[grid+49]-CSlo[grid+1]; nhi=CShi[grid+49]-CShi[grid+1]
gts=CTS[grid]
del r5,fin,CSlo,CShi
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz",allow_pickle=True)
mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mem=MT["members"]; msym=[str(s) for s in MT["symbols"]] if "symbols" in MT.files else fsym
print("meta anchors %d, y4 shape %s, symbols match cache: %s"%(len(mts),y4.shape,msym==fsym))
tag="M1_UCRYPTO_prod_s42_ccal"
A=np.load(H%tag,allow_pickle=True); R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]
ats=R[:,C["ts"]].astype(np.int64); gt=R[:,C["gross_total"]]; ne=R[:,C["net_ex"]]
asym=[str(s) for s in A["symbols"]]
print("artifact anchors %d, W %s, symbol axis == cache: %s"%(len(ats),W.shape,asym==fsym))
# align
gi={t:i for i,t in enumerate(gts)}; mi={t:i for i,t in enumerate(mts)}
CUT=calendar.timegm((2026,8,10,20,0,0))
rows=[]
for p,t in enumerate(ats):
    if t not in gi or t not in mi: continue
    w=W[p].astype(np.float64); g=abs(w).sum()
    if g<=0: continue
    lo=nlo[gi[t]]>0; hi=nhi[gi[t]]>0; anyc=lo|hi
    yy=np.nan_to_num(y4[mi[t]].astype(np.float64),nan=0.0)
    rows.append((t, g,
        abs(w[anyc]).sum()/g,                       # gross share on clipped names
        float((w[anyc]*yy[anyc]).sum()/g*1e4),      # recorded bps/gross from clipped names
        float((w*yy).sum()/g*1e4),                  # recorded bps/gross total (unit book, pre-cost)
        abs(w[lo]).sum()/g, abs(w[hi]).sum()/g,
        float(w[lo].sum()/g), float(w[hi].sum()/g), # NET (signed) exposure -> direction of bias
        int(anyc.sum())))
rows=np.array(rows,float)
t=rows[:,0].astype(np.int64); m=t<=CUT
yr=np.array([time.gmtime(int(x)).tm_year for x in t])
print("\n== book exposure to clipped cells (arm %s) =="%tag)
print("%6s %7s %9s %14s %16s %16s %14s"%("year","anch","anch w/clip","mean gross share","Σ recorded bps/gross from clipped","of which on lo-clip(-30%) names","net long on lo"))
for y in sorted(set(yr[m].tolist())):
    s=m&(yr==y); n=int(s.sum()); nc=int((rows[s,9]>0).sum())
    print("%6d %7d %9d %15.4f%% %16.2f %16.2f %14.4f"%(y,n,nc,100*rows[s,2].mean(),rows[s,3].sum(),
        (rows[s,3]*(rows[s,5]>0)).sum(), rows[s,7].mean()))
print("\nTOTAL <=cut: anchors %d, anchors with >=1 clipped held name %d (%.2f%%)"%(m.sum(),(rows[m,9]>0).sum(),100*(rows[m,9]>0).mean()))
print("Σ recorded bps/gross attributable to clipped names: %.2f  (whole-book recorded Σ %.2f, share %.3f%%)"
      %(rows[m,3].sum(),rows[m,4].sum(),100*rows[m,3].sum()/max(abs(rows[m,4].sum()),1e-9)))
w=np.argsort(-np.abs(rows[m,3]))[:15]; sub=rows[m][w]
print("\n== 15 anchors where clipped names contributed most (|bps/gross|) ==")
print("%20s %10s %10s %8s %8s"%("anchor UTC","clip bps","book bps","gross%","n_names"))
for r in sub:
    print("%20s %10.2f %10.2f %7.3f%% %8d"%(time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(int(r[0]))),r[3],r[4],100*r[2],int(r[9])))
np.savez_compressed("/workspace/review_scratch/clip_bookimpact.npz",rows=rows)
