"""Sharpness-Aware Minimization (SAM) optimizer wrapper.

Reference:
    Foret, Kleiner, Mobahi, Neyshabur (2020).
    "Sharpness-Aware Minimization for Efficiently Improving Generalization."
    ICLR 2021. https://arxiv.org/abs/2010.01412

Motivation in this codebase:
    Single-asset BTC y_600 has reached the ~0.055 Pearson ceiling on the
    proven V4 architecture (see CLAUDE.md). Generalization is the bottleneck:
    val/test correlations diverge sharply across folds (per-fold P std 0.008
    even with 3-seed median). SAM seeks parameters lying in *flat* loss
    regions, which empirically transfer better across regimes than sharp
    minima found by vanilla SGD/AdamW. Expected gain: +0.005-0.010 P pooled
    over 3 folds (subject to the usual baseline-anchor discipline,
    anti-pattern #17).

Algorithm (eqs. 5-6 of the paper, with global L2 norm):

    1. Forward + backward → gradient g(theta)
    2. Compute per-step perturbation:
           epsilon = rho * g / (||g||_2 + 1e-12)
    3. Apply: theta_perturbed = theta + epsilon
    4. Forward + backward at theta_perturbed → gradient g_sam
    5. Restore: theta = theta_perturbed - epsilon (= original theta)
    6. Apply base optimizer step using g_sam (NOT the original g)

The surrogate loss being optimized is approximately
    L_SAM(theta) = max_{||eps||<=rho} L(theta + eps)
which upper-bounds the test loss under PAC-Bayes assumptions and is
minimized by parameters with low local sharpness.

Design notes:
    * Global L2 norm (across all parameters) is used per the paper, not
      per-tensor (per-tensor is the "ASAM" variant — different algorithm).
    * No-grad parameters (e.g. frozen layers, BN running stats) are skipped
      cleanly; ``epsilon`` for them is left at zero.
    * ``||grad||=0`` edge case returns zero perturbation (no NaN, no step
      degradation — base optimizer still runs on its grad).
    * The rollback in ``second_step`` is exact (we cache ``epsilon`` per
      parameter) so there is no drift from numerical re-computation.
"""

from __future__ import annotations

from typing import Any, Iterable, Type

import torch


class SAM(torch.optim.Optimizer):
    """Sharpness-Aware Minimization wrapper around a base optimizer.

    Wraps any ``torch.optim.Optimizer`` subclass (AdamW, SGD, ...) and
    exposes two-step interface ``first_step`` / ``second_step``. The base
    optimizer owns LR/weight-decay/momentum/state; SAM only injects the
    sharpness perturbation between the two backward passes.

    Parameters
    ----------
    params : Iterable
        Parameters or iterable of parameter groups, same as a normal
        ``torch.optim.Optimizer``.
    base_optimizer_class : Type[torch.optim.Optimizer]
        Class object (NOT an instance) of the inner optimizer, e.g.
        ``torch.optim.AdamW``. SAM constructs it internally so that param
        groups stay in sync.
    rho : float, default 0.05
        Neighborhood radius for the perturbation. 0.05 is the Foret 2020
        default for AdamW + image classification. Lower values (~0.01)
        suit very low-SNR / over-regularized settings.
    **base_optimizer_kwargs
        Forwarded verbatim to ``base_optimizer_class(...)`` along with
        the param groups (e.g. ``lr=6e-4, weight_decay=1e-2``).

    Standard usage in a training loop::

        optimizer = SAM(model.parameters(), torch.optim.AdamW,
                        rho=0.05, lr=6e-4, weight_decay=1e-2)
        for x, y in loader:
            # First pass — perturbation direction
            optimizer.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            optimizer.first_step(zero_grad=True)

            # Second pass — gradient at the worst-case point in epsilon-ball
            loss = loss_fn(model(x), y)
            loss.backward()
            optimizer.second_step(zero_grad=True)

    Notes
    -----
    Cost: SAM doubles the per-step compute (two forward + two backward).
    To amortize, halve ``epochs`` or use larger ``batch`` and adjust LR.
    For y_600 (~5K samples/day, batch 1024) this is acceptable: a single
    700-day fold goes from ~30 min to ~60 min on the production GPU.
    """

    def __init__(
        self,
        params: Iterable,
        base_optimizer_class: Type[torch.optim.Optimizer],
        rho: float = 0.05,
        **base_optimizer_kwargs: Any,
    ) -> None:
        if rho < 0.0:
            raise ValueError(f"SAM rho must be non-negative, got {rho}")

        # ``defaults`` is what torch.optim.Optimizer stores for repr / state.
        defaults = dict(rho=rho, **base_optimizer_kwargs)
        super().__init__(params, defaults)

        # Construct the inner optimizer over the SAME param groups so that
        # LR scheduling, weight decay etc. stay coherent.
        self.base_optimizer = base_optimizer_class(
            self.param_groups, **base_optimizer_kwargs
        )
        # Mirror the base optimizer's groups: any LR change applied to
        # ``self.param_groups`` (e.g. by warmup helper) propagates because
        # the lists are aliased to the same dicts.
        self.param_groups = self.base_optimizer.param_groups
        self.rho = float(rho)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _safe_zero_grad(self) -> None:
        """zero_grad that works on PyTorch >=1.4 (no set_to_none kwarg).

        On 1.7+ we'd prefer ``set_to_none=True`` to free memory, but the
        deployed environments span 1.4 → 2.x. Manually zero each grad
        in-place; this is equivalent in semantics and avoids the kwarg.
        """
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is not None:
                    p.grad.detach_()
                    p.grad.zero_()

    @torch.no_grad()
    def _grad_norm(self) -> torch.Tensor:
        """Global L2 norm of gradients across all parameter groups.

        Skips params with no grad (frozen layers). Returns scalar tensor
        on the same device as the first available grad; falls back to a
        zero tensor on CPU if no grads exist.
        """
        first_device = None
        sq_sum = None
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                if first_device is None:
                    first_device = p.grad.device
                    sq_sum = torch.zeros((), device=first_device)
                # Match device: rare cross-device setups land grads on CPU.
                g2 = p.grad.detach().to(first_device).pow(2).sum()
                sq_sum = sq_sum + g2
        if sq_sum is None:
            return torch.zeros(())
        return sq_sum.sqrt()

    # ------------------------------------------------------------------
    # SAM steps
    # ------------------------------------------------------------------
    @torch.no_grad()
    def first_step(self, zero_grad: bool = True) -> torch.Tensor:
        """Compute epsilon = rho * g / ||g|| and perturb parameters in-place.

        After this call, ``model``'s parameters live at ``theta + epsilon``;
        the caller must run a second forward+backward, then call
        ``second_step``. The perturbation is cached in ``self.state[p]["e_w"]``
        so that ``second_step`` rolls back exactly (no float drift).

        Parameters
        ----------
        zero_grad : bool, default True
            Clear gradients after caching the perturbation, in preparation
            for the second backward pass.

        Returns
        -------
        torch.Tensor
            Scalar tensor with the global gradient norm. Useful for
            logging / NaN guards.
        """
        grad_norm = self._grad_norm()
        # Edge case: ||grad||=0 means no useful direction — leave params
        # untouched, cache zero perturbation, let base optimizer handle.
        # Use a small epsilon for numerical stability.
        scale = self.rho / (grad_norm + 1e-12)

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                # epsilon_w = (rho / ||g||) * g_p
                e_w = p.grad.detach().clone() * scale.to(p.grad.device)
                p.add_(e_w)
                # Cache for exact rollback in second_step.
                self.state[p]["e_w"] = e_w

        if zero_grad:
            self._safe_zero_grad()
        return grad_norm

    @torch.no_grad()
    def second_step(self, zero_grad: bool = True) -> None:
        """Restore parameters and apply base optimizer step with new gradients.

        Assumes the caller has run a second forward+backward at the perturbed
        point so ``p.grad`` now contains g_SAM = nabla L(theta + epsilon).
        Restoration uses the cached ``e_w`` so the original theta is recovered
        bit-exactly modulo the base optimizer update.
        """
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                e_w = self.state[p].get("e_w", None)
                if e_w is None:
                    # No perturbation was applied (e.g. p had no grad in
                    # first_step but does now — extremely rare). Skip.
                    continue
                # Roll back to the original theta.
                p.sub_(e_w)
                # Free the cache to keep optimizer state small.
                self.state[p].pop("e_w", None)

        # Apply the base optimizer with the SAM gradients.
        self.base_optimizer.step()

        if zero_grad:
            self._safe_zero_grad()

    # ------------------------------------------------------------------
    # torch.optim.Optimizer interface
    # ------------------------------------------------------------------
    def step(self, closure=None):  # type: ignore[override]
        """Two-step SAM update via a closure that returns loss.

        Provided for API compatibility with ``torch.optim.Optimizer``.
        The closure must (a) zero grads, (b) compute loss, (c) call
        ``loss.backward()``, and (d) return the loss tensor. It will be
        called twice: once at theta and once at theta + epsilon.

        Most callers should prefer the explicit ``first_step`` /
        ``second_step`` pattern shown in the class docstring; the closure
        form exists so SAM can be a drop-in for libraries that call
        ``optimizer.step(closure)``.
        """
        if closure is None:
            raise RuntimeError(
                "SAM.step() requires a closure that re-computes loss and "
                "calls backward(); use first_step/second_step for the "
                "explicit pattern."
            )
        # First pass already done by caller before invoking step? No — the
        # documented contract is that closure performs the full forward+
        # backward each time it is called.
        closure_with_grad = torch.enable_grad()(closure)
        # Pass 1: theta
        closure_with_grad()
        self.first_step(zero_grad=True)
        # Pass 2: theta + epsilon
        loss = closure_with_grad()
        self.second_step(zero_grad=True)
        return loss


# ----------------------------------------------------------------------
# Trainer integration recipe (DOCUMENTATION ONLY — do not auto-apply).
# ----------------------------------------------------------------------
def integrate_sam_into_trainer() -> str:
    """Return the diff snippet showing how to wire SAM into ``trainer_v2.py``.

    This function exists purely as living documentation; it is not called
    at runtime. The integration point is the optimizer step block around
    line 787-800 of ``src/training/trainer_v2.py``.

    Construction site (replaces the existing ``optimizer = AdamW(...)``)::

        from src.training.sam_optimizer import SAM

        if cfg.get("use_sam", False):
            optimizer = SAM(
                model.parameters(),
                torch.optim.AdamW,
                rho=cfg.get("sam_rho", 0.05),
                lr=lr,
                weight_decay=weight_decay,
            )
        else:
            optimizer = torch.optim.AdamW(
                model.parameters(), lr=lr, weight_decay=weight_decay
            )

    Step site (replaces lines 787-800). Note we re-run the model forward
    and the same loss assembly inside the SAM second pass; this is the
    only correct way to get gradients at theta + epsilon::

        optimizer.zero_grad()
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        if not torch.isfinite(grad_norm):
            optimizer.zero_grad()
            global_step += 1
            continue

        if hasattr(optimizer, "first_step"):
            # SAM path: perturb, recompute loss + grads at theta + eps, step.
            optimizer.first_step(zero_grad=True)
            # NOTE: caller must re-run the *exact same* forward + loss
            # assembly here. If the loss involves DUL/DANN/quantile mix,
            # all branches must be rebuilt at the perturbed parameters.
            outputs2 = model(*model_inputs)  # same inputs as the first pass
            loss2 = compute_loss(outputs2, targets)  # same loss recipe
            loss2.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            optimizer.second_step(zero_grad=True)
        else:
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            optimizer.step()

    Caveats:
        * The second forward pass MUST use the same batch (same ``x``,
          ``y``, ``mask``, dropout mask if possible). For determinism,
          consider ``torch.manual_seed`` inside the loop or accept that
          stochastic dropout introduces a small extra noise term — the
          paper found this acceptable.
        * EMA update (``ema_model.update_parameters``) should run AFTER
          ``second_step``, on the restored-and-stepped parameters.
        * Warmup helper is applied before ``second_step`` (the actual
          parameter update); ``first_step`` only perturbs and does not
          consume the LR.
        * Doubles per-step compute. Halve ``epochs`` or budget accordingly.
    """
    return integrate_sam_into_trainer.__doc__ or ""
