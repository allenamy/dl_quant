#!/usr/bin/env python3
"""Funding/carry audit of the live wide book.  READ-ONLY on the live tree.

Sources
  /Users/haosiyu/dl_quant_live/state/live/pilot_log/<day>/funding.jsonl   (venue FUNDING_FEE cash + our readback notional)
  /Users/haosiyu/dl_quant_live/state/live/pilot_log/<day>/anchors.jsonl   (realized_gross per anchor)
  /Users/haosiyu/dl_quant_live/state/live/pilot_log/<day>/daily_nav.jsonl (income-ledger cross-check)

Anchor attribution: a settlement at time s is a cost of the book established at the previous
4h anchor, so bucket(s) = floor((s-1)/14400)*14400.  A settlement at exactly HH:00 therefore
lands on the (HH-4) anchor.
"""
import json, glob, os, collections, datetime, math, sys

LOG = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
H4 = 14400

def load_funding():
    rows = []
    for f in sorted(glob.glob(LOG + '/*/funding.jsonl')):
        for l in open(f):
            if l.strip():
                rows.append(json.loads(l))
    return rows

def load_anchors():
    A = {}
    for f in sorted(glob.glob(LOG + '/*/anchors.jsonl')):
        for l in open(f):
            if not l.strip(): continue
            r = json.loads(l)
            b = int(r['anchor_ts'] // H4) * H4
            g = r.get('realized_gross') or 0.0
            # keep the larger realized_gross if a bucket has two rows (08-02 retry)
            if b not in A or g > A[b]['gross']:
                A[b] = {'gross': g, 'target_gross': r.get('target_gross'),
                        'regime': r.get('regime_at_anchor')}
    return A

def bucket(ts):
    return int((ts - 1) // H4) * H4

def fmt(b):
    return datetime.datetime.utcfromtimestamp(b).strftime('%Y-%m-%d %HZ')

def main():
    rows = load_funding()
    A = load_anchors()
    # gross for a bucket, falling back to the nearest earlier anchor with a gross
    ks = sorted(A)
    def gross_at(b):
        if b in A and A[b]['gross']: return A[b]['gross'], 'realized'
        prev = [k for k in ks if k <= b and A[k]['gross']]
        if prev: return A[prev[-1]]['gross'], 'carried'
        return None, 'none'

    per = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rows:
        b = bucket(r['settlement_ts'])
        n = r['position_notional_at_settlement']
        p = r['funding_paid']
        iv = r.get('funding_interval_h')
        d = per[b]
        d['paid'] += p
        d['n'] += 1
        if n > 0:
            d['paid_long'] += p; d['notl_long'] += n
        else:
            d['paid_short'] += p; d['notl_short'] += -n
        key = 'iv%s' % (iv if iv in (1, 4, 8) else 'X')
        d['paid_' + key] += p
        d['notl_' + key] += abs(n)
    return rows, A, per, gross_at

if __name__ == '__main__':
    rows, A, per, gross_at = main()
    print('# anchors with funding rows: %d ; funding rows: %d' % (len(per), len(rows)))
