import os
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"
V2="%s/data/npz_v2arch"%MA
days_full=sorted(f[:-4] for f in os.listdir(V2) if f.endswith(".npz") and f[0].isdigit())
print("v2arch: n=%d span %s .. %s"%(len(days_full),days_full[0],days_full[-1]))
# gap check
import datetime as dt
def dset(a,b): return [(dt.date.fromisoformat(a)+dt.timedelta(days=i)).isoformat() for i in range((dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days+1)]
cal=dset(days_full[0],days_full[-1])
missing=sorted(set(cal)-set(days_full))
print("calendar span=%d present=%d missing=%d"%(len(cal),len(days_full),len(missing)))
print("missing days:",missing)

TRAIN,VAL,TEST,EMB=450,45,28,1
def build_fold(days, ts):
    ti=days.index(ts)
    test=days[ti:ti+TEST]
    val_end=ti-EMB; val_start=val_end-VAL; val=days[val_start:val_end]
    tr_end=val_start-EMB; tr_start_req=tr_end-TRAIN; tr_start=max(0,tr_start_req)
    train=days[tr_start:tr_end]
    return train,val,test,(tr_start_req<0)

def summarize(days,ts,label):
    if ts not in days: print("  %-22s test_start NOT in list"%label); return None
    tr,va,te,trunc=build_fold(days,ts)
    print("  %-22s train[%d]=%s..%s val[%d]=%s..%s test[%d]=%s..%s trunc=%s"%(
        label,len(tr),tr[0],tr[-1],len(va),va[0],va[-1],len(te),te[0],te[-1],trunc))
    return (tr,va,te)

for ts in ["2025-10-10","2026-01-10"]:
    print("=== test_start %s ==="%ts)
    ref=summarize(days_full,ts,"FULL v2arch")
    for start in ["2024-04-01","2024-05-01","2024-06-01"]:
        cand=[d for d in days_full if d>=start and d<="2026-02-15"]
        got=summarize(cand,ts,"augms>=%s"%start)
        if ref and got:
            same=(ref==got)
            print("       -> identical to FULL: %s"%same)
