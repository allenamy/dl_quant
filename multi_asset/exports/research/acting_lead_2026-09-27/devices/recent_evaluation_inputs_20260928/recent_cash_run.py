"""Frozen-NC recent cash continuation: unchanged simulator, exact prior path gate.

No training, tuning, live state writes, live arm outcomes or publication action.
Old simulated prefixes must match ALL stored fields on ALL 64 paths. The only
driver change is the declared count of UNKNOWN bars in an extended data axis.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import sys,json,time,shutil,subprocess,signal,traceback
import numpy as np
from funding_overlap import sha
from recent_king_features import materialize
from recent_legs import certified

NS=Path('/dev/shm/news2_2026-09-23')
INP=Path('/dev/shm/recent_nc_cash_inputs_20260928')
INPUT_RESULT='f8887bfebe49b9c6b89f100c69ac065dcd2859ca34baaa706d4ae1467b12e2d7'
PY='/workspace/venv/bin/python'

def prefix_check(old,new):
    if set(old)!=set(new):raise ValueError('path field set')
    for k,v in old.items():
        q=new[k] if v.ndim==0 else new[k][:len(v)]
        if v.dtype!=q.dtype or v.shape!=q.shape or v.tobytes()!=q.tobytes():raise ValueError('old path prefix differs '+k)
    return {'fields':len(old),'anchors':len(old['A']),'bitwise_prefix_equal':True}

def patch_ua_count(s,n):
    old='want_n = {"UNAVAILABLE_3084": 3084, "OLD_ZERO_PRICED_INLIFE_NAN": 24397}'
    if s.count(old)!=1 or type(n)!=int or n<3084:raise ValueError('UA-count source identity')
    return s.replace(old,old.replace(': 3084,',f': {n},'))

def stem(root,tag,seed,smoke=False):
    t=tag.replace('|','_');d=root/('runs_smoke/prefix' if smoke else 'runs')/t
    return d/f'PATH_{t}_seed_{seed:02d}'

def main(root):
    start=time.monotonic();deadline=start+2700;root=Path(root);root.mkdir(exist_ok=False);pins={str(Path(__file__)):sha(__file__)}
    if sha(INP/'RESULT.json')!=INPUT_RESULT:raise ValueError('cash input result identity')
    ir=certified(INP,pins);end=ir['last_priced_anchor'];src=NS/'engine';engine=root/'engine';engine.mkdir()
    for p in src.glob('*.py'):shutil.copyfile(p,engine/p.name);pins[str(p)]=sha(p)
    lib=engine/'bt_driver_lib.py';lib.write_text(patch_ua_count(lib.read_text(),ir['price']['total_unknown_cells']))
    (root/'DRIVER_CHANGE.json').write_text(json.dumps({'source_sha':sha(src/'bt_driver_lib.py'),'derived_sha':sha(lib),'only_change':'literal UA set count for extended data axis','old_n':3084,'new_n':ir['price']['total_unknown_cells'],'input_result_sha':INPUT_RESULT},indent=2)+'\n')
    sys.path.insert(0,str(engine));import ovn_adapter as OA,bt_objb_targets as OT,bt_driver_lib as DL
    if sha(engine/'bt_objb_targets.py')!='05cc5dc25df99459d93b34c9b10477f08002dd301b9b45ec6aa47bd77fc95373':raise ValueError('adapter loader source')
    manifests={};configs={}
    for sd in (42,2027):
        ref=Path(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{sd}X/runs/DLARCH_REF_NC_s{sd}X_scaled_rule_raw_UAFE');files=[]
        for seed in range(32):
            st=ref/f'PATH_DLARCH_REF_NC_s{sd}X_scaled_rule_raw_UAFE_seed_{seed:02d}';jp=Path(str(st)+'.json');npz=Path(str(st)+'.npz');j=json.loads(jp.read_text());h=sha(npz)
            if j['npz_sha256']!=h or not DL.audits_clean(j['audits']):raise ValueError('baseline path audit')
            files.append({'npz':str(npz),'json':str(jp),'sha256':h,'json_sha256':sha(jp),'seed':seed})
        manifests[str(sd)]=files
        runroot=root/f's{sd}';runroot.mkdir();(runroot/'receipts').mkdir();arm=f'RECENT_NC_s{sd}';combo=INP/f'combo_s{sd}'
        spec={'arm':arm,'data':'NC original continuous state extended to Sep27; not current live intervention path','scaled':{'npz':str(combo/'scaled_diagnostic.npz'),'sha256':sha(combo/'scaled_diagnostic.npz')},'lit':{'npz':str(combo/'literal.npz'),'sha256':sha(combo/'literal.npz')},'new_receipt':{'path':str(combo/'TARGET_RECEIPT.json'),'sha256':sha(combo/'TARGET_RECEIPT.json')},'price_meta':{'path':str(INP/'price_meta_recent.npz'),'sha256':sha(INP/'price_meta_recent.npz')},'universe':{'path':str(INP/'universe_recent.npz'),'sha256':sha(INP/'universe_recent.npz')},'window_first_anchor':'2022-06-30T00:00:00Z'}
        out,info,D=OA.build(spec);npz=runroot/'TARGETS.npz';rec=runroot/'TARGETS.json';OA.write(out,info,spec,str(npz),str(rec),sha(engine/'ovn_adapter.py'))
        rt=OA.verify_roundtrip(str(npz),str(rec),arm,D,OA.ts(spec['window_first_anchor']),OT);r=json.loads(rec.read_text());r['roundtrip']=rt;rec.write_text(json.dumps(r,indent=2)+'\n')
        cfgp=NS/f'configs/RUN_CONFIG_NEWS2_s{sd}X_2026-09-23.json';pins[str(cfgp)]=sha(cfgp);cfg=json.loads(cfgp.read_text());cfg['status']='RESEARCH_RECENT_EXTENSION_NOT_RELEASE';cfg['paths']['pod_root']=str(runroot);cfg['paths_R']=32
        cfg['window']['last_anchor']=OA.iso(end);cfg['window']['n_anchors']=(end-OA.ts(cfg['window']['first_anchor']))//14400+1
        for k,n in {'price_full_raw':'price_full_recent.npy','price_full_meta':'price_meta_recent.npz','price_receipt':'PRICE_RECEIPT.json','ledger_full':'ledger_recent.npz','tradability':'tradability_recent.npz','universe':'universe_recent.npz'}.items():cfg['pins'][k]={'path':str(INP/n),'sha256':sha(INP/n)}
        cfg['pins']['recent_input_receipt']={'path':str(INP/'RESULT.json'),'sha256':INPUT_RESULT}
        for p in engine.glob('*.py'):cfg['pins']['engine_'+p.stem]={'path':str(p),'sha256':sha(p)}
        run=cfg['runs'][0];run['tag']=f'{arm}|scaled|rule|raw|UAFE';run['arm']=arm;run['targets'].update(arm=arm,sources=[{'npz':str(npz),'npz_sha256':sha(npz),'receipt':str(rec),'receipt_sha256':sha(rec)}],universe=spec['universe']);run['role']='recent fixed NC descriptive baseline'
        cfg['recent_extension']={'input_receipt_sha':INPUT_RESULT,'old_prefix_gate':'every field of 64 original path files exact','scope':'fixed NC / old execution mirror / pooled costs / scaled historical publication / UA-exclude; not current live certification'}
        cp=runroot/'CONFIG.json';cp.write_text(json.dumps(cfg,indent=2)+'\n');configs[sd]=(cp,cfg,runroot,run['tag'])
    (root/'BASELINE_MANIFEST.json').write_text(json.dumps(manifests,indent=2)+'\n')
    children=[]
    def launch(sd,smoke):
        cp,cfg,rr,tag=configs[sd];cmd=[PY,'-u',str(engine/'bt_launch.py'),'PATH,HOME,LC_CTYPE',str(cp)]
        if smoke:cmd+=['--smoke',cfg['window']['first_anchor'],str(cfg['window']['n_anchors']),'0',tag,'prefix']
        else:cmd+=['--resume','recent']
        log=rr/('PREFIX.log' if smoke else 'RUN.log');remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('whole cash budget')
        with log.open('x') as f:
            p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','HOME':'/root','LC_CTYPE':'C.UTF-8'},start_new_session=True)
            identity={'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'cmd':cmd};children.append(identity);(root/'CHILDREN.json').write_text(json.dumps(children,indent=2)+'\n')
            try:rc=p.wait(timeout=remaining)
            except BaseException:
                if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=30)
                raise
        if rc:raise RuntimeError('engine rc '+str(rc)+' '+str(log))
    # Both baseline controls run before the costly batch or any economic table.
    checks={}
    for sd in (42,2027):
        launch(sd,True);cp,cfg,rr,tag=configs[sd];st=stem(rr,tag,0,True);old=materialize(manifests[str(sd)][0]['npz']);new=materialize(str(st)+'.npz');checks[str(sd)]=prefix_check(old,new)
        out=json.loads(Path(str(st)+'.json').read_text())
        if not DL.audits_clean(out['audits']):raise ValueError('new prefix path internal audit')
        dest=stem(rr,tag,0);dest.parent.mkdir(parents=True)
        for ext in ('.json','.npz'):shutil.copyfile(str(st)+ext,str(dest)+ext)
        (root/'PREFIX_CONTROLS.json').write_text(json.dumps(checks,indent=2)+'\n');print('PREFIX EXACT',sd,checks[str(sd)],flush=True)
    for sd in (42,2027):
        launch(sd,False);cp,cfg,rr,tag=configs[sd]
        for seed,ref in enumerate(manifests[str(sd)]):
            if sha(ref['npz'])!=ref['sha256'] or sha(ref['json'])!=ref['json_sha256']:raise ValueError('baseline drift')
            st=stem(rr,tag,seed);o=json.loads(Path(str(st)+'.json').read_text())
            if o['npz_sha256']!=sha(str(st)+'.npz') or not DL.audits_clean(o['audits']):raise ValueError('new path internal audit')
            checks[f'{sd}_{seed}']=prefix_check(materialize(ref['npz']),materialize(str(st)+'.npz'))
        (root/'PREFIX_CONTROLS.json').write_text(json.dumps(checks,indent=2)+'\n');print('FULL CASH VERIFIED',sd,flush=True)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    r={'status':'RECENT_NC_CASH_COMPLETE_NOT_CURRENT_LIVE_PARITY','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'last_priced_anchor':end,'paths':64,'all64_old_prefixes_bitwise_equal':True,'configs':{str(sd):{'path':str(v[0]),'sha256':sha(v[0])} for sd,v in configs.items()},'baseline_manifest_sha256':sha(root/'BASELINE_MANIFEST.json'),'controls_sha256':sha(root/'PREFIX_CONTROLS.json'),'seconds':time.monotonic()-start,'limitations':ir['limits']}
    (root/'RESULT.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print(r['status'],flush=True)

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
