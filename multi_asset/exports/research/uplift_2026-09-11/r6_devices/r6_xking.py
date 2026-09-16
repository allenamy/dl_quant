"""X-KING localisation: are the 2000 differing re-score cells exactly the 5 whitelisted anchors?"""
import numpy as np, json, time, calendar
import lightgbm as lgb
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
WL = set(calendar.timegm((2026,8,31,h,0,0)) for h in (4,8,12,16,20))
OUT="/workspace/uplift_2026-09-11/r6/out"
MT=np.load(f"{OUT}/wide_fea_v4_meta_x0910.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]
names=[str(n) for n in MT["names"]]
PINS=json.load(open("/workspace/live_pins.json"))
keep=[k for k,nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
FEA=np.load(f"{OUT}/wide_fea_v4_x0910.npy",mmap_mode="r")
P0=np.load("/workspace/shadow_bundle_v4/slow_pred_pinned.npy")
bst=lgb.Booster(model_file="/workspace/shadow_bundle_v4/slow2026.txt")
n0=P0.shape[0]
yrs=np.array([time.gmtime(int(t)).tm_year for t in E])
old26=[i for i in range(n0) if yrs[i]==2026]
chk=old26[-200:]
in_wl={"anchors":0,"cells":0,"bitwise_equal":0,"maxabs":0.0}
out_wl={"anchors":0,"cells":0,"bitwise_equal":0,"maxabs":0.0}
for i in chk:
    m=mem[i]; ok=np.isfinite(y4[i,m])
    if ok.sum()<50: continue
    X=np.asarray(FEA[i,m[ok]][:,keep],dtype=np.float32)
    p=bst.predict(X).astype(np.float32); q=P0[i,m[ok]]
    fin=np.isfinite(q)
    d = in_wl if int(E[i]) in WL else out_wl
    d["anchors"]+=1; d["cells"]+=int(len(p))
    d["bitwise_equal"]+=int((p[fin].view(np.uint32)==q[fin].view(np.uint32)).sum())
    if fin.any(): d["maxabs"]=max(d["maxabs"],float(np.abs(p[fin]-q[fin]).max()))
for k,d in (("WHITELIST anchors",in_wl),("ALL OTHER anchors",out_wl)):
    r=d["bitwise_equal"]/max(d["cells"],1)
    print(f"{k}: anchors {d['anchors']} cells {d['cells']} bitwise_equal {d['bitwise_equal']} rate {r:.8f} maxabs {d['maxabs']:.6g}")
json.dump({"whitelist":in_wl,"other":out_wl,"checked_anchors":len(chk)},
          open("/workspace/uplift_2026-09-11/r6/RECEIPT_XKING_localised.json","w"),indent=1)
