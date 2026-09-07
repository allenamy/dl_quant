<!-- judge_trainfrac.py (written before any arm number) prereg d5f078a0910e826e; n=10038 2022-01-31 00:00→2026-08-30 20:00; windows {'FROZEN 2025-03->26<=cut': 3168, '2026<=cut': 1332, 'FULL 2025-01->26<=cut': 3522}; UTC-day block 2000 seed 20260905; delta=0.05 -->
## TF-1 · Levels per gross (bps/anchor)
| arm | FPRED | seed | FROZEN [CI95] | S | maxDD | turn/gross | 2026<=cut | FULL |
|---|---|---|---|---|---|---|---|---|
| yearly_s42 | (default f10_V2MAIN_s{FSEED}) | 42 | **+1.557** [+0.580, +2.498] | +2.57 | 1133 | 0.06442 | +3.189 | +1.611 |
| CONST42 | f10_gate_mE1c_R0_spl42.npy | 42 | **+1.442** [+0.475, +2.398] | +2.37 | 1112 | 0.06337 | +3.103 | +1.509 |
| FIX7 | f10_gate_mE1cX7_R0_spl42.npy | 42 | **+1.708** [+0.720, +2.607] | +2.87 | 832 | 0.05910 | +3.263 | +1.730 |
| X7FULL | f10_gate_mE1x7full_R0_spl42.npy | 42 | **+1.651** [+0.700, +2.575] | +2.75 | 919 | 0.06077 | +3.160 | +1.713 |
| X6FULL | f10_gate_mE1x6full_R0_spl42.npy | 42 | **+1.643** [+0.668, +2.621] | +2.72 | 970 | 0.06279 | +3.191 | +1.657 |

## TF-2 · Paired Δ per gross (Δg by anchor; UTC-day-block bootstrap; every contrast prints BOTH arm names — E-0907-E)
| contrast | **FROZEN** | **2026≤cut** | FULL | ΔSharpe frz | Δturn% | maxDD ref→x | Δ w/o best month |
|---|---|---|---|---|---|---|---|
| X7FULL − FIX7 [§4.1 primary 1] | **-0.058 [-0.212,+0.103] P0.23** | **-0.103 [-0.266,+0.058] P0.11** | -0.017 [-0.177,+0.145] P0.44 | -0.125 | +2.8% | 832→919 | -0.081 [-0.232,+0.072] (best 202505) |
| X7FULL − CONST42 [§4.1 primary 2] | **+0.209 [+0.060,+0.359] P1.00** | **+0.057 [-0.127,+0.255] P0.70** | +0.204 [+0.054,+0.347] P1.00 | +0.373 | -4.1% | 1112→919 | +0.152 [+0.012,+0.297] (best 202504) |
| X6FULL − FIX7 [§4.2 data+norm effect] | **-0.066 [-0.235,+0.111] P0.23** | **-0.071 [-0.262,+0.106] P0.21** | -0.073 [-0.241,+0.102] P0.20 | -0.151 | +6.2% | 832→970 | -0.097 [-0.278,+0.087] (best 202604) |
| X7FULL − X6FULL [§4.2 schedule/step effect] | **+0.008 [-0.088,+0.098] P0.56** | **-0.031 [-0.198,+0.123] P0.37** | +0.056 [-0.038,+0.150] P0.88 | +0.026 | -3.2% | 970→919 | -0.012 [-0.108,+0.078] (best 202504) |
| X7FULL − yearly_s42 [§4.3 NI leg] | **+0.094 [-0.079,+0.263] P0.85** | **-0.029 [-0.222,+0.175] P0.42** | +0.102 [-0.070,+0.261] P0.88 | +0.176 | -5.7% | 1133→919 | -0.001 [-0.170,+0.161] (best 202504) |
| X6FULL − yearly_s42 [§4.3 NI leg] | **+0.085 [-0.079,+0.247] P0.84** | **+0.002 [-0.230,+0.238] P0.53** | +0.047 [-0.113,+0.201] P0.72 | +0.150 | -2.5% | 1133→970 | +0.011 [-0.146,+0.172] (best 202504) |
| FIX7 − CONST42 [device integrity: must reproduce +0.267 [+0.083,+0.462]] | **+0.267 [+0.078,+0.467] P1.00** | **+0.160 [-0.034,+0.421] P0.94** | +0.221 [+0.042,+0.417] P0.99 | +0.498 | -6.7% | 1112→832 | +0.208 [+0.033,+0.402] (best 202504) |

## TF-3 · §4.1 primary gate (transcribed verbatim, frozen before numbers)
| condition | value | met |
|---|---|---|
| 1. X7FULL − FIX7 FROZEN CI lower > 0 | -0.2122 | False |
| 2. X7FULL − CONST42 FROZEN CI lower > 0 | +0.0602 | True |
| 3. X7FULL − FIX7 2026 point >= 0 | -0.1028 | False |
| (B) X7FULL − FIX7 FROZEN CI upper < 0 | +0.1032 | False |

**VERDICT: (C) UNDECIDED**

## TF-4 · §4.2 attribution (reported, non-gating)
- data+norm effect  X6FULL − FIX7   : -0.0657 [-0.2347,+0.1115]  (CI contains 0: True)
- schedule/step eff X7FULL − X6FULL : +0.0082 [-0.0876,+0.0976]  (CI lower > 0: False)
- **PRE-COMMITTED CONDITIONAL ACTION triggered: False** — if True the gain is MORE TRAINING, not new data: FIX8@0.85 / FIX9@0.85 must be run first, and until then NO claim that the full window has value.

## TF-5 · §4.3 non-inferiority vs yearly_s42 — **proper test at δ=0.05 (E-0907-F): pass ⇔ CI lower > −δ**
| arm − ref | window | Δ | CI95 | **CI lower** | −δ | NI PASS? | old decision-rule would say |
|---|---|---|---|---|---|---|---|
| X7FULL − yearly_s42 | FROZEN 2025-03->26<=cut | +0.0936 | [-0.0785,+0.2633] | **-0.0785** | -0.05 | **False** | True |
| X7FULL − yearly_s42 | 2026<=cut | -0.0293 | [-0.2221,+0.1755] | **-0.2221** | -0.05 | **False** | True |
| X6FULL − yearly_s42 | FROZEN 2025-03->26<=cut | +0.0855 | [-0.0785,+0.2470] | **-0.0785** | -0.05 | **False** | True |
| X6FULL − yearly_s42 | 2026<=cut | +0.0021 | [-0.2295,+0.2383] | **-0.2295** | -0.05 | **False** | True |

> Wording rule (E-0907-F): write "非劣于年折" ONLY where NI PASS is True. Where only the old decision rule holds, the arm may be described ONLY as "未过冻结决策规则的否决线", and δ=0.05 with the CI lower bound must be printed alongside.
