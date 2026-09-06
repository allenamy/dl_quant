"""make_patch_constseed.py — dl_monthly_gate addendum §11 (lead 09-05 ~19:1xZ): monthly trainer with a CONSTANT init/shuffle seed for every fold.
Base = verbatim dl_monthly_wf monthly trainer (sha 7bb39f8d…). Behavioural patch = ONE line: `torch.manual_seed(SEED + YM); np.random.seed(SEED + YM)` →
`torch.manual_seed(SEED); np.random.seed(SEED)`. Metadata patch = the per-fold config field "seed_fold": SEED + YM → SEED (so the receipt is not false).
Everything else byte-identical (data, fold rule, embargo 1, validation, optimiser, τ anneal, best-epoch selection, outputs under MWF_OUT; tag via MWF_TAG=mE1c).
usage: make_patch_constseed.py <verbatim monthly trainer> <out>"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]; S = open(src, encoding="utf-8").read()
assert hashlib.sha256(S.encode("utf-8")).hexdigest() == "7bb39f8d93f2daf749535f8a6d91aecd15e8e3361de80138a29c6fbb6270b51e", "verbatim monthly trainer sha mismatch"
def rep(old, new):
    global S; assert S.count(old) == 1, (S.count(old), old[:70]); S = S.replace(old, new)
rep("    torch.manual_seed(SEED + YM); np.random.seed(SEED + YM)\n", "    torch.manual_seed(SEED); np.random.seed(SEED)   # mE1_constseed (addendum §11): constant init/shuffle seed for EVERY fold\n")
rep('"seed_fold": SEED + YM,', '"seed_fold": SEED,')
open(dst, "w", encoding="utf-8").write(S); print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest())
