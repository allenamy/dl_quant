"""Constraint tests for the DSL parser/type-system/evaluator (factory_prereg §5)."""
import sys
import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl

FAILS = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}", flush=True)
    if not cond:
        FAILS.append(name)


print("=== parser + type system ===", flush=True)
# valid formulas parse; type propagation correct
check("valid dense formula parses", dsl.validate("ts_zscore(mom_24h, 24)")["ok"])
r = dsl.validate("sub(king, ema(mom_24h, 24))")
check("leg+dense -> SPARSE out", r["ok"] and r["out_type"] == "SPARSE")
check("dense-only -> DENSE out", dsl.validate("ts_corr(ret_1h, rvol_24h, 24)")["out_type"] == "DENSE")
check("xsec on leg ok (SPARSE)", dsl.validate("xsec_rank(king)")["ok"])
check("conditional combining legs ok", dsl.validate("where(gt(rvol_24h, 0), king, s2)")["ok"])

# (iii) TYPE SYSTEM: temporal operator on a SPARSE leg is rejected
r = dsl.validate("ts_delta(king, 24)")
check("(iii) ts-op on sparse leg REJECTED by type system", (not r["ok"]) and "SPARSE" in r["error"])
r2 = dsl.validate("ema(s2, 8)")
check("(iii) ema on sparse leg REJECTED", (not r2["ok"]) and "SPARSE" in r2["error"])

# "leakage formula" (non-whitelisted future/target operand) rejected by PARSER
r = dsl.validate("ts_mean(yr4b, 4)")
check("leakage formula (target operand) REJECTED by parser", (not r["ok"]) and "unknown operand" in r["error"])
r = dsl.validate("mul(king, y_forward)")
check("leakage formula (future operand) REJECTED by parser", (not r["ok"]) and "unknown operand" in r["error"])
check("unknown operator rejected", not dsl.validate("future_mean(mom_24h, 4)")["ok"])

# complexity caps
deep = "neg(neg(neg(neg(neg(neg(neg(mom_24h)))))))"        # depth 7 > 6
check("depth cap enforced", not dsl.validate(deep)["ok"])
many = "add(add(add(add(add(add(add(add(add(add(add(add(add(mom_4h,mom_8h),mom_24h),mom_72h),ret_1h),ret_4h),ret_12h),ret_24h),rvol_6h),rvol_24h),rvol_72h),beta_24h),beta_72h)"
check("op-count cap enforced", not dsl.validate(many)["ok"])

# scalar/series arg typing
check("window must be constant", not dsl.validate("ts_mean(mom_24h, mom_4h)")["ok"])
check("series arg cannot be constant", not dsl.validate("neg(24)")["ok"])

print("=== evaluator constraints (synthetic panel) ===", flush=True)
T, N = 60, 6
rng = np.random.default_rng(0)
CH = {c: rng.standard_normal((T, N)).astype(float) for c in dsl.DENSE_CHANNELS}
legs = {}
for L in dsl.LEG_COLUMNS:
    a = np.full((T, N), np.nan); a[::4] = rng.standard_normal((T // 4 + (T % 4 > 0), N))  # anchors only
    legs[L] = a
ctx = {**CH, **legs}
# inject NaN into a dense channel
CH["mom_24h"][5:8, 0] = np.nan

# (ii) NaN excluded, NOT 0-filled: mean of 1.0s with NaN in the window must be 1.0 (0-fill -> <1).
ones = np.ones((T, N)); ones[3:5, 0] = np.nan               # column 0 has 2 NaN inside the window
tm_ones = dsl.evaluate(dsl.parse("ts_mean(mom_24h, 6)"), {**ctx, "mom_24h": ones})
check("(ii) NaN excluded (mean of 1s with NaN in window == 1.0, not <1 from 0-fill)", abs(tm_ones[7, 0] - 1.0) < 1e-9)
# concrete: a cell whose entire trailing window is NaN stays NaN
colNaN = ctx["mom_24h"].copy(); colNaN[:, 1] = np.nan; ctx2 = {**ctx, "mom_24h": colNaN}
tm2 = dsl.evaluate(dsl.parse("ts_mean(mom_24h, 6)"), ctx2)
check("(ii) all-NaN trailing window -> NaN (not 0)", np.isnan(tm2[10, 1]))

# (ii) xsec_z on a degenerate (zero-variance) cross-section -> NaN, not 0 (0 would contaminate nesting)
flat = {**ctx, "mom_4h": np.ones((T, N))}                   # constant cross-section at every anchor
check("(ii) xsec_z degenerate xsec -> NaN not 0", np.isnan(dsl.evaluate(dsl.parse("xsec_z(mom_4h)"), flat)).all())
check("(ii) nested mul(xsec_z(const), y) -> NaN not 0 (no 0-contamination)",
      np.isnan(dsl.evaluate(dsl.parse("mul(xsec_z(mom_4h), ret_1h)"), flat)).all())

# (ii) div by (near-)zero -> NaN, never inf
z = {**ctx, "ret_1h": np.zeros((T, N))}
dv = dsl.evaluate(dsl.parse("div(mom_4h, ret_1h)"), z)
check("(ii) div-by-zero -> NaN not inf", np.isnan(dv).all() and not np.isinf(dv).any())

# (iv) degenerate window -> NaN: ts_corr of a constant series
constch = {**ctx, "ret_1h": np.ones((T, N)), "ret_4h": ctx["ret_4h"]}
cc = dsl.evaluate(dsl.parse("ts_corr(ret_1h, ret_4h, 12)"), constch)
check("(iv) ts_corr on constant window -> NaN", np.isnan(cc[30]).all())
tr = dsl.evaluate(dsl.parse("ts_rank(ret_1h, 12)"), constch)
check("(iv) ts_rank on constant window -> NaN", np.isnan(tr[30]).all())

# (i) center=True forbidden at the primitive
try:
    dsl._roll(np.zeros((T, N)), 6, center=True); centered_ok = False
except dsl.DSLError:
    centered_ok = True
check("(i) center=True rolling forbidden", centered_ok)

# a valid leg-combination formula evaluates to a SPARSE (anchor-only) factor
f = dsl.evaluate(dsl.parse("where(gt(rvol_24h, 0), king, s2)"), ctx)
anchor_rows = np.isfinite(legs["king"]).any(1)
check("leg-combination factor is anchor-sparse", np.isfinite(f[anchor_rows]).any() and not np.isfinite(f[~anchor_rows]).any())

print(f"\n{'#'*60}\nDSL TESTS {'OK' if not FAILS else 'FAILED: ' + str(FAILS)}\n{'#'*60}", flush=True)
sys.exit(0 if not FAILS else 1)
