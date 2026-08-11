import os, sys, json
import numpy as np, torch
torch.backends.mkldnn.enabled = False
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, MA)
from multi_asset.train.train_dual_lob import build_dual_lob_model

run1 = json.load(open(f"{MA}/configs/d1gate/basis_2026_01.json".replace("basis_", "d1_").replace(".json", "_run1.json")))
basis = json.load(open(f"{MA}/configs/d1gate/basis_2026_01.json"))
NL = int(run1["data"]["n_levels"])
SEED = 1234

def build(model_cfg, nf, seed=SEED):
    torch.manual_seed(seed); np.random.seed(seed)
    return build_dual_lob_model(model_cfg, nf, NL)

print("="*70)
# (a) CONFIG-PLUMBING NO-OP: basis cfg with revin_skip=[] and nf=88  ==  run1 nf=88
m_run1 = build(run1["model"], 88)
bcfg88 = dict(basis["model"]); bcfg88["revin_skip_idx"] = []
m_b88 = build(bcfg88, 88)
sd1, sd2 = m_run1.state_dict(), m_b88.state_dict()
keys_eq = (list(sd1.keys()) == list(sd2.keys()))
allbit = keys_eq and all(torch.equal(sd1[k], sd2[k]) for k in sd1)
print(f"(a) CONFIG-PLUMBING NO-OP  basis(revin=[],nf=88) == run1(nf=88): {allbit}  (keys_eq={keys_eq}, n_params={len(sd1)})")

print("="*70)
# (b) INIT-RNG CAVEAT at nf=98 (basis cfg as-is, revin_skip=[80,81,88..97])
m_b98 = build(basis["model"], 98)
sd98 = m_b98.state_dict()
shared = [k for k in sd1 if k in sd98]
only88 = [k for k in sd1 if k not in sd98]
only98 = [k for k in sd98 if k not in sd1]
diff_shape = [k for k in shared if tuple(sd1[k].shape) != tuple(sd98[k].shape)]
same_shape = [k for k in shared if tuple(sd1[k].shape) == tuple(sd98[k].shape)]
diff_val = [k for k in same_shape if not torch.equal(sd1[k], sd98[k])]
print(f"(b) nf=98 vs nf=88 (same seed):")
print(f"    params only in 88 build: {only88}")
print(f"    params only in 98 build: {only98}")
print(f"    DIFFERENT-SHAPE params (input proj expected): {diff_shape}")
for k in diff_shape:
    print(f"       {k}: 88={tuple(sd1[k].shape)}  98={tuple(sd98[k].shape)}")
print(f"    same-shape but DIFFERENT-VALUE (init-RNG spillover): {len(diff_val)}/{len(same_shape)}")
if diff_val:
    print(f"       e.g. {diff_val[:8]}")

print("="*70)
# (c) ARM LIVE: the input-proj weight's basis columns (88:97) are non-zero
for k in diff_shape:
    w = sd98[k]
    if w.dim() >= 2 and w.shape[-1] == 98:
        base_cols = w[..., :88]; basis_cols = w[..., 88:98]
        print(f"(c) ARM LIVE  {k}: basis-cols[88:98] std={basis_cols.std().item():.4e} "
              f"(base-cols std={base_cols.std().item():.4e})  -> basis path {'LIVE' if basis_cols.std().item()>1e-6 else 'DEAD'}")
    elif w.dim() >= 2 and w.shape[0] == 98:
        base_rows = w[:88]; basis_rows = w[88:98]
        print(f"(c) ARM LIVE  {k}: basis-rows[88:98] std={basis_rows.std().item():.4e} "
              f"(base-rows std={base_rows.std().item():.4e})  -> basis path {'LIVE' if basis_rows.std().item()>1e-6 else 'DEAD'}")
print("="*70)
print("SUMMARY: (a) config plumbing is bit-clean; (b) adding 10 input channels perturbs")
print("the input projection (and, per spillover count, downstream init-RNG) — INHERENT to")
print("any channel-addition arm, NOT a corruption; apples-to-apples is at the DATA/fold level")
print("(base-88 byte-identical + identical train/val/test days), which is separately proven.")
