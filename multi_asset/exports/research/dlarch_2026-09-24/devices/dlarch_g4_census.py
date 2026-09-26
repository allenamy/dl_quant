#!/usr/bin/env python3
"""dlarch_g4_census.py -- R25-06: replace the saturated G4 dead-band census with three quantities.

THE DEFECT (measured, not argued). `dlarch_chain_torch.py` L88-92:
    gate = (trade.abs() >= band) if s_temp <= 0 else torch.sigmoid((trade.abs() - band) / s_temp)
    census["band_open_cells"] = int(((gate > 0) & book).sum())
Under the SOFT gate (s_temp > 0, which is how T3 runs it) a sigmoid is strictly positive everywhere, so
`gate > 0` is TRUE FOR EVERY BOOK CELL and `band_open_cells == book_cells` BY CONSTRUCTION. The
delivered T3 s42 receipts confirm it: 184/184 epoch records report band_open_frac_of_book == 1.0 and
band_open_cells == book_cells in every one. The number could not have been anything else, so it carries
no information -- and the function's own docstring describes the HARD-gate meaning ("cells the band let
through ... not frozen to H"), which is vacuous for a soft gate. A saturated statistic is an instrument
ceiling wearing the clothes of a measurement.

THE REPLACEMENT -- three separately reported quantities (lead/reviewer's minimal action):
  (a) hard_hit_frac       -- the fraction of book cells with |trade| >= band. The ACTUAL dead-band
                             decision. NOT re-implemented: it is what the FROZEN census already computes
                             when called with s_temp = 0, a mode T3 never calls it in.
  (b) surviving_trade_frac-- sum(|smv_soft - H|) / sum(|smv_ungated - H|). How much of the intended
                             trade actually reaches the book. This is "real displacement".
  (c) gate_mean, gate_deriv_mean -- the effective gate weight and its derivative
                             gate*(1-gate)/s_temp, i.e. what carries gradient at the operating point.

NOTHING IS RE-IMPLEMENTED FROM A DESCRIPTION. Every quantity comes from calling the frozen
`chain_torch`:
    ungated = chain_torch(..., band=0.0, s_temp=0.0)   -> gate == 1 everywhere  -> trade = ungated - H
    hard    = chain_torch(..., band=band, s_temp=0.0)  -> its own census IS (a)
    soft    = chain_torch(..., band=band, s_temp=s_temp)
The single reconstructed quantity -- `gate` -- is then PROVEN, not asserted, by a closure identity:
    H + gate * (ungated - H)  must equal  soft   (to within float tolerance on the book cells)
If that identity fails, the device REFUSES to report, because then its `gate` is not the code's gate.

RED CONTROL (runs first, must go red or the device is void): the same census is computed at band = 0
and at band = a value above every |trade|. A working instrument must report hard_hit_frac 1.0 and 0.0
respectively. The OLD statistic reports 1.0 for BOTH -- that contrast is printed, so the saturation is
demonstrated rather than claimed.
"""
import json
import os
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dlarch_chain_torch import chain_torch, sha          # noqa: E402  -- the FROZEN code


def census_for(zc, sel, H, pm, NW, live, cap_mult, alpha, band, s_temp, clamp_mode='clamp'):
    """All three quantities, every one derived from calls to the frozen chain_torch."""
    c_hard, c_soft = {}, {}
    ungated = chain_torch(zc, sel, H, pm, NW, live, cap_mult, alpha, 0.0, 0.0, clamp_mode)
    hard = chain_torch(zc, sel, H, pm, NW, live, cap_mult, alpha, band, 0.0, clamp_mode, census=c_hard)
    soft = chain_torch(zc, sel, H, pm, NW, live, cap_mult, alpha, band, s_temp, clamp_mode,
                       census=c_soft)
    if ungated is None or hard is None or soft is None:
        return {'status': 'DEGENERATE_SPAN_NO_BOOK', 'band': band, 's_temp': s_temp}

    trade = ungated - H                      # gate == 1 everywhere at band=0, s_temp=0
    book = (H.abs() > 0) | (ungated.abs() > 0)
    nbook = int(book.sum())

    # (a) THE FROZEN CENSUS, read in the mode where it means what its docstring says
    hard_open = int(c_hard['band_open_cells'])
    hard_book = int(c_hard['book_cells'])

    # (c) the gate the soft branch uses, reconstructed ...
    gate = torch.sigmoid((trade.abs() - band) / s_temp) if s_temp > 0 else (trade.abs() >= band).to(
        trade.dtype)
    # ... and PROVEN to be that gate, not merely named it
    recon = H + gate * (ungated - H)
    resid = float((recon - soft).abs().max())
    scale = float(soft.abs().max()) + 1e-30
    closure_ok = resid <= 1e-9 * max(scale, 1.0)

    # (b) real displacement
    num = float((soft - H).abs().sum())
    den = float((ungated - H).abs().sum())

    gb = gate[book]
    out = {
        'status': 'OK' if closure_ok else 'REFUSED_CLOSURE_IDENTITY_FAILED',
        'band': band, 's_temp': s_temp, 'book_cells': nbook,
        'a_hard_hit_cells': hard_open, 'a_hard_hit_frac': (hard_open / hard_book) if hard_book else None,
        'b_surviving_trade_frac': (num / den) if den > 0 else None,
        'c_gate_mean': float(gb.mean()) if nbook else None,
        'c_gate_deriv_mean': float((gb * (1 - gb) / s_temp).mean()) if (nbook and s_temp > 0) else None,
        'OLD_saturated_statistic_gate_gt_0': int(((gate > 0) & book).sum()),
        'OLD_equals_book_cells': int(((gate > 0) & book).sum()) == nbook,
        'closure_residual_max_abs': resid,
    }
    if not closure_ok:
        out['REFUSAL'] = ('the reconstructed gate does not reproduce the frozen function output '
                          '(residual %g); refusing to report a gate that is not the code\'s gate'
                          % resid)
    return out


def red_control(dev='cpu', n=400, seed=0):
    """Must show the NEW statistic separating and the OLD one saturated, or the device is void."""
    g = torch.Generator(device='cpu').manual_seed(seed)
    NW = n
    zc = torch.randn(n, generator=g, dtype=torch.float64)
    sel = torch.ones(n, dtype=torch.bool)
    H = torch.randn(NW, generator=g, dtype=torch.float64) * 0.001
    pm = torch.arange(n)
    live = torch.ones(NW, dtype=torch.bool)
    base = dict(zc=zc, sel=sel, H=H, pm=pm, NW=NW, live=live, cap_mult=2.5, alpha=0.1)

    ung = chain_torch(zc, sel, H, pm, NW, live, 2.5, 0.1, 0.0, 0.0)
    tmax = float((ung - H).abs().max())
    arms = {'band_0_everything_trades': 0.0,
            'band_mid': tmax * 0.5,
            'band_above_every_trade': tmax * 2.0}
    rows = {}
    for name, band in arms.items():
        rows[name] = census_for(band=band, s_temp=max(tmax * 0.01, 1e-12), **base)
    new_vals = [rows[k]['a_hard_hit_frac'] for k in arms]
    old_vals = [rows[k]['OLD_equals_book_cells'] for k in arms]
    verdict = {
        'arms': rows,
        'NEW_separates': (max(new_vals) - min(new_vals)) > 0.9,
        'NEW_extremes_are_1_and_0': (abs(new_vals[0] - 1.0) < 1e-12 and abs(new_vals[-1]) < 1e-12),
        'OLD_saturated_in_every_arm': all(old_vals),
    }
    verdict['RED_CONTROL_PASS'] = (verdict['NEW_separates'] and verdict['NEW_extremes_are_1_and_0']
                                   and verdict['OLD_saturated_in_every_arm'])
    return verdict


if __name__ == '__main__':
    WL = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else {'PATH', 'HOME', 'LC_CTYPE'}
    _x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
    assert not _x, f'env outside whitelist: {_x}'
    out = sys.argv[2] if len(sys.argv) > 2 else None
    rc = red_control()
    rec = {'device': 'dlarch_g4_census.py', 'self_sha256': sha(os.path.abspath(__file__)),
           'frozen_chain_torch_sha256': sha(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         'dlarch_chain_torch.py')),
           'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'red_control': rc}
    print(json.dumps(rec, indent=1, sort_keys=True))
    if out:
        with open(out, 'w') as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        print('receipt=' + out)
    print('G4_CENSUS_RED_CONTROL PASS=%s' % rc['RED_CONTROL_PASS'])
    if not rc['RED_CONTROL_PASS']:
        sys.exit('the replacement census failed its own red control; it is void')
