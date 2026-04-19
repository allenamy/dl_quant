"""Cross-correlation off-diagonal penalty for embeddings.

Inspired by Barlow Twins (Zbontar et al. 2021). Given a batch of d-dim
embeddings, compute the d×d cross-correlation matrix and penalize off-diagonal
entries to reduce redundancy between feature channels.

L = λ · Σ_{i≠j} C_ij²
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
    e = e / (e.std(dim=0, keepdim=True) + eps)
    # Cross-correlation matrix
    C = (e.T @ e) / N  # (d, d)
    off_diag = C - torch.diag(torch.diag(C))
    # Normalize by number of off-diagonal entries so the loss is scale-invariant
    # w.r.t. embedding dimension d.  For IID inputs this equals ~1/N per channel
    # pair; for perfectly correlated inputs it approaches 1.0.
    n_off_diag = d * (d - 1)
    return (off_diag ** 2).sum() / n_off_diag
