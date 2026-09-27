"""Read-only fixed-pack price-unit/cash-coefficient verification. No network model."""
import hashlib,json,os,pathlib,resource,signal,time
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(2*2**30,2*2**30))
signal.alarm(90)
import numpy as np
from price_units import panel_class,decode_log_prices

ROOT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding')
PACK=ROOT/'first120_input_pack_20260927'
OUT=ROOT/'first120_price_units_validation_20260928'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(n,x):
    with open(OUT/n,'x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def load_npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    started=time.monotonic();OUT.mkdir(exist_ok=False)
    free=int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())-int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
    if free<10*2**30:raise ValueError('RESOURCE_REFUSED')
    cfgpath=ROOT/'first120_canonical_20260927/RUN_CONFIG.json'
    if sha(cfgpath)!='3a482d58c3adbc3f42ddf92c05539594ab078f6a7f5c589babc9060830b4fb63':raise ValueError('config drift')
    cfg=json.loads(cfgpath.read_text());result=json.loads((PACK/'RESULT.json').read_text())
    if sha(PACK/'RESULT.json')!='2bc7bef5234e29782fbfd0010d8eef8af74a0f93b3b7c698e6c97bb995fcc65b':raise ValueError('pack result drift')
    used={}
    for n in ('AXES.npz','LEGS.npz','LEGAL.npy','PRICE_RAW.npy','PRICE_TS.npy','EVENTS.npz'):
        if sha(PACK/n)!=result['artifacts'][n]['sha256']:raise ValueError('pack drift '+n)
        used[n]=result['artifacts'][n]['sha256']
    mp=cfg['inherited_pins']['price_full_meta']
    if sha(mp['path'])!=mp['sha256']:raise ValueError('meta drift')
    meta=load_npz(mp['path']);axes=load_npz(PACK/'AXES.npz');raw=np.load(PACK/'PRICE_RAW.npy',mmap_mode='r');ts=np.load(PACK/'PRICE_TS.npy',mmap_mode='r')
    source='/dev/shm/news2_2026-09-23/engine/bt_hist_sim31.py';source_sha='8ae6e2a441d700824372784b1bc0bd9e0ee2f686a3c22f522b6bb962911022a1'
    price,receipt=decode_log_prices(np,raw,ts,axes['symbols'],meta,panel_class(np,source,source_sha))
    # Independent vector equation and missingness; do not call FullPanel again as the oracle.
    known=(meta['first_fin'][None,:]>=0)&(ts[:,None]>=meta['first_fin'][None,:])
    expected=np.exp(np.asarray(raw)-meta['cref_raw'][None,:])*meta['ref_px'][None,:]
    if not np.array_equal(np.isfinite(price),known):raise ValueError('decoded missingness mismatch')
    relative=np.abs(price[known]-expected[known])/expected[known]
    if float(relative.max())>1e-14:raise ValueError('independent price equation differs')
    negative_as_price=int((np.isfinite(raw)&(raw<=0)&known).sum())
    if negative_as_price==0:raise ValueError('old interpretation red did not bite')
    # Preserve the frozen coefficient/control code; only supply correctly decoded prices.
    import importlib.util
    cp=ROOT/'first120_path_repair_sources/funding_first120_clock_core.py'
    if sha(cp)!='95405f57ad9f6c3f662784fdfa5049c44d2f24251b13cdc94328f34fc6ae756f':raise ValueError('core drift')
    sp=importlib.util.spec_from_file_location('fixed_clock_core',cp);core=importlib.util.module_from_spec(sp);sp.loader.exec_module(core)
    bp=cfg['input_pins']['combo_input_bundle_config.json'];calp=cfg['inherited_pins']['calibration']
    for v in (bp,calp):
        if sha(v['path'])!=v['sha256']:raise ValueError('coefficient dependency drift')
    off=axes['off'];data={**axes,'members':[axes['m'][off[i]:off[i+1]] for i in range(120)],'legs':load_npz(PACK/'LEGS.npz'),
                        'legal':np.load(PACK/'LEGAL.npy',mmap_mode='r'),'params':json.loads(pathlib.Path(bp['path']).read_text())['params'],
                        'events':load_npz(PACK/'EVENTS.npz'),'price':price,'price_ts':ts}
    cs,atoms,rows=core.coefficient_pack(np,data,json.loads(pathlib.Path(calp['path']).read_text()))
    control=core.coefficient_control(np,data,cs,atoms,rows)
    write('COEFFICIENT_EVENT_CONTROL.json',control)
    receipt.update({'status':'PRICE_UNITS_AND_FIXED_CASH_CONTROL_PASS_NO_NETWORK','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                    'source_sha256':sha(__file__),'adapter_sha256':sha(pathlib.Path(__file__).parent/'price_units.py'),
                    'canonical_panel':{'path':source,'sha256':source_sha},'meta':mp,'pack_inputs':used,
                    'independent_equation_max_relative_error':float(relative.max()),'old_direct_value_nonpositive_known_cells':negative_as_price,
                    'coefficient_control':control,'cpu_seconds_scope':'single CPU no torch import no optimizer',
                    'wall_seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
    write('RESULT.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['status','known_cells','unknown_cells','old_direct_value_nonpositive_known_cells','independent_equation_max_relative_error','wall_seconds','peak_rss_bytes']}))

if __name__=='__main__':main()
