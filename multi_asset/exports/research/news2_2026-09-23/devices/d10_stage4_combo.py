#!/usr/bin/env python3
"""d10_stage4_combo.py {identity|d10} -- line D stage 4: the researcher's continuous_combo.evolve (IMPORTED from the news2 root,
UNCHANGED) on the stage-2/3 inputs. news2_combo.py cannot be pointed at other inputs (it asserts the F10 TRAIN_RECEIPT input shas),
so this driver repeats its input wiring (news2_combo.py L33-L60) with the input PATHS as arguments -- the shape of
pnoise_ladder_combo.py. Only the four swapped arrays differ between modes: legs (KZ/ZFD/WL/RN8/QV/ready), F10 score, members
(asserted identical to NEWS_FEATURES -- stage 2c G2), everything else (mask, crypto, universe, config) is the same file.
  identity : original inputs -> literal.npz and scaled_diagnostic.npz must equal combo_s42's BITWISE on every key, else STOP.
  d10      : refuses unless the identity receipt is BITWISE.
Executor (protocol s10-f): news2, on pod2 under setsid; one process per mode.
"""
import argparse, collections, datetime, hashlib, json, os, pathlib, sys
import numpy as np

W = pathlib.Path('/dev/shm/news2_2026-09-23'); sys.path.insert(0, str(W / 'devices'))
from continuous_combo import evolve
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA

MASK = pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def bits(x, y):
    if x.shape != y.shape or x.dtype != y.dtype: return -1
    if x.dtype.kind == 'f':
        v = np.uint64 if x.itemsize == 8 else np.uint32
        return int((~((x.view(v) == y.view(v)) | (np.isnan(x) & np.isnan(y)))).sum())
    return int((x != y).sum())


def run(features, legs, score, out):
    F = np.load(features); leg = np.load(legs); sc = np.load(score); a = F['anchors'].astype(np.int64); syms = F['symbols']
    for z in (leg, sc): assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
    mk = np.load(MASK); assert np.array_equal(mk['ts'].astype(np.int64), a)
    crypto = np.load(W / 'receipts/P1_members_2025H2on.npz')['crypto']; cand = mk['mask'] & crypto[None, :]
    off = F['off']; members = [F['m'][off[i]:off[i + 1]].astype(np.int64) for i in range(len(a))]
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe['ts'][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    config = json.loads((W / 'inputs/bundle_config.json').read_text())
    mem_u = [members[i] for i in np.flatnonzero(use)]
    out.mkdir(parents=True, exist_ok=False); summ = {}
    for policy in ('literal', 'scaled_diagnostic'):
        r = evolve(au, leg['KZ'][use].astype(np.float64), sc['P'][use].astype(np.float64), leg['ZFD'][use].astype(np.float64), leg['WL'][use].astype(np.float64),
                   leg['RN8'][use].astype(np.float64), mem_u, leg['QV'][use].astype(np.float64), book_legal, leg['ready'][use], config['params'], policy)
        p = out / (policy + '.npz'); np.savez_compressed(p, E_ts=au, symbols=syms, **r)
        summ[policy] = {'path': str(p), 'sha': sha(p), 'reasons': dict(collections.Counter(r['reason']))}
    return summ


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['identity', 'd10']); ap.add_argument('--out', required=True)
    ap.add_argument('--features'); ap.add_argument('--legs'); ap.add_argument('--score'); ap.add_argument('--identity-receipt')
    a = ap.parse_args(); out = pathlib.Path(a.out)
    rec = {'device_sha256': sha(os.path.abspath(__file__)), 'continuous_combo_sha256': sha(W / 'devices/continuous_combo.py'), 'mode': a.mode,
           'utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
    if a.mode == 'identity':
        f, l, s = W / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'work/f10_s42/F10_OOF.npz'
    else:
        ir = json.load(open(a.identity_receipt)); assert ir.get('VERDICT') == 'BITWISE', 'identity not BITWISE: refused'
        f, l, s = pathlib.Path(a.features), pathlib.Path(a.legs), pathlib.Path(a.score)
    rec['inputs'] = {str(p): sha(p) for p in (f, l, s, MASK, W / 'receipts/P1_members_2025H2on.npz', W / 'inputs/bundle_config.json', pathlib.Path(UNIVERSE_PATH))}
    summ = run(f, l, s, out); rec['policies'] = summ
    if a.mode == 'identity':
        ref = W / 'work/combo_s42'; cmp_ = {}
        for policy in ('literal', 'scaled_diagnostic'):
            X, Y = np.load(out / (policy + '.npz'), allow_pickle=True), np.load(ref / (policy + '.npz'), allow_pickle=True)
            cmp_[policy] = {k: (bits(X[k], Y[k]) if X[k].dtype.kind != 'O' and X[k].dtype.kind != 'U' else int(not np.array_equal(X[k], Y[k]))) for k in Y.files}
            cmp_[policy]['_keys_equal'] = sorted(X.files) == sorted(Y.files)
        rec['identity_vs_combo_s42'] = cmp_
        rec['VERDICT'] = 'BITWISE' if all(v == 0 or v is True for d in cmp_.values() for v in d.values()) else 'DIFFERS'
        print('COMBO_IDENTITY', rec['VERDICT'], json.dumps(cmp_), flush=True)
    with open(out / 'STAGE4_RECEIPT.json', 'w') as fh:
        fh.write(json.dumps(rec, indent=1)); fh.flush(); os.fsync(fh.fileno())
    print('STAGE4_DONE', a.mode, json.dumps({k: v['sha'][:12] for k, v in summ.items()}), flush=True)


if __name__ == '__main__':
    main()
