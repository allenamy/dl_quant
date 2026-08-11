import sys, json, numpy as np, torch
torch.backends.mkldnn.enabled = False
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, MA)
from multi_asset.train.train_dual_lob import build_dual_lob_model, _forward_dual
run1 = json.load(open(f"{MA}/configs/d1gate/d1_2026_01_run1.json"))
concat = json.load(open(f"{MA}/configs/arch_iter/concat_2026_01.json"))
NL = int(run1["data"]["n_levels"])
z = np.load(f"{MA}/data/npz_v2arch/2026-01-15.npz", allow_pickle=True); B=8
def t(x): return torch.tensor(np.asarray(x[:B]), dtype=torch.float32)
x_feat=t(z["X"]); x_raw=t(z["X_raw"]); x_perp=t(z["X_raw_perp_deep"]); rp=t(z["regime_prior"]); nf=x_feat.shape[-1]
def build(mcfg, seed=1234):
    torch.manual_seed(seed); np.random.seed(seed); return build_dual_lob_model(mcfg, nf, NL)
def q50(o): return (o["quantiles"][:,1] if isinstance(o,dict) else o).reshape(-1)
def fwd(m, xp):
    m.eval()
    with torch.no_grad(): return q50(_forward_dual(m, x_feat, x_raw, rp, xp))
m_run1 = build(run1["model"]); m_on = build(concat["model"])
print("use_perp_residual run1:", m_run1.use_perp_residual, "| use_perp_concat on:", m_on.use_perp_concat)
print("m_on has perp_fusion:", m_on.perp_fusion is not None, "| perp_alpha run1:", float(m_run1.perp_alpha))
print("x_perp shape:", tuple(x_perp.shape), "finite:", bool(torch.isfinite(x_perp).all()), "std:", float(x_perp.std()))
# is the perp path exercised? run1 with x_perp vs None:
r_wp, r_np = fwd(m_run1, x_perp), fwd(m_run1, None)
print("RUN1: forward(x_perp) differs from forward(None):", not torch.equal(r_wp, r_np), " maxΔ=", float((r_wp-r_np).abs().max()))
# concat-on with x_perp vs None:
o_wp, o_np = fwd(m_on, x_perp), fwd(m_on, None)
print("CONCAT-ON: forward(x_perp) differs from forward(None):", not torch.equal(o_wp, o_np), " maxΔ=", float((o_wp-o_np).abs().max()))
# concat-on vs run1 (both x_perp):
print("CONCAT-ON vs RUN1 (x_perp): differ:", not torch.equal(o_wp, r_wp), " maxΔ=", float((o_wp-r_wp).abs().max()))
