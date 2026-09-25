> **Created:** 2026-09-25 16:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** DESCRIPTIVE before/after reading of fix D on ONE cell (NC s42X, 32 paths) — NOT a verdict (DECISION RULE rev 7 891aec11c: D is judged on the family n ≥ 8 against dlarch's retained baseline cells) | **Invalidated by:** a change of the fix, the mirror copy, or the filed SER

# Fix D (dust pop before reshape) in the engine: NC s42X, 32 paths, vs the filed SER_EXT_NEWS2_s42X
Mirror COPY with the fix-pkg-d 1e70316 anchor_loop patch (only file differing; the three functions AST-identical to the executor fix), new
manifest pin; filed mirror untouched. `BT_LAUNCH VERDICT=PASS label=full runs=1 seeds=32`. Hook on (read-only; the hook's zero-impact control
passed three times on the unpatched mirror).
- Book-return difference D − base, mean over 32 paths: **+0.006 bps / anchor** (Σ +56.8 bps over 9,252 anchors); 86 % of anchors differ on
  at least one path. By year (Σ bps / mean bps per anchor): 2022 0 / 0 (pad); 2023 +100.1 / +0.046; 2024 −24.6 / −0.011; 2025 −50.6 /
  −0.023; 2026 +32.0 / +0.020. Mixed signs, magnitudes ~0.01–0.05 bps per anchor.
- Post-clamp book net / NAV with the fix (all 32 paths pooled, 208,290 decided path-anchors): median |net| ≈ 1e-14 %, 5–95 % −0.068 … +0.034 %,
  p95 |net| 0.080 %, mean −0.006 %. Before the fix (c4hook2, path 0): 5–95 % −1.42 … +0.85 %, 2026 mean −0.30 %.
Reading (descriptive): the fix removes the engine's post-clamp net tilt (the tail shrinks by more than an order of magnitude) and moves the
book return by a few hundredths of a bp per anchor, sign varying by year. The verdict is the family run's (rev 7), not this cell's.
Hook rows (208,290, ~several hundred MB with per-name targets) were not copied; the summary is in FIXD_READ.json.
