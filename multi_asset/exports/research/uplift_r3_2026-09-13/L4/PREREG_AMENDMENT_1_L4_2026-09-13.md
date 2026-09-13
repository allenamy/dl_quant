> **创建:** 2026-09-13 11:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker L4) | **状态:** AMENDMENT 1 to `PREREG_L4_carry_sleeve_hysteresis_2026-09-13.md` (sha256 ced2f73f…, frozen 11:24:12Z, commit deb3af82); written before any real-data computation (neither `l4_build.py` nor `l4_run.py` has run on pod2; no input array has been read by an L4 device) | **作废条件:** same as the PREREG

# PREREG AMENDMENT 1 · L4 · entry must not admit a name the forced-exit rule would eject

## What was found, and how
Local smoke test of the uncommitted run device, synthetic worlds only (`G-SYN`, PREREG §6; scratch copy that stops before any real input is loaded). World S3 plants a name whose funding events stop at window 100 while it stays eligible, spot-tradable and marked. Under the PREREG text (§2.6), and identically in the independent pure-Python reference implementation, arm A01 exits it by forced rule (b) at anchor 106 and **re-enters at 107**, exits at 108, re-enters at 109 … (forced-(b) exits at 106/108/110/112/114) until its EMA falls below h_in. Cause: §2.6 step 4 (entry) does not check condition (b) of step 2, so the entry rule re-admits a name that the forced-exit rule ejects; every cycle is charged a full round trip. Conditions (a) and (c) do not have this problem (entry already requires spot tradable and a finite premium at E_i).

## Change (the only one)
§2.6 step 4, entry candidates, add: **Σ NEV[i−6…i−1, k] > 0** (at least one funding event for the name in (E_i − 24h, E_i]).

§6 G-SYN, add: in world S3 arm A01 must show exactly one hold, closed by forced rule (b), and no re-entry.

Nothing else changes: arms, thresholds, costs, basis, spot rule, readings, pass rule, verdict, gates and inputs are as frozen. Reason for acting now rather than reporting: in real data a funding-record gap on a still-eligible perp (the pre-freeze fund_aug spacing scan, PREREG §1, showed a few gaps of 504 h to 18,052 h) would turn this into repeated round trips charged to the sleeve by a specification slip, not by the strategy.
