#!/usr/bin/env python3
"""Wire ARM-N1b (multi-relational xattn) into the harness: import + flags + build branch.
Opt-in --multirel (default off = king WideFactorModel unchanged)."""
import py_compile
HN = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/train/train_wide_harness.py"
s = open(HN).read()
repls = [
    # import
    ("    ConformerPanelEncoder, WideFactorModel, WideQIMModel,",
     "    ConformerPanelEncoder, WideFactorModel, WideQIMModel, WideMultiRelModel,"),
    # build branch (else = non-QIM)
    ("        model = WideFactorModel(enc, n_factor_heads=K, xattn=args.xattn,\n"
     "                                n_xattn=args.n_xattn, dropout=DROPOUT, aux_horizons=aux_h).to(DEV)",
     "        if args.multirel:\n"
     "            lbs = tuple(int(x) for x in args.n1b_lookbacks.split(\",\") if x.strip())\n"
     "            ridx = data.ch_names.index(\"ret_1h\") if \"ret_1h\" in data.ch_names else 20\n"
     "            model = WideMultiRelModel(enc, n_factor_heads=K, lookbacks=lbs, ret_idx=ridx,\n"
     "                                      dropout=DROPOUT).to(DEV)\n"
     "        else:\n"
     "            model = WideFactorModel(enc, n_factor_heads=K, xattn=args.xattn,\n"
     "                                    n_xattn=args.n_xattn, dropout=DROPOUT, aux_horizons=aux_h).to(DEV)"),
    # argparse flags (after --n_xattn)
    ('    ap.add_argument("--n_xattn", type=int, default=1)',
     '    ap.add_argument("--n_xattn", type=int, default=1)\n'
     '    ap.add_argument("--multirel", action="store_true",\n'
     '                    help="ARM-N1b: replace single xattn with king-base + zero-init gated "\n'
     '                         "multi-relation delta (rolling-corr buckets @ --n1b_lookbacks).")\n'
     '    ap.add_argument("--n1b_lookbacks", type=str, default="24,72,168",\n'
     '                    help="N1b relation-edge correlation lookbacks in hours (K edges).")'),
]
for old, new in repls:
    n = s.count(old)
    assert n == 1, "anchor x%d:\n%s" % (n, old[:120])
    s = s.replace(old, new)
open(HN, "w").write(s)
py_compile.compile(HN, doraise=True)
print("N1b harness patch OK + compiled")
