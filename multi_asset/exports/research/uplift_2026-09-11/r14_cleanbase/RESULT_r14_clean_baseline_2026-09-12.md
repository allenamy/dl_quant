> **created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** MEASUREMENT, not an admission (ELIGIBILITY_CONTRACT gate `BUNDLE_export` is still empty) | **invalidated by:** any pinned input sha below changing, or STEP-1 failing to reproduce on a rebuild
> **prereg:** `PREREG_r14_clean_baseline_2026-09-12.md` sha `89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7` + `PREREG_AMENDMENT_1_2026-09-12.md` sha `e1caddf028b5148403da28527b6cb27ab152652d413c5f8bdf4bd04e4b74012f`; both asserted by every device before it runs
> **LIVE ZERO-TOUCH (VERIFIED):** no device in this round opens any path under `~/dl_quant_live` or `~/wide_shadow`; every path opened is enumerated with its sha256 in the receipts. No order, no restart, no trading endpoint. GPU not used.
> **ENV WHITELIST (E-0826-D) = EMPTY SET**, asserted in-file by all six devices; `env_seen_at_runtime` is an enumerated list in every receipt (all five ran under `env -i`).

# RESULT r14 — the baseline without the dead-leg prefix, and what it changes

## §0 One page

1. **The defect reproduces exactly, from source and from the archived arm.** `SLOW_v3_on_v4axis.npy` has its
   **first finite row at 2024-01-01T00:00:00Z** and not one anchor earlier. On W_ALPHA that is **3300/9138 =
   36.11%** king-dead, **1110/9138 = 12.15%** F10-dead, **1110** both-dead — every count exact, both prefixes
   contiguous, F10-dead a strict subset of king-dead. Conditional means exact: king-dead **−0.3770 / SR
   −1.1302**, king-live **+1.2058 / SR +2.1508**.
2. **The v4-native king has the SAME hole.** `SLOW_v4.npy` also starts at 2024-01-01T00:00:00Z. So the era and
   the defect are **perfectly confounded on this artifact** — there is no way to build a king-live baseline on
   2022–2023, with any file on pod2. This is new, and it constrains every conclusion below.
3. **Nothing in STEP 3 changes.** Across **27 candidates**, the largest |Δrho| is **0.0530**. **Zero** classification
   changes. **Zero** material moves by the pre-registered rule (|Δrho| ≥ 0.10 AND CI excludes 0). No candidate
   scored "just a re-weighting" reads independent on the clean baseline, and no candidate scored independent
   reads like a re-weighting.
4. **The control kills the interpretation of even the small moves.** rho wanders **more between 2024 / 2025 /
   2026 inside the clean sample** than it moves FULL→CLEAN, for **14/14** SET-A arms (median within-era range
   **0.1933** vs median |FULL→CLEAN| **0.0202**, a factor of 9.6). The FULL→CLEAN move is inside ordinary era
   noise. It carries no information about the defect specifically.
5. **The Amihud headline: the point estimate largely survives, the significance does not.** The archived
   **+0.2458 / CI95 [+0.0336, +0.4587]** reproduces **to four decimals** on p6's own window, 4/4 cells positive.
   On the clean sample it is **+0.2181, CI95 [−0.0278, +0.4664]** — **0/4** cells with a lower bound above zero.
   Pre-registered verdict: **COLLAPSES**. But the audit's stated reason is wrong: excluding 2023 entirely the
   gain is still **+0.1927**, and the clean-sample estimate retains **88.6%** of the full-sample value.
6. **The real problem with the Amihud result is one neither the programme nor the audit named.** At a=0.20 the
   combination's **mean g goes DOWN**: **−0.0025** bps/anchor on p6's window (the archived receipt's own
   `dg_point`), **−0.0900** on the clean sample, **−0.3766 in 2026**. The entire Sharpe gain is a **15–16% sd
   reduction**. At fixed gross it adds no net — it trades net for variance. Calling it "the programme's only
   positive result" reads a variance reduction as an alpha.
7. **The central claim does not survive — and it never held.** On the CONTAMINATED baseline, only **2 of 14**
   SET-A candidates sit in the REWEIGHTING band (|rho| ≥ 0.60); the median |rho| is **0.0254**. On the clean
   baseline: still 2 of 14, median **0.0367**. The two are `XIB_LAG50` (+0.8899) and `T1_FORMB` (+0.9362) —
   the only two candidates **constructed as modifications of A0**. Every candidate built from an independent
   data source is essentially orthogonal to the book on BOTH samples. The sentence "~300 candidates all failed
   because they were re-weightings of the same bet" is **not supported by the rho evidence it cites**, and
   fixing the baseline does not rescue it. Pre-registered verdict: **CLAIM NEVER HELD**.
8. **One error of my own, caught by a gate and disclosed:** I first loaded the wrong file for XIB_LAG50
   (`XIB_LAG50_s42__REAL.npz`, the placebo family's arm) because of its name — E-0825-H, committed in this
   round. Caught only because my rho did not reproduce the archived 0.8891. Corrected under AMENDMENT 1.

---

## §1 STEP 1 — the defect, reproduced

### 1.1 Source gate (G1) — `w10_sleeve.py` sha `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` (recomputed, matches the pin)

```
L219:  z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(FZ)
L267:  _zf = (_w3f[0] * np.nan_to_num(xz(F10P[i, m]))
L138:  def xz(v):
L139:      ok = np.isfinite(v); out = np.full(len(v), np.nan)
L140:      if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
L141:      return out
```
`xz` returns all-NaN when fewer than 10 member values are finite; `np.nan_to_num` then makes the leg an
identically-zero vector. **Nothing is logged, asserted, or counted.** G1 PASS.

### 1.2 Source coverage (G2) — from pod2, READ-ONLY

| file | sha256 (16) | finite rows / axis | first finite row | first finite ts |
|---|---|---|---|---|
| `SLOW_v3_on_v4axis.npy` (A0's king) | `647673183e6af44a` | 5838 / 10182 | 4338 | **2024-01-01T00:00:00Z** |
| `SLOW_v4.npy` (the v4-native king) | `dde19142d017c37d` | 5844 / 10182 | 4338 | **2024-01-01T00:00:00Z** |
| `f10_A0_s42.npy` on axis (A0's F10) | `ff109711f5526c68` | 8028 / 10182 | 2148 | **2023-01-01T00:00:00Z** |

King-live anchors before 2024-01-01 inside W_ALPHA: **0**. G2 PASS.
**★ `SLOW_v4` has the identical hole.** The confound in §3.3 follows from this row, and it is published here
for the first time.

### 1.3 Counts and conditionals (G3, G4), W_ALPHA n=9138

| quantity | measured | claimed | |
|---|---|---|---|
| king-dead | **3300** (36.1129%), 2022-06-30T00:00Z .. 2023-12-31T20:00Z, contiguous prefix | 3300 / 36.11% | ✓ |
| F10-dead | **1110** (12.1471%), 2022-06-30T00:00Z .. 2022-12-31T20:00Z, contiguous prefix, ⊂ king-dead | 1110 / 12.15% | ✓ |
| both-dead | **1110** | 1110 | ✓ |
| clean (king-live) | **5838**, 2024-01-01T00:00Z .. 2026-08-30T20:00Z | — | |
| king-dead mean g / Sharpe | **−0.3770 / −1.1302** | −0.3770 / −1.1302 | ✓ |
| king-live mean g / Sharpe | **+1.2058 / +2.1508** | +1.2058 / +2.1508 | ✓ |
| both-dead (fund-only) mean g / Sharpe | **+0.1586 / +0.4797** | — | |

### 1.4 Two-instrument gate (GATE D)

Instrument 1 = `isfinite(SLOW[i,m]).sum() < 10`, member set rebuilt on pod2 exactly as the arm did
(`MEMBERS_TOPN=829` from qvk, then the `m1` universe mask). Instrument 2 = `leg_king == 0.0` exactly in the
archived arm's own `rec`. **Disagreements on the 6854 anchors where `w3_king > 0`: 0.** (136 disagreements
overall, all on anchors where `w3_king == 0` and instrument 2 is blind by construction — which is why the
gate is conditioned.) PASS.

### 1.5 What the book actually IS on the dead prefix (mechanism, measured)

`w3_rev24 == 0.0` on every W_ALPHA anchor (LEGS=101). On the dead prefix:
- 2148 / 3300 anchors: `w3_king == 0` — the seat correctly hands everything to fund.
- **1152 / 3300 anchors: `w3_king == 0.5`** — the fund leg's own trailing msharpe was also ≤ 0, so `w3_at`
  falls to its `[1/3,1/3,1/3]` branch, which after the LEGS mask and renormalisation is `[0.5, 0, 0.5]`.
  **The seat LABELS king at 0.5 while king's z-vector is identically zero.**
- Either way `z = w3_fund · z_fund`, a pure multiple of the fund score, and the following `w /= L1(w)` removes
  the scalar. **The traded book is the fund-only book on all 3300 dead anchors.** `w3_king > 0` there is a
  seat label, not an exposure. Mean `gross_total` on the dead prefix is **0.8599** vs **0.6028** on the clean
  sample — the fund-only book runs 43% more gross.

### 1.6 Axis and level gates

G5: n_W_ALPHA **9138**, n_W_TAIL **10038**, strictly 4h-monotone, identity `net_ex = pnl_ex − carry_ex −
cost_ex` maxabs **0.0**. G6: A0 mean g **0.6341957**, Sharpe **1.2912234** — both to the published digit.
Books axis gate: the archived `books_on_pinned_axis.npz` A0 column matches my recomputation **bitwise (0.0)**.

---

## §2 STEP 2 — the clean sample, and what it costs

**CLEAN = the 5838 king-live anchors = 2024-01-01T00:00Z .. 2026-08-30T20:00Z.**

> **★ ERA-SELECTED. Say this next to every number below.** CLEAN is a contiguous suffix. There is no king
> prediction before 2024-01-01 in either the v3 or the v4 file (§1.2), so a king-live baseline on 2022–2023
> **cannot be built from anything on pod2**. CLEAN is a clean estimate of the book's behaviour **in that era**.
> It is **not** a clean estimate of the cross-regime Sharpe, and 2026 alone (n 1452, Sharpe 4.52, 5.1× the
> full-sample mean g) is 24.9% of it.

| | FULL (W_ALPHA) | CLEAN (king-live) | KING-DEAD | BOTH-DEAD (fund-only) |
|---|---|---|---|---|
| n | 9138 | **5838** | 3300 | 1110 |
| range | 2022-06-30 .. 2026-08-30 20Z | **2024-01-01 .. 2026-08-30 20Z** | 2022-06-30 .. 2023-12-31 20Z | 2022-06-30 .. 2022-12-31 20Z |
| mean g bps/anchor/gross | +0.6342 | **+1.2058** | −0.3770 | +0.1586 |
| mean g CI95 (block, B=2000, k=1) | [+0.1774, +1.1136] | **[+0.5213, +1.8374]** | — | — |
| sd bps | 22.985 | 26.236 | 15.612 | 15.471 |
| **Sharpe_ann** | 1.2912 | **2.1508** | −1.1302 | +0.4797 |
| **SE = √(2190/n)** | 0.4895 | **0.6125** | 0.8146 | 1.4046 |
| Sharpe CI95 analytic | [+0.332, +2.251] | **[+0.950, +3.351]** | [−2.727, +0.467] | [−2.273, +3.233] |
| Sharpe CI95 bootstrap | [+0.351, +2.272] | **[+0.926, +3.287]** | — | — |
| turnover RAW `Σ|dw|` | 0.0303158 | **0.0360281** | 0.020210 | 0.015893 |
| turnover MATCHED `E[t_i/g_i]` | 0.0540270 | **0.0708852** | 0.024203 | 0.017639 |
| matched/raw ratio | 1.78214 | **1.96750** | 1.19758 | 1.10983 |
| mean gross_total | 0.6956440 | **0.6028087** | 0.8598781 | — |
| **maxDD (bps of gross)** | 2632.4 | **1305.2** | 1694.8 | 558.0 |
| **worst UTC day (bps)** | −232.5 (2022-11-10) | **−220.0 (2025-05-13)** | −232.5 (2022-11-10) | −232.5 (2022-11-10) |
| NAV %/yr at 2× gross | +27.78% | **+52.81%** | −16.51% | +6.95% |

**Tail convention:** the W_TAIL numbers for the CLEAN sample are the **same numbers** — all 900 warm-drop
anchors are king-dead, so W_ALPHA∩CLEAN and W_TAIL∩CLEAN are the identical 5838-anchor set (verified, set
equality). The W_TAIL/W_ALPHA distinction is **vacuous on the clean sample**. For reference the full W_TAIL
book (n 10038) is mean g +0.5608, Sharpe 1.1062, maxDD 2925.9 bps, worst day **−566.6 (2022-06-07)**.

**Turnover unit note (the trap that caught the programme four times).** My unrounded matched/raw ratio is
**1.78214**; the brief's 1.78189 is the same quantity computed from the ROUNDED raw 0.03032. Both are right;
`raw / mean_gross_total = 0.0435795 ≠ 0.0540270` and `1/mean_gross_total = 1.4375` — the matched value is
`E[t_i/g_i]`, not `E[t]/E[g]`.

**Per-year, with the king-live fraction next to it** (this is the table the defect was invisible in):

| year | n | king-live frac | mean g | Sharpe |
|---|---|---|---|---|
| 2022 | 1110 | **0.00** | +0.1586 | +0.4797 |
| 2023 | 2190 | **0.00** | −0.6485 | −1.9355 |
| 2024 | 2196 | 1.00 | +0.4865 | +1.0875 |
| 2025 | 2190 | 1.00 | +0.6770 | +1.1867 |
| 2026 (→08-30) | 1452 | 1.00 | +3.0913 | +4.5165 |

---

## §3 STEP 3 — rho to baseline on FULL vs CLEAN. THE MEASUREMENT THAT MATTERS.

**Primary statistic:** Pearson rho between the candidate's per-anchor `g` and the baseline's, because that is
what every archived rho-to-baseline in this programme is. Spearman is in the receipt for each row.
**Bands (pre-registered, the programme's own 0.60 line):** REWEIGHTING |rho| ≥ 0.60 · PARTIAL 0.30–0.60 ·
INDEPENDENT < 0.30. **Material move (pre-registered):** |Δrho| ≥ 0.10 AND the paired day-block bootstrap CI95
of Δrho excludes 0.

**Cost-plane control, run because the arms are not all on one plane:** the SAME book A0 priced on the
deployed fee-only plane vs the fitted plane correlates at **rho = 1.0000** on both samples. **The cost plane
does not move rho at all.** Mixed-plane rows in the table below are therefore safe.

### 3.1 All 27 candidates + 2 disclosure rows, ranked by |Δrho|

| rank | arm | set | rho FULL (n 9138) | rho CLEAN (n 5838) | d rho | d rho CI95 paired | material? | band FULL | band CLEAN |
| 1 | `SLOWARM_A_VOL1H` | B | -0.0607 [-0.1099,-0.01] | -0.1137 [-0.1774,-0.0516] | **-0.0530** | [-0.0737,-0.0311] | no | INDEPENDENT | INDEPENDENT |
| 2 | `TSMOM_best` | A | -0.0768 [-0.124,-0.0306] | -0.1152 [-0.1697,-0.0594] | **-0.0384** | [-0.0615,-0.0158] | no | INDEPENDENT | INDEPENDENT |
| 3 | `TSMOM` | A | -0.0978 [-0.1479,-0.0482] | -0.1330 [-0.1875,-0.0748] | **-0.0352** | [-0.0587,-0.0112] | no | INDEPENDENT | INDEPENDENT |
| 4 | `SLOWARM_A_TBF1H` | B | +0.0172 [-0.0209,0.0561] | -0.0139 [-0.0632,0.0327] | **-0.0311** | [-0.0482,-0.0151] | no | INDEPENDENT | INDEPENDENT |
| 5 | `VRP` | A | +0.0076 [-0.0404,0.0555] | +0.0383 [-0.0215,0.1002] | **+0.0307** | [0.0074,0.0515] | no | INDEPENDENT | INDEPENDENT |
| 6 | `SLOW_best` | A | -0.0284 [-0.071,0.0126] | +0.0007 [-0.0505,0.0471] | **+0.0292** | [0.0135,0.0458] | no | INDEPENDENT | INDEPENDENT |
| 7 | `SLOWARM_C_TBF3D` | B | -0.0284 [-0.071,0.0126] | +0.0007 [-0.0505,0.0471] | **+0.0292** | [0.0135,0.0458] | no | INDEPENDENT | INDEPENDENT |
| 8 | `SLOWARM_B_TBF12H` | B | -0.0209 [-0.0621,0.0172] | +0.0074 [-0.0417,0.0597] | **+0.0284** | [0.012,0.046] | no | INDEPENDENT | INDEPENDENT |
| 9 | `SLOWARM_D_FSLOPE` | B | -0.0436 [-0.0836,-0.0008] | -0.0673 [-0.1138,-0.0193] | **-0.0237** | [-0.0392,-0.0098] | no | INDEPENDENT | INDEPENDENT |
| 10 | `XIB_LAG50_placeboREAL` | DISCLOSURE | +0.8555 [0.8414,0.868] | +0.8790 [0.8643,0.8927] | **+0.0235** | [0.018,0.0293] | no | REWEIGHTING | REWEIGHTING |
| 11 | `AMIHUD_SLEEVE` | A | +0.1468 [0.1077,0.1847] | +0.1237 [0.0752,0.1729] | **-0.0231** | [-0.0401,-0.007] | no | INDEPENDENT | INDEPENDENT |
| 12 | `CMUM_static` | A | +0.0223 [-0.0226,0.078] | +0.0012 [-0.0649,0.0829] | **-0.0211** | [-0.0553,0.007] | no | INDEPENDENT | INDEPENDENT |
| 13 | `XIB_LAG50` | A | +0.8899 [0.8786,0.9] | +0.9108 [0.8994,0.9215] | **+0.0209** | [0.0163,0.0259] | no | REWEIGHTING | REWEIGHTING |
| 14 | `SLOWARM_C_TBF30D` | B | -0.0884 [-0.1285,-0.051] | -0.0674 [-0.112,-0.0208] | **+0.0209** | [0.0054,0.0368] | no | INDEPENDENT | INDEPENDENT |
| 15 | `SLOWARM_C_TBF14D` | B | -0.0862 [-0.1291,-0.0476] | -0.0667 [-0.1152,-0.0162] | **+0.0196** | [0.0032,0.0365] | no | INDEPENDENT | INDEPENDENT |
| 16 | `SLOW` | A | -0.0828 [-0.1256,-0.0423] | -0.1022 [-0.1544,-0.0502] | **-0.0194** | [-0.0373,-0.0016] | no | INDEPENDENT | INDEPENDENT |
| 17 | `SLOWARM_B_REV12H` | B | +0.0005 [-0.0489,0.0495] | -0.0168 [-0.0768,0.0391] | **-0.0173** | [-0.0383,0.0024] | no | INDEPENDENT | INDEPENDENT |
| 18 | `SLOWARM_C_TBF7D` | B | -0.0714 [-0.1127,-0.0318] | -0.0561 [-0.1041,-0.0049] | **+0.0154** | [0.0002,0.0314] | no | INDEPENDENT | INDEPENDENT |
| 19 | `COINT` | A | +0.0215 [-0.0217,0.0635] | +0.0351 [-0.0198,0.086] | **+0.0136** | [-0.0048,0.0339] | no | INDEPENDENT | INDEPENDENT |
| 20 | `CMUM_best` | A | +0.0070 [-0.0506,0.0762] | -0.0034 [-0.0828,0.0852] | **-0.0104** | [-0.0451,0.0136] | no | INDEPENDENT | INDEPENDENT |
| 21 | `SLOWARM_A_QVS1H` | B | -0.0387 [-0.0765,-0.0019] | -0.0487 [-0.0946,-0.0057] | **-0.0100** | [-0.0229,0.0032] | no | INDEPENDENT | INDEPENDENT |
| 22 | `REVS_best` | A | -0.0211 [-0.065,0.0215] | -0.0136 [-0.0628,0.0385] | **+0.0075** | [-0.0085,0.0256] | no | INDEPENDENT | INDEPENDENT |
| 23 | `SLOWARM_D_FCHG12H` | B | -0.0160 [-0.0531,0.0213] | -0.0086 [-0.054,0.0382] | **+0.0074** | [-0.0084,0.0231] | no | INDEPENDENT | INDEPENDENT |
| 24 | `REVS` | A | +0.0186 [-0.0182,0.0551] | +0.0239 [-0.0185,0.0696] | **+0.0053** | [-0.0094,0.0207] | no | INDEPENDENT | INDEPENDENT |
| 25 | `T1_FORMB` | A | +0.9362 [0.9308,0.9414] | +0.9319 [0.9254,0.938] | **-0.0043** | [-0.006,-0.0025] | no | REWEIGHTING | REWEIGHTING |
| 26 | `CMUM` | A | +0.0058 [-0.0157,0.0259] | +0.0023 [-0.0245,0.0277] | **-0.0034** | [-0.0166,0.0101] | no | INDEPENDENT | INDEPENDENT |
| 27 | `SLOWARM_D_FCHG3D` | B | +0.0390 [0.0018,0.0765] | +0.0424 [-0.0034,0.087] | **+0.0034** | [-0.0113,0.0176] | no | INDEPENDENT | INDEPENDENT |
| 28 | `SLOWARM_A_REV1H` | B | +0.0021 [-0.045,0.0502] | +0.0005 [-0.057,0.0592] | **-0.0016** | [-0.0169,0.0131] | no | INDEPENDENT | INDEPENDENT |
| 29 | `A0_feeplane` | DISCLOSURE | +1.0000 [1.0,1.0] | +1.0000 [1.0,1.0] | **+0.0000** | [0.0,0.0] | no | REWEIGHTING | REWEIGHTING |

**No classification changes. No material moves. Largest |Δrho| in the whole table: 0.0530.**

### 3.2 The two REWEIGHTING candidates are the two that are BUILT from A0

- `XIB_LAG50` **+0.8899 → +0.9108**. It is A0 with the fund leg's score matrix swapped (`FEMAT_NPZ`); it is a
  re-weighting of A0 **by construction**, and the rho measures that construction, not a discovery.
- `T1_FORMB` **+0.9362 → +0.9319**. It is an **overlay on A0** (r13B `g_primary`, with `g_base` matching my
  A0 to 7.9e-06). Correlating an overlay with its own base is not evidence about candidate exhaustion.
- Every candidate built from an **independent data source** — TSMOM, VRP, CMUM, COINT, REVS, SLOW and all
  their arms, plus the Amihud sleeve — is within **|rho| ≤ 0.15** of the book on BOTH samples.

### 3.3 ★ Is the FULL→CLEAN move the DEFECT or the ERA? The control says you cannot tell, and it does not matter

The two are perfectly confounded on this artifact (§1.2: no king file of any lineage covers 2022–2023). The
available control is whether rho is era-stable *inside* the clean sample:

| arm | rho FULL | rho CLEAN | 2022 | 2023 | 2024 | 2025 | 2026 | within-clean-era range | |Δ FULL→CLEAN| |
|---|---|---|---|---|---|---|---|---|---|
| TSMOM | −0.0978 | −0.1330 | +0.0969 | −0.0295 | −0.2221 | −0.2093 | +0.1848 | **0.4069** | 0.0352 |
| VRP | +0.0076 | +0.0383 | +0.1088 | −0.2026 | +0.2819 | +0.1871 | −0.3846 | **0.6665** | 0.0307 |
| CMUM | +0.0058 | +0.0023 | +0.0160 | +0.0102 | +0.0294 | −0.0037 | −0.0429 | 0.0723 | 0.0034 |
| SLOW | −0.0828 | −0.1022 | +0.0526 | −0.0646 | −0.1529 | −0.2625 | +0.0807 | **0.3432** | 0.0194 |
| COINT | +0.0215 | +0.0351 | −0.1265 | +0.0268 | +0.1406 | +0.0662 | −0.0937 | 0.2343 | 0.0136 |
| REVS | +0.0186 | +0.0239 | −0.0456 | +0.0217 | −0.0117 | +0.0772 | −0.0112 | 0.0889 | 0.0053 |
| TSMOM_best | −0.0768 | −0.1152 | +0.0595 | +0.0405 | −0.2414 | −0.1566 | +0.2012 | **0.4426** | 0.0384 |
| CMUM_static | +0.0223 | +0.0012 | +0.0472 | +0.0924 | +0.0226 | +0.0475 | −0.1091 | 0.1566 | 0.0211 |
| CMUM_best | +0.0070 | −0.0034 | +0.0031 | +0.0653 | −0.0126 | +0.0555 | −0.1084 | 0.1639 | 0.0104 |
| SLOW_best | −0.0284 | +0.0007 | −0.1140 | −0.1437 | +0.0736 | −0.0244 | −0.0244 | 0.0980 | 0.0292 |
| REVS_best | −0.0211 | −0.0136 | −0.1034 | −0.0233 | +0.0329 | +0.0780 | −0.1448 | 0.2228 | 0.0075 |
| XIB_LAG50 | +0.8899 | +0.9108 | +0.7545 | +0.8323 | +0.8653 | +0.9457 | +0.9033 | 0.0804 | 0.0209 |
| AMIHUD_SLEEVE | +0.1468 | +0.1237 | +0.1025 | +0.3088 | +0.4064 | +0.1103 | −0.0997 | **0.5061** | 0.0231 |
| T1_FORMB | +0.9362 | +0.9319 | +0.9825 | +0.9447 | +0.9103 | +0.9401 | +0.9374 | 0.0298 | 0.0043 |

**14/14 arms: rho wanders more between 2024 / 2025 / 2026 than it moves FULL→CLEAN.** Median within-clean-era
range **0.1933** vs median |FULL→CLEAN| **0.0202** — a factor of **9.6**. Conclusion, stated as strongly as the
evidence allows and no further: **the dead-leg prefix is not what makes rho-to-baseline unreliable. rho-to-
baseline is unreliable because rho itself is not a stable quantity year to year.** A screen that admits or
rejects on a single full-sample rho was never measuring a stable property, contaminated baseline or not.

### 3.4 rho on the KING-DEAD half, for completeness

`AMIHUD_SLEEVE` is the one arm whose rho to the baseline is materially higher on the broken half (+0.2368 on
king-dead vs +0.1237 clean) — it co-moves more with the fund-only book than with the real one, which is the
mechanism behind §4.3. `XIB_LAG50` goes the other way (+0.8072 dead vs +0.9108 clean): it tracks the real
book more closely than the fund-only one, as a fund-leg re-weighting should. Full column in the receipt.

---

## §4 STEP 4 — the Amihud sleeve's +0.2458, recomputed on the clean sample

### 4.1 The archived number reproduces exactly

| cell | archived (`P6_COMBO_PAIRED.json`) | mine, p6's own window n=9018 |
|---|---|---|
| s42 ΔSharpe point | +0.24579898 | **+0.2458** |
| s42 CI95 k=0 | [+0.03364089, +0.45866263] | **[+0.0336, +0.4587]** |
| s42 CI95 k=9 | [+0.03147446, +0.47189628] | **[+0.0315, +0.4719]** |
| s2027 CI95 k=0 | [+0.03190257, +0.45530649] | **[+0.0319, +0.4553]** |
| s2027 CI95 k=9 | [+0.03051480, +0.46383553] | **[+0.0305, +0.4638]** |
| cells with CI lower bound > 0 | 4/4 | **4/4** |
| s42 Δmean-g point | **−0.00251632** | **−0.00252** |

Measured aside: the Amihud sleeve arm is **bitwise identical across the two DL seeds** (maxabs Δg = 0.0). The
archived "2 seeds" spread comes entirely from the A0 side; the sleeve has no seed.

### 4.2 On the clean sample — the pre-registered verdict

| window | n | SR A0 | SR comb (a=0.20) | **ΔSharpe** | CI95 (k=0) | cells with lower bound > 0 |
|---|---|---|---|---|---|---|
| p6 window | 9018 | 1.4150 | 1.6608 | **+0.2458** | [+0.0336, +0.4587] | **4/4** |
| W_ALPHA | 9138 | 1.2912 | 1.5375 | **+0.2462** | [+0.0361, +0.4646] | 4/4 |
| **CLEAN (king-live)** | **5838** | **2.1508** | **2.3689** | **+0.2181** | **[−0.0278, +0.4664]** | **0/4** |
| KING-DEAD | 3300 | −1.1302 | −0.6760 | +0.4542 | [−0.0146, +0.9084] | 2/4 (k=9 cells only) |
| W_ALPHA excluding 2023 | 6948 | 1.9570 | 2.1497 | **+0.1927** | [−0.0518, +0.4365] | 0/4 |
| 2023 only | 2190 | −1.9355 | −1.2368 | +0.6987 | [+0.2120, +1.2474] | 4/4 |

(Cell counts are 2 arm seeds × 2 bootstrap seeds k∈{0,9}; the per-cell lower bounds are in
`RECEIPT_r14_amihud_detail.json::cells`. CLEAN is 0/4 on all four; KING-DEAD is 2/4, positive only on the
k=9 bootstrap — i.e. not stable to the bootstrap seed, which is itself a caution about the 4/4 headline.)

**Pre-registered verdict: COLLAPSES** (point estimate +0.2181 clears the +0.1229 half-value threshold, but the
CI95 lower bound is −0.0278 < 0). The programme's only 4/4-positive result is **0/4 on the clean sample**.

**But the audit's stated reason is wrong.** "It is entirely a 2023 fix" does not hold: the clean-sample
estimate retains **88.6%** of the full-sample value, and dropping 2023 altogether still leaves **+0.1927**. The
significance dies because n falls 9138 → 5838 (SE 0.4895 → 0.6125), not because the effect does.

**Per year at a=0.20, seed 42:**

| year | king-live | SR A0 | SR sleeve | SR comb | ΔSharpe | **Δmean-g bps/anchor** |
|---|---|---|---|---|---|---|
| 2022 | 0.00 | +0.480 | +0.168 | +0.494 | +0.0141 | −0.01779 |
| 2023 | 0.00 | −1.936 | +1.861 | −1.237 | **+0.6987** | **+0.27550** |
| 2024 | 1.00 | +1.088 | +1.197 | +1.239 | +0.1518 | +0.01670 |
| 2025 | 1.00 | +1.187 | +1.379 | +1.408 | +0.2217 | −0.00694 |
| 2026 | 1.00 | +4.516 | +2.168 | +4.956 | +0.4392 | **−0.37665** |

### 4.3 ★ The finding neither the programme nor the audit named: it is a variance trade, not an alpha

| window | Δmean-g (bps/anchor/gross) | Δmean-g CI95 (k=0) | sd reduction |
|---|---|---|---|
| p6 window n=9018 | **−0.00252** | [−0.1194, +0.1204] | 15.11% |
| W_ALPHA n=9138 | **+0.00636** | [−0.1138, +0.1261] | 15.17% |
| **CLEAN n=5838** | **−0.09000** | [−0.2532, +0.0674] | **15.98%** |
| 2026 only | **−0.37665** | — | — |

The pin's own resolution on a window of this size is **±0.23 bps/anchor**; every full-sample Δmean-g above is
an order of magnitude below it. **The combination does not earn more. On the clean sample it earns less, and
in 2026 — the book's best year — it gives up 0.3766 bps/anchor, which at 2× gross is 16.5% NAV/yr.** The whole
of ΔSharpe is the 15–16% drop in sd.

That is a legitimate thing to want; it is **not** an uplift at fixed gross, and it only becomes NAV if you
re-lever — which runs straight into the desk's own W_TAIL ladder (1 halt already at 1.00×, 6 at 2.00×). The
sentence "the programme's only positive result" should read "the programme's only measured **risk reduction**,
whose Sharpe framing hid that its net is flat-to-negative."

Mechanism, for the record: the sleeve's rho to the baseline is **+0.2368 on the king-dead half** and **+0.1237
on the clean half** — it co-moves with the fund-only book more than with the real one. Its 2023 rescue
(+0.2755 bps/anchor) is a rescue **of a book that was not the book**.

---

## §5 STEP 5 — the central claim

### 5.1 The distribution of |rho|, both samples

| | SET A (14 candidates) FULL | SET A CLEAN | SET A+B (27) FULL | SET A+B CLEAN |
|---|---|---|---|---|
| min | 0.0058 | 0.0007 | 0.0005 | 0.0005 |
| p25 | 0.0192 | 0.0059 | 0.0179 | 0.0080 |
| **median** | **0.0254** | **0.0367** | **0.0284** | **0.0383** |
| p75 | 0.0940 | 0.1216 | 0.0798 | 0.0848 |
| max | 0.9362 | 0.9319 | 0.9362 | 0.9319 |
| mean | 0.1688 | 0.1739 | 0.1065 | 0.1091 |
| **REWEIGHTING ≥ 0.60** | **2** | **2** | **2** | **2** |
| PARTIAL 0.30–0.60 | 0 | 0 | 0 | 0 |
| **INDEPENDENT < 0.30** | **12** | **12** | **25** | **25** |

The distribution is **bimodal with nothing in between**: two candidates above 0.85, twenty-five below 0.15,
an empty PARTIAL band on both samples. That shape is not "a family of re-weightings of one bet." It is
"two objects that ARE A0 modified, and twenty-five that are not correlated with A0 at all."

### 5.2 Verdict, by the pre-registered rule

`R_FULL = 2 ≤ 3` ⇒ **CLAIM NEVER HELD**. The contaminated-baseline evidence itself never concentrated the
candidates at high rho. `R_CLEAN = 2` as well, and the median |rho| moves +0.0113 — the clean baseline neither
rescues the claim nor damages it.

### 5.3 What has to be retracted, plainly

> "这就是为什么 ~300 条候选一条都没过: **它们全都是同一个下注的重新加权。**" — `CLOSEOUT_uplift_program_2026-09-12.md` L44
> "rho 0.889 到 A0 —— 它是 A0 的再加权, 不是一个新赌注" — `DOCKET_r7_ship_2026-09-12.md` L255

**The first sentence is not supported by the rho evidence it cites, and never was.** 25 of 27 archived
candidates are essentially uncorrelated with the book on both the contaminated and the clean baseline. The
programme's candidates did not fail because they were the same bet. They failed on **net** — their standalone
mean g is at or below zero (`CMUM −1.0328`, `SLOW −0.2716`, `COINT −0.2739`, `REVS −2.7097`, `VRP +0.0895`,
`TSMOM +0.4076`, all bps/anchor/gross on W_ALPHA) — which is a different diagnosis with a different cure.

**The second sentence is fine**, and is the correct reading for `XIB_LAG50` and `T1_FORMB` specifically.
The error is the generalisation from those two to "~300 candidates."

**This does not soften the round-13 conclusion.** Whether the candidates were re-weightings or independent
bets, none of them paid. It changes **why**, and therefore what a round 15 should look for: not "a source
uncorrelated with A0" (there are 25 of those already, and the search has been solved) but "a source with
positive net at this turnover and this cost plane" — which is the open question Door 1 controls the sign of.

---

## §6 Limits of this round — what I did NOT establish

1. **I could not separate defect from era**, and neither can anyone with the files on pod2 (§1.2). Every
   CLEAN number is a joint statement about a working king leg AND about 2024–2026.
2. **CLEAN is 24.9% 2026 by anchor count and far more by contribution** (2026 mean g +3.0913 vs full-sample
   +0.6342). A clean-sample Sharpe of 2.1508 is not a cross-regime Sharpe and must never be quoted as one.
3. **I did not rebuild A0 without the defect.** The defect is unfixable on this artifact; what I did was
   *condition on* the anchors where it is absent. A genuine fix requires a king prediction file covering
   2022–2023, which does not exist. That is a data-production task, not a research task.
4. **Cost-estimand dispute (Door 1) is untouched here.** Every g in this round is on one of two plane choices
   and the plane does not move rho (§3), but it does move every LEVEL. Nothing here resolves the 0.5066
   bps/anchor spread, and the Amihud §4.3 conclusion (net is flat-to-negative) would move with it.
5. **Nulls.** No SHIFT/RELAB null is informative for a correlation between two archived return series, and
   this round adds no turnover; none was run. (Path note: the brief's `r3_attack_b9646/null.py` is a pod2
   path, `/workspace/uplift_2026-09-11/r3_attack_b9646`; the repo mirror is `r3_attack_RESID_SHARPE/null.py`.)
6. **SET B is 13 arms of one candidate family** (SLOW_CLOCK components). It widens the distribution in §5.1
   but is not 13 independent candidates; the SET-A-only column is the one to read.

---

## §7 My own errors this round

1. **E-0825-H, committed by me: I loaded `XIB_LAG50_s42__REAL.npz` because of its name.** It is the placebo
   family's REAL arm, not the r3 XIB screen's arm. Caught only because rho did not reproduce the archived
   0.8891 and I ran a reconciliation instead of publishing the disagreement. Corrected under AMENDMENT 1; the
   wrong arm's numbers are disclosed in the §3.1 table so the correction cannot be read as threshold-shopping
   (both files are far above the 0.60 line; the band could not have been chosen).
2. **The archived `rho = 0.8891` has no JSON receipt in this repo** — it exists only in prose in
   `PREREG_r3_xib_lag50_fundleg_promotion` L19 and `RESULT_r6_judge2` L20. I reproduced it from pod2 arms
   (`R3_XIBLAG50_dyn_s42` × `R3_A0_dyn_s42`, n=9018 → **+0.8891**, exact) and the reproduction is now
   receipted here. Before this round it was unreceipted.

---

## §8 Receipts, devices and pinned inputs

**Devices** (all six: ENV WHITELIST = EMPTY SET asserted in-file, prereg sha asserted before running,
self sha written into the receipt, run under `env -i`):

| device | sha256 | what it does | receipt |
|---|---|---|---|
| `devices/r14_pod_deadmask.py` | `3564792fd59678b202fdb96f7de778dff4afca4ed5fcc299b610d7f5e185dd67` | pod2, READ-ONLY: leg-death masks from source + Amihud arm extraction | `receipts/RECEIPT_r14_pod_deadmask.json` |
| `devices/r14_main.py` | `d1d7b153e0f0c4ecb896233b51db081fdd1d1d512eb7b9cedf902ab90a3c76b5` | STEP 1 gates, STEP 2 baseline, STEP 3 rho, STEP 4, STEP 5 | `receipts/RECEIPT_r14_main.json` |
| `devices/r14_xib_recon.py` | `5132d18a759576272fa2028f95eee43f94eeaa9a61b4e4a84cce3dd12a21b9f1` | window × cost-plane reconciliation of the archived 0.8891 | `receipts/RECEIPT_r14_xib_recon.json` |
| `devices/r14_amihud_detail.py` | `d5f87b142103892468210fc013600cdae61a53857f1724e3d9b2f3c9eca38b98` | 4/4-cell reproduction, per-year, 2023-excluded, mean-g vs sd | `receipts/RECEIPT_r14_amihud_detail.json` |
| `devices/r14_era_rho.py` | `474e61e1d1a788d9a1ea3b7b8a91f1be71e0a194e86d1911c4853e9e1979efcd` | era-vs-defect control | `receipts/RECEIPT_r14_era_rho.json` |
| `devices/r14_facts.py` | `434436070b54ed94a832efa982bc5ab27dbfc09c49d67816e7a8665af64adfdf` | seat weights on the dead prefix, turnover-unit arithmetic | `receipts/RECEIPT_r14_facts.json` |

**Pinned inputs, sha256 recomputed this session** (full list in each receipt's `inputs`):

| input | sha256 (16) | where |
|---|---|---|
| `w10_sleeve.py` | `b88e35a46b93d712` | repo `trackA/` (== the caliber pin) |
| `A0_PWR230k_s42.npz` (the baseline arm) | `352ac36fb3195327` (== the canonical pinned arm) | repo `r10_screen/CMUM_CARRY/pin/` |
| `SLOW_v3_on_v4axis.npy` | `647673183e6af44a` | pod2 `/workspace/review_scratch/king_v4/` |
| `SLOW_v4.npy` | `dde19142d017c37d` | pod2, same dir |
| `f10_A0_s42.npy` | `ff109711f5526c68` | pod2 `health_check/dev_v4/f8_2026-08-22/preds/` |
| `meta_newprod_v4.npz` | `0e3c09ac86c727ac` | pod2 `review_scratch/refute_C6_2/altrun/` |
| `umask_UPIT_CRYPTO.npz` | `47d87b5165b695a7` | pod2 `health_check/masks/` |
| `P6_AMQ64_PWR_s42.npz` (Amihud) | `edcf068affc6fc57` | pod2 `/workspace/uplift_2026-09-11/p6/arms/` |
| `R3_XIBLAG50_dyn_s42.npz` | `d364e00313959ad9` | pod2 `/workspace/uplift_2026-09-11/r3_xib/arms/` |
| `R3_A0_dyn_s42.npz` (fee-plane A0) | `5d99abfa43f1c040` | pod2, same dir |
| `A0_PWR230k_s2027.npz` | `aa44e18fb6bcfa7e` | pod2 `/workspace/uplift_2026-09-11/r3k/arms/` |

**Series published:** `series/r14_clean_series.npz` — ts, `g_A0`, the three dead masks, the per-anchor finite
counts for king-v3 / king-v4 / F10, both turnover calibers, and the 29 candidate g columns. Anyone can redo
§3 and §5 from that one file.

**Bootstrap:** UTC-day block, B=2000, `numpy.default_rng([20260905,k])`; k=1 FULL, k=1 CLEAN (clean day
universe = days every anchor of which is king-live: 973 of 1523 UTC days), k=2 paired Δrho, k=3 my Amihud
statistic, k=0 and k=9 for reproducing the archived Amihud cells.

**Standing:** EXPLORATORY. `ELIGIBILITY_CONTRACT.json` gate `BUNDLE_export` still has
`approved_source_sha256 = []`, so nothing here is promotable or deployable. These are research measurements.
