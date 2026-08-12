"""Cross-correlation off-diagonal mean-penalty for embeddings.

Inspired by Barlow Twins (Zbontar et al. 2021). Given a batch of d-dim
embeddings, compute the d×d cross-correlation matrix and penalize the mean
squared off-diagonal entry to reduce redundancy between feature channels.

L = (1 / (d·(d-1))) · Σ_{i≠j} C_ij²

Deviation from Zbontar 2021: they used the raw sum; we normalize by the
number of off-diagonal entries so the loss magnitude is invariant to
embedding dimension d. This keeps the composite-loss weight α_decorr
meaningful across V5-LH ablations where d_model may vary.
"""
import torch


def decorrelation_loss(embeddings: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """
    Parameters
    ----------
    embeddings : (N, d) batch of embeddings.
    eps : numerical stability for standardization.
    """
    N, d = embeddings.shape
    # Standardize per dim
    e = embeddings - embeddings.mean(dim=0, keepdim=True)
    # unbiased=False (denominator N) matches the (e.T @ e) / N covariance
    # convention below, ensuring C_ii = 1 exactly given sufficient samples.
    e = e / (e.std(dim=0, keepdim=True, unbiased=False) + eps)
    # Cross-correlation matrix
    C = (e.T @ e) / N  # (d, d)
    off_diag = C - torch.diag(torch.diag(C))
    # Normalize by number of off-diagonal entries so the loss is scale-invariant
    # w.r.t. embedding dimension d.  For IID inputs this equals ~1/N per channel
    # pair; for perfectly correlated inputs it approaches 1.0.
    n_off_diag = d * (d - 1)
    return (off_diag ** 2).sum() / n_off_diag
