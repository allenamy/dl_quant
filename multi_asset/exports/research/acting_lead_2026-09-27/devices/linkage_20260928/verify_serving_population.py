"""Independent scalar OLS and direct-window verification; no economic outcomes."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np

def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main(source,out):
    s=Path(source);out=Path(out);C=json.loads((s/'SERVING_POPULATION_CONTRACT.json').read_text())
    R=json.loads((out/'RESULT.json').read_text());T=json.loads((out/'TERMINAL.json').read_text())
    assert T['rc']==0 and T['result_sha256']==h(out/'RESULT.json')
    assert h(out/'COMPARISON.npz')==R['outputs']['COMPARISON.npz']
    for p,sha in C['inputs'].items():assert h(p)==sha
    snap=json.loads(Path(C['snapshot']).read_text());t=np.array(snap['ts']);day=C['day'];ends=[]
    for q in range(48,len(t)):
        if t[q]%14400==0 and t[q]<day and np.array_equal(t[q-48:q+1],np.arange(t[q]-14400,t[q]+1,300)):ends.append(int(t[q]))
    assert len(ends)==R['cache_support']['closed_before_day'] and ends[0]==R['cache_support']['first'] and ends[-1]==R['cache_support']['last']
    z=np.load(C['panel']);a=np.load(out/'COMPARISON.npz');sy=z['symbols'];ts=z['anchors'];ix=int(np.flatnonzero(ts==day)[0])
    mask=(ts>=day-360*14400)&(ts<day);r=z['r4'][mask];l=z['legal'][mask];fetch=np.isin(sy,snap['fetch_names']);common=a['scope']
    assert np.array_equal(common,z['legal'][ix]&fetch)
    errors=[];checks=0;recomputed={}
    for kind,active,now in [('full',l,z['legal'][ix]),('fetch',l&fetch,z['legal'][ix]&fetch)]:
        beta=np.full(len(sy),np.nan);scale=beta.copy();m4=beta.copy();m24=beta.copy()
        for j in np.flatnonzero(common):
            others=np.arange(len(sy))!=j;means=[];ys=[]
            for row in range(len(r)):
                ok=others&active[row]&np.isfinite(r[row])
                if active[row,j] and np.isfinite(r[row,j]) and ok.sum()>=20:
                    means.append(float(r[row,ok].mean()));ys.append(float(r[row,j]))
            x,y=np.array(means),np.array(ys)
            assert len(x)>=240
            dx=x-x.mean();dy=y-y.mean();beta[j]=float(np.dot(dx,dy)/np.dot(dx,dx));scale[j]=float(np.std(y-beta[j]*x))
            for key,v in [('beta',beta[j]),('scale',scale[j])]:
                saved=a[key+'_'+kind][j];errors.append(abs(v-saved));assert np.isclose(v,saved,rtol=1e-10,atol=1e-12);checks+=1
            for key,dest in [('r4',m4),('r24',m24)]:
                ok=others&now&np.isfinite(z[key][ix]);dest[j]=z[key][ix,ok].mean()
        e4=z['r4'][ix]-beta*m4;e24=z['r24'][ix]-beta*m24
        own=np.column_stack((e4/scale,e24/(scale*np.sqrt(6))));peers=a['peers_'+kind];X=np.full((len(sy),4),np.nan)
        for j in np.flatnonzero(common):
            ps=peers[j];ps=ps[(ps>=0)];ps=ps[now[ps]]
            assert np.isfinite(e4[ps]).all() and np.isfinite(e24[ps]).all() and len(ps)>=8
            X[j]=[e4[ps].mean()/scale[j],e24[ps].mean()/scale[j]/np.sqrt(6),(e24[j]-e24[ps].mean())/scale[j]/np.sqrt(6),(e4[ps]>0).mean()]
        for key,x in [('own',own),('X',X)]:
            old=a[key+'_'+kind];d=np.abs(x[common]-old[common]);assert np.allclose(x[common],old[common],rtol=1e-9,atol=1e-10);errors.extend(d.ravel());checks+=d.size
        recomputed[kind]=(beta,scale)
    removed=l&~fetch[None,:];changed=[]
    for j in np.flatnonzero(common):
        p=set(a['peers_full'][j]);q=set(a['peers_fetch'][j]);p.discard(-1);q.discard(-1)
        if p!=q:changed.append(str(sy[j]))
    diff=np.abs(a['X_full'][:,1]-a['X_fetch'][:,1]);ordered=sorted(np.flatnonzero(common),key=lambda j:-diff[j])[:5]
    top=[]
    for j in ordered:
        p=set(a['peers_full'][j]);q=set(a['peers_fetch'][j]);p.discard(-1);q.discard(-1)
        top.append({'symbol':str(sy[j]),'peer24_abs_delta':float(diff[j]),'removed_peers':[str(sy[k]) for k in sorted(p-q)],'added_peers':[str(sy[k]) for k in sorted(q-p)]})
    result={'status':'VERIFIED','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':h(__file__),'result_sha256':h(out/'RESULT.json'),
            'checks':int(checks),'max_absolute_arithmetic_delta':float(max(errors)),'independent_cache_count':len(ends),
            'history_member_cells_excluded':int(removed.sum()),'history_symbols_excluded':{str(sy[j]):int(removed[:,j].sum()) for j in np.flatnonzero(removed.any(0))},
            'names_with_changed_peer_set':len(changed),'largest_peer24_differences':top,
            'scope':'Direct scalar OLS/own/peer feature reconstruction from original panel; does not independently rerank every historical correlation or verify price source/actual receipt time'}
    (out/'INDEPENDENT_VERIFY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result))

if __name__=='__main__':main(*sys.argv[1:])
