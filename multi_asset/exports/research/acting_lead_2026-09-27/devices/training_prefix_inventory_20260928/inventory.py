"""Read-only sparse-metadata admission census; never loads feature matrices or GPU."""
import pathlib,os,json,hashlib,time,sys,ast,collections,resource,signal,zipfile
ROOT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding')
OUT=ROOT/'training_prefix_inventory_20260928'
CFG=ROOT/'first120_canonical_20260927/RUN_CONFIG.json'
FOLD=pathlib.Path('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/runs/d10/G1_T0_nomask/f10_s42/202608')
OBS=pathlib.Path('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/vendor_news2_20260923/devices/f10_observability.py')
PINS={str(CFG):'3a482d58c3adbc3f42ddf92c05539594ab078f6a7f5c589babc9060830b4fb63',str(FOLD/'ADMISSION.json'):'e67c02d7339da5bbf545ac13f73a9484dfe16309e546bc3191b780daff03c19b',str(FOLD/'FOLD_RECEIPT.json'):'11ca8e7d0711ad7e7a581828dc6e9d5b4869ac9030363a38a80016ccebb6a087',str(OBS):'c6399d7ae49482503209ce21916e38f1ad36fb7702c980eb5d0b67c5b9349dd1'}
def dump(p,d):
    with open(p,'x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def run():
    start=time.monotonic();signal.alarm(295)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    # No large mmap permitted in this metadata-only worker.
    resource.setrlimit(resource.RLIMIT_AS,(2*2**30,2*2**30))
    import numpy as np
    from inventory_contract import exact_axis,window_contract
    verified={};stats={}
    def check(path,h):
        p=pathlib.Path(path);b=p.stat();got=sha(p);a=p.stat()
        if (b.st_ino,b.st_size,b.st_mtime_ns)!=(a.st_ino,a.st_size,a.st_mtime_ns) or got!=h:raise ValueError('input identity drift:'+str(p))
        verified[str(p)]=h;stats[str(p)]={'inode':a.st_ino,'bytes':a.st_size,'mtime_ns':a.st_mtime_ns}
    for p,h in PINS.items():check(p,h)
    cfg=json.loads(CFG.read_text());rec=json.loads((FOLD/'FOLD_RECEIPT.json').read_text());ad=json.loads((FOLD/'ADMISSION.json').read_text())
    for p,h in rec['sources'].items():check(p,h)
    oldf=rec['argv']['features'];oldleg=rec['argv']['legs'];target=next(p for p in rec['inputs'] if p.endswith('/dlw_targets.npz'))
    for p in (oldf,oldleg,target):check(p,rec['inputs'][p])
    current={k:cfg['input_pins'][k] for k in ('features','legs','king_oof','f10_oof','combo_receipt')}
    for pin in current.values():check(pin['path'],pin['sha256'])
    def load(path,names):
        with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in names}
    names=('anchors','symbols','count','off','m')
    old=load(oldf,names);new=load(current['features']['path'],names)
    for key in ('anchors','symbols'):exact_axis(old[key],new[key])
    a=old['anchors'];symbols=old['symbols'];n=len(a);w=len(symbols)
    labels=load(target,('E_ts','symbols','y4s'));exact_axis(symbols,labels['symbols'])
    if not np.all(np.diff(labels['E_ts'])==14400):raise ValueError('raw label axis')
    y=np.full((n,w),np.nan,np.float32);ix=np.searchsorted(labels['E_ts'],a);ok=(ix<len(labels['E_ts']))&(labels['E_ts'][np.minimum(ix,len(labels['E_ts'])-1)]==a);y[ok]=labels['y4s'][ix[ok]]
    oleg=load(oldleg,('E_ts','symbols','ready'));nleg=load(current['legs']['path'],('E_ts','symbols','ready'))
    for z in (oleg,nleg):exact_axis(a,z['E_ts']);exact_axis(symbols,z['symbols'])
    def members(F):
        if len(F['off'])!=n+1 or F['off'][0]!=0 or F['off'][-1]!=len(F['m']) or not np.array_equal(np.diff(F['off']),F['count']):raise ValueError('offset/member population')
        ms=[F['m'][F['off'][i]:F['off'][i+1]].astype(np.int64) for i in range(n)]
        if any(np.any(m<0) or np.any(m>=w) or len(np.unique(m))!=len(m) for m in ms):raise ValueError('member identity')
        return ms
    om=members(old);nm=members(new)
    ns={'np':np};nodes=[x for x in ast.parse(OBS.read_bytes()).body if isinstance(x,ast.FunctionDef) and x.name=='span_admissible']
    if len(nodes)!=1:raise ValueError('original observer missing')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(OBS),'exec'),ns);admit=ns['span_admissible']
    tr=np.flatnonzero((a+14400<=ad['cutoff'])&oleg['ready']&(old['count']>=50));tr1=tr[:int(len(tr)*.85)]
    if len(tr1)!=ad['train_anchors'] or int(a[tr1[-1]])+14400!=ad['max_train_label_end']:raise ValueError('original train split does not reproduce')
    accepted=[];reject=[]
    for s in range(int(tr1[0])+24,int(tr1[-1])-96,48):
        span=np.arange(s-24,s+96);good,why=admit(om,y,span,oleg['ready'])
        row={'start_index':int(span[0]),'end_index':int(span[-1]),'first_anchor':int(a[span[0]]),'last_anchor':int(a[span[-1]]),'reason':why}
        if good:accepted.append(row)
        else:reject.append(row)
    count=dict(collections.Counter(x['reason']['reason'] for x in reject))
    if len(accepted)!=ad['accepted_windows'] or count!=ad['rejected']:raise ValueError('original 149/6 admission does not reproduce')
    preds={k:load(current[k]['path'],('P','E_ts','symbols')) for k in ('king_oof','f10_oof')}
    for z in preds.values():exact_axis(a,z['E_ts']);exact_axis(symbols,z['symbols'])
    origin=1672531200;rows=[]
    for row in accepted:
        s,e=row['start_index'],row['end_index'];idx=np.arange(s,e+1);item=window_contract(a,s,e,ad['max_train_label_end'],origin)
        good,why=admit(nm,y,idx,nleg['ready'])
        item.update(original=row,current_label_contract=bool(good),current_label_reason=why,
                    changed_member_anchors=[int(i) for i in idx if not np.array_equal(om[i],nm[i])],
                    changed_ready_anchors=[int(i) for i in idx if oleg['ready'][i]!=nleg['ready'][i]],
                    min_members=int(new['count'][idx].min()),max_members=int(new['count'][idx].max()),feature_rows=int(new['off'][e+1]-new['off'][s]),
                    feature_x171_bytes=int(new['off'][e+1]-new['off'][s])*171*4,
                    known_current_burn_start_index=s,objective_start_index=s+24,
                    prefix_anchors_from_common_origin=max(0,int(np.searchsorted(a,a[s])-np.searchsorted(a,origin))),
                    exact_event_price_contract='NOT_MEASURED',prefix_producer_state='NOT_BUILT',prefix_execution_inventory='NOT_BUILT')
        item['scores']={key:{'member_nonfinite_pairs':sum(int((~np.isfinite(z['P'][i,nm[i]])).sum()) for i in idx),'anchors_all_members_finite':sum(bool(np.isfinite(z['P'][i,nm[i]]).all()) for i in idx)} for key,z in preds.items()}
        rows.append(item)
    receipt=json.loads(pathlib.Path(current['combo_receipt']['path']).read_text());policy={}
    for k,v in receipt['policies'].items():
        p=pathlib.Path(v['path']);policy[k]={'path':str(p),'declared_sha256':v['sha'],'exists_at_recorded_path':p.is_file(),'status':'AVAILABLE_UNVERIFIED' if p.is_file() else 'UNAVAILABLE_AT_RECORDED_PATH_NOT_GLOBALLY_ABSENT'}
    headers={}
    for path in (oldf,current['features']['path']):
        with zipfile.ZipFile(path) as z:
            hd={}
            for key in ('X78','X82','X89'):
                with z.open(key+'.npy') as f:
                    ver=np.lib.format.read_magic(f)
                    if ver==(1,0):shape,order,dtype=np.lib.format.read_array_header_1_0(f)
                    elif ver==(2,0):shape,order,dtype=np.lib.format.read_array_header_2_0(f)
                    else:raise ValueError('NPY version')
                    hd[key]={'shape':list(shape),'dtype':str(dtype),'fortran_order':order,'body_read':False}
            headers[path]=hd
    summaries={}
    for row in rows:
        year=time.strftime('%Y',time.gmtime(row['first_anchor']));d=summaries.setdefault(year,{'windows':0,'common_origin_supported':0,'current_label_valid':0,'changed_member_windows':0})
        d['windows']+=1;d['common_origin_supported']+=row['prefix_status']=='NOT_BUILT';d['current_label_valid']+=row['current_label_contract'];d['changed_member_windows']+=bool(row['changed_member_anchors'])
    # Post-read stat identity protects input use through the whole measurement.
    for path,b in stats.items():
        st=pathlib.Path(path).stat()
        if (st.st_ino,st.st_size,st.st_mtime_ns)!=(b['inode'],b['bytes'],b['mtime_ns']):raise ValueError('input changed during inventory:'+path)
    result={'status':'INPUT_INVENTORY_COMPLETE_NOT_TRAINING_READY','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'original_admission':ad,'reproduced_accepted':len(rows),'reproduced_rejected':reject,'rows':rows,'by_start_year':summaries,'common_origin':origin,'current_label_support_windows':sum(x['current_label_contract'] for x in rows),'common_origin_supported_windows':sum(x['prefix_status']=='NOT_BUILT' for x in rows),'combination_artifacts':policy,'headers':headers,'all_used_input_pins_verified':verified,'input_stat_identity':stats,'features_body_loaded':False,'gpu_imported':False,'optimizer_updates':0,'max_training_span_x171_bytes':max(x['feature_x171_bytes'] for x in rows),'elapsed_seconds':time.monotonic()-start,'rss_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'actual_python':sys.executable,'numpy':np.__version__}
    dump(OUT/'RESULT.json',result)
    print(json.dumps({k:result[k] for k in ('status','reproduced_accepted','by_start_year','current_label_support_windows','common_origin_supported_windows','max_training_span_x171_bytes','elapsed_seconds','rss_peak_bytes')}),flush=True)
if __name__=='__main__':run()
