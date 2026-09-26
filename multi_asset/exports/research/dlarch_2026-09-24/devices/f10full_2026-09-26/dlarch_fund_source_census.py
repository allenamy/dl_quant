#!/usr/bin/env python3
"""dlarch_fund_source_census.py -- READ-ONLY: which funding-feature artefact (by literal sha) and which
upstream source every dlarch F10 training arm and every dlarch book cell actually consumed.

Asked by lead (2026-09-26, for news2's source-based census): fresh found the fund_replay EMA channel
contaminated; the NEW_S / FRESH roots bind NEWS_FEATURES a490c294 (and legs 18999e16 / 486dfe37). This
answers the same question for T0 / T3 / F10_FULL / NC reference cells.

Two channels, each identified by the file that was READ, never by a filename (the same name
NEWS_FEATURES.npz exists in two roots with different content):
  * MODEL-FEATURE channel (f_fund_ema, fe_v, ... in X82/X89): the NEWS_FEATURES.npz sha in each F10
    TRAIN_RECEIPT['inputs'] -- recorded by the trainer at read time;
  * CHAIN channel (Z24 / ZFD / WL / KZ / RN8 ...): the legs.npz sha in each book cell's combo
    TARGET_RECEIPT['inputs'] -- recorded by news2_combo at read time.
Upstream is then followed through the receipts that PRODUCED those files (P2B_FEATURES / P3_LEGS), so
the answer reaches fund_state, not just the next file. Every sha seen anywhere is also checked against
the contaminated set, so "not bound" is a search result over everything read, not an assumption.

usage: dlarch_fund_source_census.py <env-whitelist> <out.json>
"""
import glob
import hashlib
import json
import os
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL)
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]
W = '/workspace/dlarch_2026-09-24'
NS = '/dev/shm/news2_2026-09-23'
CONTAMINATED_PREFIXES = {'a490c294': 'NEWS_FEATURES of NEW_S/FRESH roots (fund_replay EMA)',
                         '18999e16': 'legs of NEW_S/FRESH roots', '486dfe37': 'legs of NEW_S/FRESH roots'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pick(d, suffix):
    hits = {k: v for k, v in d.items() if k.endswith(suffix)}
    assert len(hits) <= 1, f'more than one {suffix} in {list(d)}'
    return next(iter(hits.items()), (None, None))


seen = set()
train = {}
f10_dirs = sorted(glob.glob(f'{W}/T3/*/f10_s*')) + [f'{NS}/work/f10_s42', f'{NS}/work/f10_s2027']
for d in f10_dirs:
    p = f'{d}/TRAIN_RECEIPT.json'
    if not os.path.exists(p):
        train[d] = {'TRAIN_RECEIPT': 'absent'}
        continue
    r = json.load(open(p))
    inp = r.get('inputs', {})
    fp, fs = pick(inp, 'NEWS_FEATURES.npz')
    lp, ls = pick(inp, 'legs.npz')
    seen |= set(inp.values())
    train[d] = {'status': r.get('status'), 'NEWS_FEATURES': {'path': fp, 'sha256': fs},
                'legs': {'path': lp, 'sha256': ls}, 'all_inputs': inp}

cells = {}
for tr in sorted(glob.glob(f'{W}/chain/*/work/combo_s*/TARGET_RECEIPT.json')):
    r = json.load(open(tr))
    inp = r['inputs']
    seen |= set(inp.values())
    fp, fs = pick(inp, 'NEWS_FEATURES.npz')
    lp, ls = pick(inp, 'legs.npz')
    op, osha = pick(inp, 'F10_OOF.npz')
    root = tr.split('/work/')[0]
    link = os.path.realpath(os.path.dirname(op)) if op else None
    cells[os.path.basename(root)] = {'NEWS_FEATURES': {'path': fp, 'sha256': fs, 'realpath': os.path.realpath(fp) if fp else None},
                                     'legs': {'path': lp, 'sha256': ls, 'realpath': os.path.realpath(lp) if lp else None},
                                     'F10_source_dir': link, 'F10_OOF_sha256': osha}

# upstream of the NC-root files
P2B = json.load(open(f'{NS}/receipts/P2B_FEATURES.json'))
P3 = json.load(open(f'{NS}/receipts/P3_LEGS.json'))
king = {}
for p in glob.glob(f'{NS}/work/king/*.json') + glob.glob(f'{NS}/receipts/*KING*.json'):
    try:
        r = json.load(open(p))
    except Exception:                                        # noqa: BLE001
        continue
    s = json.dumps(r)
    if P3['inputs']['king_oof'] in s or 'KING_OOF' in s:
        feats = sorted({v for v in (r.get('inputs') or {}).values() if isinstance(v, str)} if isinstance(r.get('inputs'), dict) else [])
        king[p] = {'mentions_king_oof_sha': P3['inputs']['king_oof'] in s,
                   'mentions_nc_features_sha': P2B['sha256'] in s,
                   'mentions_a490c294': 'a490c294' in s, 'input_shas': feats[:20]}
upstream = {
    'NEWS_FEATURES_nc_root': {'sha256': P2B['sha256'], 'built_as': P2B['output'], 'devices': P2B['devices'],
                              'producer_tree': P2B['tree_outputs'], 'members_hist': P2B['members_hist']},
    'legs_nc_root': {'sha256': P3['sha256'], 'inputs': P3['inputs'], 'source_sha': P3['source_sha']},
    'king_receipts_found': king}
seen |= {P2B['sha256'], P3['sha256']} | set(P3['inputs'].values())

hits = {pre: sorted(s for s in seen if isinstance(s, str) and s.startswith(pre)) for pre in CONTAMINATED_PREFIXES}
feat_shas = sorted({v['NEWS_FEATURES']['sha256'] for v in train.values() if 'NEWS_FEATURES' in v}
                   | {v['NEWS_FEATURES']['sha256'] for v in cells.values()})
legs_shas = sorted({v['legs']['sha256'] for v in train.values() if 'legs' in v} | {v['legs']['sha256'] for v in cells.values()})
rec = {'device': 'dlarch_fund_source_census.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'training_arms': train, 'book_cells': cells, 'upstream': upstream,
       'distinct_NEWS_FEATURES_sha_consumed': feat_shas, 'distinct_legs_sha_consumed': legs_shas,
       'contaminated_sha_hits_over_everything_read': hits,
       'ANY_CONTAMINATED_BINDING': any(hits.values()),
       'limits': ['NC-root EMA itself is not verified cell-by-cell against an archive (fanom 28a6a2659 residual)',
                  'this reads receipts written at read time by the trainer and news2_combo; a receipt that '
                  'lied about its input would pass here -- the trainer and combo assert those shas at run time']}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('NEWS_FEATURES consumed:', [s[:8] for s in feat_shas])
print('legs consumed         :', [s[:8] for s in legs_shas])
print('training arms:', len(train), ' book cells:', len(cells))
print('contaminated hits     :', {k: len(v) for k, v in hits.items()})
print('FUND_SOURCE_CENSUS any_contaminated=%s out=%s sha256=%s' % (rec['ANY_CONTAMINATED_BINDING'], OUT, sha(OUT)))
