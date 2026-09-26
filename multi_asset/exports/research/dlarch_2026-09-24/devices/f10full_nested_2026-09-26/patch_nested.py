#!/usr/bin/env python3
"""patch_nested.py -- build the R1.4 trainer (F10_FULL + per-fold nested epoch calibration) from the F10_FULL
trainer (db6771e3). Every change is named and asserted unique; nothing is applied unless all apply.

usage: patch_nested.py <base trainer (must hash to db6771e3...)> <out trainer>

The arm (prereg R1.1 / C1.1-C1.6, lead ruling 2026-09-26 18:xxZ "run R1.4 now"):
  pass 1 (calibration)  per fold, train on the EARLIEST 85% of the admissible training anchors with the
                        in-service recipe unchanged (8-epoch grid, C1.6); after every epoch score the LAST
                        15% (with a 24-anchor burn-in prefix, frozen 7bb39f8d L365) under hard rank, tau .1,
                        va = mean(nets) - 0.25 * ES5(nets) (frozen L367, LDD=0.25, LDC=0 recorded);
                        E* = the epoch picked by the UNROUNDED running max `if va > best_va` (frozen L374;
                        C1.4/C1.6 cite it as "L370"); the rounded argmax (frozen L428) is computed beside it
                        and any disagreement is named per fold.
  pass 2 (final)        re-initialise with the same seed and train on 100% of the admissible anchors for
                        E*+1 epochs (same cosine schedule, T_max=15), keep that state.
  --force-epoch K       IDENTITY CONTROL ONLY: use K instead of E*. With K=7, pass 2 must reproduce F10_FULL
                        bit-for-bit; pass 1's terminal model must reproduce the in-service NC fold bit-for-bit
                        (its test scores are saved as calib_terminal_scores.npz for that comparison).
The one semantic choice this code makes, named: the validation pass counts an unobservable held return as 0
(frozen YT = nan_to_num, L131) instead of refusing, which is what the training path does; the count of such
anchors is recorded per epoch.
"""
import hashlib
import pathlib
import sys

BASE_PIN = 'db6771e30fb7d1befcf9bb77f4c0504131fc0d491e02dc45bab15ed04e5d8e61'
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
assert hashlib.sha256(src.read_bytes()).hexdigest() == BASE_PIN, 'base trainer is not F10_FULL db6771e3'
s = src.read_text()


def sub(old, new, what):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit('ABORT (nothing written): %s appears %d times, expected 1' % (what, n))
    s = s.replace(old, new, 1)


# 1. flags
A = "    ap.add_argument('--band-temp-div', type=float, default=10.0)"
sub(A,
    "    ap.add_argument('--nested-epoch', action='store_true',\n"
    "                    help='R1.4 arm: per-fold nested epoch calibration on the earliest 85%% (pass 1), then '\n"
    "                         'retrain on 100%% for E*+1 epochs (pass 2). Requires --train-frac 1.0.')\n"
    "    ap.add_argument('--force-epoch', type=int, default=-1,\n"
    "                    help='IDENTITY CONTROL ONLY (with --nested-epoch): use this epoch instead of E*.')\n" + A,
    'flag anchor')

# 2. arm naming (after the train_frac suffix)
B = "        arm = f'{arm}_frac{args.train_frac:g}'\n"
sub(B, B +
    "    if args.nested_epoch:\n"
    "        assert args.arm == 'T0' and args.train_frac == 1.0, 'R1.4 is defined on the F10_FULL recipe'\n"
    "        arm = f'{arm}_nestep'\n"
    "    if args.force_epoch >= 0:\n"
    "        assert args.nested_epoch and 0 <= args.force_epoch < 8, '--force-epoch is the nested identity control'\n"
    "        arm = f'{arm}_forceep{args.force_epoch}'\n",
    'arm suffix anchor')

# 3. run_span: optional non-refusing mode + census, default behaviour byte-identical
sub("    def run_span(model, idx, mu, sd, tau, hard, burn):",
    "    def run_span(model, idx, mu, sd, tau, hard, burn, refuse_unobservable=True, census=None):",
    'run_span signature')
sub("        if unobservable and bool(torch.stack(unobservable).any().item()): raise ValueError('unknown held return: loss refused')",
    "        if census is not None: census['unobservable_anchors'] = int(torch.stack(unobservable).sum().item()) if unobservable else 0\n"
    "        if refuse_unobservable and unobservable and bool(torch.stack(unobservable).any().item()): raise ValueError('unknown held return: loss refused')",
    'run_span refusal')

# 4. pass 1 (calibration), inserted before the final pass; the final pass is the untouched recipe
C = "        cut = int(len(tr) * args.train_frac); tr1 = tr[:cut]; assert a[tr1[-1]] + 14400 <= cutoff\n"
CAL = '''        nested = None; n_final_epochs = 8; final_epoch_index = 7
        if args.nested_epoch:
            ccut = int(len(tr) * NESTED_CAL_FRAC); ctr1, cva1 = tr[:ccut], tr[ccut:]
            assert len(cva1) > 0 and a[cva1[-1]] + 14400 <= cutoff, 'validation slice must end before the embargo cutoff'
            cwin = []; crej = collections.Counter()
            for s in range(int(ctr1[0]) + 24, int(ctr1[-1]) - 96, 48):
                span = np.arange(s - 24, s + 96); ok, why = span_admissible(members, y, span, ready)
                if ok: cwin.append(span)
                else: crej[why['reason']] += 1
            if len(cwin) < 5: raise ValueError('fewer than 5 observable calibration windows')
            rowsel = np.concatenate([np.arange(st[i], st[i + 1]) for i in ctr1[::7]])[::3]
            xs = XT[torch.as_tensor(rowsel, device=dev)]; cmu = xs.mean(0); csd = xs.std(0) + 1e-6; del xs
            torch.manual_seed(args.seed); np.random.seed(args.seed); cmodel = Net().to(dev)
            copt = torch.optim.AdamW(cmodel.parameters(), lr=3e-4, weight_decay=1e-4)
            csched = torch.optim.lr_scheduler.CosineAnnealingLR(copt, T_max=15)
            vspan = np.concatenate([ctr1[-24:], cva1]).astype(np.int64)      # frozen 7bb39f8d L365: tr1[-BURN:] + va1
            best_va = -1e9; e370 = None; va_raw = []; va_curve = []; ccurve = []; vunobs = []
            for ep in range(8):                                              # C1.6: the 8-epoch grid
                cmodel.train(); vals = []; t0 = time.monotonic(); tau = .5 - (.5 - .1) * ep / 14
                for wi in np.random.permutation(len(cwin)):
                    nets, nsk, _b = run_span(cmodel, cwin[wi], cmu, csd, tau, False, 24)
                    es = torch.topk(-nets, max(1, int(np.ceil(.05 * len(nets))))).values.mean(); loss = -nets.mean() + .25 * es
                    if not bool(torch.isfinite(loss)): raise ValueError('nonfinite F10 loss (calibration)')
                    copt.zero_grad(); loss.backward()
                    nn.utils.clip_grad_norm_(cmodel.parameters(), 1.); copt.step(); vals.append(float(loss.detach()))
                csched.step()
                cmodel.eval(); vc = {}
                with torch.no_grad():                                        # frozen L364-L367, LDD = 0.25, LDC = 0
                    vn, _vs, _vb = run_span(cmodel, vspan, cmu, csd, .1, True, 24, refuse_unobservable=False, census=vc)
                    va = float(vn.mean() - .25 * torch.topk(-vn, max(1, int(np.ceil(.05 * len(vn))))).values.mean())
                va_raw.append(va); va_curve.append(round(va, 4)); vunobs.append(vc['unobservable_anchors'])
                if va > best_va: best_va, e370 = va, ep                      # frozen L374 (cited "L370"): UNROUNDED running max
                ccurve.append({'epoch_index': ep, 'train_loss': float(np.mean(vals)), 'alpha': float(cmodel.alpha().detach()),
                               'va': va, 'seconds': time.monotonic() - t0})
                log('F10_CALIB', arm, tag, args.seed, ccurve[-1])
            e428 = int(np.argmax(va_curve))                                   # frozen L428: argmax of the ROUNDED curve
            cmodel.eval(); cpred = np.full((len(te), w), np.nan, np.float32)
            with torch.no_grad():                                            # diagnostic: calib-terminal model = the 0.85 recipe
                for k, i in enumerate(te):
                    if st[i + 1] - st[i] < 50: continue
                    xx = torch.clamp((XT[st[i]:st[i + 1]] - cmu) / csd, -5, 5); cpred[k, ps[st[i]:st[i + 1]]] = cmodel.f(xx).squeeze(-1).cpu().numpy()
            calib_sha = sio.save_npz(target_dir / 'calib_terminal_scores.npz', P=cpred, rows=te, E_ts=a[te], symbols=t['symbols'])
            e_used = e370 if args.force_epoch < 0 else args.force_epoch
            nested = {'rule': 'frozen 7bb39f8d: va = mean(nets) - LDD*ES5(nets) on tr1[-24:]+va1, hard rank, tau .1; E* = unrounded running max',
                      'LDD': 0.25, 'LDC': 0.0, 'LDC_note': 'LDC = 0 => the conditional-tail branch (frozen L368-L372) is not entered',
                      'calib_frac': NESTED_CAL_FRAC, 'calib_train_anchors': int(len(ctr1)), 'val_anchors': int(len(cva1)), 'val_burn_anchors': 24,
                      'val_span_len': int(len(vspan)), 'calib_windows': len(cwin), 'calib_rejected': dict(crej),
                      'val_last_label_end': int(a[cva1[-1]] + 14400), 'cutoff': cutoff,
                      'va_raw': va_raw, 'va_curve_rounded4': va_curve, 'val_unobservable_anchors_per_epoch': vunobs,
                      'calib_curve': ccurve, 'epoch_L370': e370, 'epoch_L428': e428, 'selectors_agree': e370 == e428,
                      'best_va': best_va, 'force_epoch': args.force_epoch, 'epoch_used': e_used,
                      'calib_terminal_scores_sha256': calib_sha}
            sio.write_json(target_dir / 'NESTED_EPOCH.json', nested)
            log('F10_NESTED_EPOCH', arm, tag, args.seed, json.dumps({k: nested[k] for k in ('epoch_L370', 'epoch_L428', 'selectors_agree', 'epoch_used', 'va_curve_rounded4')}))
            del cmodel, copt, csched; torch.cuda.empty_cache()
            n_final_epochs = e_used + 1; final_epoch_index = e_used
'''
sub(C, CAL + C, 'final-pass cut line')

# 5. the final pass runs E*+1 epochs (8 when not nested: default path unchanged)
sub("        for ep in range(8):\n            model.train(); vals = []",
    "        for ep in range(n_final_epochs):\n            model.train(); vals = []", 'final epoch loop')

# 6. receipts carry the epoch actually kept (7 when not nested: default bytes unchanged)
sub("'input_dim': 171, 'fixed_epoch_index': 7})", "'input_dim': 171, 'fixed_epoch_index': final_epoch_index})", 'model.pt epoch')
sub("'grad_census': grad_census, 'fixed_epoch_index': 7,", "'grad_census': grad_census, 'fixed_epoch_index': final_epoch_index, 'nested_epoch': nested,", 'receipt epoch')
sub("'schedule_T_max': 15, 'updates_end_at_index': 7,", "'schedule_T_max': 15, 'updates_end_at_index': final_epoch_index,", 'receipt updates_end')

# 7. the constant
D = "REF = VENDOR / 'devices/news2_train_f10.py'\n"
sub(D, D + "NESTED_CAL_FRAC = 0.85                                            # R1.4 pass 1: the in-service fraction\n", 'constant anchor')

dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(s)
print('patched ->', dst, hashlib.sha256(dst.read_bytes()).hexdigest())
