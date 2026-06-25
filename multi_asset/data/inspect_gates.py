import os; os.environ["CUDA_VISIBLE_DEVICES"]=""
import torch; torch.backends.mkldnn.enabled=False
import json, glob, numpy as np
from multi_asset.model.dual_lob_v2arch import DualLOBV2Arch
import sys
ckpt_dir=sys.argv[1] if len(sys.argv)>1 else "experiments/npzv4_dual/rgated_2025_04/fold_0"
cfg_path=sys.argv[2] if len(sys.argv)>2 else "configs/npzv4_dual/rgated_2025_04.json"
cfg=json.load(open(cfg_path)); m=cfg["model"]
base={k:v for k,v in m.items() if not k.startswith("_")}
nfeat=cfg.get("data",{}).get("slice",{}).get("x_channels",72)
mdl=DualLOBV2Arch(n_features=nfeat, n_levels=20, **base)
print("n_features=",nfeat)
ck=torch.load(f"{ckpt_dir}/best_model.pt", map_location="cpu", weights_only=False)
mdl.load_state_dict(ck["state"] if isinstance(ck,dict) and "state" in ck else ck); mdl.eval()
# pull real regime_prior from a STRONG month + a WEAK month, run the gates
def regime_priors(mon, cache="npzv4_dual"):
    fs=sorted(glob.glob(f"data/{cache}/*.npz")); days=[f for f in fs if f.split("/")[-1][:7]==mon][:3]
    rps=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m_=d["y_mask_600"].astype(bool)
        rps.append(d["regime_prior"][m_])
    return np.nan_to_num(np.concatenate(rps)).astype(np.float32)
def gate_vals(rp):
    rp=torch.from_numpy(rp)
    with torch.no_grad():
        g_mh = torch.sigmoid(mdl.mh_gate(rp)).mean().item() if hasattr(mdl,"mh_gate") and mdl.mh_gate is not None else None
        moe = getattr(mdl,"regime_moe",None)
        g_moe = torch.sigmoid(moe.moe_gate(rp)).mean().item() if (moe is not None and hasattr(moe,"moe_gate")) else None
    return g_mh, g_moe
for mon,lab in [("2025-04","STRONG"),("2025-08","weak-normal"),("2025-02","strong-ish"),("2025-06","mid")]:
    try:
        rp=regime_priors(mon); g_mh,g_moe=gate_vals(rp)
        print(f"  {lab:12s} {mon}: g_mh={g_mh:.3f}  g_moe={g_moe:.3f}  (n={len(rp)})")
    except Exception as e: print(f"  {mon}: {e}")
print("MECHANISM: g_mh HIGH in strong + LOW in weak; g_moe HIGH in weak + LOW in strong => learned mapping.")
print("           both ~0.5 across regimes => COSMETIC (no learned mapping).")
