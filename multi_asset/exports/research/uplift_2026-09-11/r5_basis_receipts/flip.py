"""R5/ND1 POST-HOC (declared AFTER seeing the sign of the declared arms; NOT a pre-registered admission test).
The 10 declared arms all carry the device convention high-score -> LONG, inherited from the fund leg.
Every basis arm read NEGATIVE. This builds the sign-reversed signal so the magnitude can be attacked."""
import numpy as np, json, glob, os
R="/workspace/uplift_2026-09-11/r5_basis"
MAN={}
for p in sorted(glob.glob(R+"/dev/sig/R5_*.npz")):
    b=os.path.basename(p)[:-4]
    Z=np.load(p,allow_pickle=True)
    q=R+"/dev/sig/R5_F%s.npz"%b[3:]
    np.savez(q,symbols=Z["symbols"],ts=Z["ts"],mat=(-np.asarray(Z["mat"],float)).astype(np.float32))
    MAN["F"+b[3:]]={"path":q}
json.dump(MAN,open(R+"/SIG_MANIFEST.json","w"),indent=1)
print(json.dumps(MAN,indent=1))
