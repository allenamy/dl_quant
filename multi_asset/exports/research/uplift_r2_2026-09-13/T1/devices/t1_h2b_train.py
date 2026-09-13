#!/usr/bin/env python3
"""t1_h2b_train.py — pod2, read-only (PREREG_T1 §6 H2b as amended by AMENDMENT 3).
For each training feature file, on cells where the panel f_fund_iv == 4 and float16(v0) != float16(v1):
  s0 = share of stored fund_ema == float16(nan->0(f_fund_ema))      (v0 = raw per-settlement-rate EMA)
  s1 = share of stored fund_ema == float16(nan->0(f_fund_ema_v1))   (v1 = rate*8/iv EMA)
Files: /workspace/data/wide_fea_v2ext.npy (+_meta), /workspace/data/wide_fea_v4.npy (+_meta), /workspace/dlw_ext/data/dlw_fea82.npz, /workspace/dlw_v4raw/data/dlw_fea82.npz.
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T1"
SH = {"PREREG_T1_edge_diagnosis_2026-09-13.md": "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6", "PREREG_AMENDMENT_1_T1_2026-09-13.md": "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373",
      "PREREG_AMENDMENT_2_T1_2026-09-13.md": "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207", "PREREG_AMENDMENT_3_T1_2026-09-13.md": "e6afc13879c6332520d7f3876f2adc212468e98594c312baf5fab035483685e8"}
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
for f, h in SH.items(): assert sha(R + "/" + f) == h, f
t0 = time.time()
PAN = "/workspace/data/wide_panel_4h_v2ext.npz"
P = np.load(PAN, allow_pickle=True); pts = P["ts"].astype(np.int64); PSYM = [str(s) for s in P["symbols"]]; prow = {int(t): j for j, t in enumerate(pts)}
V0 = P["f_fund_ema"]; V1 = P["f_fund_ema_v1"]; IV = P["f_fund_iv"]
C0 = np.float16(np.nan_to_num(V0, nan=0.0)); C1 = np.float16(np.nan_to_num(V1, nan=0.0))
OUT = {"panel": dict(path=PAN, sha256=sha(PAN))}
def tally(stored, c0, c1):
    use = c0 != c1
    return int(use.sum()), int((stored[use] == c0[use]).sum()), int((stored[use] == c1[use]).sum())
for name, fea, meta in (("king_v2ext_0901", "/workspace/data/wide_fea_v2ext.npy", "/workspace/data/wide_fea_v2ext_meta.npz"), ("king_v4", "/workspace/data/wide_fea_v4.npy", "/workspace/data/wide_fea_v4_meta.npz")):
    F = np.load(fea, mmap_mode="r"); M = np.load(meta, allow_pickle=True); names = [str(x) for x in M["names"]]; c = names.index("fund_ema")
    E = M["E_ts"].astype(np.int64); MS = M["members"]
    n = s0 = s1 = 0; n_anch = 0; nonzero_stored = 0
    for i in range(len(E)):
        j = prow.get(int(E[i]))
        if j is None: continue
        m = np.asarray(MS[i], dtype=np.int64); m4 = m[IV[j, m] == 4.0]
        if len(m4) == 0: continue
        st = np.asarray(F[i, m4, c]); a, b, d = tally(st, C0[j, m4], C1[j, m4]); n += a; s0 += b; s1 += d; n_anch += 1; nonzero_stored += int((st != 0).sum())
    OUT[name] = dict(fea=fea, fea_sha256=sha(fea), meta=meta, meta_sha256=sha(meta), col=c, shape=list(F.shape), dtype=str(F.dtype), anchors_with_4h_cells=n_anch, n_cells=n, s0=(s0 / n if n else None), s1=(s1 / n if n else None), stored_nonzero=nonzero_stored)
    print(name, json.dumps(OUT[name]), round(time.time() - t0, 1), flush=True)
for name, fea, tg in (("dl_ext_0901", "/workspace/dlw_ext/data/dlw_fea82.npz", "/workspace/dlw_ext/data/dlw_targets.npz"), ("dl_v4raw", "/workspace/dlw_v4raw/data/dlw_fea82.npz", "/workspace/dlw_v4raw/data/dlw_targets.npz")):
    Z = np.load(fea, allow_pickle=True); names = [str(x) for x in Z["names"]]; c = names.index("fund_ema")
    T = np.load(tg, allow_pickle=True); Ets = T["E_ts"].astype(np.int64); TSYM = [str(s) for s in T["symbols"]]
    colmap = np.array([PSYM.index(s) if s in PSYM else -1 for s in TSYM], np.int64)
    pa = Z["pair_a"].astype(np.int64); ps = Z["pair_s"].astype(np.int64); X = Z["X"][:, c]
    ts = Ets[pa]; jj = np.array([prow.get(int(t), -1) for t in ts]); nn = colmap[ps]
    ok = (jj >= 0) & (nn >= 0)
    iv = np.full(len(ok), np.nan, np.float32); iv[ok] = IV[jj[ok], nn[ok]]
    sel = ok & (iv == 4.0)
    a, b, d = tally(X[sel], C0[jj[sel], nn[sel]], C1[jj[sel], nn[sel]])
    OUT[name] = dict(fea=fea, fea_sha256=sha(fea), targets=tg, targets_sha256=sha(tg), col=c, dtype=str(X.dtype), n_pairs=int(len(pa)), n_cells=a, s0=(b / a if a else None), s1=(d / a if a else None),
                     symbols_axis_equal_panel=bool(TSYM == PSYM))
    print(name, json.dumps(OUT[name]), round(time.time() - t0, 1), flush=True)
files = ["king_v2ext_0901", "king_v4", "dl_ext_0901", "dl_v4raw"]
train_v0 = all(OUT[f]["s0"] is not None and OUT[f]["s0"] >= 0.99 and OUT[f]["s1"] <= 0.01 for f in files)
train_v1 = all(OUT[f]["s1"] is not None and OUT[f]["s1"] >= 0.99 and OUT[f]["s0"] <= 0.01 for f in files)
OUT["training_caliber"] = "v0" if train_v0 else ("v1" if train_v1 else "NOT DECIDABLE")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg=SH, result=OUT, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_h2b_train.json", "w"), indent=1, default=str)
print("TRAINING_CALIBER", OUT["training_caliber"]); print("DONE_t1_h2b_train", RC["wall_s"])
