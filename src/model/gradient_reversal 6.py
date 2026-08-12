"""Gradient Reversal Layer for DANN (Domain Adversarial Neural Network).

Ganin & Lempitsky 2015 (https://arxiv.org/abs/1409.7495).
Forward: identity. Backward: reverse gradient sign and scale by lambda.

Used to train a feature extractor to be domain-invariant by adversarial
training against a domain classifier.
"""
from __future__ import annotations

import torch
from torch.autograd import Function


class _GradReverse(Function):
    @staticmethod
    def forward(ctx, x: torch.Tensor, lambda_: float) -> torch.Tensor:
        ctx.lambda_ = float(lambda_)
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        return grad_output.neg() * ctx.lambda_, None


def grad_reverse(x: torch.Tensor, lambda_: float = 1.0) -> torch.Tensor:
    """Apply gradient reversal with scaling lambda."""
    return _GradReverse.apply(x, lambda_)
