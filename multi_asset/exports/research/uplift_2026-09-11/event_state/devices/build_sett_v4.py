"""Track G: settlement tables on the v4-pinned holefix2 5m cache. Writes only under uplift_2026-09-11/event_state/."""
import numpy as np, json, gzip, time, os, hashlib, zipfile, io
OUT="/workspace/uplift_2026-09-11/event_state"
FA="/workspace/fund_aug.json.gz"
F5="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
PANEL="/workspace/uplift_2026-09-11/dev_v4ev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz"
META="/workspace/uplift_2026-09-11/dev_v4ev/pod_backup_2026-08-21/wide_fea_hist_meta.npz"
t0=time.time()
PW=np.load(PANEL,allow_pickle=True); SY=[str(s) for s in PW["symbols"]]; NW=len(SY); kof={s:k for k,s in enumerate(SY)}
ts_a=PW["ts"].astype(np.int64); nA=len(ts_a)
MT=np.load(META,allow_pickle=True)
z=zipfile.ZipFile(F5)
ts5=np.load(io.BytesIO(z.read("ts.npy"))).astype(np.int64)
sy5=[str(s) for s in np.load(io.BytesIO(z.read("symbols.npy")),allow_pickle=True)]
ch=[str(c) for c in np.load(io.BytesIO(z.read("ch.npy")),allow_pickle=True)]
assert sy5==SY and ch[0]=="ret5" and np.all(np.diff(ts5)==300)
print("loading 5m holefix2 ...",flush=True)
D5=np.load(F5)["data"]; ret5=D5[:,:,0].astype(np.float32); del D5
print(f"ret5 {ret5.shape} {time.time()-t0:.0f}s finite {np.isfinite(ret5).mean():.4f}",flush=True)
# --- convention receipt on THIS cache against the v4 meta y4
E=MT["E_ts"].astype(np.int64); y4=MT["y4"]
row5={int(t):r for r,t in enumerate(ts5)}
rng=np.random.default_rng(0); a=[];b=[]
for i in rng.choice(np.arange(500,len(E)-100),400,replace=False):
    r0=row5.get(int(E[i]))
    if r0 is None: continue
    for k in rng.choice(NW,3,replace=False):
        if np.isfinite(y4[i,k]) and np.isfinite(ret5[r0:r0+48,k]).all() and np.isfinite(ret5[r0+1:r0+49,k]).all():
            a.append(abs(float(y4[i,k])-float(ret5[r0:r0+48,k].sum()))); b.append(abs(float(y4[i,k])-float(ret5[r0+1:r0+49,k].sum())))
conv={"n":len(a),"median_abs_err_bar_starting_E..E+47":float(np.median(a)),"median_abs_err_bar_ending_E+1..E+48":float(np.median(b))}
print("CONV",conv,flush=True)
# --- settlement events
d=json.load(gzip.open(FA,"rt")); R_=d["rates"]
evs_t=[]; evs_k=[]; evs_r=[]; evs_dr=[]; evs_miss=[]
n_out=0; n_no5=0
T0=ts_a[0]-40*86400; T1=ts_a[-1]
for s,rows in R_.items():
    k=kof.get(s)
    if k is None: continue
    t=np.array([r[0] for r in rows],np.int64)//1000; v=np.array([r[1] for r in rows],np.float64)
    o=np.argsort(t); t=t[o]; v=v[o]
    for n in range(len(t)):
        S=int(t[n])
        if S<T0 or S>T1: n_out+=1; continue
        r5=row5.get(S)
        if r5 is None or r5-2<0 or r5+5>len(ts5): n_no5+=1; continue
        w=ret5[r5-2:r5+5,k]; ok=np.isfinite(w); m=int((~ok).sum())
        dr=float(np.prod(1.0+w[ok])-1.0) if ok.any() else np.nan
        evs_t.append(S); evs_k.append(k); evs_r.append(float(v[n])); evs_dr.append(dr); evs_miss.append(m)
ET=np.array(evs_t,np.int64); EK=np.array(evs_k,np.int32); ER=np.array(evs_r,np.float64); EDR=np.array(evs_dr,np.float64); EM=np.array(evs_miss,np.int8)
o=np.lexsort((EK,ET)); ET,EK,ER,EDR,EM=ET[o],EK[o],ER[o],EDR[o],EM[o]
print(f"events {len(ET)} out-of-range {n_out} no-5m {n_no5} missingbar {(EM>0).mean():.4f} {time.time()-t0:.0f}s",flush=True)
# --- raw-rate histogram atoms (cap detection) — data-definition step
av=np.abs(ER); uq,cnt=np.unique(np.round(av,6),return_counts=True)
top=[(float(uq[i]),int(cnt[i])) for i in np.argsort(-cnt)[:25]]
print("RATE_ATOMS",top,flush=True)
np.savez_compressed(f"{OUT}/sett_v4.npz",ts=ET,k=EK,rate=ER,dr=EDR,miss=EM,symbols=np.array(SY),anchors=ts_a)
rec={"f5":F5,"panel":PANEL,"meta":META,"fund_aug_sha256":hashlib.sha256(open(FA,"rb").read()).hexdigest(),
     "n_events":int(len(ET)),"events_out_of_range":n_out,"events_no_5m_row":n_no5,
     "events_with_missing_bar_share":float((EM>0).mean()),"conv":conv,
     "window":"7 bars starting S-10m..S+20m = [S-10m,S+25m); bar-STARTING ret5",
     "rate_atoms_top25":top,"elapsed_s":round(time.time()-t0,1)}
json.dump(rec,open(f"{OUT}/sett_v4_receipt.json","w"),indent=1)
print("BUILD_DONE",flush=True)
