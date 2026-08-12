"""ARM L — state-conditioned low-rank weight adaptation (LoRA) for the conformer FFN.

Mechanism (vs FiLM): FiLM can only RESCALE features (affine on activations). A
state-conditioned LoRA lets the 24-d regime state shift the FFN's FUNCTION (a
low-rank additive delta on the weight), which is what the strong/hard-month
trade-off demands. Rank-4, zero-init B => flag-on output is BIT-IDENTICAL to the
base at init; the state gate is per-sample (batch-invariant by construction).

Wiring (in DualLOBREGArch): wrap backbone.blocks[i].ffn2.fc1/fc2 with
StateLoRALinear; a small hypernet maps the frozen-normalised regime_prior to a
per-adapter rank-r gate, set on each adapter before the backbone runs.
"""
from __future__ import annotations
from typing import List, Optional
import torch
import torch.nn as nn


class StateLoRALinear(nn.Module):
    """Wrap an nn.Linear and add a state-gated rank-r low-rank weight delta.

    delta(x) = scale * B @ ( g ⊙ (A @ x) ),  g = per-sample state gate (rank,).
    B is zero-init => delta == 0 at init => forward output == base(x) exactly.
    The gate depends ONLY on the per-sample state (set via set_gate), so sample i's
    output depends only on (state_i, x_i) — batch-invariant.
    """

    def __init__(self, base: nn.Linear, rank: int = 4, scale: float = 1.0):
        super().__init__()
        assert isinstance(base, nn.Linear)
        self.base = base
        out_f, in_f = base.weight.shape
        self.in_f, self.out_f = int(in_f), int(out_f)
        self.rank = int(rank)
        self.scale = float(scale)
        self.A = nn.Parameter(torch.randn(self.rank, self.in_f) * (self.in_f ** -0.5))
        self.B = nn.Parameter(torch.zeros(self.out_f, self.rank))  # zero-init => identity
        self._gate: Optional[torch.Tensor] = None  # (Bsz, rank)

    def set_gate(self, g: Optional[torch.Tensor]) -> None:
        self._gate = g

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.base(x)
        g = self._gate
        if g is None:
            return out
        # x: (Bsz, ..., in_f) ; A: (rank, in_f) -> Ax: (Bsz, ..., rank)
        Ax = torch.einsum("ri,...i->...r", self.A, x)
        # broadcast per-sample gate (Bsz, rank) over any middle dims (e.g. L)
        while g.dim() < Ax.dim():
            g = g.unsqueeze(1)
        Ax = Ax * g
        delta = torch.einsum("or,...r->...o", self.B, Ax)  # (Bsz, ..., out_f)
        return out + self.scale * delta


class StateLoRAHypernet(nn.Module):
    """regime_prior (Bsz, state_dim) -> per-adapter rank-r gates (Bsz, n_adapters, rank).

    Small MLP. Last layer zero-weight + ones-bias => every gate == 1 at init, so the
    (zero-init-B) adapters start as pure identity but with a sensible learning scale.
    """

    def __init__(self, state_dim: int, n_adapters: int, rank: int, hidden: int = 16):
        super().__init__()
        self.n_adapters = int(n_adapters)
        self.rank = int(rank)
        self.fc1 = nn.Linear(int(state_dim), int(hidden))
        self.act = nn.SiLU()
        self.fc2 = nn.Linear(int(hidden), self.n_adapters * self.rank)
        nn.init.zeros_(self.fc2.weight)
        nn.init.ones_(self.fc2.bias)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        g = self.fc2(self.act(self.fc1(state)))
        return g.view(state.shape[0], self.n_adapters, self.rank)


def wrap_ffn_with_lora(backbone: nn.Module, rank: int = 4,
                       which: str = "ffn2") -> List[StateLoRALinear]:
    """Replace the fc1/fc2 Linears of the chosen FFN(s) in every conformer block
    with StateLoRALinear wrappers. Returns the adapters in a stable order (the
    hypernet emits one rank-r gate per adapter in this order)."""
    adapters: List[StateLoRALinear] = []
    blocks = getattr(backbone, "blocks", None)
    if blocks is None:
        raise ValueError("backbone has no .blocks (not a ConformerBackbone?)")
    ffn_names = ["ffn1", "ffn2"] if which == "both" else [which]
    for blk in blocks:
        for fn in ffn_names:
            ffn = getattr(blk, fn, None)
            if ffn is None:
                continue
            for lin_name in ("fc1", "fc2"):
                lin = getattr(ffn, lin_name, None)
                if isinstance(lin, nn.Linear):
                    ad = StateLoRALinear(lin, rank=rank)
                    setattr(ffn, lin_name, ad)
                    adapters.append(ad)
    return adapters
