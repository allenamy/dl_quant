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

## 6. Positive control on REAL data (pod2) — `devices/run_pod2_positive.sh`, log `receipts/pod2/pod2_run.log`

Isolated chain dir `/workspace/uplift_2026-09-11/r20_gate_closure/v4chain_PROPOSED2/` (= `v4_gate_common.py` `7b6d49a3…` + PROPOSED2 contract `01692565…`); the frozen `infra2/v4chain/` and every genuine artifact read only. Device shas on pod2 verified equal to local before launch (`d63f4ec3…`, `abc45cad…`). pod2 load 1.4–1.9 on 64 cores; protected PIDs 333197/339489 untouched (T state before and after). Python 3.11.10 / numpy 2.4.6 / scipy 1.17.1.

| Step | What | Result | Receipt (sha) |
|---|---|---|---|
| [1] | v2 gate on genuine **A1** (`/workspace/shadow_bundle_v4`, books under `review_scratch/health_check/dev_v4`) | **PASS**, all 11 checks ok, **28 inputs registered**, none missing a sha; E3 ICs 0.05444/0.06092/0.05732 (Δ −0.00036/−0.00208/+0.00022), E4 Sharpe 2.3044 (claimed 2.30); E6 cost json `9349ca63…` resolves to approved tiers, mask `47d87b51…`, king `dde19142…`; E8 A1 dyn s42 max devs K1 7.4e-9 / K2 9.5e-9 / K3 1.0e-8 / K4 0.0, gross_min_frozen 0.298, K7 0 violations; E9 ratios dyn [0.794, 1.254] / [0.842, 1.218], fix [0.980, 1.030] / [0.977, 1.026], 0 anchors outside band; 20 s | `BUNDLE_export_v2_A1.json` `d0e3cf41…` |
| [2] | v2 `require` on that receipt | **REQUIRE_OK** — identity `self d63f4ec3 approved, 28 inputs verified`; content re-run E0/E1/E2/E5–E9 all ok | `REQUIRE_v2_A1.json` `fe008d12…` |
| [3a] | real-data negative: a **copy** of the bundle with one finite prediction cell +1e-4; `require` the A1 receipt against the copy | **REQUIRE_FAIL** — `input 'bundle/slow_pred_pinned.npy' changed since the receipt: 0e92849a… != dde19142…`; content E1 mismatched | `REQUIRE_v2_A1_mutated_bundle.json` |
| [3b] | v2 gate on the mutated copy | **FAIL `E1_manifest`** only (E3's IC tolerance is blind to one cell; the closure is not) | `BUNDLE_export_v2_A1_mutated_bundle.json` |
| [4] | `gate_signal_parity_v2.py` for XIBLAG50 (panel `wide_panel_4h_v2ext.npz` = the device's; FEMAT `dev/sig/XIBLAG50.npz` `4ba4fe7d…`) | PASS, stats rows 10039 / NEW 0 / OLD 9031 / f32 0 (identical to the v1 receipt's numbers) + femat aligned, finite frac 0.3755; bound: `arm`, `self_sha256 abc45cad…`, `inputs_sha256{export_panel, femat}` | `S_BITWISE_signal_v2_XIBLAG50.json` |
| [5] | v2 gate on **XIBLAG50** (informational; unregistered arm; `JUDGE_HC=infra2/JHC` as INFRA2 used) | **FAIL `E9_gross_band_vs_baseline`** only: dyn s42 ratio max **2.101** (79 anchors > 1.6), dyn s2027 max 2.084 (87 anchors); fix cells inside band; E0–E8 all ok, E7 ok with the v2 signal receipt | `BUNDLE_export_v2_XIBLAG50.json` |
| [6] | ORIGINAL gate on genuine A1 (side-by-side) | PASS, 11 inputs, `self f814c728…` | `BUNDLE_export_ORIGINAL_A1.json` |

Reading of [5]: with the original gate XIBLAG50's receipt was PASS (INFRA2, 2026-09-11). Under v2 the same books fail one check — the gross profile of the dyn seat is up to 2.1× the in-service form's at ~80 of 3168 frozen anchors (F7: no registered-form arm exceeds 1.26). Whether that band is the right definition of "the same book form" is part of the ruling; it is a constant in the contract block, and the evidence for it is F7. It is not a verdict on XIBLAG50's alpha (that program is closed: `CLOSEOUT_uplift_program_2026-09-12.md`).

## 7. The proposed contract fill — `infra2/v4chain_PROPOSED2/`

- `ELIGIBILITY_CONTRACT.json` (sha `0169256597bc813e9f1425e399e4c3f22eaca5357f6dc1baeecf452a6e347329`) = frozen `3299dc97…` + `"status": "PROPOSED - NOT APPLIED - requires user ruling; see r20_gate_closure/RESULT"` + `gates.BUNDLE_export = {source: v4e_gate_export_v2.py, approved_source_sha256: [d63f4ec3…], approved_baseline: {…F9 shas, F10 tiers, 18 knob values, thresholds, signal_gates: {S_BITWISE_signal: [abc45cad…]}}}`; `rules[3]` reworded (its old sentence "BUNDLE_export is empty because the physical export gate does not exist yet" would have become false); `review_status` appended; `proposed_changes_vs_frozen` lists every change. **arms and book_binding untouched** (XIBLAG50 not registered). Built by `devices/make_proposed2_contract.py` — every repo sha computed, every pod2 sha a `sha256sum` reading re-verified by [1] above. Diff: `ELIGIBILITY_CONTRACT.PROPOSED2.diff` (131 ± lines, no escaping noise).
- `v4_gate_common.PROPOSED.diff` (companion, **not applied**, the frozen module is unchanged): extends `REQUIRED_INPUTS["BUNDLE_export"]` from 11 to 27 static names so that `judge_v4`'s own `_require` also demands the bundle closure / baseline books / cost / mask / king / contract. Without it, the judge verifies only the 11 + whatever the `JUDGE_ELIGIBILITY` caller declares (it still refuses a receipt from a non-approved source); the v2 gate's `require` mode enforces the full floor regardless. Ruling needed on whether to apply it (it changes a reviewed module; all other gates' floors are untouched by the diff).

## 8. What the v2 gate still cannot catch (explicit)

1. **A hand-edited receipt.** Receipts are unsigned JSON. `self_sha256`, `inputs_sha256`, `PASS` are strings anyone can rewrite to match mutated files; `v4_gate_common.require` compares strings. v2 narrows this: the `require` mode re-runs every content gate from the files, so a forged receipt still needs content-valid files, and E3/E4 can be forced to recompute (`REQUIRE_RECOMPUTE_GUARDS=1`). Closing it fully needs signing or the judge re-running the gate. (The reviewer's framing — staleness/binding, not adversarial forgery — is what v2 closes.)
2. **An ab-initio forged book that is internally consistent and inside the bands.** K1–K4 are exact identities on the shipped arrays; K6/K7/E9 bound the gross/cost profile. A book fabricated by re-running the device with an unregistered change that leaves the 27 knobs, the device sha string and the gross profile intact (e.g. a hand-patched `w10_health.py` that still *reports* `8684d9a9…`) is not detectable from the arrays — `HEALTH.device_sha256` is self-reported by the device. Only re-running the archived device on the same inputs would catch it; the device file itself is not a registered input because `JUDGE_HC` dirs do not all carry it (`infra2/JHC` has none).
3. **`FPRED` (the F10 prediction file) is recorded, not bound.** It is a relative name resolved in the device's cwd; the gate cannot locate it from `config_json`. `SLOW_NPY` (king) *is* bound by sha. Binding `FPRED` needs the device to write an absolute path or its sha.
4. **E3/E4 are not re-computed at `require` time by default.** They are sha-bound (every input in the floor), so a post-receipt mutation is caught by sha, not by re-derivation; a receipt whose E3/E4 were wrong at gate time would need a wrong gate source, which the approved-sha check excludes.
5. **"Sha spoofed to match while content differs" is impossible by construction** (a SHA-256 collision), *not* because of anything in v2; the realistic failure is item 1 (edit the receipt's recorded sha), not a collision.
6. **The gross band is a research choice.** [0.6, 1.6] per anchor admits every registered-form arm with ≥20 % margin (F7) and rejects XIBLAG50's dyn cells; a legitimate new form with a different gross profile would need the band re-ruled (it lives in the contract, i.e. re-approval, by design).
7. **The judge still hard-codes its loaded-arm tuple and contrast list** (INFRA2 `PROMOTION_CHECKLIST.json` "blocking_lines_outside_the_contract") — untouched here.
