"""make_patch_warmstart_s2027.py — PREREG_dl_warmstart_replication_2026-09-06 §1: the §13 warm-start trainer with ONE line changed —
env whitelist `SEED == 42` → `SEED in (42, 2027)`. Everything else byte-identical; with SEED=2027 every fold uses the constant seed 2027
and the chain initialises from the yearly s2027 2025-fold .pt (passed via INIT_STATE by the launcher)."""
import sys, hashlib
src, dst, expect = sys.argv[1], sys.argv[2], sys.argv[3]
S = open(src, encoding="utf-8").read()
got = hashlib.sha256(S.encode("utf-8")).hexdigest()
assert got.startswith(expect), f"warmstart trainer sha mismatch: {got[:16]} != {expect}"
old = 'assert ARM == "V2MAIN" and V2 == 1 and SEED == 42 and COST == 3.52'
new = 'assert ARM == "V2MAIN" and V2 == 1 and SEED in (42, 2027) and COST == 3.52'
assert S.count(old) == 1, S.count(old)
S = S.replace(old, new); open(dst, "w", encoding="utf-8").write(S)
print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest()[:16])
