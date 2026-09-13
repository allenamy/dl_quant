"""t5b_common.py — shared helpers for T5b devices (SPEC_T5b §1). Imported by t5b_q1.py and t5b_exec.py; each device records this file's sha256.
Ledger: producer aux ledger_tail merged over copies, keyed (symbol, ft); rate/iv at anchor A = last row with ft <= A.
  c4 (panel convention, T5): stale (A - ft > 12h) or no row -> rate NaN -> c4 = 0; iv not truthy or <= 0 -> 8.0 (combo_stage L242-L243).
  rn8_ftrim (FTRIM convention, combo_stage L238-L243): last row with ft <= A regardless of age.
Bootstrap: T5 t5_bridge.py L281-L286 boot_ratio verbatim semantics (UTC-day blocks, B=2000, default_rng([20260905, k]), percentile 2.5/97.5)."""
import json, hashlib, bisect
import numpy as np
STALE_S = 12 * 3600
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def iv_eff(raw):
    iv = float(raw) if raw else 8.0
    return iv if iv > 0 else 8.0
class Ledger:
    def __init__(self, paths):
        self.rows = {}; self.conflicts = []; self.src_counts = {}; self.src_first = {}; self.src_cap = {}
        for p in paths:
            led = json.load(open(p))["ledger_tail"]; cnt = {}; first = {}
            for s, rs in led.items():
                cnt[s] = len(rs)
                if rs: first[s] = int(round(float(rs[0][0])))
                d = self.rows.setdefault(s, {})
                for r in rs:
                    ft = int(round(float(r[0]))); rate = float(r[1]); ivr = r[2] if len(r) > 2 else None
                    if ft in d:
                        if d[ft][0] != rate or d[ft][1] != ivr: self.conflicts.append((s, ft, list(d[ft]), [rate, ivr]))
                    else: d[ft] = (rate, ivr)
            self.src_counts[p] = cnt; self.src_first[p] = first; self.src_cap[p] = max(cnt.values()) if cnt else 0
        self.ft = {}; self.rate = {}; self.ivr = {}
        for s, d in self.rows.items():
            k = sorted(d); self.ft[s] = k; self.rate[s] = [d[t][0] for t in k]; self.ivr[s] = [d[t][1] for t in k]
    def at(self, s, A, strict=False):
        """(ft, rate, iv_eff) of the last row with ft <= A (ft < A if strict); None if none."""
        ft = self.ft.get(s)
        if not ft: return None
        k = (bisect.bisect_left(ft, A) if strict else bisect.bisect_right(ft, A)) - 1
        if k < 0: return None
        return ft[k], self.rate[s][k], iv_eff(self.ivr[s][k])
    def truncated_before(self, s, A):
        """True if no merged row <= A exists and the source holding the earliest row for s was at its row cap (tail cut, not unlisted)."""
        if self.at(s, A) is not None: return False
        best = None
        for p, first in self.src_first.items():
            if s in first and (best is None or first[s] < best[0]): best = (first[s], p)
        if best is None: return False
        return self.src_counts[best[1]][s] >= self.src_cap[best[1]]
    def vectors(self, SYM, A):
        """c4, rn8 (panel convention, stale -> NaN), rn8_ftrim (no staleness), iv, ft arrays over SYM at anchor A."""
        n = len(SYM); c4 = np.zeros(n); rn8 = np.full(n, np.nan); rn8f = np.full(n, np.nan); ivv = np.full(n, np.nan); ftv = np.full(n, np.nan)
        for j, s in enumerate(SYM):
            r = self.at(s, A)
            if r is None: continue
            ft, rate, iv = r
            rn8f[j] = rate * (8.0 / iv); ftv[j] = ft; ivv[j] = iv
            if A - ft <= STALE_S:
                c4[j] = rate * (4.0 / iv); rn8[j] = rate * (8.0 / iv)
        return c4, rn8, rn8f, ivv, ftv
def boot_ratio(num, den, days, k, B=2000):
    num = np.asarray(num, float); den = np.asarray(den, float); days = np.asarray(days)
    u, inv = np.unique(days, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sdn = np.bincount(inv, weights=den, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd))
    rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
def utc(t):
    import time
    return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
