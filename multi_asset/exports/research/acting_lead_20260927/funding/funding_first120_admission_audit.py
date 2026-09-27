"""Recover the preregistered first NC admission window; no scores/returns reported."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import pathlib
import resource
import subprocess
import time

G = 2**30
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS, (2*G, 2*G))
resource.setrlimit(resource.RLIMIT_CPU, (240, 250))
START = time.monotonic()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def utc(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); args = ap.parse_args()
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=False)
    current = int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
    maximum = int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())
    rss = sum(int(v) for v in subprocess.check_output(['ps', '-u', str(os.getuid()), '-o', 'rss='], text=True).split()) * 1024
    gate = {'utc': utc(time.time()), 'free_bytes': maximum-current, 'same_uid_rss_bytes': rss,
            'rss_budget_bytes': 2*G, 'spare_bytes': 8*G, 'cpu_count': 1,
            'pass': maximum-current >= 10*G and rss+2*G <= 30*G}
    (out/'RESOURCE_GATE.json').write_text(json.dumps(gate, indent=2))
    if not gate['pass']: raise SystemExit('RESOURCE_REFUSED_NO_ARRAY_READ')
    probe = out/'quota_probe.bin'
    with probe.open('wb') as f: f.write(b'\0'*65536); f.flush(); os.fsync(f.fileno())
    assert probe.stat().st_size == 65536; probe.unlink()
    import numpy as np
    nc = pathlib.Path('/dev/shm/news2_2026-09-23')
    paths = {'features': nc/'work/NEWS_FEATURES.npz', 'legs': nc/'work/legs.npz',
             'labels': pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'),
             'admission': nc/'work/f10_s42/202608/ADMISSION.json', 'predicate': nc/'devices/f10_observability.py',
             'd10_king': pathlib.Path('/workspace/dlarch_2026-09-24/chain/d10rr_s42/work/king/KING_OOF.npz'),
             'd10_f10': pathlib.Path('/workspace/dlarch_2026-09-24/chain/d10rr_s42/work/f10_s42/F10_OOF.npz')}
    pins = {k: {'path': str(p), 'sha256': sha(p)} for k, p in paths.items()}
    assert pins['features']['sha256'] == '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8'
    assert pins['legs']['sha256'] == '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65'
    assert pins['labels']['sha256'] == 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
    assert pins['admission']['sha256'] == 'e67c02d7339da5bbf545ac13f73a9484dfe16309e546bc3191b780daff03c19b'
    assert pins['d10_king']['sha256'] == '6579bc4e390493a31873d790bdbc366c48bfddc9c06b79c24eef73bc8b911e18'
    assert pins['d10_f10']['sha256'] == '081bd6e60895f76ee8f1dfd1c47347305d0139ad674638360ccb15d02e261411'
    spec = importlib.util.spec_from_file_location('original_f10_observability', paths['predicate'])
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    original = json.loads(paths['admission'].read_text())
    with np.load(paths['features']) as z:
        a, syms, off, members_flat = z['anchors'], z['symbols'], z['off'], z['m']
    members = [members_flat[int(off[i]):int(off[i+1])] for i in range(len(a))]
    with np.load(paths['legs']) as z:
        assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
        ready = z['ready']
    with np.load(paths['labels'], allow_pickle=True) as z:
        ya = z['E_ts']; assert np.array_equal(z['symbols'], syms)
        valid = np.isfinite(z['y4s'])
    ix = np.searchsorted(ya, a); aligned = (ix < len(ya)) & (ya[np.minimum(ix, len(ya)-1)] == a)
    y = np.full((len(a), len(syms)), np.nan, dtype=np.float16)
    y[aligned] = np.where(valid[ix[aligned]], 0., np.nan); del valid
    cutoff = original['cutoff']
    tr = np.flatnonzero((a+14400 <= cutoff) & ready & (np.diff(off) >= 50))
    tr1 = tr[:int(len(tr)*.85)]
    accepted, rejected = [], collections.Counter()
    for s in range(int(tr1[0])+24, int(tr1[-1])-96, 48):
        span = np.arange(s-24, s+96); ok, why = mod.span_admissible(members, y, span, ready)
        if ok: accepted.append(span)
        else: rejected[why['reason']] += 1
    assert len(accepted) == original['accepted_windows'] == 149
    assert dict(rejected) == original['rejected']
    assert len(tr1) == original['train_anchors'] and int(a[tr1[-1]]+14400) == original['max_train_label_end']
    span = accepted[0]; start, end = int(a[span[0]]), int(a[span[-1]]+14400)
    support = {}
    for key in ('d10_king', 'd10_f10'):
        with np.load(paths[key]) as z:
            keys = z.files; pa = z['E_ts']; ps = z['symbols']; assert np.array_equal(ps, syms)
            matrix_keys = [k for k in ('P', 'pred', 'score', 'Z') if k in keys]
            assert len(matrix_keys) == 1, (key, keys)
            pk = matrix_keys[0]; finite = np.isfinite(z[pk])
        assert finite.shape == (len(pa), len(syms))
        any_rows = np.flatnonzero(finite.any(1))
        pi = np.searchsorted(pa, a[span]); onaxis = (pi < len(pa)) & (pa[np.minimum(pi, len(pa)-1)] == a[span])
        counts = [int(finite[pi[k], members[i]].sum()) if onaxis[k] else 0 for k, i in enumerate(span)]
        support[key] = {'keys': keys, 'score_field': pk, 'axis_first': int(pa[0]), 'axis_last': int(pa[-1]),
                        'axis_first_utc': utc(pa[0]), 'first_any_finite': int(pa[any_rows[0]]) if len(any_rows) else None,
                        'first_any_finite_utc': utc(pa[any_rows[0]]) if len(any_rows) else None,
                        'first120_on_axis': int(onaxis.sum()), 'first120_finite_member_counts': counts,
                        'first120_total_member_cells': sum(len(members[i]) for i in span),
                        'first120_finite_member_cells': sum(counts)}
    result = {'status': 'ORIGINAL_FIRST120_SUPPORT_AUDIT', 'utc': utc(time.time()), 'source_sha256': sha(__file__),
              'inputs': pins, 'original_admission': original, 'reconstructed_accepted': len(accepted),
              'reconstructed_rejected': dict(rejected), 'first120': {'rows': span.tolist(), 'anchors': a[span].tolist(),
              'first_A': start, 'first_A_utc': utc(start), 'terminal_B': end, 'terminal_B_utc': utc(end)},
              'support': support, 'producer_state_origin': 1672531200,
              'original_contract_status': 'UNAVAILABLE_BEFORE_FULL_BOOK_STATE_ORIGIN' if start < 1672531200 else 'SUPPORT_REQUIRES_REVIEW',
              'no_return_or_score_aggregate': True, 'no_window_reselection': True, 'no_simulator_or_training': True,
              'elapsed_seconds': time.monotonic()-START, 'rss_peak_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    (out/'RESULT.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({k: result[k] for k in ('original_contract_status','elapsed_seconds','rss_peak_bytes','first120','support')}, indent=2))


if __name__ == '__main__': main()
