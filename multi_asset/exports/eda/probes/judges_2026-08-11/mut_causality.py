"""[causality] EVERY panel channel is causal — proven BEHAVIOURALLY, not by reading code.

THE TEST: build the 32 channels twice — once on clean inputs, once with every input POISONED
strictly after a cut row (prices x3, volumes x7, funding shifted). A channel that is causal
cannot see the poison: its rows at and before the cut must be BIT-IDENTICAL across the two
runs. A channel that reads the future changes. No pattern matching, no reading code, no
opinion about which API is centered — the data itself testifies.

WHY THIS EXISTS (2026-08-03): `betaadj_ret24` carried 11 hours of future market return through
`np.convolve(..., "same")` for the model's whole life. It did not LOOK like lookahead — no
`shift(-n)`, no `center=True`; every pattern scan came back clean — and it was found only by a
person reading all 32 constructions one by one. This suite is that person, mechanised. It
would have gone red the day the line was written.

★ THE KNOWN LEAK IS A NAMED EXEMPTION WITH AN ASSERTED SIGNATURE, NOT A SKIP.
  ch31 stays as-is in production (frozen by ruling: the deployed models were TRAINED on it;
  the causal rewrite on a frozen model measures 0.079 -> 0.041). So this suite asserts ch31's
  defect PRECISELY: poison may reach back exactly 11 rows and no further. If a code change
  makes it reach further (worse), or vanish (someone "fixed" the frozen line — the 0.041
  trap), or if ANY other channel moves at all, this goes red. The exemption dies with the
  retrain deployment batch (PREREG_retrain_causal_panel_2026-08-03, SHA 6336c555…): when the
  causal panel ships, delete the exemption and ch31 joins the plain causal assertion.

Exit 0 = all pass.
"""
import os
import sys

import numpy as np

_SELF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SELF, "signal"))
sys.path.insert(0, os.path.join(_SELF, "vendor"))

_fail = []


def ok(cond, label, detail=""):
    print(("  OK    " if cond else "  FAIL  ") + label + ("  — " + str(detail) if detail else ""))
    if not cond:
        _fail.append(label)


import panel_build as PB  # noqa: E402

T, N = 1400, 8
CUT = 1200          # poison strictly AFTER this row
LEAK_REACH = 11     # measured support of convolve('same', ones(24)): out[t] <- input[t-12..t+11]

# Realistic positive random-walk inputs; volumes strictly positive; funding small.
rng = np.random.default_rng(11)
_ret = rng.normal(0, 0.01, (T, N))
CLOSE = 100.0 * np.exp(np.cumsum(_ret, axis=0))
HIGH, LOW = CLOSE * 1.008, CLOSE * 0.992
VOL = np.abs(rng.normal(1e4, 2e3, (T, N))) + 100.0
QVOL = np.abs(rng.normal(1e7, 2e6, (T, N))) + 1e4
DVOL30 = np.abs(rng.normal(1e7, 1e6, (T, N))) + 1e4
FUND = rng.normal(0, 1e-4, (T, N))


def build(close, high, low, vol, qvol, dvol, fund):
    CH, names = PB.build_channels(close, high, low, vol, qvol, DVOL30=dvol, funding_ema=fund)
    return np.asarray(CH, np.float64), list(names)


CH0, names = build(CLOSE, HIGH, LOW, VOL, QVOL, DVOL30, FUND)

# Poison EVERY input strictly after CUT — multiplicative on prices/volumes (keeps them valid),
# additive on funding. If a channel can see any of it, its early rows move.
P = slice(CUT + 1, None)
c, h, l = CLOSE.copy(), HIGH.copy(), LOW.copy()
v, q, d, f = VOL.copy(), QVOL.copy(), DVOL30.copy(), FUND.copy()
c[P] *= 3.0; h[P] *= 3.0; l[P] *= 3.0
v[P] *= 7.0; q[P] *= 7.0; d[P] *= 7.0
f[P] += 5e-3
CH1, names1 = build(c, h, l, v, q, d, f)

print("[0] the harness itself is sound")
ok(names == names1 and len(names) == CH0.shape[2], "channel axis stable across runs",
   f"{len(names)} channels")
ok(not np.array_equal(np.nan_to_num(CH0[P]), np.nan_to_num(CH1[P])),
   "poison actually reached the panel (post-cut rows differ) — otherwise every check below "
   "passes vacuously and this suite asserts nothing")

LEAKY = "___no_exemption___"
print("\n[1] every channel except the named exemption is causal (rows <= cut bit-identical)")
bad = []
for j, nm in enumerate(names):
    if nm == LEAKY:
        continue
    if not np.array_equal(CH0[: CUT + 1, :, j], CH1[: CUT + 1, :, j], equal_nan=True):
        first = int(np.argwhere(~np.isclose(np.nan_to_num(CH0[:CUT + 1, :, j]),
                                            np.nan_to_num(CH1[:CUT + 1, :, j]))).min(initial=CUT))
        bad.append((nm, first))
ok(not bad, "★★★ 31/31 non-exempt channels unchanged at rows <= cut — a NEW leak anywhere "
            "in the construction turns this red with the channel named", bad[:4])

print("\n[2] the known leak has exactly its measured signature — no more, no less")
j = names.index(LEAKY)
ok(np.array_equal(CH0[: CUT - LEAK_REACH, :, j], CH1[: CUT - LEAK_REACH, :, j], equal_nan=True),
   f"★★ ch31 poison reaches back at most {LEAK_REACH} rows (rows <= cut-{LEAK_REACH + 1} "
   f"identical) — if this fails the leak got WORSE than the audited one")
tail = ~np.isclose(np.nan_to_num(CH0[CUT - LEAK_REACH: CUT + 1, :, j]),
                   np.nan_to_num(CH1[CUT - LEAK_REACH: CUT + 1, :, j]))
ok(tail.any(),
   "★★★ ...and the leak IS still present in its window — this failing means someone made the "
   "frozen line causal: on the FROZEN models that is the measured 0.079 -> 0.041 degradation "
   "(RESULT_channel_cutoff_audit SHA cd13eab6…). STOP: the only sanctioned removal is the "
   "retrain deployment batch, which also deletes this exemption.")

print("\n[3] the exemption is closed-world: exactly one name may be non-causal")
ok(sum(1 for nm in names if nm == LEAKY) == 1, "exactly one exempt channel exists in the axis")

print("\n" + "=" * 70)
if _fail:
    print("FAIL  (%d)" % len(_fail))
    for x in _fail:
        print("   -", x)
    sys.exit(1)
print("ALL PASS")
