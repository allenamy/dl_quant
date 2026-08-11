#!/usr/bin/env python3
"""Apply the opt-in --dense_train gated flag (default OFF = bit-identical to before).
Exact-anchor replacements with assert-found-once; py_compile check at the end.
"""
import py_compile

M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
DS = M + "/data/wide_panel_dataset.py"
HN = M + "/train/train_wide_harness.py"


def patch(path, repls):
    s = open(path).read()
    for old, new in repls:
        n = s.count(old)
        assert n == 1, f"anchor found {n}x (want 1) in {path}:\n{old[:120]}"
        s = s.replace(old, new)
    open(path, "w").write(s)
    py_compile.compile(path, doraise=True)
    print("patched OK:", path)


# ---- wide_panel_dataset.py ----
ds = [
    (
        "    def __init__(self, path=WIDE_DL, target_horizon=4, aux_horizons=(1, 24), window=WINDOW):",
        "    def __init__(self, path=WIDE_DL, target_horizon=4, aux_horizons=(1, 24), window=WINDOW,\n"
        "                 dense_train=False):",
    ),
    (
        "        self.valid_hour[ok] = (self.CL[ok].any(1))\n"
        "        self.mu = self.sd = self.sigma = None",
        "        self.valid_hour[ok] = (self.CL[ok].any(1))\n"
        "        # dense-train (opt-in): predict-hours where >=1 member has a finite target (ALL\n"
        "        # overlapping 1h-grid labels, not just CL{H} stride-H anchors). EVAL/scoring stays clean.\n"
        "        self.dense_train = dense_train\n"
        "        self.valid_hour_dense = np.zeros(self.T, bool)\n"
        "        self.valid_hour_dense[ok] = ((self.member[ok] & np.isfinite(self.Y[ok])).any(1))\n"
        "        self.mu = self.sd = self.sigma = None",
    ),
    (
        "    def iter_batches(self, split_hours, batch_hours=256, rng=None, shuffle=True, want_raw=False,\n"
        "                     want_aux=False):\n"
        '        """Yield standardized window batches over the prediction hours in split_hours (day list)."""\n'
        "        sel = np.isin(self.day, split_hours) & self.valid_hour\n"
        "        hrs = np.where(sel)[0]",
        "    def iter_batches(self, split_hours, batch_hours=256, rng=None, shuffle=True, want_raw=False,\n"
        "                     want_aux=False, train=False):\n"
        '        """Yield standardized window batches over the prediction hours in split_hours (day list).\n'
        "        train=True + self.dense_train -> dense grid (all overlapping labels); else CL{H} clean.\"\"\"\n"
        "        dense = train and self.dense_train\n"
        "        sel = np.isin(self.day, split_hours) & (self.valid_hour_dense if dense else self.valid_hour)\n"
        "        hrs = np.where(sel)[0]",
    ),
    (
        "            ymat = self.Y[bh]                               # (B,N)\n"
        "            mask = (self.member[bh] & self.CL[bh] & np.isfinite(ymat)).astype(np.float32)",
        "            ymat = self.Y[bh]                               # (B,N)\n"
        "            if dense:\n"
        "                mask = (self.member[bh] & np.isfinite(ymat)).astype(np.float32)\n"
        "            else:\n"
        "                mask = (self.member[bh] & self.CL[bh] & np.isfinite(ymat)).astype(np.float32)",
    ),
]
patch(DS, ds)

# ---- train_wide_harness.py ----
hn = [
    (
        '    ap.add_argument("--embargo_days", type=int, default=8)',
        '    ap.add_argument("--embargo_days", type=int, default=8)\n'
        '    ap.add_argument("--dense_train", action="store_true",\n'
        '                    help="opt-in: train on ALL overlapping 1h-grid labels (member&finite); "\n'
        '                         "eval/score/checkpoint stay CL{H} clean. For long horizons where "\n'
        '                         "CL stride-H starves training (H=24: 1:0.8 -> ~1:20 params:samples).")',
    ),
    (
        '    dl_kwargs = {"path": args.wide_dl_path} if args.wide_dl_path else {}',
        '    dl_kwargs = {"path": args.wide_dl_path} if args.wide_dl_path else {}\n'
        '    dl_kwargs["dense_train"] = args.dense_train',
    ),
    (
        "        for b in data.iter_batches(tr_days, batch_hours=args.batch_hours, rng=rng,\n"
        "                                   shuffle=(args.pred_smooth_lambda <= 0), want_aux=args.aux_mtl):",
        "        for b in data.iter_batches(tr_days, batch_hours=args.batch_hours, rng=rng,\n"
        "                                   shuffle=(args.pred_smooth_lambda <= 0), want_aux=args.aux_mtl,\n"
        "                                   train=True):",
    ),
]
patch(HN, hn)
print("ALL PATCHES APPLIED + compiled")
