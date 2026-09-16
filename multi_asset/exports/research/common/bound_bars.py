#!/usr/bin/env python3
"""bound_bars.py — the cells where the 5m cache's `ret5` channel hit its +/-0.30 bound (FIXPROGRAM 2026-09-13 RET-02; FX-DATA).

Why this exists. The canonical 5m caches store `ret5` as float16 hard-clipped at +/-0.30 (memory `cache_ret5_channel_clipped_at_0p30_2026_09_12`,
E-0908-B family). Returns must therefore never be rebuilt from that channel on a window that contains one of these bars: the 2025-10-10
crash alone contributes hundreds of them, and a clipped bar that is then compounded turns a -48% move into +55%. AUDIT_DATA RET-02 lists
devices written after the 09-12 rule that still compound or sum `ret5`, and its action is "swap to raw_patch-corrected returns or assert no
bound bar in the window, per device, when each is next reused". Until now the index of bound bars lived only on pod2, so neither half of
that action could be carried out from a committed device. It is now `common/data/bound_bars_ret5_x0910.npz`.

Provenance. Built by `r6_raw_patch_ext.py` (committed at `uplift_2026-09-11/r6_devices/`, sha 808d2f66) from the x0910 cache; receipt
`uplift_2026-09-11/r6_RECEIPT_raw_patch.json` (952 inherited from `review_scratch/raw_patch.npz` + 3 new: AKEUSDT 2026-09-02 21:45Z,
BULLAUSDT 2026-09-05 03:00Z, WOOUSDT 2026-09-06 01:35Z). 955 cells, 440 symbols, 2022-05-11T13:10Z .. 2026-09-06T01:35Z, both signs
(460 positive, 495 negative), raw values from -0.951 to +3.678. It covers the cache through 2026-09-11T00:00Z and no further; a query
whose window extends past `COVERAGE_END` raises rather than answering "clean".

There is no default window convention and no default sha: every entry point takes `window=` and `expected_sha256=` explicitly, because a
silent default is how this class of defect keeps coming back.
"""
import hashlib, os
import numpy as np

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bound_bars_ret5_x0910.npz")
DATA_SHA256 = "94e8e8c119ea719a4ed1544813d433d00c39148a8e916018435ac10402a6f149"
BOUND = 0.300048828125                 # float16 nearest to 0.30; the stored clip16 value
COVERAGE_END = 1789084800              # 2026-09-11T00:00Z, the last bar of the x0910 cache the index was built from
WINDOWS = ("(lo, hi]", "[lo, hi]", "[lo, hi)")
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class BoundBarError(ValueError):
    """a query this index refuses to answer, or a window that contains a clipped bar"""


def guarded_sha256(path):
    size = os.stat(path).st_size; h = hashlib.sha256(); n = 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    d = h.hexdigest()
    if n != size or (size > 0 and d == EMPTY_SHA256):
        raise BoundBarError("unreadable or evicted file %s (read %d of %d bytes)" % (path, n, size))
    return d


class BoundBars:
    """(symbol, bar close time) -> the raw float32 return the cache clipped."""

    def __init__(self, ts, symbol, raw32, clip16, path, sha):
        self.ts = np.asarray(ts, np.int64); self.symbol = np.asarray([str(s) for s in symbol])
        self.raw32 = np.asarray(raw32, np.float64); self.clip16 = np.asarray(clip16, np.float64)
        self.path, self.sha256 = path, sha
        if not (np.abs(self.clip16) == BOUND).all():
            raise BoundBarError("index contains a cell whose stored value is not the +/-%r bound" % BOUND)
        self._by = {}
        for i, s in enumerate(self.symbol):
            self._by.setdefault(s, []).append(i)
        self._by = {s: np.array(sorted(ix, key=lambda k: self.ts[k]), np.int64) for s, ix in self._by.items()}

    @classmethod
    def load(cls, path=None, *, expected_sha256):
        """`expected_sha256` is required: an index nobody pinned is not evidence."""
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
            raise BoundBarError("expected_sha256 must be the full 64-hex sha of the index (no default)")
        p = DATA if path is None else path
        sha = guarded_sha256(p)
        if sha != expected_sha256:
            raise BoundBarError("index sha %s != expected %s" % (sha[:16], expected_sha256[:16]))
        z = np.load(p, allow_pickle=False)
        return cls(z["ts"], z["symbol"], z["raw32"], z["clip16"], p, sha)

    def _sel(self, sym, lo, hi, window):
        if window not in WINDOWS:
            raise BoundBarError("window must be one of %s (no default), got %r" % (list(WINDOWS), window))
        lo = int(lo); hi = int(hi)
        if hi < lo:
            raise BoundBarError("empty window: hi %d < lo %d" % (hi, lo))
        if hi > COVERAGE_END:
            raise BoundBarError("window ends at %d, past the index coverage end %d: refusing to answer 'clean' "
                                "for bars this index never saw" % (hi, COVERAGE_END))
        ix = self._by.get(str(sym))
        if ix is None:
            return np.empty(0, np.int64)
        t = self.ts[ix]
        if window == "(lo, hi]":
            m = (t > lo) & (t <= hi)
        elif window == "[lo, hi]":
            m = (t >= lo) & (t <= hi)
        else:
            m = (t >= lo) & (t < hi)
        return ix[m]

    def hits(self, symbols, lo, hi, *, window):
        """every (symbol, ts, raw32) of `symbols` with a clipped bar in the window"""
        out = []
        for s in ([symbols] if isinstance(symbols, str) else symbols):
            for i in self._sel(s, lo, hi, window):
                out.append({"symbol": str(self.symbol[i]), "ts": int(self.ts[i]),
                            "raw32": float(self.raw32[i]), "stored": float(self.clip16[i])})
        return sorted(out, key=lambda r: (r["ts"], r["symbol"]))

    def clean(self, symbols, lo, hi, *, window):
        return not self.hits(symbols, lo, hi, window=window)

    def assert_clean(self, symbols, lo, hi, *, window, what=""):
        h = self.hits(symbols, lo, hi, window=window)
        if h:
            raise BoundBarError("%s: %d clipped ret5 bar(s) inside %s [%d, %d]; first %s"
                                % (what or "window", len(h), window, lo, hi, h[0]))
        return True

    def raw_of(self, symbol, ts):
        """the unclipped float32 return of one cell, or None if that cell was never clipped"""
        ix = self._sel(symbol, int(ts) - 1, int(ts), "(lo, hi]")
        return float(self.raw32[ix[0]]) if len(ix) else None
