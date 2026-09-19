#!/usr/bin/env python3
"""make_tf_trainer.py — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (sha256 9b403aad…, commit 4a96358ec) §2 "训练器".

Builds the research copy pod_f10_train_monthly_v4_tf.py from the CURRENT trainer pod_f10_train_monthly_v4.py (sha256 fd5707bd…, the copy the
FP2-8 chain executed to produce A1) by EXACT string replacement; every anchor must occur exactly once in the base, else the generator refuses.
The only behavioural knob added is TRAIN_FRAC (env, default "0.85" = the verbatim `int(len(tr_idx) * 0.85)` cut). Everything else it adds is a
receipt (env_given word, per-fold config fields). The source file in the chain device dir is never modified (its sha is pinned by the October
contract); the product is written to a NEW path.

Semantics under TRAIN_FRAC (same as the 2026-09-07 trainfrac patch, docs/PREREG_dl_full_gradient_window_2026-09-07.md §2):
  tr1 = tr_idx[:int(len*TRAIN_FRAC)]   (gradient windows `starts` and the mu/sd calibration sample follow tr1)
  va1 = tr_idx[int(len*0.85):]          (unchanged; under TRAIN_FRAC > 0.85 it lies INSIDE tr1 -> in-sample, diagnostic only)
  TRAIN_FRAC > 0.85 requires BEST_EP_FIX >= 0 (no selection on an in-sample curve).
usage: python3 make_tf_trainer.py <base.py> <out.py>
"""
import hashlib, sys, difflib

BASE_SHA = "fd5707bd3acccdbb3689cf17484fcb30c48002cabf2e1c132bcf48791ac14e21"
base_p, out_p = sys.argv[1], sys.argv[2]
src = open(base_p, encoding="utf-8").read()
got = hashlib.sha256(src.encode("utf-8")).hexdigest()
assert got == BASE_SHA, f"base sha {got} != {BASE_SHA}"

REPL = [
    # 1. the knob + its two guards, right after the best-epoch knobs
    ('BEST_EP_FLOOR = int(os.environ.get("BEST_EP_FLOOR", "0")); BEST_EP_FIX = int(os.environ.get("BEST_EP_FIX", "-1"))   # PREREG_dl_monthly_earlystop: best-epoch rule knobs (0 / -1 = verbatim)\n',
     'BEST_EP_FLOOR = int(os.environ.get("BEST_EP_FLOOR", "0")); BEST_EP_FIX = int(os.environ.get("BEST_EP_FIX", "-1"))   # PREREG_dl_monthly_earlystop: best-epoch rule knobs (0 / -1 = verbatim)\n'
     'TRAIN_FRAC = float(os.environ.get("TRAIN_FRAC", "0.85"))   # PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (9b403aad) T1: gradient share of the legal training pool; "0.85" = verbatim cut\n'
     'assert 0.85 <= TRAIN_FRAC <= 1.0, f"TRAIN_FRAC whitelist [0.85, 1.0]: {TRAIN_FRAC}"\n'
     'assert not (TRAIN_FRAC > 0.85 and BEST_EP_FIX < 0), "full window requires a fixed epoch (validation slice becomes in-sample; selecting on it would be selection leakage)"\n'),
    # 2. env whitelist receipt records the knob
    ('"MONTHS_ALL", "V4_DLW_RAW", "V4_DLW_CLIP", "V4_F8", "V4_BASE_TRAINER", "V4_MONTH", "V4_MONTH_ENV")},\n',
     '"MONTHS_ALL", "V4_DLW_RAW", "V4_DLW_CLIP", "V4_F8", "V4_BASE_TRAINER", "V4_MONTH", "V4_MONTH_ENV", "TRAIN_FRAC")},\n'),
    # 3. run-level receipt (added keys only; the inherited fold_rule strings are left byte-identical)
    ('assert np.all(np.diff(E_ts) == 14400), "anchor grid is not a regular 4h grid"\n',
     'rep.update({"train_frac": TRAIN_FRAC, "train_frac_rule": "tr1 = tr_idx[:int(len*TRAIN_FRAC)] (gradient windows + mu/sd sample); va1 = tr_idx[int(len*0.85):] unchanged, IN-SAMPLE and diagnostic-only when TRAIN_FRAC > 0.85",\n'
     '            "note_inherited_rng_string": "fold_rule.rng above is inherited verbatim and is FALSE for this code (E-0907-G): every fold re-seeds torch.manual_seed(SEED); np.random.seed(SEED) (constant), see the line tagged mE1_constseed"})\n'
     'assert np.all(np.diff(E_ts) == 14400), "anchor grid is not a regular 4h grid"\n'),
    # 4. the cut (the ONLY behavioural change)
    ('    cut = int(len(tr_idx) * 0.85)\n    tr1, va1 = tr_idx[:cut], tr_idx[cut:]\n',
     '    cut85 = int(len(tr_idx) * 0.85); cutg = int(len(tr_idx) * TRAIN_FRAC)\n'
     '    tr1, va1 = tr_idx[:cutg], tr_idx[cut85:]   # va1 unchanged (last 15%) so va_curve stays comparable across arms\n'
     '    VA_IN_SAMPLE = bool(TRAIN_FRAC > 0.85)     # under the full window va1 is INSIDE tr1: diagnostic only, never used for selection (FIX epoch asserted above)\n'
     '    cut = cutg                                  # keep the old name alive for any downstream reference\n'),
    # 5. per-fold receipts: which anchors actually reached the gradient
    ('"n_train": int(len(tr_idx)), "n_val": int(len(va1)),\n',
     '"n_train": int(len(tr_idx)), "n_val": int(len(va1)),\n'
     '            "train_frac": TRAIN_FRAC, "va_in_sample": VA_IN_SAMPLE, "n_grad_anchors": int(len(tr1)), "grad_last_ts": iso(E_ts[int(tr1[-1])]),\n'
     '            "grad_loss_last_ts": iso(E_ts[min(int(max(starts)) + WIN - 1, first_te - EMBM - 1)]), "va_first_ts": iso(E_ts[int(va1[0])]), "va_last_ts": iso(E_ts[int(va1[-1])]),\n'),
]
out = src
for old, new in REPL:
    n = out.count(old)
    assert n == 1, f"anchor occurs {n} times (need exactly 1): {old[:90]!r}"
    out = out.replace(old, new)
open(out_p, "w", encoding="utf-8").write(out)
print("base", base_p, BASE_SHA[:16])
print("out ", out_p, hashlib.sha256(out.encode("utf-8")).hexdigest())
sys.stdout.writelines(difflib.unified_diff(src.splitlines(True), out.splitlines(True), "base/pod_f10_train_monthly_v4.py", "tf/pod_f10_train_monthly_v4_tf.py", n=1))
