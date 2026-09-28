"""Fixed single-anchor state/seat substitutions; no returns or live mutations."""
import ast, importlib.util, io, json, sys, time, zipfile
from pathlib import Path
import numpy as np
from alignment import sha, sparse, compare, PINS

BASE=Path('/Users/haosiyu/.codex/tmp/live_replay_layers_20260928')
EXTRA={'ELIGIBILITY.npz':'1777b5d92974de23bd2593ad02779aa9e4c510aefae1aa89d212479b2c418cd3',
'NC_F10_s42_PREDICTIONS.npz':'1ac0c53db2406da73c7ab7763a86b07169e6885405cf7f86c42fc186ca805da8',
'bundle_config.json':'3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e'}

def kernels(raw):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in ('chain','exec_reshape')}
def exact_control(out,combo,i):
    if not out['accepted']:raise ValueError('reference_not_published')
    for k in ('kc','fc','raw'):
        if not np.array_equal(out[k],combo[k][i]):raise ValueError('reference_changed:'+k)
def load_npz(b):
    with np.load(io.BytesIO(b),allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    start=time.monotonic();d=json.loads((BASE/'result/RESULT.json').read_text());inputs={}
    for name,h in dict(PINS,**EXTRA).items():
        p=BASE/'research'/name;b=p.read_bytes()
        if sha(b)!=h:raise ValueError('input_sha:'+name)
        inputs[str(p)]=h
    Z=zipfile.ZipFile(BASE/'result/PRODUCTION_INPUTS.zip');assert sha((BASE/'result/PRODUCTION_INPUTS.zip').read_bytes())==d['archive_sha256']
    for name,rec in d['production_inputs'].items():
        if sha(Z.read(name))!=rec['sha256']:raise ValueError('archived_live_sha')
    src=BASE/'step_sources/devices/combo_target.py';old=BASE/'step_sources/vendor_live/fea171/combo_stage.py'
    if sha(src.read_bytes())!='d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544' or sha(old.read_bytes())!='fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8':raise ValueError('kernel_source_identity')
    current=Path('/Users/haosiyu/wide_shadow/fea171/combo_stage.py').read_bytes()
    (BASE/'step_sources/current_combo_stage.py').write_bytes(current)
    if set(kernels(current))!={'chain','exec_reshape'} or kernels(current)!=kernels(old.read_bytes()):raise ValueError('production_kernel_changed')
    for p in (src,old,BASE/'step_sources/current_combo_stage.py'):inputs[str(p)]=sha(p.read_bytes())
    spec=importlib.util.spec_from_file_location('bound_combo_step',src);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    data={name:load_npz((BASE/'research'/name).read_bytes()) for name in dict(PINS,**EXTRA) if name.endswith('.npz')}
    c=data['NC_s42_literal.npz'];l=data['LEGS_CONTINUATION.npz'];f=data['KING_FEATURES_AND_MEMBERS.npz'];pred=data['NC_F10_s42_PREDICTIONS.npz'];el=data['ELIGIBILITY.npz']
    params=json.loads((BASE/'research/bundle_config.json').read_text())['params'];livecfg=json.loads(Z.read('shadow_bundle/config.json'))
    used={x.slice.value for fn in ast.parse(current).body if isinstance(fn,ast.FunctionDef) and fn.name=='chain' for x in ast.walk(fn) if isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id=='P' and isinstance(x.slice,ast.Constant)}
    if any(params[k]!=livecfg['params'][k] for k in used):raise ValueError('chain_parameter_changed')
    E=c['E_ts'];sy=list(map(str,c['symbols']));N=len(sy)
    if not np.array_equal(pred['E_ts'],E) or not np.array_equal(pred['symbols'],c['symbols']) or not np.array_equal(el['E_ts'][1:],E):raise ValueError('extra_clock_or_axis')
    controls=0;rows=[]
    for i in range(1,len(E)):
        a=int(E[i]);pm=f['m'][f['off'][i]:f['off'][i+1]].astype(int)
        args=dict(king_rank=l['KZ'][i,pm].astype(float),f10_score=pred['P'][i,pm].astype(float),fund_rank=l['ZFD'][i,pm].astype(float),seats=l['WL'][i].astype(float),rn8=l['RN8'][i,pm].astype(float),members=pm,qv=l['QV'][i,pm].astype(float),legal=el['legal'][i+1],params=params,kc_prev=c['kc'][i-1].copy(),fc_prev=c['fc'][i-1].copy(),publication='literal')
        ref=m.step(**args);exact_control(ref,c,i);controls+=1
        r=d['rows'][i]
        if r['model_status']!='SAME_MODEL_FILES':continue
        row={'anchor':a,'utc':r['utc'],'status':'MEASURED','signal_parity_f32':bool(r.get('members',{}).get('equal_ordered')) and all(r['measurements'][k]['equal_after_f32_cast'] for k in ('king_z_common_members','rev24_z_common_members','fund_z_common_members')),'arms':{}};rows.append(row)
        try:
            prev={}
            for k in ('kc','fc'):
                v=load_npz(Z.read(f'fea171/state_H_{k}_{a-14400}.npz'))
                if int(v['anchor'])!=a-14400:raise ValueError('prior_state_clock')
                prev[k]=sparse(v['idx'],v['val'],N)
            target=json.loads(Z.read(f'state/target_live/{a}.json'))
            live=np.array([target['weights'].get(s,0.) for s in sy])
            for arm in ('R','H','W','HW'):
                ka=dict(args)
                if 'H' in arm:ka.update(kc_prev=prev['kc'].copy(),fc_prev=prev['fc'].copy())
                if 'W' in arm:ka['seats']=np.array(r['live_w3'])
                got=m.step(**ka)
                if not got['accepted']:raise ValueError('substitution_release_gate:'+arm)
                row['arms'][arm]=compare(live,got['raw'])
                row['arms'][arm]['kc_error']=compare(load_state(Z,'kc',a,N),got['kc'])
                row['arms'][arm]['fc_error']=compare(load_state(Z,'fc',a,N),got['fc'])
        except (KeyError,ValueError) as e:row['status']='UNAVAILABLE';row['reason']=str(e)
    # Deliberately corrupt a known reference output, preserving population.
    bad={k:v.copy() if isinstance(v,np.ndarray) else v for k,v in ref.items()};bad['raw'][0]+=1e-5
    rejected=False
    try:exact_control(bad,c,len(E)-1)
    except ValueError:rejected=True
    if not rejected:raise ValueError('reference_control_lacks_red_capacity')
    result={'schema':'fixed_single_anchor_state_substitutions/1','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(Path(__file__).read_bytes()),'inputs':inputs,'parent_result_sha256':sha((BASE/'result/RESULT.json').read_bytes()),'reference_exact_controls':controls,'reference_corruption_refused':rejected,'current_kernel_AST_equal':True,'chain_parameter_keys':sorted(used),'rows':rows,'seconds':time.monotonic()-start,'limits':['Same model files, not F10 inference parity','Single-anchor substitutions conditional on original research inputs; not independently evolving strategy arms','No returns, no economic explanation or strategy release']}
    (BASE/'result/SUBSTITUTION.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print({'controls':controls,'same_model_rows':len(rows),'seconds':result['seconds']})

def load_state(z,k,a,n):
    v=load_npz(z.read(f'fea171/state_H_{k}_{a}.npz'));return sparse(v['idx'],v['val'],n)
if __name__=='__main__':main()
