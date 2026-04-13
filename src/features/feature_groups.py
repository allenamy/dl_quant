"""Semantic feature grouping for the SpatialLOBEncoder.

Defines which microstructure features belong to the bid-side, ask-side,
and global groups so that cross-group attention has meaningful structure.

The grouping covers the 39 original features produced by
``compute_microstructure_features`` plus 5 order-flow features that are
being added in parallel (``delta_bid_depth_L5``, ``delta_ask_depth_L5``,
``net_order_flow_L5``, ``delta_obi_L5_5s``, ``delta_pressure_5s``).
If those features are not yet present in the data, they are silently
skipped when building index mappings.
"""

from __future__ import annotations

from typing import Dict, List


# -----------------------------------------------------------------------
# Canonical feature groups (name-based)
# -----------------------------------------------------------------------

_BID_FEATURES: List[str] = [
    # OBI features (bid-dominated semantics: positive = bid > ask)
    "obi_L1",
    "obi_L5",
    "obi_L10",
    "obi_L25",
    "obi_L1_delta",
    # Bid depth
    "bid_depth_L5",
    "bid_depth_L25",
    # Bid-side weighted price
    "weighted_price_bid_L10",
    # Bid slope
    "bid_slope_L10",
    # Bid concentration
    "bid_concentration",
    # Per-level bid amount ratios
    "bid_amt_ratio_L0",
    "bid_amt_ratio_L1",
    "bid_amt_ratio_L2",
    "bid_amt_ratio_L3",
    "bid_amt_ratio_L4",
    # Order-flow (bid-side, being added in parallel)
    "delta_bid_depth_L5",
]

_ASK_FEATURES: List[str] = [
    # Ask depth
    "ask_depth_L5",
    "ask_depth_L25",
    # Ask-side weighted price
    "weighted_price_ask_L10",
    # Ask slope
    "ask_slope_L10",
    # Ask concentration
    "ask_concentration",
    # Per-level ask amount ratios
    "ask_amt_ratio_L0",
    "ask_amt_ratio_L1",
    "ask_amt_ratio_L2",
    "ask_amt_ratio_L3",
    "ask_amt_ratio_L4",
    # Order-flow (ask-side, being added in parallel)
    "delta_ask_depth_L5",
]

_GLOBAL_FEATURES: List[str] = [
    # Returns
    "log_return_1s",
    "log_return_5s",
    "log_return_30s",
    # Spread (cross-side)
    "spread_bps",
    "spread_change",
    # Depth ratio (cross-side)
    "depth_ratio_L5",
    # Price pressure (cross-side)
    "price_pressure",
    # Volatility
    "realized_vol_30s",
    "realized_vol_60s",
    "realized_vol_300s",
    # Microstructure
    "kyle_lambda_30s",
    "amihud_30s",
    # Temporal
    "second_of_day_sin",
    "second_of_day_cos",
    # Order-flow (cross-side, being added in parallel)
    "net_order_flow_L5",
    "delta_obi_L5_5s",
    "delta_pressure_5s",
]


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def get_feature_groups() -> Dict[str, List[str]]:
    """Return the canonical name-based feature groups.

    Returns
    -------
    dict with keys ``"bid"``, ``"ask"``, ``"global"``, each mapping to a
    list of feature name strings.
    """
    return {
        "bid": list(_BID_FEATURES),
        "ask": list(_ASK_FEATURES),
        "global": list(_GLOBAL_FEATURES),
    }


def get_feature_group_indices(
    feature_names: List[str],
) -> Dict[str, List[int]]:
    """Map semantic group names to column indices for a given feature list.

    Parameters
    ----------
    feature_names : list[str]
        Ordered list of feature column names as they appear in the data
        (e.g. from the NPZ ``features`` array).

    Returns
    -------
    dict with keys ``"bid_idx"``, ``"ask_idx"``, ``"global_idx"``, each
    mapping to a sorted list of integer indices.  Features present in the
    canonical groups but absent from *feature_names* are silently skipped.
    Features present in *feature_names* but not in any canonical group are
    assigned to the ``"global_idx"`` group so that no feature is lost.
    """
    name_to_idx = {name: idx for idx, name in enumerate(feature_names)}

    bid_set = set(_BID_FEATURES)
    ask_set = set(_ASK_FEATURES)
    global_set = set(_GLOBAL_FEATURES)

    bid_idx: List[int] = []
    ask_idx: List[int] = []
    global_idx: List[int] = []

    for name, idx in name_to_idx.items():
        if name in bid_set:
            bid_idx.append(idx)
        elif name in ask_set:
            ask_idx.append(idx)
        elif name in global_set:
            global_idx.append(idx)
        else:
            # Unknown features default to global group
            global_idx.append(idx)

    bid_idx.sort()
    ask_idx.sort()
    global_idx.sort()

    return {
        "bid_idx": bid_idx,
        "ask_idx": ask_idx,
        "global_idx": global_idx,
    }
