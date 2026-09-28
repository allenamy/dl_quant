"""Read-only pooled quantity audit. No live imports, credentials, APIs or arm outcomes."""
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def dec(x):
    v = Decimal(str(x))
    if not v.is_finite():
        raise ValueError('nonfinite quantity/price')
    return v


def audit(live):
    sources = {}

    def read(path):
        raw = path.read_bytes()
        sources[str(path)] = hashlib.sha256(raw).hexdigest()
        return raw.decode('utf-8')

    phases = []
    log = read(live / 'state/anchor_runs.log')
    for line in log.splitlines():
        if not line.startswith(('2026-09-27T', '2026-09-28T')):
            continue
        for phase in ('A', 'C'):
            marker = 'phase_' + phase + ': '
            if marker in line:
                phases.append((line.split()[0], phase, json.loads(line.split(marker, 1)[1])))
    positions, fills = [], []
    for day in ('20260927', '20260928'):
        root = live / 'state/live/pilot_log' / day
        positions.extend(json.loads(x) for x in read(root / 'position_readback.jsonl').splitlines() if x.strip())
        fills.extend(json.loads(x) for x in read(root / 'fills.jsonl').splitlines() if x.strip())
    snapshots = defaultdict(dict)
    for row in positions:
        if row['read_ts'] < 1790524800:
            continue
        key = (row['anchor_ts'], row['read_ts'])
        name = row['symbol']
        financial = (dec(row['venue_position_qty']), dec(row['venue_position_notional']))
        if name in snapshots[key] and snapshots[key][name] != financial:
            raise ValueError('conflicting same-read snapshot')
        snapshots[key][name] = financial
    ordered = sorted(snapshots, key=lambda x: x[1])
    unique, repeats = {}, 0
    for row in fills:
        if row['fill_ts'] < ordered[0][1]:
            continue
        if row.get('trade_id') is None:
            raise ValueError('missing trade identity')
        key = (row['symbol'], str(row['trade_id']))
        fin = (dec(row['fill_ts']), row['side'].lower(), dec(row['fill_px']), dec(row['fill_notional']))
        if fin[2] <= 0 or fin[3] < 0 or fin[1] not in ('buy', 'sell'):
            raise ValueError('invalid execution financial fields')
        if key in unique:
            if unique[key] != fin:
                raise ValueError('conflicting same-trade quantity fields')
            repeats += 1
        unique[key] = fin
    intervals = []
    for left, right in zip(ordered, ordered[1:]):
        start, end = snapshots[left], snapshots[right]
        changes = defaultdict(Decimal)
        nfill = 0
        ties = 0
        for (name, tid), (ts, side, px, amount) in unique.items():
            if ts in (dec(left[1]), dec(right[1])):
                ties += 1
            if dec(left[1]) < ts <= dec(right[1]):
                changes[name] += amount / px * (1 if side == 'buy' else -1)
                nfill += 1
        rows = []
        for name in sorted(set(start) | set(end) | set(changes)):
            q1, n1 = start.get(name, (Decimal(0), Decimal(0)))
            q2, n2 = end.get(name, (Decimal(0), Decimal(0)))
            residual = q2 - q1 - changes[name]
            mark = abs(n2 / q2) if q2 else (abs(n1 / q1) if q1 else None)
            tol = Decimal('1e-8') * max(Decimal(1), abs(q1), abs(q2))
            rows.append(dict(symbol=name, start_qty=str(q1), end_qty=str(q2),
                             signed_fill_qty=str(changes[name]), residual_qty=str(residual),
                             residual_usdt=float(residual * mark) if mark is not None else None,
                             quantity_changed=q1 != q2, within_numeric_tolerance=abs(residual) <= tol,
                             explicit_start=name in start, explicit_end=name in end))
        # Observation marker is supplied by the writer, not inferred from row count.
        evidence = []
        for anchor, readts in (left, right):
            matching = [(ts, d) for ts, phase, d in phases if phase == 'C'
                        and d.get('book_observation', {}).get('anchor_ts') == anchor]
            evidence.append([dict(log_ts=ts, book_observation=d.get('book_observation'),
                                  rows=d.get('position_readback_rows')) for ts, d in matching])
        intervals.append(dict(start_anchor=left[0], start_read_ts=left[1], end_anchor=right[0],
                              end_read_ts=right[1], start_names=len(start), end_names=len(end),
                              unique_fills=nfill, endpoint_ties=ties, n_names=len(rows),
                              n_quantity_residuals=sum(not r['within_numeric_tolerance'] for r in rows),
                              max_abs_residual_usdt=max((abs(r['residual_usdt']) for r in rows
                                                        if r['residual_usdt'] is not None), default=None),
                              missing_two_endpoints=[r['symbol'] for r in rows
                                                     if not r['explicit_start'] and not r['explicit_end']],
                              observation_evidence=evidence, rows=rows))
    notices = []
    for ts, phase, d in phases:
        if phase == 'A' and ts.startswith('2026-09-28T04:'):
            notices.append(dict(log_ts=ts, summary=d.get('reconcile_summary'), sample=d.get('reconciled')))
    return dict(utc=datetime.now(timezone.utc).isoformat(), sources=sources,
                pooled_only=True, repeat_fill_rows_collapsed=repeats, intervals=intervals,
                phase_A_notices=notices,
                limits=['No venue API; validates recorded endpoints against local fills, not foreign-order absence.',
                        'Absent endpoint zeros rely on full writer observation and universe contract; inspect evidence.',
                        'Phase A logs only first ten outliers; this does not prove all 39 price-only.',
                        'Numeric tolerance is rounding allowance, not a trading risk threshold.'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    result = audit(Path(args.live))
    Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'intervals': [{k: v for k, v in x.items() if k not in ('rows', 'observation_evidence')}
                                   for x in result['intervals']],
                      'observation_evidence': [x['observation_evidence'] for x in result['intervals']]}))
