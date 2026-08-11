#!/usr/bin/env python3
"""Add opt-in --year_folds_from (default None = bit-identical). Skips early test years."""
import py_compile
HN = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/train/train_wide_harness.py"
s = open(HN).read()
repls = [
    ("def year_folds(data, embargo_days=8, val_days=30, min_train_days=120, min_test_days=60):",
     "def year_folds(data, embargo_days=8, val_days=30, min_train_days=120, min_test_days=60, year_from=None):"),
    ("    for Y in sorted(set(day_year.tolist())):\n        te = data.uniq_days[day_year == Y]",
     "    for Y in sorted(set(day_year.tolist())):\n"
     "        if year_from is not None and Y < year_from:\n"
     "            continue                                        # opt-in: skip degenerate early test years\n"
     "        te = data.uniq_days[day_year == Y]"),
    ('                         "ARM-S1): keys ts, YR4K, KMASK. Input CH still from --wide_dl_path.")',
     '                         "ARM-S1): keys ts, YR4K, KMASK. Input CH still from --wide_dl_path.")\n'
     '    ap.add_argument("--year_folds_from", type=int, default=None,\n'
     '                    help="opt-in: with --year_folds, skip test years < this (drop degenerate early "\n'
     '                         "folds, e.g. ARM-S1 te=2022 whose 2021 train has no king-residual target).")'),
    ("        folds = year_folds(data, embargo_days=args.embargo_days, val_days=args.val_days)",
     "        folds = year_folds(data, embargo_days=args.embargo_days, val_days=args.val_days,\n"
     "                            year_from=args.year_folds_from)"),
]
for old, new in repls:
    n = s.count(old)
    assert n == 1, "anchor x%d: %s" % (n, old[:80])
    s = s.replace(old, new)
open(HN, "w").write(s)
py_compile.compile(HN, doraise=True)
print("year_folds_from patch OK + compiled")
