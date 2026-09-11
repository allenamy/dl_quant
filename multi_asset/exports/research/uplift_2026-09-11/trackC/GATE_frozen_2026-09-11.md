# TRACK C — FROZEN ACCEPTANCE GATE (written BEFORE any controller number was computed)

Written 2026-09-11, Track C agent. Instrument: w10_ablation_series_pod_live_w3fix_callog_s42.npz,
arm d30_n2_c42, u = net_ex/gross_total (bps per unit gross per anchor, live caliber, CAL=log,
W3FIX 0.21/0/0.79, FTRIM=zero, PHI=0.45, MEMBERS_TOPN 829, TRADE_TOPN 400, LOOK 900).
Sample 2022-01-31 .. 2026-08-30, 10038 anchors. Baseline g=1 always.

A controller is ADMITTED only if ALL of the following hold on the FULL sample, walk-forward,
with every input strictly trailing (signal known at anchor t-1 applied to anchor t's return):

G1  LEAD, not LAG. For the driving input x: corr(x_t, u_{t+1..t+6}) must be of the intended sign
    AND |corr| must exceed |corr(x_t, u_{t-6..t-1})|. An input that only correlates with PAST book
    return is rejected outright, regardless of backtest Sharpe.
G2  TAIL. maxDD (per unit gross, cumulative-sum caliber) reduced by >= 20% relative vs baseline,
    AND CVaR5 of the daily (6-anchor) return improved (less negative).
G3  ALPHA GIVEN UP. Full-sample mean bps/anchor must not fall below 85% of baseline
    (i.e. at most 15% of the mean is paid for the tail reduction).
G4  NO YEAR MADE MATERIALLY WORSE. For each calendar year 2022..2026, the controlled Sharpe must be
    >= baseline Sharpe - 0.50 (0.5 is ~half the annual Sharpe SE of 1.0).
G5  SHARPE. Full-sample annualised Sharpe improves by >= +0.25, and the improvement survives a
    block bootstrap (30-anchor blocks, 2000 draws) with one-sided p <= 0.10.
G6  EXCHANGE RATE reported as a number: (alpha given up, bps/anchor) / (maxDD removed, % of gross).
    No threshold - it must be REPORTED, and it is the quantity the user rules on.
G7  PARAMETER PARSIMONY. At most 2 free scalars in the rule. Any rule with >2 tuned scalars is
    reported as EXPLORATORY ONLY, never as admitted, and its K-fold multiple-testing count is stated.
G8  TURNOVER. Gross scaling turnover must be reported in units of |dg|/anchor x gross; charged at
    3.52 bps per unit of traded intent (project receipt turnover_cost_reaudit_2026_08_21).

Stop-line frequency (fraction of days breaching -4.0% of equity at 2.0x) is REPORTED for baseline
and controlled, no threshold.

Failure to meet any of G1-G5 => the candidate is reported as NOT ADMITTED with its numbers.
