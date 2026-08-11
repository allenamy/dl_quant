"""Patch build_wide_panel.py: settlement-interval dimension fix for FUND_EMA."""
import shutil, sys

P = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/data/build_wide_panel.py"

OLD = '''        ih = float(np.median(fd["funding_interval_h"].values)) if "funding_interval_h" in fd else 8.0
        span = max(2, int(round(24.0 / max(ih, 1.0))))     # 24h-equivalent EMA
        rate = pd.to_numeric(fd["fundingRate"], errors="coerce").values.astype(np.float64)
        ema = pd.Series(rate).ewm(span=span, adjust=False).mean().values'''

NEW = '''        if "funding_interval_h" in fd:
            ivh = pd.to_numeric(fd["funding_interval_h"], errors="coerce").values.astype(np.float64)
        else:
            ivh = np.full(len(fd), 8.0)
        # DELIBERATE: a non-finite/non-positive interval falls back to the 8h default rather than
        # dropping that settlement -- production must never silently lose a funding observation.
        # Such rows are vanishingly rare (0C's reference drops them; the two agree to 3.8e-12).
        ivh = np.where(np.isfinite(ivh) & (ivh > 0), ivh, 8.0)
        ih = float(np.median(ivh))
        span = max(2, int(round(24.0 / max(ih, 1.0))))     # 24h-equivalent EMA
        rate = pd.to_numeric(fd["fundingRate"], errors="coerce").values.astype(np.float64)
        # ★ SETTLEMENT-INTERVAL DIMENSION FIX (0B found / 0C reproduced, 2026-07-25).
        # 4h- and 8h-settled coins coexist in the panel. A 4h coin with identical ANNUALISED carry
        # shows HALF the per-settlement rate, and the engine rank-centres funding cross-sectionally
        # -- rank-centring removes INDIVIDUAL scale but NOT a GROUP-level location shift, so the 4h
        # cohort was pushed systematically to one side (measured gap -0.3745 rank units; it
        # manufactured a spurious -0.006 rank-IC in the funding leg, paired t=+7.79).
        # Normalise to an 8h equivalent PER ROW and BEFORE the EMA: per-row because ~29 coins
        # migrated 8h<->4h mid-history, and before the EMA because the EMA averages settlements --
        # the averaged quantity has to be on a common basis first.
        # Guarded permanently by exports/eda/assert_funding_dim.py (hard gate in build_wide_dl.py).
        ema = pd.Series(rate * (8.0 / ivh)).ewm(span=span, adjust=False).mean().values'''


def main():
    s = open(P).read()
    if "SETTLEMENT-INTERVAL DIMENSION FIX" in s:
        print("already patched; nothing to do")
        return 0
    if s.count(OLD) != 1:
        print(f"FAIL: anchor found {s.count(OLD)} times, expected 1")
        return 1
    shutil.copy(P, P + ".bak_predimfix")
    open(P, "w").write(s.replace(OLD, NEW))
    print("patched build_wide_panel.py (backup: .bak_predimfix)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
