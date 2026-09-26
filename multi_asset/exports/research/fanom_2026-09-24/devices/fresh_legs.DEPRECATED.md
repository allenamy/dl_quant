# `fresh_legs.py` — RETIRED 2026-09-25. Do not use for any new reading.

**The file itself is deliberately left byte-identical** to what the FRESH training receipts pin
(sha256 `97077d7e890223a966ed190ff4a1d6ff…`). Enforcement lives outside it — see "How this is enforced".

## Why it is retired

`fresh_legs.py` **L80-81** computes the combo kernel's `RN8` from `fund_replay.npz`:

```python
lr_ = fr["last_rate"][i, m]; li_ = fr["last_iv"][i, m]   # combo_stage L266-273 rn8 (ledger tail, no freshness)
iv = np.where(np.isfinite(li_) & (li_ > 0), li_, 8.0)
RN8[i, m] = np.where(np.isfinite(lr_), lr_ * (8.0 / iv), np.nan)
```

`fund_replay.npz` is contaminated. Root cause (`FA_RN8CENSUS.json`, commit `9f9c8ac96`; news2 `2b87e8546`):

* the producer block the replay compiles (`shadow_loop_v3.py` as pinned, sha `6080073964`) **skips the fetch**
  when `anchor - last_ts < exp_iv*3600*0.9`. The LIVE producer (`52baf979`) L633-634 guards that same line with
  `not _bulk_ok` — *"NC A4: under bulk, never skip on the predicted interval"*. The pinned copy predates the guard
  and contains **zero** occurrences of `_bulk_ok`;
* in the replay that block is the **sole populator** of `led` (cold start), so the gate self-locks: once a name is
  recorded at `iv=8` it is not looked at again for 7.2 h, and every 1 h spike settlement is skipped;
* news2 measured the consequence independently on their own population: `STALE_ASOF` **5,613/5,613 = 100%**,
  median lag **9 days**, max **946 days**.

**Effect versus the clean NC legs**, measured: **639** cells not identical (404 both-finite-differing + 235
NaN-vs-value), **43 sign flips**, 358 of the differing cells in 2026. Clamp-eligibility flips **64**, of which
**48 (75%)** come from the NaN-vs-value cells. TLMUSDT 2026-03-02: truth `+0.0001`, this path `−0.02`.

## Use instead

`/dev/shm/news2_2026-09-23/work/legs.npz` (sha `9ee5886f37d1727c…`) — **read** its `RN8`; do not re-derive the
rule. Its RN8 is bitwise equal to the exchange archive on every adjudicated diagnostic cell, and the parity
control (`FA_RN8PARITY.json`) matched rate / interval / RN8 on all 13 comparable cells, the rate in float64.

Lead ruling 2026-09-25: the replay is **not fixed, it is retired**; research uses NC legs only.

## How this is enforced (and why not in the file)

An earlier version of this deprecation put a `raise` at the top of `main()`. That changed the file's bytes, and
`fa_ladder.py` **L206** (`assert sha(p) == h, ('training source drift', p)`) then correctly refused to build any
FRESH-rooted arm, because the FRESH training receipt pins this file's sha. **A pinned source file must not be
edited in place** — the pin exists precisely so that editing it is visible. Lead ruling 2026-09-26 moved
enforcement out:

1. this sidecar;
2. `test_no_fresh_legs_callers.py` — asserts no device in this suite imports it or invokes it as a subprocess,
   with a red control that plants a caller and requires the test to fail;
3. `news_p2_build.py`, the other path that consumed `fund_replay.npz`, refuses via `require_clean_fund_replay`
   with **no** `allow` argument.

Retirement guards against the file being **run**, not against it being **hashed**.
