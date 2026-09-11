# VERIFY the sign convention of funding.jsonl funding_paid against the venue's own income accounting
# (daily_nav.jsonl realised_by_type.FUNDING_FEE, which is /fapi/v1/income since 00:00Z).
import json,os,collections,datetime
base='/Users/haosiyu/dl_quant_live/state/live/pilot_log'
days=sorted(d for d in os.listdir(base) if d.isdigit())
print("day   sum(funding_paid)  nav.FUNDING_FEE(last row)   ratio")
rows=[]
for d in days:
    p=f'{base}/{d}/funding.jsonl'
    if not os.path.exists(p): continue
    seen=set(); s=0.0; n=0
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        k=(r['symbol'],r['settlement_ts'])
        if k in seen: continue
        seen.add(k)
        s+=float(r.get('funding_paid') or 0); n+=1
    ff=None
    q=f'{base}/{d}/daily_nav.jsonl'
    if os.path.exists(q):
        for ln in open(q):
            ln=ln.strip()
            if not ln: continue
            try: r=json.loads(ln)
            except: continue
            v=(r.get('realised_by_type') or {}).get('FUNDING_FEE')
            if v is not None: ff=float(v)
    if ff is None: continue
    rows.append((d,s,ff,n))
    print(f"{d}  {s:12.3f}  {ff:12.3f}   {(s/ff if abs(ff)>1e-9 else float('nan')):7.3f}  (n_settle={n})")
import statistics
tot_s=sum(r[1] for r in rows); tot_f=sum(r[2] for r in rows)
print(f"\nTOTAL sum(funding_paid) {tot_s:.3f}   TOTAL nav FUNDING_FEE {tot_f:.3f}   ratio {tot_s/tot_f:.4f}")
print("days compared:",len(rows))
