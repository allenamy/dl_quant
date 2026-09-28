import json,hashlib,subprocess,sys,time,math
from pathlib import Path
from datetime import datetime,timezone
R=Path('/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research')
sys.path.insert(0,str(R/'multi_asset/exports/research/common'))
from venue_quiet_window import quiet_window_status
A=1790625600
assert 3600<=time.time()%14400<13200
q=quiet_window_status();assert q['open'] and not q['override'] and not q['stale_start'] and not q['anchor_in_progress']
L=Path.home()/'dl_quant_live';W=Path.home()/'wide_shadow';sources={}
def read(k,p):
 b=p.read_bytes();sources[k]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(k,p):return json.loads(read(k,p))
def git(*args):return subprocess.check_output(['git','-C',str(L),*args]).decode().strip()
t=js('target',W/f'state/target_live/{A}.json');pa=js('parity',W/f'state/snap/{A}/PARITY.json')
cb=read('config',L/'config/book.json');c=json.loads(cb)
e=js('watchdog',L/'state/live/watchdog/last_eval.json');s=js('state',L/'state/live/watchdog/state.json')
ar=[json.loads(l) for l in read('anchors',L/'state/live/pilot_log/20260928/anchors.jsonl').splitlines() if l.strip()]
ar=[r for r in ar if A<=r['anchor_ts']<A+14400];assert len(ar)==1
a=ar[0];eb=a['external_book'];lines=read('runlog',L/'state/anchor_runs.log').decode().splitlines()
starts=[l for l in lines if l[20:33]==' anchor start'];done=[l for l in lines if l[20:32]==' anchor done'];ds=done[-1]
kh=hashlib.sha256(read('king',W/'shadow_bundle/slow2026.txt')).hexdigest();fh=hashlib.sha256(read('f10',W/'fea171/f10_live_s42_np.npz')).hexdigest()
head=git('rev-parse','HEAD');cfghead=subprocess.check_output(['git','-C',str(L),'show','HEAD:config/book.json'])
print(json.dumps({'parity_fields':list(pa),'parity_verdict':pa.get('verdict'),'parity_status':pa.get('status')}))
checks={'done_rc0':ds>starts[-1] and 'rc=0' in ds and ds.startswith('2026-09-28T20:'),
'king_pin':kh==c['external_book']['booster_sha_pin']==eb['booster_sha']=='700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d',
'f10_pin':fh==c['external_book']['f10_sha_pin']==eb['f10_sha']=='3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f',
'consumed_target_sha':eb['json_sha']==sources['target']['sha256'], 'external_ok':eb['ok'] is True and eb['nominal_ts']==A,
'producer_parity':pa.get('verdict')=='PARITY', 'not_halted':a['opening_halted'] is False,
'no_trip':s['_mode']=='LIVE' and s['reduce_only'] is False and s['tripped_at'] is None and e['tripped'] is False,
'current_watchdog':A<=datetime.fromisoformat(e['evaluated_utc'].replace('Z','+00:00')).timestamp()<A+14400,
'existing_partial_only':set(e['conditions_partial'])=={'cond2_day_loss','cond4_drawdown'} and not any(e[k] for k in ('triggers','metric_errors','conditions_blind','conditions_unevaluated','conditions_degraded')),
'config_equals_head':cb==cfghead,'expected_head':head=='d01e35db56b4d7ed6abf0befd9f18452cd06c329',
'code_unmodified':not git('diff','HEAD','--','live','scheduler','ops','config')}
out={'utc':datetime.now(timezone.utc).isoformat(),'scope':'local_posttrade_existing_records_no_venue_check_not_full_acceptance','nominal_anchor':A,'execution_anchor':a['anchor_ts'],'rid':a['rebalance_id'],'head':head,'checks':checks,'done':ds,'gross_completion_ratio':a['realized_gross']/a['target_gross'],'watchdog_utc':e['evaluated_utc'],'watchdog_partial':e['conditions_partial'],'sources':sources,'quiet':q,'venue_k1_repeated':False,'device_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out['status']='LOCAL_FINISHED_WITH_EXISTING_PARTIAL' if all(checks.values()) else 'REVIEW_REQUIRED'
p=R/'multi_asset/exports/research/acting_lead_2026-09-27/receipts/ROOT_20Z_LOCAL_POSTTRADE_20260928.json'
with p.open('x') as f:json.dump(out,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(out,indent=2));sys.exit(0 if all(checks.values()) else 2)
