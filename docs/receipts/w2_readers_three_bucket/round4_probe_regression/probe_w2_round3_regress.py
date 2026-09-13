#!/usr/bin/env python3
"""Pure AST numeric readers; old fixtures, actual frozen positive anchor, and distinct fault models."""
import ast,copy,io,contextlib,json,math,random,types
import audit_common as C

def main():
    cb,pm,ds,sf,e6=C.cost_readers()
    fill=dict(anchor_ts=1.,symbol='AAA',order_type='maker',side='buy',filled_notional=100.,avg_fill_px=100.01,mid_at_anchor=100.,fee_paid=.02)
    fixtures={
        'normal':[fill],
        'no_side':[dict(fill,side=None)],
        'mixed_missing_side':[fill,dict(fill,side=None,avg_fill_px=101.)],
        'fee_nan':[dict(fill,fee_paid=float('nan'))],
        'unconverted_foreign_fee':[dict(fill,fee_paid=0.,fee_all_usdt=False)],
        'converted_foreign_fee':[dict(fill,fee_paid=.02,fee_all_usdt=False,fee_conversion={'asset':'BNB','amount':.00001,'usdt_value':.02})],
        'known_zero_fee':[dict(fill,fee_paid=0.)],
        'unknown_fill':[dict(fill,filled_notional=None)],
        'zero_fill':[dict(fill,filled_notional=0.)],
        'valid_sell':[dict(fill,side='sell',filled_notional=-100.)],
        'contradictory_sign':[dict(fill,side='sell')],
    }
    outcomes={k:e6(v) for k,v in fixtures.items()}
    assert outcomes['mixed_missing_side']['verdict']=='FAIL' and outcomes['mixed_missing_side']['cost_bps_displayed']==52.5 and outcomes['mixed_missing_side']['c_bps_overall']==3.
    assert outcomes['no_side']['verdict']=='FAIL' and outcomes['no_side']['c_bps_overall'] is None
    assert outcomes['normal']['verdict']==outcomes['converted_foreign_fee']['verdict']==outcomes['known_zero_fee']['verdict']==outcomes['valid_sell']['verdict']=='PASS'
    assert outcomes['fee_nan']['verdict']==outcomes['unconverted_foreign_fee']['verdict']==outcomes['unknown_fill']['verdict']==outcomes['contradictory_sign']['verdict']=='FAIL'
    assert outcomes['zero_fill']['verdict']=='UNDETERMINED'
    # The exact E6 scalar comparisons at either side of declared tolerances.
    tolerance={str(delta):sf['_agree'](1.,1.+delta,sf['E6_CARRIER_BPS_TOL_BPS']) for delta in [.00049,.00051]}
    assert tolerance=={'0.00049':True,'0.00051':False}
    mass_tolerance={str(delta):sf['_agree'](100.,100.+delta,.01,1e-9) for delta in [.0099,.0101]}
    assert mass_tolerance=={'0.0099':True,'0.0101':False}
    # Same counts and same notional mass cannot certify row IDs. This deliberately substitutes
    # m1's return with a calculation over OTHER members. It is not the production same-input call.
    other=[dict(fill,symbol='OTHER_MEMBER')]
    wrong_members=e6([fill],m1_override=pm['m1_effective_cost'](other,{1.:'calm'}))
    assert wrong_members['verdict']=='PASS'
    wrong_members_record={'fault_model':'m1 carrier replaced by output from a different member set, same numerical rows; not reachable through current same-input m1 call without another fault','buckets_member_ids':['AAA'],'mock_m1_member_ids':['OTHER_MEMBER'],'result':wrong_members}
    # Same total count/mass but a swap ACROSS regimes does get caught by the per-regime gate.
    reg_rows=[fill,dict(fill,anchor_ts=2.,symbol='BBB',filled_notional=200.)]
    regimes={1.:'calm',2.:'stress'}
    swap=[dict(fill,filled_notional=200.),dict(fill,anchor_ts=2.,symbol='BBB',filled_notional=100.)]
    wrong_reg=e6(reg_rows,regimes,m1_override=pm['m1_effective_cost'](swap,regimes))
    assert wrong_reg['carrier_consistency']['population']['same_count'] and wrong_reg['carrier_consistency']['population']['same_notional']
    assert wrong_reg['verdict']=='FAIL' and not wrong_reg['carrier_consistency']['population']['by_regime_all_same']
    # Compensating sign disagreement has the SAME member support. Aggregate cost agrees, each
    # regime's signed cost does not: the actual code validates regime counts/mass, not regime bps.
    sign_rows=[dict(fill,side='sell',avg_fill_px=101.),dict(fill,anchor_ts=2.,symbol='BBB',side='sell',avg_fill_px=99.)]
    sign_offset=e6(sign_rows,regimes)
    pm_reg=pm['m1_effective_cost'](sign_rows,regimes)['by_regime']
    cb_reg={reg:cb['bucket_fills']([r]) for reg,r in zip(['calm','stress'],sign_rows)}
    assert sign_offset['verdict']=='PASS' and pm_reg['calm']['c_bps_net']!=cb_reg['calm']['bps_measured']
    # A zero-filled-only regime is included by the bucket grouping but has no m1 accumulator.
    zero_reg=e6([fill,dict(fill,anchor_ts=2.,symbol='NO_FILL',filled_notional=0.)],regimes)
    assert zero_reg['measurement_complete'] and zero_reg['verdict']=='FAIL'
    # Actual code proof aid: instrument only the accumulator's row ID, without changing its
    # filtering or arithmetic, and compare it with bucket members under complete=True.
    tree=ast.parse((C.W2/'live/pilot_metrics.py').read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='m1_effective_cost')
    loop=next(n for n in f.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='o')
    spot=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='r' for t in n.targets))
    loop.body.insert(spot,ast.parse('_audit_members.append(o["_audit_id"])').body[0]);ast.fix_missing_locations(f)
    ns=dict(pm,_audit_members=[]);exec(compile(ast.Module(body=[f],type_ignores=[]),'m1-membership-instrument-only','exec'),ns)
    rng=random.Random(310913);support={'generated_populations':1200,'complete_populations':0,'equal_count_complete_populations':0,'membership_violations':[]}
    for trial in range(1200):
        rows=[]
        # Clean populations deliberately frequent; other populations challenge support filtering.
        for j in range(rng.randint(1,8)):
            row=dict(fill,_audit_id=j,symbol=str(j),anchor_ts=float(j%2+1))
            if trial%3:
                row.update(side=rng.choice(['buy','sell','LONG','SHORT',None]),filled_notional=rng.choice([-100.,0.,100.,None]),avg_fill_px=rng.choice([99.,100.,101.,None]),fee_paid=rng.choice([0.,.02,None]))
            rows.append(row)
        ns['_audit_members'].clear();mr=ns['m1_effective_cost'](rows,regimes);bk=cb['bucket_fills'](rows)
        if bk['measurement_complete'] is True:
            support['complete_populations']+=1
            bm={r['_audit_id'] for r in cb['partition'](rows)[0]};mm=set(ns['_audit_members'])
            assert mm.issubset(bm),'unexpected non-subset support from frozen m1'
            if mr['n_filled_orders']==bk['n_fills']:
                support['equal_count_complete_populations']+=1
                assert mm==bm,'same-input complete population membership mismatch'
    # Read the actual frozen copied anchor, not author output JSON or author tests.
    orders=[json.loads(l) for l in (C.W2/'state/live/pilot_log/20260912/orders.jsonl').read_text().splitlines() if l]
    anchors=[json.loads(l) for l in (C.W2/'state/live/pilot_log/20260912/anchors.jsonl').read_text().splitlines() if l]
    real_rows=[r for r in orders if r.get('rebalance_id')=='A1789201439'];actual=e6(real_rows,{a['anchor_ts']:a['regime_at_anchor'] for a in anchors})
    assert actual['verdict']=='PASS' and actual['buckets']['n_fills']==185
    assert actual['buckets']['notional_usdt']==11883.468 and actual['carrier_consistency']['population']['m1_filled_notional_total']==11883.47
    frozen_incident=[json.loads(l) for l in (C.OUT_SRC/'private/prior/private/incident_orders.jsonl').read_text().splitlines() if l]
    flat=[r for r in frozen_incident if any(str(r.get(k,'')).startswith('F20260912124738-') for k in ['client_order_id','client_id'])]
    assert len(flat)==255 and all(r.get('fee_paid') is None for r in flat)
    flat_e6=e6(flat)
    assert flat_e6['verdict']=='UNDETERMINED' and flat_e6['protective_flatten_fee_known_by_buckets']==0 and flat_e6['protective_flatten_buckets']['n_unpriced']==255
    incident={'source':'own frozen prior incident orders; prefix F20260912124738-*','n_rows':255,'gross':sum(abs(r['filled_notional']) for r in flat),'fee_paid_null':sum(r.get('fee_paid') is None for r in flat),'fee_flags_absent':{k:sum(k not in r for r in flat) for k in ['fee_all_usdt','fee_conversion','fee_source']},'e6':flat_e6}
    # First-anchor full-population call sites + _leg body only; no surrounding main.
    fat=ast.parse((C.W2/'ops/first_anchor_review.py').read_text());leg=next(n for n in ast.walk(fat) if isinstance(n,ast.FunctionDef) and n.name=='_leg')
    calls=sorted([n for n in ast.walk(fat) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='_leg'],key=lambda n:n.lineno)[:3]
    mod=types.SimpleNamespace(**cb);fans={'CB':mod,'mine':[fill,dict(fill,filled_notional=None)]}
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):exec(compile(ast.Module(body=[leg,*calls],type_ignores=[]),'first-anchor-pure-actual-calls','exec'),fans)
    first_anchor=capture.getvalue();assert 'measurement complete: NO' in first_anchor and 'UNKNOWN fill amount' in first_anchor and 'measurement complete: yes' not in first_anchor
    base=dict(day='20260912',wallet_balance=100.,unrealised_pnl=0.,nav=100.,external_flow_usdt=1000.,realised_pnl=0.,realised_by_type_asset={},realised_truncated=False)
    nav_cases={
        'prior_1000_both':[base,dict(base)],
        'same_day_transfer_20':[base,dict(base,external_flow_usdt=1020.,nav=120.,wallet_balance=120.)],
        'cross_midnight':[base,dict(base,day='20260913',external_flow_usdt=20.,nav=120.,wallet_balance=120.)],
        'flow_nan':[base,dict(base,external_flow_usdt=float('nan'))],
        'flow_none':[base,dict(base,external_flow_usdt=None)],
        'income_truncated':[base,dict(base,realised_truncated=True)],
        'equity_nan':[base,dict(base,nav=float('nan'))],
        'equity_none':[base,dict(base,nav=None)],
        'start_equity_none':[dict(base,nav=None),base],
        'valid_zero_start_deposit':[dict(base,nav=0.,wallet_balance=0.,external_flow_usdt=0.),dict(base,nav=100.,wallet_balance=100.,external_flow_usdt=100.)],
    }
    nav={k:ds['account_facts'](v) for k,v in nav_cases.items()}
    nav_versions={'current':nav}
    for version,path in [('base_918559f',C.LIVE/'ops/daily_summary.py'),('prior_0158f5d1',C.OUT_SRC/'private/prior/private/inputs/w2/ops/daily_summary.py')]:
        tree=ast.parse(path.read_text());present={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
        names=present & {'_finite','realised_facts','anchor_cost_facts','account_facts','render_account'}
        oldds=C.extracted(path,names,constants=True)
        nav_versions[version]={k:oldds['account_facts'](v) for k,v in nav_cases.items()}
    assert nav['prior_1000_both']['unexplained_equity_change']==0. and nav['same_day_transfer_20']['unexplained_equity_change']==0.
    for name in ['cross_midnight','flow_nan','flow_none','income_truncated']:assert nav[name]['unexplained_equity_change'] is None
    assert nav['equity_nan']['unexplained_computable'] and math.isnan(nav['equity_nan']['unexplained_equity_change'])
    assert nav['valid_zero_start_deposit']['unexplained_computable'] and nav['valid_zero_start_deposit']['unexplained_equity_change']==-100.
    rendered_nav={k:ds['render_account'](nav[k]) for k in ['equity_nan','equity_none','start_equity_none','valid_zero_start_deposit']}
    # An interval crossing midnight can be partitioned into same-day pieces if actual boundary
    # snapshots exist. We do not invent those rows in the product; this is a composability control.
    a0=dict(base,external_flow_usdt=1000.);a1=dict(base,external_flow_usdt=1010.,nav=110.,wallet_balance=110.)
    b0=dict(base,day='20260913',external_flow_usdt=0.,nav=110.,wallet_balance=110.);b1=dict(b0,external_flow_usdt=20.,nav=130.,wallet_balance=130.)
    parts=[ds['account_facts']([a0,a1]),ds['account_facts']([b0,b1])]
    assert sum(p['external_flow_interval_usdt'] for p in parts)==30 and all(p['unexplained_equity_change']==0 for p in parts)
    C.write('w2_receipt.json',{'old_fixtures_current_results':outcomes,'tolerance_boundary':{'bps':tolerance,'notional':mass_tolerance},'different_members_mocked_carrier':wrong_members_record,'different_regime_masses_mocked_carrier':wrong_reg,'actual_sign_cancellation':{'e6':sign_offset,'m1_per_regime':pm_reg,'bucket_per_regime':cb_reg},'zero_fill_only_extra_regime':zero_reg,'same_input_membership_checks':support,'real_positive_anchor':{'rebalance_id':'A1789201439','total_order_rows':len(real_rows),'e6':actual},'actual_incident_255':incident,'first_anchor_stdout':first_anchor,'nav_fixtures':nav_cases,'nav_results':nav,'nav_version_comparison':nav_versions,'nav_rendered':rendered_nav,'midnight_partition_positive':parts})
    print(json.dumps(C.clean({'old_cases':{k:(v['verdict'],v['cost_bps_displayed']) for k,v in outcomes.items()},'real':{k:actual['buckets'][k] for k in ['n_fills','notional_usdt']},'real_verdict':actual['verdict'],'wrong_members_mock_verdict':wrong_members['verdict'],'per_regime_mass_swap':wrong_reg['verdict'],'signed_compensation_verdict':sign_offset['verdict'],'zero_extra_regime':zero_reg['verdict'],'support':support,'nav_residuals':{k:v['unexplained_equity_change'] for k,v in nav.items()}}),indent=2))

if __name__=='__main__':main()
