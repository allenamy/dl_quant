"""Source-only event cash simulator with frozen planning quantities.

This is a research economic path, not a live/PIT, margin, watchdog, or publication
certificate. Caller supplies the complete ordered lifecycle/funding event stream,
its coverage oracle, selected payload, and explicit market/filter observations.
No I/O except reading the SHA-bound pure source dependency at construction.
"""
from pathlib import Path
import copy
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
import time

HOUR4 = 14_400_000
DAY_MS = 86_400_000
POLICY_SHA = '129479e610c501e865b6e01e7af31ed125c6902dd222438c29ca4e0cd0ca2c35'
POLICY_FILE = Path(__file__).resolve().parent.parent / 'actual_executor_policy_review_20260915/pure_policy.py'
PRIORITY = {'DAY': 0, 'FUNDING': 1, 'CLOSE': 2, 'OPEN': 3,
            'NAV_SNAPSHOT': 4, 'PLAN': 5, 'ATTEMPT': 6, 'READBACK': 7}
SCOPE = {
    'certificate': 'RESEARCH_ECONOMIC_PATH_ONLY',
    'sizing': 'FRESH_PROCESS_GROSS_ZERO_EACH_ANCHOR',
    'request': 'N20_PROXY_NAV_AND_MID_N24_PLAN_FROZEN_QUANTITY',
    'fill': 'ONE_PREDECLARED_ATTEMPT_WHOLE_FILL_OR_NO_SUBMISSION',
    'no_submission': 'CONDITIONAL_POLICY_NOT_EVIDENCE_OF_HISTORICAL_NO_FILL',
    'valuation': 'ORDINARY_CLOSE_PROXY_UTC_LEFT_LIMIT',
    'settlement': 'PER_SCENARIO_CONDITIONAL_REFERENCE_MULTIPLIER',
    'not_covered': ['fault_watchdog', 'daily_loss_halt_or_recovery', 'margin_liquidation',
                    'historical_sigma_ladder', 'venue_filter_PIT', 'queue_partial_fill',
                    'spread_or_impact', 'venue_caps_or_post_clamp_netbias', 'publisher_guard_or_fallback_admission', 'archive_PIT'],
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _integer(value, name):
    if type(value) is not int:
        raise ValueError(name + ' must be an exact integer')
    return value


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive(value):
    return _finite(value) and value > 0


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(_jsonable(x) for x in value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(x) for x in value]
    return value


def _quantity_sum(qty, delta):
    # Legal native request quantities are decimal lot amounts. No epsilon/dust
    # erasure: retain even tiny legal amounts, and stop if JSON float transport
    # cannot losslessly represent the exact decimal result of the two inputs.
    with localcontext() as ctx:
        ctx.prec = 1000
        exact = Decimal(str(qty)) + Decimal(str(delta))
    result = float(exact)
    if not math.isfinite(result) or Decimal(str(result)) != exact:
        raise ValueError('quantity exceeds lossless decimal JSON representation')
    return result


def position_after_fill(qty, entry, delta, price):
    """Signed linear contracts; entry only affects PNS, not cash accounting."""
    if not all(_finite(x) for x in (qty, delta)) or not _positive(price):
        raise ValueError('invalid fill arithmetic')
    if qty != 0 and not _positive(entry):
        raise ValueError('held position needs finite positive entry')
    new = _quantity_sum(qty, delta)
    if new == 0:
        return 0., None
    if qty == 0 or qty * new < 0:
        return new, float(price)
    if qty * delta > 0:
        return new, (abs(qty) * entry + abs(delta) * price) / abs(new)
    return new, entry


class _Unknown(Exception):
    def __init__(self, reason, **detail):
        self.reason, self.detail = reason, detail


class Engine:
    """One scenario, one state. apply/run never infer omitted external events.

    funding_coverage(symbol, instrument_id, start_ms, end_ms) must certify that
    ALL cash obligations in the held half-open interval [start_ms, end_ms) are
    enumerated/priced by the supplied event source. Its config ID is a binding
    label; the outer runner must SHA-bind the actual callback/data implementation.
    """
    def __init__(self, config, *, state=None, funding_coverage):
        self.config = copy.deepcopy(config)
        c = self.config
        if c.get('schema') != 'DYNAMIC_EXECUTOR_CASH_CONFIG_1':
            raise ValueError('config schema')
        for key in ('initial_capital', 'settlement_factor'):
            if not _positive(c.get(key)):
                raise ValueError(key + ' must be finite and positive')
        for key in ('ordinary_fee_bps', 'settlement_fee_bps'):
            if not _finite(c.get(key)) or c[key] < 0:
                raise ValueError(key + ' must be finite and nonnegative')
        if c.get('ladder_multiplier') not in (.5, 1.) or type(c.get('use_pns')) is not bool:
            raise ValueError('explicit ladder/PNS policy required')
        if not isinstance(c.get('funding_coverage_id'), str) or not c['funding_coverage_id']:
            raise ValueError('funding coverage identity required')
        _integer(c.get('origin_ms'), 'origin_ms')
        c.setdefault('attempt_offset_ms', 1_500_000)
        if c['attempt_offset_ms'] not in (1_500_000, 3_300_000):
            raise ValueError('predeclare 25 or 55 minute attempt')
        instruments = c.get('instruments')
        if not isinstance(instruments, dict) or not instruments:
            raise ValueError('unique instrument identity map required')
        initial_positions = {}
        for symbol, value in instruments.items():
            if not isinstance(symbol, str) or not symbol:
                raise ValueError('nonempty symbol required')
            # String form is the synthetic/all-current-active shorthand. Real
            # calendar admission can represent a not-yet-born name explicitly.
            rec = dict(instrument_id=value, active=True) if isinstance(value, str) else value
            if not isinstance(rec, dict) or type(rec.get('active')) is not bool:
                raise ValueError('explicit initial lifecycle activity required')
            iid = rec.get('instrument_id')
            if not (isinstance(iid, str) and iid) and not (iid is None and rec['active'] is False):
                raise ValueError('active instrument requires an identity')
            initial_positions[symbol] = dict(qty=0., entry=None, instrument_id=iid, active=rec['active'])
        initial_ids = [p['instrument_id'] for p in initial_positions.values() if p['instrument_id'] is not None]
        if len(initial_ids) != len(set(initial_ids)):
            raise ValueError('unique instrument identity map required')
        if not callable(funding_coverage):
            raise ValueError('funding coverage oracle required')
        self.coverage = funding_coverage
        if hashlib.sha256(POLICY_FILE.read_bytes()).hexdigest() != POLICY_SHA:
            raise ValueError('pure policy source identity')
        spec = importlib.util.spec_from_file_location('_dynamic_cash_bound_pure_policy', POLICY_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.policy = module.load_policy()
        self.identity = _digest({'config': c, 'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                 'policy_sha256': POLICY_SHA, 'source_pins': self.policy.pins, 'scope': SCOPE})
        if state is not None:
            self.s = copy.deepcopy(state)
            if self.s.get('schema') != 'DYNAMIC_EXECUTOR_CASH_STATE_1' or self.s.get('identity') != self.identity:
                raise ValueError('resume source/config identity mismatch')
            json.dumps(self.s, allow_nan=False)
            self._check_state(self.s)
        else:
            self.s = dict(schema='DYNAMIC_EXECUTOR_CASH_STATE_1', identity=self.identity,
                scope=copy.deepcopy(SCOPE), status='RESEARCH_PATH_OPEN', blocked=None,
                config=copy.deepcopy(c), cash=float(c['initial_capital']),
                positions=initial_positions, generation_history=initial_ids,
                pns=dict(counters={}, stopped={}, cooldown={}), clock_ms=c['origin_ms'],
                last_order=None, seen_ids=[], seen_economic_events=[], snapshot=None, pending=None,
                totals=dict(ordinary_fees=0., ordinary_turnover=0., trade_cash=0., funding_cash=0.,
                            settlement_cash_gross=0., settlement_fees=0.), journal=[], days=[])
        self._seen = set(self.s['seen_ids'])
        self._economic_seen = set(self.s['seen_economic_events'])

    def _check_state(self, s):
        if not _finite(s['cash']) or set(s['positions']) != set(self.config['instruments']):
            raise ValueError('invalid resumed cash/axis')
        for p in s['positions'].values():
            if type(p['active']) is not bool or (p['active'] and (not isinstance(p['instrument_id'], str) or not p['instrument_id'])):
                raise ValueError('invalid resumed lifecycle identity')
            if p['instrument_id'] is not None and p['instrument_id'] not in s['generation_history']:
                raise ValueError('resumed lifecycle identity absent from history')
            if not _finite(p['qty']) or (p['qty'] != 0 and not _positive(p['entry'])):
                raise ValueError('invalid resumed position')
            if (p['qty'] == 0 and p['entry'] is not None) or (not p['active'] and p['qty'] != 0):
                raise ValueError('invalid resumed flat/inactive position')
        if not all(_finite(x) for x in s['totals'].values()):
            raise ValueError('nonfinite cash accumulation')

    def export(self):
        return copy.deepcopy(self.s)

    def run(self, events):
        iterator = iter(events)
        event = next(iterator, None)
        while event is not None and self.s['status'] != 'UNMEASURABLE':
            if event.get('type') == 'FUNDING':
                batch = [event]
                future = next(iterator, None)
                while future is not None and future.get('type') == 'FUNDING' and future.get('ts_ms') == event.get('ts_ms'):
                    batch.append(future)
                    future = next(iterator, None)
                self.apply_funding_batch(batch)
                event = future
            else:
                self.apply(event)
                event = next(iterator, None)
        return self.export()

    def _copy_core(self):
        # Historical rows are immutable; copy only current economic state per event.
        return {k: (v if k in ('journal', 'days', 'seen_ids', 'seen_economic_events') else copy.deepcopy(v))
                for k, v in self.s.items()}

    def apply(self, event):
        if self.s['status'] == 'UNMEASURABLE':
            raise ValueError('unmeasurable path cannot continue by guessing')
        if event.get('type') == 'FUNDING':
            return self.apply_funding_batch([event])
        e = copy.deepcopy(event)
        kind, eid = e.get('type'), e.get('id')
        ts = _integer(e.get('ts_ms'), 'event ts_ms')
        if kind not in PRIORITY or not isinstance(eid, str) or not eid:
            raise ValueError('event type/id')
        order = [ts, PRIORITY[kind]]
        if (ts == self.s['clock_ms'] and eid in self._seen) or ts < self.s['clock_ms'] or (self.s['last_order'] is not None and order < self.s['last_order']):
            raise ValueError('duplicate or event order')
        if kind in ('FUNDING', 'CLOSE', 'OPEN'):
            key = json.dumps([kind, ts, e.get('symbol'), e.get('instrument_id')])
        elif kind == 'DAY':
            key = json.dumps([kind, ts])
        else:
            key = json.dumps([kind, e.get('anchor_ms')]) if kind != 'READBACK' else json.dumps([kind, ts // HOUR4 * HOUR4])
        if ts == self.s['clock_ms'] and key in self._economic_seen:
            raise ValueError('duplicate economic event under another id')
        s = self._copy_core()
        row = dict(type=kind, ts_ms=ts, id=eid)
        try:
            if ts > s['clock_ms']:
                for sym, p in s['positions'].items():
                    if p['qty'] != 0:
                        known = self.coverage(sym, p['instrument_id'], s['clock_ms'], ts)
                        if type(known) is not bool:
                            raise ValueError('funding coverage oracle must return exact bool')
                        if not known:
                            raise _Unknown('MISSING_HELD_FUNDING_COVERAGE', symbol=sym,
                                           start_ms=s['clock_ms'], end_ms=ts)
            getattr(self, '_on_' + kind.lower())(s, e, row)
            self._check_state(s)
            # Validate JSON safety without scanning the growing immutable journals.
            json.dumps({k: v for k, v in s.items() if k not in ('journal', 'days', 'seen_ids', 'seen_economic_events')}, allow_nan=False)
            json.dumps(row, allow_nan=False)
        except _Unknown as x:
            self.s['status'] = 'UNMEASURABLE'
            self.s['blocked'] = dict(reason=x.reason, event_id=eid, ts_ms=ts, **x.detail)
            self.s['journal'].append(dict(row, outcome='UNMEASURABLE', reason=x.reason, detail=x.detail))
            return copy.deepcopy(self.s['journal'][-1])
        if ts > self.s['clock_ms']:
            s['seen_ids'], s['seen_economic_events'] = [], []
            self._seen, self._economic_seen = set(), set()
        s['clock_ms'], s['last_order'] = ts, order
        row.update(cash_after=s['cash'], outcome='APPLIED_RESEARCH_EVENT')
        s['journal'].append(row)
        if 'day_record' in row:
            s['days'].append(copy.deepcopy(row['day_record']))
        s['seen_ids'].append(eid); s['seen_economic_events'].append(key)
        self._seen.add(eid); self._economic_seen.add(key)
        self.s = s
        return copy.deepcopy(row)

    def _anchor(self, e, offset=None):
        a = _integer(e.get('anchor_ms'), 'anchor_ms')
        if a % HOUR4 != 0 or (offset is not None and e['ts_ms'] != a + offset):
            raise ValueError('fixed anchor/clock policy mismatch')
        return a

    def _marks(self, s, e, reason):
        asof = _integer(e.get('price_asof_ms'), 'price_asof_ms')
        if asof > e['ts_ms']:
            raise ValueError('future valuation price')
        if not isinstance(e.get('prices'), dict):
            raise ValueError('prices mapping required')
        marks, notionals = {}, {}
        for sym, p in s['positions'].items():
            value = e['prices'].get(sym)
            marks[sym] = float(value) if _positive(value) else None
            if p['qty'] != 0:
                if marks[sym] is None:
                    raise _Unknown(reason, symbol=sym, instrument_id=p['instrument_id'])
                notionals[sym] = p['qty'] * marks[sym]
        return marks, notionals

    def _on_nav_snapshot(self, s, e, row):
        a = self._anchor(e, 1_200_000)
        if e['price_asof_ms'] != e['ts_ms']:
            raise ValueError('NAV proxy must be exact N20 close, no future or opportunistic stale mark')
        old = s['pending']
        if old and (not old['attempted'] or (self.config['use_pns'] and not old['readback'])):
            raise ValueError('previous anchor lacks required attempt/readback')
        marks, notionals = self._marks(s, e, 'MISSING_HELD_NAV_MARK')
        nav = s['cash'] + sum(notionals.values())
        if not _finite(nav) or nav <= 0:
            raise _Unknown('NONPOSITIVE_OR_NONFINITE_NAV_UNSUPPORTED_RISK', nav=nav if _finite(nav) else None)
        s['snapshot'] = dict(id=e['id'], anchor_ms=a, ts_ms=e['ts_ms'], cash=s['cash'], nav=nav,
            marks=marks, notionals=notionals,
            positions=copy.deepcopy(s['positions']))
        row.update(nav=nav, held_count=len(notionals))

    def _on_plan(self, s, e, row):
        a = self._anchor(e, 1_440_000)
        cut = s['snapshot']
        if not cut or cut['id'] != e.get('snapshot_id') or cut['anchor_ms'] != a:
            raise ValueError('plan snapshot identity mismatch')
        observed = _integer(e.get('payload_observed_ms'), 'payload_observed_ms')
        if observed > e['ts_ms']:
            raise ValueError('future payload')
        if s['positions'] != cut['positions']:
            raise _Unknown('SNAPSHOT_INVENTORY_CHANGED_BEFORE_PLAN')
        weights, universe = e.get('weights'), e.get('universe')
        if not isinstance(weights, dict) or not weights or not all(isinstance(k, str) and _finite(v) for k, v in weights.items()):
            raise ValueError('finite selected raw weights required')
        if not isinstance(universe, list) or not universe or len(set(universe)) != len(universe) or not all(isinstance(x, str) and x for x in universe):
            raise ValueError('explicit unique producer universe required')
        if not set(weights).issubset(s['positions']) or not set(universe).issubset(s['positions']):
            raise ValueError('payload axis outside lifecycle instrument map')
        # Original publisher sparsity uses unrounded Python floats. This local
        # envelope is a research input, not a fabricated actual producer receipt.
        serial = self.policy.serialize_weights(list(weights.values()), list(weights))
        payload = dict(schema='wide_target_v1', anchor_ts=a // 1000, weights=serial,
            gross_norm=sum(abs(v) for v in serial.values()), n_names=len(serial), universe=universe,
            universe_sha=self.policy.ext['universe_sha'](universe), booster_sha='RESEARCH_SELECTED_PAYLOAD',
            weights_sha=_digest(weights), written_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(observed / 1000)))
        parsed = self.policy.ext['parse_target'](json.dumps(payload).encode(),
            dict(schema='wide_target_v1', require_anchor_match=True, max_age_min=10.), a // 1000, e['ts_ms'] / 1000)
        if not parsed['ok']:
            raise ValueError('selected payload contract: ' + str(parsed['reason']))
        sizing = self.policy.size_fresh(cut['nav'], ladder_multiplier=self.config['ladder_multiplier'])
        if sizing['blind'] or not _positive(sizing['nav']):
            raise _Unknown('BLIND_SIZING_UNSUPPORTED_RISK')
        pending = dict(anchor_ms=a, snapshot_id=cut['id'], ts_ms=e['ts_ms'], expiry_ms=a + HOUR4,
            sizing=sizing, requests={}, attempted=False, readback=False,
            payload_sha256=_digest(payload), publication='CALLER_SELECTED_RESEARCH_PAYLOAD_NOT_ADMITTED_HERE')
        filters = e.get('filters')
        if not isinstance(filters, dict) or not set(s['positions']).issubset(filters):
            raise ValueError('explicit filter assumptions required for every lifecycle symbol')
        for f in filters.values():
            if not isinstance(f, dict) or not _positive(f.get('step')) or not _positive(f.get('min_notional')):
                raise ValueError('invalid filter assumptions')
        restricted = e.get('untradable')
        if not isinstance(restricted, list) or not set(restricted).issubset(s['positions']):
            raise ValueError('explicit untradable axis')
        if sizing['halt']:
            pending['halt_reason'] = 'SOURCE_MIN_GROSS_NO_ORDERS_THIS_ANCHOR'
        else:
            active = self.policy.pns['active_sets'](s['pns'], e['ts_ms'] / 1000) if self.config['use_pns'] else {'stop': set(), 'cooldown': set()}
            blocked = set(restricted) | {k for k, p in s['positions'].items() if not p['active']} | active['cooldown']
            shaped = self.policy.shape_target(parsed, cut['notionals'], blocked, sizing['gross'],
                floors_usdt={k: v['min_notional'] for k, v in filters.items()}, force_flat=active['stop'])
            reduce_only = set(shaped['clamp']['reduced']) | set(shaped['clamp']['flatten_only'])
            requests = self.policy.quantity_plan(shaped['target_notional'], cut['notionals'], cut['marks'],
                held_qty={k: p['qty'] for k, p in cut['positions'].items()}, filters=filters, reduce_only_syms=reduce_only)
            for request in requests:
                sym = request['symbol']
                request.update(instrument_id=cut['positions'][sym]['instrument_id'],
                    held_qty_at_plan=cut['positions'][sym]['qty'],
                    desired_qty_after_request=_quantity_sum(cut['positions'][sym]['qty'], request.get('qty', 0.)))
                pending['requests'][sym] = request
            pending['shape'] = _jsonable(shaped)
        s['pending'] = pending
        row.update(sizing=copy.deepcopy(sizing), request_count=len(pending['requests']),
                   payload_sha256=pending['payload_sha256'], halt_reason=pending.get('halt_reason'))

    def _on_attempt(self, s, e, row):
        a = self._anchor(e, self.config['attempt_offset_ms'])
        pending = s['pending']
        if not pending or pending['anchor_ms'] != a or pending['attempted'] or e['ts_ms'] >= pending['expiry_ms']:
            raise ValueError('missing, repeated, or expired frozen plan')
        observations = e.get('observations')
        if not isinstance(observations, dict):
            raise ValueError('explicit attempt observations required')
        fills, missed = [], []
        for sym, request in sorted(pending['requests'].items()):
            p = s['positions'][sym]
            common = dict(symbol=sym, request_qty=request.get('qty'), target_notional=request['target_notional'])
            reason = None
            if p['instrument_id'] != request['instrument_id']:
                reason = 'GENERATION_CHANGED'
            elif not p['active']:
                reason = 'INSTRUMENT_CLOSED'
            elif 'qty' not in request:
                reason = request.get('skip') or 'NO_REQUEST_INSIDE_BAND'
            else:
                ob = observations.get(sym)
                if not isinstance(ob, dict):
                    raise ValueError('missing observation must be explicit MISSING status')
                if _integer(ob.get('observed_ms'), 'observation ms') != e['ts_ms']:
                    raise ValueError('future or stale attempt observation')
                status = ob.get('status')
                if status not in ('ACTIVE', 'ZERO_ACTIVITY', 'MISSING'):
                    raise ValueError('attempt activity status')
                if status == 'ZERO_ACTIVITY':
                    reason = 'OBSERVED_ZERO_ACTIVITY'
                elif status == 'MISSING':
                    reason = 'MISSING_REQUIRED_OBSERVATION'
                elif not _positive(ob.get('price')):
                    raise ValueError('ACTIVE observation needs finite positive fill price; use MISSING explicitly')
                elif ob.get('submission_allowed', True) is not True:
                    if ob['submission_allowed'] is not False:
                        raise ValueError('submission_allowed exact bool')
                    reason = 'EXPLICIT_NO_SUBMISSION'
            if reason:
                missed.append(dict(common, reason=reason, residual_qty=request.get('qty')))
                continue
            delta, price = request['qty'], float(ob['price'])
            if p['qty'] != request['held_qty_at_plan']:
                raise ValueError('inventory changed after frozen plan without lifecycle cancellation')
            if request['reduce_only']:
                if p['qty'] * delta >= 0:
                    missed.append(dict(common, reason='REDUCE_ONLY_NO_REDUCIBLE_POSITION', residual_qty=delta))
                    continue
                delta = math.copysign(min(abs(delta), abs(p['qty'])), delta)
            fee = abs(delta * price) * self.config['ordinary_fee_bps'] / 10000.
            s['cash'] -= delta * price + fee
            s['totals']['trade_cash'] -= delta * price
            s['totals']['ordinary_turnover'] += abs(delta * price)
            s['totals']['ordinary_fees'] += fee
            p['qty'], p['entry'] = position_after_fill(p['qty'], p['entry'], delta, price)
            fills.append(dict(common, filled_qty=delta, fill_price=price, fee=fee,
                              residual_qty=_quantity_sum(request['qty'], -delta), instrument_id=p['instrument_id']))
        pending['attempted'] = True
        row.update(fills=fills, missed=missed, halt_reason=pending.get('halt_reason'))

    def _position(self, s, e):
        sym = e.get('symbol')
        if sym not in s['positions']:
            raise ValueError('unknown lifecycle symbol')
        p = s['positions'][sym]
        if e.get('instrument_id') != p['instrument_id']:
            raise ValueError('event instrument identity mismatch')
        return sym, p

    def apply_funding_batch(self, events):
        """Same timestamp only; stable sequential sums, no whole-book copies.

        Event identity is (type, timestamp, symbol, instrument_id). The auxiliary
        id is unique within a timestamp. Previous timestamps cannot recur. A
        resumable hash chain commits all ordered source rows and computed cash
        rows, including zero-held obligations, without a million-row journal.
        """
        if self.s['status'] == 'UNMEASURABLE':
            raise ValueError('unmeasurable path cannot continue by guessing')
        if not isinstance(events, (list, tuple)) or not events:
            raise ValueError('nonempty same-timestamp funding batch required')
        ts = _integer(events[0].get('ts_ms'), 'funding ts_ms')
        order = [ts, PRIORITY['FUNDING']]
        if ts < self.s['clock_ms'] or (self.s['last_order'] is not None and order < self.s['last_order']):
            raise ValueError('funding event order')
        ids = set(self._seen) if ts == self.s['clock_ms'] else set()
        keys = set(self._economic_seen) if ts == self.s['clock_ms'] else set()
        prepared = []
        # Contract errors reject the whole call before changing any money.
        for e in events:
            if e.get('type') != 'FUNDING' or _integer(e.get('ts_ms'), 'funding ts_ms') != ts:
                raise ValueError('batch must contain only one funding timestamp')
            eid = e.get('id')
            if not isinstance(eid, str) or not eid:
                raise ValueError('funding id required')
            key = json.dumps(['FUNDING', ts, e.get('symbol'), e.get('instrument_id')])
            if eid in ids or key in keys:
                raise ValueError('duplicate funding event')
            sym, p = self._position(self.s, e)
            # Null is the explicit missing observation; NaN is not JSON evidence.
            digest = _digest(e)
            prepared.append((copy.deepcopy(e), key, sym, p, digest))
            ids.add(eid); keys.add(key)
        current = self.s
        last = current['journal'][-1] if current['journal'] else None
        extend = bool(last and last['type'] == 'FUNDING' and last['ts_ms'] == ts and last.get('outcome') == 'APPLIED_RESEARCH_EVENT')
        row = copy.deepcopy(last) if extend else dict(type='FUNDING', ts_ms=ts, id=prepared[0][0]['id'],
            event_count=0, held_event_count=0, not_held_event_count=0,
            funding_cash=0., cash_before=current['cash'],
            ordered_event_digest='0' * 64, ordered_cash_digest='0' * 64,
            digest_rule='SHA256(previous_digest_bytes || SHA256(canonical_JSON_row)_bytes)',
            obligation='ALL_ORDERED_EVENTS_RETAINED_BY_HASH_CHAIN', outcome='APPLIED_RESEARCH_EVENT')
        cash = current['cash']; fund_total = current['totals']['funding_cash']
        accepted = []
        def commit():
            if not accepted:
                return
            if ts > current['clock_ms']:
                current['seen_ids'], current['seen_economic_events'] = [], []
                self._seen, self._economic_seen = set(), set()
            current['cash'] = cash
            current['totals']['funding_cash'] = fund_total
            current['clock_ms'], current['last_order'] = ts, order
            row['cash_after'] = cash
            if extend:
                current['journal'][-1] = row
            else:
                current['journal'].append(row)
            for eid, key in accepted:
                current['seen_ids'].append(eid); current['seen_economic_events'].append(key)
                self._seen.add(eid); self._economic_seen.add(key)
        def unknown(reason, e, **detail):
            # A known prefix at this timestamp remains booked, exactly as single
            # apply calls do. Unknown cash is never replaced by zero.
            commit()
            current['status'] = 'UNMEASURABLE'
            current['blocked'] = dict(reason=reason, event_id=e['id'], ts_ms=ts, **detail)
            r = dict(type='FUNDING', ts_ms=ts, id=e['id'], outcome='UNMEASURABLE', reason=reason, detail=detail)
            current['journal'].append(r)
            return copy.deepcopy(r)
        if ts > current['clock_ms']:
            for sym, p in current['positions'].items():
                if p['qty'] != 0:
                    known = self.coverage(sym, p['instrument_id'], current['clock_ms'], ts)
                    if type(known) is not bool:
                        raise ValueError('funding coverage oracle must return exact bool')
                    if not known:
                        return unknown('MISSING_HELD_FUNDING_COVERAGE', prepared[0][0], symbol=sym,
                                       start_ms=current['clock_ms'], end_ms=ts)
        for e, key, sym, p, digest in prepared:
            amount = 0.
            if p['qty'] != 0:
                if not _finite(e.get('rate')) or not _positive(e.get('mark')):
                    return unknown('UNPRICED_HELD_FUNDING', e, symbol=sym, instrument_id=p['instrument_id'])
                amount = -p['qty'] * e['mark'] * e['rate']
            if not _finite(amount) or not _finite(cash + amount) or not _finite(fund_total + amount):
                return unknown('NONFINITE_HELD_FUNDING_ARITHMETIC', e, symbol=sym)
            cash += amount; fund_total += amount
            cash_row = dict(type='FUNDING', ts_ms=ts, id=e['id'], symbol=sym,
                            instrument_id=p['instrument_id'], held_qty=p['qty'], funding_cash=amount)
            row['ordered_event_digest'] = hashlib.sha256(bytes.fromhex(row['ordered_event_digest']) + bytes.fromhex(digest)).hexdigest()
            row['ordered_cash_digest'] = hashlib.sha256(bytes.fromhex(row['ordered_cash_digest']) + bytes.fromhex(_digest(cash_row))).hexdigest()
            row['event_count'] += 1
            row['held_event_count' if p['qty'] != 0 else 'not_held_event_count'] += 1
            row['funding_cash'] += amount
            accepted.append((e['id'], key))
        commit()
        return copy.deepcopy(row)

    def _on_close(self, s, e, row):
        sym, p = self._position(s, e)
        if not p['active']:
            raise ValueError('cannot close inactive instrument twice')
        q = p['qty']; gross = fee = 0.; price = None
        if q != 0:
            if not _positive(e.get('reference_price')):
                raise _Unknown('MISSING_CONDITIONAL_SETTLEMENT_REFERENCE', symbol=sym)
            price = e['reference_price'] * self.config['settlement_factor']
            gross = q * price
            fee = abs(gross) * self.config['settlement_fee_bps'] / 10000.
            s['cash'] += gross - fee
            s['totals']['settlement_cash_gross'] += gross
            s['totals']['settlement_fees'] += fee
        p.update(qty=0., entry=None, active=False)
        row.update(symbol=sym, instrument_id=p['instrument_id'], closed_qty=q,
                   conditional_price=price, settlement_cash_gross=gross, settlement_fee=fee,
                   claim='CONDITIONAL_REFERENCE_NOT_ACTUAL_SETTLEMENT')

    def _on_open(self, s, e, row):
        sym = e.get('symbol'); new = e.get('instrument_id')
        if sym not in s['positions'] or not isinstance(new, str) or not new:
            raise ValueError('new lifecycle identity')
        p = s['positions'][sym]
        if p['active'] or p['qty'] != 0 or new == p['instrument_id']:
            raise ValueError('OPEN requires flat closed predecessor and new generation')
        if new in s['generation_history']:
            raise ValueError('generation identity reused')
        s['generation_history'].append(new)
        p.update(instrument_id=new, active=True, qty=0., entry=None)
        row.update(symbol=sym, instrument_id=new, pns_policy='SYMBOL_STATE_PRESERVED_SOURCE_PARITY')

    def _on_day(self, s, e, row):
        if e['ts_ms'] % DAY_MS != 0 or e['price_asof_ms'] != e['ts_ms']:
            raise ValueError('UTC day left-limit exact ordinary close required')
        _, notionals = self._marks(s, e, 'MISSING_HELD_DAILY_MARK')
        nav = s['cash'] + sum(notionals.values())
        if not _finite(nav) or nav <= 0:
            raise _Unknown('NONPOSITIVE_OR_NONFINITE_DAILY_NAV_UNSUPPORTED_RISK', nav=nav if _finite(nav) else None)
        row['day_record'] = dict(ts_ms=e['ts_ms'], nav=nav, cash=s['cash'], held_count=len(notionals),
                                  convention='T_MINUS_BEFORE_SAME_TIME_FUNDING_CLOSE_OR_TRADE')

    def _on_readback(self, s, e, row):
        pending = s['pending']
        if not pending or not pending['attempted'] or pending['readback'] or not (pending['anchor_ms'] + self.config['attempt_offset_ms'] <= e['ts_ms'] < pending['expiry_ms']):
            raise ValueError('readback must follow one attempt within its anchor')
        if self.config['use_pns']:
            if _integer(e.get('price_asof_ms'), 'readback price_asof_ms') != e['ts_ms']:
                raise ValueError('PNS requires exact postattempt close proxy, no stale/future readback mark')
            marks, notionals = self._marks(s, e, 'MISSING_HELD_PNS_MARK')
            snap = dict(positions_notional=notionals,
                positions_unrealized={k: p['qty'] * (marks[k] - p['entry']) for k, p in s['positions'].items() if p['qty'] != 0})
            s['pns'], events = self.policy.evaluate_postreadback(snap, s['pns'], e['ts_ms'] / 1000)
            row.update(pns_events=events, pns_state=copy.deepcopy(s['pns']))
        pending['readback'] = True
