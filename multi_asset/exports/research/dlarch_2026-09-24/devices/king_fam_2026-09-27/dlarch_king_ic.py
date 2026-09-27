#!/usr/bin/env python3
"""dlarch_king_ic.py -- the IC-layer statistics of DECISION_RULE_king_improvement_family_2026-09-27.md §1 / §3 (lead,
4158f1521). Written and committed BEFORE any KN / A1 score or T_net reading exists. It computes and transcribes; it sets no
threshold.

TARGET: T_net from dlarch_t_net.py (pinned by the sha its own receipt reports), placed on the NEWS_FEATURES anchor axis by
timestamp, restricted to each anchor's MEMBERS (the rule ranks T_net within members). Anchors not covered by the funding
ledger are NaN (T_net stops 2026-08-31).
IC: per anchor, Spearman(score, T_net) over names finite in both, through the FROZEN news2_diag1_score_ic.ic_series (MIN_NAMES
20), CALLED ONE UTC DAY AT A TIME (dlarch_t2_pregate_2026 alignment rule); the day's IC = mean of its anchors' ICs.
dIC(day) = IC_arm(day) - IC_A0(day), paired on days where both exist; A0 = the in-service King OOF (a10b8725).
BOOTSTRAP: moving-block over days, B = 2000, seed 20260927 (the rule's numbers); block = 30 days (the frozen judge's
BLOCK_MAIN, read from it); 5-day block reported beside it.
SEGMENTS: pre-2026 = 2023-01-01 .. 2025-12-31 (the King OOF test years); 2026 = 2026-01-01 .. last covered anchor.
ARM READING (rule §3, transcribed): per member, the mean dIC per segment; the arm series = per-day mean dIC across the
members defined that day; PASS per segment iff arm 95% lower > 0 AND arm point >= 0.002; plus >= 6 of the members with a
positive mean dIC (per segment). Both segments must pass.
RED CONTROL (rule §3): the A0 scores shuffled across names within each anchor (finite cells only, seed 20260927) read as an
arm: dIC must be < 0 with 95% upper < 0 in BOTH segments, else the instrument has no resolution and the family stops.

usage: dlarch_king_ic.py <env-whitelist> <T_NET.npz> <T_NET_receipt.json> <A0 KING_OOF.npz> <out.json> red
       dlarch_king_ic.py <env-whitelist> <T_NET.npz> <T_NET_receipt.json> <A0 KING_OOF.npz> <out.json> arm <NAME> <score1.npz> [...]
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
TNET, TREC, A0P, OUT, MODE = sys.argv[2:7]
NS2 = '/dev/shm/news2_2026-09-23'; FEAT = f'{NS2}/work/NEWS_FEATURES.npz'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       f'{NS2}/devices/news2_diag1_score_ic.py': '291d800709650dddac72ba347cd151e71a8b0d22c730b535f3298e85bf6c79fc',
       A0P: 'a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a'}
B, SEED, DAY = 2000, 20260927, 86400
T_ = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


for p, w in PIN.items():
    assert sha(p) == w, f'input moved: {p}'
TR = json.load(open(TREC))
assert TR['device'] == 'dlarch_t_net.py' and TR['ALL_CONTROLS_PASS'] is True and TR['output']['sha256'] == sha(TNET), 'T_net not certified'
sys.path.insert(0, f'{NS2}/devices'); sys.path.insert(0, f'{NS2}/engine')
from news2_diag1_score_ic import ic_series                        # noqa: E402
import news_stats as NS                                            # noqa: E402

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
NA, NW = len(a), len(F['symbols'])
Tz = np.load(TNET, allow_pickle=True); assert [str(s) for s in Tz['symbols']] == [str(s) for s in F['symbols']]
Et = Tz['E_ts'].astype(np.int64); ix = np.searchsorted(Et, a); okt = (ix < len(Et)) & (Et[np.minimum(ix, len(Et) - 1)] == a)
Y = np.full((NA, NW), np.nan)
for i in np.flatnonzero(okt):
    mem = m_all[off[i]:off[i + 1]]
    Y[i, mem] = Tz['T_net'][ix[i], mem]
last_cov = int(a[np.flatnonzero(np.isfinite(Y).any(1))].max())
SEG = {'pre2026': (T_(2023, 1), T_(2026, 1)), '2026': (T_(2026, 1), last_cov + 1)}


def load_scores(p):
    z = np.load(p, allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a), f'{p}: axis differs'
    return z['P'].astype(np.float64)


def daily_ic(P):
    out = {}
    rows = np.flatnonzero(np.isfinite(Y).any(1) & np.isfinite(P).any(1))
    days = np.unique((a[rows] // DAY) * DAY)
    for u in days:
        r = rows[(a[rows] // DAY) * DAY == u]
        icd, _, _ = ic_series(P, Y, r, r)
        if len(icd):
            out[int(u)] = float(np.mean(icd))
    return out


def mbb(x, block, rng):
    n = len(x); nb = int(np.ceil(n / block)); means = np.empty(B)
    for b in range(B):
        st = rng.integers(0, max(1, n - block + 1), nb)
        idx = np.concatenate([np.arange(s, min(s + block, n)) for s in st])[:n]
        means[b] = x[idx].mean()
    return means


def seg_stats(series):
    out = {}
    for s, (lo, hi) in SEG.items():
        d = sorted(t for t in series if lo <= t < hi); x = np.array([series[t] for t in d])
        if len(x) < 30:
            out[s] = {'n_days': len(x), 'status': 'UNDEFINED'}
            continue
        mm = mbb(x, NS.BLOCK_MAIN, np.random.default_rng(SEED)); ms = mbb(x, NS.BLOCK_SENS, np.random.default_rng(SEED))
        out[s] = {'n_days': len(x), 'mean': float(x.mean()), 'ci95': [float(np.percentile(mm, 2.5)), float(np.percentile(mm, 97.5))],
                  'ci95_block5': [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))],
                  'block_days': NS.BLOCK_MAIN, 'B': B, 'seed': SEED}
    return out


A0 = load_scores(A0P); IC0 = daily_ic(A0)
rec = {'device': 'dlarch_king_ic.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': MODE, 'inputs': dict(PIN, T_net=sha(TNET)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'criterion': 'DECISION_RULE_king_improvement_family_2026-09-27.md §3 (4158f1521), transcribed',
       'segments': {k: [time.strftime('%Y-%m-%d', time.gmtime(v[0])), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(v[1] - 1))] for k, v in SEG.items()},
       'A0_IC': seg_stats(IC0)}


def diff(ICa):
    return {t: ICa[t] - IC0[t] for t in ICa if t in IC0}


if MODE == 'red':
    P = A0.copy(); rng = np.random.default_rng(SEED)
    for i in range(NA):
        f = np.flatnonzero(np.isfinite(P[i]))
        if len(f) > 1:
            P[i, f] = P[i, f[rng.permutation(len(f))]]
    st = seg_stats(diff(daily_ic(P)))
    ok = all(st[s].get('mean', 0) < 0 and st[s].get('ci95', [0, 0])[1] < 0 for s in SEG)
    rec.update({'red_dIC': st, 'gate': 'shuffled A0: dIC < 0 and 95% upper < 0 in BOTH segments', 'RED_PASS': bool(ok)})
    tag = 'RED_PASS=%s' % ok
elif MODE == 'arm':
    name, files = sys.argv[7], sys.argv[8:]
    members, per_day = {}, {}
    for p in files:
        dd = diff(daily_ic(load_scores(p)))
        members[p] = {'sha256': sha(p), 'dIC': seg_stats(dd)}
        for t, v in dd.items():
            per_day.setdefault(t, []).append(v)
    arm_series = {t: float(np.mean(v)) for t, v in per_day.items() if len(v) == len(files)}
    arm = seg_stats(arm_series); verdict = {}
    for s in SEG:
        npos = sum(1 for m in members.values() if m['dIC'][s].get('mean', 0) > 0)
        need = 6 if len(files) == 8 else int(np.ceil(0.75 * len(files)))
        verdict[s] = {'arm_ci95_lower_gt_0': bool(arm[s].get('ci95', [0])[0] > 0), 'arm_point_ge_0.002': bool(arm[s].get('mean', 0) >= 0.002),
                      'members_positive': npos, 'members_needed': need, 'PASS': bool(arm[s].get('ci95', [0])[0] > 0 and arm[s].get('mean', 0) >= 0.002 and npos >= need)}
    rec.update({'arm': name, 'n_members': len(files), 'members': members, 'arm_dIC': arm, 'segment_verdicts': verdict,
                'IC_LAYER_MAIN_PASS': all(v['PASS'] for v in verdict.values())})
    tag = 'ARM=%s IC_LAYER_MAIN_PASS=%s' % (name, rec['IC_LAYER_MAIN_PASS'])
else:
    sys.exit(f'unknown mode {MODE}')
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=float)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('KING_IC %s out=%s sha256=%s' % (tag, OUT, sha(OUT)), flush=True)
