"""Standalone source-bound settlement ledger; not wired into frozen cash runs.

Termination and cash measurability are distinct. A scheduled close-all notice
can support a named schedule-conditional replay, but never invents settlement
price, historical fee, or proof of the venue's actual completion timestamp.
"""
import copy
import hashlib
import json
import math
from types import MappingProxyType

SCHEMA = 'lifecycle-cash-1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('invalid finite '+name)
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError('invalid sign '+name)
    return float(value)


def stamp(value, name):
    if type(value) is not int or value < 0:
        raise ValueError('invalid milliseconds '+name)
    return value


class Registry:
    def __init__(self, digest, payloads):
        self.sha256 = digest
        self.payloads = MappingProxyType(dict(payloads))


def cash_claim(event, qty):
    if qty == 0 or event['value_evidence'] == 'EXACT':
        return None
    return {'event_id':event['event_id'],'instrument_id':event['instrument_id'],'symbol':event['symbol'],
            'effective_ms':event['effective_ms'],'quantity':qty,'settlement_price':event.get('settlement_price'),
            'fee_rate':event.get('fee_rate'),'value_evidence':event['value_evidence'],
            'time_evidence':event['time_evidence'],'source_sha256':event['source_sha256'],
            'cash_expression':'quantity * settlement_price - abs(quantity) * settlement_price * fee_rate'}


def load_registry(body, expected_sha256, source_reader):
    if not isinstance(body, bytes) or hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError('registry SHA binding')
    registry = json.loads(body)
    if registry.get('schema') != 'lifecycle-registry-1' or not isinstance(registry.get('events'), list):
        raise ValueError('registry schema')
    payloads, identities = {}, set()
    for event in registry['events']:
        for name in ('event_id','instrument_id','symbol','source_path','source_url','source_sha256'):
            if not isinstance(event.get(name),str) or not event[name]:
                raise ValueError('settlement identity '+name)
        if event['event_id'] in payloads or event['instrument_id'] in identities:
            raise ValueError('duplicate settlement/instrument identity')
        if not event['source_url'].startswith('https://www.binance.com/'):
            raise ValueError('settlement source URL')
        if stamp(event['published_ms'],'published') > stamp(event['effective_ms'],'effective'):
            raise ValueError('announcement after effective: requires separate late-evidence contract')
        if event.get('time_evidence') not in ('OFFICIAL_SCHEDULED','VENUE_CONFIRMED'):
            raise ValueError('explicit settlement time evidence required')
        if event.get('value_evidence') not in ('UNKNOWN','EXACT','PROXY'):
            raise ValueError('explicit settlement value evidence required')
        if event.get('settlement_price') is not None:
            number(event['settlement_price'],'settlement price',positive=True)
        if event.get('fee_rate') is not None:
            number(event['fee_rate'],'settlement fee',nonnegative=True)
        if event['value_evidence']=='EXACT' and (event.get('settlement_price') is None or event.get('fee_rate') is None):
            raise ValueError('exact settlement needs price and fee')
        source = source_reader(event['source_path'])
        if not isinstance(source,bytes) or hashlib.sha256(source).hexdigest()!=event['source_sha256']:
            raise ValueError('source SHA binding')
        payloads[event['event_id']] = canonical(event)
        identities.add(event['instrument_id'])
    return Registry(expected_sha256,payloads)


def new_state(cash, quantities):
    if not isinstance(quantities,dict):
        raise ValueError('instrument quantities mapping')
    state = {'schema':SCHEMA,'known_cash':number(cash,'cash'),'q':dict(quantities),
             'claims':[],'closed':{},'processed_settlements':{},'registry_shas':[],
             'unresolved_prior_cash':[],'endpoint_cash_complete':True,
             'last_event_ms':-1,'last_event_kind':None}
    return restore(state)


def restore(state):
    if not isinstance(state,dict) or state.get('schema') != SCHEMA:
        raise ValueError('legacy lifecycle state requires_replay')
    required={'known_cash','q','claims','closed','processed_settlements','registry_shas','unresolved_prior_cash','endpoint_cash_complete','last_event_ms','last_event_kind'}
    if not required.issubset(state):
        raise ValueError('incomplete lifecycle state requires_replay')
    s=copy.deepcopy(state)
    s['known_cash']=number(s['known_cash'],'state cash')
    if not isinstance(s['q'],dict) or not isinstance(s['closed'],dict) or not isinstance(s['processed_settlements'],dict):
        raise ValueError('state instrument identity mapping')
    for instrument,qty in s['q'].items():
        if not isinstance(instrument,str) or not instrument:
            raise ValueError('state instrument identity')
        s['q'][instrument]=number(qty,'quantity')
        if instrument in s['closed'] and qty != 0:
            raise ValueError('terminated instrument cannot retain quantity')
    if any(not isinstance(s[k],list) for k in ('claims','registry_shas','unresolved_prior_cash')):
        raise ValueError('state obligations list')
    for instrument,event_id in s['closed'].items():
        if instrument not in s['q'] or event_id not in s['processed_settlements']:
            raise ValueError('terminated instrument evidence requires_replay')
    expected_claims = []
    for event_id, receipt in s['processed_settlements'].items():
        if not isinstance(receipt,dict) or not isinstance(receipt.get('event'),dict):
            raise ValueError('invalid settlement receipt requires_replay')
        event = receipt['event']
        if (event.get('event_id')!=event_id or hashlib.sha256(canonical(event)).hexdigest()!=receipt.get('event_sha256')
                or s['closed'].get(event.get('instrument_id'))!=event_id
                or receipt.get('registry_sha256') not in s['registry_shas']):
            raise ValueError('settlement receipt identity binding requires_replay')
        qty=number(receipt.get('quantity_before'),'settled quantity')
        claim=cash_claim(event,qty)
        if claim is not None:
            expected_claims.append(claim)
    if sorted(map(canonical,s['claims'])) != sorted(map(canonical,expected_claims)):
        raise ValueError('settlement claim obligation differs from receipt requires_replay')
    for claim in s['claims']:
        if not isinstance(claim,dict) or claim.get('instrument_id') not in s['closed'] or s['closed'][claim['instrument_id']] != claim.get('event_id'):
            raise ValueError('settlement claim identity binding')
        number(claim.get('quantity'),'claim quantity')
        if claim['quantity']==0:
            raise ValueError('zero quantity settlement claim')
    if type(s['last_event_ms']) is not int or s['last_event_ms'] < -1 or s['last_event_kind'] not in (None,'FUNDING','TRADE','SETTLEMENT'):
        raise ValueError('state event prefix requires_replay')
    # Completeness is derived from persisted unresolved obligations, never
    # trusted from the serialized caller flag.
    s['endpoint_cash_complete']=not s['claims'] and not s['unresolved_prior_cash']
    canonical(s)
    return s


def settle(state,event,registry,*,asof_ms,same_time_order=None):
    s=restore(state)
    if not isinstance(registry,Registry) or not isinstance(event,dict) or registry.payloads.get(event.get('event_id'))!=canonical(event):
        raise ValueError('settlement event registry binding')
    event_id=event['event_id'];digest=hashlib.sha256(canonical(event)).hexdigest()
    if event_id in s['processed_settlements']:
        if s['processed_settlements'][event_id]['event_sha256']!=digest:
            raise ValueError('changed processed settlement requires_replay')
        return s
    now=stamp(asof_ms,'asof');when=event['effective_ms']
    if when>now or event['published_ms']>now:
        raise ValueError('future settlement unavailable')
    if when<s['last_event_ms']:
        raise ValueError('late historical settlement requires_replay')
    if when==s['last_event_ms']:
        if s['last_event_kind']!='FUNDING' or same_time_order!='funding_before_settlement':
            raise ValueError('same_time settlement order requires explicit evidence/assumption')
    elif same_time_order is not None:
        raise ValueError('same_time order supplied without same-time events')
    instrument=event['instrument_id']
    if instrument in s['closed']:
        raise ValueError('terminated instrument has incompatible settlement')
    qty=s['q'].get(instrument,0.)
    if qty!=0:
        if event['value_evidence']=='EXACT':
            price=event['settlement_price'];fee=event['fee_rate']
            s['known_cash']=number(s['known_cash']+qty*price-abs(qty)*price*fee,'settlement cash')
        else:
            s['claims'].append(cash_claim(event,qty))
    s['q'][instrument]=0.;s['closed'][instrument]=event_id
    s['processed_settlements'][event_id]={'event_sha256':digest,'event':copy.deepcopy(event),
        'quantity_before':qty,'registry_sha256':registry.sha256}
    if registry.sha256 not in s['registry_shas']:
        s['registry_shas'].append(registry.sha256)
    s['last_event_ms']=when;s['last_event_kind']='SETTLEMENT'
    return restore(s)


def funding(state,instrument_id,event_ms,mark,rate):
    s=restore(state);when=stamp(event_ms,'funding')
    if when<=s['last_event_ms']:
        raise ValueError('funding historical/same_time event requires_replay or explicit ordered adapter')
    if not isinstance(instrument_id,str) or not instrument_id:
        raise ValueError('funding instrument identity')
    mark=number(mark,'funding mark',positive=True);rate=number(rate,'funding rate')
    s['known_cash']=number(s['known_cash']-s['q'].get(instrument_id,0.)*mark*rate,'funding cash')
    s['last_event_ms']=when;s['last_event_kind']='FUNDING'
    return restore(s)


def trade(state,instrument_id,event_ms,delta_quantity,price):
    s=restore(state);when=stamp(event_ms,'trade')
    if instrument_id in s['closed']:
        raise ValueError('terminated instrument cannot trade')
    if not isinstance(instrument_id,str) or not instrument_id:
        raise ValueError('trade instrument identity')
    if when<=s['last_event_ms']:
        raise ValueError('trade historical/same_time event requires_replay or explicit ordered adapter')
    delta=number(delta_quantity,'trade quantity');price=number(price,'trade price',positive=True)
    s['q'][instrument_id]=number(s['q'].get(instrument_id,0.)+delta,'post-trade quantity')
    s['known_cash']=number(s['known_cash']-delta*price,'trade cash')
    s['last_event_ms']=when;s['last_event_kind']='TRADE'
    return restore(s)
