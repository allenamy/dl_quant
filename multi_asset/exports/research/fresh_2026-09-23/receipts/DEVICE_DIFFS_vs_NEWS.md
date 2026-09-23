# FRESH devices — line-by-line diff against the NEW_S originals

NEW_S originals: multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/ (hash-identical to pod2 /dev/shm/news_2026-09-23/devices/)
FRESH devices:   multi_asset/exports/research/fresh_2026-09-23/devices/ (hash-identical to pod2 /dev/shm/fresh_2026-09-23/devices/)

## news_train_king.py -> fresh_train_king.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_train_king.py	2026-09-23 19:16:50
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_train_king.py	2026-09-23 21:11:53
@@ -1,8 +1,9 @@
-"""NEWS P3 King: the NEW recipe (codex_combo_20260923 devices/train_king.py 1c...: LGBM params, annual folds via
-king_folds.fold_rows embargo 60, target = within-anchor rank of the raw label over members with >= 50 finite labels)
-applied UNCHANGED to the NEWS inputs: X78 = producer King block features (NEWS_FEATURES.npz), members = producer member
-screen on legal ∧ crypto candidates, labels = NEW dlw_targets y4s (raw compounded (E,E+48], all closes observed, NaN never 0).
-Only the input-loading lines differ from train_king.py (diff archived); the fold loop is copied verbatim.
+"""FRESH P3 King: news_train_king.py with ONLY the three PREREG_fresh_models_newS_2026-09-23.md §1 changes:
+  K  annual folds (2022H2_WARMUP + 2023/2024/2025/2026)  ->  one fold per calendar month from 2022-07 (expanding window)
+  E  embargo 60 anchors                                  ->  embargo 6 anchors (fold_rows + receipt field + assertion)
+  roots: this agent's own root for outputs; NEW_S root read-only for the frozen inputs (features, labels, receipts).
+LGBM params, target definition, random_state, fold loop body and receipts are byte-for-byte news_train_king.py.
+king_folds.py is the NEW_S file unchanged (embargo is already its parameter).
 """
 import os
 os.environ['OMP_NUM_THREADS'] = '8'; os.environ['OPENBLAS_NUM_THREADS'] = '2'
@@ -10,10 +11,13 @@
 import numpy as np
 from scipy.stats import rankdata, spearmanr, pearsonr
 
-W = pathlib.Path('/dev/shm/news_2026-09-23')
+W = pathlib.Path('/dev/shm/fresh_2026-09-23')
+N = pathlib.Path('/dev/shm/news_2026-09-23')           # NEW_S root: READ-ONLY frozen inputs
 NEWT = pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
 NEWT_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
 FOLDS_SRC = W / 'devices/king_folds.py'
+EMBARGO = 6                                            # PREREG §1 E (NEW_S: 60)
+PREREG = {'path': 'docs/PREREG_fresh_models_newS_2026-09-23.md', 'commit': 'b6e682e0a'}
 
 
 def sha(p):
@@ -26,10 +30,20 @@
 def log(*x): print(time.strftime('%H:%M:%S', time.gmtime()), *x, flush=True)
 
 
+def month_specs(a):
+    """PREREG §1 K: one fold per calendar month from 2022-07 to the last month on the axis; expanding train window."""
+    utc = lambda yr, mo: calendar.timegm((yr, mo, 1, 0, 0, 0))
+    out = []; y, m = 2022, 7
+    while utc(y, m) <= int(a[-1]):
+        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
+        out.append((f'{y}{m:02d}', utc(y, m), utc(ny, nm))); y, m = ny, nm
+    return out
+
+
 def main():
     sys.path.insert(0, str(W / 'devices')); from king_folds import fold_rows
     out = W / 'work/king'; out.mkdir(exist_ok=False)
-    feat = W / 'work/NEWS_FEATURES.npz'; frec = json.load(open(W / 'receipts/P2B_FEATURES.json'))
+    feat = N / 'work/NEWS_FEATURES.npz'; frec = json.load(open(N / 'receipts/P2B_FEATURES.json'))
     assert sha(feat) == frec['sha256'] and sha(NEWT) == NEWT_SHA
     F = np.load(feat); T = np.load(NEWT, allow_pickle=True)
     a = F['anchors'].astype(np.int64); syms = F['symbols']; off = F['off']; cnt = F['count']
@@ -40,22 +54,23 @@
     y[ok] = T['y4s'][ix[ok]]
     pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F['m'].astype(np.int64); x = F['X78'].astype(np.float32)
     assert x.shape[1] == 78 and np.isfinite(x).all() and len(pa) == len(ps) == len(x) == off[-1]
-    # ---- verbatim from train_king.py from here (target, params, folds, receipts) ----
+    # ---- verbatim from news_train_king.py from here (target, params, folds, receipts) ----
     target = np.full(len(pa), np.nan, np.float32); st = np.searchsorted(pa, np.arange(len(a) + 1))
     for i in range(len(a)):
         ixx = np.arange(st[i], st[i + 1]); vals = y[i, ps[ixx]]; good = np.isfinite(vals)
         if good.sum() >= 50: target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
     import lightgbm as lgb
     params = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8, colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=0)
-    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); folds = []
-    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
-    specs = [('2022H2_WARMUP', utc(2022, 7), utc(2023))] + [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]
+    pred = np.full(y.shape, np.nan, np.float32); model_id = np.full(len(a), '', dtype='U64'); fold_id = np.full(len(a), '', dtype='U16')
+    train_end = np.full(len(a), -1, np.int64); folds = []
+    specs = month_specs(a)
     for tag, start, end in specs:
-        train, test = fold_rows(a, start, end, 60); tr = np.isin(pa, train) & np.isfinite(target); te = np.isin(pa, test)
+        train, test = fold_rows(a, start, end, EMBARGO); tr = np.isin(pa, train) & np.isfinite(target); te = np.isin(pa, test)
         assert tr.sum() > 1000 and te.sum() > 0
         t = time.monotonic(); log('King start', tag, int(tr.sum()), int(te.sum()))
         model = lgb.LGBMRegressor(**params).fit(x[tr], target[tr]); modelpath = out / ('king_' + tag + '.txt'); model.booster_.save_model(str(modelpath))
-        pred[pa[te], ps[te]] = model.predict(x[te]); mh = sha(modelpath); model_id[test] = mh
+        pred[pa[te], ps[te]] = model.predict(x[te]); mh = sha(modelpath); model_id[test] = mh; fold_id[test] = tag
+        mtle = int(a[pa[tr]].max() + 14400); train_end[test] = mtle
         ic = []; pp = []
         for i in test:
             good = np.isfinite(pred[i]) & np.isfinite(y[i])
@@ -65,17 +80,18 @@
         for j in range(len(syms)):
             good = np.isfinite(pred[test, j]) & np.isfinite(y[test, j])
             if good.sum() >= 30 and np.std(pred[test[good], j]) > 0: per.append(float(pearsonr(pred[test[good], j], y[test[good], j])[0]))
-        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': int(a[pa[tr]].max() + 14400), 'embargo_anchors': 60,
+        rr = {'fold': tag, 'score_start': int(a[test[0]]), 'score_end': int(a[test[-1]]), 'max_train_label_end': mtle, 'embargo_anchors': EMBARGO,
               'train_pairs': int(tr.sum()), 'scored_pairs': int(te.sum()), 'model_path': str(modelpath), 'model_sha256': mh, 'seconds': time.monotonic() - t,
               'mean_cs_spearman': float(np.mean(ic)), 'mean_cs_pearson': float(np.mean(pp)), 'mean_per_asset_pearson': float(np.mean(per)), 'n_cs_anchors': len(ic), 'status': 'SIGNAL_DIAGNOSTIC_ONLY'}
-        assert rr['max_train_label_end'] <= rr['score_start'] - 60 * 14400
+        assert rr['max_train_label_end'] <= rr['score_start'] - EMBARGO * 14400
         folds.append(rr); log(json.dumps(rr)); (out / 'PROGRESS.json').write_text(json.dumps(folds, indent=2, allow_nan=False))
-    np.savez(out / 'KING_OOF.npz', P=pred, E_ts=a, symbols=syms, model_sha256=model_id)
-    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds,
+    np.savez(out / 'KING_OOF.npz', P=pred, E_ts=a, symbols=syms, model_sha256=model_id, fold_tag=fold_id, max_train_label_end=train_end)
+    receipt = {'status': 'OOF_KING_NOT_FULL_STRATEGY', 'recipe': params, 'folds': folds, 'prereg': PREREG,
+               'fresh_changes': {'K': 'calendar-month folds from 2022-07, expanding window (NEW_S: annual folds)', 'E': f'embargo {EMBARGO} anchors (NEW_S: 60)'},
                'source_sha': {__file__: sha(os.path.abspath(__file__)), str(FOLDS_SRC): sha(FOLDS_SRC)},
                'inputs': {str(feat): sha(feat), str(NEWT): NEWT_SHA}, 'predictions_sha256': sha(out / 'KING_OOF.npz'),
                'label': 'NEW dlw_targets y4s (raw compounded, all closes observed; NaN excluded, never 0)',
-               'features': 'producer shadow_loop_v3 King block replayed (P2B_FEATURES.json)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
+               'features': 'producer shadow_loop_v3 King block replayed (NEW_S receipts/P2B_FEATURES.json)', 'lightgbm': lgb.__version__, 'numpy': np.__version__}
     (out / 'TRAIN_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); log('KING_DONE')
 
 
```

## news_legs.py -> fresh_legs.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_legs.py	2026-09-23 19:16:44
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_legs.py	2026-09-23 21:13:40
@@ -1,10 +1,10 @@
-"""NEWS P3 legs/seats in PRODUCTION caliber (AMENDMENT 1 §3.10), for F10 training (Z24/ZFD/WL/ready) and the combo.
-Source lines used verbatim (compiled from shadow_loop_v3.py, sha asserted):
-  xz_in_base (module-level function), xz (L598-602), leg-return recursion (L556-L572 formula), msharpe w3 (L589-596).
-Readiness follows NEW's convention (no fabricated King score): an anchor is ready iff the producer would have produced a
-record (members >= 50, sel >= sel_min) AND the NEWS King OOF score is finite for every member AND the fund base has >= 10 names.
-Leg returns are appended only between consecutive ready anchors (the producer appends only when prev_rec is the previous anchor).
-y4v uses the cache ret5 of (A-4h, A] for ALL names (the producer's rolling cache holds every fetched name), hole cells NaN.
+"""FRESH P3 legs/seats — news_legs.py with ONLY the roots changed (PREREG_fresh_models_newS_2026-09-23.md §1: the seat legs
+and the combo are rebuilt from FRESH's own King OOF; everything else is byte-for-byte news_legs.py).
+  inputs  : NEW_S root (READ-ONLY) for NEWS_FEATURES.npz / fund_replay.npz / cache_x0918r_* / bundle_config.json
+            FRESH root for work/king/KING_OOF.npz
+  outputs : FRESH root work/legs.npz, receipts/P3_LEGS.json
+Producer source lines (xz_in_base, xz, leg-return recursion, msharpe w3) are taken from the same producer snapshot with the
+same sha assertion, through news_hist_features (copied unchanged into this agent's devices).
 """
 import os, sys, ast, json, time, hashlib
 import numpy as np
@@ -12,7 +12,10 @@
 sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 import news_hist_features as H
 
-W = H.W
+W = "/dev/shm/fresh_2026-09-23"      # FRESH root (outputs, King OOF)
+N = H.W                              # NEW_S root, READ-ONLY (frozen shared inputs); asserted below
+assert N == "/dev/shm/news_2026-09-23"
+CACHE_NPY = f"{N}/work/cache_x0918r_data.npy"
 
 
 def prod_funcs():
@@ -27,13 +30,14 @@
 
 def main():
     t0 = time.time(); xz_in_base, xz = prod_funcs()
-    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); K = np.load(f"{W}/work/king/KING_OOF.npz")
+    F = np.load(f"{N}/work/NEWS_FEATURES.npz"); K = np.load(f"{W}/work/king/KING_OOF.npz")
     a = F["anchors"].astype(np.int64); syms = [str(s) for s in F["symbols"]]; off = F["off"]; cnt = F["count"]; n, NW = len(a), len(syms)
     assert np.array_equal(K["E_ts"].astype(np.int64), a)
-    cfg = json.load(open(f"{W}/inputs/bundle_config.json")); P = cfg["params"]
-    fr = np.load(f"{W}/work/fund_replay.npz"); assert np.array_equal(fr["anchors"], a)
-    ax = np.load(f"{W}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
-    D = np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
+    cfg = json.load(open(f"{N}/inputs/bundle_config.json")); P = cfg["params"]
+    fr = np.load(f"{N}/work/fund_replay.npz"); assert np.array_equal(fr["anchors"], a)
+    ax = np.load(f"{N}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
+    assert os.path.exists(CACHE_NPY), "NEW_S rolling cache .npy removed; rebuild from the npz into THIS root before rerunning"
+    D = np.load(CACHE_NPY, mmap_mode="r")
     h = np.load("/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"); o = np.lexsort((h["col"], h["row"])); hr = h["row"][o].astype(np.int64); hc = h["col"][o].astype(np.int64)
     KZ = np.full((n, NW), np.nan, np.float32); Z24 = KZ.copy(); ZFD = KZ.copy(); QV = KZ.copy(); RN8 = KZ.copy()
     WL = np.full((n, 3), np.nan, np.float32); LRm = np.full((n, 3), np.nan); ready = np.zeros(n, bool); recorded = np.zeros(n, bool)
@@ -83,8 +87,11 @@
     import collections
     rec = {"status": "PRODUCTION_CALIBER_LEGS_NOT_CASH_PNL", "output": out, "sha256": H.sha(out), "ready": int(ready.sum()), "not_ready": int((~ready).sum()),
            "not_ready_reasons": dict(collections.Counter(why.values())), "leg_returns": len(LR["king"]),
-           "first_ready": int(a[np.argmax(ready)]), "inputs": {"features": H.sha(f"{W}/work/NEWS_FEATURES.npz"), "king_oof": H.sha(f"{W}/work/king/KING_OOF.npz"),
-           "fund_replay": H.sha(f"{W}/work/fund_replay.npz")}, "source_sha": H.sha(os.path.abspath(__file__)), "producer": {H.SHADOW_SRC: H.SHADOW_SHA},
+           "first_ready": int(a[np.argmax(ready)]), "inputs": {"features": H.sha(f"{N}/work/NEWS_FEATURES.npz"), "king_oof": H.sha(f"{W}/work/king/KING_OOF.npz"),
+           "fund_replay": H.sha(f"{N}/work/fund_replay.npz"), "rolling_cache_npy": H.sha(CACHE_NPY), "cache_axes": H.sha(f"{N}/work/cache_x0918r_axes.npz")},
+           "source_sha": H.sha(os.path.abspath(__file__)), "producer": {H.SHADOW_SRC: H.SHADOW_SHA},
+           "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
+           "fresh_note": "identical to news_legs.py except the roots; King OOF is FRESH's monthly-fold OOF (PREREG §1 K/E)",
            "seconds": round(time.time() - t0, 1)}
     json.dump(rec, open(f"{W}/receipts/P3_LEGS.json", "w"), indent=1); print("LEGS_DONE", json.dumps({k: rec[k] for k in ("ready", "not_ready", "not_ready_reasons", "leg_returns")}), flush=True)
 
```

## news_train_f10.py -> fresh_train_f10.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_train_f10.py	2026-09-23 19:16:49
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_train_f10.py	2026-09-23 21:15:02
@@ -1,10 +1,9 @@
-"""NEWS P3 F10: train_f10.py (07ac4c67) with ONLY the input section replaced by NEWS inputs (producer-replayed
-171 features, producer member screen on legal∧crypto candidates, production-caliber legs); recipe verbatim.
-F10 V2MAIN/FIX7 with observable-held-price windows, not a proxy MLP.
-
-No deployment; predictions require the complete combo/cash evaluation. The
-171-column architecture, soft rank, EMA, ES loss and fixed epoch match the
-frozen reference. Missing-price handling is an explicit corrected candidate.
+"""FRESH P3 F10: news_train_f10.py with ONLY the three PREREG_fresh_models_newS_2026-09-23.md §1 changes:
+  F1 fold_specs: 2023 / 2024 annual folds + monthly from 2025-01  ->  calendar-month folds for EVERY month from 2023-01
+  F2 gradient window: tr1 = tr[:int(len(tr)*.85)]                 ->  tr1 = tr  (100 %: FIX7 needs no validation slice)
+  E  cutoff = a[first] - 60*14400                                 ->  cutoff = a[first] - 6*14400
+  roots: FRESH root for legs / outputs; NEW_S root (READ-ONLY) for the frozen features and its P2B receipt.
+Network, loss, soft rank, tau schedule, fixed epoch 7, admission rule, mu/sd sampling, receipts: byte-for-byte news_train_f10.py.
 """
 import os
 os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['OMP_NUM_THREADS']='2'
@@ -13,8 +12,11 @@
 import torch
 from torch import nn
 import hashlib
-W=pathlib.Path('/dev/shm/news_2026-09-23')
+W=pathlib.Path('/dev/shm/fresh_2026-09-23')
+N=pathlib.Path('/dev/shm/news_2026-09-23')      # NEW_S root: READ-ONLY frozen features
 NEWT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz');NEWT_SHA='ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
+EMBARGO=6                                       # PREREG §1 E (NEW_S: 60)
+PREREG={'path':'docs/PREREG_fresh_models_newS_2026-09-23.md','commit':'b6e682e0a'}
 def sha(p):
     h=hashlib.sha256()
     with open(p,'rb') as f:
@@ -36,9 +38,10 @@
     return u-u.mean()
 
 def fold_specs(a):
+    """PREREG §1 F: every calendar month from 2023-01 (NEW_S: 2023 and 2024 annual, monthly only from 2025-01)."""
     utc=lambda y,m=1:calendar.timegm((y,m,1,0,0,0))
-    out=[('2023',utc(2023),utc(2024)),('2024',utc(2024),utc(2025))]
-    for y in (2025,2026):
+    out=[]
+    for y in (2023,2024,2025,2026):
         for m in range(1,13):
             start=utc(y,m);end=utc(y+1) if m==12 else utc(y,m+1)
             if start<=a[-1]:out.append((f'{y}{m:02d}',start,end))
@@ -62,10 +65,10 @@
 def main():
     ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=[42,2027],required=True);ap.add_argument('--folds',default='all');args=ap.parse_args()
     assert torch.cuda.is_available(),'GPU required; refuse silently slow CPU fallback'
-    # ---- NEWS input section (the only lines that differ from train_f10.py 07ac4c67) ----
+    # ---- FRESH input section (roots only; recipe below is news_train_f10.py verbatim apart from the three PREREG changes) ----
     r=W/'work';out=r/f'f10_s{args.seed}';out.mkdir(exist_ok=True)
-    files=[r/'NEWS_FEATURES.npz',NEWT,r/'legs.npz',W/'receipts/P2B_FEATURES.json',W/'receipts/P3_LEGS.json']
-    inputs={str(p):sha(p) for p in files};sources={str(p):sha(p) for p in (pathlib.Path(__file__),W/'devices/f10_observability.py',W/'devices/news_hist_features.py',W/'devices/news_legs.py',W/'devices/news_p2_build.py')}
+    files=[N/'work/NEWS_FEATURES.npz',NEWT,r/'legs.npz',N/'receipts/P2B_FEATURES.json',W/'receipts/P3_LEGS.json']
+    inputs={str(p):sha(p) for p in files};sources={str(p):sha(p) for p in (pathlib.Path(__file__),W/'devices/f10_observability.py',W/'devices/news_hist_features.py',W/'devices/fresh_legs.py',W/'devices/news_p2_build.py')}
     assert inputs[str(files[1])]==NEWT_SHA and json.load(open(files[3]))['sha256']==inputs[str(files[0])] and json.load(open(files[4]))['sha256']==inputs[str(files[2])]
     F=np.load(files[0]);T=np.load(files[1],allow_pickle=True);leg=np.load(files[2])
     a=F['anchors'].astype(np.int64);assert np.array_equal(T['symbols'],F['symbols']) and np.array_equal(leg['E_ts'],a) and np.array_equal(leg['symbols'],F['symbols'])
@@ -101,15 +104,15 @@
             assert sha(target/'scores.npz')==old['score_sha256'] and sha(target/'model.pt')==old['model_sha256']
             z=np.load(target/'scores.npz');allpred[z['rows']]=z['P'];reports.append(old);continue
         target.mkdir(exist_ok=False)
-        te=np.flatnonzero((a>=start)&(a<end));first=int(te[0]);cutoff=int(a[first])-60*14400
+        te=np.flatnonzero((a>=start)&(a<end));first=int(te[0]);cutoff=int(a[first])-EMBARGO*14400
         tr=np.flatnonzero((a+14400<=cutoff)&ready&(np.diff(st)>=50));assert len(tr)>=300
-        cut=int(len(tr)*.85);tr1=tr[:cut];assert a[tr1[-1]]+14400<=cutoff
+        tr1=tr;assert a[tr1[-1]]+14400<=cutoff                       # PREREG §1 F: full gradient window (NEW_S: tr[:int(len(tr)*.85)])
         windows=[];rejected=collections.Counter()
         for s in range(int(tr1[0])+24,int(tr1[-1])-96,48):
             span=np.arange(s-24,s+96);ok,why=span_admissible(members,y,span,ready)
             if ok:windows.append(span)
             else:rejected[why['reason']]+=1
-        admission={'fold':tag,'accepted_windows':len(windows),'rejected':dict(rejected),'train_anchors':len(tr1),'max_train_label_end':int(a[tr1[-1]]+14400),'test_start':int(a[first]),'cutoff':cutoff}
+        admission={'fold':tag,'accepted_windows':len(windows),'rejected':dict(rejected),'train_anchors':len(tr1),'max_train_label_end':int(a[tr1[-1]]+14400),'test_start':int(a[first]),'cutoff':cutoff,'embargo_anchors':EMBARGO,'train_frac':1.0}
         (target/'ADMISSION.json').write_text(json.dumps(admission,indent=2));log('F10 admission',args.seed,admission)
         if len(windows)<5:raise ValueError('fewer than 5 observable training windows')
         rowsel=np.concatenate([np.arange(st[i],st[i+1]) for i in tr1[::7]])[::3];xs=XT[torch.as_tensor(rowsel,device=dev)];mu=xs.mean(0);sd=xs.std(0)+1e-6;del xs
@@ -132,7 +135,7 @@
         torch.save({'state_dict':model.state_dict(),'mu':mu,'sd':sd,'input_dim':171,'fixed_epoch_index':7},target/'model.pt')
         np.savez_compressed(target/'scores.npz',P=pred,rows=te,E_ts=a[te],symbols=t['symbols']);allpred[te]=pred
         # Do not report mean cash/net on a filtered test population.
-        rr={'status':'F10_OOF_SCORES_NOT_COMBO_PNL','seed':args.seed,'rng_rule':'constant seed per fold','fold':tag,'inputs':inputs,'sources':sources,'admission':admission,'curve':curve,'fixed_epoch_index':7,'schedule_T_max':15,'updates_end_at_index':7,'test_anchors':len(te),'scored_pairs':int(np.isfinite(pred).sum()),'score_label_missing_pairs':int((np.isfinite(pred)&~np.isfinite(y[te])).sum()),'score_sha256':sha(target/'scores.npz'),'model_sha256':sha(target/'model.pt'),'elapsed_seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(0)}
+        rr={'status':'F10_OOF_SCORES_NOT_COMBO_PNL','seed':args.seed,'rng_rule':'constant seed per fold','fold':tag,'prereg':PREREG,'inputs':inputs,'sources':sources,'admission':admission,'curve':curve,'fixed_epoch_index':7,'schedule_T_max':15,'updates_end_at_index':7,'test_anchors':len(te),'scored_pairs':int(np.isfinite(pred).sum()),'score_label_missing_pairs':int((np.isfinite(pred)&~np.isfinite(y[te])).sum()),'score_sha256':sha(target/'scores.npz'),'model_sha256':sha(target/'model.pt'),'elapsed_seconds':time.monotonic()-started,'gpu':torch.cuda.get_device_name(0)}
         for p,hsh in inputs.items():assert sha(p)==hsh
         for p,hsh in sources.items():assert sha(p)==hsh
         result.write_text(json.dumps(rr,indent=2,allow_nan=False));reports.append(rr);log('F10_FOLD_DONE',tag,args.seed)
```

## news_combo.py -> fresh_combo.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_combo.py	2026-09-23 19:16:38
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_combo.py	2026-09-23 21:15:27
@@ -1,11 +1,9 @@
-"""NEWS P4 combo targets: the researcher's continuous_combo.evolve / combo_target.step (1501c9f6 / d7577e82; chain and
-exec_reshape compiled from combo_stage.py fb5a9407 by combo_target.source_kernels) run UNCHANGED on NEWS production-caliber
-inputs: King rank = legs KZ, F10 score = NEWS F10 OOF (seed), fund rank = legs ZFD (xz_in_base over the replayed M1 base),
-seats = legs WL (production msharpe 900), rn8 = ledger-tail rate*8/iv (no freshness), qv = production qv4h,
-LIVE_MASK = book universe (book_universe.py, the same U-PIT/CRYPTO proxy NEW used) ∧ candidates(A) (legal ∧ crypto).
-Both publication policies are written (the Stage-1 adapter consumes both; scaled_diagnostic is the main reading).
-State starts from zero at 2023-01-01, as in NEW / Stage 1 C5.
-usage: python news_combo.py --seed 42|2027
+"""FRESH P4 combo targets — news_combo.py with ONLY the roots changed (PREREG_fresh_models_newS_2026-09-23.md §1:
+the combo is rebuilt from FRESH's own King OOF / legs / F10 OOF; the evolve/step kernels, the publication policies,
+the universe and the state start are byte-for-byte news_combo.py).
+  NEW_S root (READ-ONLY): NEWS_FEATURES.npz, inputs/bundle_config.json, receipts/P1_members_2025H2on.npz, vendor_live/fea171/combo_stage.py
+  FRESH root            : work/legs.npz, receipts/P3_LEGS.json, work/f10_s<seed>/, work/combo_s<seed>/ (output)
+usage: python fresh_combo.py --seed 42|2027
 """
 import os, sys, json, argparse, collections, datetime, pathlib, hashlib
 import numpy as np
@@ -14,7 +12,9 @@
 from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
 import combo_target
 
-W = pathlib.Path('/dev/shm/news_2026-09-23')
+W = pathlib.Path('/dev/shm/fresh_2026-09-23')
+N = pathlib.Path('/dev/shm/news_2026-09-23')      # NEW_S root: READ-ONLY frozen inputs
+PREREG = {'path': 'docs/PREREG_fresh_models_newS_2026-09-23.md', 'commit': 'b6e682e0a'}
 
 
 def sha(p):
@@ -27,8 +27,8 @@
 def main():
     ap = argparse.ArgumentParser(); ap.add_argument('--seed', type=int, choices=(42, 2027), required=True); args = ap.parse_args()
     froot = W / f'work/f10_s{args.seed}'
-    paths = [W / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'receipts/P3_LEGS.json', froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', W / 'inputs/bundle_config.json',
-             W / 'receipts/P1_members_2025H2on.npz', pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]
+    paths = [N / 'work/NEWS_FEATURES.npz', W / 'work/legs.npz', W / 'receipts/P3_LEGS.json', froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', N / 'inputs/bundle_config.json',
+             N / 'receipts/P1_members_2025H2on.npz', pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]
     ident = {str(p): sha(p) for p in paths}
     rec = json.loads(paths[4].read_text()); lr = json.loads(paths[2].read_text())
     assert rec['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256'] == ident[str(paths[3])]
@@ -49,7 +49,7 @@
     ident[UNIVERSE_PATH] = UNIVERSE_SHA
     config = json.loads(paths[5].read_text())
     sources = {str(p): sha(p) for p in [pathlib.Path(__file__), pathlib.Path(HERE) / 'continuous_combo.py', pathlib.Path(HERE) / 'combo_target.py', pathlib.Path(HERE) / 'book_universe.py',
-                                          W / 'vendor_live/fea171/combo_stage.py']}
+                                          N / 'vendor_live/fea171/combo_stage.py']}
     out = W / f'work/combo_s{args.seed}'; out.mkdir(exist_ok=False)
     mem_u = [members[i] for i in np.flatnonzero(use)]
     # members outside the book universe: counted (they can hold no weight: LIVE_MASK False ⇒ chain's keep excludes them)
@@ -66,11 +66,12 @@
         summary[policy] = {'path': str(p), 'sha': sha(p), 'reasons': counts, 'years': years}
     for p, h in ident.items(): assert sha(p) == h
     for p, h in sources.items(): assert sha(p) == h
-    receipt = {'status': 'NEWS_TARGETS_NOT_EXECUTION_PNL', 'seed': args.seed, 'inputs': ident, 'sources': sources, 'policies': summary,
+    receipt = {'status': 'FRESH_TARGETS_NOT_EXECUTION_PNL', 'seed': args.seed, 'prereg': PREREG, 'inputs': ident, 'sources': sources, 'policies': summary,
                'member_cells_outside_book_universe': outside,
                'state_init': 'zero at 2023-01-01; hypothetical common start, not live archived state',
                'hold_contract': 'trade_mask False = maintain quantities, never King substitution',
-               'limits': ['production-caliber legs replayed on history; seat history starts with King OOF (2022H2)', 'no execution/cash or policy-stop result',
+               'fresh_note': 'identical to news_combo.py except the roots; King/legs/F10 are FRESH (PREREG §1 K/F/E)',
+               'limits': ['production-caliber legs replayed on history; seat history starts with King OOF (2022-07)', 'no execution/cash or policy-stop result',
                           'scaled_diagnostic changes historical publication gate; never current-live literal']}
     (out / 'TARGET_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)); print(json.dumps({k: receipt[k] for k in ('seed', 'member_cells_outside_book_universe')}), json.dumps({k: v['reasons'] for k, v in summary.items()}), flush=True)
 
```

## news_adapter_specs.py -> fresh_adapter_specs.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_adapter_specs.py	2026-09-23 19:16:37
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_adapter_specs.py	2026-09-23 21:16:45
@@ -1,22 +1,39 @@
 #!/usr/bin/env python3
-"""NEWS adapter specs: Stage 1 ADAPTER_SPEC_NEW_s* with ONLY arm / data / scaled / lit / new_receipt replaced by this agent's combo files
-(price_meta, universe and window_first_anchor copied from the Stage 1 spec byte for byte)."""
+"""FRESH adapter specs — news_adapter_specs.py with the arm/data/combo paths pointed at this agent's FRESH combo files.
+price_meta / universe / window_first_anchor are copied byte for byte from the Stage 1 spec, and (when NEW_S's own spec already
+exists) asserted equal to NEW_S's, so FRESH and NEW_S enter the adapter through identical price/universe/window settings.
+usage: python -B fresh_adapter_specs.py PATH,HOME,LC_CTYPE <fresh_root>"""
 import os, sys, json, hashlib
 WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
 W = sys.argv[2]
+N = "/dev/shm/news_2026-09-23"
+COPIED = ("price_meta", "universe", "window_first_anchor")
 def sha(p):
     h = hashlib.sha256()
     with open(p, "rb") as f:
         for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
     return h.hexdigest()
+out = {"device": "fresh_adapter_specs.py", "self_sha256": sha(os.path.abspath(__file__)),
+       "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"}, "specs": {}, "news_spec_agreement": {}}
 for seed in ("42", "2027"):
-    base = json.load(open(f"/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json"))
+    bp = f"/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json"; base = json.load(open(bp))
     c = f"{W}/work/combo_s{seed}"
-    spec = {"arm": f"NEWS_s{seed}", "data": f"NEW_S (news_2026-09-23) combo_s{seed}: producer-replayed features, King + F10 s{seed} retrained",
+    spec = {"arm": f"FRESH_s{seed}", "data": f"FRESH (fresh_2026-09-23) combo_s{seed}: NEW_S producer-replayed features, King monthly folds + F10 all-monthly full-window, seed {seed}",
             "scaled": {"npz": f"{c}/scaled_diagnostic.npz", "sha256": sha(f"{c}/scaled_diagnostic.npz")},
             "lit": {"npz": f"{c}/literal.npz", "sha256": sha(f"{c}/literal.npz")},
             "new_receipt": {"path": f"{c}/TARGET_RECEIPT.json", "sha256": sha(f"{c}/TARGET_RECEIPT.json")},
             "price_meta": base["price_meta"], "universe": base["universe"], "window_first_anchor": base["window_first_anchor"]}
     assert set(spec) == set(base), (sorted(spec), sorted(base))
-    json.dump(spec, open(f"{W}/configs/ADAPTER_SPEC_NEWS_s{seed}.json", "w"), indent=1)
-    print("spec", seed, json.dumps(spec)[:300])
+    np_ = f"{N}/configs/ADAPTER_SPEC_NEWS_s{seed}.json"
+    if os.path.exists(np_):
+        nb = json.load(open(np_)); agree = {k: (nb.get(k) == spec[k]) for k in COPIED}
+        assert all(agree.values()), f"FRESH vs NEW_S adapter spec differs on a copied key: {agree}"
+        out["news_spec_agreement"][seed] = {"news_spec": np_, "news_spec_sha256": sha(np_), "identical_keys": list(COPIED)}
+    else:
+        out["news_spec_agreement"][seed] = {"news_spec": np_, "status": "ABSENT at spec time; copied keys taken from the Stage 1 spec both arms derive from", "stage1_spec": bp, "stage1_spec_sha256": sha(bp)}
+    op = f"{W}/configs/ADAPTER_SPEC_FRESH_s{seed}.json"
+    json.dump(spec, open(op, "w"), indent=1)
+    out["specs"][seed] = {"path": op, "sha256": sha(op)}
+    print("spec", seed, json.dumps(spec)[:300], flush=True)
+json.dump(out, open(f"{W}/receipts/engine/FRESH_ADAPTER_SPECS.json", "w"), indent=1)
+print("FRESH_ADAPTER_SPECS VERDICT=PASS", json.dumps(out["specs"]), flush=True)
```

## news_make_configs.py -> fresh_make_configs.py
```diff
--- multi_asset/exports/research/news_2026-09-23/devices_pod2_1116Z/news_make_configs.py	2026-09-23 19:16:45
+++ multi_asset/exports/research/fresh_2026-09-23/devices/fresh_make_configs.py	2026-09-23 21:17:20
@@ -1,22 +1,27 @@
 #!/usr/bin/env python3
-"""news_make_configs.py — NEW_S run configurations derived by copy from the Stage 1 configs (ovn_make_configs.py), with the leaf-level
-diff asserted before anything is written:
-  RUN_CONFIG_NEWS_s{42,2027}   = Stage 1 RUN_CONFIG_OVN_NEW_s{seed} with ONLY labels (config / status / created_utc / object / pending / ovn),
-                                 per run arm / tag / role / targets.arm / targets.sources (this agent's adapter npz + receipt, shas pinned),
-                                 new_lineage, and paths.pod_root (/dev/shm/news_2026-09-23). Asserted against RUN_CONFIG_OVN_OLD:
-                                 every differing leaf ∈ Stage 1's ALLOWED_NEW_VS_OLD ∪ {paths.pod_root} (the output root).
-  RUN_CONFIG_NEWS_s{seed}X     = the same substitutions on Stage 1 RUN_CONFIG_OVN_NEW_s{seed}X (describe-only extension, scaled main run only).
-usage: python -B news_make_configs.py PATH,HOME,LC_CTYPE <out_dir> <adapter_receipt_s42> <adapter_receipt_s2027> <diff_receipt.json>
+"""fresh_make_configs.py — FRESH run configurations derived BY COPY from the NEW_S configs (the control arm), with the
+leaf-level diff asserted before anything is written (PREREG_fresh_models_newS_2026-09-23.md §2: "配置逐叶 diff 只允许标签 / 目标 / 输出根不同"):
+
+  RUN_CONFIG_FRESH_s{42,2027}   = NEW_S RUN_CONFIG_NEWS_s{seed} with ONLY labels (config / status / created_utc / object / pending / ovn),
+                                  per run arm / tag / role / targets.arm / targets.sources (this agent's adapter npz + receipt, shas pinned),
+                                  new_lineage, and paths.pod_root (/dev/shm/fresh_2026-09-23).
+  RUN_CONFIG_FRESH_s{seed}X     = the same substitutions on RUN_CONFIG_NEWS_s{seed}X (describe-only extension, scaled main run only).
+
+Asserted twice: every differing leaf FRESH vs NEW_S, and FRESH vs Stage 1 RUN_CONFIG_OVN_OLD, is in the allowed set.
+The allowed set is Stage 1's ALLOWED_NEW_VS_OLD as NEW_S used it, verbatim.
+usage: python -B fresh_make_configs.py PATH,HOME,LC_CTYPE <out_dir> <adapter_receipt_s42> <adapter_receipt_s2027> <diff_receipt.json>
 """
 import os, sys, json, time, hashlib, re
 
 WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
 OUTD, AR42, AR2027, DIFF = sys.argv[2:6]
-S1 = "/workspace/old_vs_new_2026-09-23"; POD_ROOT = "/dev/shm/news_2026-09-23"
-STAGE1 = {"OLD": f"{S1}/RUN_CONFIG_OVN_OLD_2026-09-23.json", "NEW_s42": f"{S1}/RUN_CONFIG_OVN_NEW_s42_2026-09-23.json",
-          "NEW_s2027": f"{S1}/RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json", "NEW_s42X": f"{S1}/RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json",
-          "NEW_s2027X": f"{S1}/RUN_CONFIG_OVN_NEW_s2027X_2026-09-23.json", "OLD_HOLD": f"{S1}/RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json"}
-PREREG = {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7", "amendment_1": {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}}
+S1 = "/workspace/old_vs_new_2026-09-23"; NS = "/dev/shm/news_2026-09-23/configs"; POD_ROOT = "/dev/shm/fresh_2026-09-23"
+CONTROL = {"NEWS_s42": f"{NS}/RUN_CONFIG_NEWS_s42_2026-09-23.json", "NEWS_s2027": f"{NS}/RUN_CONFIG_NEWS_s2027_2026-09-23.json",
+           "NEWS_s42X": f"{NS}/RUN_CONFIG_NEWS_s42X_2026-09-23.json", "NEWS_s2027X": f"{NS}/RUN_CONFIG_NEWS_s2027X_2026-09-23.json"}
+STAGE1_OLD = f"{S1}/RUN_CONFIG_OVN_OLD_2026-09-23.json"
+PREREG = {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a",
+          "newS_prereg": {"path": "docs/PREREG_new_servable_models_2026-09-23.md", "commit": "db0123df7"},
+          "newS_amendment_1": {"path": "docs/AMENDMENT_1_new_servable_models_2026-09-23.md", "commit": "63ca0d0bb"}}
 NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
 
 
@@ -44,40 +49,43 @@
     return [{"leaf": k, "a": la.get(k, "<absent>"), "b": lb.get(k, "<absent>")} for k in ks if la.get(k, "<absent>") != lb.get(k, "<absent>")]
 
 
-ALLOWED_NEWS_VS_OLD = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
-                       r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$",
-                       r"^paths\.pod_root$"]
+# verbatim from news_make_configs.py (which took it from Stage 1's ovn_make_configs.py)
+ALLOWED = [r"^config$", r"^status$", r"^created_utc$", r"^object$", r"^pending(\.|$)", r"^ovn(\.|$)", r"^objb_lineage(\.|$)", r"^new_lineage(\.|$)",
+           r"^runs\[\d+\]\.(arm|tag|role)$", r"^runs\[\d+\]\.targets\.arm$", r"^runs\[\d+\]\.targets\.sources(\[\d+\]\.(npz|npz_sha256|receipt|receipt_sha256))?$",
+           r"^paths\.pod_root$"]
 
 
-def check(d, allowed, what):
-    bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in allowed)]
+def check(d, what):
+    bad = [x["leaf"] for x in d if not any(re.search(p, x["leaf"]) for p in ALLOWED)]
     assert not bad, f"{what}: leaves outside the allowed set (settings would differ): {bad[:10]}"
 
 
-C = {k: json.load(open(p)) for k, p in STAGE1.items()}
+C = {k: json.load(open(p)) for k, p in CONTROL.items()}
+OLD = json.load(open(STAGE1_OLD))
 AR = {}
 for seed, p in (("42", AR42), ("2027", AR2027)):
-    R = json.load(open(p)); assert R["arm"] == f"NEWS_s{seed}" and R["roundtrip"]["scaled"]["bitwise_equal"] and R["roundtrip"]["lit"]["bitwise_equal"], "adapter receipt"
-    R["_npz_path"] = f"{POD_ROOT}/targets/TARGETS_NEWS_s{seed}.npz"; assert sha(R["_npz_path"]) == R["targets_npz_sha256"]
+    R = json.load(open(p)); assert R["arm"] == f"FRESH_s{seed}" and R["roundtrip"]["scaled"]["bitwise_equal"] and R["roundtrip"]["lit"]["bitwise_equal"], "adapter receipt"
+    R["_npz_path"] = f"{POD_ROOT}/targets/TARGETS_FRESH_s{seed}.npz"; assert sha(R["_npz_path"]) == R["targets_npz_sha256"]
     AR[seed] = (p, R)
 os.makedirs(OUTD, exist_ok=True)
-rec = {"device": "news_make_configs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "prereg": PREREG,
-       "stage1_configs": {k: {"path": p, "sha256": sha(p)} for k, p in STAGE1.items()}, "pod_root": POD_ROOT, "configs": {}, "diffs": {}}
+rec = {"device": "fresh_make_configs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": NOW, "prereg": PREREG,
+       "control_configs": {k: {"path": p, "sha256": sha(p)} for k, p in CONTROL.items()},
+       "stage1_old_config": {"path": STAGE1_OLD, "sha256": sha(STAGE1_OLD)}, "pod_root": POD_ROOT, "configs": {}, "diffs": {}}
 
 
-def news_cfg(base, seed, ext):
-    N = json.loads(json.dumps(base)); p, R = AR[seed]; arm = f"NEWS_s{seed}"; run_arm = f"NEWS_s{seed}{'X' if ext else ''}"
-    N["config"] = f"RUN_CONFIG_NEWS_s{seed}{'X' if ext else ''}_2026-09-23"
-    N["status"] = f"FROZEN before any NEW_S book number; arm {arm}; settings byte-identical to Stage 1 RUN_CONFIG_OVN_OLD{'X' if ext else ''} (only labels, targets and output root differ)"
+def fresh_cfg(base, seed, ext):
+    N = json.loads(json.dumps(base)); p, R = AR[seed]; arm = f"FRESH_s{seed}"; run_arm = f"FRESH_s{seed}{'X' if ext else ''}"
+    N["config"] = f"RUN_CONFIG_FRESH_s{seed}{'X' if ext else ''}_2026-09-23"
+    N["status"] = f"FROZEN before any FRESH book number; arm {arm}; settings byte-identical to the NEW_S control config (only labels, targets and output root differ)"
     N["created_utc"] = NOW
-    N["object"] = f"NEW_S arm {arm}: producer-code-replayed features, retrained King + F10 s{seed}, combo via combo_target (scaled_diagnostic = scaled reading, literal = lit reading), through ovn_adapter.py"
-    N["pending"] = {"(a) targets": f"filled: TARGETS_{arm} (adapter round-trip bitwise PASS)", "(b) the controls": "Stage 1 OLD / OLD_HOLD runs (reused, path shas re-checked)"}
-    N["ovn"] = dict(N["ovn"], role=f"NEW_S arm {arm}", news_prereg=PREREG, derived_by="news_make_configs.py")
+    N["object"] = f"FRESH arm {arm}: NEW_S producer-replayed features, King calendar-month folds + F10 all-monthly full-gradient-window, embargo 6 anchors, seed {seed}; combo via combo_target (scaled_diagnostic = scaled reading, literal = lit reading), through ovn_adapter.py"
+    N["pending"] = {"(a) targets": f"filled: TARGETS_{arm} (adapter round-trip bitwise PASS)", "(b) the control": "NEW_S same-seed runs (reused; config leaves diffed and asserted)"}
+    N["ovn"] = dict(N["ovn"], role=f"FRESH arm {arm}", fresh_prereg=PREREG, derived_by="fresh_make_configs.py", control_arm=f"NEWS_s{seed}")
     N["paths"]["pod_root"] = POD_ROOT
     N["new_lineage"] = {"arm": arm, "adapter_receipt": {"path": p, "sha256": sha(p)}, "new_target_receipt": R["adapter"]["new_receipt"], "sources": R["adapter"]["sources"]}
     for r in N["runs"]:
-        old_arm = r["arm"]; r["arm"] = run_arm; r["tag"] = run_arm + "|" + r["tag"].split("|", 1)[1]
-        r["role"] = re.sub(r"NEW arm NEW_s\d+", f"NEW_S arm {arm}", r["role"])
+        r["arm"] = run_arm; r["tag"] = run_arm + "|" + r["tag"].split("|", 1)[1]
+        r["role"] = re.sub(r"NEW_S arm NEWS_s\d+", f"FRESH arm {arm}", r["role"])
         r["targets"]["arm"] = arm
         r["targets"]["sources"] = [{"npz": R["_npz_path"], "npz_sha256": R["targets_npz_sha256"], "receipt": p, "receipt_sha256": sha(p)}]
     return N
@@ -85,18 +93,18 @@
 
 docs = {}
 for seed in ("42", "2027"):
-    N = news_cfg(C[f"NEW_s{seed}"], seed, False); d = diff(C["OLD"], N); check(d, ALLOWED_NEWS_VS_OLD, f"NEWS_s{seed} vs OVN_OLD"); rec["diffs"][f"NEWS_s{seed}_vs_OVN_OLD"] = d
-    d2 = diff(C[f"NEW_s{seed}"], N); check(d2, ALLOWED_NEWS_VS_OLD, f"NEWS_s{seed} vs OVN_NEW_s{seed}"); rec["diffs"][f"NEWS_s{seed}_vs_OVN_NEW_s{seed}"] = d2
-    docs[f"RUN_CONFIG_NEWS_s{seed}_2026-09-23.json"] = N
-    NX = news_cfg(C[f"NEW_s{seed}X"], seed, True); d = diff(C[f"NEW_s{seed}X"], NX); check(d, ALLOWED_NEWS_VS_OLD, f"NEWS_s{seed}X vs OVN_NEW_s{seed}X"); rec["diffs"][f"NEWS_s{seed}X_vs_OVN_NEW_s{seed}X"] = d
-    docs[f"RUN_CONFIG_NEWS_s{seed}X_2026-09-23.json"] = NX
-# OLD_HOLD control: Stage 1 config vs OLD, re-listed for the record (no new run)
-rec["diffs"]["stage1_OVN_OLD_HOLD_vs_OVN_OLD_leaves"] = [x["leaf"] for x in diff(C["OLD"], C["OLD_HOLD"])]
+    N = fresh_cfg(C[f"NEWS_s{seed}"], seed, False)
+    d = diff(C[f"NEWS_s{seed}"], N); check(d, f"FRESH_s{seed} vs NEWS_s{seed}"); rec["diffs"][f"FRESH_s{seed}_vs_NEWS_s{seed}"] = d
+    d2 = diff(OLD, N); check(d2, f"FRESH_s{seed} vs OVN_OLD"); rec["diffs"][f"FRESH_s{seed}_vs_OVN_OLD"] = d2
+    docs[f"RUN_CONFIG_FRESH_s{seed}_2026-09-23.json"] = N
+    NX = fresh_cfg(C[f"NEWS_s{seed}X"], seed, True)
+    dx = diff(C[f"NEWS_s{seed}X"], NX); check(dx, f"FRESH_s{seed}X vs NEWS_s{seed}X"); rec["diffs"][f"FRESH_s{seed}X_vs_NEWS_s{seed}X"] = dx
+    docs[f"RUN_CONFIG_FRESH_s{seed}X_2026-09-23.json"] = NX
 for fn, D in docs.items():
     assert not [k for k, v in leaves(D).items() if v == "PENDING"], f"{fn} holds PENDING"
     op = os.path.join(OUTD, fn); json.dump(D, open(op, "w"), indent=1, ensure_ascii=False)
     rec["configs"][fn] = {"path": op, "sha256": sha(op), "runs": [r["tag"] for r in D["runs"]], "window": [D["window"]["first_anchor"], D["window"]["last_anchor"]]}
-rec["settings_identical_statement"] = "every differing leaf between a NEWS config and Stage 1 OVN_OLD is labels / arm-tag-role / targets / lineage / output root; asserted"
-rec["allowed"] = ALLOWED_NEWS_VS_OLD
+rec["settings_identical_statement"] = "every differing leaf between a FRESH config and its NEW_S control (and Stage 1 OVN_OLD) is labels / arm-tag-role / targets / lineage / output root; asserted"
+rec["allowed"] = ALLOWED
 json.dump(rec, open(DIFF, "w"), indent=1, ensure_ascii=False)
-print("NEWS_MAKE_CONFIGS VERDICT=PASS", {k: v["sha256"][:16] for k, v in rec["configs"].items()}, "diff_receipt", sha(DIFF), flush=True)
+print("FRESH_MAKE_CONFIGS VERDICT=PASS", {k: v["sha256"][:16] for k, v in rec["configs"].items()}, "diff_receipt", sha(DIFF), flush=True)
```

