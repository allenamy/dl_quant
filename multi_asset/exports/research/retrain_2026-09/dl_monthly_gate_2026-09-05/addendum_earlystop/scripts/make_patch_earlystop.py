"""make_patch_earlystop.py — PREREG_dl_monthly_earlystop_2026-09-06 (sha d1feddc0…): on the CONST monthly trainer (pod_f10_train_monthly_constseed.py,
sha 6003c2a2…; = verbatim monthly trainer 7bb39f8d + constant seed 42), change ONLY the best-epoch selection:
  BEST_EP_FLOOR (default 0): keep the validation-best weights only among epochs ep >= FLOOR; best_epoch = FLOOR + argmax(va_curve[FLOOR:]).  FLOOR=0 ≡ verbatim.
  BEST_EP_FIX   (default -1 = off): reload the weights of epoch FIX regardless of validation; best_epoch = FIX; training still runs all EPOCHS (LR/τ unchanged).
Metadata: per-fold config gains "best_epoch_rule"; env_given records the two knobs. Everything else byte-identical. usage: <const trainer> <out>"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]; S = open(src, encoding="utf-8").read()
assert hashlib.sha256(S.encode("utf-8")).hexdigest() == "6003c2a2978e8aa52d9725f510d4ba630d2ac1104d2959af9d382720054c630b", "CONST trainer sha mismatch"
def rep(old, new):
    global S; assert S.count(old) == 1, (S.count(old), old[:80]); S = S.replace(old, new)
rep('TAG = os.environ.get("MWF_TAG", f"mE{EMBM}"); FORCE = int(os.environ.get("FORCE", "0"))\n',
    'TAG = os.environ.get("MWF_TAG", f"mE{EMBM}"); FORCE = int(os.environ.get("FORCE", "0"))\n'
    'BEST_EP_FLOOR = int(os.environ.get("BEST_EP_FLOOR", "0")); BEST_EP_FIX = int(os.environ.get("BEST_EP_FIX", "-1"))   # PREREG_dl_monthly_earlystop: best-epoch rule knobs (0 / -1 = verbatim)\n'
    'BEST_EP_RULE = (f"fix{BEST_EP_FIX}" if BEST_EP_FIX >= 0 else f"floor{BEST_EP_FLOOR}"); assert BEST_EP_FLOOR >= 0 and BEST_EP_FIX < EPOCHS\n')
rep('"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE")},',
    '"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE", "BEST_EP_FLOOR", "BEST_EP_FIX")},')
rep('        if va > best_va:\n            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}\n',
    '        if BEST_EP_FIX >= 0:   # PREREG_dl_monthly_earlystop FIX arm: keep exactly epoch FIX\n'
    '            if ep == BEST_EP_FIX:\n'
    '                best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}\n'
    '        elif ep >= BEST_EP_FLOOR and va > best_va:   # FLOOR arm (FLOOR 0 = verbatim rule)\n'
    '            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}\n')
rep('    wall = time.time() - t_fit\n    mdl.load_state_dict(best_state); mdl.eval()\n',
    '    wall = time.time() - t_fit\n'
    '    _best_ep = BEST_EP_FIX if BEST_EP_FIX >= 0 else BEST_EP_FLOOR + int(np.argmax(va_curve[BEST_EP_FLOOR:]))   # reported best epoch under the rule\n'
    '    assert best_state is not None and abs(va_curve[_best_ep] - round(best_va, 4)) < 1e-6, (_best_ep, va_curve[_best_ep], best_va)\n'
    '    mdl.load_state_dict(best_state); mdl.eval()\n')
rep('"n_windows_per_epoch": len(starts), "best_va": round(best_va, 4), "best_epoch": int(np.argmax(va_curve)), "va_curve": va_curve, "alpha_curve": alist,\n',
    '"n_windows_per_epoch": len(starts), "best_va": round(best_va, 4), "best_epoch": _best_ep, "best_epoch_rule": BEST_EP_RULE, "va_curve": va_curve, "alpha_curve": alist,\n')
rep('            "alpha_final": alist[int(np.argmax(va_curve))], "net_mean_bps"', '            "alpha_final": alist[_best_ep], "net_mean_bps"')
open(dst, "w", encoding="utf-8").write(S); print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest())
