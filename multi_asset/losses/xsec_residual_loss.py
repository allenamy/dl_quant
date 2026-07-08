"""Cross-sectional RESIDUAL loss for the multi-asset y_600 long-short model.

Design (from the 2026 loss-research synthesis, grounded in HRT + our data):
- TARGET = cross-sectional residual r = y - mean_j(y_j) (equal-weight demean removes
  the ~70% common factor; the predictable alpha is the residual). Per-asset MAD-norm +
  clip happens in the dataset; this module operates on the prepared residual target.
- LOSS per horizon = 0.30*Huber(q50,r) + 0.70*LambdaRankIC(q50,r) + 0.10*Pinball(q,r).
  * Huber  — residual magnitude calibration (sizing/threshold) + dense anti-σ-collapse gradient.
  * LambdaRankIC (Lin 2026) — rank term that is RANK-INVARIANT (robust to crypto fat tails),
    validated in low-SNR + Student-t sims, and an UPPER BOUND on (1 - Spearman rank-IC),
    i.e. it directly minimises our headline trade metric. Replaces Pearson-IC (the safe
    fallback, also provided). Weight (rank vs rank-grad) uses DETACHED ranks (LambdaLoss
    convention) so gradient flows only through the pairwise logistic.
  * Pinball (q10/q50/q90) — fat-tail-robust conviction-σ for position sizing.
- Both Huber and the rank term see the SAME residual target -> their gradients are
  co-linear (no rank-vs-magnitude conflict; no gradient surgery needed).

All terms are masked over valid (timestep, asset) entries and meaned over valid timesteps.
S<=14 so the O(S^2) pairwise op is trivial.
"""
from __future__ import annotations

import math

import torch
import torch.nn.functional as F

_LOG2 = math.log(2.0)


def cross_sectional_residual(y, mask):
    """y,mask: (B,S). Return residual r = y - cross-sectional mean over VALID assets,
    zeroed where invalid. Equal-weight demean (betas~1 -> mean ~ PC1 score)."""
    valid = (mask > 0.5) & torch.isfinite(y)
    v = valid.to(y.dtype)
    cnt = v.sum(dim=1, keepdim=True).clamp(min=1.0)
    ysafe = torch.where(valid, y, torch.zeros_like(y))
    mean = ysafe.sum(dim=1, keepdim=True) / cnt
    r = torch.where(valid, y - mean, torch.zeros_like(y))
    return r, valid


def _hard_rank(x, valid):
    """Average ranks (1..n) of x over the VALID entries per row; invalid -> 0. Detached.
    x,valid: (B,S). Returns float ranks (B,S). Ties get distinct ranks (argsort order);
    fine for the LambdaLoss weight which only needs |rank gaps|."""
    with torch.no_grad():
        neg = ~valid
        xs = x.masked_fill(neg, float("inf"))          # invalid sorted to the end
        order = xs.argsort(dim=1)                       # ascending
        ranks = torch.zeros_like(x)
        ar = torch.arange(1, x.shape[1] + 1, device=x.device, dtype=x.dtype)
        ranks.scatter_(1, order, ar.unsqueeze(0).expand_as(x))
        ranks = torch.where(valid, ranks, torch.zeros_like(ranks))
    return ranks


def lambda_rank_ic(s, target, valid, sigma=1.0):
    """LambdaRankIC loss (Lin 2026). s,target,valid: (B,S). Per cross-section, over ordered
    pairs (i,j) with target_i > target_j:
        w_ij = 12*|rhat_j-rhat_i|*|rtil_i-rtil_j| / (n*(n^2-1))   [detached]
        l_ij = w_ij * log2(1 + exp(-sigma*(s_i - s_j)))
    Mean over valid timesteps. Upper-bounds (1 - Spearman)."""
    B, S = s.shape
    v = valid.to(s.dtype)
    n = v.sum(dim=1)                                    # (B,)
    ok = n >= 2.0
    if not ok.any():
        return s.new_zeros(())
    rhat = _hard_rank(s, valid)                         # detached ranks of preds
    rtil = _hard_rank(target, valid)                    # detached ranks of target
    # pairwise (B,S,S): index i = dim1, j = dim2
    ti = target.unsqueeze(2); tj = target.unsqueeze(1)
    vij = (valid.unsqueeze(2) & valid.unsqueeze(1)).to(s.dtype)
    pair = (ti > tj).to(s.dtype) * vij                  # ordered pairs target_i>target_j
    rh_i = rhat.unsqueeze(2); rh_j = rhat.unsqueeze(1)
    rt_i = rtil.unsqueeze(2); rt_j = rtil.unsqueeze(1)
    denom = (n * (n * n - 1.0)).clamp(min=1.0).view(B, 1, 1)
    w = 12.0 * (rh_j - rh_i).abs() * (rt_i - rt_j).abs() / denom    # detached weight
    si = s.unsqueeze(2); sj = s.unsqueeze(1)
    # log2(1+exp(-sigma*(si-sj))) = softplus(-sigma*(si-sj))/ln2
    logistic = F.softplus(-sigma * (si - sj)) / _LOG2
    # NORMALISE by the per-cross-section weight-sum -> weighted-average logistic, O(1)
    # scale (so the 0.30/0.70 magnitude/rank weighting is meaningful + scale-stable
    # across n; raw LambdaLoss sum is ~10x Huber and would swamp the magnitude head).
    wp = w * pair
    num = (wp * logistic).sum(dim=(1, 2))               # (B,)
    den = wp.sum(dim=(1, 2)).clamp(min=1e-6)            # (B,)
    l = (num / den) * ok.to(s.dtype)
    return l.sum() / ok.to(s.dtype).sum().clamp(min=1.0)


def pearson_ic_loss(s, target, valid, eps=1e-6):
    """Safe-fallback cross-sectional Pearson-IC loss: mean over t of (1 - corr(s,target))
    across valid assets. Separate σ clamps guard variance collapse."""
    v = valid.to(s.dtype)
    cnt = v.sum(dim=1)
    ok = cnt >= 2.0
    if not ok.any():
        return s.new_zeros(())
    ssafe = torch.where(valid, s, torch.zeros_like(s))
    tsafe = torch.where(valid, target, torch.zeros_like(target))
    c = cnt.clamp(min=1.0).unsqueeze(1)
    ms = ssafe.sum(1, keepdim=True) / c
    mt = tsafe.sum(1, keepdim=True) / c
    sc = torch.where(valid, s - ms, torch.zeros_like(s))
    tc = torch.where(valid, target - mt, torch.zeros_like(target))
    num = (sc * tc).sum(1)
    ds = torch.sqrt((sc * sc).sum(1).clamp(min=eps))
    dt = torch.sqrt((tc * tc).sum(1).clamp(min=eps))
    ic = num / (ds * dt)
    l = (1.0 - ic) * ok.to(s.dtype)
    return l.sum() / ok.to(s.dtype).sum().clamp(min=1.0)


def masked_huber(s, target, valid, delta=2.0):
    if not valid.any():
        return s.new_zeros(())
    diff = (s - target)[valid]
    a = diff.abs()
    quad = torch.minimum(a, a.new_full((), delta))
    lin = a - quad
    return (0.5 * quad * quad + delta * lin).mean()


def masked_pinball(quantiles, target, valid, taus=(0.1, 0.5, 0.9)):
    """quantiles: (B,S,Q); target,valid: (B,S)."""
    if not valid.any():
        return quantiles.new_zeros(())
    t = target.unsqueeze(-1)
    err = t - quantiles
    tau = quantiles.new_tensor(taus)
    pin = torch.maximum(tau * err, (tau - 1.0) * err).mean(dim=-1)   # (B,S)
    return pin[valid].mean()


def residual_loss(quantiles, target_resid, mask, q50_idx=1, sigma=1.0,
                  w_huber=0.30, w_rank=0.70, w_pin=0.10, rank_kind="lambda",
                  delta=2.0):
    """Full per-horizon residual loss. quantiles: (B,S,Q) (q10,q50,q90); target_resid,mask:
    (B,S). Returns (total, parts_dict). target_resid is the PREPARED residual (demeaned,
    MAD-normed, clipped) from the dataset."""
    valid = (mask > 0.5) & torch.isfinite(target_resid)
    s = quantiles[..., q50_idx]
    lh = masked_huber(s, target_resid, valid, delta=delta)
    if rank_kind == "lambda":
        lr = lambda_rank_ic(s, target_resid, valid, sigma=sigma)
    else:
        lr = pearson_ic_loss(s, target_resid, valid)
    lp = masked_pinball(quantiles, target_resid, valid)
    total = w_huber * lh + w_rank * lr + w_pin * lp
    return total, {"huber": float(lh.detach()), "rank": float(lr.detach()),
                   "pin": float(lp.detach())}


def orthogonality_penalty(scores, funding, valid):
    """STAGE-2B: penalize (a) pairwise cross-sectional corr among the K factor heads and
    (b) each head's corr vs funding_ema — so the heads mine mutually-different structure that
    funding doesn't already have. scores (B,S,K), funding (B,S), valid (B,S) {0,1}. Per-timestamp
    cross-sectional correlations, meaned over valid timesteps."""
    B, S, K = scores.shape
    m = valid.float().unsqueeze(-1)                                   # (B,S,1)
    cnt = m.sum(1, keepdim=True).clamp_min(1.0)                       # (B,1,1)
    scz = (scores - (scores * m).sum(1, keepdim=True) / cnt) * m      # demeaned, masked (B,S,K)
    u = scz / torch.sqrt((scz ** 2).sum(1, keepdim=True).clamp_min(1e-8))   # unit per head (B,S,K)
    gram = torch.einsum("bsk,bsl->bkl", u, u)                         # (B,K,K) xsec corr among heads
    eye = torch.eye(K, device=scores.device).unsqueeze(0)
    pair = (gram - eye).abs().sum((1, 2)) / max(K * (K - 1), 1)       # mean |off-diag| per B
    fz = (funding - (funding * valid.float()).sum(1, keepdim=True) /
          valid.float().sum(1, keepdim=True).clamp_min(1.0)) * valid.float()
    uf = (fz / torch.sqrt((fz ** 2).sum(1, keepdim=True).clamp_min(1e-8))).unsqueeze(-1)  # (B,S,1)
    fund = (u * uf).sum(1).abs().mean(1)                              # (B,) mean_k |corr(head_k, funding)|
    ok = (cnt.squeeze(-1).squeeze(-1) >= 5).float()
    pen = (pair + fund) * ok
    return pen.sum() / ok.sum().clamp_min(1.0)


def stage2b_loss(scores, target_resid, funding, valid, w_mag=0.3, lam_orth=1.0):
    """K orthogonal factor heads: LambdaRankIC (primary, per head, on the funding-residual target)
    + magnitude Huber (sizing/anti-collapse) + orthogonality penalty (pairwise + vs funding)."""
    valid = valid > 0.5                        # lambda_rank_ic needs a boolean mask (~valid)
    K = scores.shape[-1]
    lr = torch.stack([lambda_rank_ic(scores[..., k], target_resid, valid) for k in range(K)]).mean()
    lm = torch.stack([masked_huber(scores[..., k], target_resid, valid) for k in range(K)]).mean()
    lo = orthogonality_penalty(scores, funding, valid)
    total = lr + w_mag * lm + lam_orth * lo
    return total, {"rank": float(lr.detach()), "mag": float(lm.detach()), "orth": float(lo.detach())}
