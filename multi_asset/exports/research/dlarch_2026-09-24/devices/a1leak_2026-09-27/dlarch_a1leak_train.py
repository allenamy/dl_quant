"""dlarch_a1leak_train.py (dlarch 2026-09-27, A1 leakage audit, lead 05:1xZ; DESCRIPTIVE, the A1 verdict d585e1792 is not reopened)
= kf_train_king.py (fresh2, sha bf4594ff, the trainer that produced A1 m0..m7) with ONE addition: --shuffle, which permutes the
LABEL within each anchor over that anchor's member cells with a finite label (population and marginal kept), then recomputes the
verbatim target for the permuted anchors. Everything else -- features, members, params, folds, embargo, loop -- is untouched.
  none     : nothing permuted (identity path).
  future   : per fold, every anchor NOT eligible for training (a + 4h > fold start - 60 anchors, i.e. the embargo, the test
             window and everything after it) is permuted, afresh for each fold. A fold scheme that never reads those labels
             must give scores BITWISE equal to the unshuffled run. This is the executed form of "no future label reaches training".
  pastlast : per fold, the LAST 6 training-eligible anchors are permuted -- labels training DOES read. Scores must differ.
             Negative control: shows the bitwise comparison has power (a comparison that cannot go red certifies nothing).
  all      : every anchor permuted once (seed fixed) -- the model learns noise; its IC against the TRUE label must sit
             inside its own permutation null (read by dlarch_a1leak_audit.py).
--folds restricts training to the named fold tags (pastlast runs on a few folds only). Receipt records mode, seed, folds, and
per fold the number of anchors permuted. NOTE: under 'all' the per-fold diagnostic IC in the receipt is against the PERMUTED
label (the loop body is verbatim); it is not a reading -- the audit device computes IC against the true label.
BASE DOCSTRING: KINGFAM King trainer (fresh2 2026-09-27, DECISION_RULE_king_improvement_family_2026-09-27.md 4158f1521) = mr_train_king.py
(2444fe22, passed the monthly-retrain family's device gates) with ONE addition: --label y4s|tnet (default y4s = in-service behaviour,
byte-for-byte the same code path). tnet = the KN arm: the training label is dlarch's T_NET (price − long funding paid over (A, A+4h]),
read from --tnet whose sha must equal --tnet-sha, mapped onto the feature anchors exactly as y4s is, and whose PRICE array must be
bitwise equal to the y4s it replaces on the NEWT axis (one change only: the funding term). Target construction is unchanged
(within-anchor rank over members with >= 50 finite labels). Diff vs mr_train_king.py: kf_train_king.DIFF.txt.
MRETRAIN docstring: news2_train_king.py b19459a5 with ONLY
  (1) OUT dir from --out (inputs still read from the news2 root, read-only); (2) random_state from --rs;
  (3) fold specs from --arm: A0 annual (in service, verbatim) / A1 monthly / A2 quarterly, expanding / A3 annual, rolling 24-month
      train window; (4) arm, rs and window written into the receipt; (5) model .txt files deleted after the OOF is written unless
      --keep-models (their sha stays in KING_OOF model_sha256 and in the receipt). Embargo 60, params, target, loop body verbatim.
ORIGINAL DOCSTRING: NEWS P3 King: the NEW recipe (codex_combo_20260923 devices/train_king.py 1c...: LGBM params, annual folds via
king_folds.fold_rows embargo 60, target = within-anchor rank of the raw label over members with >= 50 finite labels)
applied UNCHANGED to the NEWS inputs: X78 = producer King block features (NEWS_FEATURES.npz), members = producer member
screen on legal ∧ crypto candidates, labels = NEW dlw_targets y4s (raw compounded (E,E+48], all closes observed, NaN never 0).
Only the input-loading lines differ from train_king.py (diff archived); the fold loop is copied verbatim.
"""
import os
os.environ['OMP_NUM_THREADS'] = '8'; os.environ['OPENBLAS_NUM_THREADS'] = '2'
import sys, pathlib, json, time, calendar, hashlib, argparse
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

W = pathlib.Path('/dev/shm/news2_2026-09-23')
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
FOLDS_SRC = W / 'devices/king_folds.py'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


def arm_specs(arm, a):
    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
    if arm in ('A0', 'A3'):
        return [('2022H2_WARMUP', utc(2022, 7), utc(2023))] + [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]
    step = {'A1': 1, 'A2': 3}[arm]; out = []; y, m = 2022, 7
    while utc(y, m) <= int(a[-1]):
        ny, nm = y + (m - 1 + step) // 12, (m - 1 + step) % 12 + 1
        out.append((f'{y}{m:02d}', utc(y, m), utc(ny, nm))); y, m = ny, nm
    return out


def window_start(arm, start):
    """A3: rolling 24 calendar months before the fold start (train rows with anchor >= this); others: None (expanding)"""
    if arm != 'A3': return None
    t = time.gmtime(start); return calendar.timegm((t.tm_year - 2, t.tm_mon, 1, 0, 0, 0))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--arm', choices=('A0', 'A1', 'A2', 'A3'), required=True)
    ap.add_argument('--rs', type=int, required=True); ap.add_argument('--keep-models', action='store_true')
    ap.add_argument('--label', choices=('y4s', 'tnet'), default='y4s'); ap.add_argument('--tnet'); ap.add_argument('--tnet-sha')
    ap.add_argument('--shuffle', choices=('none', 'future', 'pastlast', 'all'), required=True); ap.add_argument('--shuffle-seed', type=int, default=20260927)
    ap.add_argument('--folds', default=''); args = ap.parse_args()
    sys.path.insert(0, str(W / 'devices')); from king_folds import fold_rows
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=False)
    feat = W / 'work/NEWS_FEATURES.npz'; frec = json.load(open(W / 'receipts/P2B_FEATURES.json'))
    assert sha(feat) == frec['sha256'] and sha(NEWT) == NEWT_SHA
    F = np.load(feat); T = np.load(NEWT, allow_pickle=True)
    a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; cnt = F['count']
    assert np.array_equal(T['symbols'], syms)
    # labels from NEW's builder on NEW's axis; mapped by timestamp (anchors outside NEW's axis have no label)
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(syms)), np.nan, np.float32)
    ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a)
    y[ok] = T['y4s'][ix[ok]]
    tnet_input = {}; tnet_cells_rec = None
    if args.label == 'tnet':   # KINGFAM: the only change of the KN arm -- the label's funding term
        # dlarch T_NET.npz (1231f7f72): E_ts (NEWT axis), symbols, T_net (float64) = y4s - F, F (long funding paid), covered (bool)
        assert args.tnet and args.tnet_sha and sha(args.tnet) == args.tnet_sha, 'T_NET file identity'
        TN = np.load(args.tnet, allow_pickle=False)
        assert np.array_equal(TN['symbols'], syms) and np.array_equal(TN['E_ts'].astype(np.int64), ya), 'T_NET axes must be the NEWT axes'
        tn, FU, y4 = TN['T_net'], TN['F'], T['y4s']; assert tn.shape == FU.shape == y4.shape and tn.dtype == np.float64
        fin = np.isfinite(tn)
        assert not (fin & ~np.isfinite(y4)).any(), 'T_net finite where y4s is not'
        assert (y4[fin].astype(np.float64) - FU[fin]).tobytes() == tn[fin].tobytes(), 'T_net must be bitwise y4s - F (price half = the y4s it replaces)'
        tnet_cells = {'finite_T_net': int(fin.sum()), 'finite_y4s': int(np.isfinite(y4).sum()), 'y4s_finite_but_T_net_NaN': int((np.isfinite(y4) & ~fin).sum())}
        log('T_NET', json.dumps(tnet_cells))
        y = np.full((len(a), len(syms)), np.nan, np.float64); y[ok] = tn[ix[ok]]   # float64: ranks of the label as delivered (no float32 ties)
        tnet_input = {args.tnet: args.tnet_sha}; tnet_cells_rec = tnet_cells   # FU, not F: F is the feature file
    pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
    assert x.shape[1] == 78 and np.isfinite(x).all() and len(pa) == len(ps) == len(x) == off[-1]
    # ---- verbatim from train_king.py from here (target, params, folds, receipts) ----
    target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))

    def fill_target(tgt, yy, rows):   # the verbatim target body, for the given anchors
        for i in rows:
            ixx = np.arange(st[i], st[i + 1]); vals = yy[i, ps[ixx]]; good = np.isfinite(vals)
            tgt[ixx] = np.nan
            if good.sum() >= 50: tgt[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5

    def permute(yy, rows, rng):       # A1LEAK: within-anchor permutation over member cells with a finite label
        yy = yy.copy()
        for i in rows:
            cols = ps[st[i]:st[i + 1]]; v = yy[i, cols]; g = np.flatnonzero(np.isfinite(v))
            v[g] = v[g[rng.permutation(len(g))]]; yy[i, cols] = v
        return yy
    if args.shuffle == 'all':
        y = permute(y, range(len(a)), np.random.default_rng(args.shuffle_seed))
    for i in range(len(a)):
        ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
        if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    keep_folds = set(x for x in args.folds.split(',') if x); shuf_rec = {}
    import lightgbm as lgb
    params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=args.rs)
    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); folds = []
    specs = arm_specs(args.arm, a)
    for fi, (tag, start, end) in enumerate(specs):
        if keep_folds and tag not in keep_folds: continue
        train, test = fold_rows(a, start, end, 60)
        tgt = target
        if args.shuffle in ('future', 'pastlast'):
            elig = a + 14400 <= start - 60 * 14400
            rows = np.flatnonzero(~elig) if args.shuffle == 'future' else np.flatnonzero(elig)[-6:]
            tgt = target.copy(); fill_target(tgt, permute(y, rows, np.random.default_rng([args.shuffle_seed, fi])), rows)
            shuf_rec[tag] = {'anchors_permuted': int(len(rows)), 'first': int(a[rows].min()), 'last': int(a[rows].max())}
        ws = window_start(args.arm, start)
        if ws is not None: train = train[a[train] >= ws]
        if len(test) == 0: continue
        tr = np.isin(pa, train) & np.isfinite(tgt); te = np.isin(pa, test)
        assert tr.sum() > 1000 and te.sum() > 0
        t = time.monotonic(); log('King start', tag, int(tr.sum()), int(te.sum()))
        model = lgb.LGBMRegressor(**params).fit(x[tr], tgt[tr]); modelpath = out / ('king_' + tag + '.txt'); model.booster_.save_model(str(modelpath))
        pred[pa[te], ps[te]] = model.predict(x[te]); mh = sha(modelpath); model_id[test] = mh
        ic = []; pp = []
        for i in test:
            good = np.isfinite(pred[i]) & np.isfinite(y[i])
            if good.sum() >= 30:
                ic.append(float(spearmanr(pred[i, good], y[i, good]).correlation)); pp.append(float(pearsonr(pred[i, good], y[i, good])[0]))
        per = []
        for j in range(len(syms)):
            good = np.isfinite(pred[test, j]) & np.isfinite(y[test, j])
            if good.sum() >= 30 and np.std(pred[test[good], j]) > 0: per.append(float(pearsonr(pred[test[good], j], y[test[good], j])[0]))
        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': int(a[pa[tr]].max() + 14400), 'embargo_anchors': 60, 'train_window_start': ws,
              'train_pairs': int(tr.sum()), 'scored_pairs': int(te.sum()), 'model_path': str(modelpath), 'model_sha256': mh, 'seconds': time.monotonic() - t,
              'mean_cs_spearman': float(np.mean(ic)), 'mean_cs_pearson': float(np.mean(pp)), 'mean_per_asset_pearson': float(np.mean(per)), 'n_cs_anchors': len(ic), 'status': 'SIGNAL_DIAGNOSTIC_ONLY'}
        assert rr['max_train_label_end'] <= rr['score_start'] - 60 * 14400
        folds.append(rr); log(json.dumps(rr)); (out / 'PROGRESS.json').write_text(json.dumps(folds, indent=2, allow_nan=False))
    np.savez(out / 'KING_OOF.npz', P=pred, E_ts=a, symbols=syms, model_sha256=model_id)
    if not args.keep_models:
        for rr in folds: os.remove(rr['model_path'])
    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds, 'arm': args.arm, 'random_state': args.rs, 'label_switch': args.label, 'T_NET_cells': tnet_cells_rec,
               'models_kept': bool(args.keep_models), 'A1LEAK_shuffle': {'mode': args.shuffle, 'seed': args.shuffle_seed, 'folds': sorted(keep_folds) or 'all', 'per_fold': shuf_rec},
               'source_sha': {__file__: sha(os.path.abspath(__file__)), str(FOLDS_SRC): sha(FOLDS_SRC)},
               'inputs': {str(feat): sha(feat), str(NEWT): NEWT_SHA, **tnet_input}, 'predictions_sha256': sha(out / 'KING_OOF.npz'),
               'label': 'NEW dlw_targets y4s (raw compounded, all closes observed; NaN excluded, never 0)' if args.label == 'y4s' else
                        'T_NET = y4s (bitwise) - long funding paid over (A, A+4h] (dlarch, producer caliber); NaN excluded, never 0',
               'features': 'producer shadow_loop_v3 King block replayed (P2B_FEATURES.json)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
    (out / 'TRAIN_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); log('KING_DONE')


if __name__ == '__main__':
    main()
