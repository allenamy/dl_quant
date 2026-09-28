"""Bind new archived funding to the fixed NC history before extending any model input.

Read-only evidence: events absent from either source are not zero, and the
current archive is not independent proof of complete venue history.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import sys,json,hashlib,math,time
import numpy as np

NEW_SHA='927cac43f071049aa0f68276b0337acf4cbad382383f07ee893264340f4fd8e3'

def no_duplicates(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate serialized event key')
        d[k]=v
    return d

def event_map(d):
    if not isinstance(d,dict) or not d:raise ValueError('empty funding population')
    out={}
    for k,v in d.items():
        if not isinstance(k,str) or k.count('|')!=1 or not isinstance(v,list) or len(v)!=3:raise ValueError('event schema')
        s,t=k.split('|')
        if not s or not t.isdigit() or type(v[0])!=int or v[0]!=int(t):raise ValueError('event timestamp identity')
        if type(v[1]) not in (int,float) or not math.isfinite(v[1]):raise ValueError('unknown rate')
        if v[2] is not None and (type(v[2]) not in (int,float) or not math.isfinite(v[2]) or v[2]<=0):raise ValueError('interval schema')
        out[(s,int(t))]=float(v[1])
    return out

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main(root):
    root=Path(root);start=time.monotonic();newp=root/'funding_ledger_2026-09.json'
    if sha(newp)!=NEW_SHA:raise ValueError('new archive identity')
    new=event_map(json.loads(newp.read_text(),object_pairs_hook=no_duplicates))
    oldroot=Path('/dev/shm/nc_2026-09-23');axp=oldroot/'work/axes.npz';oldp=oldroot/'work/fund_state.npz';rp=oldroot/'receipts/NC_PREP.json'
    r=json.loads(rp.read_text());pins={str(newp):NEW_SHA,str(rp):sha(rp),str(axp):sha(axp),str(oldp):sha(oldp)}
    for p in (axp,oldp):
        if pins[str(p)]!=r['outputs'][p.name]:raise ValueError('old preparation receipt mismatch')
    ax=np.load(axp);f=np.load(oldp);sy=ax['symbols'];cols=ax['crypto_cols'];off=f['ev_off'];ft=f['ft'];rate=f['rate'];end=int(ax['anchors'][-1]);begin=1788220800
    if not np.array_equal(cols,f['cols']) or not np.array_equal(ax['anchors'],f['anchors']) or len(off)!=len(cols)+1 or off[0]!=0 or off[-1]!=len(ft) or len(ft)!=len(rate):raise ValueError('old population shape')
    old={}
    for i,j in enumerate(cols):
        ts=ft[off[i]:off[i+1]];rs=rate[off[i]:off[i+1]]
        if ts.dtype.kind not in 'iu' or np.any(np.diff(ts)<=0) or not np.isfinite(rs).all():raise ValueError('old event schema')
        for t,v in zip(ts,rs):
            if begin<=t<=end:old[(str(sy[j]),int(t))]=float(v)
    both=set(old)&set(new);different=[{'symbol':s,'ts':t,'old':old[(s,t)],'archive':new[(s,t)]} for s,t in sorted(both) if old[(s,t)]!=new[(s,t)]]
    old_only=sorted(set(old)-set(new));crypto={str(sy[j]) for j in cols};new_oldwindow={(s,t) for s,t in new if s in crypto and begin<=t<=end};new_only=sorted(new_oldwindow-set(old));extension=[(s,t) for s,t in new if s in crypto and t>end]
    def counts(keys):
        out={}
        for s,t in keys:out[s]=out.get(s,0)+1
        return out
    record={'status':'FUNDING_OVERLAP_MEASURED_NOT_COMPLETE_HISTORY','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'inputs':pins,'begin':begin,'old_last_anchor':end,
        'old_events':len(old),'shared_events':len(both),'rate_differences':different,'old_only_count':len(old_only),'new_only_oldwindow_count':len(new_only),
        'old_only_by_symbol':counts(old_only),'new_only_oldwindow_by_symbol':counts(new_only),'old_only':old_only,'new_only_oldwindow':new_only,
        'extension_events_in_old_crypto_axis':len(extension),'extension_symbols':len(counts(extension)),'extension_first':min(t for s,t in extension) if extension else None,'extension_last':max(t for s,t in extension) if extension else None,
        'new_archive_outside_old_crypto_axis':counts([(s,t) for s,t in new if s not in crypto]),'seconds':time.monotonic()-start,
        'limits':['Old identity bound to its original NC_PREP receipt, not refreshed to a moving model','Production archive absence is unknown, not zero/no settlement','No EMA is reseeded and no funding interval is changed','No model prediction, cash outcome or eligibility certification']}
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('source changed during read')
    (root/'RESULT.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    (root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n')
    print({k:record[k] for k in ['status','old_events','shared_events','old_only_count','new_only_oldwindow_count','extension_events_in_old_crypto_axis','extension_symbols','seconds']});print('rate_differences',len(different))

if __name__=='__main__':main(*sys.argv[1:])
