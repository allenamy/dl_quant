import numpy as np, glob, torch
d = "multi_asset/exports/train/wideA_n1b_multirel_c1"
pr = np.load(d + "/panel_ref.npz", allow_pickle=True)
member = pr["member"].astype(bool); CL = pr["CL"].astype(bool); YR = pr["YR"].astype(float)
print("=== per test-row valid YR4B cross-section ===")
for f in sorted(glob.glob(d + "/fold_*_head_scores.npz")):
    z = np.load(f); te = z["te_rows"]
    cnt = np.array([(member[t] & CL[t] & np.isfinite(YR[t])).sum() for t in te])
    nz = (cnt >= 8).sum()
    print(f"{f.split('/')[-1]}: te={te.shape[0]} rows_ge8valid={nz} mean_valid_assets={cnt.mean():.1f} median={np.median(cnt):.0f}")

print("=== checkpoint multi-rel gate / alpha / lambda ===")
sd = torch.load(d + "/fold_0_model.pt", map_location="cpu")
if isinstance(sd, dict) and "model" in sd:
    sd = sd["model"]
keys = list(sd.keys())
print("total tensors:", len(keys))
hit = False
for k in keys:
    kl = k.lower()
    if any(s in kl for s in ["alpha", "lambda", "lam", "gate", "rel", "edge", "bucket", "scale", "beta", "tau", "temp"]):
        v = sd[k]
        if v.numel() <= 16:
            print(f"  {k} {tuple(v.shape)} vals={[round(x,5) for x in v.flatten().tolist()]}")
        else:
            print(f"  {k} {tuple(v.shape)} mean={v.float().mean().item():.5f} absmax={v.abs().max().item():.5f} std={v.float().std().item():.5f}")
        hit = True
if not hit:
    print("  no name match — dumping all small (<=16-elem) tensors:")
    for k in keys:
        v = sd[k]
        if v.numel() <= 16:
            print(f"  {k} {tuple(v.shape)} vals={[round(x,5) for x in v.flatten().tolist()]}")
