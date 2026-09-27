"""Pure retained-tape verification; never imports or runs a simulator."""
import argparse,bisect,collections,copy,hashlib,json,math,pathlib,time


def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def reconcile_record(expected,observed):
    """Same acceptance function used for original rows and deliberate mutations."""
    ms,s,q,p,r,cash=expected
    t,os,oq,op,orr,ocash=observed
    if (round(t*1000),os)!=(ms,s) or t!=ms/1000:raise ValueError('event identity differs')
    if oq!=q:raise ValueError('quantity differs independently of funding rate')
    if op!=p or orr!=r:raise ValueError('price/rate identity differs')
    if abs(ocash-cash)>1e-8:raise ValueError('cash amount differs')


def verify(tape,result):
    state=tape['initial_state']
    canonical=json.dumps(state,sort_keys=True,separators=(',',':'),default=repr).encode()
    if hashlib.sha256(canonical).hexdigest()!=result['initial_state_sha256'] or state!=result['initial_state']:
        raise ValueError('initial sealed state identity differs')
    if state['n_positions']!=len(state['positions_qty']):raise ValueError('initial quantity count differs')
    q=dict(state['positions_qty']);trades=tape['trade_log'];j=0
    if any(a[0]>b[0] for a,b in zip(trades,trades[1:])):raise ValueError('trade order differs')
    ref={}
    for row in tape['fund_log']:
        key=(round(row[0]*1000),row[1])
        if key in ref:raise ValueError('duplicate logged funding')
        ref[key]=row
    A=result['first_A'];B=result['terminal_B'];n=(B-A)//14400
    expected_windows=[0.]*n;logged_windows=[0.]*n;maxq=maxcash=0.;worst_example=None
    for row in tape['independent_ms_cash_rows']:
        ms,s,stored_q,p,r,stored_cash=row;t=ms/1000
        if not A*1000<ms<=B*1000:raise ValueError('cash interval differs')
        while j<len(trades) and trades[j][0]<t:
            v=trades[j];old=q.get(v[1],0.);new=old+v[2]
            if abs(new)<1e-9*max(1.,abs(old)):new=0.
            if new:q[v[1]]=new
            else:q.pop(v[1],None)
            j+=1
        qty=q.get(s,0.)
        if stored_q!=qty:raise ValueError('stored independent quantity differs from reconstructed quantity')
        if qty and (p is None or not math.isfinite(p) or p<=0):raise ValueError('unpriced quantity')
        cash=0. if qty==0 else -qty*p*r
        if abs(cash-stored_cash)>1e-8:raise ValueError('stored independent cash differs')
        k=(ms-A*1000-1)//14400000;expected_windows[k]+=cash
        observed=ref.pop((ms,s),None)
        if observed is None:
            if cash!=0. or qty!=0.:raise ValueError('held funding event missing')
        else:
            reconcile_record((ms,s,qty,p,r,cash),observed)
            maxq=max(maxq,abs(qty-observed[2]));maxcash=max(maxcash,abs(cash-observed[5]));logged_windows[k]+=observed[5]
            if worst_example is None:worst_example=((ms,s,qty,p,r,cash),observed)
    if ref:raise ValueError('unmatched logged funding')
    err=max(abs(a-b) for a,b in zip(expected_windows,logged_windows))
    if err>1e-8:raise ValueError('window cash differs')
    return {'status':'SEALED_INITIAL_Q_EVENT_Q_AND_CASH_PASS','initial_quantities':state['positions_qty'],
            'logged_events':len(tape['fund_log']),'all_events':len(tape['independent_ms_cash_rows']),
            'quantity_gate':'exact binary64 equality after ordered fills and documented near-zero cleanup',
            'max_event_quantity_error':maxq,'max_event_cash_error_usd':maxcash,'max_window_cash_error_usd':err,
            'window_cash_usd':expected_windows},worst_example


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tape',required=True);ap.add_argument('--result',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    out=pathlib.Path(args.out)
    if out.exists():raise ValueError('refuse result overwrite')
    tape=json.loads(pathlib.Path(args.tape).read_text());result=json.loads(pathlib.Path(args.result).read_text())
    passed,example=verify(tape,result);reds={}
    bad=copy.deepcopy(tape);bad['fund_log'][0][-1]+=.01
    try:verify(bad,result)
    except ValueError as e:reds['actual_logged_cash_plus_001']=str(e)
    else:raise AssertionError('one-cent mutation accepted')
    bad=copy.deepcopy(tape);bad['fund_log'][0][2]+=1.
    try:verify(bad,result)
    except ValueError as e:reds['actual_logged_quantity_plus_one']=str(e)
    else:raise AssertionError('quantity mutation accepted')
    expected,observed=example;ez=list(expected);oz=list(observed);ez[4]=0.;ez[5]=0.;oz[4]=0.;oz[5]=0.;oz[2]+=1.
    try:reconcile_record(ez,oz)
    except ValueError as e:reds['zero_rate_cannot_mask_quantity_difference']=str(e)
    else:raise AssertionError('zero-rate quantity mutation accepted')
    bad=copy.deepcopy(tape);bad['initial_state']['positions_qty']['_INJECTED_']=1.
    try:verify(bad,result)
    except ValueError as e:reds['initial_quantity_mutation']=str(e)
    else:raise AssertionError('initial-state mutation accepted')
    passed.update(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=sha(__file__),tape_sha256=sha(args.tape),original_result_sha256=sha(args.result),
                  mutations_rejected=reds,original_result_unchanged=True,simulator_rerun=False,
                  interpretation='cash interface only; original 9/120 publish and111 HOLD; no strategy representativeness or return claim',
                  correction='Original plus_one_cent_control_red was only arithmetic and is not acceptance evidence; this replaces that control claim, not the original file.')
    out.write_text(json.dumps(passed,indent=2,allow_nan=False)+'\n');print(json.dumps({k:passed[k] for k in ('status','max_event_quantity_error','max_event_cash_error_usd','max_window_cash_error_usd','mutations_rejected')},indent=2))


if __name__=='__main__':main()
