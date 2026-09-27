"""Rebuild only the frozen supported 120-anchor D10 complete-book target slice."""
import os
for n in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[n]='1'
import argparse, contextlib, hashlib, importlib.util, json, pathlib, resource, subprocess, sys, time
G=2**30
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(2*G,2*G));resource.setrlimit(resource.RLIMIT_CPU,(240,250))
ROOT=pathlib.Path(__file__).resolve().parent; T0=time.monotonic()


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
    free=int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())-int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
    urss=sum(int(x) for x in subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True).split())*1024
    gate={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'free_bytes':free,'same_uid_rss_bytes':urss,'pass':free>=10*G and urss+2*G<=30*G,'cpu':1,'rss_limit_bytes':2*G,'shared_spare_bytes':8*G}
    dump(out/'RESOURCE_GATE.json',gate)
    if not gate['pass']:raise SystemExit('RESOURCE_REFUSED')
    p=out/'quota_probe.bin'
    with p.open('wb') as f:f.write(b'\0'*65536);f.flush();os.fsync(f.fileno())
    assert p.stat().st_size==65536;p.unlink()
    import numpy as np
    ip=ROOT/'IDENTITY_MANIFEST.json';assert sha(ip)=='9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78'
    identity=json.loads(ip.read_text());assets=identity['assets'];checked={}
    def pin(k):
        e=assets[k];p=pathlib.Path(e['path']);assert p.is_file() and sha(p)==e['sha256'],k
        checked[k]={'path':str(p),'sha256':e['sha256']};return p
    def npz(k,keys):
        p=pin(k)
        with np.load(p,allow_pickle=False) as z:return {q:z[q] for q in keys}
    support_path=ROOT/'first120_supported_20260927/RESULT.json'
    support=json.loads(support_path.read_text())['supported_revision']
    assert support['status']=='SUPPORT_PASS_CASH_UNVALIDATED' and support['first_A']==1672531200 and support['terminal_B']==1674259200
    assert support['producer_prefix_anchors']==0
    a=np.array(support['anchors'],np.int64);rows=np.array(support['rows'],np.int64)
    F=npz('features',('anchors','symbols','off','m'));syms=F['symbols'];assert np.array_equal(F['anchors'][rows],a)
    members=[F['m'][F['off'][i]:F['off'][i+1]].astype(np.int64) for i in rows]
    L=npz('legs',('E_ts','symbols','KZ','ZFD','WL','RN8','QV','ready'))
    S=npz('f10_oof',('E_ts','symbols','P'))
    for z in (L,S):assert np.array_equal(z['E_ts'],F['anchors']) and np.array_equal(z['symbols'],syms)
    for k in ('king_oof','legs_receipt','f10_receipt','combo_receipt','combo_source_news2_combo.py','combo_source_continuous_combo.py','combo_source_combo_target.py','combo_source_book_universe.py','combo_source_combo_stage.py'):pin(k)
    mk=npz('combo_input_member_mask_tradable_AND_live_W24H_cachegrid.npz',('ts','mask'))
    assert np.array_equal(mk['ts'],F['anchors'])
    crypto=npz('combo_input_P1_members_2025H2on.npz',('crypto',))['crypto']
    u=npz('target_universe',('ts','symbols','pit'))
    sys.path.insert(0,str(assets['combo_source_continuous_combo.py']['path'].rsplit('/',1)[0]))
    import continuous_combo as CC,combo_target as CT,book_universe as BU
    assert sha(CC.__file__)==assets['combo_source_continuous_combo.py']['sha256']
    assert sha(CT.__file__)==assets['combo_source_combo_target.py']['sha256']
    assert sha(CT.ROOT/'vendor_live/fea171/combo_stage.py')==assets['combo_source_combo_stage.py']['sha256']
    legal=BU.align(a,syms,u)&mk['mask'][rows]&crypto[None,:]
    cfg=json.loads(pin('combo_input_bundle_config.json').read_text())
    combo_receipt={'status':'FIRST120_D10_COMPLETE_BOOK_TARGETS_NOT_EXECUTION_PNL','seed':42,'state_init':'zero at 2023-01-01; exact original producer origin; prefix length0',
                   'hold_contract':'trade_mask False = hold contracts, no King substitution','policies':{},'inputs':checked,'source_sha256':sha(__file__),
                   'support_receipt_sha256':sha(support_path),'scope':'frozen120 only; no new model or candidate'}
    for policy in ('literal','scaled_diagnostic'):
        r=CC.evolve(a,L['KZ'][rows].astype(np.float64),S['P'][rows].astype(np.float64),L['ZFD'][rows].astype(np.float64),L['WL'][rows].astype(np.float64),L['RN8'][rows].astype(np.float64),members,L['QV'][rows].astype(np.float64),legal,L['ready'][rows],cfg['params'],policy)
        p=out/(policy+'.npz');np.savez_compressed(p,E_ts=a,symbols=syms,**r)
        combo_receipt['policies'][policy]={'path':str(p),'sha':sha(p),'published':int(r['trade_mask'].sum())}
    dump(out/'TARGET_RECEIPT.json',combo_receipt)
    ep=pin('engine_ovn_adapter.py');pin('engine_bt_objb_targets.py');sys.path.insert(0,str(ep.parent))
    import ovn_adapter as OV,bt_objb_targets as OT
    assert sha(OV.__file__)==assets['engine_ovn_adapter.py']['sha256'] and sha(OT.__file__)==assets['engine_bt_objb_targets.py']['sha256']
    arm='ACTING_D10_FIRST120_CLOCK_s42'
    spec={'arm':arm,'data':'D10 bound inputs; frozen120 complete King/F10/fund producer; original models rescored, not retrained',
          'scaled':{'npz':str(out/'scaled_diagnostic.npz'),'sha256':sha(out/'scaled_diagnostic.npz')},
          'lit':{'npz':str(out/'literal.npz'),'sha256':sha(out/'literal.npz')},
          'new_receipt':{'path':str(out/'TARGET_RECEIPT.json'),'sha256':sha(out/'TARGET_RECEIPT.json')},
          'price_meta':{'path':str(pin('price_full_meta')),'sha256':assets['price_full_meta']['sha256']},
          'universe':{'path':str(pin('target_universe')),'sha256':assets['target_universe']['sha256']},'window_first_anchor':'2023-01-01T00:00:00Z'}
    dump(out/'ADAPTER_SPEC.json',spec)
    arr,info,data=OV.build(spec);tn=out/'TARGETS.npz';tr=out/'TARGETS.json'
    OV.write(arr,info,spec,str(tn),str(tr),sha(OV.__file__))
    rt=OV.verify_roundtrip(str(tn),str(tr),arm,data,int(a[0]),OT)
    rec=json.loads(tr.read_text());rec['roundtrip']=rt;rec['roundtrip_loader_sha256']=sha(OT.__file__);dump(tr,rec)
    base=json.loads(pin('actual_config').read_text())
    contract={'schema':'d10-first-120-contract/1','identity_manifest_sha256':sha(ip),'anchors':a.tolist(),'end_ms':int(a[-1]+14400)*1000,
              'cash_interval':'(start,end]','feature_known_offset_ms':999,'decision_offset_ms':1440000,'funding_before_same_time_fill':True,
              'funding':{'path':assets['ms_ledger']['path'],'sha256':assets['ms_ledger']['sha256'],'field':'ft_ms','dtype':'<i8','unit':'millisecond','clock':'economic_settlement','coalesce_seconds':False},
              'consumer':{'kind':'exact_ms_active_view','path':str(ROOT/'funding_exact_ms_consumer.py'),'sha256':sha(ROOT/'funding_exact_ms_consumer.py')},
              'targets':{'path':str(tn),'sha256':sha(tn),'new_independent':True}}
    dump(out/'INPUT_CONTRACT.json',contract)
    cp=ROOT/'d10_first_span_identity.py';assert sha(cp)=='5f1ba04e22ac45ae4b7c632a9df1ae11f8f55b164c59ba33e7bc0fc62800c104'
    ms=importlib.util.spec_from_file_location('identity_checker',cp);check=importlib.util.module_from_spec(ms);ms.loader.exec_module(check)
    events,irec=check.check_and_load(contract,ip,sha(ip));dump(out/'INPUT_RECEIPT.json',irec)
    newconfig={'schema':'acting-d10-first120-canonical-cash/1','status':'INPUT_TARGET_PASS_CASH_UNVALIDATED','base_config':checked['actual_config'],'identity_manifest_sha256':sha(ip),
               'anchors':a.tolist(),'terminal_B':int(a[-1]+14400),'seed_execution':0,'seed_model':42,'reading':'scaled',
               'arm':arm,'nav0_usdt':base['nav0_usdt'],'current_production_config':base['current_production_config'],
               'policy':'UA-FREEZE-EXCLUDE','ua_set':'UNAVAILABLE_3084','events':'rule','price':'raw','paths':base['paths'],
               'targets':{'npz':str(tn),'npz_sha256':sha(tn),'receipt':str(tr),'receipt_sha256':sha(tr)},
               'cash_contract':{'path':str(out/'INPUT_CONTRACT.json'),'sha256':sha(out/'INPUT_CONTRACT.json')},
               'checker_sha256':sha(cp),'adapter_roundtrip':rt,'inherited_pins':base['pins'],'input_pins':checked,
               'legacy_ledger_is_reference_only':True,'cash_source':'INPUT_CONTRACT exact-ms checker events; never base ledger_full',
               'limitations':['fixed-window cash instrument; not candidate/OOS evidence','source producer state starts Jan1; simulation inventory starts cash', 'NC/D10RR reference is preserved, no frozen pins changed']}
    dump(out/'RUN_CONFIG.json',newconfig)
    result={'status':'FIRST120_D10_TARGET_AND_INPUT_PASS_CASH_UNVALIDATED','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_sha256':sha(__file__),
            'config_sha256':sha(out/'RUN_CONFIG.json'),'target_sha256':sha(tn),'input_receipt_sha256':sha(out/'INPUT_RECEIPT.json'),'roundtrip':rt,
            'elapsed_seconds':time.monotonic()-T0,'rss_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'output_bytes':sum(p.stat().st_size for p in out.iterdir() if p.is_file())}
    assert result['output_bytes']<64<<20;dump(out/'BUILD_RESULT.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
