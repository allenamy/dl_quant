"""B1 needs a like-for-like comparison, so the holefix prod meta is restricted to the ORIGINAL 10,176 anchor
set (the +6 anchors that the 08-31 repair unlocked have no king prediction and are outside the gate region
anyway). The extension window handles them separately."""
import numpy as np, os, time
KM = np.load("/workspace/data/wide_fea_v2holefix_meta.npz", allow_pickle=True)
TG = np.load("/workspace/dlw_holefix/data/dlw_targets.npz", allow_pickle=True)
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True)
kt = KM["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64); mt = MN["E_ts"].astype(np.int64)
rk = {int(x): i for i, x in enumerate(kt)}; rt = {int(x): i for i, x in enumerate(tt)}
keep = np.array([rk[int(x)] for x in mt])
kti = np.array([rt[int(x)] for x in mt])
y4 = TG["y4s"][kti].astype(np.float32)
out = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_holefix_t10176.npz"
np.savez_compressed(out, E_ts=kt[keep], members=KM["members"][keep], y4=y4, qvk=KM["qvk"][keep], names=KM["names"])
print("wrote %s  anchors %d  (axis identical to old meta: %s)" % (out, len(keep), bool((kt[keep] == mt).all())))
print("members identical to old meta on all anchors: %s"
      % all(np.array_equal(np.asarray(KM["members"][keep][i]), np.asarray(MN["members"][i])) for i in range(0, len(mt), 250)))
