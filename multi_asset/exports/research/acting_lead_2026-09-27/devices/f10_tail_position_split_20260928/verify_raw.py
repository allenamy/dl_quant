"""Independent stdlib scalar accounting on prespecified raw-weight probes."""
from pathlib import Path
import copy, hashlib, json, math, sys

def verify(rows):
    n=0; worst=0.
    for r in rows:
        lengths={len(r[k]) for k in ('old','new','y')}
        if len(lengths)!=1:raise ValueError('raw population')
        groups=[]
        for idx in r['bins']:
            out=[[],[],[],[]]
            for i in idx:
                a,b,y=(r[k][i] for k in ('old','new','y'))
                if not all(math.isfinite(x) for x in (a,b,y)):raise ValueError('nonfinite')
                oldlong=a if a>0 else 0.; newlong=b if b>0 else 0.
                oldshort=a if a<0 else 0.; newshort=b if b<0 else 0.
                dl=newlong-oldlong; ds=newshort-oldshort
                out[0 if dl>0 else 1].append(dl*y*10000)
                out[2 if ds<0 else 3].append(ds*y*10000)
            groups.append([math.fsum(xs) for xs in out])
        for actual,expected in zip(r['parts_bps'],groups):
            for a,b in zip(actual,expected):
                err=abs(a-b);worst=max(worst,err);n+=1
                if err>1e-11:raise ValueError('scalar component differs')
    return {'checks':n,'max_abs_error':worst}

if __name__=='__main__':
    root=Path(sys.argv[1]);dest=Path(sys.argv[2]);raw=root.joinpath('RAW_CHECKS.json').read_bytes();rp=root.joinpath('RESULT.json').read_bytes();r=json.loads(rp)
    if hashlib.sha256(raw).hexdigest()!=r['raw_sha256']:raise ValueError('raw sha')
    rows=json.loads(raw);out=verify(rows)
    mutation=copy.deepcopy(rows);mutation[0]['parts_bps'][0][2]+=.01
    try:verify(mutation)
    except ValueError:out['wrong_short_component_rejected']=True
    else:raise ValueError('negative control failed')
    out.update(raw_sha256=r['raw_sha256'],result_sha256=hashlib.sha256(rp).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='prespecified every 30th original anchor, all members; not independent cash or bootstrap')
    with dest.open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
    print(json.dumps(out))
