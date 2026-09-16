"""Fixed four current-role/mode requests. A plan is never actual-input authority."""
import copy,hashlib,json
import numpy as np
FIRST=1735689600000;TERMINAL=1788220800000
BOOKS=('current_main__main','king0_benchmark__main')
MODES=('ECONOMIC_HALT','NO_ECONOMIC_HALT')
PREREG_SHA='4525f0bceb04150fdc210c8229c23a80697a6af6d0705c0c984bde9b9898507e'
def need(ok,message):
 if not ok:raise ValueError(message)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def symbols(axis):
 x=np.asarray(axis);need(x.dtype.kind=='U' and x.shape==(829,) and len(set(x.tolist()))==829 and all(x.tolist()),'complete unique source-admitted829 symbols');return x.tolist()
def make_plan(axis):
 sy=symbols(axis)
 rows=[dict(id=('halt_' if mode=='ECONOMIC_HALT' else 'nohalt_')+book.removesuffix('__main'),book=book,mode=mode,delay_s=1500,ordinary_fee_bps=3.52,settlement_fee_bps=3.52,settlement_factor=1.,step=1e-8,min_notional=5.) for mode in MODES for book in BOOKS]
 return dict(schema='CURRENT_RULE_TWO_BOOK_TWO_RISK_MODE_PLAN_1',status='SOURCE_ONLY_NOT_INPUT_ADMITTED',runnable=False,initial_capital=100000.,origin_ms=FIRST,terminal_ms=TERMINAL,anchors=3648,daily_nodes=609,symbols=sy,symbol_axis_sha256=hashlib.sha256(canonical(sy)).hexdigest(),scenarios=rows,ladder_multiplier=1.,use_pns=True,filter_status='SCENARIO_NOT_HISTORICAL_PIT',historical_filter_certified=False,readback_offset_ms=3300000,model_schema='CURRENT_RULE_KING0_F10_15BEST32_PREDICTIONS_1')
def validate_plan(plan,axis):
 need(canonical(plan)==canonical(make_plan(axis)),'exact current four-mode descriptor');return plan
def validate_row(plan,row,axis):
 validate_plan(plan,axis);need(sum(canonical(x)==canonical(row) for x in plan['scenarios'])==1,'unique fixed current scenario');return row
def filters(plan,row,axis):
 validate_row(plan,row,axis)
 return dict(schema='EXPLICIT_FILTER_SCENARIO_1',status='SCENARIO_NOT_HISTORICAL_PIT',id='ROOT_PREREG_FIXED_STEP_MIN_5.0',source_sha256=PREREG_SHA,values={s:dict(step=row['step'],min_notional=row['min_notional']) for s in symbols(axis)})
def engine_config(plan,row,axis,instruments,funding_id):
 validate_row(plan,row,axis);sy=symbols(axis);need(isinstance(funding_id,str) and bool(funding_id),'actual shared funding identity');need(isinstance(instruments,dict) and set(instruments)==set(sy),'source initial generation map')
 for x in instruments.values():need(type(x.get('active')) is bool and (isinstance(x.get('instrument_id'),str) and bool(x['instrument_id']) or x.get('instrument_id') is None and not x['active']),'source initial generation')
 return dict(schema='DYNAMIC_EXECUTOR_CASH_CONFIG_1',initial_capital=plan['initial_capital'],origin_ms=FIRST,ordinary_fee_bps=row['ordinary_fee_bps'],settlement_fee_bps=row['settlement_fee_bps'],settlement_factor=row['settlement_factor'],ladder_multiplier=plan['ladder_multiplier'],use_pns=plan['use_pns'],attempt_offset_ms=1500000,funding_coverage_id=funding_id,instruments=copy.deepcopy(instruments))
