"""Append measured recent inputs to frozen NC cash simulation; never rewrite prefix.

Prices retain each symbol's old price UNIT and append official close RETURNS.
Missing bars are explicitly UNKNOWN under the existing UA-FREEZE-EXCLUDE
policy; last-price valuation is not a claim that their return is zero.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,traceback,shutil
import numpy as np
from funding_overlap import sha
from recent_king_features import materialize,BASE
from recent_legs import certified

NS=Path('/dev/shm/news2_2026-09-23')
RAW=Path('/dev/shm/recent_inputs_overlap_20260928/RAW_AND_PRODUCTION_CHANNELS.npz')
FUND=Path('/dev/shm/recent_funding_overlap_20260928/funding_ledger_2026-09.json')
RAW_SHA='ac8bfa6f438d6e96c0bd4317d29961172d8cfe8ef76629f2fdfa474e90dc1fbe'
FUND_SHA='927cac43f071049aa0f68276b0337acf4cbad382383f07ee893264340f4fd8e3'

def extend_log_prices(last_log,close):
    last_log=np.asarray(last_log);close=np.asarray(close)
    if last_log.ndim!=1 or close.ndim!=2 or close.shape[1]!=len(last_log) or len(close)<2:raise ValueError('price shape')
    if not np.isfinite(last_log).all() or np.isinf(close).any() or np.any(np.isfinite(close)&(close<=0)):raise ValueError('price finite positivity')
    seed=np.isfinite(close[0]);seen=np.isfinite(close[1:]).any(0)
    if np.any(seen&~seed):raise ValueError('no observable boundary; no future seed')
    out=np.tile(last_log,(len(close)-1,1));unknown=~np.isfinite(close[1:]);previous=last_log.copy()
    for i in range(1,len(close)):
        good=np.isfinite(close[i])&seed
        v=previous.copy();v[good]=last_log[good]+np.log(close[i,good]/close[0,good]);out[i-1]=v;previous=v
    return out,unknown,seed

def append_funding(old_t,old_r,events,boundary,end):
    old_t=np.asarray(old_t);old_r=np.asarray(old_r)
    if old_t.ndim!=1 or old_r.shape!=old_t.shape or np.any(np.diff(old_t)<=0) or np.any(old_t>boundary) or not np.isfinite(old_r).all():raise ValueError('old funding schema')
    seen=set();new=[];shared=0
    for t,r in events:
        if type(t) is not int or not np.isfinite(r):raise ValueError('funding finite/time')
        if t in seen:raise ValueError('duplicate funding event')
        seen.add(t)
        if t<=boundary:
            i=int(np.searchsorted(old_t,t))
            if i==len(old_t) or old_t[i]!=t:raise ValueError('new historical funding event')
            if float(old_r[i])!=float(r):raise ValueError('funding conflict')
            shared+=1
        elif t<=end:new.append((t,float(r)))
    new.sort();nt=np.array([v[0] for v in new],dtype=old_t.dtype);nr=np.array([v[1] for v in new],dtype=old_r.dtype)
    return np.r_[old_t,nt],np.r_[old_r,nr],{'shared':shared,'appended':len(new)}

def concat_combo(old,new,end):
    if set(old)!=set(new) or not np.array_equal(old['symbols'],new['symbols']):raise ValueError('combo schema/axis')
    if old['E_ts'][-1]+14400!=new['E_ts'][0] or np.any(np.diff(new['E_ts'])!=14400):raise ValueError('combo time gap')
    take=new['E_ts']+14400<=end
    if not take.any():raise ValueError('no fully priced new window')
    out={'symbols':old['symbols'].copy()}
    for k in old:
        if k=='symbols':continue
        out[k]=np.concatenate([old[k],new[k][take]])
        if not np.array_equal(out[k][:len(old[k])],old[k],equal_nan=old[k].dtype.kind in 'fc'):raise ValueError('old combo mutated '+k)
    return out

def main(root):
    start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);pins={str(Path(__file__)):sha(__file__)}
    if shutil.disk_usage(root).free<8.5*1024**3:raise ValueError('insufficient disk headroom for 3GB price extension')
    cfgp=NS/'configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json';cfg=json.loads(cfgp.read_text());pins[str(cfgp)]=sha(cfgp)
    for k in ('price_full_raw','price_full_meta','ledger_full','tradability'):
        v=cfg['pins'][k];pins[v['path']]=v['sha256']
    up=cfg['runs'][0]['targets']['universe'];pins[up['path']]=up['sha256'];pins[str(RAW)]=RAW_SHA;pins[str(FUND)]=FUND_SHA
    cr=Path('/dev/shm/recent_nc_combo_20260928');wr=Path('/dev/shm/recent_rolling_inputs_20260928')
    certified(cr,pins);certified(wr,pins)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input sha '+p)
    pm=materialize(cfg['pins']['price_full_meta']['path']);oldp=np.load(cfg['pins']['price_full_raw']['path'],mmap_mode='r');raw=materialize(RAW);sy=pm['symbols'];ng,nw=oldp.shape
    if not np.array_equal(sy,raw['symbols'][:nw]) or np.any(np.diff(raw['ts'])!=300) or np.any(np.diff(pm['grid'])!=300):raise ValueError('raw grid/axis')
    b=int(pm['grid'][-1]);end=int(raw['ts'][-1]);bi=int(np.searchsorted(raw['ts'],b))
    if raw['ts'][bi]!=b:raise ValueError('price seam missing')
    recent,unknown,seed=extend_log_prices(oldp[-1],raw['close'][bi:,:nw]);newgrid=np.r_[pm['grid'],raw['ts'][bi+1:]]
    outp=root/'price_full_recent.npy';op=np.lib.format.open_memmap(outp,mode='w+',dtype=oldp.dtype,shape=(len(newgrid),nw))
    for lo in range(0,ng,8192):
        op[lo:min(lo+8192,ng)]=oldp[lo:min(lo+8192,ng)]
        if not np.array_equal(op[lo:min(lo+8192,ng)].view('u8'),oldp[lo:min(lo+8192,ng)].view('u8')):raise ValueError('price prefix bytes')
    op[ng:]=recent;op.flush();ur,uc=np.nonzero(unknown)
    scale=pm['ref_px']*np.exp(oldp[-1]-pm['cref_raw']);relative=scale[seed]/raw['close'][bi,:nw][seed]-1
    pm['grid']=newgrid;pm['unavail_grid_row']=np.r_[pm['unavail_grid_row'],ur+ng];pm['unavail_col']=np.r_[pm['unavail_col'],uc]
    np.savez_compressed(root/'price_meta_recent.npz',**pm)
    pp={'VERDICT':'PASS','meaning':'prefix-bitwise and new official RETURNS; price units remain old reconstruction; missing bars explicitly UA, not closed real cash',
        'old_rows':ng,'new_rows':len(recent),'new_unknown_cells':int(unknown.sum()),'total_unknown_cells':len(pm['unavail_col']),
        'boundary_price_scale_relative_min':float(relative.min()),'boundary_price_scale_relative_max':float(relative.max()),
        'outputs':{'raw':{'sha256':sha(outp)},'meta':{'sha256':sha(root/'price_meta_recent.npz')}}}
    (root/'PRICE_RECEIPT.json').write_text(json.dumps(pp,indent=2)+'\n');del op,oldp,recent
    ledger=materialize(cfg['pins']['ledger_full']['path']);arch=json.loads(FUND.read_text());events={str(s):[] for s in sy};outside=0
    for key,v in arch.items():
        s,t=key.rsplit('|',1);t=int(t)
        if int(v[0])!=t or float(v[0])!=t:raise ValueError('funding key/time')
        if s in events:events[s].append((t,float(v[1])))
        else:outside+=1
    if not np.array_equal(ledger['symbols'],sy):raise ValueError('funding symbol axis')
    offs=[0];fts=[];rates=[];shared=0;added=0
    for j,s in enumerate(sy):
        sl=slice(int(ledger['off'][j]),int(ledger['off'][j+1]));t,r,c=append_funding(ledger['ft'][sl],ledger['rate'][sl],events[str(s)],b,end)
        fts.append(t);rates.append(r);offs.append(offs[-1]+len(t));shared+=c['shared'];added+=c['appended']
    np.savez_compressed(root/'ledger_recent.npz',symbols=sy,off=np.array(offs,np.int64),ft=np.concatenate(fts),rate=np.concatenate(rates))
    fundrec={'shared_equal':shared,'appended':added,'outside_axis_events_excluded':outside,'old_prefix_preserved_per_symbol':True,'not_independent_venue_completeness_proof':True}
    # Use original causal W24H tradability implementation on observed rolling
    # channels; require every symbol's old terminal state before extension.
    ax=materialize(wr/'axes.npz');sys.path.insert(0,str(BASE/'devices'));import nc_hist_features as H
    H.set_tree(str(BASE/'tree'));TR=H._G['TR'];C=np.load(wr/'cache_crypto.npy',mmap_mode='r');oldtr=materialize(cfg['pins']['tradability']['path']);ca=np.r_[oldtr['anchor_ts'][-1],ax['anchors']]
    # new targets start at the old tradability axis's terminal anchor.
    ca=np.unique(ca);cls=ax['crypto_cols']
    states,truncated=TR.window_states(ax['ts'],TR.bar_states(C[:,:,4]),ca,window='W24H')
    if truncated.any():raise ValueError('truncated tradability lookback')
    # API shape/order is checked against the original fixed boundary below.
    if states.shape!=(len(ca),len(cls)):raise ValueError('tradability API shape')
    first=int(np.searchsorted(ca,oldtr['anchor_ts'][-1]));eq=np.array_equal(states[first],oldtr['state_W24H'][-1,cls])
    if not eq:raise ValueError('tradability boundary changed')
    mask=ca>oldtr['anchor_ts'][-1];newstates=np.zeros((int(mask.sum()),nw),oldtr['state_W24H'].dtype)
    # For non-crypto names no new ingestion: explicitly NODATA, never inherit
    # a stale TRADABLE state. They are excluded from the book universe too.
    newstates[:]=TR.NODATA
    newstates[:,cls]=states[mask]
    np.savez_compressed(root/'tradability_recent.npz',symbols=sy,anchor_ts=np.r_[oldtr['anchor_ts'],ca[mask]],state_W24H=np.concatenate([oldtr['state_W24H'],newstates]))
    universe=materialize(up['path']);elig=materialize(cr/'ELIGIBILITY.npz');ua=elig['E_ts'][1:];pin=elig['fixed_september_universe']
    if universe['ts'][-1]+14400!=ua[0] or not np.array_equal(universe['pit'][-1],pin):raise ValueError('universe seam')
    # Only PIT is consumed by the runner; do not fabricate other unconsumed fields.
    np.savez_compressed(root/'universe_recent.npz',symbols=sy,ts=np.r_[universe['ts'],ua],pit=np.concatenate([universe['pit'],np.tile(pin,(len(ua),1))]))
    combos={}
    for sd in (42,2027):
        oldroot=NS/f'work/combo_s{sd}';rec=json.loads((oldroot/'TARGET_RECEIPT.json').read_text());dest=root/f'combo_s{sd}';dest.mkdir();pols={}
        for pol in ('literal','scaled_diagnostic'):
            src=oldroot/(pol+'.npz');pins[str(src)]=rec['policies'][pol]['sha']
            if sha(src)!=pins[str(src)]:raise ValueError('old combo source')
            d=concat_combo(materialize(src),materialize(cr/f'NC_s{sd}_{pol}.npz'),end);p=dest/(pol+'.npz');np.savez_compressed(p,**d);pols[pol]={'sha':sha(p)}
        (dest/'TARGET_RECEIPT.json').write_text(json.dumps({'policies':pols,'state_init':rec['state_init'],'hold_contract':rec['hold_contract'],'source_recent':sha(cr/'RESULT.json'),'scope':'prefix preserved; same conditional NC state, not actual live interventions'},indent=2)+'\n');combos[str(sd)]=str(dest)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input changed '+p)
    outputs={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
    result={'status':'RECENT_CASH_INPUTS_READY_NOT_PNL','utc':time.strftime('%FT%TZ',time.gmtime()),'inputs':pins,'outputs':outputs,'price':pp,'funding':fundrec,'tradability_boundary_exact':eq,'end_price':end,'last_priced_anchor':end-14400,'combos':combos,'seconds':time.monotonic()-start,'limits':['Legacy price unit retained per symbol; recent absolute exchange closes differ by documented scale','UA-FREEZE-EXCLUDE remains conditional not complete cash certification','Existing execution mirror and pooled calibration unchanged, not current live tree certification','NC state continued without September live manual reseed/dual-executor event']}
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print({k:result[k] for k in ('status','funding','last_priced_anchor','seconds')},flush=True)

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True);(root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2));raise
