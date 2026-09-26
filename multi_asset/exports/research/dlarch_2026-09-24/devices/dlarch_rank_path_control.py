#!/usr/bin/env python3
"""dlarch_rank_path_control.py -- R25-07: the full score -> rank -> FTRIM -> chain positive control.

THE TWO DIFFERENCES (read off the two lines, not inferred from the names):

  TRAIN  dlarch_train_f10.py `soft_rank(..., hard=True)`:
             argsort(argsort(z)) / max(n-1,1) - 0.5
         ranks are 0..n-1 ; ties broken ARBITRARILY (by index order) ; range exactly [-0.5, +0.5]

  CHAIN  dlarch_chain_torch.py L120 (the numpy reconstruction):
             rankdata(p[okf]) / max(okf.sum()-1,1) - 0.5
         ranks are 1..n     ; ties AVERAGED                          ; range [1/(n-1)-0.5, n/(n-1)-0.5]

  => 1 ORIGIN: a CONSTANT offset c = 1/(n-1) on every ranked cell.
     2 TIES:   differs only where duplicate scores exist.

WHY THE OFFSET DOES NOT "JUST CANCEL" (the reviewer's point, made precise). Both paths later subtract a
mean, and a constant added to every member is removed by a demean -- BUT ONLY IF THE SET THAT RECEIVED
THE OFFSET IS THE SET THAT IS DEMEANED. In the chain the offset lands on `okf` (finite score) while the
demean runs over `sel` (the FTRIM/liquidity selection). When okf != sel the constant is no longer
constant over the demeaned population, so a residual survives into the book. That is the whole mechanism
and this device measures it instead of asserting it.

WHAT IS MEASURED: the book output of the FROZEN `chain_torch` under the two rank conventions, in three
arms. Materiality is reported in units that matter -- max |dW| as a fraction of the per-name cap
(cap = cap_mult/|sel|), because a difference far below the cap cannot move a lot or a fill.

ARMS
  A no_ties_okf_eq_sel  : offset SHOULD cancel at the demean  -> expect ~float noise. This is the
                          GREEN BASELINE: if it is not ~0, the harness itself is wrong and the other
                          two arms mean nothing.
  B ties_okf_eq_sel     : duplicate scores present (the convention the review says cannot be assumed
                          away), still okf == sel.
  C no_ties_okf_subset  : okf STRICTLY inside sel -- the FTRIM case where the offset cannot cancel.
"""
import json
import os
import sys
import time

import numpy as np
import torch
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dlarch_chain_torch import chain_torch, sha          # noqa: E402  -- FROZEN code, called not copied

N = 400
CAP_MULT, ALPHA, BAND, S_TEMP = 2.5, 0.1, 0.0, 0.0


def rank_train(x):
    """TRAIN convention, transcribed from soft_rank(hard=True) and then PROVEN below."""
    t = torch.as_tensor(x, dtype=torch.float64)
    z = (t - t.mean()) / (t.std() + 1e-8)
    n = len(z)
    return (torch.argsort(torch.argsort(z)).to(z.dtype) / max(n - 1, 1) - .5).numpy()


def rank_chain(x):
    """CHAIN convention, transcribed from dlarch_chain_torch.py L120."""
    return rankdata(x) / max(len(x) - 1, 1) - .5


def _proof_rank_train_matches_the_shipped_function():
    """The transcription above must equal what the trainer's own soft_rank returns. Proven, not claimed."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dlarch_train_f10 import soft_rank               # noqa: E402
    g = torch.Generator().manual_seed(7)
    x = torch.randn(N, generator=g, dtype=torch.float64)
    a = soft_rank(x, tau=0.1, hard=True).numpy()
    b = rank_train(x.numpy())
    return {'max_abs_diff': float(np.abs(a - b).max()), 'bitwise_equal': bool((a == b).all())}


def book(zc_np, sel_np, H_np):
    z = torch.as_tensor(zc_np, dtype=torch.float64)
    sel = torch.as_tensor(sel_np, dtype=torch.bool)
    H = torch.as_tensor(H_np, dtype=torch.float64)
    pm = torch.arange(N)
    live = torch.ones(N, dtype=torch.bool)
    return chain_torch(z, sel, H, pm, N, live, CAP_MULT, ALPHA, BAND, S_TEMP, 'clamp')


def arm(name, scores, sel_np, okf_np):
    """Run both conventions through the frozen chain on identical everything else."""
    H = np.zeros(N)
    out = {}
    for conv, fn in (('train', rank_train), ('chain', rank_chain)):
        zf = np.zeros(N)
        k = int(okf_np.sum())
        if k:
            zf[okf_np] = fn(scores[okf_np])
        b = book(zf, sel_np, H)
        out[conv] = None if b is None else b.numpy()
    if out['train'] is None or out['chain'] is None:
        return {'arm': name, 'status': 'DEGENERATE'}
    d = np.abs(out['train'] - out['chain'])
    cap = CAP_MULT / max(int(sel_np.sum()), 1)
    gross = np.abs(out['train']).sum()
    return {'arm': name, 'status': 'OK', 'n_sel': int(sel_np.sum()), 'n_okf': int(okf_np.sum()),
            'okf_equals_sel': bool((okf_np == sel_np).all()),
            'n_duplicate_scores': int(len(scores[okf_np]) - len(np.unique(scores[okf_np]))),
            'max_abs_dW': float(d.max()), 'sum_abs_dW': float(d.sum()),
            'per_name_cap': cap, 'max_abs_dW_over_cap': float(d.max() / cap),
            'sum_abs_dW_over_gross': float(d.sum() / gross) if gross > 0 else None,
            'cells_differing': int((d > 0).sum())}


def main():
    WL = set(sys.argv[1].split(',')) if len(sys.argv) > 1 else {'PATH', 'HOME', 'LC_CTYPE'}
    _x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
    assert not _x, f'env outside whitelist: {_x}'
    out = sys.argv[2] if len(sys.argv) > 2 else None

    rng = np.random.default_rng(11)
    cont = rng.normal(size=N)
    tied = np.round(rng.normal(size=N), 1)            # ~10x fewer distinct values -> many exact ties
    all_sel = np.ones(N, bool)
    sub_okf = all_sel.copy(); sub_okf[:80] = False     # okf strictly inside sel: the FTRIM case

    arms = [arm('A_no_ties_okf_eq_sel', cont, all_sel, all_sel),
            arm('B_ties_okf_eq_sel', tied, all_sel, all_sel),
            arm('C_no_ties_okf_subset_of_sel', cont, all_sel, sub_okf)]

    baseline = arms[0]
    rec = {'device': 'dlarch_rank_path_control.py', 'self_sha256': sha(os.path.abspath(__file__)),
           'frozen_chain_torch_sha256': sha(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         'dlarch_chain_torch.py')),
           'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'transcription_proof_rank_train_vs_shipped_soft_rank':
               _proof_rank_train_matches_the_shipped_function(),
           'constant_origin_offset_c': 1.0 / (N - 1), 'arms': arms,
           'GREEN_BASELINE_offset_cancels_when_okf_eq_sel': baseline['max_abs_dW_over_cap'] < 1e-9}
    print(json.dumps(rec, indent=1, sort_keys=True))
    if out:
        with open(out, 'w') as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        print('receipt=' + out)
    print('RANK_PATH_CONTROL baseline_cancels=%s' % rec['GREEN_BASELINE_offset_cancels_when_okf_eq_sel'])


if __name__ == '__main__':
    main()
