import numpy as np
z = np.load("data/npz_v2arch/2025-01-09.npz"); y600 = z["y_600"]; m600 = z["y_mask_600"].astype(bool)
s = np.load("data/npz_v2arch_y180/2025-01-09.npz"); y180 = s["y_180"]; m180 = s["y_mask_180"].astype(bool)
both = m600 & m180
print("valid=%d std(y180)=%.2fbps std(y600)=%.2fbps ratio=%.2f (expect ~0.5-0.6)" % (
    both.sum(), np.std(y180[both])*1e4, np.std(y600[both])*1e4, np.std(y180[both])/np.std(y600[both])))
print("corr(y180,y600)=%.3f ts_aligned=%s" % (
    np.corrcoef(y180[both], y600[both])[0,1], np.array_equal(z["timestamps"], s["timestamps"])))
