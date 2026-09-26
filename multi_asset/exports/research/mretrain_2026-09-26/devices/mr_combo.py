"""NEWS P4 combo targets: the researcher's continuous_combo.evolve / combo_target.step (1501c9f6 / d7577e82; chain and
exec_reshape compiled from combo_stage.py fb5a9407 by combo_target.source_kernels) run UNCHANGED on NEWS production-caliber
inputs: King rank = legs KZ, F10 score = NEWS F10 OOF (seed), fund rank = legs ZFD (xz_in_base over the replayed M1 base),
seats = legs WL (production msharpe 900), rn8 = ledger-tail rate*8/iv (no freshness), qv = production qv4h,
LIVE_MASK = book universe (book_universe.py, the same U-PIT/CRYPTO proxy NEW used) ∧ candidates(A) (legal ∧ crypto).
Both publication policies are written (the Stage-1 adapter consumes both; scaled_diagnostic is the main reading).
State starts from zero at 2023-01-01, as in NEW / Stage 1 C5.
usage: python news_combo.py --seed 42|2027
"""
import os, sys, json, argparse, collections, datetime, pathlib, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from continuous_combo import evolve, verify_training
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
import combo_target

W = pathlib.Path(os.environ['MR_W'])                     # MRETRAIN change 1: the arm's own root (legs, P3_LEGS, outputs)
F10_ROOT = pathlib.Path('/dev/shm/news2_2026-09-23')     # MRETRAIN change 2: F10 fixed in service (DECISION_RULE §5), read-only
# MRETRAIN change 3: the ONE location of the vendored producer source = the file combo_target.source_kernels() reads (its ROOT =
# devices/..). In news2 W and that ROOT were the same directory; change 1 split them and the 2026-09-26 18:35Z run died on it
# (FileNotFoundError after King + legs). mr_prep vendors to `--stage-path` and the receipt records this path, never a W copy.
STAGE = combo_target.ROOT / 'vendor_live/fea171/combo_stage.py'
# MRETRAIN change 4 (pre-flight, below): pins of the in-service NEWS2 X run configs; each names its combo TARGET_RECEIPT by sha.
REF_CONFIG = {42: ('/dev/shm/news2_2026-09-23/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json', '9526ad1883129f689bff53f9b68b91ade3db8885f67a43f8c21e038fb2e85e2a'),
              2027: ('/dev/shm/news2_2026-09-23/configs/RUN_CONFIG_NEWS2_s2027X_2026-09-23.json', 'edd176f3719c13661add9b62a1645fb798c480e0f562145cf364e133f45e02d1')}
PRODUCED = ('legs.npz', 'P3_LEGS.json')                  # written by this arm's own legs step: cannot be checked before training


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def input_paths(seed):
    froot = F10_ROOT / f'work/f10_s{seed}'
    return froot, [W / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'receipts/P3_LEGS.json', froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', W / 'inputs/bundle_config.json',
                   W / 'receipts/P1_members_2025H2on.npz', pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]


def source_paths():
    return [pathlib.Path(__file__), pathlib.Path(HERE) / 'continuous_combo.py', pathlib.Path(HERE) / 'combo_target.py', pathlib.Path(HERE) / 'book_universe.py', STAGE]


def preflight(seed, sha=sha):
    """MRETRAIN change 4: every file main() reads that exists before this arm's King/legs are trained — taken from main's own
    input_paths() / source_paths(), never a second hand-written list — checked against the in-service NEWS2 combo receipt of the
    same seed (reached through REF_CONFIG's literal sha, so a swapped reference tree fails too). Run by mr_prep before any training."""
    combo_target.source_kernels()                        # the exact read (and EXPECTED sha) that failed at 18:35Z, first: cheapest
    cp, csha = REF_CONFIG[seed]; assert sha(cp) == csha, ('in-service run config changed', cp)
    lin = json.loads(pathlib.Path(cp).read_text())['new_lineage']['new_target_receipt']; assert sha(lin['path']) == lin['sha256'], lin['path']
    ref = json.loads(pathlib.Path(lin['path']).read_text())
    froot, paths = input_paths(seed); out = {}
    mine, theirs = paths + [pathlib.Path(UNIVERSE_PATH)], list(ref['inputs'].items()); assert len(mine) == len(theirs), 'input list length'
    for p, (q, h) in zip(mine, theirs):
        assert p.name == pathlib.Path(q).name, ('input order', str(p), q)
        if p.name in PRODUCED: out[str(p)] = 'PRODUCED_BY_THIS_ARM'; continue
        assert p.is_file(), ('static input missing', str(p))
        assert sha(p) == h, ('static input differs from the in-service combo input', str(p), q); out[str(p)] = h
    assert sorted(pathlib.Path(k).name for k, v in out.items() if v == 'PRODUCED_BY_THIS_ARM') == sorted(PRODUCED)
    srcs, rsrc = source_paths(), list(ref['sources'].items()); assert len(srcs) == len(rsrc), 'source list length'
    for p, (q, h) in list(zip(srcs, rsrc))[1:]:          # [0] = this file vs news2_combo.py: different by design (mr_combo.DIFF.txt)
        assert p.name == pathlib.Path(q).name and sha(p) == h, ('source differs from the in-service combo source', str(p), q); out[str(p)] = h
    rec = json.loads(paths[4].read_text())               # F10 identity, as main() checks it
    assert rec['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256'] == sha(paths[3])
    verify_training(froot, rec, seed, sha)
    assert set(rec['folds']) == set(rec['expected_folds'])
    for p, h in rec['inputs'].items(): assert sha(p) == h, ('training input drift', p)
    for p, h in rec['sources'].items(): assert sha(p) == h, ('training source drift', p)
    return {'reference_receipt': lin, 'checked': out}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, choices=(42, 2027))
    ap.add_argument('--preflight', action='store_true'); ap.add_argument('--stage-path', action='store_true'); args = ap.parse_args()
    if args.stage_path: print(STAGE); return
    if args.preflight:
        memo = {}; msha = lambda p: memo[str(p)] if str(p) in memo else memo.setdefault(str(p), sha(p))
        res = {s: preflight(s, msha) for s in ((args.seed,) if args.seed else (42, 2027))}
        print('MR_COMBO_PREFLIGHT PASS', json.dumps({'stage': str(STAGE), 'W': str(W), 'files_checked': len(memo)}), flush=True); return
    assert args.seed in (42, 2027), '--seed required'
    froot, paths = input_paths(args.seed)
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
    sources = {str(p): sha(p) for p in source_paths()}
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
    receipt = {'status': 'NEWS_TARGETS_NOT_EXECUTION_PNL', 'seed': args.seed, 'inputs': ident, 'sources': sources, 'policies': summary,
               'member_cells_outside_book_universe': outside,
               'state_init': 'zero at 2023-01-01; hypothetical common start, not live archived state',
               'hold_contract': 'trade_mask False = maintain quantities, never King substitution',
               'limits': ['production-caliber legs replayed on history; seat history starts with King OOF (2022H2)', 'no execution/cash or policy-stop result',
                          'scaled_diagnostic changes historical publication gate; never current-live literal']}
    (out / 'TARGET_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); print(json.dumps({k: receipt[k] for k in ('seed', 'member_cells_outside_book_universe')}), json.dumps({k: v['reasons'] for k, v in summary.items()}), flush=True)


if __name__ == '__main__':
    main()
