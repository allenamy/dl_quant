import numpy as np, glob, os, sys
new={os.path.basename(p):p for p in glob.glob("/workspace/review_scratch/costdose/SELFCHK/shard*/preds_fold/*.npz")}
old={os.path.basename(p):p for p in glob.glob("/workspace/review_scratch/allweather_trackB/earlystop/FIX7/shard*/preds_fold/*.npz")}
if not new:
    print("SELFCHK_FAIL no preds produced"); sys.exit(1)
bad=[]
for k in sorted(new):
    if k not in old: bad.append((k,"-","missing in archive")); continue
    A,B=np.load(new[k]),np.load(old[k])
    if sorted(A.files)!=sorted(B.files): bad.append((k,"-","keyset")); continue
    for f in sorted(A.files):
        a,b=A[f],B[f]
        if a.shape!=b.shape: bad.append((k,f,"shape")); continue
        if a.dtype.kind=="f":
            d=float(np.nanmax(np.abs(np.nan_to_num(a)-np.nan_to_num(b)))) if a.size else 0.0
            nm=int((np.isnan(a)!=np.isnan(b)).sum())
            if d!=0.0 or nm: bad.append((k,f,"maxabs=%.3e nan=%d"%(d,nm)))
        elif not np.array_equal(a,b): bad.append((k,f,"neq"))
    status = "MISMATCH" if any(x[0]==k for x in bad) else "OK"
    print("  %s: %s" % (k,status))
print("compared %d folds" % len(new))
if bad:
    print("SELFCHK_FAIL"); [print("   ",*x) for x in bad]; sys.exit(1)
print("SELFCHK_PASS")
