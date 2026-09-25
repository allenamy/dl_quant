#!/usr/bin/env python3
"""dlarch_train_f10.py — arms T0 and T3 for docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md (ba54ec9f8).

DERIVED FROM news2_train_f10.py (sha asserted at run time). The recipe -- 171 columns, soft rank, cost
term, ES tail, fold list, embargo 60, TRAIN_FRAC .85, stride 48, span 120, burn 24, fixed epoch 7, tau
anneal, AdamW/cosine, per-fold mu/sd from the 1/21 subsample -- is UNCHANGED. The diff is archived.

  T0  the common baseline (lead 2026-09-24): mask WL the way production does before it reaches the
      utility -- w=[WL0,0,WL2], w/=w.sum() (combo_target.py L30). Nothing else changes. Because WL[1]
      (rev24) is zeroed, the z24 term of the utility vanishes identically, so T0's `r` IS production's
      pre-clamp zfc.
  T3  on top of T0, under lead's ruling (a): replace the self-made weight map (news2_train_f10.py
      L35-L36: de-mean -> L1 -> cap*tanh, then an external EMA) with the rn8 funding clamp
      (combo_target.py L33-34) followed by the PRODUCTION chain (combo_stage.py L78-L101) in its
      differentiable form, which does sel-mask / de-mean-on-sel / L1 / clip-cap / renorm / EMA(alpha=0.1)
      / dead band / exit mask itself. G3 (receipt G3_CHAIN_PARITY.json) already proved that
      differentiable chain reproduces the archived production book bit-for-bit at s=0.

G6/G6b: T3 adds NO parameters; `Net.a` (the learnable EMA rate) is RETAINED so the parameter count is
identical, but T3 does not use it -- so it is a DEAD parameter in T3 and alive in T0. That asymmetry is
named, and asserted: after every backward pass in T3, a.grad must be None or exactly 0, and a's value at
the end of the fold must equal its initial value.

READ-ONLY inputs under /dev/shm; ALL outputs under /workspace. No writes to /dev/shm, none to live trees.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_train_f10.py \
         PATH,HOME,LC_CTYPE --arm T0|T3 --seed N [--clamp-mode clamp|tanh] [--folds all|t1,t2,...]
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '2'; os.environ['OMP_NUM_THREADS'] = '2'
import pathlib, json, time, calendar, argparse, collections, hashlib, sys
import numpy as np
import torch
from torch import nn

W = pathlib.Path('/dev/shm/news2_2026-09-23')                      # READ-ONLY
OUT_ROOT = pathlib.Path('/workspace/dlarch_2026-09-24/T3')         # ALL writes land here
REF = W / 'devices/news2_train_f10.py'
REF_SHA = '66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'  # news2_train_f10.py, asserted in main()
NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
MASK_PATH = '/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)


sys.path.insert(0, str(W / 'devices'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f10_observability import span_admissible, measured_dot          # noqa: E402
from dlarch_chain_torch import chain_torch                           # noqa: E402


class Net(nn.Module):                                                # verbatim from news2_train_f10.py
    def __init__(self):
        super().__init__(); self.f = nn.Sequential(nn.Linear(171, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 1)); self.a = nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(self.f[-1].weight, 0, .001); nn.init.zeros_(self.f[-1].bias)
    def alpha(self): return .02 + .88 * torch.sigmoid(self.a)


def soft_rank(score, tau, hard=False):
    """news2_train_f10.py L33-L34 verbatim (the rank half of utility())."""
    z = (score - score.mean()) / (score.std() + 1e-8); n = len(z)
    return torch.argsort(torch.argsort(z)).to(z.dtype) / max(n - 1, 1) - .5 if hard else (torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1) - .5) / max(n - 1, 1) - .5


def utility(score, z24, zfd, wl, tau, hard=False):                   # verbatim from news2_train_f10.py L32-36
    rank = soft_rank(score, tau, hard); n = len(score)
    r = wl[0] * rank + wl[1] * z24 + wl[2] * zfd; r = r - r.mean(); u = r / (r.abs().sum() + 1e-8); cap = 2.5 / n; u = cap * torch.tanh(u / cap)
    return u - u.mean()


def mask_wl(wl):
    """combo_target.py L30, in torch: w=[WL0,0,WL2]; w/=w.sum(); degenerate -> [.5,0,.5]."""
    s = wl[0] + wl[2]
    if float(s) > 1e-12:
        return torch.stack([wl[0] / s, torch.zeros_like(wl[0]), wl[2] / s])
    return torch.tensor([.5, 0., .5], dtype=wl.dtype, device=wl.device)


def fold_specs(a):                                                   # verbatim
    utc = lambda y, m=1: calendar.timegm((y, m, 1, 0, 0, 0))
    out = [('2023', utc(2023), utc(2024)), ('2024', utc(2024), utc(2025))]
    for y in (2025, 2026):
        for m in range(1, 13):
            start = utc(y, m); end = utc(y + 1) if m == 12 else utc(y, m + 1)
            if start <= a[-1]: out.append((f'{y}{m:02d}', start, end))
    return out


def merge_folds(out, a, symbols, inputs, sources, seed, arm):         # verbatim + arm in the receipt
    pred = np.full((len(a), len(symbols)), np.nan, np.float32); found = []; fold_artifacts = {}
    for tag, start, end in fold_specs(a):
        p = out / tag; rp = p / 'FOLD_RECEIPT.json'
        if not rp.exists(): continue
        rec = json.load(open(rp)); assert rec['inputs'] == inputs and rec['sources'] == sources and rec['seed'] == seed and rec['fold'] == tag and rec['arm'] == arm
        assert sha(p / 'scores.npz') == rec['score_sha256'] and sha(p / 'model.pt') == rec['model_sha256']
        z = np.load(p / 'scores.npz'); rows = np.flatnonzero((a >= start) & (a < end))
        assert np.array_equal(z['rows'], rows) and np.array_equal(z['E_ts'], a[rows]) and np.array_equal(z['symbols'], symbols)
        assert z['P'].shape == (len(rows), len(symbols)); pred[rows] = z['P']; found.append(tag)
        fold_artifacts.update({str(q): sha(q) for q in (rp, p / 'scores.npz', p / 'model.pt')})
    tmp = out / 'F10_OOF.tmp.npz'; np.savez_compressed(tmp, P=pred, E_ts=a, symbols=symbols); tmp.replace(out / 'F10_OOF.npz')
    rr = {'status': 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' if len(found) == len(fold_specs(a)) else 'PARTIAL_FOLDS',
          'arm': arm, 'seed': seed, 'fold_artifacts': fold_artifacts, 'folds': found,
          'expected_folds': [s[0] for s in fold_specs(a)], 'inputs': inputs, 'sources': sources,
          'pred_sha256': sha(out / 'F10_OOF.npz')}
    tmp = out / 'TRAIN_RECEIPT.tmp.json'; tmp.write_text(json.dumps(rr, indent=2)); tmp.replace(out / 'TRAIN_RECEIPT.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=['T0', 'T3'], required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--clamp-mode', choices=['clamp', 'tanh'], default='clamp')
    ap.add_argument('--folds', default='all')
    ap.add_argument('--band-temp-div', type=float, default=10.0)      # s = band / this; prereg pins 10
    args = ap.parse_args()
    assert torch.cuda.is_available(), 'GPU required; refuse silently slow CPU fallback'
    assert sha(REF) == REF_SHA, f'the reference recipe changed: {sha(REF)[:16]} != {REF_SHA[:16]}'
    arm = args.arm if args.arm == 'T0' else f'T3_{args.clamp_mode}'
    r = W / 'work'
    out = OUT_ROOT / arm / f'f10_s{args.seed}'; out.mkdir(parents=True, exist_ok=True)
    files = [r / 'NEWS_FEATURES.npz', NEWT, r / 'legs.npz', W / 'receipts/P2B_FEATURES.json', W / 'receipts/P3_LEGS.json']
    inputs = {str(p): sha(p) for p in files}
    sources = {str(p): sha(p) for p in (pathlib.Path(os.path.abspath(__file__)), REF,
                                       pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / 'dlarch_chain_torch.py',
                                       W / 'devices/f10_observability.py', W / 'devices/nc_hist_features.py',
                                       W / 'devices/nc_legs.py', W / 'devices/nc_p2_build.py')}
    assert inputs[str(files[1])] == NEWT_SHA and json.load(open(files[3]))['sha256'] == inputs[str(files[0])] and json.load(open(files[4]))['sha256'] == inputs[str(files[2])]
    F = np.load(files[0]); T = np.load(files[1], allow_pickle=True); leg = np.load(files[2])
    a = F['anchors'].astype(np.int64)
    assert np.array_equal(T['symbols'], F['symbols']) and np.array_equal(leg['E_ts'], a) and np.array_equal(leg['symbols'], F['symbols'])
    ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(F['symbols'])), np.nan, np.float32)
    ix = np.searchsorted(ya, a); okk = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a); y[okk] = T['y4s'][ix[okk]]
    cnt = F['count']; off = F['off']; pa = np.repeat(np.arange(len(a)), cnt).astype(int); ps = F['m'].astype(int)
    members = [ps[off[i]:off[i + 1]] for i in range(len(a))]; st = np.searchsorted(pa, np.arange(len(a) + 1)); n, w = y.shape
    assert np.all(np.diff(a) == 14400)
    x = np.concatenate([F['X82'].astype(np.float32), F['X89']], 1).astype(np.float32); assert x.shape == (len(pa), 171) and np.isfinite(x).all()
    t = {'symbols': F['symbols']}
    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x
    YVALID = torch.from_numpy(np.isfinite(y)).to(dev); YT = torch.from_numpy(np.where(np.isfinite(y), y, 0.)).to(dev)
    Z24 = torch.from_numpy(np.nan_to_num(leg['Z24'], nan=0.)).to(dev)
    ZFD = torch.from_numpy(np.nan_to_num(leg['ZFD'], nan=0.)).to(dev)
    WLraw = torch.from_numpy(leg['WL']).to(dev)
    ready = leg['ready']; requested = None if args.folds == 'all' else set(args.folds.split(','))
    cols = [torch.as_tensor(ps[st[i]:st[i + 1]], device=dev) for i in range(n)]
    # ---- masked seats (T0 change; T3 inherits it) + the WL census for G2 ----
    WL = torch.stack([mask_wl(WLraw[i]) for i in range(n)])
    wl_diff_rows = int((torch.abs(WL - WLraw).max(1).values > 0).sum().item())
    seat_census = {'raw_WL_mean': [float(v) for v in WLraw.mean(0)], 'masked_WL_mean': [float(v) for v in WL.mean(0)],
                   'anchors_where_WL_changed': wl_diff_rows, 'n_anchors': int(n)}
    log('seat census', json.dumps(seat_census))
    assert wl_diff_rows > 0, 'G2 SWITCH_NOT_WIRED: masking changed WL on zero anchors'
    # ---- T3-only fields: sel (from QV) and LIVE_MASK (book universe), both known 0/1 ----
    extra = {}
    if args.arm == 'T3':
        from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
        assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
        cfg = json.load(open(W / 'inputs/bundle_config.json'))['params']
        mk = np.load(MASK_PATH); assert np.array_equal(mk['ts'].astype(np.int64), a)
        crypto = np.load(W / 'receipts/P1_members_2025H2on.npz')['crypto']
        cand = mk['mask'] & crypto[None, :]
        universe = np.load(UNIVERSE_PATH)
        inuni = a <= universe['ts'][-1]
        legal = np.zeros((n, w), bool)
        legal[inuni] = align_universe(a[inuni], t['symbols'], universe) & cand[inuni]
        QVn = leg['QV']
        sel_list = [np.isfinite(QVn[i][members[i]]) & (QVn[i][members[i]] >= cfg['qv4h_min']) for i in range(n)]
        sel_ok = np.array([s.sum() >= cfg['sel_min'] for s in sel_list])
        extra = {'cfg': cfg, 'legal': torch.from_numpy(legal).to(dev),
                 'sel': [torch.from_numpy(s).to(dev) for s in sel_list], 'sel_ok': sel_ok,
                 's_temp': cfg['band'] / args.band_temp_div,
                 'anchors_outside_universe': int((~inuni).sum()),
                 'anchors_sel_below_min': int((~sel_ok).sum())}
        inputs[MASK_PATH] = sha(MASK_PATH); inputs[UNIVERSE_PATH] = UNIVERSE_SHA
        log('T3 fields', json.dumps({k: extra[k] for k in ('anchors_outside_universe', 'anchors_sel_below_min', 's_temp')}))

    RN8T = torch.from_numpy(leg['RN8'].astype(np.float64)).to(dev).float() if args.arm == 'T3' else None

    def run_span(model, idx, mu, sd, tau, hard, burn):
        held = torch.zeros(w, device=dev); alpha = model.alpha(); nets = []; unobservable = []
        n_skip = 0; band_open = 0; band_book = 0
        for k, i in enumerate(idx):
            if not ready[i]: raise ValueError('missing causal leg in span')
            xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5); score = model.f(xx).squeeze(-1)
            if args.arm == 'T0':
                u = utility(score, Z24[i, cols[i]], ZFD[i, cols[i]], WL[i], tau, hard)
                target = torch.zeros(w, device=dev).scatter(0, cols[i], u); new = (1 - alpha) * held + alpha * target
            else:
                if not extra['sel_ok'][i]: n_skip += 1; continue          # producer would not have written a book
                zf = soft_rank(score, tau, hard)
                rr_ = WL[i][0] * zf + WL[i][2] * ZFD[i, cols[i]]
                rn = RN8T[i, cols[i]]
                rr_ = torch.where((rr_ < 0) & torch.isfinite(rn) & (rn <= -.001), torch.zeros((), device=dev, dtype=rr_.dtype), rr_)
                cens = {}
                new = chain_torch(rr_, extra['sel'][i], held, cols[i], w, extra['legal'][i],
                                  extra['cfg']['cap_mult'], extra['cfg']['alpha'], extra['cfg']['band'],
                                  extra['s_temp'], args.clamp_mode, census=cens)
                band_open += cens.get('band_open_cells', 0); band_book += cens.get('book_cells', 0)
                if new is None: n_skip += 1; continue                    # degenerate signal: producer returns None
            unobservable.append(((new != 0) & ~YVALID[i]).any())
            net = 1e4 * (new * YT[i]).sum() - 3.52 * torch.sqrt((new - held) ** 2 + 1e-12).sum()
            if k >= burn: nets.append(net)
            held = new
        if unobservable and bool(torch.stack(unobservable).any().item()): raise ValueError('unknown held return: loss refused')
        if not nets: raise ValueError('span produced no scored anchors')
        return torch.stack(nets), n_skip, (band_open, band_book)

    allpred = np.full((n, w), np.nan, np.float32); reports = []
    nparam = sum(p.numel() for p in Net().parameters())
    for tag, start, end in fold_specs(a):
        if requested is not None and tag not in requested: continue
        target_dir = out / tag; result = target_dir / 'FOLD_RECEIPT.json'
        if result.exists():
            old = json.load(open(result)); assert old['inputs'] == inputs and old['sources'] == sources and old['seed'] == args.seed and old['arm'] == arm, 'resume identity changed'
            assert sha(target_dir / 'scores.npz') == old['score_sha256'] and sha(target_dir / 'model.pt') == old['model_sha256']
            z = np.load(target_dir / 'scores.npz'); allpred[z['rows']] = z['P']; reports.append(old); continue
        target_dir.mkdir(exist_ok=False, parents=True)
        te = np.flatnonzero((a >= start) & (a < end)); first = int(te[0]); cutoff = int(a[first]) - 60 * 14400
        tr = np.flatnonzero((a + 14400 <= cutoff) & ready & (np.diff(st) >= 50)); assert len(tr) >= 300
        cut = int(len(tr) * .85); tr1 = tr[:cut]; assert a[tr1[-1]] + 14400 <= cutoff
        windows = []; rejected = collections.Counter()
        for s in range(int(tr1[0]) + 24, int(tr1[-1]) - 96, 48):
            span = np.arange(s - 24, s + 96); ok, why = span_admissible(members, y, span, ready)
            if ok: windows.append(span)
            else: rejected[why['reason']] += 1
        admission = {'fold': tag, 'accepted_windows': len(windows), 'rejected': dict(rejected), 'train_anchors': len(tr1),
                     'max_train_label_end': int(a[tr1[-1]] + 14400), 'test_start': int(a[first]), 'cutoff': cutoff}
        (target_dir / 'ADMISSION.json').write_text(json.dumps(admission, indent=2)); log('F10 admission', arm, args.seed, admission)
        if len(windows) < 5: raise ValueError('fewer than 5 observable training windows')
        rowsel = np.concatenate([np.arange(st[i], st[i + 1]) for i in tr1[::7]])[::3]
        xs = XT[torch.as_tensor(rowsel, device=dev)]; mu = xs.mean(0); sd = xs.std(0) + 1e-6; del xs
        torch.manual_seed(args.seed); np.random.seed(args.seed); model = Net().to(dev)
        a_init = float(model.a.detach())
        opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=15)
        started = time.monotonic(); curve = []; grad_census = []; skipped_total = 0
        for ep in range(8):
            model.train(); vals = []; t0 = time.monotonic(); tau = .5 - (.5 - .1) * ep / 14
            bo = bb = 0; a_grad_nonzero = 0
            for wi in np.random.permutation(len(windows)):
                nets, nsk, (o_, b_) = run_span(model, windows[wi], mu, sd, tau, False, 24); skipped_total += nsk; bo += o_; bb += b_
                es = torch.topk(-nets, max(1, int(np.ceil(.05 * len(nets))))).values.mean(); loss = -nets.mean() + .25 * es
                if not bool(torch.isfinite(loss)): raise ValueError('nonfinite F10 loss')
                opt.zero_grad(); loss.backward()
                if args.arm == 'T3' and model.a.grad is not None and float(model.a.grad.abs().sum()) != 0.0: a_grad_nonzero += 1
                nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step(); vals.append(float(loss.detach()))
            sched.step()
            rr = {'epoch_index': ep, 'train_loss': float(np.mean(vals)), 'alpha': float(model.alpha().detach()), 'seconds': time.monotonic() - t0}
            # G4 measures how much of the BOOK the dead band freezes -- not parameter-gradient sparsity.
            # For T0 there is no band, so the fraction is 1.0 BY CONSTRUCTION and is reported as such,
            # not computed from a quantity that cannot vary.
            g4 = {'epoch_index': ep, 'a_grad_nonzero_steps': a_grad_nonzero}
            if args.arm == 'T0':
                g4['band_open_frac_of_book'] = 1.0; g4['basis'] = 'no dead band in T0: 1.0 by construction'
            else:
                g4['band_open_frac_of_book'] = (bo / bb) if bb else None
                g4['band_open_cells'] = bo; g4['book_cells'] = bb; g4['basis'] = 'measured inside the differentiable chain'
            curve.append(rr); grad_census.append(g4)
            log('F10', arm, tag, args.seed, rr, 'g4_band_open', g4['band_open_frac_of_book'])
            (target_dir / 'PROGRESS.json').write_text(json.dumps({'curve': curve, 'grad_census': grad_census}, indent=2, allow_nan=False))
        a_final = float(model.a.detach())
        if args.arm == 'T3':
            assert sum(g['a_grad_nonzero_steps'] for g in grad_census) == 0, 'G6b: a received a gradient in T3'
            assert a_final == a_init, f'G6b: a moved in T3 ({a_init} -> {a_final})'
        model.eval(); pred = np.full((len(te), w), np.nan, np.float32)
        with torch.no_grad():
            for k, i in enumerate(te):
                if st[i + 1] - st[i] < 50: continue
                xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5); pred[k, ps[st[i]:st[i + 1]]] = model.f(xx).squeeze(-1).cpu().numpy()
        torch.save({'state_dict': model.state_dict(), 'mu': mu, 'sd': sd, 'input_dim': 171, 'fixed_epoch_index': 7}, target_dir / 'model.pt')
        np.savez_compressed(target_dir / 'scores.npz', P=pred, rows=te, E_ts=a[te], symbols=t['symbols']); allpred[te] = pred
        rr = {'status': 'F10_OOF_SCORES_NOT_COMBO_PNL', 'arm': arm, 'clamp_mode': args.clamp_mode if args.arm == 'T3' else None,
              'seed': args.seed, 'rng_rule': 'constant seed per fold', 'fold': tag, 'inputs': inputs, 'sources': sources,
              'admission': admission, 'curve': curve, 'grad_census': grad_census, 'fixed_epoch_index': 7,
              'schedule_T_max': 15, 'updates_end_at_index': 7, 'test_anchors': len(te),
              'scored_pairs': int(np.isfinite(pred).sum()), 'score_label_missing_pairs': int((np.isfinite(pred) & ~np.isfinite(y[te])).sum()),
              'param_count': nparam, 'a_init': a_init, 'a_final': a_final, 'seat_census': seat_census,
              'anchors_skipped_in_spans': skipped_total, 't3_extra': {k: extra[k] for k in ('anchors_outside_universe', 'anchors_sel_below_min', 's_temp')} if args.arm == 'T3' else None,
              'score_sha256': sha(target_dir / 'scores.npz'), 'model_sha256': sha(target_dir / 'model.pt'),
              'elapsed_seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(0)}
        for p, hsh in inputs.items(): assert sha(p) == hsh
        for p, hsh in sources.items(): assert sha(p) == hsh
        result.write_text(json.dumps(rr, indent=2, allow_nan=False)); reports.append(rr); log('F10_FOLD_DONE', arm, tag, args.seed)
        merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm); del model, opt, sched; torch.cuda.empty_cache()
    merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm)
    print(f"DLARCH_TRAIN_DONE arm={arm} seed={args.seed} params={nparam} out={out} "
          f"oof_sha={sha(out / 'F10_OOF.npz')[:16]} receipt_sha={sha(out / 'TRAIN_RECEIPT.json')[:16]}", flush=True)


if __name__ == '__main__':
    main()
