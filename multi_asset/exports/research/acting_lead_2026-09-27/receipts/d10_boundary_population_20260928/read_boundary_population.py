"""Read-only cash-ledger boundary and frozen book eligibility facts; no q or PnL."""
import resource
resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
import datetime, hashlib, json, os, pathlib, time
import numpy as np
START = time.monotonic()
B = 1789776000
LO = 1577836800000
PATHS = {
 'old': '/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz',
 'new': '/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz',
 'stream_d': '/workspace/axis_0919/funding/funding_ledger.npz',
 'universe': '/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz',
 'members': '/workspace/dlarch_2026-09-24/chain/d10rr_s42/receipts/P1_members_2025H2on.npz',
 'mask': '/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz',
 'features': '/workspace/dlarch_2026-09-24/chain/d10rr_s42/work/NEWS_FEATURES.npz',
}
READS = {}
def fields(key, names):
 p = pathlib.Path(PATHS[key])
 with p.open('rb') as f:
  before = os.fstat(f.fileno())
  with np.load(f, allow_pickle=False) as z: out = {n: z[n] for n in names}
  after = os.fstat(f.fileno())
 now = p.stat()
 sig = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
 assert sig(before) == sig(after) == sig(now), ('input changed', key)
 READS[key] = {'path': str(p), 'resolved': str(p.resolve()), 'file_bytes': before.st_size,
  'fields': {n: {'shape': list(a.shape), 'dtype': str(a.dtype), 'array_bytes': a.nbytes} for n,a in out.items()},
  'stat': dict(zip(['dev','inode','bytes','mtime_ns','ctime_ns'],sig(before))),
  'fd_and_path_stable': True, 'content_rehashed_this_audit': False}
 return out
O=fields('old',['symbols','off','ft','rate'])
N=fields('new',['symbols','off','ft_ms','rate'])
D=fields('stream_d',['symbols','sym','ts','ts_ms','rate'])
U=fields('universe',['symbols','ts','pit'])
M=fields('members',['symbols','crypto'])
K=fields('mask',['symbols','ts','mask'])
F=fields('features',['symbols','anchors'])
syms=O['symbols']; assert len(syms)==829 and len(set(syms))==829
for x in (N,D,U,M,K,F): assert np.array_equal(syms,x['symbols'])
assert np.array_equal(K['ts'],F['anchors'])
assert np.array_equal(D['ts'],D['ts_ms']//1000)
assert M['crypto'].dtype == bool and M['crypto'].shape==(829,)
assert K['mask'].dtype==bool and K['mask'].shape==(len(K['ts']),829)
assert U['pit'].dtype==bool and U['pit'].shape==(len(U['ts']),829)
for data,tkey in ((O,'ft'),(N,'ft_ms')):
 off=[int(x) for x in data['off']]
 assert len(off)==830 and off[0]==0 and off[-1]==len(data[tkey])==len(data['rate'])
 assert all(0<=x<=len(data[tkey]) for x in off) and all(a<=b for a,b in zip(off,off[1:]))
 assert np.isfinite(data['rate']).all()
 assert all(np.all(np.diff(data[tkey][off[j]:off[j+1]])>0) for j in range(829))
assert int(O['ft'].max())==B
use=(F['anchors']>=1672531200)&(F['anchors']<=U['ts'][-1])
au=F['anchors'][use]; ui=np.searchsorted(U['ts'],au)
assert np.array_equal(U['ts'][ui],au)
rows=[]; multis=[]
for j,s in enumerate(syms):
 ol,oh=map(int,O['off'][j:j+2]); nl,nh=map(int,N['off'][j:j+2])
 ot=O['ft'][ol:oh]; orate=O['rate'][ol:oh]
 nt=N['ft_ms'][nl:nh]; nr=N['rate'][nl:nh]
 olduse=(ot*1000>=LO)&(ot<=B); newuse=(nt>=LO)&(nt<=B*1000)
 secs,cnt=np.unique(nt[newuse]//1000,return_counts=True)
 for sec in np.setdiff1d(ot[olduse],secs):
  oi=np.flatnonzero(ot==sec); ni=np.flatnonzero((nt>=sec*1000)&(nt<=sec*1000+999)); di=np.flatnonzero((D['sym']==j)&(D['ts']==sec))
  rows.append({'symbol':str(s),'axis_index':j,'old_second':int(sec),
   'old_rates':orate[oi].tolist(), 'new_ms_full_second':nt[ni].tolist(),'new_rates_full_second':nr[ni].tolist(),
   'stream_d_ms':D['ts_ms'][di].tolist(),'stream_d_rates':D['rate'][di].tolist(),
   'at_old_upper_second':bool(sec==B), 'one_to_one_same_rate_in_full_second':bool(len(oi)==len(ni)==1 and np.array_equal(orate[oi],nr[ni])),
   'stream_d_identical_ms_rate':bool(np.array_equal(D['ts_ms'][di],nt[ni]) and np.array_equal(D['rate'][di],nr[ni])),
   'new_event_excluded_only_by_exact_ms_upper_bound':bool(len(ni)==1 and B*1000<int(nt[ni[0]])<=B*1000+999)})
 for sec in secs[cnt>1]:
  ni=np.flatnonzero((nt>=sec*1000)&(nt<=sec*1000+999)); oi=np.flatnonzero(ot==sec)
  event_anchor=(int(sec)//14400)*14400
  ai=np.searchsorted(au,event_anchor); anchor_present=bool(ai<len(au) and au[ai]==event_anchor)
  legal=U['pit'][ui,j]&K['mask'][use,j]&M['crypto'][j]
  multis.append({'symbol':str(s),'axis_index':j,'second':int(sec),'new_ms':nt[ni].tolist(),'new_rates':nr[ni].tolist(),
   'old_rates':orate[oi].tolist(),'crypto':bool(M['crypto'][j]),
   'universe_pit_true_all_rows':int(U['pit'][:,j].sum()),'member_mask_true_all_rows':int(K['mask'][:,j].sum()),
   'book_legal_true_on_all_producer_anchors':int(legal.sum()),'event_floor_4h_anchor':event_anchor,
   'event_anchor_exists_in_producer_axis':anchor_present,
   'book_legal_at_event_anchor':bool(legal[ai]) if anchor_present else None})
checks={
 'all_149_old_only_accounted':len(rows)==149,
 'all_old_only_at_terminal_second':all(r['at_old_upper_second'] for r in rows),
 'all_149_match_new_rate_and_stream_d_original_ms':all(r['one_to_one_same_rate_in_full_second'] and r['stream_d_identical_ms_rate'] for r in rows),
 'all_149_new_events_clipped_by_common_ms_upper_bound':all(r['new_event_excluded_only_by_exact_ms_upper_bound'] for r in rows),
 'all_18_multiple_second_groups_accounted':len(multis)==18,
 'all_18_excluded_by_frozen_crypto':all(not r['crypto'] for r in multis),
 'all_18_never_book_legal_on_producer_axis':all(r['book_legal_true_on_all_producer_anchors']==0 for r in multis),
}
small_sources={}
for p0 in ['/workspace/axis_0919/receipts/FUNDING_LEDGER.json','/workspace/axis_0919/devices/ax04_funding_ledger.py','/workspace/baseline_tables_2026-09-19/funding/BT_FUNDING_OVERLAP.json','/workspace/baseline_tables_2026-09-19/devices_v3/bt_funding_overlap.py','/workspace/dlarch_2026-09-24/chain/devices/news2_combo.py','/workspace/dlarch_2026-09-24/chain/devices/book_universe.py']:
 raw=pathlib.Path(p0).read_bytes(); item={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 if p0.endswith('FUNDING_LEDGER.json'):
  x=json.loads(raw);item['recorded_generation']={k:x[k] for k in ['self_sha256','window','out_npz_sha256','inputs_sha256']}; item['recorded_env']=x['env']
 elif p0.endswith('BT_FUNDING_OVERLAP.json'):
  x=json.loads(raw);item['recorded_generation']={k:x[k] for k in ['self_sha256','inputs','splice']}
 small_sources[p0]=item
out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':AUDIT_SOURCE_SHA,
 'status':'BOUNDARY_AND_ELIGIBILITY_FACTS_ONLY_NO_CASH_OR_POSITION_EVALUATION',
 'common_interval_ms_inclusive':[LO,B*1000],
 'full_terminal_second_inspected_ms_inclusive':[B*1000,B*1000+999],
 'checks':checks,'inputs':READS,'small_sources_rehashed':small_sources,
 'old_only_rows_all_149':rows,'multiple_second_groups_all_18':multis,
 'producer_anchor_interval_inclusive':[int(au[0]),int(au[-1])],'producer_anchor_count':len(au),
 'limit_bytes':512<<20,'wall_seconds':time.monotonic()-START,
 'peak_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'limitations':['No q, targets, prices, returns, simulation or exchange read. Frozen masks establish target eligibility only; actual held positions were not inspected.',
 'Large inputs were not rehashed: prior identity manifest hashes are separate evidence; this read verifies unchanged FD/path stat during selected-field access.',
 'Raw REST payload was not parsed. Original stream-D ts_ms and generation source/receipt prove the stored boundary provenance, not an independent exchange-record audit.',
 'Old integer seconds and new millisecond event-time differences are not alone a cash-impact finding.']}
print(json.dumps(out,indent=2,allow_nan=False))
assert all(checks.values()),checks
