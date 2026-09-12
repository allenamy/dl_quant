> **创建:** 2026-09-12 | **Session:** r20-gate-closure (research-chain engineer, branch `research/book-uplift-2026-09-11`) | **状态:** final — PROPOSED, NOT APPLIED; awaits user ruling | **作废条件:** `infra2/v4e_gate_export_v2.py` / `infra2/gate_signal_parity_v2.py` / `v4_chain_2026-09-09/v4_gate_common.py` / the frozen contract change sha; or a new counter-example passes the v2 gate (then re-run `devices/test_matrix_v2.py` with it added)

# r20 — Closing the export-gate falsifiability gap (N1)

**One line.** The INFRA2 export gate (`infra2/v4e_gate_export.py`, sha `f814c728…`) that I had recommended approving into `ELIGIBILITY_CONTRACT.gates.BUNDLE_export` is not falsifiable: the reviewer's six probes reproduce exactly (§2). A replacement `v4e_gate_export_v2.py` (sha `d63f4ec3…`) plus a companion bound signal gate is proposed; on an isolated synthetic world it passes 2 positives and fails every one of 30 negatives with the failing check named (§5); on pod2 the genuine A1 bundle + A1 books pass it end-to-end (gate + require) and a one-cell mutation of a *copy* of the shipped predictions fails it (§6). The proposed contract fill is `infra2/v4chain_PROPOSED2/ELIGIBILITY_CONTRACT.json` (§7). Nothing frozen or live was written.

Scope discipline: only `uplift_2026-09-11/infra2/` (new files) and `uplift_2026-09-11/r20_gate_closure/` (new) were written locally; on pod2 only the new dir `/workspace/uplift_2026-09-11/r20_gate_closure/`. `~/dl_quant_live`, `~/wide_shadow`, `infra2/v4chain/*`, `/workspace/shadow_bundle_v4/*` and every judged book were read only. XIBLAG50 stays unregistered (arms block untouched).

## 1. Fact table (all VERIFIED this session by recompute unless marked)

| # | Fact | How verified |
|---|---|---|
| F1 | Original gate sha `f814c728938482b876cbcaa31f200832d207a0f89387d58ed3e2d0d45448e214` identical in research repo, on pod2 (`/workspace/uplift_2026-09-11/infra2/v4e_gate_export.py`) and in the reviewer's `sources/04_…` | `shasum`/`sha256sum` ×3 |
| F2 | `v4_gate_common.py` `7b6d49a3…`, frozen contract `3299dc97…` — identical local / pod2 (`infra2/v4chain/`) / reviewer sources | same |
| F3 | `REQUIRED_INPUTS["BUNDLE_export"]` = 11 names (7 upstream + 4 books); no shipped bundle file, no FEMAT, no signal receipt, no cost json, no mask | read `v4_gate_common.py` L48 |
| F4 | Original E5/E6 pin 8 of the device's 27 config knobs (`PINNED_BOOK_ENV`), check shapes + finiteness of W only; E7 reads `sig.get("PASS") is True` | read gate L67, L210-238 |
| F5 | Device (`w10_health.py` sha `8684d9a9…`, 5 archived copies in repo, = pod2 file) writes `config_json` with exactly 27 keys (`_CFG`, L51-54); FTRIM threshold −0.0010 is **hard-coded** (L207/252) — the reviewer's `FTRIM_TH` is not a device key; its binding is the device sha | read device |
| F6 | Genuine books (A0/A1/A3/XIBLAG50, both seats/seeds, pod2): `net = pnl − carry − cost` and `net_ex = pnl_ex − carry_ex − cost_ex` exactly (max dev 0.0); `Σ|W_t| = gross_total_t` ≤ 7.5e-9; `Σ|W_t − W_{t−1}| = turnover_t` (row 0: `Σ|W_0|`) ≤ 9.5e-9; `ΣW_t/Σ|W_t| = netlong_t` ≤ 1.4e-8; all rec finite; gross_total ∈ (0.096, 0.985] over history | pod2 python, 5 books + 4 for identities |
| F7 | Per-anchor gross ratio arm/A0 (same seat, seed), frozen window, 7 registered-form arms × 4 cells: min 0.766 (A1e dyn s42), max 1.258 (A1s dyn s42), medians 0.9665–1.021. XIBLAG50/XIBOLD50 dyn: max 2.10 | pod2 python, 40 cells |
| F8 | cost > 0 and cost_ex > 0 on every frozen anchor of all 40 cells; `cost ≤ turnover × max tier rate (2.20213)` with 0 violations | same |
| F9 | Approved-baseline shas (pod2 `sha256sum`): costb_fee_steady.json `9349ca63…`, umask_UPIT_CRYPTO.npz `47d87b51…`, live_pins.json `fd27fe48…`, slow_scorer_v4base.json `dce6a228…`, A0 books dyn_s42 `88283c5f…` / dyn_s2027 `6b40d13d…` / fix_s42 `a110c5b0…` / fix_s2027 `bbba0d78…` (identical under `health_check/dev_v4` and `infra2/JHC/dev_v4`) | pod2 `sha256sum`; re-verified by the v2 gate E0/E2b/E6/E9 in §6 |
| F10 | Genuine COST_B in every A0/A1/A1s/A1e/A2/A3 book = `[[1.8001,4.5001,0.8511],[1.799,4.4988,0.9246],[1.7998,4.5002,0.921]]`; the reviewer's fixture used `[[2,5,.8]]×3` (the original gate never read it) | pod2 config_json |
| F11 | `GATE_signal_parity.json` (sha `3941268b…`) has no `self_sha256`, `arm` or `inputs_sha256`; `gate_signal_parity.py` (`19b7419f…`) does not call `finalize` | read both |
| F12 | The reviewer's fixtures lived in `tempfile.TemporaryDirectory` (gone); their method is fully specified in `probe_export_gate.py` | read script; `ls contracts/fixture_*` → none |

## 2. Step 1 — the six reviewer probes reproduced against the ORIGINAL gate

Device `devices/probe_original_gate.py` (E5/E6/E7 block of the original exec'd verbatim; real `v4_gate_common.require` against an isolated contract copy approving `f814c728`). Receipt `receipts/RECEIPT_probe_original_gate.json`, `ALL_REPRODUCED: true`.

| Probe | Reviewer (E5/E6, E7) | Ours (E5/E6, E7) | Reproduced |
|---|---|---|---|
| positive_shape_control | ok, ok | ok, ok | yes |
| bare_PASS_wrong_signal_gate | ok, **ok** | ok, **ok** | yes — a PASS from `NOT_A_SIGNAL_GATE` accepted |
| signal_FAIL_negative_control | ok, fail | ok, fail | yes — E5/E6 still ok while the signal gate fails |
| different_cost_and_ftrim_accepted | **ok**, ok | **ok**, ok | yes — COST_B all-zero + injected knob accepted |
| bad_fixed_PIN_negative_control (PHI 0.99) | fail, ok | fail, ok | yes — the one check that works |
| zero_W_and_infinite_pnl_accepted | **ok**, ok | **ok**, ok | yes — all-zero W, `net_ex = inf` accepted |
| unbound_shipped_bundle (require) | PASS, PASS after pred→NaN, FAIL after registered input | same | yes — the shipped prediction is unbound |

## 3. What v2 binds, and why each check is an identity rather than a word

`infra2/v4e_gate_export_v2.py` (sha `d63f4ec3f9e657259c2d4826f95552007f34eb63eab1d67357d8ad5b54cd5c1e`). E1–E4 are the original's code verbatim (band / N_FROZEN / IC tolerances now read from the contract block; env overrides refused). New or rebuilt:

| Check | What it binds | Fails when |
|---|---|---|
| **E0_contract_baseline** | the contract's `gates.BUNDLE_export.approved_baseline` block (device sha, cost json sha + tiers, mask sha, live_pins sha, bundle_base sha, A0 book shas, all 18 value-pinned knobs, every threshold, approved signal gates) is present and well-formed; the block itself is a registered input (`eligibility_contract`) | block missing/malformed → **refuse rc=2**; `BUNDLE_GUARD_LO/HI`, `JUDGE_N_FROZEN` in env ≠ contract → refuse |
| **E1_manifest** (a) | MANIFEST closure; **every listed file registered as `bundle/<f>`** so `require` re-hashes the exported predictions/model/config/ledgers | mismatch, missing, unlisted file |
| **E2_config / E2b_pins_identity** (d) | config parity as before **+ `LIVE_PINS` and `BUNDLE_BASE` must hash to the approved shas** (the reviewer: they were the caller's choice) | any byte differs, even with equal content |
| E3 / E4 | verbatim re-derivation of the three exporter guards from the shipped `slow_pred_pinned.npy` | as before |
| **E5_books_shape** | + every rec value finite; symbols identical across the 4 books **and equal to the approved baseline books'**; strict 4h grid over the whole history | NaN/inf anywhere, relabelled symbol axis |
| **E6_books_config** (c) | `config_json` key set **exactly** the device's 27 keys; **all 18 value knobs** pinned (not 8); `W3FIX`/`FSEED` per cell; `HEALTH.device_sha256`; `COST_B` tiers == approved; `COSTB_JSON`/`UMASK_NPZ`/`SLOW_NPY`/`FEMAT_NPZ` one value across the 4 cells, exist, **registered as inputs**, cost json and mask **sha == approved**, cost json **resolves to the approved tiers** | injected key, changed knob, different cost/mask file (even same content), seed/seat relabel |
| **E7_signal_receipt** (b) | if any book injected a FEMAT: receipt exists (registered), `gate` ∈ approved signal gates, `self_sha256` ∈ approved sources, `arm` == this arm, `inputs_sha256.femat` == sha(FEMAT on disk now), recorded `thresholds` == approved, **PASS re-derived from recorded stats vs thresholds** (the word `PASS` is not read as evidence). No FEMAT → not applicable, stated | wrong gate, unbound receipt, other arm, mutated FEMAT, stats that violate thresholds under a `PASS: true` |
| **E8_books_content** | the four device identities of F6 to 1e-6 / 1e-9 (K1 Σ|W|=gross, K2 turnover=Σ|ΔW|, K3 netlong, K4 net identities), K6 `0 < gross ≤ 1`, K7 cost>0 & cost_ex>0 on the frozen window and `cost ≤ turnover·rate_max` | zero W, tampered W row, zero cost, inconsistent rec |
| **E9_gross_band_vs_baseline** (d) | approved A0 books hash to the contract; per-anchor `gross(arm)/gross(A0)` ∈ [0.6, 1.6] and median ∈ [0.8, 1.25] (evidence F7) | baseline swapped, self-consistent ×2 forgery, a book form with a different gross profile |

**`require` mode** (`python v4e_gate_export_v2.py require <receipt>` with the same env): derives every path from env + contract exactly as gate mode (the receipt is never a path source), calls `v4_gate_common.require` over the **full floor** (28 inputs for A1: 7 upstream + 4 books + 4 baseline + manifest + 8 bundle files + costb + umask + slow_npy + contract; +femat, +signal_receipt when injected) with the pinned v2 sha, **and re-runs E0/E1/E2/E5–E9 from the files**. E3/E4 are sha-bound (their inputs are all in the floor) and recomputed only with `REQUIRE_RECOMPUTE_GUARDS=1`.

**Companion** `infra2/gate_signal_parity_v2.py` (sha `abc45cad806c22d717d4924869b34d8e127dbe8e61fec07c00008e5df52a3ed0`): the v1 statistic verbatim + FEMAT alignment, written through `finalize` with `arm`, `stats`, `thresholds`, `inputs_sha256{export_panel, femat}` — the receipt shape E7 demands. (F11: no v1 receipt can satisfy E7.)

## 4. Caliber of the content checks

Pinned book conventions (`CALIBER_PIN_v4_2026-09-11.md` §3): `g = net_ex/gross_total`; the identity `net_ex = pnl_ex − carry_ex − cost_ex` is exact in the device (`rec.append(... float(pnl_r - car_r - cbps_r), pnl_r, car_r, float(cbps_r) ...)`, L327) and is checked at 1e-9. Tolerances for the W-derived identities (1e-6) are 60–130× the observed float32-storage deviations (F6). The gross band constants are evidence-based (F7), not chosen to admit anything in particular; the arm that would fail them (XIBLAG50, 2.10) is reported in §6, not hidden.
