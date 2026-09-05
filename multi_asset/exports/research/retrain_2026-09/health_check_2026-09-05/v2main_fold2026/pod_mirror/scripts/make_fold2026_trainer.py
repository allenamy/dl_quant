"""Derive pod_f10_train_ext_fold2026.py from the verbatim pod trainer by anchored string edits (each anchor must occur exactly once)."""
import hashlib, sys
src_p = sys.argv[1]; dst_p = sys.argv[2]
s = open(src_p).read()
assert hashlib.sha256(s.encode()).hexdigest() == "93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598", "base script sha mismatch"
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:60], s.count(old))
    s = s.replace(old, new)
# E1: fold selection + output redirection + model dir (after EPOCHS/LR line)
rep('EPOCHS = int(os.environ.get("EPOCHS", "15")); LR = float(os.environ.get("LR", "3e-4"))\n',
    'EPOCHS = int(os.environ.get("EPOCHS", "15")); LR = float(os.environ.get("LR", "3e-4"))\n'
    '# ── fold2026 derivation (PREREG_live_form_health_check_2026-09-05 AMENDMENT 1). Base = /workspace/pod_f10_train_ext.py sha256 93cc2cdf… (verbatim 09-01 gate trainer).\n'
    '# FOLDS = test folds that are TRAINED (default = all four = base behaviour). A skipped fold only replays the base script\'s numpy RNG draws\n'
    '# (one np.random.permutation(starts) per epoch) so the numpy stream at the trained fold is identical to a full 4-fold run; torch RNG is re-seeded\n'
    '# per fold by the base script (torch.manual_seed(SEED + YV)). F10_TAG / F10_PREDS_DIR / F10_RES_DIR redirect the outputs (defaults = base paths);\n'
    '# F10_MODELS_DIR (if set) saves the selected best-validation model (state_dict + mu/sd standardisation + config) per trained fold. Numerics untouched.\n'
    'BASE_SHA256 = "93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598"\n'
    'FOLDS = tuple(int(x) for x in os.environ.get("FOLDS", "2023,2024,2025,2026").split(","))\n'
    'TAG = os.environ.get("F10_TAG", f"f10_{ARM}_s{SEED}")\n'
    'PREDS_DIR = os.environ.get("F10_PREDS_DIR", f"{OUT}/preds"); RES_DIR = os.environ.get("F10_RES_DIR", f"{OUT}/results"); MODELS_DIR = os.environ.get("F10_MODELS_DIR", "")\n'
    'for _d in (PREDS_DIR, RES_DIR, MODELS_DIR):\n'
    '    if _d: os.makedirs(_d, exist_ok=True)\n')
# E2: V2 guard (E-0826-D)
rep('V2 = int(os.environ.get("V2", "0"))\n',
    'V2 = int(os.environ.get("V2", "0"))\n'
    'if ARM == "V2MAIN": assert V2 == 1, "E-0826-D: ARM=V2MAIN requires V2=1 (msharpe-leg composite chain)"\n')
# E3: self-report additions to rep
rep('       "folds": {}}\n',
    '       "folds": {}}\n'
    'rep.update({"v2": V2, "folds_trained": list(FOLDS), "tag": TAG, "base_script_sha256": BASE_SHA256, "torch": torch.__version__, "cuda": torch.version.cuda,\n'
    '            "device": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"), "legs_sha256": (sha(f"{OUT}/data/f10v2_legs.npz") if V2 else None),\n'
    '            "env": {k: os.environ.get(k) for k in ("ARM", "SEED", "V2", "FOLDS", "F10_DLW", "F10_OUT", "F10_TAG", "F10_PREDS_DIR", "F10_RES_DIR", "F10_MODELS_DIR", "COST", "LDD", "AFIX", "EPOCHS", "LR", "NCOL", "EXTRA", "LPP", "LDC", "CTXA", "REC", "PLE")}})\n')
# E4: skip (RNG replay) for folds not in FOLDS, placed right after `starts` is built
rep('    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))\n',
    '    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))\n'
    '    if YV not in FOLDS:   # fold2026: replay this fold\'s per-epoch numpy draws (base: order = np.random.permutation(starts) once per epoch), train nothing\n'
    '        for _ep in range(EPOCHS): np.random.permutation(starts)\n'
    '        log(f"[{YV}] SKIPPED (FOLDS={FOLDS}): replayed {EPOCHS} np.random.permutation draws over {len(starts)} starts; train idx {int(tr_idx[0])}..{int(tr_idx[-1])}")\n'
    '        del mdl, opt; torch.cuda.empty_cache(); continue\n'
    '    fold_t0 = time.time()\n')
# E5: model save after best-state load
rep('    mdl.load_state_dict(best_state); mdl.eval()\n',
    '    mdl.load_state_dict(best_state); mdl.eval()\n'
    '    if MODELS_DIR:   # fold2026: persist the selected model (best validation epoch) with its standardisation vectors and config\n'
    '        _mp = f"{MODELS_DIR}/{TAG}_fold{YV}.pt"\n'
    '        _fc = {"fold": YV, "model_path": _mp, "first_te": int(first_te), "n_test": int(te.size), "n_trainval_anchors": int(len(tr_idx)), "n_train_anchors": int(len(tr1)), "n_val_anchors": int(len(va1)),\n'
    '               "train_first_E_ts": int(E_ts[tr1[0]]), "train_last_E_ts": int(E_ts[tr1[-1]]), "val_first_E_ts": int(E_ts[va1[0]]), "val_last_E_ts": int(E_ts[va1[-1]]),\n'
    '               "max_trainval_idx": int(tr_idx[-1]), "max_trainval_E_ts": int(E_ts[tr_idx[-1]]), "embargo_anchors_between": int(first_te - 1 - tr_idx[-1]),\n'
    '               "first_test_E_ts": int(E_ts[first_te]), "last_test_E_ts": int(E_ts[te[-1]]), "best_va": float(best_va), "best_epoch": int(np.argmax(va_curve)), "alpha_final": float(mdl.alpha()),\n'
    '               "n_starts": int(len(starts)), "config": {k: v for k, v in rep.items() if k != "folds"}}\n'
    '        torch.save({"state_dict": {k: v.cpu() for k, v in best_state.items()}, "mu": mu.cpu(), "sd": sd.cpu(), "fold_config": _fc}, _mp)\n'
    '        json.dump(_fc, open(f"{MODELS_DIR}/{TAG}_fold{YV}_config.json", "w"), indent=1, default=float)\n'
    '        log(f"[{YV}] model saved {_mp} (sha256 {sha(_mp)[:16]}) best_epoch {int(np.argmax(va_curve))} best_va {best_va:+.4f}")\n')
# E6: wall-clock per fold + output redirection
rep('                             "turnover_mean": round(float(np.mean(trn_series)), 5)}\n',
    '                             "turnover_mean": round(float(np.mean(trn_series)), 5), "wall_s": round(time.time() - fold_t0, 1)}\n')
rep('    np.save(f"{OUT}/preds/f10_{ARM}_s{SEED}.npy", PRED)\n', '    np.save(f"{PREDS_DIR}/{TAG}.npy", PRED)\n')
rep('json.dump(rep, open(f"{OUT}/results/f10_{ARM}_s{SEED}.json", "w"), indent=1, default=float)\n', 'json.dump(rep, open(f"{RES_DIR}/{TAG}.json", "w"), indent=1, default=float)\n', count=2)
rep('rep["net_mean_all"] = round(float(np.mean([f["net_mean_bps"] for f in rep["folds"].values()])), 4)\n',
    'rep["net_mean_all"] = round(float(np.mean([f["net_mean_bps"] for f in rep["folds"].values()])), 4); rep["wall_total_s"] = round(time.time() - T0, 1)\n')
open(dst_p, "w").write(s)
print("written", dst_p, "sha256", hashlib.sha256(s.encode()).hexdigest())
