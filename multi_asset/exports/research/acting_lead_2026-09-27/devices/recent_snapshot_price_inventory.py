"""Inventory exact anchor-end prices in archived producer states. No targets/PnL.

Endpoint availability does not certify all 48 intervening raw bars. This file
must not be substituted for the simulator's 5m raw price path or training y4s.
Only named snapshot files are read; there are no exchange or production writes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(root, first, last):
    out = {"schema": "archived_anchor_endpoints_inventory/1",
           "utc": datetime.now(timezone.utc).isoformat(),
           "scope": "raw_close_endpoints_only_not_training_labels_or_cash_replay",
           "source_sha256": sha(Path(__file__).read_bytes()),
           "requested_first": first, "requested_last": last, "rows": [], "missing": []}
    for anchor in range(first, last + 1, 14400):
        p = root / str(anchor)
        if not p.is_dir():
            out["missing"].append({"anchor": anchor, "reason": "snapshot_directory_absent"})
            continue
        # An incomplete or conflicting snapshot is a failure, never an empty book.
        complete = (p / 'COMPLETE').read_bytes()
        manifest = (p / 'SHA256SUMS').read_bytes()
        hashes = {}
        for line in manifest.decode().splitlines():
            digest, name = line.split()
            if name in hashes or '/' in name or len(digest) != 64:
                raise ValueError('ambiguous snapshot manifest')
            hashes[name] = digest
        raw = (p / 'aux.json').read_bytes()
        if sha(raw) != hashes.get('aux.json'):
            raise ValueError('aux snapshot content mismatch')
        a = json.loads(raw)
        if a.get('last_anchor') != anchor or a.get('prev_rec', {}).get('anchor_ts') != anchor:
            raise ValueError('aux anchor identity mismatch')
        prices, unavailable = {}, {}
        for sym, value in a['prev_close'].items():
            ts = a.get('prev_close_ts', {}).get(sym)
            if ts != anchor:
                unavailable[sym] = 'raw_close_timestamp_not_anchor'
            elif type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                unavailable[sym] = 'raw_close_unknown_or_invalid'
            else:
                prices[sym] = value
        out['rows'].append({'anchor': anchor, 'snapshot_path': str(p),
            'aux_sha256': sha(raw), 'manifest_sha256': sha(manifest),
            'complete_sha256': sha(complete), 'complete_record': complete.decode().strip(),
            'fresh_raw_close': prices, 'unknown': unavailable,
            'n_prices': len(prices), 'n_unknown': len(unavailable)})
    out['n_rows'] = len(out['rows'])
    out['n_missing'] = len(out['missing'])
    out['n_fresh_endpoints'] = sum(r['n_prices'] for r in out['rows'])
    out['status'] = 'INVENTORY_WITH_GAPS' if out['missing'] else 'ENDPOINT_INVENTORY_COMPLETE_NOT_EVALUATION_READY'
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--first', type=int, required=True)
    p.add_argument('--last', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.first % 14400 or a.last % 14400 or a.last < a.first:
        raise ValueError('invalid 4h scope')
    result = build(a.root, a.first, a.last)
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print({k: result[k] for k in ('status','n_rows','n_missing','n_fresh_endpoints')})
