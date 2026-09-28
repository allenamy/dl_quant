"""Read-only layer comparison; targets are intentions, never realized PnL."""
import argparse, hashlib, io, json, sys, time, zipfile
from pathlib import Path
import numpy as np

KING='700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d'
F10='3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f'
PINS={'NC_s42_literal.npz':'f6e7da7b8f9428752ef3abf973193c3d00628fca9636b80e5bedff0ce22b6ca8',
'LEGS_CONTINUATION.npz':'7caf1d5a1e85791fce1f663cf9c6b2591a5dc3c2b2b23e4b7d07ec9912a10737',
'KING_FEATURES_AND_MEMBERS.npz':'0a8f4bb1f9a01d5c6ecd7047e4f63a72fe627809186dbb176b9d202ff36b6855'}

def sha(b):return hashlib.sha256(b).hexdigest()
def axes(a,b):
    a=list(map(str,a));b=list(map(str,b))
    if len(set(a))!=len(a) or a!=b:raise ValueError('symbol_axis_not_identical_unique')
    return a

def sparse(idx,val,n):
    ii=np.asarray(idx);vv=np.asarray(val,dtype=float)
    if ii.ndim!=1 or vv.shape!=ii.shape or not np.isfinite(ii).all() or not np.equal(ii,np.floor(ii)).all():raise ValueError('invalid_sparse_axis')
    ii=ii.astype(int)
    if len(set(ii.tolist()))!=len(ii) or np.any(ii<0) or np.any(ii>=n) or not np.isfinite(vv).all():raise ValueError('invalid_sparse_values')
    out=np.zeros(n);out[ii]=vv;return out

def compare(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if a.shape!=b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('unavailable_comparison')
    d=np.abs(a-b)
    return {'n':int(a.size),'exact':bool(np.array_equal(a,b)),'equal_after_f32_cast':bool(np.array_equal(a.astype(np.float32),b.astype(np.float32))),
            'n_different':int(np.count_nonzero(d)),'max_abs':float(d.max()),'l1':float(d.sum()),'lhs_gross':float(np.abs(a).sum()),'rhs_gross':float(np.abs(b).sum())}

def check_anchor(doc,a):
    if type(doc.get('anchor_ts')) is not int or doc['anchor_ts']!=a:raise ValueError('anchor_identity_mismatch')

def model_status(doc,king,f10):
    if not doc.get('booster_sha') or not doc.get('f10_sha'):return 'UNAVAILABLE_MODEL_IDENTITY'
    return 'SAME_MODEL_FILES' if doc['booster_sha']==king and doc['f10_sha']==f10 else 'DIFFERENT_MODEL'

def seat(lr,look):
    r=[np.array(lr[k],float) for k in ('king','rev24','fund')]
    if len({len(x) for x in r})!=1 or any(x.ndim!=1 or not np.isfinite(x).all() for x in r):raise ValueError('invalid_LR_population')
    if len(r[0])>=look:
        r=np.stack([x[-look:] for x in r]);s=np.maximum(r.mean(1)/(r.std(1)+1e-9),0)
        w=s/s.sum() if s.sum()>0 else np.ones(3)/3
    else:w=np.ones(3)/3
    m=w.copy();m[1]=0
    m=m/m.sum() if m.sum()>0 else np.array([.5,0,.5])
    return w,m

def raw_from_states(kc,fc):return .55*kc+.45*fc

class Capture:
    def __init__(self,root,out):
        self.root=root;self.rows={};self.z=zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=1)
    def read(self,rel):
        if rel in self.rows:return self.z.read(rel)
        p=self.root/rel;b=p.read_bytes();h=sha(b)
        if sha(p.read_bytes())!=h:raise ValueError('input_changed_during_read:'+rel)
        self.z.writestr(rel,b);self.rows[rel]={'source':str(p),'sha256':h,'bytes':len(b)};return b
    def doc(self,rel):return json.loads(self.read(rel))
    def npz(self,rel):
        with np.load(io.BytesIO(self.read(rel)),allow_pickle=False) as z:return {k:z[k] for k in z.files}
    def close(self):self.z.close()

def manifest(c,a):
    prefix=f'state/snap/{a}/';complete=c.read(prefix+'COMPLETE')
    if not complete.strip():raise ValueError('empty_COMPLETE')
    lines=c.read(prefix+'SHA256SUMS').decode().splitlines();m={}
    for line in lines:
        h,n=line.split()
        if n in m or '/' in n or len(h)!=64:raise ValueError('ambiguous_snapshot_manifest')
        m[n]=h
    for name in ['aux.json','leg_returns_live.json']:
        if sha(c.read(prefix+name))!=m.get(name):raise ValueError('snapshot_sha_mismatch:'+name)
    aux=c.doc(prefix+'aux.json');lr=c.doc(prefix+'leg_returns_live.json')
    if aux.get('last_anchor')!=a:raise ValueError('aux_last_anchor_mismatch')
    check_anchor(aux['prev_rec'],a)
    return aux,lr

def dense_doc(d,sy):
    lookup={s:i for i,s in enumerate(sy)}
    if any(s not in lookup for s in d['weights']):raise ValueError('unknown_weight_symbol')
    return sparse([lookup[s] for s in d['weights']],list(d['weights'].values()),len(sy))

def run(ws,root,out):
    started=time.monotonic();out.mkdir(parents=True,exist_ok=False)
    research={}
    for name,h in PINS.items():
        b=(root/name).read_bytes()
        if sha(b)!=h:raise ValueError('research_input_sha:'+name)
        with np.load(io.BytesIO(b),allow_pickle=False) as z:research[name]={k:z[k] for k in z.files}
    combo=research['NC_s42_literal.npz'];legs=research['LEGS_CONTINUATION.npz'];fea=research['KING_FEATURES_AND_MEMBERS.npz']
    E=combo['E_ts'];expected=np.arange(1789776000,1790553600+1,14400)
    if not np.array_equal(E,expected) or not np.array_equal(E,legs['E_ts']) or not np.array_equal(E,fea['anchors']):raise ValueError('frozen_anchor_population')
    sy=axes(combo['symbols'],legs['symbols']);axes(sy,fea['symbols']);n=len(sy)
    c=Capture(ws,out/'PRODUCTION_INPUTS.zip');cfg=c.doc('shadow_bundle/config.json');axes(sy,cfg['symbols_panel'])
    if cfg['params']['msharpe_look']!=900:raise ValueError('unexpected_current_lookback')
    rows=[]
    try:
        for i,a0 in enumerate(E):
            a=int(a0);row={'anchor':a,'utc':time.strftime('%FT%TZ',time.gmtime(a)),'measurements':{},'unavailable':[]};rows.append(row)
            try:
                target=c.doc(f'state/target_live/{a}.json');check_anchor(target,a)
                side=c.read(f'state/target_live/{a}.json.sha256').decode().split()[0]
                if side!=sha(c.read(f'state/target_live/{a}.json')):raise ValueError('target_sidecar_mismatch')
                row['model_status']=model_status(target,KING,F10);row['king_sha']=target.get('booster_sha');row['f10_sha']=target.get('f10_sha')
                live=dense_doc(target,sy);row['measurements']['published_raw']=compare(live,combo['raw'][i])
            except (FileNotFoundError,ValueError,KeyError) as e:
                target=None;row['model_status']='UNAVAILABLE_MODEL_IDENTITY';row['unavailable'].append('target:'+str(e))
            try:
                aux,lr=manifest(c,a);pr=aux['prev_rec'];pm=np.asarray(pr['members']);sparse(pm,np.ones(len(pm)),n);pm=pm.astype(int)
                rm=fea['m'][fea['off'][i]:fea['off'][i+1]].astype(int)
                common=np.intersect1d(pm,rm);pos={int(j):k for k,j in enumerate(pm)}
                row['members']={'live':len(pm),'research':len(rm),'equal_ordered':bool(np.array_equal(pm,rm)),
                    'live_only':[sy[j] for j in np.setdiff1d(pm,rm)],'research_only':[sy[j] for j in np.setdiff1d(rm,pm)],'common':len(common)}
                for key,rkey in [('king','KZ'),('rev24','Z24'),('fund','ZFD')]:
                    vals=np.asarray(pr['legz'][key],float);sparse(pm,vals,n)
                    row['measurements'][key+'_z_common_members']=compare(vals[[pos[j] for j in common]],legs[rkey][i,common])
                w,m=seat(lr,900);row['live_w3']=w.tolist();row['live_masked_w3']=m.tolist();row['research_w3']=legs['WL'][i].astype(float).tolist();row['lr_count']=len(lr['king'])
                row['measurements']['w3']=compare(w,legs['WL'][i])
                row['base_n']=pr.get('base_n');row['fund_base_n']=pr.get('fund_base_n')
            except (FileNotFoundError,ValueError,KeyError) as e:row['unavailable'].append('snapshot:'+str(e))
            h={}
            for role in ['kc','fc']:
                try:
                    z=c.npz(f'fea171/state_H_{role}_{a}.npz')
                    if np.asarray(z['anchor']).item()!=a:raise ValueError('H_anchor_mismatch')
                    h[role]=sparse(z['idx'],z['val'],n);row['measurements']['H_'+role]=compare(h[role],combo[role][i])
                except (FileNotFoundError,ValueError,KeyError) as e:row['unavailable'].append('H_'+role+':'+str(e))
            if target is not None and len(h)==2:
                row['measurements']['live_own_raw_identity']=compare(live,raw_from_states(h['kc'],h['fc']))
            row['status']='MEASURED_WITH_GAPS' if row['unavailable'] else 'MEASURED'
    finally:c.close()
    result={'schema':'live_replay_layer_alignment/1','utc':time.strftime('%FT%TZ',time.gmtime()),'status':'DIAGNOSTIC_NOT_STRATEGY_CERTIFICATION',
        'source_sha256':sha(Path(__file__).read_bytes()),'research_inputs':PINS,'production_inputs':c.rows,'archive_sha256':sha((out/'PRODUCTION_INPUTS.zip').read_bytes()),
        'python':sys.executable,'numpy':np.__version__,'rows':rows,'seconds':time.monotonic()-started,
        'limits':['Historical symbol axis is interpreted with current pinned config; no historical config proof',
        'Member intersection metrics must be read together with complete member-set differences',
        'F10 raw scores absent in archived artifacts; file identity does not certify feature equality',
        'Continuous NC history is not actual manual reseed/migration/intervention history',
        'No economic attribution, profitability, statistical significance or release conclusion']}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'rows':len(rows),'source_files':len(c.rows),'seconds':result['seconds']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ws',type=Path,required=True);p.add_argument('--research',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.ws,a.research,a.out)
