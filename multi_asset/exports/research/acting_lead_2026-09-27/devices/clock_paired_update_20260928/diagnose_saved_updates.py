"""Post-read diagnosis only. No optimization; fixed splice at first baseline fill.
Rule written before this diagnostic's output: first baseline publication + 1.
Carry baseline quantity at the splice, then obey candidate HOLD quantities.
This is not a producer-state-consistent strategy backtest or causal effect.
"""
import io,json,zipfile,hashlib,pathlib
import numpy as np

def run(root):
    z=zipfile.ZipFile(root/'ARCHIVE.zip')
    def load(n):
        with np.load(io.BytesIO(z.read(n)),allow_pickle=False) as a:return {k:a[k] for k in a.files}
    base=load('BASE_HARD_ARRAYS.npz');co=load('CLOCK_COEFFICIENTS.npz')
    atoms=json.loads(z.read('CLOCK_COEFFICIENT_RECEIPT.json'))['atoms'];total=sum(x[1] for x in atoms)
    def cash(w,mask,zero_at=None):
        q=np.zeros(w.shape[1]);out={k:[] for k in ('price','fee','carry','q_start')}
        for i,target0 in enumerate(w):
            if i==zero_at:q*=0 # Explicit wrong-state red comparator, not evaluator behavior.
            out['q_start'].append(q.copy());delta=np.zeros_like(q)
            if mask[i]:
                target=target0.copy();nz=np.abs(target)>1e-12
                if nz.any():
                    shaped=np.where(nz,target-target[nz].mean(),target);g=np.abs(shaped).sum()
                    if g>1e-9:shaped*=np.abs(target).sum()/g
                    target=shaped
                delta=200000*target/co['p_dec'][i]-q
            out['price'].append(np.sum(q*co['price_old'][i]+delta*co['price_delta'][i]-np.abs(delta)*co['slip_abs'][i])*.1)
            out['fee'].append(np.sum(np.abs(delta)*co['fee_abs'][i]+delta*co['fee_signed'][i])*.1)
            out['carry'].append(np.sum(q*co['carry_old'][i]+delta*co['carry_delta'][i])*.1)
            q+=total*delta
        return {k:np.array(v) for k,v in out.items()}
    checks={}
    for name in ('BASE','A0','A1'):
        a=base if name=='BASE' else load(name+'_HARD_ARRAYS.npz');b=cash(a['weights'],a['trade_mask'])
        checks[name]=max(float(np.max(np.abs(a[k]-b[k]))) for k in ('price','fee','carry'))
    if max(checks.values())>1e-8:raise ValueError('independent cash does not match saved proxy')
    pub=np.flatnonzero(base['trade_mask'])
    if not len(pub) or pub[0]+1>=len(base['trade_mask']):raise ValueError('no supported splice')
    cut=int(pub[0]+1);rows={}
    for name in ('A0','A1'):
        a=load(name+'_HARD_ARRAYS.npz');mask=a['trade_mask'].copy();w=a['weights'].copy();mask[:cut]=base['trade_mask'][:cut];w[:cut]=base['weights'][:cut]
        if mask[cut:].any():raise ValueError('expected saved all-HOLD diagnosis only')
        good=cash(w,mask);bad=cash(w,mask,zero_at=cut)
        q=good['q_start'][cut];qdiff=float(np.max(np.abs(good['q_start'][cut:]-q)))
        if qdiff!=0 or np.abs(q).sum()==0:raise ValueError('HOLD not preserving nonzero quantity')
        if np.abs(bad['q_start'][cut:]).sum()!=0:raise ValueError('red reset did not reset')
        rows[name]={'cut_index':cut,'first_baseline_publish_index':cut-1,'remaining_anchors':len(mask)-cut,'carried_names':int(np.count_nonzero(q)),
            'carried_quantity_constant_max_error':qdiff,'wrong_reset_quantity_difference_l1':float(np.abs(q).sum()),
            'retained_quantity_proxy_sum_NAV_bps':{k:float(good[k][cut:].sum()) for k in ('price','fee','carry')},
            'wrong_reset_proxy_sum_NAV_bps':{k:float(bad[k][cut:].sum()) for k in ('price','fee','carry')}}
    out={'scope':'saved-output intervention on quantity initialization, not a full producer-state candidate and not efficacy','selection':'first baseline publication + 1, frozen before diagnostic output','cash_parity_error_NAV_bps':checks,'rows':rows,'archive_sha256':hashlib.sha256((root/'ARCHIVE.zip').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    with open(root/'HOLD_NONZERO_STATE_DIAG.json','x') as f:json.dump(out,f,indent=2,allow_nan=False)
    print(json.dumps(out,indent=2))
if __name__=='__main__':
    import sys
    run(pathlib.Path(sys.argv[1]))
