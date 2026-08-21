"""DomainAwareDataset wrapper — adds domain label to sample tuple for DANN.

Wraps LOBDatasetV2; uses ``_offsets`` to map sample idx → day idx → domain.
Time-based domain assignment: train days split into thirds (early/mid/late).
"""
from __future__ import annotations

import bisect
import numpy as np
import torch
from torch.utils.data import Dataset


class DomainAwareDataset(Dataset):
    """Wraps LOBDatasetV2; appends domain label as last tuple element.

    Parameters
    ----------
    base : LOBDatasetV2
        Must expose ``_offsets`` (cumulative day-count array of length n_days+1).
    n_domains : int
        Number of domain buckets (typically 3 = early/mid/late).
    """

    def __init__(self, base: Dataset, n_domains: int = 3):
        super().__init__()
        if not hasattr(base, "_offsets"):
            raise AttributeError(
                "DomainAwareDataset requires base to expose _offsets (LOBDatasetV2)"
            )
        self.base = base
        self.n_domains = int(n_domains)

        offsets = np.asarray(base._offsets, dtype=np.int64)
        n_days = len(offsets) - 1
        # Time-based domain: bucket day idx into N equal-size chunks.
        # Day 0..n_days/N-1 → domain 0; n_days/N..2n_days/N-1 → 1; etc.
        edges = np.linspace(0, n_days, self.n_domains + 1).astype(np.int64)
        day_to_domain = np.zeros(n_days, dtype=np.int64)
        for d in range(self.n_domains):
            day_to_domain[edges[d]:edges[d + 1]] = d
        self.day_to_domain = day_to_domain
        self._offsets_list = offsets.tolist()

    def __len__(self):
        return len(self.base)

    def __getitem__(self, idx: int):
        item = self.base[idx]
        # Map sample idx → day idx → domain
        day_idx = bisect.bisect_right(self._offsets_list, idx) - 1
        domain = int(self.day_to_domain[day_idx])
        domain_t = torch.tensor(domain, dtype=torch.long)
        if isinstance(item, tuple):
            return (*item, domain_t)
        return (item, domain_t)

    # Forward common attributes used by trainer for introspection
    def __getattr__(self, name):
        if name in ("base", "n_domains", "day_to_domain", "_offsets_list"):
            raise AttributeError(name)
        return getattr(self.base, name)
