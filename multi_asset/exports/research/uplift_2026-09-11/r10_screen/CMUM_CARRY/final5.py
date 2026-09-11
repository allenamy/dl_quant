import os,json,datetime as dt,numpy as np
W=os.path.dirname(os.path.abspath(__file__))
B=np.load(W+"/best_series.npz",allow_pickle=True)
TS=B["TS"];G=B["net"];A0g=B["A0g"]
day=(TS//86400).astype(np.int64);ud=np.unique(day)
gd=np.array([G[day==d].sum() for d in ud]);ad=np.array([A0g[day==d].sum() for d in ud])
o=np.argsort(gd)[:6]
print("candidate 6 worst UTC days, with what A0 did the same day:")
for i in o:
    print("  %s  cand %+8.3f   A0 %+9.3f   A0 pctile %.3f"%(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date(),gd[i],ad[i],(ad<ad[i]).mean()))
o2=np.argsort(ad)[:6]
print("\nA0 6 worst UTC days, with what the candidate did:")
for i in o2:
    print("  %s  A0 %+9.3f   cand %+8.3f"%(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date(),ad[i],gd[i]))
print("\ncorr of DAILY sums: %.4f"%np.corrcoef(gd,ad)[0,1])
res={}
for x in (1,2,4):
    c=ad+x*gd; res["x%d"%x]=dict(worst_day=round(float(c.min()),3),worst_date=str(dt.datetime.utcfromtimestamp(int(ud[int(c.argmin())])*86400).date()))
    print("combo x%d worst UTC day %+.3f on %s   (A0 alone %+.3f)"%(x,c.min(),dt.datetime.utcfromtimestamp(int(ud[int(c.argmin())])*86400).date(),ad.min()))
json.dump(dict(daily_corr=round(float(np.corrcoef(gd,ad)[0,1]),4),combo=res,
  cand_worst=[[str(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date()),round(float(gd[i]),3),round(float(ad[i]),3)] for i in o],
  a0_worst=[[str(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date()),round(float(ad[i]),3),round(float(gd[i]),3)] for i in o2]),
  open(W+"/STEP4_tail_overlap.json","w"),indent=1)
