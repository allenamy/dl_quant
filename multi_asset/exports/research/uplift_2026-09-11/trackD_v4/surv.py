"""Survivorship probe: does the 829-name panel contain names that STOP trading mid-sample, and how much
of each candidate sleeve's long book sits in names that later disappear?"""
import numpy as np, time, json
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]; NW=829
last=np.full(NW,-1,np.int64); first=np.full(NW,10**9,np.int64)
for i in range(len(E)):
    m=np.asarray(mem[i]); ok=np.isfinite(y4[i,m]); idx=m[ok]
    last[idx]=i
    new=idx[first[idx]==10**9]
    if len(new): first[new]=i
END=len(E)-1
dead=(last>=0)&(last<END-60)     # stops >10 days before the end of the sample
print("names ever present:", int((last>=0).sum()))
print("names whose last anchor is >60 anchors before the sample end (DELISTED/dropped):", int(dead.sum()))
yrs={}
for y in [2022,2023,2024,2025,2026]:
    idx=[i for i in range(len(E)) if time.gmtime(int(E[i])).tm_year==y]
    if not idx: continue
    d=[]
    for i in idx[::20]:
        m=np.asarray(mem[i]); d.append(dead[m].mean())
    yrs[str(y)]=round(float(np.mean(d)),4)
print("fraction of each anchor's member set that eventually disappears, by year:", json.dumps(yrs))
lastdate={int(k):time.strftime("%F",time.gmtime(int(E[v]))) for k,v in zip(np.where(dead)[0][:10],last[dead][:10])}
print("sample of dropped names' last anchor dates:", list(lastdate.values()))
