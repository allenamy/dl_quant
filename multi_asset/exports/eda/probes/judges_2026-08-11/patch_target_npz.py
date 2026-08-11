#!/usr/bin/env python3
"""Add the opt-in --target_npz sidecar-target hook (default None = bit-identical to before)."""
import py_compile
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
DS = M + "/data/wide_panel_dataset.py"; HN = M + "/train/train_wide_harness.py"


def patch(path, repls):
    s = open(path).read()
    for old, new in repls:
        n = s.count(old)
        assert n == 1, "anchor x%d in %s:\n%s" % (n, path, old[:110])
        s = s.replace(old, new)
    open(path, "w").write(s); py_compile.compile(path, doraise=True); print("patched", path)


patch(DS, [
    ("                 dense_train=False):",
     "                 dense_train=False, target_npz=None):"),
    ("        self.aux = {int(h): (z[f\"YR{h}\"].astype(np.float32), z[f\"CL{h}\"]) for h in aux_horizons}\n"
     "        # hourly grid -> day index for walk-forward folds",
     "        self.aux = {int(h): (z[f\"YR{h}\"].astype(np.float32), z[f\"CL{h}\"]) for h in aux_horizons}\n"
     "        # ARM-S1 (opt-in): override primary target with a king-residual sidecar (YR4K) and restrict\n"
     "        # the clean/eval mask to king-available cells (2022+). Yraw (raw fwd ret) stays as-is.\n"
     "        if target_npz is not None:\n"
     "            tn = np.load(target_npz, allow_pickle=True)\n"
     "            assert np.array_equal(tn[\"ts\"], self.ts), \"target_npz ts mismatch\"\n"
     "            self.Y = tn[\"YR4K\"].astype(np.float32)\n"
     "            self.CL = self.CL & tn[\"KMASK\"]\n"
     "        # hourly grid -> day index for walk-forward folds"),
])

patch(HN, [
    ('                         "CL stride-H starves training (H=24: 1:0.8 -> ~1:20 params:samples).")',
     '                         "CL stride-H starves training (H=24: 1:0.8 -> ~1:20 params:samples).")\n'
     '    ap.add_argument("--target_npz", type=str, default=None,\n'
     '                    help="opt-in sidecar replacement primary target (e.g. YR4K king-residual for "\n'
     '                         "ARM-S1): keys ts, YR4K, KMASK. Input CH still from --wide_dl_path.")'),
    ('    dl_kwargs["dense_train"] = args.dense_train',
     '    dl_kwargs["dense_train"] = args.dense_train\n'
     '    dl_kwargs["target_npz"] = args.target_npz'),
])
print("ALL PATCHES APPLIED + compiled")
