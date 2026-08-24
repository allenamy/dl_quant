import sys, numpy as np
HERE = "/mnt/storage/private/work_hsy/f8_2026-08-22"; sys.path.insert(0, HERE)
import f3_zoo_nonfunding_leg as f3
f3.load_all()
L = np.load(f"{HERE}/data/f10v2_legs.npz", allow_pickle=True)
d_ts = L["E_ts"].astype(np.int64)
wa_ts = f3.G["E_ts"].astype(np.int64); rmap = {int(t): j for j, t in enumerate(wa_ts)}
TG = np.load(f"{HERE}/../dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)
dsyms = [str(s) for s in TG["symbols"]]; wa_syms = f3.G["syms"]
smap = np.array([wa_syms.index(s) if s in wa_syms else -1 for s in dsyms]); ok = smap >= 0
KZ = np.full(L["Z24"].shape, np.nan, np.float32)
for i, t in enumerate(d_ts):
    j = rmap.get(int(t))
    if j is not None:
        m = f3.G["members"][j]
        z = np.full(len(wa_syms), np.nan, np.float32)
        z[m] = np.nan_to_num(f3.xz(f3.G["SLOW"][j, m].astype(float)))
        KZ[i, ok] = z[smap[ok]]
np.savez(f"{HERE}/data/f10v2_legs2.npz", KZ=KZ, Z24=L["Z24"], ZFD=L["ZFD"], WL=L["WL"], E_ts=d_ts)
print("legs2 exported", KZ.shape)
