#!/usr/bin/env python3
"""Bit-identical proof for the --dense_train gated flag (default OFF).

Only the data layer changed. Load pre-patch (backup) and post-patch WidePanelData as
separate modules; with dense_train=False confirm iter_batches yields byte-identical
batches to the backup (train arg absent). Also confirm patched train=True + off ==
train=False (both clean). Identical inputs -> identical training downstream.
"""
import importlib.util, hashlib, numpy as np

M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
NPZ = M + "/exports/wide_dl_full_39ch.npz"
PATCHED = M + "/data/wide_panel_dataset.py"
BACKUP = M + "/data/wide_panel_dataset.py.bak_predense"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WidePanelData


def h(arr):
    return hashlib.md5(np.ascontiguousarray(arr).tobytes()).hexdigest()


def batch_digest(WPD, dense_train, train_flag, n_batches=6):
    kw = {} if dense_train is None else {"dense_train": dense_train}
    d = WPD(path=NPZ, target_horizon=24, **kw)
    days = d.uniq_days
    d.set_fold(days[:int(len(days) * 0.6)])
    te = days[int(len(days) * 0.6):int(len(days) * 0.7)]
    rng = np.random.default_rng(123)
    kwargs = {"batch_hours": 16, "rng": rng, "shuffle": True}
    if train_flag is not None:
        kwargs["train"] = train_flag
    digs = []
    for i, b in enumerate(d.iter_batches(te, **kwargs)):
        if i >= n_batches:
            break
        digs.append((h(b["rows"]), h(b["Xseq"]), h(b["y"]), h(b["mask"]), int(b["mask"].sum())))
    return digs, (d.mu is not None and h(d.mu)), (d.sd is not None and h(d.sd)), float(d.resid_sigma)


WPD_bak = load(BACKUP, "wpd_bak")
WPD_new = load(PATCHED, "wpd_new")

# reference: pre-patch (no train arg, no dense_train kw)
ref = batch_digest(WPD_bak, dense_train=None, train_flag=None)
# post-patch flag OFF, as the harness now calls training (train=True, dense_train=False)
off_train = batch_digest(WPD_new, dense_train=False, train_flag=True)
# post-patch eval path (train=False)
off_eval = batch_digest(WPD_new, dense_train=False, train_flag=False)

print("mu/sd/resid_sigma  ref:", ref[1], ref[2], round(ref[3], 6))
print("mu/sd/resid_sigma  off:", off_train[1], off_train[2], round(off_train[3], 6))
print("batches ref==off_train (flag off, train=True):", ref[0] == off_train[0])
print("batches ref==off_eval  (train=False):        ", ref[0] == off_eval[0])
ok = (ref[0] == off_train[0] == off_eval[0]) and ref[1] == off_train[1] and ref[2] == off_train[2] and ref[3] == off_train[3]
print("\nBIT-IDENTICAL (flag off == pre-change):", "PASS" if ok else "FAIL")

# sanity: with dense_train=True + train=True, batches MUST differ (more members unmasked)
dense_on = batch_digest(WPD_new, dense_train=True, train_flag=True)
more = sum(x[4] for x in dense_on[0]) > sum(x[4] for x in ref[0])
print("dense-ON train mask-sum > clean:", more,
      "(dense", sum(x[4] for x in dense_on[0]), "vs clean", sum(x[4] for x in ref[0]), ")")
print("dense-ON eval path (train=False) == clean:", batch_digest(WPD_new, dense_train=True, train_flag=False)[0] == ref[0])
