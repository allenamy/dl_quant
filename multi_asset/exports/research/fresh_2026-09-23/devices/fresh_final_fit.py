"""FRESH deployment-candidate fit: the SAME rule as the FRESH OOF folds, but at the end of the data.
Training-label cutoff for both legs = last available label on the axis − 6 anchors (PREREG §1 E, task brief §5).

King : fresh_train_king.py's params / target / random_state, one fit on every row with a+4h <= cutoff.
F10  : fresh_train_f10.py's Net / utility / run_span / admission / mu-sd sampling / fixed epoch 7, seed 42,
       gradient window = 100 % of the admissible training anchors (PREREG §1 F).
       Net and utility are IMPORTED from fresh_train_f10.py; run_span is compiled from the literal source lines of
       fresh_train_f10.main (boundary text and the file sha asserted), so this device cannot drift from the trainer.

No deployment. usage: python -u fresh_final_fit.py --leg king|f10 [--seed 42]
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '2'; os.environ['OMP_NUM_THREADS'] = '2'
import sys, json, time, argparse, inspect, textwrap, collections, hashlib, pathlib
import numpy as np

W = pathlib.Path('/dev/shm/fresh_2026-09-23')
N = pathlib.Path('/dev/shm/news_2026-09-23')
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
EMBARGO = 6
PREREG = {'path': 'docs/PREREG_fresh_models_newS_2026-09-23.md', 'commit': 'b6e682e0a'}
sys.path.insert(0, str(W / 'devices'))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


def load_axis():
    F = np.load(N / 'work/NEWS_FEATURES.npz'); frec = json.load(open(N / 'receipts/P2B_FEATURES.json'))
    assert sha(N / 'work/NEWS_FEATURES.npz') == frec['sha256'] and sha(NEWT) == NEWT_SHA
    T = np.load(NEWT, allow_pickle=True)
    a = F['anchors'].astype(np.int64); syms = F['symbols']
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(syms)), np.nan, np.float32)
    ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a); y[ok] = T['y4s'][ix[ok]]
    return F, T, a, syms, y


def final_cutoff(a, y):
    """last available label on the axis, minus EMBARGO anchors."""
    has = np.isfinite(y).any(1)
    assert has.any(), 'no finite label anywhere'
    last_label_end = int(a[np.flatnonzero(has)[-1]] + 14400)
    return last_label_end - EMBARGO * 14400, last_label_end


def do_king(cut, a, F, y, syms):
    from scipy.stats import rankdata
    import lightgbm as lgb
    out = W / 'work/final'; out.mkdir(exist_ok=True)
    off = F['off']; cnt = F['count']
    pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
    target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))
    for i in range(len(a)):
        ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
        if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=0)
    train = np.flatnonzero(a + 14400 <= cut); tr = np.isin(pa, train) & np.isfinite(target)
    assert tr.sum() > 1000
    t0 = time.monotonic(); log('KING final fit', int(tr.sum()), 'rows, cutoff', cut)
    model = lgb.LGBMRegressor(**params).fit(x[tr], target[tr])
    mp = out / 'king_final.txt'; model.booster_.save_model(str(mp))
    rr = {'leg': 'king', 'model_path': str(mp), 'model_sha256': sha(mp), 'recipe': params, 'prereg': PREREG,
          'max_train_label_end': int(a[pa[tr]].max() + 14400), 'max_train_label_end_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(a[pa[tr]].max() + 14400))),
          'cutoff': cut, 'embargo_anchors': EMBARGO, 'train_pairs': int(tr.sum()), 'train_anchors': int(len(train)),
          'seconds': time.monotonic() - t0, 'lightgbm': lgb.__version__, 'numpy': np.__version__,
          'inputs': {str(N / 'work/NEWS_FEATURES.npz'): sha(N / 'work/NEWS_FEATURES.npz'), str(NEWT): NEWT_SHA},
          'source_sha': {str(pathlib.Path(__file__)): sha(os.path.abspath(__file__)), str(W / 'devices/fresh_train_king.py'): sha(W / 'devices/fresh_train_king.py')},
          'status': 'DEPLOYMENT_CANDIDATE_NOT_DEPLOYED'}
    assert rr['max_train_label_end'] <= cut
    (out / 'KING_FINAL_RECEIPT.json').write_text(json.dumps(rr, indent=2, allow_nan=False)); log('KING_FINAL_DONE', json.dumps(rr)[:400])


def do_f10(cut, seed, a, F, y, syms):
    import torch
    from torch import nn
    import fresh_train_f10 as TF
    assert torch.cuda.is_available(), 'GPU required'
    TFSRC = W / 'devices/fresh_train_f10.py'; tf_sha = sha(TFSRC)
    src = inspect.getsource(TF.main).split('\n')
    i0 = [i for i, l in enumerate(src) if l.strip().startswith('def run_span(')]
    assert len(i0) == 1, 'run_span not found exactly once in fresh_train_f10.main'
    i1 = [i for i, l in enumerate(src) if l.strip() == 'return torch.stack(nets)']
    assert len(i1) == 1 and i1[0] > i0[0], 'run_span end line not unique'
    body = textwrap.dedent('\n'.join(src[i0[0]:i1[0] + 1]))
    from f10_observability import span_admissible
    out = W / 'work/final'; out.mkdir(exist_ok=True)
    leg = np.load(W / 'work/legs.npz'); lrec = json.load(open(W / 'receipts/P3_LEGS.json'))
    assert sha(W / 'work/legs.npz') == lrec['sha256'] and np.array_equal(leg['E_ts'].astype(np.int64), a)
    off = F['off']; cnt = F['count']
    pa = np.repeat(np.arange(len(a)), cnt).astype(int); ps = F['m'].astype(int)
    members = [ps[off[i]:off[i + 1]] for i in range(len(a))]; st = np.searchsorted(pa, np.arange(len(a) + 1)); n, w = y.shape
    x = np.concatenate([F['X82'].astype(np.float32), F['X89']], 1).astype(np.float32); assert x.shape == (len(pa), 171) and np.isfinite(x).all()
    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x
    YVALID = torch.from_numpy(np.isfinite(y)).to(dev); YT = torch.from_numpy(np.where(np.isfinite(y), y, 0.)).to(dev)
    Z24 = torch.from_numpy(np.nan_to_num(leg['Z24'], nan=0.)).to(dev); ZFD = torch.from_numpy(np.nan_to_num(leg['ZFD'], nan=0.)).to(dev); WL = torch.from_numpy(leg['WL']).to(dev)
    cols = [torch.as_tensor(ps[st[i]:st[i + 1]], device=dev) for i in range(n)]; ready = leg['ready']
    ns = {'torch': torch, 'dev': dev, 'ready': ready, 'XT': XT, 'st': st, 'Z24': Z24, 'ZFD': ZFD, 'WL': WL, 'cols': cols, 'YVALID': YVALID, 'YT': YT, 'w': w, 'utility': TF.utility}
    exec(compile(body, str(TFSRC), 'exec'), ns); run_span = ns['run_span']
    tr = np.flatnonzero((a + 14400 <= cut) & ready & (np.diff(st) >= 50)); assert len(tr) >= 300
    tr1 = tr; assert a[tr1[-1]] + 14400 <= cut
    windows = []; rejected = collections.Counter()
    for s in range(int(tr1[0]) + 24, int(tr1[-1]) - 96, 48):
        span = np.arange(s - 24, s + 96); ok, why = span_admissible(members, y, span, ready)
        if ok: windows.append(span)
        else: rejected[why['reason']] += 1
    admission = {'fold': 'FINAL', 'accepted_windows': len(windows), 'rejected': dict(rejected), 'train_anchors': len(tr1),
                 'max_train_label_end': int(a[tr1[-1]] + 14400), 'cutoff': cut, 'embargo_anchors': EMBARGO, 'train_frac': 1.0}
    log('F10 final admission', seed, admission)
    assert len(windows) >= 5
    rowsel = np.concatenate([np.arange(st[i], st[i + 1]) for i in tr1[::7]])[::3]; xs = XT[torch.as_tensor(rowsel, device=dev)]; mu = xs.mean(0); sd = xs.std(0) + 1e-6; del xs
    torch.manual_seed(seed); np.random.seed(seed); model = TF.Net().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4); sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=15)
    started = time.monotonic(); curve = []
    for ep in range(8):
        model.train(); vals = []; t0 = time.monotonic(); tau = .5 - (.5 - .1) * ep / 14
        for wi in np.random.permutation(len(windows)):
            nets = run_span(model, windows[wi], mu, sd, tau, False, 24); es = torch.topk(-nets, max(1, int(np.ceil(.05 * len(nets))))).values.mean(); loss = -nets.mean() + .25 * es
            assert bool(torch.isfinite(loss)), 'nonfinite F10 loss'
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step(); vals.append(float(loss.detach()))
        sched.step(); rr = {'epoch_index': ep, 'train_loss': float(np.mean(vals)), 'alpha': float(model.alpha().detach()), 'seconds': time.monotonic() - t0}
        curve.append(rr); log('F10 FINAL', seed, rr); (out / f'F10_FINAL_PROGRESS_s{seed}.json').write_text(json.dumps(curve, indent=2, allow_nan=False))
    mp = out / f'f10_final_s{seed}.pt'
    torch.save({'state_dict': model.state_dict(), 'mu': mu, 'sd': sd, 'input_dim': 171, 'fixed_epoch_index': 7}, mp)
    rr = {'leg': 'f10', 'seed': seed, 'model_path': str(mp), 'model_sha256': sha(mp), 'prereg': PREREG, 'admission': admission, 'curve': curve,
          'fixed_epoch_index': 7, 'schedule_T_max': 15, 'max_train_label_end_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(admission['max_train_label_end'])),
          'run_span_compiled_from': {'file': str(TFSRC), 'sha256': tf_sha, 'first_line': src[i0[0]].strip(), 'last_line': src[i1[0]].strip(), 'n_lines': i1[0] - i0[0] + 1},
          'inputs': {str(N / 'work/NEWS_FEATURES.npz'): sha(N / 'work/NEWS_FEATURES.npz'), str(NEWT): NEWT_SHA, str(W / 'work/legs.npz'): lrec['sha256']},
          'source_sha': {str(pathlib.Path(__file__)): sha(os.path.abspath(__file__)), str(TFSRC): tf_sha, str(W / 'devices/f10_observability.py'): sha(W / 'devices/f10_observability.py')},
          'elapsed_seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
          'status': 'DEPLOYMENT_CANDIDATE_NOT_DEPLOYED'}
    (out / f'F10_FINAL_RECEIPT_s{seed}.json').write_text(json.dumps(rr, indent=2, allow_nan=False)); log('F10_FINAL_DONE', json.dumps({k: rr[k] for k in ('model_sha256', 'max_train_label_end_iso')}))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--leg', choices=('king', 'f10'), required=True); ap.add_argument('--seed', type=int, default=42); args = ap.parse_args()
    F, T, a, syms, y = load_axis()
    cut, last = final_cutoff(a, y)
    log('axis last anchor', int(a[-1]), 'last available label end', last, 'cutoff', cut)
    (W / 'work').mkdir(exist_ok=True); (W / 'work/final').mkdir(exist_ok=True)
    (W / 'work/final/CUTOFF.json').write_text(json.dumps({'axis_last_anchor': int(a[-1]), 'last_available_label_end': last, 'embargo_anchors': EMBARGO, 'cutoff': cut,
                                                          'cutoff_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(cut)),
                                                          'rule': 'training-label cutoff = last available label on the axis − 6 anchors'}, indent=2))
    if args.leg == 'king': do_king(cut, a, F, y, syms)
    else: do_f10(cut, args.seed, a, F, y, syms)


if __name__ == '__main__':
    main()
