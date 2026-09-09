"""meta_newprod_hf2: king meta (holefix features chain, 10182 anchors) with y4 <- dlw_hf2 y4s (compounded target), same recipe
that produced meta_newprod (verified: E_ts/members/qvk/names identical to king meta, y4 == dlw y4s maxabs 0).
GATE: on anchors < 2026-08-12 00:00Z the new meta must equal the old meta_newprod bitwise (E_ts, members, qvk, y4)."""
import numpy as np, time, calendar, sys
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
KM = np.load("/workspace/data/wide_fea_v2holefix_meta.npz", allow_pickle=True); TG = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True)
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True)
kt = KM["E_ts"].astype(np.int64); tt = TG["E_ts"].astype(np.int64); mt = MN["E_ts"].astype(np.int64)
MNm = MN["members"]; KMm = KM["members"]; MNy = MN["y4"]; MNq = MN["qvk"].astype(float); KMq = KM["qvk"].astype(float)   # materialise once
rt = {int(x): i for i, x in enumerate(tt)}; idx = np.array([rt[int(x)] for x in kt]); y4 = TG["y4s"][idx].astype(np.float32)
out = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_hf2.npz"
np.savez_compressed(out, E_ts=kt, members=KM["members"], y4=y4, qvk=KM["qvk"], names=KM["names"])
CH = calendar.timegm((2026, 8, 12, 0, 0, 0)); assert (kt[:len(mt)] == mt).all()
pre = np.where(mt < CH)[0]; bad = 0
for i in pre:
    if not np.array_equal(np.asarray(MNm[i]), np.asarray(KMm[i])): bad += 1
a = MNy[pre]; b = y4[pre]; ya = np.array_equal(np.nan_to_num(a, nan=-9e9), np.nan_to_num(b, nan=-9e9))
qa = np.array_equal(np.nan_to_num(MNq[pre], nan=-9e9), np.nan_to_num(KMq[pre], nan=-9e9))
print("meta_newprod_hf2 written: anchors %d (old %d) ; pre-change anchors %d ; members differ %d ; y4 bitwise %s ; qvk bitwise %s" % (len(kt), len(mt), len(pre), bad, ya, qa), flush=True)
# post-change descriptive
post = np.where(mt >= CH)[0]; ch = 0; first = None
for i in post:
    same = np.array_equal(np.asarray(MNm[i]), np.asarray(KMm[i])) and np.array_equal(np.nan_to_num(MNy[i], nan=-9e9), np.nan_to_num(y4[i], nan=-9e9))
    if not same:
        ch += 1
        if first is None: first = mt[i]
print("post-change anchors %d ; changed %d ; FIRST %s ; extra anchors %s" % (len(post), ch, T(first) if first else "-", [T(x) for x in kt[len(mt):]]), flush=True)
print("META_HF2_GATE %s" % ("PASS" if (bad == 0 and ya and qa) else "FAIL"), flush=True); sys.exit(0 if (bad == 0 and ya and qa) else 3)
