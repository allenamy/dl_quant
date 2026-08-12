import torch
from src.losses.decorrelation_loss import decorrelation_loss


def test_orthogonal_embeddings_zero_loss():
    """Independent unit-variance features have near-zero decorrelation loss.

    Loss is normalized by d*(d-1), so for IID inputs it scales as 1/N ≈ 0.002
    for N=500.  Threshold 0.05 gives >20× margin.
    """
    torch.manual_seed(42)
    d = 8; n = 500
    x = torch.randn(n, d)  # IID -> off-diag corr ≈ 0
    loss = decorrelation_loss(x)
    assert loss.item() < 0.05


def test_highly_correlated_embeddings_high_loss():
    """All identical features have decorrelation loss close to 1.0.

    Four identical columns -> all pairwise correlations = 1 -> mean off-diagonal
    C_ij^2 ≈ 1.  Threshold 0.9 accommodates tiny eps-induced deflation.
    """
    x = torch.randn(200, 1).repeat(1, 4)  # 4 identical features
    loss = decorrelation_loss(x)
    assert loss.item() > 0.9


def test_gradient_flows():
    x = torch.randn(100, 6, requires_grad=True)
    loss = decorrelation_loss(x)
    loss.backward()
    assert x.grad is not None
