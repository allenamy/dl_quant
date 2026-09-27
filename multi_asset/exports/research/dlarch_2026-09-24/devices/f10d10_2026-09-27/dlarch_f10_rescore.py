#!/usr/bin/env python3
"""dlarch_f10_rescore.py -- re-SCORE the FROZEN October D10 F10 models (no retraining; lead 6838a219a froze them) on a different
feature file, for lead's descriptive re-read (11:1xZ): news2 extends the D10 ledger past the 09-01T02Z cut and rebuilds the features
and legs; the verdict (UNDECIDED) is not reopened.

WHAT IT DOES, per fold of the frozen seed directory (read-only; its artifacts are checked against the frozen TRAIN_RECEIPT):
  load model.pt (state_dict, mu, sd) into the trainer's own Net (imported from dlarch_train_f10.py, not re-typed), eval mode, and score
  the fold's test anchors EXACTLY as the trainer's scoring block does: rows with >= 50 members, xx = clamp((X - mu) / sd, -5, 5),
  model.f(xx) on the same GPU, float32 -> the fold's scores. X = concat(X82, X89) of the NEW feature file.
  Output mirrors a trainer run (so dlarch_chain_run.py / news2_combo.py accept it unchanged): <out>/<fold>/{FOLD_RECEIPT.json,
  model.pt (byte copy of the frozen file, sha asserted equal), scores.npz}, F10_OOF.npz and TRAIN_RECEIPT.json (status
  ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED, inputs = the NEW features / legs + their receipts + the label file, exactly the
  trainer's five-input shape; sources = this device + the trainer it imports). Every receipt says mode RESCORE_FROZEN_MODELS and
  names the frozen directory, its receipt sha, and the frozen OOF sha.
IDENTITY CONTROL (lead: before any real re-score): run on the OLD D10 features (f1cd3fa2) and require the resulting F10_OOF P and
  every fold's scores P to be BITWISE equal to the frozen ones. --identity makes the device assert that itself and print a verdict line.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_f10_rescore.py --frozen <seed dir> --out <dir>
         --features F --features-sha S --features-receipt R --legs L --legs-sha S --legs-receipt R [--identity]
"""
import argparse, hashlib, json, os, pathlib, shutil, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dlarch_train_f10 as TR          # noqa: E402  Net, fold_specs, sio (guards installed at its import)
import torch                           # noqa: E402

sio = TR.sio
NEWT = TR.NEWT; NEWT_SHA = TR.NEWT_SHA


def sha(p):
    return TR.sha(p)


def main():
    ap = argparse.ArgumentParser()
    for k in ('--frozen', '--out', '--features', '--features-sha', '--features-receipt', '--legs', '--legs-sha', '--legs-receipt'):
        ap.add_argument(k, required=True)
    ap.add_argument('--identity', action='store_true'); args = ap.parse_args()
    assert torch.cuda.is_available(), 'GPU required (the frozen scores were produced on the GPU)'
    FZ = pathlib.Path(args.frozen); out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=False)
    frec = json.load(open(FZ / 'TRAIN_RECEIPT.json')); seed = frec['seed']
    assert frec['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED'
    for p, h in frec['fold_artifacts'].items(): assert sha(p) == h, f'frozen artifact drift: {p}'
    assert sha(FZ / 'F10_OOF.npz') == frec['pred_sha256']
    files = [pathlib.Path(args.features), NEWT, pathlib.Path(args.legs), pathlib.Path(args.features_receipt), pathlib.Path(args.legs_receipt)]
    inputs = {str(p): sha(p) for p in files}
    assert inputs[str(files[0])] == args.features_sha and inputs[str(files[2])] == args.legs_sha and inputs[str(files[1])] == NEWT_SHA
    rsha = lambda rp: (lambda j: j.get('sha256') or (j.get('output') or {}).get('sha256'))(json.load(open(rp)))
    assert rsha(files[3]) == args.features_sha and rsha(files[4]) == args.legs_sha
    sources = {str(p): sha(p) for p in (pathlib.Path(os.path.abspath(__file__)), pathlib.Path(os.path.abspath(TR.__file__)))}
    F = np.load(files[0]); a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; ps = F['m'].astype(int)
    Z0 = np.load(FZ / 'F10_OOF.npz'); assert np.array_equal(Z0['E_ts'], a) and np.array_equal(Z0['symbols'], syms), 'axis differs from the frozen OOF'
    cnt = F['count']; pa = np.repeat(np.arange(len(a)), cnt).astype(int); st = np.searchsorted(pa, np.arange(len(a) + 1)); w = len(syms)
    x = np.concatenate([F['X82'].astype(np.float32), F['X89']], 1).astype(np.float32); assert x.shape == (len(pa), 171) and np.isfinite(x).all()
    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x
    allpred = np.full((len(a), w), np.nan, np.float32); fold_artifacts = {}; found = []; ident = {}
    for tag, start, end in TR.fold_specs(a):
        if tag not in frec['folds']: continue
        ck = torch.load(FZ / tag / 'model.pt', map_location=dev, weights_only=True)
        model = TR.Net().to(dev); model.load_state_dict(ck['state_dict']); model.eval(); mu, sd = ck['mu'].to(dev), ck['sd'].to(dev)
        te = np.flatnonzero((a >= start) & (a < end)); pred = np.full((len(te), w), np.nan, np.float32)
        with torch.no_grad():
            for k, i in enumerate(te):
                if st[i + 1] - st[i] < 50: continue
                xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5); pred[k, ps[st[i]:st[i + 1]]] = model.f(xx).squeeze(-1).cpu().numpy()
        d = out / tag; d.mkdir()
        shutil.copyfile(FZ / tag / 'model.pt', d / 'model.pt'); msha = sha(d / 'model.pt')
        assert msha == sha(FZ / tag / 'model.pt'), 'model copy differs from the frozen model'
        ssha = sio.save_npz(d / 'scores.npz', P=pred, rows=te, E_ts=a[te], symbols=syms); allpred[te] = pred
        z0 = np.load(FZ / tag / 'scores.npz'); ident[tag] = bool(z0['P'].tobytes() == pred.tobytes())
        rr = {'status': 'F10_OOF_SCORES_NOT_COMBO_PNL', 'mode': 'RESCORE_FROZEN_MODELS', 'arm': frec['arm'], 'seed': seed, 'fold': tag,
              'inputs': inputs, 'sources': sources, 'score_sha256': ssha, 'model_sha256': msha,
              'frozen_fold_receipt': [str(FZ / tag / 'FOLD_RECEIPT.json'), sha(FZ / tag / 'FOLD_RECEIPT.json')],
              'frozen_scores_P_bitwise_equal': ident[tag], 'argv': vars(args), 'python': sys.version, 'gpu': torch.cuda.get_device_name(0)}
        sio.write_json(d / 'FOLD_RECEIPT.json', rr)
        fold_artifacts.update({str(q): sha(q) for q in (d / 'FOLD_RECEIPT.json', d / 'scores.npz', d / 'model.pt')}); found.append(tag)
    assert found == frec['folds'] or sorted(found) == sorted(frec['folds'])
    oof_sha = sio.save_npz(out / 'F10_OOF.npz', P=allpred, E_ts=a, symbols=syms)
    oof_equal = bool(Z0['P'].tobytes() == allpred.tobytes())
    tr = {'status': 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED', 'mode': 'RESCORE_FROZEN_MODELS', 'arm': frec['arm'], 'seed': seed,
          'fold_artifacts': fold_artifacts, 'folds': found, 'expected_folds': frec['expected_folds'], 'inputs': inputs, 'sources': sources,
          'pred_sha256': oof_sha, 'frozen_dir': str(FZ), 'frozen_receipt_sha256': sha(FZ / 'TRAIN_RECEIPT.json'), 'frozen_oof_sha256': frec['pred_sha256'],
          'oof_P_bitwise_equal_to_frozen': oof_equal, 'folds_P_bitwise_equal_to_frozen': ident, 'argv': vars(args), 'python': sys.version,
          'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    sio.write_json(out / 'TRAIN_RECEIPT.json', tr)
    if args.identity:
        ok = oof_equal and all(ident.values())
        print(f'F10_RESCORE_IDENTITY seed={seed} {"PASS" if ok else "FAIL"} oof_equal={oof_equal} folds_equal={sum(ident.values())}/{len(ident)}', flush=True)
        sys.exit(0 if ok else 2)
    print(f'F10_RESCORE_DONE seed={seed} oof={oof_sha[:16]} oof_equal_to_frozen={oof_equal} folds_equal={sum(ident.values())}/{len(ident)}', flush=True)


if __name__ == '__main__':
    main()
