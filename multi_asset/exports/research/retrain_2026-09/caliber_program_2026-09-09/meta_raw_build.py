"""meta_newprod_raw: ORIGINAL meta_newprod (10176 anchors, original members/qvk) with y4 <- dlw_raw32 y4s (raw-return target).
Gate: y4 differs from meta_newprod.y4 exactly on the expected clip windows (+ cumsum noise <= 1e-6); everything else bitwise."""
import numpy as np, os, sys, time
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True); TG = np.load(os.environ.get("DLW_RAW", "/workspace/dlw_raw32") + "/data/dlw_targets.npz", allow_pickle=True)
mt = MN["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64); rt = {int(x): i for i, x in enumerate(tt)}; idx = np.array([rt[int(x)] for x in mt]); y4 = TG["y4s"][idx].astype(np.float32)
F = np.load("/workspace/review_scratch/clip_flags.npz", allow_pickle=True); fts = F["E_ts"].astype(np.int64); has = F["has"]; gi = {int(t): i for i, t in enumerate(fts)}
old = MN["y4"]; fa, fb = np.isfinite(old), np.isfinite(y4); assert np.array_equal(fa, fb), "finiteness changed"
d = np.abs(old.astype(np.float64) - y4.astype(np.float64)); ch = fa & (d > 0)
exp = np.zeros_like(ch)
for i, t in enumerate(mt):
    j = gi.get(int(t))
    if j is not None: exp[i] = has[j] & fa[i]
real_out = int((ch & ~exp & (d > 1e-6)).sum()); print("y4 changed cells %d ; expected-window cells %d ; outside-expected real (>1e-6) %d ; outside noise max %.2e" % (int(ch.sum()), int((ch & exp).sum()), real_out, d[ch & ~exp].max() if (ch & ~exp).any() else 0.0), flush=True)
assert real_out == 0
out = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_raw.npz"; np.savez_compressed(out, E_ts=mt, members=MN["members"], y4=y4, qvk=MN["qvk"], names=MN["names"]); print("written", out, flush=True); print("META_RAW_DONE", flush=True)
