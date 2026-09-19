"""AX09b (axis_0919): the member rule of the accounting meta against the UNMASKED September reference, with the chain's ONE implementation
(fp2_gate_lib.members_subset_check, AMENDMENT 8 + F06, truncation-aware) called exactly as build_dev_v4.py L33-39 does under DEV_MEMBER_MASK_NPZ:
common anchors outside the hole neighbourhoods, control = reference members, masked = this build's members, mask rows = the declared member mask.
ax09's plain subset count lists 'additions' without checking truncation; this receipt is the rule's verdict. Pure reads.
env: META (this build) REF_META CACHE HOLE_CELLS MEMBER_MASK GATE_LIB_DIR RECEIPT
"""
import os, sys, json, time, hashlib, zipfile
import numpy as np
E = {k: os.environ[k] for k in ("META", "REF_META", "CACHE", "HOLE_CELLS", "MEMBER_MASK", "GATE_LIB_DIR", "RECEIPT")}
assert not os.path.exists(E["RECEIPT"])
sys.path.insert(0, E["GATE_LIB_DIR"]); import fp2_gate_lib as GL
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
with zipfile.ZipFile(E["CACHE"]) as z:
    CTS = np.load(z.open("ts.npy")).astype(np.int64); csyms = [str(s) for s in np.load(z.open("symbols.npy"), allow_pickle=True)]
M4 = np.load(E["META"], allow_pickle=True); MR = np.load(E["REF_META"], allow_pickle=True)
E4 = M4["E_ts"].astype(np.int64); ER = MR["E_ts"].astype(np.int64)
com = np.intersect1d(E4, ER); i4 = np.searchsorted(E4, com); ir = np.searchsorted(ER, com); rows = np.searchsorted(CTS, com)
NEIGH = np.load(E["HOLE_CELLS"], allow_pickle=True)["neigh_rows"]; inn = np.zeros(len(com), bool)
for lo, hi in NEIGH: inn |= (rows >= lo) & (rows <= hi)
nz = np.nonzero(~inn)[0]; Ek = com[nz].astype(np.int64)
MASKk, why = GL.mask_rows(E["MEMBER_MASK"], Ek, csyms); assert why is None, why
M4m = M4["members"]; MRm = MR["members"]
sc = GL.members_subset_check(Ek, [MRm[ir[k]] for k in nz], Ek, [M4m[i4[k]] for k in nz], MASKk, ntop=400, MASK_c=MASKk, min_mem=50)
rep = {"device": "ax09b_member_rule.py", "self_sha256": sha(os.path.abspath(__file__)), "gate_lib_sha256": sha(os.path.join(E["GATE_LIB_DIR"], "fp2_gate_lib.py")),
       "env": E, "inputs_sha256": {k: sha(E[k]) for k in ("META", "REF_META", "HOLE_CELLS", "MEMBER_MASK")},
       "n_common": int(len(com)), "n_common_outside_neigh": int(len(nz)), "members_subset_check": sc}
json.dump(rep, open(E["RECEIPT"], "w"), indent=1, default=str)
print("AX09B_DONE", json.dumps(sc, default=str), flush=True)
