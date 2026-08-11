#!/usr/bin/env python3
"""ARM-N1a Phase-2 harness hooks (opt-in, default off = king unchanged):
--pretrained_encoder PATH (init encoder from comovement-pretrained weights),
--enc_lr_mult (discriminative LR for encoder params), --max_folds (fold0 early-screen cap)."""
import py_compile
HN = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/train/train_wide_harness.py"
s = open(HN).read()
repls = [
    # 1. load pretrained encoder after build
    ("    enc = build_encoder(args.encoder, data.C, args.d_model, args.n_blocks, KERNEL, DROPOUT)",
     "    enc = build_encoder(args.encoder, data.C, args.d_model, args.n_blocks, KERNEL, DROPOUT)\n"
     "    if args.pretrained_encoder:\n"
     "        enc.load_state_dict(torch.load(args.pretrained_encoder, map_location=DEV))\n"
     "        if fold_i == 0 and verbose:\n"
     "            print(f\"[n1a] loaded pretrained encoder <- {args.pretrained_encoder}\", flush=True)"),
    # 2. discriminative LR
    ("    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=WD)",
     "    if args.enc_lr_mult != 1.0:\n"
     "        _eid = {id(p) for p in model.encoder.parameters()}\n"
     "        _encp = [p for p in model.parameters() if id(p) in _eid]\n"
     "        _othp = [p for p in model.parameters() if id(p) not in _eid]\n"
     "        opt = torch.optim.AdamW([{\"params\": _encp, \"lr\": args.lr * args.enc_lr_mult},\n"
     "                                 {\"params\": _othp, \"lr\": args.lr}], weight_decay=WD)\n"
     "    else:\n"
     "        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=WD)"),
    # 3. max_folds early-screen cap
    ("    all_m = []\n    for i, fold in enumerate(folds):",
     "    all_m = []\n    for i, fold in enumerate(folds):\n"
     "        if args.max_folds and i >= args.max_folds:\n"
     "            print(f\"[n1a] max_folds={args.max_folds} reached -- stopping (early-screen).\", flush=True)\n"
     "            break"),
    # 4. argparse flags (after --year_folds_from)
    ('                         "folds, e.g. ARM-S1 te=2022 whose 2021 train has no king-residual target).")',
     '                         "folds, e.g. ARM-S1 te=2022 whose 2021 train has no king-residual target).")\n'
     '    ap.add_argument("--pretrained_encoder", type=str, default=None,\n'
     '                    help="ARM-N1a: init encoder from comovement-pretrained weights (per-fold).")\n'
     '    ap.add_argument("--enc_lr_mult", type=float, default=1.0,\n'
     '                    help="ARM-N1a: discriminative LR multiplier for encoder params (e.g. 0.3).")\n'
     '    ap.add_argument("--max_folds", type=int, default=0,\n'
     '                    help="cap #folds (0=all); fold0 early-screen uses 1.")'),
]
for old, new in repls:
    n = s.count(old)
    assert n == 1, "anchor x%d:\n%s" % (n, old[:110])
    s = s.replace(old, new)
open(HN, "w").write(s)
py_compile.compile(HN, doraise=True)
print("N1a phase-2 harness patch OK + compiled")
