"""Exact-ms rate view for the unchanged canonical on_funding cash calculation.

Construct only from d10_first_span_identity.check_and_load returned events. This
module reads no files and does not change targets, fills, prices, fees or priority.
Pair ExactMsFundingMixin with the SHA-bound HistSim31 class, not Sim.run (whose
historical funding scheduler iterates integer-second dictionary keys).
"""
import collections
import contextlib
import math
import numbers


class _ActiveRates:
    def __init__(self, owner):
        self.owner = owner

    def get(self, key, default=None):
        active = self.owner._active
        if active is None:
            raise RuntimeError('Funding rate queried outside an exact-ms event')
        symbol, second = key
        if second != active[0] // 1000:
            raise RuntimeError('Canonical second key differs from the active ms event')
        return active[1].get(symbol, default)


class ExactMsFunding:
    def __init__(self, events, start_ms, end_ms):
        if not isinstance(start_ms, numbers.Integral) or not isinstance(end_ms, numbers.Integral) or end_ms <= start_ms:
            raise ValueError('Integer-ms nonempty cash interval required')
        symbols = [str(s) for s in events['symbols']]
        if len(set(symbols)) != len(symbols):
            raise ValueError('Duplicate symbols')
        ts, jj, rates = events['ft_ms'], events['symbol_index'], events['rate']
        if not (len(ts) == len(jj) == len(rates)):
            raise ValueError('Event axes differ')
        self._events = {}
        seen = set()
        for t, j, r in zip(ts, jj, rates):
            if not isinstance(t, numbers.Integral) or not isinstance(j, numbers.Integral):
                raise ValueError('Times and symbol indices must be integer')
            t, j, r = int(t), int(j), float(r)
            if not 0 <= j < len(symbols) or not math.isfinite(r):
                raise ValueError('Invalid symbol index or funding rate')
            if (t, j) in seen:
                raise ValueError('Duplicate exact-ms event for symbol')
            seen.add((t, j))
            if start_ms < t <= end_ms:
                self._events.setdefault(t, {})[symbols[j]] = r
        self.times_ms = tuple(sorted(self._events))
        self.times = tuple(t / 1000 for t in self.times_ms)
        if any(round(t * 1000) != ms for t, ms in zip(self.times, self.times_ms)):
            raise ValueError('Float event time does not round-trip to original ms')
        self.n_rows = sum(len(v) for v in self._events.values())
        self._active = None
        self.rate = _ActiveRates(self)
        self.xcheck = {'source': 'bound exact-ms events; no second coalescing',
                       'start_ms_exclusive': int(start_ms), 'end_ms_inclusive': int(end_ms),
                       'rows': self.n_rows, 'event_times': len(self.times)}
        self.src = collections.Counter({'bound_exact_ms': self.n_rows})

    @contextlib.contextmanager
    def active_event(self, t):
        if self._active is not None:
            raise RuntimeError('Nested funding event activation')
        if not math.isfinite(t):
            raise ValueError('Nonfinite event time')
        ms = round(t * 1000)
        if t != ms / 1000 or ms not in self._events:
            raise ValueError('Unbound exact-ms event time')
        self._active = (ms, self._events[ms])
        try:
            yield
        finally:
            self._active = None


class ExactMsFundingMixin:
    def on_funding(self, t):
        with self.F.active_event(t):
            return super().on_funding(t)
