"""PREREG caliber §2 gate C1: wide_fea_v2ext_clamp vs wide_fea_v2ext must differ ONLY at anchors with E_row<8640 (138) and
ONLY in the 16 columns of the 8640-window family; meta bitwise identical."""
import numpy as np, sys, time
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); MN = np.load("/workspace/data/wide_fea_v2ext_clamp_meta.npz", allow_pickle=True)
eo = MO["E_ts"].astype(np.int64); en = MN["E_ts"].astype(np.int64); names = [str(x) for x in MO["names"]]
ok = eo.shape == en.shape and (eo == en).all() and [str(x) for x in MN["names"]] == names
MEMO, MEMN = MO["members"], MN["members"]
ok &= all(np.array_equal(np.asarray(MEMO[i]), np.asarray(MEMN[i])) for i in range(len(eo)))
ok &= np.array_equal(np.nan_to_num(MO["y4"], nan=-9e9), np.nan_to_num(MN["y4"], nan=-9e9)) and np.array_equal(np.nan_to_num(MO["qvk"].astype(float), nan=-9e9), np.nan_to_num(MN["qvk"].astype(float), nan=-9e9))
print("meta identical (E_ts/members/y4/qvk/names): %s" % ok, flush=True)
import sys as _s; _s.path.insert(0, "/workspace"); from zload import zload
CTS = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)["ts"].astype(np.int64); rowof = {int(t): k for k, t in enumerate(CTS)}
erow = np.array([rowof[int(t)] for t in eo]); expect_anchor = erow < 8640
cols8640 = np.array(["8640" in n for n in names])
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2ext_clamp.npy", mmap_mode="r")
bad_anchor = 0; bad_col = 0; changed_anchors = 0; cells = 0; sat_before = 0; sat_after = 0
for i in range(len(eo)):
    a = np.asarray(FO[i], dtype=np.float64); b = np.asarray(FN[i], dtype=np.float64)
    d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
    if d.any():
        changed_anchors += 1; cells += int(d.sum())
        if not expect_anchor[i]: bad_anchor += 1
        if d[:, ~cols8640].any(): bad_col += 1
        sat_before += int((np.abs(a[:, cols8640]) >= 1e4).sum()); sat_after += int((np.abs(b[:, cols8640]) >= 1e4).sum())
print("changed anchors %d (expected %d with E_row<8640) ; cells %d ; changed anchors OUTSIDE expectation %d ; anchors touching non-8640 columns %d" % (changed_anchors, int(expect_anchor.sum()), cells, bad_anchor, bad_col), flush=True)
print("8640-family cells saturated at ±1e4: before %d -> after %d" % (sat_before, sat_after), flush=True)
ok &= (bad_anchor == 0 and bad_col == 0 and changed_anchors <= int(expect_anchor.sum()))
print("GATE_C1 %s" % ("PASS" if ok else "FAIL")); sys.exit(0 if ok else 3)
