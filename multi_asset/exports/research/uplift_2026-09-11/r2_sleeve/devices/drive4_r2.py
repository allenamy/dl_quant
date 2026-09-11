import sys; sys.argv=["x","none"]
exec(open("/workspace/uplift_2026-09-11/r2_sleeve/drive2_r2.py").read().replace("if __name__==\"__main__\":","if False:"))
ZT_raw=ema(TBF,8)
# COST-MATCHED placebo: a FIXED random relabelling of symbols. Each name keeps a real, equally smooth
# series (so turnover matches), but it is attached to the wrong name => cross-sectional link destroyed.
rng=np.random.default_rng(20260913); pidx=rng.permutation(ZT_raw.shape[1])
run("TBF_PLA_relabel", orth(lagn(rz(ZT_raw[:,pidx]),1)))
# sign-flip of the survivor (AMENDMENT 1 antisymmetry is empirically FALSE -- measure it)
run("TBF_ema08_MINUS", -orth(lagn(rz(ZT_raw),1)))
# per-anchor permuted placebo of the SMOOTHED feature
run("TBF_PLA_permsm", orth(lagn(rz(perm(ZT_raw,20260914)),1)))
print("DONE_stage4",flush=True)
