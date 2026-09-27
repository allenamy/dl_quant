"""king_oct_repredict.py -- re-predict the FROZEN October King (release m0, MANIFEST_RELEASE 2d0fa3f9) on another feature file
(fresh2 2026-09-27; lead: descriptive D10 re-read on features extended past the cut). No training, no frozen file written: the five
fold boosters of release m0 are READ (each file's sha must equal both TRAIN_RECEIPT folds[].model_sha256 and the manifest's
m0_all_fold_models), and each scores exactly the test rows king_folds.fold_rows(anchors, start, end, 60) gives it on the NEW axis
(same pinned fold source 4886c278 and the same A0 fold specs as king_oct_train.py; anchors past the old axis end fall in fold 2026).
Prediction path = lightgbm.Booster(model_file).predict(X78 rows).astype(float32), the path release gate G3 showed reproduces the
trained P bitwise. Output <out>/KING_OOF.npz (P, E_ts, symbols, model_sha256 -- the in-service format) + REPREDICT_RECEIPT.json,
both through durable_write. The identity control (run on f1cd3fa2, must equal release m0's P / E_ts / symbols bitwise) is the
driver's first step, not this file's.
usage: python king_oct_repredict.py --release-root DIR --manifest MANIFEST_RELEASE.json --manifest-sha SHA --features F --features-sha SHA --out DIR
"""
import os, sys, json, hashlib, argparse, calendar, pathlib
import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW

FOLDS_SRC = pathlib.Path('/dev/shm/news2_2026-09-23/devices/king_folds.py')
FOLDS_SHA = '4886c278c12b0f5126bb1e8ad6b4789db95e604180a77d0cd02f1e7c612df640'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def a0_specs():   # == king_oct_train.a0_specs (in service, verbatim)
    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
    return [('2022H2_WARMUP', utc(2022, 7), utc(2023))] + [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]


def main():
    ap = argparse.ArgumentParser()
    for k in ('--release-root', '--manifest', '--manifest-sha', '--features', '--features-sha', '--out'): ap.add_argument(k, required=True)
    args = ap.parse_args()
    assert sha(FOLDS_SRC) == FOLDS_SHA, 'king_folds.py is not the pinned fold-boundary source'
    sys.path.insert(0, str(FOLDS_SRC.parent)); from king_folds import fold_rows
    assert sha(args.manifest) == args.manifest_sha, 'manifest identity'
    man = json.load(open(args.manifest)); rec = json.load(open(os.path.join(args.release_root, 'TRAIN_RECEIPT.json')))
    mf = {f['fold']: f for f in man['m0_all_fold_models']}; rf = {f['fold']: f for f in rec['folds']}
    assert sorted(mf) == sorted(rf) == sorted(t for t, _, _ in a0_specs()), (sorted(mf), sorted(rf))
    fsha = sha(args.features); assert fsha == args.features_sha, 'features sha %s != --features-sha' % fsha
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=False)
    import lightgbm as lgb
    F = np.load(args.features)
    a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; cnt = F['count']
    pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
    assert x.shape[1] == 78 and np.isfinite(x).all() and len(pa) == len(ps) == len(x) == off[-1]
    pred = np.full((len(a), len(syms)), np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); folds = []
    for tag, start, end in a0_specs():
        _, test = fold_rows(a, start, end, 60)
        if len(test) == 0: continue
        mp = rf[tag]['model_path']; ms = sha(mp)
        assert ms == rf[tag]['model_sha256'] == mf[tag]['sha256'], 'fold %s booster is not the frozen one' % tag
        te = np.isin(pa, test)
        pred[pa[te], ps[te]] = lgb.Booster(model_file=mp).predict(x[te]).astype(np.float32); model_id[test] = ms
        folds.append({'fold': tag, 'model_path': mp, 'model_sha256': ms, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]),
                      'scored_pairs': int(te.sum()), 'trained_scored_pairs': rf[tag]['scored_pairs']})
    psha = DW.write_npz(str(out / 'KING_OOF.npz'), P=pred, E_ts=a, symbols=syms, model_sha256=model_id)
    receipt = {'status': 'REPREDICT_FROZEN_KING_NO_TRAINING', 'argv': vars(args), 'python': {'version': sys.version.split()[0], 'executable': sys.executable},
               'source_sha': {os.path.realpath(__file__): sha(os.path.realpath(__file__)), str(FOLDS_SRC): FOLDS_SHA,
                              os.path.realpath(DW.__file__): sha(os.path.realpath(DW.__file__))},
               'inputs': {args.features: fsha, args.manifest: args.manifest_sha}, 'folds': folds, 'n_anchors': int(len(a)),
               'axis': [int(a[0]), int(a[-1])], 'predictions_sha256': psha, 'P_array_sha256': hashlib.sha256(pred.tobytes()).hexdigest(),
               'lightgbm': lgb.__version__, 'numpy': np.__version__}
    DW.write_json(str(out / 'REPREDICT_RECEIPT.json'), receipt, indent=2, allow_nan=False)
    print('KRP_DONE out=%s predictions_sha256=%s n_anchors=%d' % (out, psha, len(a)), flush=True)


if __name__ == '__main__':
    main()
