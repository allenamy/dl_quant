"""Instrument check: venue /fapi/v1/fundingRate (pulled now) vs producer ledger_tail (aux.json) on shared settlements; then recompute dev/settle carry with venue rates."""
import json, numpy as np, time
G="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/gap_1"
SP="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
WS="/Users/haosiyu/wide_shadow"
V=json.load(open(f"{G}/venue_funding_rates.json")); VR=V["rates"]; FI={x["symbol"]:x["fundingIntervalHours"] for x in V["fundingInfo"]} if isinstance(V["fundingInfo"],list) else {}
LT=json.load(open(f"{WS}/state/aux.json"))["ledger_tail"]
# bitwise compare on shared (symbol, fundingTime)
n=0; neq=0; maxd=0.0; miss_in_ledger=0; ms_off=[]
for s,lst in VR.items():
    if not isinstance(lst,list): continue
    led={ft:(r,iv) for ft,r,iv in LT.get(s,[])}
    for row in lst:
        ft=int(row["fundingTime"])//1000; ms_off.append(int(row["fundingTime"])%1000); r=float(row["fundingRate"])
        if ft< 1787702400-14400: continue
        if ft not in led: miss_in_ledger+=1; continue
        n+=1; d=abs(led[ft][0]-r); maxd=max(maxd,d); neq+= (led[ft][0]!=r)
print(f"shared settlements >= 08-25 20Z: n={n} unequal={neq} max|diff|={maxd:.2e} venue-rows-missing-in-ledger={miss_in_ledger}; fundingTime ms offsets: {np.percentile(ms_off,[0,50,100])}")
# interval check: ledger iv (from diffs) vs fundingInfo (default 8 when absent)
iv_mis=0; iv_n=0
for s in VR:
    led=LT.get(s)
    if not led: continue
    iv_led=led[-1][2]; iv_fi=float(FI.get(s,8))
    iv_n+=1; iv_mis+=(iv_led!=iv_fi)
    if iv_led!=iv_fi and iv_mis<=5: print("  iv mismatch", s, "ledger", iv_led, "fundingInfo", iv_fi)
print(f"interval: {iv_n} symbols, ledger-vs-fundingInfo mismatches {iv_mis}")
# recompute with venue rates
rows=json.load(open(f"{SP}/gt/live_reconcile_report.json"))["rows"]
def r_last(s,N):
    lst=VR.get(s); 
    if not isinstance(lst,list): return None
    best=None
    for row in lst:
        ft=int(row["fundingTime"])//1000
        if ft<=N: best=(ft,float(row["fundingRate"]))
        else: break
    if best is None or N-best[0]>12*3600: return None
    return best
def settles(s,N):
    lst=VR.get(s) or []
    return [float(row["fundingRate"]) for row in lst if isinstance(lst,list) and N<int(row["fundingTime"])//1000<=N+14400]
def iv_of(s,N):
    lst=VR.get(s) or []; ts=[int(r["fundingTime"])//1000 for r in lst if int(r["fundingTime"])//1000<=N]
    if len(ts)>=2:
        d=round((ts[-1]-ts[-2])/3600); return float(min([1,2,4,6,8],key=lambda a:abs(a-d)))
    return float(FI.get(s,8))
dev=[];setl=[];live=[]
for x in rows:
    N=int(x["N"]); w=json.load(open(f"{WS}/state/target_live/{N}.json"))["weights"]; g=sum(abs(v) for v in w.values())
    d=0;st=0
    for s,v in w.items():
        rl=r_last(s,N)
        if rl is None: continue
        d+=v*rl[1]*(4.0/iv_of(s,N)); st+=v*sum(settles(s,N))
    dev.append(d/g*1e4); setl.append(st/g*1e4); live.append(-x["funding_usd"]/x["realized_gross"]*1e4)
dev=np.array(dev);setl=np.array(setl);live=np.array(live)
def S(a): return f"mean {a.mean():+.3f} sd {a.std(ddof=1):.3f} se {a.std(ddof=1)/np.sqrt(len(a)):.3f}"
print("VENUE-rate instrument, 52 windows, target weights, per target gross, +=book pays")
print("dev_target   ", S(dev)); print("settle_target", S(setl)); print("live_pays    ", S(live)); print("gap live-dev ", S(live-dev)); print("gap live-settle", S(live-setl))
led_rows=json.load(open(f"{G}/carry_reconcile_rows.json"))
ld=np.array([o["dev_target"] for o in led_rows]); ls_=np.array([o["settle_target"] for o in led_rows])
print("venue vs ledger instrument: dev_target max|diff|", np.abs(ld-dev).max(), "settle_target max|diff|", np.abs(ls_-setl).max())
