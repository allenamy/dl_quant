import numpy as np, datetime as dt
m=np.load("/workspace/data/wide_fea_v1_meta.npz",allow_pickle=True)
E=m["E_ts"]; mem=m["members"]; y4=m["y4"]; qvk=m["qvk"]
p=np.load("/workspace/data/wide_panel_4h_v1.npz",allow_pickle=True)
ts=p["ts"]
d=np.load("/workspace/data/dlnative_5m_wide829_f16.npz",allow_pickle=True,mmap_mode='r')
dts=d["ts"]
def f(x): return dt.datetime.utcfromtimestamp(int(x)).isoformat()
print("E_ts",E[:3],E[-3:], f(E[0]),f(E[-1]), "sorted",bool(np.all(np.diff(E)>0)))
print("E diffs uniq",np.unique(np.diff(E))[:5],np.unique(np.diff(E))[-5:])
print("panel ts",ts[:3],ts[-3:], f(ts[0]),f(ts[-1]),"sorted",bool(np.all(np.diff(ts)>0)))
print("panel diffs uniq",np.unique(np.diff(ts))[:5],np.unique(np.diff(ts))[-5:])
print("5m ts",dts[:3],dts[-3:],f(dts[0]),f(dts[-1]),"sorted",bool(np.all(np.diff(dts)>0)))
print("5m diffs uniq",np.unique(np.diff(dts))[:6])
# coverage
setp=set(ts.tolist()); setE=set(E.tolist()); setd=set(dts.tolist())
print("E in panel:",sum(1 for x in E if x in setp),"of",len(E))
print("panel in E:",sum(1 for x in ts if x in setE),"of",len(ts))
print("E in 5m:",sum(1 for x in E if x in setd),"of",len(E))
# 2024+ subset
yrs=np.array([dt.datetime.utcfromtimestamp(int(x)).year for x in E])
print("year counts",{int(u):int(c) for u,c in zip(*np.unique(yrs,return_counts=True))})
E24=E[yrs>=2024]
print("E>=2024 in panel:",sum(1 for x in E24 if x in setp),"of",len(E24))
print("E>=2024 in 5m:",sum(1 for x in E24 if x in setd),"of",len(E24))
print("members type",type(mem[0]),np.asarray(mem[0]).dtype,np.asarray(mem[0])[:10],"len",len(np.asarray(mem[0])))
ln=np.array([len(np.asarray(x)) for x in mem]); print("member counts min/med/max",ln.min(),np.median(ln),ln.max())
print("y4 finite frac",np.isfinite(y4).mean(),"qvk finite",np.isfinite(qvk).mean())
print("qvk sample",qvk[5000,:5],"expm1*48",np.expm1(qvk[5000,:5])*48)
