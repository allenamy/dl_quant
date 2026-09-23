"""FRESH P4 combo targets — news_combo.py with ONLY the roots changed (PREREG_fresh_models_newS_2026-09-23.md §1:
the combo is rebuilt from FRESH's own King OOF / legs / F10 OOF; the evolve/step kernels, the publication policies,
the universe and the state start are byte-for-byte news_combo.py).
  NEW_S root (READ-ONLY): NEWS_FEATURES.npz, inputs/bundle_config.json, receipts/P1_members_2025H2on.npz, vendor_live/fea171/combo_stage.py
  FRESH root            : work/legs.npz, receipts/P3_LEGS.json, work/f10_s<seed>/, work/combo_s<seed>/ (output)
usage: python fresh_combo.py --seed 42|2027
"""
import os, sys, json, argparse, collections, datetime, pathlib, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from continuous_combo import evolve, verify_training
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
import combo_target

W = pathlib.Path('/dev/shm/fresh_2026-09-23')
N = pathlib.Path('/dev/shm/news_2026-09-23')      # NEW_S root: READ-ONLY frozen inputs
PREREG = {'path': 'docs/PREREG_fresh_models_newS_2026-09-23.md', 'commit': 'b6e682e0a'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, choices=(42, 2027), required=True); args = ap.parse_args()
    froot = W / f'work/f10_s{args.seed}'
    paths = [N / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'receipts/P3_LEGS.json', froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', N / 'inputs/bundle_config.json',
             N / 'receipts/P1_members_2025H2on.npz', pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]
    ident = {str(p): sha(p) for p in paths}
    rec = json.loads(paths[4].read_text()); lr = json.loads(paths[2].read_text())
    assert rec['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256'] == ident[str(paths[3])]
    verify_training(froot, rec, args.seed, sha)
    assert set(rec['folds']) == set(rec['expected_folds'])
    for p, h in rec['inputs'].items(): assert sha(p) == h, ('training input drift', p)
    for p, h in rec['sources'].items(): assert sha(p) == h, ('training source drift', p)
    assert ident[str(paths[1])] == lr['sha256']
    F = np.load(paths[0]); leg = np.load(paths[1]); score = np.load(paths[3]); a = F['anchors'].astype(np.int64); syms = F['symbols']
    for z in (leg, score): assert np.array_equal(z['E_ts'], a) and np.array_equal(z['symbols'], syms)
    mk = np.load(paths[7]); assert np.array_equal(mk['ts'].astype(np.int64), a)
    crypto = np.load(paths[6])['crypto']; cand = mk['mask'] & crypto[None, :]
    off = F['off']; members = [F['m'][off[i]:off[i + 1]].astype(np.int64) for i in range(len(a))]
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, 'universe content identity'
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe['ts'][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    ident[UNIVERSE_PATH] = UNIVERSE_SHA
    config = json.loads(paths[5].read_text())
    sources = {str(p): sha(p) for p in [pathlib.Path(__file__), pathlib.Path(HERE) / 'continuous_combo.py', pathlib.Path(HERE) / 'combo_target.py', pathlib.Path(HERE) / 'book_universe.py',
                                          N / 'vendor_live/fea171/combo_stage.py']}
    out = W / f'work/combo_s{args.seed}'; out.mkdir(exist_ok=False)
    mem_u = [members[i] for i in np.flatnonzero(use)]
    # members outside the book universe: counted (they can hold no weight: LIVE_MASK False ⇒ chain's keep excludes them)
    outside = int(sum(int((~book_legal[k][m]).sum()) for k, m in enumerate(mem_u)))
    summary = {}
    for policy in ('literal', 'scaled_diagnostic'):
        result = evolve(au, leg['KZ'][use].astype(np.float64), score['P'][use].astype(np.float64), leg['ZFD'][use].astype(np.float64), leg['WL'][use].astype(np.float64),
                        leg['RN8'][use].astype(np.float64), mem_u, leg['QV'][use].astype(np.float64), book_legal, leg['ready'][use], config['params'], policy)
        p = out / (policy + '.npz'); tmp = out / (policy + '.tmp.npz'); np.savez_compressed(tmp, E_ts=au, symbols=syms, **result); tmp.replace(p)
        counts = dict(collections.Counter(result['reason'])); years = {}
        yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in au])
        for y in np.unique(yr):
            m = yr == y; years[str(y)] = {'anchors': int(m.sum()), 'publish': int(result['trade_mask'][m].sum()), 'mean_producer_gross': float(np.abs(result['raw'][m]).sum(1).mean())}
        summary[policy] = {'path': str(p), 'sha': sha(p), 'reasons': counts, 'years': years}
    for p, h in ident.items(): assert sha(p) == h
    for p, h in sources.items(): assert sha(p) == h
    receipt = {'status': 'FRESH_TARGETS_NOT_EXECUTION_PNL', 'seed': args.seed, 'prereg': PREREG, 'inputs': ident, 'sources': sources, 'policies': summary,
               'member_cells_outside_book_universe': outside,
               'state_init': 'zero at 2023-01-01; hypothetical common start, not live archived state',
               'hold_contract': 'trade_mask False = maintain quantities, never King substitution',
               'fresh_note': 'identical to news_combo.py except the roots; King/legs/F10 are FRESH (PREREG §1 K/F/E)',
               'limits': ['production-caliber legs replayed on history; seat history starts with King OOF (2022-07)', 'no execution/cash or policy-stop result',
                          'scaled_diagnostic changes historical publication gate; never current-live literal']}
    (out / 'TARGET_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); print(json.dumps({k: receipt[k] for k in ('seed', 'member_cells_outside_book_universe')}), json.dumps({k: v['reasons'] for k, v in summary.items()}), flush=True)


if __name__ == '__main__':
    main()
