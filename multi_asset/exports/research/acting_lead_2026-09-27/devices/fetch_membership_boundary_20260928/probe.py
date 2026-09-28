"""Fixed eight-anchor input diagnostic; no live imports, network, PnL, or training."""
import ast, hashlib, importlib.util, io, json, sys, time, types, zipfile
from pathlib import Path
import numpy as np

ANCHORS=np.arange(1790236800,1790337600+1,14400,dtype=np.int64)
BASE=Path('/Users/haosiyu/.codex/tmp/live_replay_layers_20260928')
FEA_SHA='0a8f4bb1f9a01d5c6ecd7047e4f63a72fe627809186dbb176b9d202ff36b6855'
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def load_npz(b):
    with np.load(io.BytesIO(b),allow_pickle=False) as z:return {k:z[k] for k in z.files}
def read_npz(p):return load_npz(Path(p).read_bytes())
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def member_block(text):
    start=text.index('    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]')
    end=text.index('    st.record_members(anchor, m)',start)
    return text[start:end]
def compile_block(src,nc,tr):
    ns={'np':np,'NC':nc,'TR':tr}
    code='def screen(st, anchor, P, CDf):\n    ai=len(st.cts)-1\n'+member_block(src)+'\n    return dict(m=m,covr=covr,v7=v7,qvm=qvm,legal=legal_now,ok=ok)\n'
    exec(compile(code,'pinned_member_block','exec'),ns);return ns['screen']
def checked_fetch(names,sy):
    if len(names)!=len(set(names)) or any(s not in sy for s in names):raise ValueError('unknown_or_duplicate_fetch')
    return np.array([s in set(names) for s in sy],bool)
def run_screen(ts,cd,rr,crypto,fetch,anchor,params,fn):
    ts=np.asarray(ts);n=cd.shape[1]
    if ts.ndim!=1 or len(ts)!=len(cd) or rr.shape!=cd.shape[:2] or len(ts)<2016:raise ValueError('invalid_axes')
    if not np.isfinite(ts).all() or np.any(ts!=np.floor(ts)) or np.any(np.diff(ts)!=300):raise ValueError('invalid_time_grid')
    if anchor not in ts:raise ValueError('missing_exact_anchor')
    take=(ts<=anchor);ts=ts[take];cd=cd[take];rr=rr[take]
    ts=ts[-2016:];cd=cd[-2016:];rr=rr[-2016:]
    if len(ts)!=2016 or np.shape(crypto)!=(n,) or np.shape(fetch)!=(n,):raise ValueError('invalid_screen_population')
    st=types.SimpleNamespace(cts=ts,cd=cd,crypto=crypto,fetch_mask=fetch)
    CDf=cd.astype(np.float32);CDf[:,:,0]=rr
    return fn(st,int(anchor),params,CDf)
def summary(x):return {k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in x.items()}
def save_json(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def actual(out):
    start=time.monotonic();out=Path(out);out.mkdir(exist_ok=False);(out/'sources').mkdir()
    ws=Path('/Users/haosiyu/wide_shadow');inputs={}
    for rel in ('shadow_loop_v3.py','fea171/nc_contract.py','fea171/tradability.py','shadow_bundle/crypto_axis.json'):
        b=(ws/rel).read_bytes();dest=out/'sources'/Path(rel).name;dest.write_bytes(b);inputs[str(ws/rel)]={'sha256':sha(b),'copy':str(dest)}
    nc=module(out/'sources/nc_contract.py','boundary_nc');tr=module(out/'sources/tradability.py','boundary_tr')
    src=(out/'sources/shadow_loop_v3.py').read_text();fn=compile_block(src,nc,tr)
    parent=json.loads((BASE/'result/RESULT.json').read_text());archive=BASE/'result/PRODUCTION_INPUTS.zip';b=archive.read_bytes()
    if sha(b)!=parent['archive_sha256']:raise ValueError('frozen_archive_mismatch')
    z=zipfile.ZipFile(io.BytesIO(b));cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];cr=json.loads((out/'sources/crypto_axis.json').read_text())
    if cr['symbols']!=sy:raise ValueError('crypto_axis')
    crypto=np.array(cr['crypto'],bool);stg=sy.index('STGUSDT');rows=[]
    for a0 in ANCHORS:
        if time.monotonic()-start>120:raise TimeoutError('actual_120s_budget')
        a=int(a0);prefix=f'state/snap/{a}/';aux=json.loads(z.read(prefix+'aux.json'))
        man={l.split()[1]:l.split()[0] for l in z.read(prefix+'SHA256SUMS').decode().splitlines()}
        if sha(z.read(prefix+'aux.json'))!=man['aux.json'] or aux['last_anchor']!=a:raise ValueError('aux_identity')
        ss={}
        for name in ('rolling.npz','boundary_raw.npz'):
            p=ws/prefix/name;b=p.read_bytes()
            if sha(b)!=man[name]:raise ValueError('snapshot_sha:'+str(p))
            ss[name]=load_npz(b);inputs[str(p)]={'sha256':sha(b),'bytes':len(b)}
        ts=ss['rolling.npz']['ts'];cd=ss['rolling.npz']['data'];bd=ss['boundary_raw.npz']
        if int(ts[-1])!=a:raise ValueError('snapshot_endpoint')
        ts=ts[-2016:];cd=cd[-2016:];rr=nc.rr_from_ch0(ts,cd[:,:,0],bd['ts'],bd['col'],bd['raw'])
        fetch=checked_fetch(aux['fetch_syms'],sy);res=run_screen(ts,cd,rr,crypto,fetch,a,cfg['params'],fn)
        exact=np.array_equal(res['m'],np.asarray(aux['prev_rec']['members']))
        if not exact:raise ValueError('actual_member_control:'+str(a))
        valid=np.isfinite(cd[:,stg,3]);last=int(ts[valid][-1]) if valid.any() else None
        slim=out/f'ACTUAL_{a}.npz';np.savez_compressed(slim,ts=ts,cd=cd,rr=rr,crypto=crypto,fetch=fetch,**res)
        row={'anchor':a,'utc':time.strftime('%FT%TZ',time.gmtime(a)),'original_member_control':exact,'members':res['m'].tolist(),
             'fetch_names':aux['fetch_syms'],'stg':{'fetched':bool(fetch[stg]),'legal':bool(res['legal'][stg]),'last_qv_bar_in_7d':last,'prev_close_ts':aux['prev_close_ts'].get('STGUSDT')},
             'artifact':{'path':slim.name,'sha256':sha(slim.read_bytes())}}
        rows.append(row)
    cfgout=out/'config.json';cfgout.write_bytes(z.read('shadow_bundle/config.json'))
    result={'scope':'eight_anchor_members_only','utc':time.strftime('%FT%TZ',time.gmtime()),'python':sys.executable,'numpy':np.__version__,
            'source_sha256':sha(Path(__file__).read_bytes()),'inputs':inputs,'frozen_parent_sha256':sha((BASE/'result/RESULT.json').read_bytes()),'frozen_archive_sha256':parent['archive_sha256'],
            'config_sha256':sha(cfgout.read_bytes()),'member_block_sha256':sha(member_block(src).encode()),'rows':rows,'seconds':time.monotonic()-start}
    save_json(out/'ACTUAL.json',result);print(json.dumps({'rows':len(rows),'all_exact':True,'seconds':result['seconds']}))

def research(root):
    start=time.monotonic();root=Path(root);rec=json.loads((root/'ACTUAL.json').read_text());cfg=json.loads((root/'config.json').read_text());sy=cfg['symbols_panel'];N=len(sy)
    if sha((root/'config.json').read_bytes())!=rec['config_sha256']:raise ValueError('config_sha')
    fixed=Path('/dev/shm/nc_2026-09-23');patch=json.loads((fixed/'tree/PATCH_RECEIPT.json').read_text())
    frozen=(fixed/'tree/shadow_loop_v3.py').read_bytes()
    if sha(frozen)!=patch['outputs']['shadow_loop_v3.py']:raise ValueError('frozen_source')
    current=(root/'sources/shadow_loop_v3.py').read_text()
    if member_block(current)!=member_block(frozen.decode()):raise ValueError('member_source_diff')
    for name in ('nc_contract.py','tradability.py'):
        if (root/'sources'/name).read_bytes()!=(fixed/'tree/fea171'/name).read_bytes():raise ValueError('pure_helper_diff:'+name)
    nc=module(root/'sources/nc_contract.py','boundary_nc');tr=module(root/'sources/tradability.py','boundary_tr');fn=compile_block(current,nc,tr)
    wr=Path('/dev/shm/recent_rolling_inputs_20260928');wrrec=json.loads((wr/'RESULT.json').read_text());pins={}
    for name in ('axes.npz','cache_crypto.npy','R_crypto.npy'):
        h=file_sha(wr/name)
        if h!=wrrec['outputs'][name]['sha256']:raise ValueError('research_sha:'+name)
        pins[str(wr/name)]=h
    ax=read_npz(wr/'axes.npz');C=np.load(wr/'cache_crypto.npy',mmap_mode='r');R=np.load(wr/'R_crypto.npy',mmap_mode='r')
    if list(ax['symbols'])!=sy:raise ValueError('research_axis')
    cols=ax['crypto_cols'];crypto=np.zeros(N,bool);crypto[cols]=True
    feap=Path('/dev/shm/recent_king_features_20260928/KING_FEATURES_AND_MEMBERS.npz');b=feap.read_bytes()
    if sha(b)!=FEA_SHA:raise ValueError('fixed_member_sha')
    fea=load_npz(b);rows=[]
    for row in rec['rows']:
        if time.monotonic()-start>300:raise TimeoutError('research_300s_budget')
        a=row['anchor'];p=root/row['artifact']['path'];b=p.read_bytes()
        if sha(b)!=row['artifact']['sha256']:raise ValueError('actual_slim_sha')
        actual=load_npz(b);ia=int(np.searchsorted(ax['ts'],a));ts=ax['ts'][ia-2015:ia+1]
        cd=np.full((2016,N,7),np.nan,np.float16);cd[:,cols]=C[ia-2015:ia+1]
        rr=np.full((2016,N),np.nan,np.float32);rr[:,cols]=R[ia-2015:ia+1]
        original=run_screen(ts,cd,rr,crypto,crypto,a,cfg['params'],fn)
        i=int(np.where(fea['anchors']==a)[0][0]);expected=fea['m'][fea['off'][i]:fea['off'][i+1]]
        if not np.array_equal(original['m'],expected):raise ValueError('original_research_control:'+str(a))
        fetched=run_screen(ts,cd,rr,crypto,actual['fetch'],a,cfg['params'],fn)
        if not np.array_equal(actual['crypto'],crypto):raise ValueError('crypto_mismatch')
        stg=sy.index('STGUSDT');v=np.isfinite(cd[:,stg,3]);qdiff=(cd[:,:,3]!=actual['cd'][:,:,3])&~(np.isnan(cd[:,:,3])&np.isnan(actual['cd'][:,:,3]))
        absent_before=[sy[j] for j in np.setdiff1d(original['m'],actual['m'])];absent_after=[sy[j] for j in np.setdiff1d(fetched['m'],actual['m'])]
        rows.append({'anchor':a,'utc':row['utc'],'original_research_control':True,'actual_control':row['original_member_control'],
                     'research_only_before':absent_before,'live_only_before':[sy[j] for j in np.setdiff1d(actual['m'],original['m'])],
                     'research_only_after':absent_after,'live_only_after':[sy[j] for j in np.setdiff1d(actual['m'],fetched['m'])],
                     'ordered_members_equal_after':bool(np.array_equal(actual['m'],fetched['m'])),
                     'all_qv_cells_differ':int(qdiff.sum()),'member_qvm_max_abs_delta':float(np.max(np.abs(fetched['qvm'][actual['m']]-actual['qvm'][actual['m']]))),
                     'stg_actual':row['stg'],'stg_research':{'legal':bool(original['legal'][stg]),'last_qv_bar_in_7d':int(ts[v][-1]) if v.any() else None}})
    result={'scope':'FETCH_ONLY_MEMBER_DIAGNOSTIC_NOT_FEATURE_OR_PNL_PARITY','utc':time.strftime('%FT%TZ',time.gmtime()),'rows':rows,'inputs':pins,'actual_sha256':sha((root/'ACTUAL.json').read_bytes()),
            'source_sha256':sha(Path(__file__).read_bytes()),'member_block_byte_identical':True,'python':sys.executable,'numpy':np.__version__,'seconds':time.monotonic()-start,
            'limits':['Actual as-of fetch is known only for these archived anchors','No historical venue-status reconstruction','No cash or portfolio gain claim','Full features and F10 history not rerun']}
    save_json(root/'RESULT.json',result);print(json.dumps({'scope':result['scope'],'rows':len(rows),'exact_after':sum(x['ordered_members_equal_after'] for x in rows),'seconds':result['seconds']}))

if __name__=='__main__':globals()[sys.argv[1]](sys.argv[2])
