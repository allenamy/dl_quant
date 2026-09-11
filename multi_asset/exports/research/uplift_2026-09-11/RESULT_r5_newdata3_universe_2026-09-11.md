> **创建:** 2026-09-11 | **Session:** round-5 NEW DATA 3 | **状态:** 判决完成, K=10 零录取; 交付 = 一份"刷新提案"而非一条新腿 | **作废条件:** v4 口径链作废, 或成员筛/宇宙文件改动

# RESULT — NEW DATA 3: the names the book cannot see

**Headline.** There is no third bet here. The excluded names are excluded because they are illiquid, and
adding them buys nothing (CI95 straddles zero in 8/8 cells). The listing-age sleeve looks good on the point
estimate and dies on every gate — most decisively, its rank-IC spectrum is FLAT across k = -3..+3, which makes
it a static exposure, not a forecast. **What this study DID find is a cost the book is currently paying: the
universe has been frozen since 2026-08-16 with no refresh mechanism in the code, and at v4 caliber and the
fitted cost the staleness curve on the LIVE seat runs 0.4841 (fresh) -> 0.342 (1 month) -> -0.021 (3 months)
-> -0.317 (6 months) -> -1.339 (12 months) Sharpe.** A monthly refresh costs essentially no turnover (the
names that leave carry 0.011% of gross on average). This is a repair, not an uplift.

## 0. Gate receipts (all VERIFIED, all run by me in this session)
| gate | result | file |
|---|---|---|
| GATE P (knobs-off bitwise vs archived V4_A0) | **PASS**, 4/4 cells, `d30_n2_c42_rec` (10039x23) and `_W` (10039x829), maxabs 0.0 | `r5_newdata3/GATE_P_r5nd.json` |
| device sha256 | `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` | same |
| G0 mask parity (my re-derivation from the PINNED holefix2 cache vs the pinned `_ext`-built masks) | **equal cell-for-cell** to `umask_UPIT.npz` AND, with the coin filter, to `umask_UPIT_CRYPTO.npz` | `mask_summary_r5.json` |
| A0 run parity (my mask + my driver vs round-4 `R4B1_A0_*`) | **bitwise on rec and W, 4/4 cells** | `run_univ.log` tail |
| FEMAT injection parity (`IB_PAR` = plain fund rank vs A0) | **bitwise on rec and W, 4/4 cells** | `run_sleeve_base.log` tail |
| A0 headline reproduction | n=9018, g 0.6890 bps, **Sharpe 1.4150**, SE 0.4928 (dyn seat, seed 42) — the brief's figure to 4 dp | `A0_headline_check.json` |
| concentration-ruler control | LIVE_FUND 2025on top-20 share **0.1109**, ex-top-20 Sharpe **+6.709** — reproduces round 3's 11.09% / +6.71 | `conc_r5.json` |

**ENV WHITELIST asserted (E-0826-D).** `LEGS, CAL, WRULE, LOOK, MEMBERS_TOPN, FTRIM, PHI, UMASK_SCOPE,
UMASK_NPZ, SLOW_NPY, FSEED, FPRED, COSTB_JSON, W3FIX (fix seat only), FEMAT_NPZ (sleeve arms only), OUT_TAG,
OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS.` Nothing else set; the device self-reports every knob
into `config_json` inside each arm npz.

**A caliber fact the brief's summary omits.** A0 = 1.4150 is the **dyn** seat. The **deployed** seat
(`W3FIX=0.21,0,0.79`) reads **0.4841** on the same full cycle, same cost. Every conclusion below is reported
on both, and the live-relevant one is the fix seat.

## 1. Exclusion mechanics — read out of the code, not the docs
`~/wide_shadow/shadow_loop_v3.py` (READ-ONLY; line numbers from the running file):

| step | line | what it does |
|---|---|---|
| data | 272 `for s in st.live` | 5m klines are fetched **only** for the 450 names in `symbols_live`. Every other column of the 829-wide cache stays NaN forever. |
| coverage gate | 305-306 | `coverage = cov_now/len(st.live)`; OK >= 0.95, DEGRADED >= 0.80, else skip the anchor. |
| member filter | 374-377 | `ok = (covr >= 0.95 over the last 2016 5m bars) & (7d vol >= 1e-4)`; if more than `NTOP=400` qualify, keep the **top 400 by mean log_qv over 2016 bars**. |
| liquidity gate | 473-474 | `sel = qv4h >= 2.5e5`, `qv4h = expm1(clip(qvm,0,30))*48`. |
| exit | 501-517 | out-of-universe, non-member and liquidity-failed names are force-flattened at `FORCED_EXIT_COST_BPS = 4.7`. |
| refresh | **none** | `self.live = cfg["symbols_live"]` at line 189 is the ONLY assignment. There is no code path that adds or removes a live name. |

**The 450 has not changed since it was frozen.** `shadow_bundle.aug20260816_backup/config.json`
(`built_utc 2026-08-16T13:03:59Z`) and the running `shadow_bundle/config.json` (`built_utc
2026-09-01T06:00:37Z`) have **identical** `symbols_live` (sorted-list sha256 `8aebc19d1e406f37`, and the pod's
`syms450.txt` matches it too). The 2026-09-01 monthly retrain replaced the booster and left the universe alone.
Frozen for **26 days** as of today, with no scheduled refresh.

**M1 (deployed 2026-09-04) did NOT fix this.** Lines 311-318 build `st.base` = venue TRADING USDT-perp union
`symbols_live`, and lines 415-418 use it **only** as the rank base for the fund leg (`xz_in_base`). The traded
set is untouched. Live log confirms: `base_n 530, fund_base_n 523, members 400, sel 243-261`.

### The enumeration (venue exchangeInfo fetched 2026-09-11 13:54:02Z, public endpoint, one request, 13:54Z is outside every anchor window)
- Venue lists **528** PERPETUAL / USDT / TRADING contracts (plus 190 `TRADIFI_PERPETUAL` tokenised equities the
  `contractType` filter correctly excludes, and 129 SETTLING).
- Book holds **450**; intersection **448**. **2 held names are now SETTLING: `SCRTUSDT`, `STORJUSDT`.**
- **80 venue names the book cannot trade**; 72 have v4 panel data, 8 do not
  (`哈基米USDT PONSUSDT MARSCOINUSDT 牛来USDT DOSUSDT 龙虾USDT 我踏马来了USDT 币安人生USDT`).
- Only **4** venue names onboarded since the freeze (2026-08-30 .. 09-06); none is in the 829 panel. The
  exclusion is therefore **not mainly a new-listing problem** — most of the 80 are 2020-2023 listings that
  failed the volume filter.
- **Of the 80, only 7 clear `qv4h >= 250k` at a majority of 2026 anchors** (`AXLUSDT SUPERUSDT MASKUSDT
  INITUSDT ANIMEUSDT WCTUSDT SOMIUSDT`). The rest could not be traded even if admitted.
- **The marginal names the book already holds: 170 of 450 (37.8%)** have a 2026 median `qv4h` below the 250k
  gate. They occupy universe slots and are never traded. (Caveat: names listed mid-2026 have a large number of
  zero-`log_qv` anchors, so a few of the "median 0" entries are listing artefacts, not dead names.)

## 2. What exclusion costs — v4 caliber, FITTED cost `costb_PWR_G230k.json`, FULL_pw n=9018
**Breadth buys nothing ON TOP OF M1.** Widening the *tradable* set from 449 to the venue's 529, or to 600,
with the fund-leg rank base already 829-wide (which is what `MEMBERS_TOPN=829 + UMASK_SCOPE=m1` means, and what
A0 already is since M1 shipped 2026-09-04):

| arm | dyn s42 dSharpe | dyn s2027 | fix s42 | fix s2027 | dg CI95 excludes 0? |
|---|---|---|---|---|---|
| WIDE529 | -0.047 | -0.015 | +0.010 | +0.005 | **no, 0/8 cells** |
| WIDE600 | -0.045 | -0.021 | +0.001 | -0.001 | **no, 0/8 cells** |

**Reconciliation with `docs/RESULT_universe_dyn_2026-09-04.md` (REQUIRED: a new result that looks opposed to a
receipted one gets reconciled before it is reported).** That campaign found N600/N829 worth **+0.10 to +0.11
Sharpe, CI>0, double seed, double caliber** — and decomposed it itself: "变宽只作用于 fund 腿的秩映射",
with the **extra tradable names contributing only +0.02 to +0.03**. Its control was `N400r` = a 400-wide rank
base. **My baseline is not that control.** A0 already carries the market-wide rank base — that is exactly what
M1 deployed on 2026-09-04 — so the +0.06..+0.085 rank-base channel is already inside my A0, and the only thing
WIDE529/WIDE600 can add is the extra-tradable-names channel their own table prices at +0.02..+0.03. My
measurement (-0.03 to +0.005, CI95 width ~0.13) is **consistent with +0.02..+0.03**, not opposed to it. The two
instruments agree. The correct statement is: **the rank-base widening was the whole prize and it has already
shipped; trading the extra names is the small remainder and this study cannot resolve it from zero.**

The same campaign's age-gate row is an independent replication of my §4 finding: it read A30 -0.149/-0.166 and
A60 -0.246/-0.303 (CI excludes 0), i.e. excluding young names costs Sharpe. My `NOYOUNG90` reads **dSharpe -0.390/-0.383**
on the fix seat (dg -0.193/-0.191, CI95 [-0.365,-0.035] / [-0.364,-0.028], excludes 0). **Two devices, two
lineages (v3 `w10_universe.py` vs v4 `w10_sleeve.py`), same sign and the same order of magnitude.**

*Caveat on "already inside A0":* the replay's rank base is the full 829-name panel, while live M1's is
`venue TRADING ∪ live` = 530 names (live log `fund_base_n 523`). The replay therefore carries a slightly WIDER
rank base than production. That makes my WIDE arms a conservative test of the extra-names channel and leaves a
real, unmeasured 530-vs-829 gap between production and this replay.

**Staleness is what costs.** `STALE_L` = at every anchor use the top-449 selection made L calendar months
earlier (L=0 is A0). FULL_pw Sharpe:

| arm | dyn s42 | dyn s2027 | **fix s42 (live seat)** | fix s2027 | fix s42 dg CI95 |
|---|---|---|---|---|---|
| A0 (monthly) | 1.4150 | 1.4370 | **0.4841** | 0.4848 | — |
| STALE1 | 1.2234 | 1.3128 | **0.3420** | 0.2787 | [-0.201, +0.059] |
| STALE3 | 1.0539 | 1.1156 | **-0.0214** | -0.0423 | **[-0.471, -0.017]** |
| STALE6 | 0.9588 | 1.0004 | **-0.3174** | -0.3161 | **[-0.650, -0.091]** |
| STALE12 | 0.3625 | 0.4067 | **-1.3393** | -1.3251 | **[-1.218, -0.407]** |
| QTR449 (block hold) | 1.3369 | 1.3709 | 0.3035 | 0.2931 | [-0.233, +0.048] |
| ANN449 (block hold) | 1.3263 | 1.3429 | -0.2083 | -0.2013 | **[-0.588, -0.068]** |

Monotone in L, in every cell, on both seats, both seeds. **The deployed (fix) seat is far more sensitive than
the dyn seat** — the frozen-universe cost lands hardest on exactly the configuration that is live.
`STALE12` clears the Bonferroni CI99.5 bar on the fix seat ([-1.376, -0.187]); `STALE3` and `STALE6` clear
CI95 but not CI99.5.

**Against the v3 receipts.** `docs/AUDIT_live_vs_replay_2026-09-04.md` row 2 said monthly -8% / quarterly -43%
of Sharpe on 2023+, and `docs/RESULT_universe_dyn_2026-09-04.md` priced the cadence at monthly -0.06..-0.09,
quarterly -0.29..-0.34, annual -0.47..-0.56 Sharpe. My block-hold arms on the fix seat read quarterly
**-0.172/-0.183** and annual **-0.683/-0.677** dSharpe: same sign, same ordering, quarterly milder and annual
harsher, on a different span (2022+ vs 2023+), a different caliber (v4 vs v3) and a different cost (fitted vs
scenario b). No reversal. Redone at v4 and the fitted cost on the LIVE seat, 2024on: A0 1.0271 -> STALE1 0.7754
(-24.5%) -> STALE3 0.3634 (-64.6%) -> STALE6 -0.0503 -> STALE12 -1.5617. **The v4 redo makes the cost bigger,
not smaller.**

**The trap I pre-declared, confirmed.** `UFROZEN450` — the actual live 450-name list projected back over the
whole history — reads **BETTER** than A0 (dg +0.225 to +0.462, dyn s2027 CI95 [0.056, 0.723]). That is pure
look-ahead: the 450 names alive and liquid in August 2026 are the survivors. Anyone who reads "the frozen list
beats the dynamic one" off this number has measured survivorship, not membership. It is an upper bound and
nothing else.

**Refresh turnover cost (measured, not assumed).** Month-over-month, the names that drop out of the top-449
carry a mean **0.011%** of book gross (max 0.30%) at the last anchor of the month they leave — at the tier-2
forced-exit rate of 4.7 bps that is below 0.001 bps/anchor. Meanwhile **staleness RAISES turnover**: fix-seat
mean turnover A0 0.0160 -> STALE3 0.0180 -> STALE6 0.0198 -> STALE12 0.0231, because a stale roster keeps
force-flattening names that have fallen through the liquidity gate. **A monthly refresh is turnover-negative.**

**Churn is accelerating**: names entering/leaving the top-449 per month averaged 0.5 (2023), 2.2 (2024),
12.2 (2025), **51.3 (2026)**. The list ages ~11% per month now versus ~0.5% in 2024.

## 3. New listings specifically — the receipt does not reproduce, and the sleeve dies
`young_listings_carry_fund_alpha` claims the fund leg's IC on names listed < 90 days is 3-4x the mature
universe (2026 +0.086 vs +0.024) and deep-negative funding is 3x as common. Measured on the **device's own
evaluation grid** with the A0 member set and the live liquidity gate (`age_profile.json`):

| year | bucket | names/anchor | median qv4h | deep-neg (<= -10bp/8h) share | fund rank-IC in bucket |
|---|---|---|---|---|---|
| 2026 | <90d | 9.9 | $1.01M | 5.16% | **+0.0044** |
| 2026 | >2y | 117.1 | $1.24M | 3.32% | **+0.0163** |
| 2025 | <90d | 27.7 | $1.67M | **5.38%** | +0.0080 |
| 2025 | >2y | 137.8 | $1.43M | **1.65%** | +0.0130 |

The **deep-negative funding concentration is real in 2025 (3.3x)** and weaker in 2026 (1.55x). The **IC claim
does not reproduce**: young names carry LOWER fund IC than mature ones in 2025 and 2026 on this grid. The
receipt was measured on the jpline B panel with a different qualification rule and reported ICs an order of
magnitude larger than anything the device grid produces; the two are not the same quantity. Caveat on my own
number: with ~10 young names per anchor the within-bucket IC is measured only on the 574 of 1433 2026 anchors
where the bucket had >= 10 scorable names, and it is noisy.

**Sleeve arms (in-book FEMAT injection, A0's exact config otherwise):**

| arm | dyn s42 Sharpe | dSharpe | dg | dg CI95 | 4/4 cells above 0? |
|---|---|---|---|---|---|
| SL_AGE25 (0.75 ZF + 0.25 young) | 1.5074 | +0.092 | +0.053 | [-0.082, +0.177] | no |
| **SL_AGE50 (0.50 / 0.50)** | **1.7172** | **+0.302** | **+0.195** | **[-0.104, +0.485]** | **no — 0/4** |
| SL_AGEMOD50 (ZF x (1+0.5 AY)) | 1.3919 | -0.023 | -0.007 | [-0.074, +0.063] | no |
| SL_AGEMOD100 (a=1.0) | 1.4254 | +0.010 | +0.010 | [-0.088, +0.104] | no |

SL_AGE50 is the best thing in this study and it fails on four independent grounds:

1. **Paired CI.** dg CI95 contains zero in 4/4 cells; Bonferroni CI99.5 is nowhere near.
2. **Turnover-matched nulls (`JUDGE_nulls_r5.json`).** `beats all nulls on g: False` in **4/4 cells**
   (and on `pnl_ex` in 3/4). The killer is `SHIFT101`: shifting the age matrix 101 anchors (~17 days) barely
   changes it, and the shifted copy **beats** the arm (dyn s42 dg -0.0131, CI95 [-0.0249, -0.0011]). An arm
   that cannot beat a time-shifted copy of itself is carrying an exposure, not a forecast.
   `SL_AGEMOD100` beats all six nulls on g in the 2 dyn cells and fails in both fix cells (again to
   `SHIFT101`), so it too misses the 4/4 requirement — and its dg vs A0 was only +0.010..+0.038 anyway.
3. **Forward vs backward rank-IC at k = -3..+3** (`collin_r5.json`). The age signal:
   `-0.02120, -0.02127, -0.02143, -0.02149, -0.02143, -0.02138, -0.02134`. **Flat to 3 decimal places, with no
   forward peak.** Compare the book's own fund leg (`+0.00542, +0.00464, +0.00573, +0.00788, +0.00746, +0.00702,
   +0.00680` — peaks at k=0/+1, forward > backward) and Amihud (`+0.00416, +0.01353, +0.02532, +0.01178,
   +0.01487, +0.01484, +0.01345` — peaks BACKWARD at k=-1, backward/forward 1.70).
4. **Tail concentration** (`conc_r5.json`, ruler verbatim from `r3_gates/rs_conc.py`). Pure age signal, 2025on:
   top-20 share **220.3%** of the leg return, **ex-top-20 Sharpe -2.757** — the RESID_SHARPE death signature
   (130-189% / -2.40). The SL_AGE50 blend reads 67.2% / +1.406, still far from the live fund leg's 11.09% / +6.709.

**Standalone** (`LEGS=001, PHI=0`): the age signal as its own fund-slot leg reads Sharpe 0.2992 (dyn) / 0.6143
(fix) on the full cycle, with turnover 0.0019-0.0032 — a near-static book. Its own RELAB1 null reads 0.5421
(dyn) / 0.8201 (fix): **the null beats it on both seats.**

**Not new information anyway.** rho of SL_AGE50's per-anchor g to A0 = 0.840/0.818; to the round-4 XIB arm =
0.804/0.689. Cross-sectionally, rank(young) vs rank(Amihud) rose from 0.049 (2022) to **0.242 (2026)**, and
rank(young) vs rank(fund EMA) to **0.308 (2026)**. The young tilt is increasingly the illiquidity tilt the
round-4 sleeve already measured.

**Capacity.** `MIN_NOTIONAL` is $5 for all 80 excluded names (the book's own 450 carry $5/$20/$50). At USD 230k
gross across 258 traded names the mean per-name notional is **$891**; at 600k **$2,326**; at 1M **$3,876**. The
min-notional floor is therefore NOT the binding constraint at any of the three gross levels. The binding
constraint is the liquidity gate: only 7 of the 80 clear 250k qv4h at a majority of 2026 anchors.

## 4. The opposite tail — there is no admissible "drop names" change either
Live state, read from the executor (READ-ONLY): `state/live/per_name_stop.json` has **1 permanently stopped
name (IOSTUSDT)** and 10 in cooldown; the 12Z 2026-09-11 reshape record shows `n_popped 12`
(incl. BTCUSDT, 1000SHIBUSDT), `names_crossed_floor ["IOSTUSDT","KSMUSDT"]`, and the shadow log's last 12
anchors show `forced_exit_n` 0-2 at gross 0.0008-0.0095 (121-anchor mean 5.04 names / 0.0077 gross).

Replay verdict on tightening:
- `DROPTAIL399` (drop the bottom 50 members by trailing volume each month): dg -0.024 .. -0.087, CI95 straddles
  zero in 8/8 cells. Buys nothing, mildly negative.
- `NOYOUNG90` (drop names younger than 90 days): dg **-0.161 to -0.311**, CI95 **excludes zero on the fix seat**
  ([-0.365, -0.035] s42 FULL_pw). Dropping young names **hurts**. Whatever the receipt got wrong about the IC,
  it was right that the young cohort is not dead weight.

## 5. Verdict against the declared K
**K = 10 declared before the fact** (8 in the PREREG, 2 added by AMENDMENT 1 before any sleeve number was read),
Bonferroni alpha 0.005, admission = paired two-sided CI99.5 excluding zero in the arm's favour in all four cells
plus the full battery. **Admitted: 0 of 10.** H1/H2 (breadth) null; H3/H4 (cadence) are costs, not gains;
H5/H6/H9/H10 (age sleeve) fail the nulls, the spectrum and the concentration ruler; H7/H8 (tightening) lose.

## 6. Deliverable — the membership-refresh proposal
See `PROPOSED_membership_refresh_2026-09-11.md`. In one line: this is a **repair with a measured cost of doing
nothing and an unmeasurably small cost of acting**, not a new bet, and it is the user's call.
