"""FRESH P3 King: news_train_king.py with ONLY the three PREREG_fresh_models_newS_2026-09-23.md §1 changes:
  K  annual folds (2022H2_WARMUP + 2023/2024/2025/2026)  ->  one fold per calendar month from 2022-07 (expanding window)
  E  embargo 60 anchors                                  ->  embargo 6 anchors (fold_rows + receipt field + assertion)
  roots: this agent's own root for outputs; NEW_S root read-only for the frozen inputs (features, labels, receipts).
LGBM params, target definition, random_state, fold loop body and receipts are byte-for-byte news_train_king.py.
king_folds.py is the NEW_S file unchanged (embargo is already its parameter).
"""
import os
os.environ['OMP_NUM_THREADS'] = '8'; os.environ['OPENBLAS_NUM_THREADS'] = '2'
import sys, pathlib, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

W = pathlib.Path('/dev/shm/fresh_2026-09-23')
N = pathlib.Path('/dev/shm/news_2026-09-23')           # NEW_S root: READ-ONLY frozen inputs
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
FOLDS_SRC = W / 'devices/king_folds.py'
EMBARGO = 6                                            # PREREG §1 E (NEW_S: 60)
PREREG = {'path': 'docs/PREREG_fresh_models_newS_2026-09-23.md', 'commit': 'b6e682e0a'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


def month_specs(a):
    """PREREG §1 K: one fold per calendar month from 2022-07 to the last month on the axis; expanding train window."""
    utc = lambda yr, mo: calendar.timegm((yr, mo, 1, 0, 0, 0))
    out = []; y, m = 2022, 7
    while utc(y, m) <= int(a[-1]):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append((f'{y}{m:02d}', utc(y, m), utc(ny, nm))); y, m = ny, nm
    return out


def main():
    sys.path.insert(0, str(W / 'devices')); from king_folds import fold_rows
    out = W / 'work/king'; out.mkdir(exist_ok=False)
    feat = N / 'work/NEWS_FEATURES.npz'; frec = json.load(open(N / 'receipts/P2B_FEATURES.json'))
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
    # ---- verbatim from news_train_king.py from here (target, params, folds, receipts) ----
    target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))
    for i in range(len(a)):
        ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
        if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    import lightgbm as lgb
    params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=0)
    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); fold_id = np.full(len(a), '', dtype='U16')
    train_end = np.full(len(a), -1, np.int64); folds = []
    specs = month_specs(a)
    for tag, start, end in specs:
        train, test = fold_rows(a, start, end, EMBARGO); tr = np.isin(pa, train) & np.isfinite(target); te = np.isin(pa, test)
        assert tr.sum() > 1000 and te.sum() > 0
        t = time.monotonic(); log('King start', tag, int(tr.sum()), int(te.sum()))
        model = lgb.LGBMRegressor(**params).fit(x[tr], target[tr]); modelpath = out / ('king_' + tag + '.txt'); model.booster_.save_model(str(modelpath))
        pred[pa[te], ps[te]] = model.predict(x[te]); mh = sha(modelpath); model_id[test] = mh; fold_id[test] = tag
        mtle = int(a[pa[tr]].max() + 14400); train_end[test] = mtle
        ic = []; pp = []
        for i in test:
            good = np.isfinite(pred[i]) & np.isfinite(y[i])
            if good.sum() >= 30:
                ic.append(float(spearmanr(pred[i, good], y[i, good]).correlation)); pp.append(float(pearsonr(pred[i, good], y[i, good])[0]))
        per = []
        for j in range(len(syms)):
            good = np.isfinite(pred[test, j]) & np.isfinite(y[test, j])
            if good.sum() >= 30 and np.std(pred[test[good], j]) > 0: per.append(float(pearsonr(pred[test[good], j], y[test[good], j])[0]))
        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': mtle, 'embargo_anchors': EMBARGO,
              'train_pairs': int(tr.sum()), 'scored_pairs': int(te.sum()), 'model_path': str(modelpath), 'model_sha256': mh, 'seconds': time.monotonic() - t,
              'mean_cs_spearman': float(np.mean(ic)), 'mean_cs_pearson': float(np.mean(pp)), 'mean_per_asset_pearson': float(np.mean(per)), 'n_cs_anchors': len(ic), 'status': 'SIGNAL_DIAGNOSTIC_ONLY'}
        assert rr['max_train_label_end'] <= rr['score_start'] - EMBARGO * 14400
        folds.append(rr); log(json.dumps(rr)); (out / 'PROGRESS.json').write_text(json.dumps(folds, indent=2, allow_nan=False))
    np.savez(out / 'KING_OOF.npz', P=pred, E_ts=a, symbols=syms, model_sha256=model_id, fold_tag=fold_id, max_train_label_end=train_end)
    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds, 'prereg': PREREG,
               'fresh_changes': {'K': 'calendar-month folds from 2022-07, expanding window (NEW_S: annual folds)', 'E': f'embargo {EMBARGO} anchors (NEW_S: 60)'},
               'source_sha': {__file__: sha(os.path.abspath(__file__)), str(FOLDS_SRC): sha(FOLDS_SRC)},
               'inputs': {str(feat): sha(feat), str(NEWT): NEWT_SHA}, 'predictions_sha256': sha(out / 'KING_OOF.npz'),
               'label': 'NEW dlw_targets y4s (raw compounded, all closes observed; NaN excluded, never 0)',
               'features': 'producer shadow_loop_v3 King block replayed (NEW_S receipts/P2B_FEATURES.json)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
    (out / 'TRAIN_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); log('KING_DONE')


if __name__ == '__main__':
    main()
