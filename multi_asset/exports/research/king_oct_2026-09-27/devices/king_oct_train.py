"""king_oct_train.py -- the October King trainer (fresh2 2026-09-27; lead ruling on RUNBOOK_october_rebuild_D10 §7-1/4: King's
October recipe = the in-service recipe (A0 annual folds, rs=0 served, m0..m7 descriptive only), retrained on D10 features).
= kf_train_king.py (bf4594ff, the KINGFAM trainer whose A0_m0 reproduced the in-service KING_OOF a10b8725 bitwise) with the KN
T_NET branch and the A1/A2/A3 fold shapes removed and FOUR changes, none in the fold loop / target / params:
  (1) features and labels are arguments, each with a required sha that is asserted before use (--features/--features-sha,
      --labels/--labels-sha; the labels default to the in-service dlw_targets ca479fcc) -- no path is read from a receipt file;
  (2) every file written goes through common/durable_write.py (model text, PROGRESS, KING_OOF, TRAIN_RECEIPT): temp -> fsync ->
      read-back -> replace; the shas in the receipt are the ones the verified writes returned, never a later re-read (E-0925-A);
  (3) the receipt carries argv = vars(parsed args) and the interpreter (lead 09-27 decision 1), plus the trainer's own sha;
  (4) king_folds.py (fold boundaries) is pinned by sha (4886c278, the file every KINGFAM receipt names).
Output format is unchanged (KING_OOF.npz: P, E_ts, symbols, model_sha256; TRAIN_RECEIPT.json keys a superset of the old ones; the
fold "2026" model is the served booster -- news2_export_models.py L104/L143 -- so --keep-models is required for the served run).
usage: python king_oct_train.py --out DIR --rs 0 --features F.npz --features-sha SHA [--labels L.npz --labels-sha SHA] [--keep-models]
"""
import os
os.environ['OMP_NUM_THREADS'] = '8'; os.environ['OPENBLAS_NUM_THREADS'] = '2'
import sys, pathlib, json, time, calendar, hashlib, argparse
import numpy as np
from scipy.stats import rankdata, spearmanr, pearsonr

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it

NEWT = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
FOLDS_SRC = pathlib.Path('/dev/shm/news2_2026-09-23/devices/king_folds.py')
FOLDS_SHA = '4886c278c12b0f5126bb1e8ad6b4789db95e604180a77d0cd02f1e7c612df640'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


def a0_specs():   # in service, verbatim (kf_train_king.arm_specs('A0'))
    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
    return [('2022H2_WARMUP', utc(2022, 7), utc(2023))] + [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--rs', type=int, required=True)
    ap.add_argument('--features', required=True); ap.add_argument('--features-sha', required=True)
    ap.add_argument('--labels', default=NEWT); ap.add_argument('--labels-sha', default=NEWT_SHA)
    ap.add_argument('--keep-models', action='store_true'); args = ap.parse_args()
    assert sha(FOLDS_SRC) == FOLDS_SHA, 'king_folds.py is not the pinned fold-boundary source'
    sys.path.insert(0, str(FOLDS_SRC.parent)); from king_folds import fold_rows
    feat, lab = pathlib.Path(args.features), pathlib.Path(args.labels)
    fsha, lsha = sha(feat), sha(lab)   # identities before anything is created: a refused run leaves no output dir behind
    assert fsha == args.features_sha, 'features sha %s != --features-sha %s' % (fsha, args.features_sha)
    assert lsha == args.labels_sha, 'labels sha %s != --labels-sha %s' % (lsha, args.labels_sha)
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=False)
    F = np.load(feat); T = np.load(lab, allow_pickle=True)
    a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; cnt = F['count']
    assert np.array_equal(T['symbols'], syms), 'feature and label symbol axes differ'
    # labels from NEW's builder on NEW's axis; mapped by timestamp (anchors outside NEW's axis have no label)
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(syms)), np.nan, np.float32)
    ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a)
    y[ok] = T['y4s'][ix[ok]]
    pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
    assert x.shape[1] == 78 and np.isfinite(x).all() and len(pa) == len(ps) == len(x) == off[-1]
    # ---- verbatim from train_king.py from here (target, params, folds); only the writes go through DW ----
    target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))
    for i in range(len(a)):
        ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
        if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    import lightgbm as lgb
    params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=args.rs)
    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); folds = []
    for tag, start, end in a0_specs():
        train, test = fold_rows(a, start, end, 60)
        if len(test) == 0: continue
        tr = np.isin(pa, train) & np.isfinite(target); te = np.isin(pa, test)
        assert tr.sum() > 1000 and te.sum() > 0
        t = time.monotonic(); log('King start', tag, int(tr.sum()), int(te.sum()))
        model = lgb.LGBMRegressor(**params).fit(x[tr], target[tr]); modelpath = out / ('king_' + tag + '.txt')
        mh = DW.write_bytes(str(modelpath), model.booster_.model_to_string().encode())
        pred[pa[te], ps[te]] = model.predict(x[te]); model_id[test] = mh
        ic = []; pp = []
        for i in test:
            good = np.isfinite(pred[i]) & np.isfinite(y[i])
            if good.sum() >= 30:
                ic.append(float(spearmanr(pred[i, good], y[i, good]).correlation)); pp.append(float(pearsonr(pred[i, good], y[i, good])[0]))
        per = []
        for j in range(len(syms)):
            good = np.isfinite(pred[test, j]) & np.isfinite(y[test, j])
            if good.sum() >= 30 and np.std(pred[test[good], j]) > 0: per.append(float(pearsonr(pred[test[good], j], y[test[good], j])[0]))
        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': int(a[pa[tr]].max() + 14400), 'embargo_anchors': 60, 'train_window_start': None,
              'train_pairs': int(tr.sum()), 'scored_pairs': int(te.sum()), 'model_path': str(modelpath), 'model_sha256': mh, 'seconds': time.monotonic() - t,
              'mean_cs_spearman': float(np.mean(ic)), 'mean_cs_pearson': float(np.mean(pp)), 'mean_per_asset_pearson': float(np.mean(per)), 'n_cs_anchors': len(ic), 'status': 'SIGNAL_DIAGNOSTIC_ONLY'}
        assert rr['max_train_label_end'] <= rr['score_start'] - 60 * 14400
        folds.append(rr); log(json.dumps(rr)); DW.write_json(str(out / 'PROGRESS.json'), folds, indent=2, allow_nan=False)
    psha = DW.write_npz(str(out / 'KING_OOF.npz'), P=pred, E_ts=a, symbols=syms, model_sha256=model_id)
    if not args.keep_models:
        for rr in folds: os.remove(rr['model_path'])
    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds, 'arm': 'A0', 'random_state': args.rs, 'label_switch': 'y4s',
               'models_kept': bool(args.keep_models), 'argv': vars(args),
               'python': {'version': sys.version.split()[0], 'executable': sys.executable},
               'source_sha': {os.path.abspath(__file__): sha(os.path.abspath(__file__)), str(FOLDS_SRC): FOLDS_SHA,
                              os.path.realpath(DW.__file__): sha(os.path.realpath(DW.__file__))},
               'inputs': {str(feat): fsha, str(lab): lsha}, 'predictions_sha256': psha,
               'label': 'dlw_targets y4s (raw compounded, all closes observed; NaN excluded, never 0)',
               'features': 'producer King block X78 from --features (in-service NEWS_FEATURES or its D10 rebuild)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
    DW.write_json(str(out / 'TRAIN_RECEIPT.json'), receipt, indent=2, allow_nan=False); log('KING_DONE')


if __name__ == '__main__':
    main()
