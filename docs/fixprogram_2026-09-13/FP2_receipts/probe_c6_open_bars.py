# FP2-7 probe (read-only): at each of the 13 lifecycle OPEN transitions, what does OUR holefix2 cache hold
# around the first new-generation bar? (fake cross-generation return = frozen-close rows then a jump)
import numpy as np, zipfile, json, time
Z="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"; z=zipfile.ZipFile(Z)
ts=np.load(z.open("ts.npy")); sy=[str(s) for s in np.load(z.open("symbols.npy"),allow_pickle=True)]
data=np.load(z.open("data.npy"))
cal=json.load(open("/workspace/codex_research/QNT-2026-0907/causal_fullchain_20260914/book/full_axis_calendar_review_20260914/evidence1/calendar_candidate2/CONTRACT_LIFECYCLE.json"))
opens=[(t["effective_ms"]//1000,s) for s,v in cal["symbols"].items() for t in v.get("transitions",[]) if t["kind"]=="OPEN"]
fmt=lambda x: time.strftime("%F %H:%M",time.gmtime(int(x)))
print("row  symbol        OPEN(cal)         cache: frozen(ret5==0&cnt==0) rows in prior 30d | first bar with cnt>0 at/after OPEN | its ret5 | prev-bar ret5 | NaN rows in prior 30d")
for o,s in sorted(opens):
    if s not in sy: print(f"  {s}: NOT IN CACHE"); continue
    j=sy.index(s); r=data[:,j,0].astype(np.float64); c=data[:,j,4].astype(np.float64)
    i0=int(np.searchsorted(ts,o)); lo=int(np.searchsorted(ts,o-30*86400))
    frozen=int(((r[lo:i0]==0)&(c[lo:i0]==0)).sum()); nan=int(np.isnan(r[lo:i0]).sum())
    k=i0+int(np.argmax(c[i0:i0+2000]>0)) if (c[i0:i0+2000]>0).any() else None
    if k is None: print(f"  {s:12s} {fmt(o)}  frozen30d={frozen:5d} NaN30d={nan:5d}  no traded bar within 7d after OPEN"); continue
    print(f"  {s:12s} {fmt(o)}  frozen30d={frozen:5d} NaN30d={nan:5d}  first traded {fmt(ts[k])}  ret5={r[k]:+.4f}  prev={r[k-1]:+.4f}  prev cnt={c[k-1]:.2f}")
