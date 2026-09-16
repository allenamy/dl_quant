"""Independent original-response valuation reader; never supplies fill facts."""
import hashlib,json,math
from decimal import Decimal
from pathlib import Path

R=Path('/workspace/codex_research/QNT-2026-0907/causal_fullchain_20260914')
SOURCE=R/'integration/aergo_public_price_probe_20260915'
SYMBOL='AERGOUSDT';GENERATION='AERGOUSDT#2025-04-16-Aergo'
FIRST=1784851200000;CLOSE=1784874600000
TARGETS={('NAV_SNAPSHOT',1784852400000):'0.02210142',('READBACK',1784854500000):'0.02273000',('NAV_SNAPSHOT',1784866800000):'0.02297000',('READBACK',1784868900000):'0.02275592'}
SOURCE_HASHES={'markPriceKlines.body':'d991d6c786fcf5c569437864470f4aa50c0fbdfa3f942c9f6b8dac8a0864fcc0','markPriceKlines.json':'eed8243e170fa31ffdaad77020be081766b1a2fadcf79dd1b2bb22cd6062cc77','RESULT.json':'9b3125b5a012e96f29fbfea421751326586f3125e6cf50ab2781b80aab17780a','klines.body':'882fbec4a8b18dbba2b41cf9b2c93512b35d0a28c3a4961892d2419946857b9b','klines.json':'d87c791e3024b7c784bdcda7b306e740292d9d50ad9f7e318bdf4ebe85473638'}
ORIGINAL_EVENT_SHA='a5563c827fc20b94a5fe54beb67a5fe6b2db253b74d5ddae506c23cfcdc7bb2d'
PREFIX=R/'integration/current_rule_e60_cash_audit_20260915/formal1/nohalt_current_main/audit1/DAILY_AGGREGATES.json'
PREFIX_SHA='f8a8200aea5637cbeb087c0c2b42da57ac8c2af2a56836fc4bb66f8e8ec94876'

def need(ok,message):
    if not ok:raise ValueError(message)

class MarkFacts:
    def __init__(self,blobs):
        need(set(blobs)==set(SOURCE_HASHES),'full original public evidence population')
        for n,h in SOURCE_HASHES.items():need(hashlib.sha256(blobs[n]).hexdigest()==h,'fixed original source bytes '+n)
        rec=json.loads(blobs['markPriceKlines.json']);result=json.loads(blobs['RESULT.json']);rows=json.loads(blobs['markPriceKlines.body'])
        url='https://fapi.binance.com/fapi/v1/markPriceKlines?symbol=AERGOUSDT&interval=5m&startTime=1784851200000&endTime=1784874599999&limit=100'
        need(rec['url']==url and rec['method']=='GET' and rec['authenticated']is False and type(rec['status'])is int and rec['status']==200,'fixed original unauthenticated public request')
        need(rec['body_sha256']==SOURCE_HASHES['markPriceKlines.body'] and rec['body_bytes']==len(blobs['markPriceKlines.body']) and result['requests'][1]==rec and result['start_ms']==FIRST and result['end_ms']==CLOSE-1,'original receipt/body/window binding')
        need(isinstance(rows,list) and len(rows)==78,'complete original pre-CLOSE grid')
        self.values={};self.seen=set()
        for i,row in enumerate(rows):
            need(isinstance(row,list) and len(row)==12 and type(row[0])is int and type(row[6])is int and row[0]==FIRST+i*300000 and row[6]==row[0]+299999,'exact original five-minute open/close grid')
            need(isinstance(row[4],str),'original decimal close')
            p=Decimal(row[4]);need(p.is_finite() and p>0 and math.isfinite(float(p)),'positive finite original mark close')
        for (kind,t),want in TARGETS.items():
            i=(t-FIRST)//300000-1;row=rows[i]
            need(row[6]+1==t and row[4]==want and t<CLOSE,'exact four source rows, closed-bar clock and values')
            self.values[(kind,t)]=float(row[4])

    def binding(self):
        return dict(schema='EXACT_PUBLIC_MARK_VALUATION_SUPPLEMENT_1',symbol=SYMBOL,instrument_id=GENERATION,raw_source_pins={str(SOURCE/n):h for n,h in SOURCE_HASHES.items()},scope='CURRENT_SNAPSHOT_MARK_ONLY_NOT_ORDINARY_TRADE_OR_HISTORICAL_FEED_CERTIFICATION',source_rows=78,normalization='RAW_CLOSE_MS_PLUS_1_CLOSED_BAR_CLOCK',targets=[dict(type=k,ts_ms=t,source_row_index=(t-FIRST)//300000-1,mark_close=p) for (k,t),p in TARGETS.items()],ordinary_execution_observations_changed=False,settlement_assumptions_changed=False)

    def validate_stream(self,binding,stream,path_result):
        need(binding==self.binding() and stream['valuation_source']==binding,'actual valuation binding equals independently read source')
        need(stream['schema']=='FOUR_MARK_EVENT_STREAM_DIFFERENCE_1' and type(stream['changed_events'])is int and stream['changed_events']==4 and stream['all_other_event_bytes_unchanged']is True,'exact four valuation changes only')
        need(stream['original_event_sha256']==ORIGINAL_EVENT_SHA and stream['upgraded_event_sha256']==path_result['input_event_sha256'],'original complete event stream and actual upgraded identity')

    def prices(self,kind,t,original,positions):
        need(kind in ('DAY','NAV_SNAPSHOT','READBACK'),'valuation event only; never trade, funding or settlement')
        key=(kind,t)
        if key not in TARGETS:return original
        need(type(t)is int and key not in self.seen,'duplicate or noninteger exact valuation')
        pos=positions.get(SYMBOL,{})
        need(pos.get('active')is True and pos.get('instrument_id')==GENERATION and t<CLOSE,'active original generation at valuation')
        need(SYMBOL in original and original[SYMBOL]is None,'only original missing valuation may be supplemented')
        new=dict(original);new[SYMBOL]=self.values[key];self.seen.add(key);return new

    def finish(self,last_accepted_ms):
        need(self.seen=={key for key in TARGETS if key[1]<=last_accepted_ms},'complete accepted valuation prefix; no missing/future source uses')

    def summary(self):
        return dict(source_body_sha256=SOURCE_HASHES['markPriceKlines.body'],applied_valuation_events=len(self.seen),events=[dict(type=k,ts_ms=t,price=self.values[(k,t)]) for k,t in sorted(self.seen,key=lambda x:x[1])],ordinary_execution_observations_changed=False,funding_or_settlement_marks_changed=False)

def admit(original_pins,pins):
    blobs={}
    for n,h in SOURCE_HASHES.items():
        p=str(SOURCE/n);need(original_pins.get(p)==h and (p not in pins or pins[p]==h),'actual original mark source monitored without conflict')
        blobs[n]=Path(p).read_bytes();pins[p]=h
    return MarkFacts(blobs)

def compare_prefix(day_records,raw):
    need(hashlib.sha256(raw).hexdigest()==PREFIX_SHA,'frozen previously accepted 570-DAY reference')
    previous=json.loads(raw)
    need(len(previous)==570 and previous[-1]['ts_ms']==FIRST,'original 570-DAY prefix endpoint')
    need(len(day_records)>=570 and day_records[:570]==previous,'all independent economic quantities unchanged over original 570-DAY prefix')
    return dict(reference=dict(path=str(PREFIX),sha256=PREFIX_SHA),daily_nodes=570,last_ms=FIRST,all_economic_fields_equal=True,repeated_original_arithmetic=False)
