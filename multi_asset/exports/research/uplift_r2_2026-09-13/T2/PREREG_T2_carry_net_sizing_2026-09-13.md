> **创建:** 2026-09-13 05:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (subagent T2) | **状态:** 冻结 — written before any κ estimate, any arm run and any Δg; sha256 goes to `receipts/PREREG_FREEZE_sha.txt` and is asserted by every T2 device before it reads data | **作废条件:** a chain newer than v4 passing its gates; replacement of the archived A0 / NW / r15 ARM-S artifacts; a change of the pinned device `w10_sleeve.py` b88e35a4… or of the r18 derived device 9b8a6323… | **口径:** `uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md` (v4 chain; RAW accounting `y4` = Π(1+r)−1 from `meta_newprod_v4.npz`; nothing is recomputed from the ret5-clipped 5m cache)
> **纲领:** `uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md` §2 T2 (facts P1, P4, P5) | **分支:** `research/book-uplift-2026-09-11` | **实盘零接触:** `~/dl_quant_live` and `~/wide_shadow` are neither read nor written by this round; no API call

# PREREG T2 · Size the funding leg on expected NET return: price edge minus the UNCOMPENSATED part of carry

## §0 Question, prior evidence, and one conflict in the task that this prereg resolves

**Question.** The book pays carry (A0 book carry_ex/gt 0.4797 bps/anchor/unit gross on W_ALPHA, r15 §3), and part of that carry is returned by price (r15 ARM-F: 77% of the carry saved by killing leaked shorts came back as forgone price P&L; program P4). If only a fraction κ* of carry is uncompensated, a fund leg ranked on *expected net* = price edge − κ*·carry should beat the fund leg ranked on price edge alone (A0, which implicitly assumes κ = 0, i.e. carry fully compensated). κ* is estimated from data, walk-forward, never grid-searched.

**Ceiling, frozen before any number (program P5).** Uncompensated carry ≈ 0.480 × 0.23 ≈ **0.11 bps/anchor/unit gross ⇒ ≤ +0.2 Sharpe**. A Δg point estimate above **1.5 × 0.11 = 0.165** is treated as a leakage suspect first (§7), not as a win. The bootstrap resolution of this window is 0.23 bps/anchor (r15 §6): the ceiling sits below it, so a PROMOTE-candidate here needs a tight paired CI, not a large point.

**Prior receipts this prereg must not ignore (read, not re-litigated):**
- trackA (v4, `RESULT_trackA_carry_sleeves_2026-09-11.md` §3): CDAMP (z ÷ (1 + λ·carry/10bp) on the paying side) lost at every dose (Δ −0.06…−0.09, price given up per unit carry saved 1.4–1.8); trimming longs with funding ≥ +10bp gave up **3.81** bps of price per bp of carry saved; shorts of negative funding were the favourable side (price improved too). ⇒ the carry–price relation is plausibly **asymmetric by the sign of funding**. The primary estimand below is the symmetric κ* the task asks for; the per-side slopes are pre-registered as a **diagnostic** (§2.5), not as an arm.
- `funding_transfer_priced_in_settlement_window`: in the settlement window, paid funding ≈ price move in every rate bucket; "dodging" carry forfeits the compensation.
- r15 ARM-S (`SEATNET=1`, leg seat input = price LR − leg rank-book carry, every leg): Δg −0.0928 [−0.359, +0.172] (s42) / −0.0894 (s2027), REJECT (turnover +27%).

**The conflict (stated once, resolved by construction).** The lead's arm definition (ii) is a **name-level** change — the fund-leg *score* becomes expected net, with the seat rule identical to A0 — while the lead's κ≡1 positive control ("must reproduce r15 ARM-S Δg −0.0928 / −0.0894") is only definable for a **seat-level** construction: ARM-S changes the seat input of every leg and leaves every score untouched, so no score-level arm can reproduce it at any κ. Rather than build one and STOP on a control that cannot pass by construction, this prereg declares **both** constructions, each with the controls that are defined for it:
- **ARM-N / ARM-Nσ** (name level, the lead's (ii) and (iii)): κ≡0 must reproduce A0 bitwise; κ≡1 has no archived counterpart, so a wiring check replaces the reproduction (§4).
- **ARM-SK** (seat level): κ≡0 must reproduce A0 bitwise, κ≡1 must reproduce r15 ARM-S bitwise (hence its Δg to 4 decimals).
**Interpretation caveat for ARM-SK, frozen now:** the seat input is the *realized* leg price return, which already contains whatever price compensation occurred; subtracting κ*·carry with κ* < 1 therefore adds back the compensated part (seat input = realized net + (1−κ*)·carry). ARM-SK is a data-dosed interpolation between A0 (κ=0) and ARM-S (κ=1), **not** an expected-net seat. ARM-N is the construction whose algebra is expected net (§2.2).

## §1 Instruments (all sha256 recomputed on pod2 before use; any mismatch aborts)

| item | value |
|---|---|
| pinned replay device | pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 **b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650** (VERIFIED 2026-09-13 on pod2) |
| r18 derived device (parent of T2) | pod2 `/workspace/uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py` sha256 **9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4** (VERIFIED) |
| T2 derived device | `devices/w10_sleeve_t2.py`, generated by `devices/mk_t2_device.py` from the r18 device by once-only string replacements; diff kept as `devices/w10_sleeve_t2.diff`; self-reports its sha256, the parent sha and this prereg's sha in `config_json["T2"]` |
| κ estimator | `devices/t2_kappa.py` (writes the per-anchor κ path used by the device; §2) |
| archived A0 | `/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz` **352ac36f…bcfd339**, `_s2027.npz` **aa44e18f…e1c7b** (VERIFIED) |
| archived NW (r18: N2 causal eligibility + WU warm-up, `R18_ELIG=1 R18_WARM=1 R18_INSTR=1`) | `/workspace/uplift_2026-09-11/r18_foundation/arms/NW_s42.npz` **afbcd92ea41d7e4cd75159e64e8640dedf7727219dd852df3a1f0ef3e7f4692d**, `NW_s2027.npz` **89d28a319f2bd61f755cf973d1697f30b6fe0f3dfeb9aad20d2bb553575c11a5** (VERIFIED) |
| archived r15 ARM-S | `/workspace/uplift_2026-09-11/r15_structural/arms/S_s42.npz` **6d59d57fc4f139a5d7f7b75417b4f804a5a3397950ae2f8df64bdf1662ad8376**, `S_s2027.npz` **2e38ecf2930db850b2133b2879e74e67297fb5be81b198c1e9c50ad5b002beda** (VERIFIED; run on the pinned device, A0 env + `SEATNET=1`) |
| cost | `r3k/costb_PWR_G230k.json` **295b4e7b…d53** (λ = 1.0 is the only verdict number) |
| data (via a T2-owned symlink tree identical in layout to r18's `dev/`) | meta `meta_newprod_v4.npz` sha16 0e3c09ac86c727ac; panel `wide_panel_4h_v2ext.npz` 5e67c0559daa904d; umask `umask_UPIT_CRYPTO.npz` 47d87b5165b695a7; king `SLOW_v3_on_v4axis.npy` 647673183e6af44a; F10 `f10_A0_s42.npy` ff109711f5526c68 / `f10_A0_s2027.npy` 98bfe779261b550f; `dlw_v4raw/data/dlw_targets.npz` d1976cf6246cdc25 (all VERIFIED in r18's receipt; re-hashed by the T2 driver) |
| A0 env (verbatim from the archived arms) | `LEGS=101 PHI=0.45 WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FTRIM_TH=-0.0010 UMASK_SCOPE=m1 CAL=log FTPOS=0 SEATNET=0 UMASK_NPZ=…/umask_UPIT_CRYPTO.npz SLOW_NPY=…/SLOW_v3_on_v4axis.npy FSEED∈{42,2027} FPRED=f10_A0_s{FSEED}.npy COSTB_JSON=…/costb_PWR_G230k.json`; NW env = A0 env + `R18_ELIG=1 R18_WARM=1 R18_INSTR=1` |
| statistics kernel | UTC-day block bootstrap, 2000 draws, draw k uses `numpy.random.default_rng([20260905, k])`, statistic Σ_day Σ_anchor d / Σ_day n (r12/r15/r18 `boot()` verbatim); Sharpe = mean/sd(ddof=1)·√2190 |

Baseline facts carried from r15/r18 (VERIFIED there; re-asserted by the T2 judge): A0 s42 W_ALPHA g **0.6341957**, Sharpe **1.2912234**, matched turnover **0.0540270**; king leg is dead (SLOW_v3_on_v4axis NaN) before 2024-01-01 and F10 before 2023-01-01; the archived A0 carries v3-lineage model legs and is used as pinned, not repaired.

## §2 The estimand κ* (walk-forward; estimator `t2_kappa.py`)

### §2.1 Per-anchor cross-section (replicates the device's own sets exactly)
For each replay anchor i with a panel row j (the 10039 anchors the device books):
- members = `MEMBERS_TOPN=829` rebuild from `qvk[i]` (device L70-76), then the m1 umask row for j if present (device L212-214);
- `FZ = xz(FE[j, :])[m]` with `FE = f_fund_ema_v1` and `xz(v) = rankdata(v[ok])/max(ok.sum()−1, 1) − 0.5` over finite entries (≥ 10) — the device's `FZB`, i.e. the fund-leg score in the 829 base;
- carry per unit long weight over the holding interval `c = nan_to_num(FN[j, m])·(4/IVf[j, m])`, `FN = f_fund_now`, `IVf = IV if finite and > 0 else 8` — exactly the quantity the device charges (`car = Σ sm·fnow·4/iv`);
- price P&L per unit long weight over the same interval `y = y4[i, m]` (RAW accounting return, CAL=log ⇒ no expm1);
- estimation set: `isfinite(y4[i,m]) ∧ qv4h ≥ 2.5e5 ∧ isfinite(FZ) ∧ isfinite(FN[j,m])` with `qv4h = expm1(clip(qvk[i,m], 0, 30))·48`; the anchor enters only if the set has ≥ 80 names.
- **Winsorization for estimation only:** `y_w = clip(y, −0.20, +0.20)` (a 4h move beyond ±20% is a crash/listing event unrelated to a funding transfer of a few bps; one such cell can move a pooled slope by O(0.1)). The **book's accounting is never winsorized.** The unwinsorized path is a reported diagnostic (§2.5).
- Within-anchor demeaning of `y_w`, `FZ`, `c` over the estimation set (anchor fixed effects: the book is cross-sectionally demeaned).

### §2.2 The regression and the algebra of "expected net"
Pooled within-anchor OLS over the estimation window: `y_w = a_i + λ·FZ + b·c + ε`.
- `b` = the fraction of carry returned by price, holding the fund score fixed; **κ*_raw = 1 − b̂**.
- `λ` = the fund score's price edge beyond carry compensation (return per rank unit).
- Expected net per unit long = `λ·FZ + b·c − c = λ·FZ − κ*·c`. A0 ranks on FZ alone ⇔ κ = 0 ⇔ "carry fully compensated".
- Guards (mechanical, frozen): **κ* = clip(κ*_raw, 0, 1)**; **λ⁺ = max(λ̂, 0)**; if λ⁺ = 0 and κ* = 0 the adjustment is inactive. Counts of each guard firing are reported.
- Standard errors: sandwich with UTC-day clusters (primary) and ISO-week clusters (reported), from per-day aggregates Σx̃x̃ᵀ and Σx̃ỹ.

### §2.3 Walk-forward schedule (choice: MONTHLY refit, EXPANDING window)
- Refit instants T = 00:00Z on the 1st of every calendar month on the replay axis. The estimate at T uses only anchors with **E_ts ≤ T − 8h** (their forward 4h return closed by T − 4h: one full anchor of embargo beyond the closing time).
- Anchor i uses the latest refit T ≤ E_ts[i]. Before the first refit with ≥ **540** estimation anchors (≈ 90 days) the path is **inactive** (the arm equals its baseline there).
- **Why monthly-expanding and not yearly:** κ* is a slowly varying structural quantity and the signal is weak (R² < 1%), so effective sample dominates: an expanding window uses all past data at every anchor; a yearly refit would run the whole of 2022 on the first ~90-day estimate and leave every later estimate up to 12 months stale, with no offsetting benefit. Monthly refits of an expanding window move the estimate smoothly (each refit adds ≤ 1/6 of the data after year one). A yearly-refit path is computed as a **diagnostic** only.
- One path, independent of seed and of the A0/NW base (it is a property of the data, not of the book).

### §2.4 State-conditioned variant κ*(σ_fund) (ARM-Nσ; bins fixed now as a causal rule)
- State: `σ_j = std(_RN8[j, isfinite(FN[j])])·1e4` if > 50 finite quotes else NaN, with `_RN8 = nan_to_num(FN)·(8/IVf)` — the device's own FUNDSCALE dispersion definition (829 base, 8h-equivalent rate, bps).
- Bins: at each refit T, cut points `q1, q2 = np.quantile(σ over the estimation window's anchors with finite σ, [1/3, 2/3])`; bin 0 if σ ≤ q1, 1 if σ ≤ q2, else 2. Anchor i is binned with ITS OWN σ_{j(i)} against the cut points of its refit T. **Numeric cut points from r12's SIGF receipt are deliberately not used**: they were computed on the whole W_ALPHA and would put future distribution information into the early part of the path.
- Per refit and bin: the §2.2 regression on that bin's estimation anchors ⇒ (λ̂_b, b̂_b) ⇒ κ*_b, λ⁺_b with the same guards. Active only if every bin has ≥ **180** anchors and σ_{j(i)} is finite.
- The T1 thread may later suggest other states; this prereg does not wait for it and does not add them.

### §2.5 Diagnostics computed from the same cross-sections (reported, never used by an arm)
(d1) unwinsorized path; (d2) **per-side slopes**: `y_w = a_i + λ·FZ + b⁺·c⁺ + b⁻·c⁻` with `c⁺ = max(c, 0)` (longs pay), `c⁻ = min(c, 0)` (shorts pay), each demeaned within anchor ⇒ κ⁺ = 1 − b⁺, κ⁻ = 1 − b⁻; (d3) yearly-refit path (refit on 1 January only); (d4) **live-window reading**: the §2.2 regression on anchors 2026-08-26 00Z … 2026-09-10 00Z only, on the r6 extension tree (`/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz` sha256 a8eb3597…, `wide_panel_4h_v2ext_x0910.npz` sha16 042478f7…; prefix bitwise equality to the incumbent meta/panel is re-asserted; the incumbent umask ends 2026-08-31 00Z, so its last row is carried forward for September — an approximation, labelled), with day-clustered SE and the explicit caveat that 16 clusters make that SE unreliable.

## §3 Arms (K = 3; all declared now; no arm added after any number)

Every arm = baseline env (A0 for the verdict; NW reported) + exactly one T2 change; seeds 42 and 2027.

| arm | knobs | what changes | what stays identical to the baseline |
|---|---|---|---|
| **ARM-N** | `T2_MODE=name T2_KCOL=scalar` | at anchor i, the fund-leg score used by BOTH book chains (king chain L219, F10 chain L269) becomes `FZ_book = xz(λ⁺_T·xz(FE[j,:]) − κ*_T·c_all)[m]`, `c_all = nan_to_num(FN[j,:])·(4/IVf[j,:])`, ranked in the 829 base | seat input (`legs()` keeps the unadjusted FZ), seat rule, EMA/band, FTRIM, universe, cap, gross, F10 blend, stop layer, cost, accounting; the `leg_fund` diagnostic column keeps the unadjusted FZ |
| **ARM-Nσ** | `T2_MODE=name T2_KCOL=sigma` | as ARM-N with (λ⁺, κ*) of the anchor's σ bin | as ARM-N |
| **ARM-SK** | `T2_MODE=seat T2_KCOL=scalar` | seat input of every leg at anchor i = `P_leg[p−900:p] − κ*_i·C_leg[p−900:p]` (the current κ applied to the whole trailing window), `P_leg` = A0's price LR, `C_leg` = the leg's unit-gross rank-book 4h carry (the exact quantity `SEATNET` subtracts); κ*_i = 0 where the path is inactive | every score, FTRIM, EMA/band, universe, cap, gross, blend, stop layer, cost, accounting |

Why the **rank** of expected net (ARM-N) and not an additive shift in rank units: the fund leg keeps exactly A0's score distribution on [−0.5, 0.5], so the seat weights, the blend and the cap see the same scale as in A0 and only the cross-sectional **ordering** changes; an additive `FZ − (κ*/λ̂)·c` would divide by a noisy λ̂ and let extreme-carry names dominate the L1 normalisation. With κ* = 0 the rank of `λ⁺·FZ` equals FZ bit for bit (monotone transform, same finite set), which is what PC-0 tests.

Why the seat arm applies κ* to **every** leg: the carry–price relation is a property of the carry, not of which leg holds the name, and it is the only form whose κ≡1 endpoint is ARM-S.

## §4 Gates before any arm result (STOP rules frozen)

| gate | runs | pass condition | on failure |
|---|---|---|---|
| **GATE P** | T2 device, `T2_MODE=off`: A0 env ×2 seeds, NW env ×2 seeds | `rec` (10039×23) and `W` (10039×829) bitwise equal to archived A0 / archived NW (`np.array_equal` incl. NaN pattern, maxabs 0.0), cols equal, self-reported sha = T2 device sha | **STOP everything** |
| **PC-0** (lead's κ≡0 control) | `T2_KFORCE=0` for `T2_MODE=name` and `=seat`, A0 and NW env, both seeds (8 runs) | bitwise equal to the same baseline as GATE P; the receipt counts the anchors that actually went through the rank path | **STOP everything** |
| **PC-1** (lead's κ≡1 control, seat) | `T2_MODE=seat T2_KFORCE=1`, A0 env, both seeds | `rec` and `W` bitwise equal to archived r15 `S_s42` / `S_s2027`, **and** judge-computed W_ALPHA Δg vs A0 formats to **−0.0928** (s42) and **−0.0894** (s2027) at 4 decimals | **STOP everything** |
| **WIRE** (κ≡1 on the name path; no archived counterpart exists) | `T2_MODE=name T2_KFORCE=1`, A0 env, both seeds, `T2_INSTR=1` | (a) g differs from A0 (|Δ| > 1e-12) on ≥ 50% of W_ALPHA anchors; (b) `FZ_book` recorded by the device at 12 fixed rec rows `900 + 745·k` (k = 0..11) equals an independent re-implementation in the driver (panel + path) bitwise, NaN pattern included | ARM-N and ARM-Nσ = NOT_RUN; ARM-SK proceeds |
| **C1** estimator future-invariance | `t2_kappa.py` self-gate at 12 refits evenly spaced over the refit list (scalar and σ bins) | estimates bitwise identical after replacing every y4 row with E_ts > T − 8h and every panel funding row (f_fund_now, f_fund_ema_v1, f_fund_iv) with ts > T − 8h by seeded garbage | **STOP everything** |
| **C2** device shuffle-future | garbled tree: y4 rows with E_ts ≥ T* permuted within row among finite cells (NaN pattern kept — the pinned A0 eligibility reads the forward NaN pattern, a known look-ahead that NW fixes), and panel rows with ts > T* permuted within row for f_fund_now / f_fund_ema_v1 / f_fund_iv; **T* = 2024-07-16 00:00Z** (mid-month, so a leak that reads end-of-month data inside the current refit period is caught); κ path re-estimated on the garbled tree; runs: A0 (`T2_MODE=off`) and the three arms, A0 env, both seeds | path bitwise equal for every anchor with E_ts ≤ T*; `W` rows with ts ≤ T* bitwise equal to the real runs; rec columns other than net/pnl/net_ex/pnl_ex/leg_* bitwise equal for ts ≤ T*, and all rec columns bitwise equal for ts < T* | the failing arm's verdict = **VOID (LEAK)** |

All gates run on pod2 before the judge opens any arm's W_ALPHA statistics. The positive controls run first; the arm runs are launched by the driver only after GATE P, PC-0, PC-1 and C1 have passed.

## §5 Windows (never mixed)
- `W_ALPHA` = rec rows ≥ 900 ∩ ts ≤ 2026-08-30 20Z ⇒ **n = 9138** (asserted). All means, CIs, Sharpe, turnover, decompositions.
- `W_TAIL` = ts ≤ 2026-08-30 20Z ⇒ **n = 10038** (asserted). All maxDD / worst day / HALT / ALERT.
- `KING_LIVE` = W_ALPHA ∩ ts ≥ 2024-01-01 ⇒ n = 5838 (asserted). Every headline is repeated there.
- `W_LIVE_REPLAY` = 2026-08-26 00Z ≤ ts ≤ 2026-08-30 20Z ⇒ n = 30 (asserted). The replay cannot go further: F10 predictions end 2026-08-30 20Z (r6 §5, every PHI>0 arm) and 2026-08-31 is contaminated (E-0911-B). **2026-09-01 → 09-11 is not replayable on this device family**; the only reading there is the κ diagnostic (d4).

## §6 Statistics and the decision rule (frozen)

### §6.1 Per arm × seed × base
- `g = net_ex/gross_total` (bps/anchor/unit gross); identity `net_ex = pnl_ex − carry_ex − cost_ex` asserted per anchor (atol 1e-9).
- **Primary:** paired `Δg = mean_{W_ALPHA}(g_arm − g_base)`, **base = A0 of the same seed** (reference name printed with every Δ). CI95 from the kernel in §1. CI99-K (K = 3, percentiles 0.8333 / 99.1667) reported, never decisive.
- Decomposition Δpnl, Δcarry, Δcost (and the ratio Δpnl/Δcarry = price given up per unit of carry saved, comparable with trackA/r15); book carry_ex/gt arm vs base.
- Turnover (matched `turnover/gross_total` only): arm, base, Δτ %.
- Sharpe arm and base with SE √(2190/n); ΔSharpe against the ceiling +0.2.
- Per calendar year on W_ALPHA (2022 from 2022-06-30, 2023, 2024, 2025, 2026 to 08-30): g and Sharpe for arm and base, Δg.
- KING_LIVE repeat of the primary block.
- W_LIVE_REPLAY: g arm, g base, Δg, day-bootstrap CI with n_days = 5 printed and labelled uninformative.
- Tail on W_TAIL at **fixed 2.0× NAV**: UTC-day return `Π(1 + 2·g·1e-4) − 1`, NAV compounded with 1.0 prepended (E-0909-C), true peak-to-trough maxDD, worst day, HALT (day ≤ −4.00%), ALERT (≤ −2.68%) — r18 `tailrow` verbatim at L = 2.0, M = 1.0.
- Descriptive: Δg by the anchor's causal σ bin (§2.4 assignment), with within-bin day bootstrap; for ARM-N/Nσ the fraction of anchors where FZ_book ≠ FZ, mean |ΔFZ| and mean within-anchor correlation of FZ_book with FZ; for ARM-SK the seat path (w3_king mean, p10/p50/p90, by year) vs A0.
- NW base: every statistic above, Δ vs **NW of the same seed**; reported as a robustness reading, not a verdict.

### §6.2 Decision (A0 base, W_ALPHA, per arm, both seeds required)
- **PROMOTE-candidate** iff on **both** seeds: CI95 lower bound of Δg **> 0**; W_TAIL 2.0× compounded maxDD_arm **≤** maxDD_A0; HALT_arm **≤** HALT_A0; C2 passed; and, if the ceiling tripwire fired, §7 passed. Turnover change is disclosed (no turnover gate: cost is already inside Δg at λ = 1.0).
- **REJECT** iff on either seed the CI95 upper bound of Δg < 0.
- **UNDECIDED** otherwise, with the failing clause named.
- Flags that never change the verdict: `MULTIPLICITY-FRAGILE` (a PROMOTE-candidate whose CI99-K includes 0); `BELOW-RESOLUTION` (|Δg| < 0.23).
- **Language rule (E-0907-F):** "maxDD not worse" and "HALT not worse" are single-path point comparisons inside a decision rule, not a statistical non-inferiority proof, and are written as such.
- **Replication rule (E-0907-E):** the s2027 contrast is `ARM_s2027 − A0_s2027` with the reference name printed; the same contrast as s42, never a different reference.

### §6.3 Mechanism readouts (reported before the P&L table; not STOP conditions)
- **M1 identification:** at the final refit (2026-08-01), is κ*_raw's day-clustered CI95 inside [0, 1] or does it straddle a boundary? Stability: min / max / mean of κ* over the refits used in W_ALPHA, fraction of those refits where a guard clipped it, first-half vs second-half W_ALPHA mean.
- **M2 engagement:** did the arm reduce book carry (Δcarry < 0 on W_ALPHA, both seeds)? An arm that does not move carry cannot be a carry-sizing effect whatever its Δg.

## §7 Ceiling tripwire and leakage investigation (frozen)
- **Fires** if any arm's Δg point estimate on the A0 base, W_ALPHA, exceeds **+0.165** on either seed.
- Then, before the arm may be reported as an effect, both seeds: **offset spectrum** (a) path shift by refit months s ∈ {−1 (look-ahead: month M uses the refit of M+1), +1 (stale: uses M−1)}; (b) for ARM-N / ARM-Nσ, carry-input lead `T2_CLEAD` ∈ {−1 (row j−1, 4h stale), +1 (row j+1, 4h future)}.
- **PASS** iff Δg(path stale +1) ≥ 0.5·Δg(0) **and**, for name arms, Δg(CLEAD −1) ≥ 0.5·Δg(0) — a real carry-sizing effect built on persistent funding survives a one-anchor or one-month stale input, while a contemporaneous leak collapses when the input is made stale. The look-ahead offsets (path −1, CLEAD +1) are reported to show the size of a leak signature; they are not pass conditions, because future funding is genuinely informative about the next interval's price and would spike for a clean arm too. C1 and C2 (§4) are the shuffle-future tests and are already standing gates.
- **FAIL** ⇒ verdict `UNDECIDED (LEAK-SUSPECT)`; the Δg is not reported as an effect.

## §8 ENV whitelist and receipts (E-0826-C/D)
- Every device run: exact env dict = `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3` ∪ baseline knobs ∪ arm knobs ∪ `OUT_TAG`; the dict is written to the receipt key by key.
- Driver, estimator, judge: launched `env -i PATH=… HOME=/root /workspace/venv/bin/python <device> PATH,HOME,LC_CTYPE`; each asserts `os.environ` keys ⊆ the whitelist and that no caliber-flag prefix is present (`CAL JUDGE UPLIFT PANEL LOOK WRULE LEGS PHI FSEED W3FIX FTRIM UMASK SLOW FPRED MEMBERS_TOPN COSTB SLEEVE KMOD SEAT RNSM LTRIM CDAMP FUNDSCALE FEMAT TRADE_TOPN REF_SKIP PYTHON OMP MKL R15 R18 SMA SBAND FTPOS OUT_TAG T2`). Caliber is read from each artifact's `config_json`, never from the environment.
- Every receipt: `self_sha256`, `prereg_sha256` (asserted), env whitelist (non-empty), input realpaths + sha256, `nvidia-smi` before/after (expected `0 %, 2 MiB`), protected PIDs 333197 / 339489 state before/after (expected stopped, never signalled), load average before (the driver waits while the 1-minute load is > 6).
- Rerun commands are transcribed verbatim into the RESULT.

## §9 What this round does not do
- No deployment proposal and no production diff: a fund-leg score or seat-rule change is a book-behaviour change that needs its own prereg and a user ruling. Any PROMOTE-candidate is labelled NOT_DEPLOYABLE as-is.
- No null family beyond C1/C2 and §7: the κ path is estimated, not chosen, so the matched-placebo family of r15 has no dose to match; this is a stated limitation.
- No GPU, no retraining, no September replay of any PHI>0 book.

## §10 Number labels
§1 hashes: VERIFIED on pod2 2026-09-13 before this prereg was frozen. §0 prior numbers (trackA, r15, program P1/P4/P5): INFERRED here (quoted from their receipts). No κ estimate and no arm statistic existed when this document was frozen.
