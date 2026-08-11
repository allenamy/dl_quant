"""Bit-identity + liveness tests for ARM CONCAT + ARM TAILW.
CONCAT: (A) OFF state_dict == Run1; (B) OFF forward == Run1 forward (bit-identical);
        (C) ON builds, forward finite, differs from OFF (live).
TAILW:  (D) build_tailw_loss_fn(run1_cfg) == _build_loss_fn_for_dul(run1_cfg) (bit-identical,
        same RNG); (E) ON differs from OFF + up-weights tail-sample gradient."""
import sys, json, numpy as np, torch
torch.backends.mkldnn.enabled = False
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, MA)
from multi_asset.train.train_dual_lob import build_dual_lob_model, _forward_dual
from src.training.trainer_v2 import _build_loss_fn_for_dul
from multi_asset.losses.tail_weighted_dul import build_tailw_loss_fn

run1 = json.load(open(f"{MA}/configs/d1gate/d1_2026_01_run1.json"))
concat = json.load(open(f"{MA}/configs/arch_iter/concat_2026_01.json"))
tailw = json.load(open(f"{MA}/configs/arch_iter/tailw_2026_01.json"))
NL = int(run1["data"]["n_levels"]); SEED = 1234

def build(mcfg, nf, seed=SEED):
    torch.manual_seed(seed); np.random.seed(seed)
    return build_dual_lob_model(mcfg, nf, NL)

# ---- real batch from a npz_v2arch day ----
z = np.load(f"{MA}/data/npz_v2arch/2026-01-15.npz", allow_pickle=True)
B = 8
def t(x): return torch.tensor(np.asarray(x[:B]), dtype=torch.float32)
x_feat = t(z["X"]); x_raw = t(z["X_raw"]) if "X_raw" in z.files else None
x_perp = t(z["X_raw_perp_deep"]) if "X_raw_perp_deep" in z.files else None
rp = t(z["regime_prior"]) if "regime_prior" in z.files else None
nf = x_feat.shape[-1]
print(f"batch: x_feat{tuple(x_feat.shape)} x_raw{None if x_raw is None else tuple(x_raw.shape)} "
      f"x_perp{None if x_perp is None else tuple(x_perp.shape)} rp{None if rp is None else tuple(rp.shape)} nf={nf}")

def fwd(model):
    model.eval()
    with torch.no_grad():
        return _forward_dual(model, x_feat, x_raw, rp, x_perp)

print("\n===== ARM CONCAT =====")
m_run1 = build(run1["model"], nf)
mcfg_off = dict(concat["model"]); mcfg_off["use_perp_concat"] = False
m_off = build(mcfg_off, nf)
m_on = build(concat["model"], nf)   # use_perp_concat=True

sd1, sdoff, sdon = m_run1.state_dict(), m_off.state_dict(), m_on.state_dict()
# (A) OFF state_dict == Run1
a_keys = (list(sd1.keys()) == list(sdoff.keys()))
a_bit = a_keys and all(torch.equal(sd1[k], sdoff[k]) for k in sd1)
print(f"(A) CONCAT-OFF state_dict == Run1: {a_bit}  (n_params run1={len(sd1)} off={len(sdoff)})")
# ON has the extra perp_fusion params
extra = [k for k in sdon if k not in sd1]
print(f"    CONCAT-ON extra params vs Run1: {extra}")
# (B) OFF forward == Run1 forward
o1, ooff, oon = fwd(m_run1), fwd(m_off), fwd(m_on)
def q50(o): return (o["quantiles"][:, 1] if isinstance(o, dict) else o).reshape(-1)
b_bit = torch.equal(q50(o1), q50(ooff))
print(f"(B) CONCAT-OFF forward == Run1 forward (bit-identical): {b_bit}")
# (C) ON live
on_fin = bool(torch.isfinite(q50(oon)).all()); on_diff = not torch.equal(q50(oon), q50(ooff))
print(f"(C) CONCAT-ON forward finite={on_fin} & differs from OFF={on_diff} -> {'LIVE' if on_fin and on_diff else 'DEAD'}")

print("\n===== ARM TAILW =====")
dul_run1 = run1["training"]["dul_config"]
dul_tw = tailw["training"]["dul_config"]
# fabricate an outputs dict + target (single-horizon: quantiles (N,3), point_pred (N,))
torch.manual_seed(0)
N = 512
qk = torch.randn(N, 3).cumsum(dim=1) * 0.1   # monotone-ish quantiles
qk.requires_grad_(True)
outs = {"quantiles": qk, "point_pred": qk[:, 1], "sign_logit": torch.randn(N)}
y = torch.randn(N) * 1.5
def loss_of(fn, seed=7):
    torch.manual_seed(seed)
    return fn(outs, y)
# (D) OFF bit-identity: build_tailw_loss_fn(run1) == _build_loss_fn_for_dul(run1)
lf_src = _build_loss_fn_for_dul(dul_run1)
lf_tw_off = build_tailw_loss_fn(dul_run1)          # use_tail_weight absent -> passthrough
d_bit = torch.equal(loss_of(lf_src), loss_of(lf_tw_off))
print(f"(D) TAILW-OFF loss == src loss (bit-identical, same RNG): {d_bit}  "
      f"(src={float(loss_of(lf_src)):.6f})")
# also: tailw config with use_tail_weight forced False
dul_tw_off = dict(dul_tw); dul_tw_off["use_tail_weight"] = False
d_bit2 = torch.equal(loss_of(lf_src), loss_of(build_tailw_loss_fn(dul_tw_off)))
print(f"    TAILW cfg w/ use_tail_weight=False == src: {d_bit2}")
# (E) ON live + up-weights tail
lf_on = build_tailw_loss_fn(dul_tw)                # use_tail_weight=True
l_off, l_on = loss_of(lf_tw_off), loss_of(lf_on)
e_diff = not torch.equal(l_off, l_on)
# tail-emphasis check: gradient magnitude on tail samples should be relatively higher under ON
qk.grad = None; loss_of(lf_on).backward()
g_on = qk.grad[:, 1].abs().detach()
qk.grad = None; loss_of(lf_tw_off).backward()
g_off = qk.grad[:, 1].abs().detach()
tail = y.abs() > y.abs().median()
ratio_on = float(g_on[tail].mean() / (g_on[~tail].mean() + 1e-9))
ratio_off = float(g_off[tail].mean() / (g_off[~tail].mean() + 1e-9))
e_tail = ratio_on > ratio_off
print(f"(E) TAILW-ON differs from OFF={e_diff} (off={float(l_off):.5f} on={float(l_on):.5f}); "
      f"tail/body grad-ratio ON={ratio_on:.3f} > OFF={ratio_off:.3f} = {e_tail} -> "
      f"{'LIVE+TAIL-EMPHASIS' if e_diff and e_tail else 'CHECK'}")

allok = a_bit and b_bit and on_fin and on_diff and d_bit and d_bit2 and e_diff and e_tail
print(f"\nARCH_ITER TESTS: {'ALL PASS' if allok else 'REVIEW'}")
