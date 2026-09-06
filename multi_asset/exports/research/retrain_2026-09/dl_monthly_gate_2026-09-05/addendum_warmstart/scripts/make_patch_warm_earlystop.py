"""make_patch_warm_earlystop.py — PREREG_incremental_retrain §1 末句 (W1+FLOOR5 combination arm): the SAME warm-start patch applied on top of the §12 early-stop trainer
(pod_f10_train_monthly_earlystop.py, sha 55ee8382… = CONST 6003c2a2 + best-epoch rule knobs), so BEST_EP_FLOOR=5 and INIT_STATE can be combined. ONE initialisation patch:
  INIT_STATE (env, default "" = verbatim): path of the state dict used to initialise the FIRST fold of this process (W1/W2: the yearly s42 2025-fold model);
  every later fold initialises from the previous fold's best_state (in memory; reloaded from {MWF_OUT}/models/{TAG}_{prev}.pt when a fold is skipped by resume).
  With INIT_STATE empty nothing changes (Net() is built exactly as before; no extra RNG use) ⇒ bitwise identity with CONST.
Also: LR whitelist widened to {3e-4, 1e-4} (W2 dose arm; config self-reports lr); per-fold config gains init_mode / init_state_path / init_state_sha256 / init_from_fold.
Everything else byte-identical (15 epochs, cosine LR, τ anneal, AdamW rebuilt per fold, validation slice 15%, best-epoch rule, embargo 1, mu/sd per fold).
usage: make_patch_warmstart.py <const trainer> <out>"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]; S = open(src, encoding="utf-8").read()
assert hashlib.sha256(S.encode("utf-8")).hexdigest() == "55ee8382deecebce60215a382bea47bd398ee3c99bab181f5df16ed1ef5fd450", "earlystop trainer sha mismatch"
def rep(old, new):
    global S; assert S.count(old) == 1, (S.count(old), old[:80]); S = S.replace(old, new)
rep('TAG = os.environ.get("MWF_TAG", f"mE{EMBM}"); FORCE = int(os.environ.get("FORCE", "0"))\n',
    'TAG = os.environ.get("MWF_TAG", f"mE{EMBM}"); FORCE = int(os.environ.get("FORCE", "0"))\n'
    'INIT_STATE = os.environ.get("INIT_STATE", ""); WARM = 1 if INIT_STATE else 0   # PREREG_incremental_retrain §1: warm start (empty = verbatim)\n'
    'if WARM: assert os.path.exists(INIT_STATE), INIT_STATE\n')
rep('and PLEON == 0 and EPOCHS == 15 and LR == 3e-4 and NCOL == 167', 'and PLEON == 0 and EPOCHS == 15 and LR in (3e-4, 1e-4) and NCOL == 167')
rep('"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE", "BEST_EP_FLOOR", "BEST_EP_FIX")},',
    '"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE", "BEST_EP_FLOOR", "BEST_EP_FIX", "INIT_STATE", "LR")},')
rep('PRED = np.full((nA, NW), np.nan, np.float32)\n_RESF = ',
    'PRED = np.full((nA, NW), np.nan, np.float32)\n_prev_state, _prev_ym = None, None   # warm-start chain state\n_RESF = ')
rep('    if _done and not FORCE and str(YM) in rep["folds"]:\n        log(f"skip {YM}: already done"); continue\n',
    '    if _done and not FORCE and str(YM) in rep["folds"]:\n'
    '        if WARM:   # resume: the chain continues from the skipped fold\'s saved best_state\n'
    '            _pp = f"{MWF_OUT}/models/{TAG}_{YM}.pt"; _prev_state = torch.load(_pp, map_location=DEV); _prev_ym = YM; log(f"WARM resume: reloaded best_state of {YM} from disk {_pp} sha {sha(_pp)[:16]}")\n'
    '        log(f"skip {YM}: already done"); continue\n')
rep('    mdl = Net(XT.shape[1] + (4 if CTXA else 0)).to(DEV)\n    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)\n    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)\n    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))\n    best_va, best_state, va_curve, alist, ep_s = -1e9, None, [], [], []\n',
    '    mdl = Net(XT.shape[1] + (4 if CTXA else 0)).to(DEV)\n'
    '    _init_path, _init_sha, _init_from = None, None, None\n'
    '    if WARM:   # warm start: first fold of the process from INIT_STATE, later folds from the previous fold\'s best_state (weights only; optimiser rebuilt below)\n'
    '        if _prev_state is None:\n'
    '            _init_path = INIT_STATE; _init_sha = sha(INIT_STATE); _init_from = "INIT_STATE"; mdl.load_state_dict(torch.load(INIT_STATE, map_location=DEV))\n'
    '        else:\n'
    '            _init_path = f"{MWF_OUT}/models/{TAG}_{_prev_ym}.pt"; _init_sha = sha(_init_path); _init_from = f"prev_fold_best_state:{_prev_ym}"; mdl.load_state_dict(_prev_state)\n'
    '        log(f"WARM init {YM} from {_init_from} ({_init_path})")\n'
    '    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)\n    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)\n    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))\n    best_va, best_state, va_curve, alist, ep_s = -1e9, None, [], [], []\n')
rep('    torch.save(best_state, f"{MWF_OUT}/models/{TAG}_{YM}.pt")\n',
    '    torch.save(best_state, f"{MWF_OUT}/models/{TAG}_{YM}.pt")\n    if WARM: _prev_state = {k: v.detach().clone() for k, v in best_state.items()}; _prev_ym = YM\n')
rep('"wall_clock_s": round(wall, 1), "epoch_s": ep_s, "test_vs_all_maxdiff": _dm,',
    '"wall_clock_s": round(wall, 1), "epoch_s": ep_s, "test_vs_all_maxdiff": _dm, "init_mode": ("warm" if WARM else "verbatim"), "init_state_path": _init_path, "init_state_sha256": _init_sha, "init_from": _init_from, "lr": LR,')
open(dst, "w", encoding="utf-8").write(S); print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest())
