"""Known contract generations around the frozen funding EMA implementation.

No arithmetic changes: each admitted generation gets the same at_anchors call,
with only that instrument's events. Unlisted names retain conditional legacy
continuity. This calendar is an audited boundary subset, not PIT certification.
"""
import hashlib
import re

import numpy as np

from funding_features import at_anchors
from market_utils import canonical_rates


def validate_calendar(calendar, *, source_reader=None):
    if not isinstance(calendar, dict) or calendar.get('schema') != 'contract-lifecycle-1':
        raise ValueError('lifecycle calendar schema')
    if calendar.get('unlisted_symbol_policy') != 'LEGACY_CONTINUITY_UNAUDITED':
        raise ValueError('explicit unlisted lifecycle policy required')
    names, sources = calendar.get('symbols'), calendar.get('sources')
    if not isinstance(names, dict) or not isinstance(sources, dict):
        raise ValueError('lifecycle population/source mapping')
    for source_id, source in sources.items():
        if not isinstance(source, dict) or not isinstance(source_id, str):
            raise ValueError('lifecycle source structure')
        if (not isinstance(source.get('url'), str) or not source['url'].startswith('https://www.binance.com/')
                or not isinstance(source.get('text_path'), str)
                or not re.fullmatch('[a-f0-9]{64}', str(source.get('text_sha256')))):
            raise ValueError('lifecycle source identity')
        if type(source.get('published_at_ms')) is not int or source['published_at_ms'] < 0:
            raise ValueError('lifecycle source published time')
        if source_reader is not None:
            payload = source_reader(source['text_path'])
            if not isinstance(payload, bytes) or hashlib.sha256(payload).hexdigest() != source['text_sha256']:
                raise ValueError('lifecycle source SHA changed')
    for symbol, entry in names.items():
        if not isinstance(symbol, str) or not isinstance(entry, dict):
            raise ValueError('lifecycle symbol entry')
        initial, transitions = entry.get('initial_generation'), entry.get('transitions')
        if not isinstance(initial, dict) or not isinstance(transitions, list):
            raise ValueError('lifecycle initial generation/transitions')
        current = initial.get('instrument_id')
        if not isinstance(current, str) or not current or not isinstance(initial.get('underlying'), str):
            raise ValueError('initial instrument identity')
        if initial.get('birth_ms') is not None or initial.get('birth_evidence') != 'UNKNOWN':
            raise ValueError('initial birth must retain explicit unknown evidence')
        previous = -1
        seen_ids = {current}
        for event in transitions:
            if not isinstance(event, dict):
                raise ValueError('lifecycle transition structure')
            stamp, announced = event.get('effective_ms'), event.get('announced_at_ms')
            if type(stamp) is not int or type(announced) is not int or not 0 <= announced <= stamp or stamp <= previous:
                raise ValueError('lifecycle announcement/effective clock')
            previous = stamp
            source = sources.get(event.get('source_id'))
            if source is None or source['published_at_ms'] != announced:
                raise ValueError('lifecycle source published time binding')
            identity = event.get('instrument_id')
            if not isinstance(identity, str) or not identity or not isinstance(event.get('underlying'), str):
                raise ValueError('lifecycle transition identity')
            if event.get('kind') == 'CLOSE':
                if identity != current:
                    raise ValueError('lifecycle CLOSE identity/order')
                current = None
            elif event.get('kind') == 'OPEN':
                if current is not None or identity in seen_ids:
                    raise ValueError('lifecycle OPEN needs a distinct inactive instrument')
                seen_ids.add(identity)
                current = identity
            else:
                raise ValueError('lifecycle transition kind')
    return calendar


def generation_at_anchors(events, anchors, *, calendar, symbol, observed_ts, **kwargs):
    """Apply known transitions causally at the funding query cutoff.

    Announcement timestamps are historical publication proxies; observation O
    is modeled. This function does not imply new-risk eligibility at O. In
    particular, a close after the funding cutoff but before O is still handled
    by the producer's separate instrument eligibility at O.
    """
    validate_calendar(calendar)
    a, observed = np.asarray(anchors), np.asarray(observed_ts)
    if (a.ndim != 1 or a.dtype.kind not in 'iu' or observed.shape != a.shape
            or observed.dtype.kind not in 'iu' or (observed < a).any()):
        raise ValueError('generation observation clock')
    # The original function validates and canonicalizes all source event facts.
    rows = canonical_rates(events)
    if symbol not in calendar['symbols']:
        return at_anchors(rows, a, **kwargs)
    entry = calendar['symbols'][symbol]
    cutoff = a.astype(np.int64) * 1000 + kwargs.get('visibility_cutoff_ms', 0)
    observation_ms = observed.astype(np.int64) * 1000
    # -1 denotes an observed closure. 0 retains unaudited initial history.
    selected = np.zeros(len(a), dtype=np.int32)
    generations = [{'birth': None, 'close': None}]
    current = 0
    for event in entry['transitions']:
        visible = (event['announced_at_ms'] <= observation_ms) & (event['effective_ms'] <= cutoff)
        if event['kind'] == 'CLOSE':
            generations[current]['close'] = event['effective_ms']
            selected[visible] = -1
        else:
            generations.append({'birth': event['effective_ms'], 'close': None})
            current = len(generations) - 1
            selected[visible] = current
    result = at_anchors([], a, **kwargs)
    for index, generation in enumerate(generations):
        mask = selected == index
        if not mask.any():
            continue
        born, closed = generation['birth'], generation['close']
        history = [r for r in rows if (born is None or r[0] >= born) and (closed is None or r[0] < closed)]
        values = at_anchors(history, a[mask], **kwargs)
        for name, array in values.items():
            result[name][mask] = array
    return result
