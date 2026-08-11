#!/usr/bin/env python3
"""Assemble the 39-channel wide panel for ARM-S2 (24h supplementary factor arm).

32 existing factor channels (wide_dl_full.npz CH) + 7 OI/positioning metrics
channels (wide_metrics_ch.npz CH, already 0-filled outside its MASK, matching the
existing 0-fill convention). All targets (Y/YR/CL {1,4,24}), masks, ts, symbols,
baseline_cols carried through unchanged. Harness auto-adapts to C=39 from shape.
"""
import numpy as np

BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"
METRICS = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_metrics_ch.npz"
OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full_39ch.npz"

A = np.load(BASE, allow_pickle=True)
B = np.load(METRICS, allow_pickle=True)

assert np.array_equal(A["ts"], B["ts"]), "ts mismatch"
assert list(A["symbols"]) == list(B["symbols"]), "symbols mismatch"
assert not (set(A["ch_names"]) & set(B["ch_names"])), "channel name collision"

CH32 = A["CH"].astype(np.float32)          # (T,N,32) fully finite (0-filled)
CH7 = B["CH"].astype(np.float32)           # (T,N,7)  0-filled outside MASK
assert np.isfinite(CH32).all() and np.isfinite(CH7).all(), "non-finite CH"
CH39 = np.concatenate([CH32, CH7], axis=2)  # (T,N,39)
ch_names = list(A["ch_names"]) + list(B["ch_names"])
assert CH39.shape[2] == len(ch_names) == 39

out = {k: A[k] for k in A.files}           # carry every key through unchanged
out["CH"] = CH39
out["ch_names"] = np.array(ch_names, dtype=object)
# provenance: which channels are the new metrics block (for downstream ablation)
out["metrics_ch_idx"] = np.arange(32, 39, dtype=np.int64)

np.savez_compressed(OUT, **out)
print("SAVED", OUT)
print("CH", CH39.shape, "ch_names", len(ch_names))
print("metrics block idx 32..38:", ch_names[32:])
print("keys:", sorted(out.keys()))
