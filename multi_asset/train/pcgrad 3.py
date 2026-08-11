"""ARM P — PCGrad gradient surgery for the raw-primary + demeaned-aux multi-horizon
setup (revives the ALIGN lever without the trunk damage plain-aux caused).

Plain 0.3-aux summed its gradient into the shared trunk; where the demeaned-aux
gradient CONFLICTS with the raw-primary gradient (negative cosine), it drags the
primary down (the strong-month contamination we measured on aux_2025_10). PCGrad:
project the conflicting aux gradient onto the primary gradient's NULL SPACE before
combining, so the aux can only help (or be neutral), never fight the primary.

Self-contained: computes the per-horizon losses (same masked slices as
src.training._multi_horizon_loss, replicated so src/ stays untouched), does the
per-task backward, projects, and writes the combined .grad. Caller then clips +
steps as usual. horizon layout: aux horizons first, primary LAST (== primary_idx).
"""
from __future__ import annotations
from typing import Callable, Dict, List, Optional
import torch


def _per_horizon_losses(outputs: Dict[str, torch.Tensor], y, mask, loss_fn,
                        horizon_weights) -> tuple:
    """Return (losses, weights, hidx) with one entry per contributing horizon,
    matching _multi_horizon_loss's masked-slice semantics exactly."""
    q_by_h = outputs["quantiles_by_horizon"]   # (B, n_h, Q)
    p_by_h = outputs["point_pred_by_horizon"]  # (B, n_h)
    n_h = q_by_h.shape[1]
    losses: List[torch.Tensor] = []
    weights: List[float] = []
    hidx: List[int] = []
    for h in range(n_h):
        idx = mask[:, h].nonzero(as_tuple=True)[0]
        if idx.numel() == 0:
            continue
        m_out = {"quantiles": q_by_h[idx, h, :], "point_pred": p_by_h[idx, h]}
        losses.append(loss_fn(m_out, y[idx, h]))
        weights.append(1.0 if horizon_weights is None else float(horizon_weights[h]))
        hidx.append(h)
    return losses, weights, hidx


def pcgrad_multi_horizon_backward(model, optimizer, outputs, y, mask, loss_fn,
                                  horizon_weights, primary_idx) -> Optional[float]:
    """Per-task backward with PCGrad projection of aux tasks onto the primary's
    null space (on conflict). Writes the weighted-combined gradient into p.grad and
    returns a scalar proxy loss for logging, or None if no horizon contributed."""
    losses, weights, hidx = _per_horizon_losses(outputs, y, mask, loss_fn, horizon_weights)
    if not losses:
        return None
    params = [p for p in model.parameters() if p.requires_grad]

    # If only one horizon contributed this batch, no surgery possible -> plain path.
    if len(losses) == 1:
        optimizer.zero_grad(set_to_none=True)
        (weights[0] * losses[0]).backward()
        return float(losses[0].item())

    # Per-task gradients (retain graph until the last task).
    task_flat: List[torch.Tensor] = []
    for i, loss in enumerate(losses):
        optimizer.zero_grad(set_to_none=True)
        loss.backward(retain_graph=(i < len(losses) - 1))
        flat = torch.cat([(p.grad.detach().reshape(-1) if p.grad is not None
                           else torch.zeros(p.numel(), device=p.device, dtype=p.dtype))
                          for p in params])
        task_flat.append(flat)

    # Identify the primary (== the contributing horizon whose h == primary_idx; else
    # the last contributing one, which is the highest horizon = primary by convention).
    p_pos = hidx.index(primary_idx) if primary_idx in hidx else len(losses) - 1
    g_primary = task_flat[p_pos]
    pp = g_primary.dot(g_primary) + 1e-12

    combined = torch.zeros_like(g_primary)
    wsum = 0.0
    for i, gi in enumerate(task_flat):
        if i != p_pos:
            dot = gi.dot(g_primary)
            if dot < 0:                       # conflict -> project onto primary null space
                gi = gi - (dot / pp) * g_primary
        combined = combined + weights[i] * gi
        wsum += weights[i]
    combined = combined / max(wsum, 1e-12)

    # Write combined gradient back into p.grad.
    optimizer.zero_grad(set_to_none=True)
    off = 0
    for p in params:
        k = p.numel()
        p.grad = combined[off:off + k].view_as(p).clone()
        off += k

    # proxy loss = the same weighted-mean scalar _multi_horizon_loss would report.
    wt = torch.tensor(weights, dtype=losses[0].dtype, device=losses[0].device)
    return float((torch.stack([l.detach() for l in losses]) * wt).sum().item() / float(wt.sum().item()))
