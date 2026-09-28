"""Compare a fixed observed residual to the already completed GAP4 replay; no rerun."""
import importlib.util,json,zipfile,time
from pathlib import Path
import numpy as np
from alignment import sha,compare
from substitute import BASE,load_npz,load_state
A=1790524800

def main():
    root=Path('/Users/haosiyu/cc_tmp/gapfix_c0_round5_16Z_20260927')
    sub=json.loads((BASE/'result/SUBSTITUTION.json').read_text());pins={}
    for p,h in sub['inputs'].items():
        if sha(Path(p).read_bytes())!=h:raise ValueError('changed_input')
    z=zipfile.ZipFile(BASE/'result/PRODUCTION_INPUTS.zip');d=json.loads((BASE/'result/RESULT.json').read_text())
    if sha((BASE/'result/PRODUCTION_INPUTS.zip').read_bytes())!=d['archive_sha256']:raise ValueError('archive_identity')
    r=next(r for r in d['rows'] if r['anchor']==A)
    c=load_npz((BASE/'research/NC_s42_literal.npz').read_bytes());l=load_npz((BASE/'research/LEGS_CONTINUATION.npz').read_bytes());f=load_npz((BASE/'research/KING_FEATURES_AND_MEMBERS.npz').read_bytes());pr=load_npz((BASE/'research/NC_F10_s42_PREDICTIONS.npz').read_bytes());el=load_npz((BASE/'research/ELIGIBILITY.npz').read_bytes());i=int(np.flatnonzero(c['E_ts']==A)[0]);pm=f['m'][f['off'][i]:f['off'][i+1]].astype(int);sy=list(map(str,c['symbols']));N=len(sy)
    cfg=json.loads((BASE/'research/bundle_config.json').read_text());src=BASE/'step_sources/devices/combo_target.py';spec=importlib.util.spec_from_file_location('bound_step_gap_bridge',src);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    got=m.step(l['KZ'][i,pm].astype(float),pr['P'][i,pm].astype(float),l['ZFD'][i,pm].astype(float),np.array(r['live_w3']),l['RN8'][i,pm].astype(float),pm,l['QV'][i,pm].astype(float),el['legal'][i+1],cfg['params'],load_state(z,'kc',A-14400,N),load_state(z,'fc',A-14400,N))
    vectors={}
    for arm in ('current','patched'):
        p=root/f'{arm}_base/{A}/wide_shadow/state/target_live_PARITY/{A}.json';b=p.read_bytes();pins[str(p)]=sha(b);v=json.loads(b)
        if v['anchor_ts']!=A:raise ValueError('old_replay_anchor')
        vectors[arm]=np.array([v['weights'].get(s,0.) for s in sy]);(BASE/'result'/f'EXISTING_GAP_PARITY_{arm}_target.json').write_bytes(b)
    archived=json.loads(z.read(f'state/target_live/{A}.json'));v=np.array([archived['weights'].get(s,0.) for s in sy]);assert np.array_equal(v,vectors['current'])
    mhpath=Path(f'/Users/haosiyu/wide_shadow/state/snap/{A}/members_hist.npz');mhb=mhpath.read_bytes();man=dict((line.split()[1],line.split()[0]) for line in z.read(f'state/snap/{A}/SHA256SUMS').decode().splitlines());assert sha(mhb)==man['members_hist.npz'];mh=load_npz(mhb);missing=sorted(set(range(A-40*86400,A+1,14400))-set(map(int,mh['anchors'])));pins[str(mhpath)]=sha(mhb);(BASE/'result/EXISTING_GAP_members_hist.npz').write_bytes(mhb)
    out={'status':'EXISTING_GAP4_CONTROL_BRIDGED_NOT_NEW_RELEASE','utc':time.strftime('%FT%TZ',time.gmtime()),'anchor':A,'source_sha256':sha(Path(__file__).read_bytes()),'parent_substitution_sha256':sha((BASE/'result/SUBSTITUTION.json').read_bytes()),'inputs':pins,'current_matches_archive':True,'research_HW_vs_existing_patched':compare(got['raw'],vectors['patched']),'existing_patched_vs_current':compare(vectors['patched'],vectors['current']),'history_missing_last_24h':[a for a in missing if A-86400<=a<=A],'missing_at_exact_24h':A-86400 not in set(map(int,mh['anchors'])),'limits':['One actual fixed anchor; does not certify all F10 residuals','Existing GAP4 effect, not a newly discovered defect or strategy improvement','No production deployment; historical battery failure still blocks release']}
    (BASE/'result/GAP_BRIDGE.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
