"""MoE (Mixture-of-Experts) backbone — regime experts with learned routing.

Reference family: Switch Transformer (Fedus et al, 2021), GShard (Lepikhin
et al, 2020), more recently Soft-MoE (Puigcerver et al, 2024).

Why this is meaningfully different from FiLM
--------------------------------------------
FiLM (Phase 2, fold-0 rejected) modulated a *single shared* backbone via
γ,β scaling driven by 6 closed-form regime descriptors. One backbone has
to be good at all regimes — it gets pulled in conflicting directions.

MoE keeps multiple INDEPENDENT expert sub-networks. The router decides
which experts each sample uses. Different experts can specialise:
  - one for low-vol calm regimes
  - one for high-vol panic regimes
  - one for trend-following
  - one for mean-reverting

The router is light (a small MLP on regime descriptors), but the experts
collectively have more capacity than a single backbone would dare on this
sample size.

Top-K (default K=2) routing keeps inference cost per sample at K experts,
and the load is distributed across N experts during training (with a
load-balance loss to discourage degenerate "always pick expert 0" failures).

Architecture
------------
Input h: (B, L, D)
   ├── Each expert is a small inner backbone (default: lightweight EMA-pool)
   │   producing (B, D)
   └── Router: optional regime descriptor (B, R) OR mean-pool of h (B, D)
              → MLP → softmax over N experts → top-K weights
   Output: weighted sum of top-K expert outputs → (B, D)

Forward signature matches other backbones:
    forward(h, regime=None) where regime is optional (B, R) tensor.

If `regime` is None, the router uses h.mean(dim=1) as the routing input
(self-supervised regime detection from upstream features).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class _LightExpert(nn.Module):
    """Single-expert sub-backbone: causal-conv + EMA pool.

    Same shape as EMAPoolBackbone but without sharing weights with siblings.
    Kept small (~2K params) so N=4 experts fit in the param budget.
    """

    def __init__(self, d_model: int, dropout: float, decay: float):
        super().__init__()
        if not (0.0 < decay < 1.0):
            raise ValueError(f"decay must be in (0,1), got {decay}")
        self.decay = float(decay)
        # Single causal conv (lighter than EMAPoolBackbone's 3 layers, since we
        # have N copies of this module — total params still ≥ a single
        # full-fat backbone).
        self.conv = nn.Conv1d(d_model, d_model, kernel_size=3, padding=2, dilation=1)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # h: (B, L, D) -> (B, D, L) for Conv1d
        x = h.transpose(1, 2)
        x = self.conv(x)
        # Causal: drop the last 2 timesteps (padding=2 with kernel=3 produces
        # +2 future-leaking steps at the right edge).
        x = x[..., : h.size(1)]
        x = self.act(x)
        x = self.dropout(x)
        x = x.transpose(1, 2)  # (B, L, D)

        L = x.size(1)
        idx = torch.arange(L - 1, -1, -1, device=x.device, dtype=x.dtype)
        weights = (1.0 - self.decay) * (self.decay ** idx)
        weights = weights / weights.sum()
        return (x * weights.view(1, L, 1)).sum(dim=1)


class MoEBackbone(nn.Module):
    """Mixture-of-experts backbone with top-K routing.

    Parameters
    ----------
    d_model : int
        Channel dim of input/output.
    n_experts : int, default 4
    top_k : int, default 2
        Number of experts each sample uses.
    expert_decay : float, default 0.9
        EMA decay inside each expert. Different from EMAPoolBackbone default
        (0.95) — MoE experts specialise so we want shorter-memory experts
        to differ on local timescales.
    regime_dim : int, optional
        Dim of optional regime descriptor input. If None, router uses
        h.mean(dim=1) (a self-detected regime signal).
    router_hidden : int, default 32
    dropout : float, default 0.15
    load_balance_aux_weight : float, default 0.01
        Auxiliary loss weight to discourage routing collapse. The aux loss
        is exposed via `self.last_aux_loss` so the trainer can add it.
    """

    def __init__(
        self,
        d_model: int,
        n_experts: int = 4,
        top_k: int = 2,
        expert_decay: float = 0.9,
        regime_dim: int | None = None,
        router_hidden: int = 32,
        dropout: float = 0.15,
        load_balance_aux_weight: float = 0.01,
    ):
        super().__init__()
        if top_k > n_experts:
            raise ValueError(f"top_k={top_k} > n_experts={n_experts}")
        if top_k < 1:
            raise ValueError(f"top_k must be ≥ 1, got {top_k}")
        self.d_model = int(d_model)
        self.n_experts = int(n_experts)
        self.top_k = int(top_k)
        self.regime_dim = None if regime_dim is None else int(regime_dim)
        self.load_balance_aux_weight = float(load_balance_aux_weight)
        self.last_aux_loss: torch.Tensor = torch.zeros(())  # exposed for trainer

        # Experts (independent — the whole point of MoE)
        self.experts = nn.ModuleList(
            [_LightExpert(d_model, dropout, expert_decay) for _ in range(n_experts)]
        )

        router_in_dim = self.regime_dim if self.regime_dim is not None else d_model
        self.router = nn.Sequential(
            nn.Linear(router_in_dim, router_hidden),
            nn.GELU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(router_hidden, n_experts),
        )

        # Init router so initial routing is roughly uniform
        with torch.no_grad():
            nn.init.zeros_(self.router[-1].weight)
            nn.init.zeros_(self.router[-1].bias)

    def _compute_aux_loss(self, gate_probs: torch.Tensor, top_k_idx: torch.Tensor) -> torch.Tensor:
        """Switch-Transformer-style load balance loss.

        Encourages mean(P) · mean(f) to be uniform across experts:
            P_i = mean over batch of softmax probs to expert i
            f_i = fraction of batch routed to expert i (top-K mass)
        Loss = N_experts · sum_i (P_i · f_i)
        Minimum at uniform routing.
        """
        B = gate_probs.size(0)
        # f: fraction of routing mass on each expert (one-hot top-K, summed)
        one_hot = F.one_hot(top_k_idx, num_classes=self.n_experts).float()  # (B, K, N)
        f = one_hot.sum(dim=(0, 1)) / (B * self.top_k)  # (N,)
        # P: mean gate probability per expert
        p = gate_probs.mean(dim=0)  # (N,)
        return self.n_experts * (p * f).sum()

    def forward(
        self,
        h: torch.Tensor,
        regime: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        h : (B, L, D)
        regime : (B, regime_dim), optional
            Pre-computed regime descriptors. Required if model was constructed
            with regime_dim != None.

        Returns
        -------
        (B, D) — top-K-weighted sum of expert outputs.
        """
        B, L, D = h.shape
        if D != self.d_model:
            raise ValueError(f"d_model mismatch: got D={D}, expected {self.d_model}")

        # Routing input
        if self.regime_dim is None:
            route_in = h.mean(dim=1)  # (B, D)
        else:
            if regime is None:
                raise ValueError(
                    "MoEBackbone constructed with regime_dim but forward got regime=None"
                )
            if regime.size(-1) != self.regime_dim:
                raise ValueError(
                    f"regime dim mismatch: expected {self.regime_dim}, got {regime.size(-1)}"
                )
            route_in = regime.float()

        gate_logits = self.router(route_in)        # (B, n_experts)
        gate_probs = F.softmax(gate_logits, dim=-1)  # (B, n_experts)

        # Top-K routing — keep only the K highest-prob experts per sample.
        top_k_vals, top_k_idx = gate_probs.topk(self.top_k, dim=-1)  # (B, K)
        # Renormalise over the K kept experts so weights sum to 1.
        top_k_w = top_k_vals / (top_k_vals.sum(dim=-1, keepdim=True) + 1e-8)

        # Compute each expert's output for the full batch (cheap at this scale —
        # n_experts=4, B=512 → 4× the per-batch cost of a single backbone).
        # For larger n_experts we'd dispatch only routed samples to each expert.
        expert_outs = torch.stack([e(h) for e in self.experts], dim=1)  # (B, N, D)

        # Gather the K experts' outputs per sample, then weight + sum.
        idx_expand = top_k_idx.unsqueeze(-1).expand(-1, -1, D)            # (B, K, D)
        gathered = expert_outs.gather(dim=1, index=idx_expand)            # (B, K, D)
        out = (gathered * top_k_w.unsqueeze(-1)).sum(dim=1)               # (B, D)

        # Aux load-balance loss (set on self for trainer to add to total loss)
        if self.training:
            self.last_aux_loss = self.load_balance_aux_weight * self._compute_aux_loss(
                gate_probs, top_k_idx
            )
        else:
            self.last_aux_loss = torch.zeros((), device=h.device)

        return out
