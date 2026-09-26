"""Read-only: zero share of J:drank_{m7,v7,r24}_1d in the TRAINING set of the in-service F10 (news2 f10_s42 fold 202609,
the model exported as f10_live_s42_np 3d7d050f). Training set rebuilt with the trainer's own lines (cutoff, tr, 85%, windows)."""
import sys, json, hashlib, numpy as np
sys.path.insert(0, '/workspace/dlarch_2026-09-24/f10full_2026-09-26/vendor_news2_20260923/devices')
from f10_observability import span_admissible
def sha(p):
    h = hashlib.sha256(); f = open(p, 'rb')
    for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()
W = '/dev/shm/news2_2026-09-23'
FP, LP = W + '/work/NEWS_FEATURES.npz', W + '/work/legs.npz'
TP = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
names = [str(x) for x in np.load('/workspace/f8_ext/data/f8_fea89.npz', allow_pickle=True, mmap_mode='r')['names']]
IDX = [names.index(n) for n in ('J:drank_m7_1d', 'J:drank_v7_1d', 'J:drank_r24_1d')]
F = np.load(FP); a = F['anchors'].astype(np.int64); cnt = F['count']; off = F['off']
X = F['X89'][:, IDX].astype(np.float64)
T = np.load(TP, allow_pickle=True); leg = np.load(LP)
ya = T['E_ts'].astype(np.int64); y = np.full((len(a), len(F['symbols'])), np.nan, np.float32)
ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a); y[ok] = T['y4s'][ix[ok]]
members = [F['m'][off[i]:off[i + 1]].astype(int) for i in range(len(a))]
st = np.concatenate([[0], np.cumsum(cnt)]).astype(np.int64); assert np.array_equal(st, off.astype(np.int64))
ready = leg['ready']
fr = json.load(open(W + '/work/f10_s42/202609/FOLD_RECEIPT.json'))
cutoff = int(fr['admission']['cutoff']); first = int(fr['admission']['test_start'])
tr = np.flatnonzero((a + 14400 <= cutoff) & ready & (np.diff(st) >= 50)); tr1 = tr[:int(len(tr) * .85)]
assert int(a[tr1[-1]] + 14400) == fr['admission']['max_train_label_end'] and len(tr1) == fr['admission']['train_anchors']
win = []
for s in range(int(tr1[0]) + 24, int(tr1[-1]) - 96, 48):
    span = np.arange(s - 24, s + 96); okk, _ = span_admissible(members, y, span, ready)
    if okk: win.append(span)
assert len(win) == fr['admission']['accepted_windows'], (len(win), fr['admission']['accepted_windows'])
wa = np.unique(np.concatenate(win))
def rep(anc, label):
    rows = np.concatenate([np.arange(st[i], st[i + 1]) for i in anc])
    z = (X[rows] == 0)
    per_anchor_all0 = [bool((X[st[i]:st[i + 1]] == 0).all()) for i in anc]
    return {'set': label, 'anchors': int(len(anc)), 'rows': int(len(rows)),
            'cell_zero_share': {n: float(z[:, k].mean()) for k, n in enumerate(('drank_m7_1d', 'drank_v7_1d', 'drank_r24_1d'))},
            'rows_all_three_zero_share': float(z.all(1).mean()),
            'anchors_all_names_all_three_zero': int(sum(per_anchor_all0)),
            'anchors_all_zero_share': float(np.mean(per_anchor_all0))}
out = {'features': FP, 'features_sha256': sha(FP), 'legs_sha256': sha(LP), 'fold': '202609 (news2 f10_s42; exported model = f10_live_s42_np 3d7d050f from model.pt b67499bb)',
       'column_indices_in_X89': IDX, 'names_source': '/workspace/f8_ext/data/f8_fea89.npz names (same f8 column order)',
       'training_windows_union': rep(wa, 'anchors inside the accepted training windows (what the loss saw)'),
       'tr1_85pct': rep(tr1, 'tr1 = first 85% of admissible anchors (also the mu/sd population)'),
       'all_anchors': rep(np.arange(len(a)), 'every anchor in NEWS_FEATURES')}
print(json.dumps(out, indent=1))
