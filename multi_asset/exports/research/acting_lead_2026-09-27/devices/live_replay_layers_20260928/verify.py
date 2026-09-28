"""Independent arithmetic/identity verification directly from archived inputs."""
import hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
BASE=Path('/Users/haosiyu/.codex/tmp/live_replay_layers_20260928')
def digest(b):return hashlib.sha256(b).hexdigest()
def arrays(b):
    with np.load(io.BytesIO(b),allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
    d=json.loads((BASE/'result/RESULT.json').read_text());s=json.loads((BASE/'result/SUBSTITUTION.json').read_text());c=json.loads((BASE/'result/CONTINUOUS.json').read_text());z=zipfile.ZipFile(BASE/'result/PRODUCTION_INPUTS.zip');checks=0;worst=0.
    for name,rec in d['production_inputs'].items():
        b=z.read(name);assert digest(b)==rec['sha256'] and len(b)==rec['bytes'];checks+=1
    assert len(z.namelist())==len(set(z.namelist()))==len(d['production_inputs']);checks+=1
    assert digest((BASE/'result/PRODUCTION_INPUTS.zip').read_bytes())==d['archive_sha256'];checks+=1
    cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];N=len(sy)
    research=arrays((BASE/'research/NC_s42_literal.npz').read_bytes());legs=arrays((BASE/'research/LEGS_CONTINUATION.npz').read_bytes());states=arrays((BASE/'result/CONTINUOUS_STATES.npz').read_bytes())
    def test(x,y):
        nonlocal checks,worst
        delta=abs(float(x)-float(y));worst=max(worst,delta);assert delta<=1e-12;checks+=1
    def dense(k,a):
        n=arrays(z.read(f'fea171/state_H_{k}_{a}.npz'));assert int(n['anchor'])==a
        v=np.zeros(N);v[n['idx']]=n['val'];return v
    def target(a):
        t=json.loads(z.read(f'state/target_live/{a}.json'));assert t['anchor_ts']==a;return np.array([t['weights'].get(q,0.) for q in sy])
    for i,r in enumerate(d['rows']):
        a=r['anchor'];assert int(research['E_ts'][i])==a;checks+=1
        if 'published_raw' in r['measurements']:
            v=target(a);x=r['measurements']['published_raw'];e=np.abs(v-research['raw'][i]);test(sum(e),x['l1']);test(max(e),x['max_abs']);test(np.count_nonzero(e),x['n_different'])
        if 'live_own_raw_identity' in r['measurements']:
            e=np.abs(target(a)-(.55*dense('kc',a)+.45*dense('fc',a)));test(e.max(),r['measurements']['live_own_raw_identity']['max_abs'])
        if 'members' in r:
            pr=json.loads(z.read(f'state/snap/{a}/aux.json'))['prev_rec'];pm=np.asarray(pr['members']);mi=np.array([j for j in pm if np.isfinite(legs['KZ'][i,j])]);idx={j:k for k,j in enumerate(pm)}
            for k,rk in [('king','KZ'),('rev24','Z24'),('fund','ZFD')]:
                a1=np.array([pr['legz'][k][idx[j]] for j in mi]);a2=legs[rk][i,mi];rr=r['measurements'][k+'_z_common_members'];test(sum(abs(a1-a2)),rr['l1']);test(max(abs(a1-a2)),rr['max_abs']);assert bool(np.array_equal(a1.astype('float32'),a2.astype('float32')))==rr['equal_after_f32_cast'];checks+=1
    for arm,rows in c['rows'].items():
        for r in rows:
            a=r['anchor'];v=target(a);p=states[f'{arm}_{a}'][2];err=abs(v-p);test(sum(err),r['error']['l1']);test(max(err),r['error']['max_abs'])
        # At schedule holds, the stored state must equal the prior arm's own state.
        if arm in ['C2','C3']:
            for a in c['hold_anchors']:
                for j in (0,1):assert np.array_equal(states[f'{arm}_{a}'][j],states[f'{arm}_{a-14400}'][j]);checks+=1
    same=[r for r in d['rows'] if r['model_status']=='SAME_MODEL_FILES'];last=d['rows'][-1];summary={'same_model_anchors':len(same),'signal_parity_anchors':sum(r.get('members',{}).get('equal_ordered',False) and all(r['measurements'][k]['equal_after_f32_cast'] for k in ('king_z_common_members','rev24_z_common_members','fund_z_common_members')) for r in same),'initial_reference_median_L1':float(np.median([r['measurements']['published_raw']['l1'] for r in same])),'continuous':{},'last_utc':last['utc'],'last_original_error_fraction_of_live_gross':last['measurements']['published_raw']['l1']/last['measurements']['published_raw']['lhs_gross']}
    for arm,rows in c['rows'].items():summary['continuous'][arm]={'median_L1':float(np.median([r['error']['l1'] for r in rows])),'last_L1':rows[-1]['error']['l1'],'last_max_abs':rows[-1]['error']['max_abs'],'last_L1_fraction_of_live_gross':rows[-1]['error']['l1']/rows[-1]['error']['lhs_gross']}
    out={'status':'PASS_WITH_RESEARCH_SCOPE_LIMITS','checks':checks,'max_arithmetic_delta':worst,'production_archive_members':len(z.namelist()),'result_sha256':digest((BASE/'result/RESULT.json').read_bytes()),'substitution_sha256':digest((BASE/'result/SUBSTITUTION.json').read_bytes()),'continuous_sha256':digest((BASE/'result/CONTINUOUS.json').read_bytes()),'summary':summary,'limits':['Recalculates recorded arithmetic and identities, not independently building missing F10 input panels','No cash evaluation or diagnosis of all original state divergences']}
    (BASE/'result/VERIFY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
