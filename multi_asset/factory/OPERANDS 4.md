# Factory — operand whitelist + operator signatures (proposer reference)

Write formulas as nested function calls, e.g. `where(gt(rvol_24h, 0), king, sub(king, s2))`. A wrong
name fails the parser (wastes a parse, not an `M` slot). Depth ≤ 6, operators ≤ 12.

## Operands

**DENSE channels (27)** — defined at every hour; the ONLY operands temporal operators accept:
```
funding_ema  mom_4h  mom_8h  mom_24h  mom_72h  mom_168h  rev_1h  rev_3h
rvol_24h  dvol_24h  rvol_72h  dvol_72h  beta_24h  beta_72h  lturnover_24h  illiq_72h
size_dvol  max_ret_24h  gtja_046  a101_044  ret_1h  ret_4h  ret_12h  ret_24h
rvol_6h  logqvol  betaadj_ret24
```
(`xsr_*` are intentionally removed — use `xsec_rank(...)` to express cross-section explicitly.)

**SPARSE leg columns (4)** — the four book legs; defined only at anchors. Admissible ONLY into
pointwise / cross-sectional / conditional operators (NEVER temporal — the type system rejects that):
```
king          # 4h residual-reversal OOS prediction
s2            # 24h slow-factor OOS prediction
funding_leg   # the funding leg signal = -1 * xsec_rank(funding_ema)
size_leg      # the SIZE leg signal   = xsec_z(size_dvol)
```

**Constants**: bare numbers for windows / powers / thresholds / bounds, e.g. `24`, `0.5`, `-3`.

## Operators (one-line signatures)

**temporal — DENSE series only; trailing window [t−n+1, t]** (`n` = a constant window/span):
```
ts_delta(x, n)      x_t − x_{t−n}
ts_mean(x, n)       trailing mean over n
ts_std(x, n)        trailing std over n
ts_zscore(x, n)     (x − ts_mean)/ts_std
ema(x, span)        causal EMA (adjust=False)
ts_rank(x, n)       rank of x_t within its trailing-n window, centered to [−0.5, 0.5]
ts_corr(x, y, n)    trailing Pearson corr of x,y over n  (x,y both DENSE)
ts_min(x, n)        trailing min
ts_max(x, n)        trailing max
decay_linear(x, n)  linearly-weighted trailing mean
```
**cross-sectional — any series; per-anchor over the member cross-section:**
```
xsec_rank(x)        pct-rank across coins at t, centered to [−0.5, 0.5]
xsec_z(x)           (x − xsec_mean)/xsec_std at t
xsec_demean(x)      x − xsec_mean at t
```
**pointwise — any series; a scalar constant may stand in for b/thresholds (broadcast):**
```
add(a, b)  sub(a, b)  mul(a, b)  div(a, b)   neg(x)  abs(x)  sign(x)  log1p_safe(x)  power(x, p)
```
**conditional:**
```
where(cond, a, b)   a where cond>0 else b
gt(a, b)  lt(a, b)  boolean masks
clip(x, lo, hi)     winsorize to [lo, hi]
```

## Notes for writing a batch
- The factory's unique space is **conditioning/combining on the legs** — e.g. `where(lt(rvol_24h, 0),
  king, s2)`, `mul(king, sign(sub(funding_leg, 0)))`. Raw-channel-only compositions are welcome too but
  overlap more with what the book already captures.
- Credit is scored on the king+S2-orthogonalized target (`YR4B`/`YR24B`), so a formula that is just a
  re-scaling of a leg (pred-corr ≥ 0.70 to king/S2/funding/size) is auto-rejected as redundant.
- Windows: prefer the panel's native scales `{4, 8, 12, 24, 72, 168}`; `ts_rank`/`ts_corr` want n ≥ ~12
  to avoid degenerate windows (which return NaN and are excluded).
