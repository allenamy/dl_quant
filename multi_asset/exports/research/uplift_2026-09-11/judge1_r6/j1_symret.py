"""Per-anchor, per-symbol realized simple 4h return and held notional, from the live ledgers (READ-ONLY).
  n1_s = qty_s(post-anchor readback at E) * mid_s(E)      [notional marked at the anchor mid]
  r_s  = mid_s(E+4h)/mid_s(E) - 1                          [realized 4h simple return, order-book mid to mid]
  price P&L = sum_s n1_s * r_s  (identical to sum q(p2-p1))
Saves a symbol-aligned matrix on the replay's 829-symbol order plus an 'other' bucket.
"""
import json, os, time, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
Z = np.load(f'{HERE}/j1_slice.npz', allow_pickle=True)
SYM = [str(s) for s in Z['symbols']]; sidx = {s: i for i, s in enumerate(SYM)}
ts = Z['ts'].astype(np.int64)
def G(t): return int(float(t)//14400)*14400
days = sorted(d for d in os.listdir(BASE) if d.isdigit())
MID = {}; POS = {}
for d in days:
    p = f'{BASE}/{d}/anchors.jsonl'
    if os.path.exists(p):
        for ln in open(p):
            ln = ln.strip()
            if not ln: continue
            try: r = json.loads(ln)
            except Exception: continue
            if r.get('anchor_ts') is None: continue
            mv = r.get('mid_at_anchor_vector'); m = {}
            if isinstance(mv, str):
                try: m = json.loads(mv)
                except Exception: m = {}
            elif isinstance(mv, dict): m = mv
            if m: MID[G(r['anchor_ts'])] = m
    p = f'{BASE}/{d}/position_readback.jsonl'
    if os.path.exists(p):
        for ln in open(p):
            ln = ln.strip()
            if not ln: continue
            try: r = json.loads(ln)
            except Exception: continue
            if r.get('anchor_ts') is None: continue
            q = r.get('venue_position_qty')
            if q is None: continue
            POS.setdefault(G(r['anchor_ts']), {})[r['symbol']] = float(q)
n = len(ts); NW = len(SYM)
N1 = np.zeros((n, NW)); RR = np.full((n, NW), np.nan)
oth_n1 = np.zeros(n); oth_pnl = np.zeros(n); nomid_n1 = np.zeros(n)
have = np.zeros(n, bool)
for i, t in enumerate(ts):
    t = int(t); m1 = MID.get(t); m2 = MID.get(t + 14400); pos = POS.get(t)
    if not (m1 and m2 and pos): continue
    have[i] = True
    for s, q in pos.items():
        p1 = m1.get(s); p2 = m2.get(s)
        if not p1: continue
        v = q * float(p1)
        if abs(v) < 1e-9: continue
        if not p2: nomid_n1[i] += abs(v); continue
        r = float(p2)/float(p1) - 1.0
        j = sidx.get(s)
        if j is None: oth_n1[i] += abs(v); oth_pnl[i] += v*r; continue
        N1[i, j] += v; RR[i, j] = r
np.savez_compressed(f'{HERE}/j1_symret.npz', ts=ts, symbols=np.array(SYM), N1=N1.astype(np.float32),
                    RR=RR.astype(np.float32), oth_n1=oth_n1, oth_pnl=oth_pnl, nomid_n1=nomid_n1, have=have)
print('anchors with mid+mid+pos:', int(have.sum()), '/', n)
print('mean |n1| outside the 829 replay universe, share:',
      float(np.nanmean((oth_n1/(np.abs(N1).sum(1)+oth_n1+nomid_n1))[have])))
print('mean share with no forward mid (delisted/halted):',
      float(np.nanmean((nomid_n1/(np.abs(N1).sum(1)+oth_n1+nomid_n1))[have])))
print('self_sha256', hashlib.sha256(open(__file__,'rb').read()).hexdigest()[:16], 'read_utc', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
