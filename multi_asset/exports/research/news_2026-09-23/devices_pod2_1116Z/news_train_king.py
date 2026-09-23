"""NEWS P3 King: the NEW recipe (codex_combo_20260923 devices/train_king.py 1c...: LGBM params, annual folds via
king_folds.fold_rows embargo 60, target = within-anchor rank of the raw label over members with >= 50 finite labels)
applied UNCHANGED to the NEWS inputs: X78 = producer King block features (NEWS_FEATURES.npz), members = producer member
screen on legal ∧ crypto candidates, labels = NEW dlw_targets y4s (raw compounded (E,E+48], all closes observed, NaN never 0).
Only the input-loading lines differ from train_king.py (diff archived); the fold loop is copied verbatim.
"""
import os
os.environ['OMP_NUM_THREADS'] = '8'; os.environ['OPENBLAS_NUM_THREADS'] = '2'
import sys, pathlib, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

W = pathlib.Path('/dev/shm/news_2026-09-23')
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
FOLDS_SRC = W / 'devices/king_folds.py'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


def main():
    sys.path.insert(0, str(W / 'devices')); from king_folds import fold_rows
    out = W / 'work/king'; out.mkdir(exist_ok=False)
    feat = W / 'work/NEWS_FEATURES.npz'; frec = json.load(open(W / 'receipts/P2B_FEATURES.json'))
    assert sha(feat) == frec['sha256'] and sha(NEWT) == NEWT_SHA
    F = np.load(feat); T = np.load(NEWT, allow_pickle=True)
    a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; cnt = F['count']
    assert np.array_equal(T['symbols'], syms)
    # labels from NEW's builder on NEW's axis; mapped by timestamp (anchors outside NEW's axis have no label)
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(syms)), np.nan, np.float32)
    ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a)
    y[ok] = T['y4s'][ix[ok]]
    pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
    assert x.shape[1] == 78 and np.isfinite(x).all() and len(pa) == len(ps) == len(x) == off[-1]
    # ---- verbatim from train_king.py from here (target, params, folds, receipts) ----
    target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))
    for i in range(len(a)):
        ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
        if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    import lightgbm as lgb
    params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=0)
    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); folds = []
    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
    specs = [('2022H2_WARMUP', utc(2022, 7), utc(2023))] + [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]
    for tag, start, end in specs:
        train, test = fold_rows(a, start, end, 60); tr = np.isin(pa, train) & np.isfinite(target); te = np.isin(pa, test)
        assert tr.sum() > 1000 and te.sum() > 0
        t = time.monotonic(); log('King start', tag, int(tr.sum()), int(te.sum()))
        model = lgb.LGBMRegressor(**params).fit(x[tr], target[tr]); modelpath = out / ('king_' + tag + '.txt'); model.booster_.save_model(str(modelpath))
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
        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': int(a[pa[tr]].max() + 14400), 'embargo_anchors': 60,
              'train_pairs': int(tr.sum()), 'scored_pairs': int(te.sum()), 'model_path': str(modelpath), 'model_sha256': mh, 'seconds': time.monotonic() - t,
              'mean_cs_spearman': float(np.mean(ic)), 'mean_cs_pearson': float(np.mean(pp)), 'mean_per_asset_pearson': float(np.mean(per)), 'n_cs_anchors': len(ic), 'status': 'SIGNAL_DIAGNOSTIC_ONLY'}
        assert rr['max_train_label_end'] <= rr['score_start'] - 60 * 14400
        folds.append(rr); log(json.dumps(rr)); (out / 'PROGRESS.json').write_text(json.dumps(folds, indent=2, allow_nan=False))
    np.savez(out / 'KING_OOF.npz', P=pred, E_ts=a, symbols=syms, model_sha256=model_id)
    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds,
               'source_sha': {__file__: sha(os.path.abspath(__file__)), str(FOLDS_SRC): sha(FOLDS_SRC)},
               'inputs': {str(feat): sha(feat), str(NEWT): NEWT_SHA}, 'predictions_sha256': sha(out / 'KING_OOF.npz'),
               'label': 'NEW dlw_targets y4s (raw compounded, all closes observed; NaN excluded, never 0)',
               'features': 'producer shadow_loop_v3 King block replayed (P2B_FEATURES.json)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
    (out / 'TRAIN_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); log('KING_DONE')


if __name__ == '__main__':
    main()
