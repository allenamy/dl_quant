"""r5nd/refresh_cost.py -- what a monthly membership refresh costs in TURNOVER.
(a) month-over-month churn of the U-PIT top-449 selection (names in / names out);
(b) the gross actually carried by the names that would LEAVE, taken from the A0 arm's own weight
    matrix W at the last anchor of each month -> the forced-exit turnover a refresh event would cause;
(c) the same for the LIVE frozen list: what fraction of today's 450 would leave on a first refresh."""
import numpy as np, json, time
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
UM=np.load(R+"/masks/umask_R5_MONTHLY449.npz",allow_pickle=True)
PTS=UM["ts"].astype(np.int64); SYM=[str(s) for s in UM["symbols"]]; M=np.asarray(UM["mask"])
mkey=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in PTS])
umk=sorted(set(mkey.tolist()))
first={k:int(np.where(mkey==k)[0][0]) for k in umk}
last={k:int(np.where(mkey==k)[0][-1]) for k in umk}
Z=np.load(R+"/arms/R5U_A0M_fix_s42.npz",allow_pickle=True)
Rr=np.asarray(Z["rec"],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
ats=Rr[:,ix["ts"]].astype(np.int64); W=np.asarray(Z["W"],float)
arow={int(t):i for i,t in enumerate(ats)}
rows=[]
for a,b in zip(umk[:-1],umk[1:]):
    ma=M[first[a]]; mb=M[first[b]]
    out=ma&~mb; inn=mb&~ma
    t_last=int(PTS[last[a]]); i=arow.get(t_last)
    lv=np.nan
    if i is not None and i>=900:
        w=np.abs(W[i]); g=w.sum()
        if g>1e-9: lv=float(w[out].sum()/g)
    rows.append({"from":a,"to":b,"n_out":int(out.sum()),"n_in":int(inn.sum()),
                 "leaving_gross_share":None if not np.isfinite(lv) else round(lv,5)})
ok=[r for r in rows if r["leaving_gross_share"] is not None]
yr=lambda r: r["to"]//100
summ={"n_months":len(rows),
      "churn_names_per_month_mean":round(float(np.mean([r["n_out"] for r in rows])),2),
      "churn_names_per_month_median":float(np.median([r["n_out"] for r in rows])),
      "leaving_gross_share_mean":round(float(np.mean([r["leaving_gross_share"] for r in ok])),5),
      "leaving_gross_share_max":round(float(np.max([r["leaving_gross_share"] for r in ok])),5),
      "by_year":{}}
for y in sorted(set(yr(r) for r in ok)):
    s=[r for r in ok if yr(r)==y]
    summ["by_year"][str(y)]={"months":len(s),
        "churn_names_mean":round(float(np.mean([r["n_out"] for r in s])),2),
        "leaving_gross_share_mean":round(float(np.mean([r["leaving_gross_share"] for r in s])),5)}
# (c) live frozen list vs the U-PIT selection of the most recent panel month
live=set(l.strip() for l in open(HC+"/syms450.txt") if l.strip())
lastk=umk[-1]; sel=set(np.array(SYM)[M[first[lastk]]].tolist())
summ["live_450_vs_last_panel_month_selection"]={"panel_month":lastk,"n_selection":len(sel),
    "live_not_in_selection":len(live-sel),"selection_not_in_live":len(sel-live),
    "overlap":len(live&sel),
    "examples_live_would_drop":sorted(live-sel)[:20],
    "examples_would_add":sorted(sel-live)[:20]}
json.dump({"summary":summ,"months":rows},open(R+"/refresh_cost.json","w"),indent=1)
print(json.dumps(summ,indent=1))
