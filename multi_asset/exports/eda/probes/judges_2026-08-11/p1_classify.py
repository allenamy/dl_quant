"""For every residual name at every trip anchor: is it 'went flat with no logged flatten'
(our own record gap) or something ELSE (a real drift candidate)?"""
import sys, json, time
from collections import defaultdict
sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
import pilot_log as PL
root = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
days = PL.available_days(root)
mids={}; rb=defaultdict(dict); rbq=defaultdict(dict); rbt={}; orders=[]
for d in days:
    one = PL.read_day(root, d)
    for a in one["anchors"]:
        v=a.get("mid_at_anchor_vector")
        if isinstance(v,str): v=json.loads(v)
        mids[a["anchor_ts"]]=v or {}
    for r in one["position_readback"]:
        rb[r["anchor_ts"]][r["symbol"]]=float(r["venue_position_notional"])
        rbq[r["anchor_ts"]][r["symbol"]]=r.get("venue_position_qty")
        rbt[r["anchor_ts"]]=float(r.get("read_ts") or r["anchor_ts"])
    orders+=one["orders"]
def mid_for(ats,sym):
    if ats in mids and sym in mids[ats]: return mids[ats][sym]
    best,bd=None,None
    for t,v in mids.items():
        if sym in v and (bd is None or abs(t-ats)<bd): best,bd=v[sym],abs(t-ats)
    return best
def dq_of(o):
    fn=o.get("filled_notional")
    if fn is None:
        return (0.0,"structural_zero") if o.get("submit_ts") is None else (None,"unquantifiable")
    fn=float(fn)
    if fn==0.0: return 0.0,"known"
    px=o.get("avg_fill_px")
    return (fn/float(px),"known") if px else (None,"unquantifiable")
ex=[]
for o in orders:
    dq,kind=dq_of(o)
    if kind!="unquantifiable" and dq==0.0: continue
    t=o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
    if t is None: continue
    ex.append((float(t),o["symbol"],dq,o))
ex.sort(key=lambda e:e[0])
ancs=sorted(rb); prev=None
TRIP_ANCH = {"2026-07-26T00:01:03Z","2026-07-26T04:00:41Z","2026-07-26T12:00:48Z",
             "2026-07-26T16:01:39Z","2026-07-27T00:01:07Z","2026-07-27T04:00:47Z",
             "2026-07-27T16:01:10Z","2026-07-28T08:01:24Z"}
summary={}
for ats in ancs:
    if prev is None: prev=ats; continue
    lbl=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(ats))
    if lbl not in TRIP_ANCH: prev=ats; continue
    t_lo,t_hi=rbt[prev],rbt[ats]
    agg=defaultdict(float); unk=set()
    for t,sym,dq,o in ex:
        if t_lo<t<=t_hi:
            if dq is None: unk.add(sym)
            else: agg[sym]+=dq
    cls=defaultdict(list)
    for sym,n2 in rb[ats].items():
        if sym in unk: cls["unknown_size_leg"].append((sym,None)); continue
        m2=mid_for(ats,sym); m1=mid_for(prev,sym)
        if not m2 or not m1: continue
        q2=float(rbq[ats][sym]) if rbq[ats].get(sym) is not None else n2/m2
        n1=rb[prev].get(sym,0.0)
        q1=float(rbq[prev][sym]) if rbq[prev].get(sym) is not None else n1/m1
        res_q=q2-(q1+agg.get(sym,0.0)); res_u=abs(res_q)*m2
        if res_u<=5.0: continue
        # classify
        went_flat = abs(q2*m2) < 5.0
        toward_zero = abs(q2) < abs(q1) - 1e-12
        opposite_sign = (q1!=0 and q2!=0 and (q1>0)!=(q2>0))
        grew = abs(q2*m2) > abs(q1*m1) + 5.0
        if went_flat and abs(agg.get(sym,0.0))*m2 < 5.0:
            cls["A_went_flat_no_logged_flatten"].append((sym,round(res_u,2)))
        elif went_flat:
            cls["B_went_flat_partially_logged"].append((sym,round(res_u,2)))
        elif opposite_sign:
            cls["D_SIGN_FLIP"].append((sym,round(res_u,2),round(q1*m1,2),round(q2*m2,2)))
        elif grew:
            cls["E_POSITION_GREW"].append((sym,round(res_u,2),round(q1*m1,2),round(q2*m2,2)))
        elif toward_zero:
            cls["C_partial_reduction_not_flat"].append((sym,round(res_u,2),round(q1*m1,2),round(q2*m2,2)))
        else:
            cls["F_OTHER"].append((sym,round(res_u,2),round(q1*m1,2),round(q2*m2,2)))
    print("==",lbl)
    for k in sorted(cls):
        print(f"   {k:34s} n={len(cls[k]):4d}  e.g. {cls[k][:3]}")
    summary[lbl]={k:len(v) for k,v in cls.items()}
    summary[lbl+"_examples"]={k:v[:5] for k,v in cls.items() if k[0] in "CDEF"}
    prev=ats
json.dump(summary,open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/0C_p1_residual_classification.json","w"),indent=1)
