"""Use hash-pinned real admission records; no model, prediction or PNL reads."""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
from sampling import sample_ids


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pins', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    started = time.monotonic()
    raw = args.pins.read_bytes()
    pins = json.loads(raw)
    data = {}
    for name, expected in pins['inputs'].items():
        b = Path(name).read_bytes()
        if digest(b) != expected:
            raise ValueError('input drift: ' + name)
        data[name] = json.loads(b)
    by_id = {(x['arm'], x['seed'], x['fold']): x for x in data.values() if 'arm' in x}
    expected_ids = {(arm, seed, fold) for arm in ('U', 'REPAIR')
                    for seed in (42, 2027) for fold in ('202608', '202609')}
    if set(by_id) != expected_ids or sum('arm' in x for x in data.values()) != 8:
        raise ValueError('missing or duplicate fold identities')
    rows = []
    for seed in (42, 2027):
        for fold in ('202608', '202609'):
            old = by_id['U', seed, fold]['admission']
            new = by_id['REPAIR', seed, fold]['admission']
            ids = [[str(t) for t in r['label_end_times']] for r in (old, new)]
            draws = list(range(96))
            common = set(ids[0]); added = set(ids[1]) - common
            if not common <= set(ids[1]):
                raise ValueError('removal in addition-only probe')
            weights_by_id = [dict(zip(pop, record['probabilities']))
                             for pop, record in zip(ids, (old, new))]
            ratios = [weights_by_id[1][i] / weights_by_id[0][i] for i in sorted(common)]
            if not all(math.isfinite(r) and math.isclose(r, ratios[0], rel_tol=1e-12)
                       for r in ratios):
                raise ValueError('old relative weights changed: stability premise absent')
            old_actual = [ids[0][i] for i in old['sampled_windows']]
            new_actual = [ids[1][i] for i in new['sampled_windows']]
            if len(old_actual) != 96 or len(new_actual) != 96:
                raise ValueError('unexpected recorded update count')
            result = []
            stream = 'F10/' + fold
            for pop, record in zip(ids, (old, new)):
                weights = record['probabilities']
                sampled = sample_ids(pop, weights, seed=seed, stream=stream, draw_ids=draws)
                if sampled != sample_ids(pop[::-1], weights[::-1], seed=seed, stream=stream, draw_ids=draws):
                    raise ValueError('actual population order dependency')
                first = sample_ids(pop, weights, seed=seed, stream=stream, draw_ids=draws[:31])
                tail = sample_ids(pop, weights, seed=seed, stream=stream, draw_ids=draws[31:])
                if sampled != first + tail:
                    raise ValueError('actual population resume differs')
                result.append(sampled)
            count = lambda a, b: sum(x != y and y in common for x, y in zip(a, b))
            new_old_switches = count(*result)
            if new_old_switches:
                raise ValueError('stable coupling changed old winner')
            rows.append({'seed': seed, 'fold': fold, 'updates': len(draws),
                         'recorded_CDF_old_to_other_old_updates': count(old_actual, new_actual),
                         'stable_old_to_other_old_updates': new_old_switches,
                         'stable_new_window_updates': sum(y in added for y in result[1]),
                         'common_weight_ratio_minmax': [min(ratios), max(ratios)],
                         'stable_sampled_ids_sha256': [digest(json.dumps(q).encode()) for q in result],
                         'stable_sampled_ids': result})
    output = {'status': 'REAL_ADMISSION_COUPLING_VERIFIED_NO_TRAINING',
              'utc': time.strftime('%FT%TZ', time.gmtime()), 'rows': rows,
              'inputs': pins['inputs'], 'pin_record_sha256': digest(raw),
              'source_sha256': digest(Path(__file__).read_bytes()),
              'sampler_sha256': digest(Path(__file__).with_name('sampling.py').read_bytes()),
              'python': sys.executable, 'numpy': np.__version__, 'seconds': time.monotonic() - started,
              'limits': 'A new offline sampling algorithm, not a patch to frozen results. Identical distributions do not imply identical model fits, lower economic variance, or improved performance.'}
    with args.output.open('x') as f:
        json.dump(output, f, indent=2, allow_nan=False)
    print(json.dumps({**output, 'inputs': len(output['inputs']), 'rows': [{k:v for k,v in x.items() if k!='stable_sampled_ids'} for x in rows]}))


if __name__ == '__main__':
    main()
