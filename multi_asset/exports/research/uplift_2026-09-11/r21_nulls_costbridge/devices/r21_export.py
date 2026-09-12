"""r21_export.py -- pod2 export for Part B (PREREG_r21 SS B1/B2): the PINNED pod 5m cache's `ret5` channel (BY NAME) for rows
2026-08-22 20:00Z .. 2026-09-11 00:00Z, and the replay's own tier input `qvk` (meta_newprod_v4_x0910, = realpath of the r12
dev-tree meta) for anchors 2026-08-23 00Z .. 2026-09-10 20Z. Symbol axes asserted equal across cache / panel / dlw_targets.
Full-file sha256 of both inputs recorded. ENV whitelist = EMPTY SET (asserted). Read-only on every input."""
import os, json, time, hashlib, calendar
assert not any(k in os.environ for k in ("CAL","PHI","CEM_Q","LEGS","FTRIM","R12_NULL","R21_DOSE","FSEED","FPRED","PANEL_IN")), "env not empty"
import numpy as np
U="/workspace/uplift_2026-09-11"; R21=f"{U}/r21_nulls_costbridge"; os.makedirs(f"{R21}/out",exist_ok=True)
PREREG_SHA="c4de6df3a37483462d4e10373c30ea4137c02c78f9a23e06148007c5ce246232"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<26),b""): h.update(c)
    return h.hexdigest()
assert sha(f"{R21}/PREREG_r21_2026-09-12.md")==PREREG_SHA
CACHE="/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
META="/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"
PANEL="/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
DLW="/workspace/uplift_2026-09-11/r6/out/dlw_v4raw_x0910/data/dlw_targets.npz"
DEVMETA="/workspace/uplift_2026-09-11/r12_intervene/dev_ext/pod_backup_2026-08-21/wide_fea_hist_meta.npz"
assert os.path.realpath(DEVMETA)==META, os.path.realpath(DEVMETA)
t0=time.time(); sc=sha(CACHE); sm=sha(META); print("sha done",round(time.time()-t0,1),"s",flush=True)
C=np.load(CACHE,allow_pickle=True); ch=[str(x) for x in C["ch"]]; assert "ret5" in ch, ch
ci=ch.index("ret5")                                   # BY NAME (E-0825-H)
ts=C["ts"].astype(np.int64); sym=np.array([str(s) for s in C["symbols"]])
P=np.load(PANEL,allow_pickle=True); T=np.load(DLW,allow_pickle=True)
assert np.array_equal(sym,np.array([str(s) for s in P["symbols"]])) and np.array_equal(sym,np.array([str(s) for s in T["symbols"]])), "symbol axes differ"
lo=calendar.timegm((2026,8,22,20,0,0)); hi=calendar.timegm((2026,9,11,0,0,0))
r0=int(np.searchsorted(ts,lo)); r1=int(np.searchsorted(ts,hi,side="right"))
assert ts[r0]==lo and ts[r1-1]==hi and np.all(np.diff(ts[r0:r1])==300), "cache row grid"
RET=np.asarray(C["data"][r0:r1,:,ci],np.float32)
M=np.load(META,allow_pickle=True); E=M["E_ts"].astype(np.int64)
e0=calendar.timegm((2026,8,23,0,0,0)); e1=calendar.timegm((2026,9,10,20,0,0))
es=(E>=e0)&(E<=e1); assert es.sum()==114, es.sum()
QVK=np.asarray(M["qvk"][es],np.float32); EW=E[es]
out=f"{R21}/out/r21_slice.npz"
np.savez_compressed(out,ts=ts[r0:r1],symbols=sym,ret5=RET,ret5_channel_index=np.int64(ci),channels=np.array(ch),E_ts=EW,qvk=QVK,
    cache_path=CACHE,cache_sha256=sc,meta_path=META,meta_sha256=sm,prereg_sha256=PREREG_SHA,
    note="ret5 = close-to-close SIMPLE 5m return, row ts = bar CLOSE time (pod_panel_ext.py lineage; NO expm1). qvk -> qv4h = expm1(clip(qvk,0,30))*48 (w10 device L251).")
rc={"prereg_sha256":PREREG_SHA,"env_whitelist":[],"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"cache":{"path":CACHE,"sha256":sc,"channels":ch,"ret5_index":ci,
    "rows_exported":[r0,r1,r1-r0],"ts_first":time.strftime("%FT%TZ",time.gmtime(int(ts[r0]))),"ts_last":time.strftime("%FT%TZ",time.gmtime(int(ts[r1-1])))},
    "meta":{"path":META,"sha256":sm,"dev_tree_meta_realpath":os.path.realpath(DEVMETA),"anchors_exported":int(es.sum()),"E_first":time.strftime("%FT%TZ",time.gmtime(int(EW[0]))),
    "E_last":time.strftime("%FT%TZ",time.gmtime(int(EW[-1]))),"qvk_finite_frac":float(np.isfinite(QVK).mean())},
    "symbol_axes_equal_cache_panel_dlw":True,"slice_path":out,"slice_sha256":sha(out)}
json.dump(rc,open(f"{R21}/out/EXPORT_r21.json","w"),indent=1); print(json.dumps(rc,indent=1)); print("EXPORT_DONE")
