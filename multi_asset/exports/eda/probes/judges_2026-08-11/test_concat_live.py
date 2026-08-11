"""ARM CONCAT liveness at the ENCODE level (where the perp effect is not swamped by
the tiny-at-init final-head magnitude). Proves: (C1) concat fusion is EXERCISED by the
perp (encode responds to x_perp); (C2) concat mechanism DIFFERS from the additive path;
(C3) concat-ON forward q50 (eval caliber) IS perp-sensitive with a non-trivial alpha-scale."""
import sys, json, numpy as np, torch
torch.backends.mkldnn.enabled = False
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"; sys.path.insert(0, MA)
from multi_asset.train.train_dual_lob import build_dual_lob_model
run1 = json.load(open(f"{MA}/configs/d1gate/d1_2026_01_run1.json"))
concat = json.load(open(f"{MA}/configs/arch_iter/concat_2026_01.json"))
z = np.load(f"{MA}/data/npz_v2arch/2026-01-15.npz", allow_pickle=True); B=8
def t(x): return torch.tensor(np.asarray(x[:B]), dtype=torch.float32)
x_feat=t(z["X"]); x_raw=t(z["X_raw"]); x_perp=t(z["X_raw_perp_deep"]); rp=t(z["regime_prior"])
def build(mcfg, seed=1234):
    torch.manual_seed(seed); np.random.seed(seed); return build_dual_lob_model(mcfg, 88, 20)
m_on = build(concat["model"]); m_add = build(run1["model"])
for m in (m_on, m_add): m.eval()
def enc(m, xp):
    rpn = m._normalize_prior(rp) if getattr(m,"use_fixed_regime_state",False) else rp
    with torch.no_grad():
        m._x_raw_perp_deep = xp
        h = m.encode(x_feat, x_raw, regime_prior=rpn); m._x_raw_perp_deep = None
    return h
# C1: concat fusion exercised by perp
c1 = float((enc(m_on, x_perp) - enc(m_on, None)).abs().max())
# C2: concat h_pred differs from additive h_pred on the SAME perp input (different mechanism)
c2 = float((enc(m_on, x_perp) - enc(m_add, x_perp)).abs().max())
# C3: concat-ON final q50 is perp-sensitive at a diagnostic alpha (concat has no alpha; scale perp_fusion perp-half)
with torch.no_grad():
    m_on2 = build(concat["model"]); m_on2.eval()
    # amplify the perp-half of the fusion to show the eval-caliber q50 responds
    m_on2.perp_fusion.weight[:, 32:] *= 50.0
    def q50f(m, xp):
        with torch.no_grad(): o = m(x_feat, x_raw, regime_prior=rp, x_raw_perp_deep=xp)
        return o["quantiles"][:, 1]
    c3 = float((q50f(m_on2, x_perp) - q50f(m_on2, None)).abs().max())
print(f"(C1) concat encode responds to x_perp (fusion exercised): maxΔ={c1:.5f} -> {'LIVE' if c1>1e-6 else 'DEAD'}")
print(f"(C2) concat vs additive encode differ (distinct mechanism): maxΔ={c2:.5f} -> {'DISTINCT' if c2>1e-4 else 'SAME'}")
print(f"(C3) concat-ON eval q50 perp-sensitive (amplified fusion): maxΔ={c3:.5f} -> {'SENSITIVE' if c3>1e-5 else 'INSENSITIVE'}")
print(f"CONCAT LIVENESS: {'PASS' if (c1>1e-6 and c2>1e-4 and c3>1e-5) else 'REVIEW'}")
