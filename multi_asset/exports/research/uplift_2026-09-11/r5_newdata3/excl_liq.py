"""r5nd/excl_liq.py -- would the 80 venue-listed names the book cannot trade even pass the live
liquidity gate?  qv4h = expm1(clip(qvk,0,30))*48 exactly as the device computes it, on the v4 meta grid."""
import numpy as np, json, time
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); qvk=np.asarray(MT["qvk"],float); members=MT["members"]
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
WSYM=[str(s) for s in PW["symbols"]]; col={s:j for j,s in enumerate(WSYM)}
VC=json.load(open(R+"/venue_class_2026-09-11.json"))
live=set(l.strip() for l in open(HC+"/syms450.txt") if l.strip())
venue=set(s for s,v in VC.items() if v["contractType"]=="PERPETUAL" and v["quoteAsset"]=="USDT" and v["status"]=="TRADING")
vo=sorted(venue-live)
qv4h=np.expm1(np.clip(np.nan_to_num(qvk,nan=0.0),0,30))*48
yrs=np.array([time.gmtime(int(t)).tm_year for t in E_ts])
m26=yrs==2026
MEM=np.zeros((len(E_ts),len(WSYM)),bool)
for i in range(len(E_ts)): MEM[i,members[i]]=True
out={"n_venue_only":len(vo),"in_panel":0,"rows":[]}
pass_n=0; tot=0
for s in vo:
    j=col.get(s)
    if j is None: continue
    out["in_panel"]+=1
    v=qv4h[m26,j]; fin=np.isfinite(qvk[m26,j])
    if fin.sum()<10: continue
    tot+=1
    med=float(np.median(v[fin])); sh=float((v[fin]>=2.5e5).mean())
    if sh>=0.5: pass_n+=1
    out["rows"].append({"sym":s,"anchors_2026":int(fin.sum()),"qv4h_median_usd":round(med,0),
                        "share_anchors_above_250k":round(sh,3)})
out["n_with_2026_data"]=tot; out["n_passing_liq_gate_majority"]=pass_n
out["rows"].sort(key=lambda r:-r["qv4h_median_usd"])
# the book's own 450: how many are now marginal on the same ruler?
lv=[]
for s in sorted(live):
    j=col.get(s)
    if j is None: continue
    v=qv4h[m26,j]; fin=np.isfinite(qvk[m26,j])
    if fin.sum()<10: continue
    lv.append((s,float(np.median(v[fin])),float((v[fin]>=2.5e5).mean())))
lv.sort(key=lambda x:x[1])
out["book_450_marginal"]={"n_with_2026_data":len(lv),
    "n_median_below_250k":int(sum(1 for x in lv if x[1]<2.5e5)),
    "n_below_250k_at_majority_of_anchors":int(sum(1 for x in lv if x[2]<0.5)),
    "worst_25":[{"sym":s,"qv4h_median_usd":round(m,0),"share_above_250k":round(p,3)} for s,m,p in lv[:25]]}
json.dump(out,open(R+"/excl_liq.json","w"),indent=1)
print("venue-only names:",out["n_venue_only"],"in panel:",out["in_panel"],"with 2026 data:",tot,
      "| passing the 250k gate at a majority of 2026 anchors:",pass_n)
print("top 15 venue-only by 2026 median qv4h:")
for r in out["rows"][:15]: print("   %-16s med qv4h $%12.0f  share>=250k %.3f"%(r["sym"],r["qv4h_median_usd"],r["share_anchors_above_250k"]))
print("bottom 8:")
for r in out["rows"][-8:]: print("   %-16s med qv4h $%12.0f  share>=250k %.3f"%(r["sym"],r["qv4h_median_usd"],r["share_anchors_above_250k"]))
print("book 450:",json.dumps({k:v for k,v in out["book_450_marginal"].items() if k!="worst_25"}))
for r in out["book_450_marginal"]["worst_25"][:12]: print("   worst %-16s med $%10.0f share %.3f"%(r["sym"],r["qv4h_median_usd"],r["share_above_250k"]))
