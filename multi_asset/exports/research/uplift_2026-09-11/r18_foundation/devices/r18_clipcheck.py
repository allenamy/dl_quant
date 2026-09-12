#!/usr/bin/env python3
"""r18_clipcheck.py — explains GATE_Y2's 590 value-mismatch cells (PREREG_AMENDMENT_1 'reported, not a stop'):
hypothesis (from the SOLVUSDT 2025-10-10 20Z bars) = the 5m cache's ret5 channel is hard-clipped at +-0.30 per bar, while the
accounting meta's y4 is RAW (unclipped) => clip-then-compound (E-0908-B family). Tests: (1) global bound of ret5; (2) every
mismatch cell has >=1 forward bar at the bound; (3) every finite cell with a bound bar in its forward window is a mismatch cell
(or differs by < tol). Read-only. Writes receipts/RECEIPT_r18_clipcheck.json."""
import os, sys, json, time, hashlib, zipfile
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
R = "/workspace/uplift_2026-09-11/r18_foundation"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
AMEND_SHA = "f8c23823259ee542c29672958ee1f53e066f50022843e9b14e77f88b32994025"; assert sha(R + "/PREREG_AMENDMENT_1_r18_2026-09-12.md") == AMEND_SHA
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; A0 = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz"; CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], np.float32)
ts = np.load(A0, allow_pickle=True)["rec"][:, 0].astype(np.int64); i = np.searchsorted(E, ts); assert np.array_equal(E[i], ts)
z = zipfile.ZipFile(CACHE)
with z.open("ch.npy") as f: CH = [str(c) for c in np.lib.format.read_array(f)]
with z.open("ts.npy") as f: CTS = np.lib.format.read_array(f).astype(np.int64)
with z.open("symbols.npy") as f: SYM = [str(c) for c in np.lib.format.read_array(f)]
with z.open("data.npy") as f: D = np.lib.format.read_array(f)
R16 = D[:, :, CH.index("ret5")]; del D
fin = np.isfinite(R16); v = R16[fin]
BOUND = float(np.abs(v).max()); n_at = int((np.abs(v) >= BOUND - 1e-7).sum()); n_gt_03 = int((np.abs(v) > 0.3).sum())
RET = R16.astype(np.float64); cpos = {int(t): k for k, t in enumerate(CTS)}
mism = 0; mism_with_bound = 0; bound_cells = 0; bound_cells_mismatch = 0; fin_cells = 0; ex = []
for a in range(len(ts)):
    k = cpos[int(ts[a])]; seg = RET[k + 1:k + 49]; nf = np.isfinite(seg).sum(0); p = np.nanprod(1.0 + seg, 0) - 1.0; p[nf < 46] = np.nan
    ref = y4[i[a]].astype(np.float64); ok = np.isfinite(ref) & np.isfinite(p); fin_cells += int(ok.sum())
    d = np.abs(ref - p); d[~ok] = 0.0; hasb = (np.nan_to_num(np.abs(seg), nan=0.0) >= BOUND - 1e-7).any(0)
    m_ = d > 1e-5; mism += int(m_.sum()); mism_with_bound += int((m_ & hasb).sum()); bound_cells += int((hasb & ok).sum()); bound_cells_mismatch += int((hasb & ok & m_).sum())
    for b in np.nonzero(m_ & ~hasb)[0][:5]: ex.append(dict(iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[a]))), symbol=SYM[b], y4_meta=float(ref[b]), y4_cache=float(p[b]), max_abs_bar=float(np.nanmax(np.abs(seg[:, b])))))
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), env=ENV, ret5_channel_bound_abs=BOUND, n_bars_at_bound=n_at, n_bars_abs_gt_0p3=n_gt_03, finite_cells=fin_cells, mismatch_cells=mism, mismatch_cells_with_bound_bar=mism_with_bound,
           cells_with_bound_bar_in_fwd_window=bound_cells, of_which_mismatch=bound_cells_mismatch, mismatch_cells_without_bound_bar_examples=ex[:20], n_mismatch_without_bound_bar=mism - mism_with_bound,
           explanation_holds=bool(mism_with_bound == mism), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(OUT, open(R + "/receipts/RECEIPT_r18_clipcheck.json", "w"), indent=1); print(json.dumps({k: v for k, v in OUT.items() if k not in ("env", "mismatch_cells_without_bound_bar_examples")})); print("examples without bound bar:", ex[:5]); print("DONE_r18_clipcheck")
