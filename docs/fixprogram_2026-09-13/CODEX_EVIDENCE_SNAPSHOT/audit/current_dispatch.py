"""Original-price E55/E60 wiring for two current books and two risk modes.

Independent accounting only; no execution Engine import or monetary overrides.
"""
from pathlib import Path
import hashlib, importlib.util
import numpy as np

HERE = Path(__file__).resolve().parent
SCENARIOS = {
    'nohalt_current_main': ('current_main__main', 'NO_ECONOMIC_HALT'),
}
READER_SHA = 'a193df4890abd0724f36dd768fb78d810dfbac1392bc42fdc88ecaa3abe69c33'
READER_LOCK_SHA = '26904b4515d0d6cf0d60325fbb994152c08f9373a73def7688f49e1e849615ba'
RISK_READER_SHA = '727608f7cc1950dc6706b6cc03248c230048595663b227dd0930ccebec7c0925'
RISK_READER_LOCK_SHA = '2a8a8ba72f09c9a54a6c49c3ea5a1f74d84a2bb64cc7f794dda71105adb775e8'
RISK_MARKET_SHA = '1b45e1e8e5e711379eade0c6ff709a05d3a9296948decc54e4f530dfa0d9ac48'
PRIORITY = {'DAY':0, 'FUNDING':1, 'CLOSE':2, 'OPEN':3, 'NAV_SNAPSHOT':4,
            'PLAN':5, 'ATTEMPT':6, 'READBACK':7, 'RISK_ATTEMPT':8}

def need(ok, message):
    if not ok: raise ValueError(message)

def scenario_identity(sid):
    need(sid in SCENARIOS, 'only current-main mark valuation path')
    return SCENARIOS[sid]

def load_accountant(mode):
    need(mode in ('ECONOMIC_HALT', 'NO_ECONOMIC_HALT'), 'explicit risk mode')
    exact = HERE.parent/'dynamic_cash_reconciliation_exact_quantity_20260915'
    risk = HERE.parent/'current_risk_cash_reconciliation_20260915'
    paths = [(exact/'exact_reconciliation.py', READER_SHA), (exact/'SOURCE_LOCK.json', READER_LOCK_SHA)]
    if mode == 'ECONOMIC_HALT':
        paths += [(risk/'risk_reconciliation.py', RISK_READER_SHA), (risk/'SOURCE_LOCK.json', RISK_READER_LOCK_SHA)]
    for p,h in paths:
        need(hashlib.sha256(p.read_bytes()).hexdigest() == h, 'fixed approved independent reader '+str(p))
    p = risk/'risk_reconciliation.py' if mode == 'ECONOMIC_HALT' else exact/'exact_reconciliation.py'
    spec = importlib.util.spec_from_file_location('_current_cash_accountant_'+mode, p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cls = m.IndependentRiskCashAudit if mode == 'ECONOMIC_HALT' else m.IndependentExactCashAudit
    return m, cls

def expected_clocks(anchors, funding_ms, life_events, mode):
    need(mode in ('ECONOMIC_HALT', 'NO_ECONOMIC_HALT'), 'explicit risk mode')
    need(anchors.dtype == np.int64 and anchors.ndim == 1 and len(anchors)>1
         and np.all(np.diff(anchors)==14400), 'exact continuous int64 4h anchors')
    expected = [('DAY',int(t)*1000,None) for t in anchors[::6]]
    offsets = [('NAV_SNAPSHOT',1200000),('PLAN',1440000),('ATTEMPT',1500000),('READBACK',3300000)]
    if mode == 'ECONOMIC_HALT': offsets += [('RISK_ATTEMPT',3600000)]
    for t in anchors[:-1]:
        expected.extend((kind,int(t)*1000+off,None) for kind,off in offsets)
    expected.extend(('FUNDING',int(t),None) for t in np.unique(funding_ms))
    expected.extend((e['type'],e['ts_ms'],e['id']) for e in life_events)
    expected.sort(key=lambda e:(e[1],PRIORITY[e[0]]))
    return expected

def prices(values, symbols):
    return {str(s):float(v) if np.isfinite(v) and v>0 else None for s,v in zip(symbols,values)}

class OriginalRiskFacts:
    """One immutable NPZ load, exact index lookup, original activity and rules."""
    def __init__(self, arrays, anchors, symbols, calendar):
        expected = {'anchor_ts','symbols'}
        for off in (3300,3600):
            expected.update('{}_{}'.format(k,off) for k in ('observation_ts','price','quote_volume','trade_count'))
        need(set(arrays)==expected, 'exact raw risk artifact fields')
        need(arrays['anchor_ts'].dtype==np.int64 and arrays['anchor_ts'].shape==anchors.shape
             and np.array_equal(arrays['anchor_ts'],anchors), 'raw risk original anchor identity')
        need(arrays['symbols'].dtype==symbols.dtype and arrays['symbols'].shape==symbols.shape
             and arrays['symbols'].tobytes()==symbols.tobytes(), 'raw risk exact symbol identity')
        need(anchors.ndim==1 and np.all(np.diff(anchors)==14400), 'continuous raw risk anchors')
        for off in (3300,3600):
            ts = arrays['observation_ts_'+str(off)]
            need(ts.dtype==np.int64 and ts.shape==anchors.shape and np.array_equal(ts,anchors+off), 'exact E55/E60 original clock')
            for k in ('price','quote_volume','trade_count'):
                a = arrays[k+'_'+str(off)]
                need(a.dtype==np.float64 and a.shape==(len(anchors),len(symbols)), 'raw risk numeric axis '+k)
        self.a,self.anchors,self.symbols,self.calendar = arrays,anchors,symbols,calendar

    def index(self, ts_ms, off):
        need(type(ts_ms)is int and off in (3300,3600) and ts_ms%1000==0, 'exact risk millisecond clock')
        anchor = ts_ms//1000-off; i = int(np.searchsorted(self.anchors,anchor))
        need(i<len(self.anchors) and int(self.anchors[i])==anchor
             and int(self.a['observation_ts_'+str(off)][i])*1000==ts_ms, 'risk clock absent; no nearest/clip')
        return i

    def prices(self, ts_ms):
        return prices(self.a['price_3300'][self.index(ts_ms,3300)],self.symbols)

    def observations(self, ts_ms):
        i = self.index(ts_ms,3600); result = {}
        for j,s in enumerate(self.symbols):
            p,v,c = (self.a[k+'_3600'][i,j] for k in ('price','quote_volume','trade_count'))
            observed = np.isfinite(p) and np.isfinite(v) and np.isfinite(c) and p>0 and v>=0 and c>=0
            status = 'MISSING' if not observed else ('ACTIVE' if v>0 and c>0 else 'ZERO_ACTIVITY')
            broad = any(ts_ms>=z['announced_at_ms'] and z['effective_ms']<=ts_ms<z['end_ms']
                        for z in self.calendar['symbols'].get(str(s),{}).get('new_order_restrictions',[]))
            result[str(s)] = dict(price=float(p) if np.isfinite(p) else None,
                quote_volume=float(v) if np.isfinite(v) else None, trade_count=float(c) if np.isfinite(c) else None,
                status=status, observed_ms=ts_ms, submission_allowed=not broad)
        return result

def dispatch_readback(audit, row, original_prices, mode):
    need(mode in ('ECONOMIC_HALT','NO_ECONOMIC_HALT'), 'explicit risk mode')
    need(audit.pending is not None and type(row.get('ts_ms'))is int
         and row['ts_ms']==audit.pending['anchor_ms']+3300000, 'exact current E55 readback')
    if mode=='ECONOMIC_HALT':
        audit.readback(row,original_prices)
    else:
        need('economic_risk' not in row and 'nav_observation' not in row, 'no-halt must not borrow risk state')
        for s in audit.positions:
            if audit._q(s):
                p=original_prices.get(s)
                need(p is not None and np.isfinite(p) and p>0, 'no-halt held E55 original mark')
        audit.cash_only(row)
    # This is independently derived equity. Only the halt log records a NAV
    # against which risk_reconciliation.readback compares it.
    return float(audit.book.value(original_prices)['equity'])
