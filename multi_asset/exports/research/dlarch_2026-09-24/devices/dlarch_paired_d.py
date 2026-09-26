#!/usr/bin/env python3
"""dlarch_paired_d.py -- the paired difference d for ANY arm, under BOTH candidate baselines, and
revision 4's clauses evaluated on each. Written BEFORE any F10_FULL book-layer reading existed.

WHY BOTH. Revision 4 defines `d_k = dbar(arm_k) - dbar(T0_k)`. Revision 5(b) then made the common
baseline "the in-service NC F10 recipe (unmasked)". Those are two different d's, and which one is GATED
decides what the arm is measured against. dlarch has a stake in F10_FULL's admission, so dlarch does not
choose: both are computed and reported side by side, and `ambiguity_for_lead` names the open question.
The criterion's author decides; this device only makes both answers available at once so that no ordering
of "see number, then pick baseline" is possible.

WHAT CANCELS, AND WHY IT MATTERS. Every RETAIN receipt in this campaign was judged against ONE control,
`DLARCH_REF_NC_s42X`. So each receipt's `dbar` is already "this cell minus in-service NC s42", and in
  d^T0_k = dbar(arm_k) - dbar(T0_k) = (arm_k - NC42) - (T0_k - NC42) = arm_k - T0_k
the NC42 term cancels exactly. That is why revision 4's clause 5 ("also report the difference against
the in-service NC") needs no extra computation: `dbar` IS that difference. Verified, not assumed: the
device asserts every receipt it reads reports the same `control_tag`, and refuses otherwise.

sigma_hat IS NOT RECOMPUTED. Revision 4 fixes sigma_ref = 1.3533 * sigma_hat_F10 with sigma_hat measured
on the T0 x 8 family. This device READS those values from the delivered SIGMA receipt. Recomputing them
from a different population would silently move the threshold.

TWO ROUTES, and a refusal if they disagree (same discipline as dlarch_sigma_f10.py):
  route (i)  d from the dbar scalars the receipts record;
  route (ii) d computed DIRECTLY through the frozen judge from each cell's small series.
Segment bounds are taken from what each receipt RECORDS (`segments_used`), never re-derived from prose.

usage: dlarch_paired_d.py <env-whitelist> <receipts-dir> <sigma-receipt.json> <engine-dir> <out.json>
                          --arm-glob <glob> --arm-tagkey <str>
                          [--base-glob <glob> --base-tagkey <str>]...
  Each --base-* pair adds one candidate baseline. Seeds are matched by the seed parsed out of the tag
  the receipt REPORTS, never from a filename.
"""
import glob as G
import hashlib
import itertools
import json
import math
import os
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL)
assert not _x, f'env outside whitelist: {_x}'
RDIR, SIGR, ENGINE, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
REST = sys.argv[6:]

KAPPA = 1.3533          # revision 1; do not retype elsewhere
N1 = 3                  # stage 1: seeds 42 / 2027 / 7
STAGE1_SEEDS = {42, 2027, 7}
SEGS = ('pre2026', '2026')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def opts(flag):
    return [REST[i + 1] for i, a in enumerate(REST) if a == flag]


arm_globs, arm_keys = opts('--arm-glob'), opts('--arm-tagkey')
base_globs, base_keys = opts('--base-glob'), opts('--base-tagkey')
assert len(arm_globs) == len(arm_keys) == 1, 'exactly one --arm-glob/--arm-tagkey pair is required'
assert len(base_globs) == len(base_keys) >= 1, 'at least one --base-glob/--base-tagkey pair is required'


def collect(pattern, tagkey):
    """Key every cell by the tag the receipt REPORTS, never by its filename (E-0825-H/G)."""
    out = {}
    for d in sorted(G.glob(os.path.join(RDIR, pattern))):
        fs = G.glob(os.path.join(d, 'RETAIN_*.json'))
        if not fs:
            continue
        r = json.load(open(fs[0]))
        tag = r['tag']
        if tagkey not in tag:
            continue                      # a sibling receipt in the same dir, not this arm
        # NC reference tags carry an X suffix (DLARCH_REF_NC_s42X_...), so take the LEADING DIGITS
        # rather than the first underscore-token: int('42X') raises, and a crash here would look like a
        # missing cell rather than a parsing bug.
        _rest = tag.split(tagkey)[1]
        _dig = ''.join(itertools.takewhile(str.isdigit, _rest))
        assert _dig, f'cannot parse a seed out of {tag!r} after {tagkey!r}'
        seed = int(_dig)
        assert seed not in out, f'two receipts report seed {seed} for {tagkey}'
        assert r['ALL_PRECONDITIONS_PASS'], f'{tag}: retention preconditions did NOT pass'
        out[seed] = {'tag': tag, 'receipt': fs[0], 'receipt_sha256': sha(fs[0]),
                     'control_tag': r['control_tag'], 'segments_used': r['segments_used'],
                     'small': r['small_series']['path'],
                     'dbar': {k: v['mean_bps_per_day'] for k, v in r['dbar_vs_control'].items()}}
    return out


ARM = collect(arm_globs[0], arm_keys[0])
BASES = {k: collect(g, k) for g, k in zip(base_globs, base_keys)}

# every dbar must be against the SAME control, or the subtraction is between different quantities
ctrls = {v['control_tag'] for v in ARM.values()}
for b in BASES.values():
    ctrls |= {v['control_tag'] for v in b.values()}
assert len(ctrls) == 1, f'cells were judged against DIFFERENT controls; dbars are not comparable: {ctrls}'
COMMON_CONTROL = ctrls.pop()

SIG = json.load(open(SIGR))
sigma_hat = {g: SIG['sigma_hat_F10_per_segment'][g]['sigma_hat_F10'] for g in SEGS}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlarch_cell_retain as CR            # noqa: E402  -- import the frozen helpers, never copy them
import numpy as np                         # noqa: E402

NS, _BT, _DL = CR.load_frozen(ENGINE)      # unpacking this wrong is how route (ii) failed once before


def route_ii(a_cell, b_cell):
    """d per segment computed DIRECTLY through the frozen judge from the two small series."""
    ra, rb = json.load(open(a_cell['receipt'])), json.load(open(b_cell['receipt']))
    assert ra['segments_used'] == rb['segments_used'], (
        'the two receipts record DIFFERENT segment bounds, so their dbars are not on the same population')
    pa = CR.paths_from_small(np.load(a_cell['small'], allow_pickle=False))
    pb = CR.paths_from_small(np.load(b_cell['small'], allow_pickle=False))
    assert len(pa) == len(pb), f'path counts differ ({len(pa)} vs {len(pb)})'
    A = pa[0]['A']
    assert np.array_equal(A, pb[0]['A']), 'the two cells are on different axes'
    per = {}
    for g, (lo, hi) in ra['segments_used'].items():
        m = NS.seg_mask(A, lo, hi)
        days = NS.full_days(A, m)
        db, _D = NS.dbar(pa, pb, m, days)
        per[g] = float(1e4 * db.mean())
    return per


def judge(dper, label):
    """Revision 4's clauses, transcribed. No summarising: the clause text drives the branch."""
    out = {'baseline': label, 'segments': {}}
    for g in SEGS:
        per = dper[g]
        vals = [per[s] for s in sorted(per)]
        mean_d = sum(vals) / len(vals)
        sd_d = (sum((v - mean_d) ** 2 for v in vals) / (len(vals) - 1)) ** .5 if len(vals) > 1 else 0.0
        sref = KAPPA * sigma_hat[g]
        se_meas = sd_d / math.sqrt(len(vals))
        se_back = sref * math.sqrt(2) / math.sqrt(len(vals))
        se = max(se_meas, se_back)
        out['segments'][g] = {
            'd_per_seed': per, 'mean_d': mean_d, 'sd_d': sd_d, 'n': len(vals),
            'n_positive': sum(1 for v in vals if v > 0),
            'sigma_hat_F10_from_T0x8': sigma_hat[g], 'sigma_ref': sref,
            'SE_measured_branch': se_meas, 'SE_backstop_branch': se_back, 'SE': se,
            'branch_taken': 'backstop' if se_back > se_meas else 'measured',
            'three_SE': 3 * se, 'threshold_max_1_or_3SE': max(1.0, 3 * se)}
    y, p = out['segments']['2026'], out['segments']['pre2026']
    # REJECT clauses first, exactly as written
    rej = []
    if y['mean_d'] <= 0:
        rej.append('mean(d_2026) <= 0')
    if y['n_positive'] <= 1:
        rej.append('2026 has <= 1 seed with d > 0')
    if p['mean_d'] < -3 * p['SE']:
        rej.append('mean(d_pre) < -3*SE_pre (significant historical harm)')
    rec = (y['mean_d'] >= y['threshold_max_1_or_3SE'] and y['n_positive'] == y['n']
           and p['mean_d'] >= 0)
    ext = (1.0 <= y['mean_d'] < y['three_SE'] and y['n_positive'] == y['n'] and p['mean_d'] >= 0)
    out['reject_clauses_fired'] = rej
    out['verdict'] = ('REJECT' if rej else 'RECOMMEND_TO_USER' if rec else 'EXTEND' if ext
                      else 'UNDECIDED')
    out['clause_5_dbar_vs_in_service_NC_is_dbar_itself'] = (
        'every receipt is judged against %s, so dbar already IS the difference against the in-service NC '
        'reference; no extra computation is needed for clause 5.' % COMMON_CONTROL)
    out['drawdown_guardrail'] = 'NOT evaluated here: section 3 condition 4 needs the maxdd table; ' \
                               'dlarch_t3_verdict.py computes it and this device does not duplicate it.'
    return out


results, routes = {}, {}
for key, base in BASES.items():
    seeds = sorted(set(ARM) & set(base))
    assert seeds, f'no seed has both an arm cell and a {key} cell'
    i_per = {g: {s: ARM[s]['dbar'][g] - base[s]['dbar'][g] for s in seeds} for g in SEGS}
    ii_raw = {s: route_ii(ARM[s], base[s]) for s in seeds}
    ii_per = {g: {s: ii_raw[s][g] for s in seeds} for g in SEGS}
    agree = {g: max(abs(i_per[g][s] - ii_per[g][s]) for s in seeds) for g in SEGS}
    routes[key] = {'route_i_from_dbar_scalars': i_per, 'route_ii_through_frozen_judge': ii_per,
                   'max_abs_route_disagreement': agree,
                   'routes_agree': all(v <= 1e-6 for v in agree.values())}
    if not routes[key]['routes_agree']:
        results[key] = {'baseline': key, 'status': 'REFUSED_ROUTES_DISAGREE',
                        'max_abs_route_disagreement': agree,
                        'why': 'two independent routes to the same d differ; refusing to publish a '
                               'verdict from either rather than silently trusting one reader'}
        continue
    results[key] = judge(i_per, key)
    results[key]['seeds_used'] = seeds
    results[key]['stage1_seeds_complete'] = set(seeds) == STAGE1_SEEDS

rec = {'device': 'dlarch_paired_d.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'criterion_source': 'DECISION_RULE_dl_program_book_gate_2026-09-25.md revision 4, transcribed; '
                           'thresholds not authored here',
       'sigma_source': {'path': SIGR, 'sha256': sha(SIGR),
                        'note': 'sigma_hat read from the delivered T0 x 8 receipt, NOT recomputed'},
       'frozen_judge': os.path.join(ENGINE, 'news_stats.py'),
       'frozen_judge_sha256': sha(os.path.join(ENGINE, 'news_stats.py')),
       'common_control_tag': COMMON_CONTROL,
       'arm_cells': {s: ARM[s]['tag'] for s in sorted(ARM)},
       'base_cells': {k: {s: v[s]['tag'] for s in sorted(v)} for k, v in BASES.items()},
       'routes': routes, 'verdict_per_baseline': results,
       'ambiguity_for_lead': (
           'revision 4 defines d against T0; revision 5(b) made the common baseline the in-service NC '
           'recipe. Both are computed above and NEITHER is privileged here. Two things need lead: '
           '(1) which pairing is the GATED d; (2) whether sigma_ref, whose sigma_hat was measured on the '
           'T0 x 8 family, applies unchanged to an NC-paired difference. dlarch has a stake in this '
           "arm's admission and does not choose.")}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)

for k, v in results.items():
    if v.get('status'):
        print(f'  {k}: {v["status"]}')
        continue
    for g in SEGS:
        sg = v['segments'][g]
        print('  %-28s %-8s mean(d)=%+.4f  %d/%d positive  thr=%.4f (%s branch)'
              % (k, g, sg['mean_d'], sg['n_positive'], sg['n'], sg['threshold_max_1_or_3SE'],
                 sg['branch_taken']))
    print('  %-28s VERDICT=%s  fired=%s' % (k, v['verdict'], v['reject_clauses_fired'] or 'none'))
print('DLARCH_PAIRED_D out=%s sha256=%s' % (OUT, sha(OUT)[:16]))
