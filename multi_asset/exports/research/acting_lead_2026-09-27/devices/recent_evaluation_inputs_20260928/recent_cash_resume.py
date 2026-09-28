"""Resume unchanged cash engine after proving terminal sampler BLAS geometry.
Only the old terminal NAV5 sample may differ by one ULP. Every economic field,
every other historical 5m point, and the complete anchor axis remain exact.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import numpy as np
import json,sys,time,subprocess,signal,traceback
from funding_overlap import sha
from recent_king_features import materialize
from recent_cash_run import stem
OLD=Path('/dev/shm/recent_nc_cash_20260928')
PROBE=Path('/dev/shm/recent_nc_cash_seam_probe_20260928/RESULT.json')

def semantic_prefix(a,b):
    if set(a)!=set(b):raise ValueError('fields differ')
    changes=[]
    for k,v in a.items():
        q=b[k] if v.ndim==0 else b[k][:len(v)]
        if v.shape!=q.shape or v.dtype!=q.dtype:raise ValueError('shape/dtype '+k)
        if v.tobytes()==q.tobytes():continue
        if k not in ('nav5_main','nav5_sim') or len(b['A'])<=len(a['A']):raise ValueError('economic prefix differs '+k)
        if v[:-1].tobytes()!=q[:-1].tobytes():raise ValueError('NAV interior differs')
        end=int(a['nav5_t0'])+300*(len(v)-1)
        if end!=int(a['A'][-1])+14400 or end!=int(b['A'][len(a['A'])]):raise ValueError('not the old terminal')
        if not np.isfinite([v[-1],q[-1]]).all() or v[-1]<=0 or q[-1]<=0:raise ValueError('nonfinite/negative sample')
        delta=float(q[-1]-v[-1]);ulp=float(abs(np.spacing(v[-1])))
        if abs(delta)>ulp:raise ValueError('terminal differs by more than one ULP')
        changes.append({'field':k,'delta_usd':delta,'ulp_usd':ulp,'timestamp':end})
    return {'fields':len(a),'anchors':len(a['A']),'economic_and_interior_prefix_bitwise_equal':True,'endpoint_samples_changed':changes,'all_bytes_equal':not changes}

def main(root):
    root=Path(root);root.mkdir(exist_ok=False);start=time.monotonic();deadline=start+1800
    pr=json.loads(PROBE.read_text())
    if pr['status']!='SAME_STATE_SAMPLER_BATCH_SHAPE_REPRODUCED' or not pr['observer_path_unchanged']['bitwise_prefix_equal']:raise ValueError('probe not proven')
    if pr['records'][0]['rows_short']!=1 or pr['records'][0]['rows_long']!=5 or not pr['records'][0]['short_bitwise_old']:raise ValueError('probe shape')
    manifests=json.loads((OLD/'BASELINE_MANIFEST.json').read_text());sys.path.insert(0,str(OLD/'engine'));import bt_driver_lib as DL
    def verify(sd):
        rr=OLD/f's{sd}';cfg=json.loads((rr/'CONFIG.json').read_text());tag=cfg['runs'][0]['tag'];out={}
        for seed,ref in enumerate(manifests[str(sd)]):
            st=stem(rr,tag,seed);jp=Path(str(st)+'.json');npz=Path(str(st)+'.npz')
            if not jp.exists() or not npz.exists():continue
            if sha(ref['npz'])!=ref['sha256'] or sha(ref['json'])!=ref['json_sha256']:raise ValueError('baseline drift')
            j=json.loads(jp.read_text())
            if j['npz_sha256']!=sha(npz) or not DL.audits_clean(j['audits']):raise ValueError('new audit')
            out[str(seed)]=semantic_prefix(materialize(ref['npz']),materialize(npz))
        return out
    before={str(s):verify(s) for s in (42,2027)}
    (root/'REUSED_PATHS.json').write_text(json.dumps(before,indent=2)+'\n')
    if len(before['42'])!=32 or len(before['2027'])!=1:raise ValueError('unexpected resume population')
    cp=OLD/'s2027/CONFIG.json';cmd=['/workspace/venv/bin/python','-u',str(OLD/'engine/bt_launch.py'),'PATH,HOME,LC_CTYPE',str(cp),'--resume','recent_seam_verified']
    with (root/'RUN.log').open('x') as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','HOME':'/root','LC_CTYPE':'C.UTF-8'},start_new_session=True)
        (root/'CHILD.json').write_text(json.dumps({'pid':p.pid,'pgid':os.getpgid(p.pid),'ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'cmd':cmd},indent=2))
        try:rc=p.wait(timeout=deadline-time.monotonic())
        except BaseException:
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=30)
            raise
    if rc:raise RuntimeError('engine failed '+str(rc))
    allchecks={str(s):verify(s) for s in (42,2027)}
    if any(len(v)!=32 for v in allchecks.values()):raise ValueError('missing paths')
    (root/'PREFIX_CONTROLS.json').write_text(json.dumps(allchecks,indent=2)+'\n')
    ir=json.loads(Path('/dev/shm/recent_nc_cash_inputs_20260928/RESULT.json').read_text())
    result={'status':'RECENT_NC_CASH_COMPLETE_SAMPLER_TERMINAL_1ULP_DECLARED','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'paths':64,'all64_anchor_and_interior_prefixes_bitwise_equal':True,'all64_old_prefixes_bitwise_equal':all(x['all_bytes_equal'] for d in allchecks.values() for x in d.values()),'terminal_sampler_exception':'old final NAV5 only, <=1 ULP; economic accounts and all other historical samples exact','probe':{'path':str(PROBE),'sha256':sha(PROBE)},'old_failed_terminal_sha256':sha(OLD/'TERMINAL.json'),'controls_sha256':sha(root/'PREFIX_CONTROLS.json'),'configs':{str(s):{'path':str(OLD/f's{s}/CONFIG.json'),'sha256':sha(OLD/f's{s}/CONFIG.json')} for s in (42,2027)},'limitations':ir['limits']+['Exact old terminal NAV5 bytes are not preserved in all paths; explicit sampler geometry exception'],'seconds':time.monotonic()-start}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n')

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        p=Path(sys.argv[1]);p.mkdir(exist_ok=True);(p/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
