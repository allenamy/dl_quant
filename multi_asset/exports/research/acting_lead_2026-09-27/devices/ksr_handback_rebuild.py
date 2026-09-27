"""Rebuild unchanged, source-pinned combo code to explain a saved publication fork.
Engineering diagnostic only. One CPU, no training, no execution simulator.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    args = ap.parse_args(); out = Path(args.out); out.mkdir(exist_ok=False)
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *args: (_ for _ in ()).throw(TimeoutError('300s original deadline')))
    signal.alarm(300)
    pins = {}
    try:
        assert os.environ['NPY_DISABLE_CPU_FEATURES'] == 'X86_V4 AVX512_ICL AVX512_SPR'
        assert os.environ['OMP_NUM_THREADS'] == os.environ['OPENBLAS_NUM_THREADS'] == '1'
        cg = Path('/sys/fs/cgroup')
        assert int((cg/'memory.max').read_text()) - int((cg/'memory.current').read_text()) >= 5 * 2**30
        resource.setrlimit(resource.RLIMIT_AS, (4 * 2**30, 4 * 2**30))
        import numpy as np
        root = Path('/dev/shm/mretrain_2026-09-26'); D = root/'devices'
        role_paths = {'BASE': root/'arms/A0_m0', 'COMP': root/'arms/KSR_COMP_ONLY_m0'}
        recs = {}
        for seed in (42, 2027):
            for role, w in role_paths.items():
                p = w/f'work/combo_s{seed}/TARGET_RECEIPT.json'
                pins[str(p)] = sha(p); r = json.loads(p.read_text()); recs[seed, role] = r
                assert r['seed'] == seed and r['state_init'] == 'zero at 2023-01-01; hypothetical common start, not live archived state'
                for source, expected in r['sources'].items():
                    assert sha(source) == expected, source; pins[source] = expected
                for source, expected in r['inputs'].items():
                    p = Path(source)
                    if p.name == 'legs.npz':
                        p = Path('/workspace/ksr_2026-09-27/legs') / ('KSR_S0_m0.npz' if role=='BASE' else 'KSR_COMP_ONLY_m0.npz')
                    if str(p) not in pins:
                        assert sha(p) == expected, str(p); pins[str(p)] = expected
                    assert pins[str(p)] == expected
        sys.path.insert(0, str(D))
        import continuous_combo as CC
        import book_universe as BU
        for mod in (CC, BU):
            assert sha(mod.__file__) == recs[42, 'BASE']['sources'][mod.__file__]
        w = role_paths['BASE']
        with np.load(w/'work/NEWS_FEATURES.npz', allow_pickle=False) as F:
            a = F['anchors']; syms = F['symbols']; off = F['off']; mem = F['m']
        use = (a >= 1672531200) & (a < 1740787200)  # original start, strictly before 2025-03-01
        au = a[use]; assert np.all(np.diff(au) == 14400)
        members = [mem[off[i]:off[i+1]].astype(np.int64) for i in np.flatnonzero(use)]
        with np.load('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz', allow_pickle=False) as z:
            assert np.array_equal(z['ts'], a); mask = z['mask'][use]
        with np.load(w/'receipts/P1_members_2025H2on.npz', allow_pickle=False) as z: crypto=z['crypto']
        with np.load(BU.PATH, allow_pickle=False) as z: legal=BU.align(au, syms, z) & mask & crypto[None, :]
        params = json.loads((w/'inputs/bundle_config.json').read_text())['params']
        rows, controls = {}, {}
        trace = (au >= 1735603200) & (au <= 1735862400)
        for seed in (42, 2027):
            with np.load(f'/dev/shm/news2_2026-09-23/work/f10_s{seed}/F10_OOF.npz', allow_pickle=False) as z:
                assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
                f10 = z['P'][use].astype(np.float64)
            for role in ('BASE', 'COMP'):
                name = 'KSR_S0_m0' if role=='BASE' else 'KSR_COMP_ONLY_m0'
                with np.load(f'/workspace/ksr_2026-09-27/legs/{name}.npz', allow_pickle=False) as z:
                    assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
                    v = {k: z[k][use].astype(np.float64) for k in ('KZ','ZFD','WL','RN8','QV')}; ready=z['ready'][use]
                o = CC.evolve(au,v['KZ'],f10,v['ZFD'],v['WL'],v['RN8'],members,v['QV'],legal,ready,params,'scaled_diagnostic')
                p = Path(f'/workspace/ksr_2026-09-27/targets_stats/{name}_s{seed}.npz')
                mr = json.loads(p.with_suffix('.json').read_text()); assert sha(p)==mr['out_sha256']; pins[str(p)]=mr['out_sha256']
                with np.load(p, allow_pickle=False) as z:
                    idx=np.searchsorted(z['anchors'],au); assert np.array_equal(z['anchors'][idx],au)
                    k=z['scaled_kind'][idx]; g=z['gross'][idx]
                kind=np.where(o['trade_mask'],2,0); err=float(np.max(np.abs(np.abs(o['weights']).sum(1)-g)))
                assert np.array_equal(kind,k), (seed,role,'publication mismatch')
                assert err <= 1e-12, (seed,role,'gross mismatch',err)
                controls[f'{role}_s{seed}']={'publication_exact':True,'n':len(au),'max_gross_diff':err}
                rr=[]
                for i in np.flatnonzero(trace):
                    rr.append({'utc':dt.datetime.fromtimestamp(int(au[i]),dt.timezone.utc).isoformat(),
                      'gross_raw':float(np.abs(o['raw'][i]).sum()),'names':int((np.abs(o['raw'][i])>1e-9).sum()),
                      'kc_gross':float(np.abs(o['kc'][i]).sum()),'fc_gross':float(np.abs(o['fc'][i]).sum()),
                      'reason':str(o['reason'][i]),'publish':bool(o['trade_mask'][i])})
                rows[f'{role}_s{seed}']=rr
                print('CELL_VERIFIED',role,seed,'seconds',round(time.monotonic()-start,1),flush=True)
                del o,v
            del f10
        result={'status':'SOURCE_REBUILD_DIAGNOSTIC','utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                'self_sha256':sha(__file__),'python':sys.executable,'numpy':np.__version__,'controls':controls,'trace':rows,
                'pins':pins,'seconds':time.monotonic()-start,'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'not_claimed':['No per-path holdings/cash attribution.','No new model or deployment decision.']}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print('DIAGNOSTIC_DONE',sha(out/'RESULT.json'),flush=True)
    except BaseException as e:
        (out/'FAILED.json').write_text(json.dumps({'type':type(e).__name__,'reason':str(e),'seconds':time.monotonic()-start})+'\n')
        raise


if __name__ == '__main__':main()
