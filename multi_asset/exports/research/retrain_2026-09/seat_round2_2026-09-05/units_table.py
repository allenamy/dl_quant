"""units_table.py — scripted unit conversion (feedback_units_chain: never by hand). Device-book scale = rec columns net_ex (bps/anchor of the device book whose
gross_total ≈ 0.6 of the L1-normalised target, identical scale to health_check RECEIPT_EX). per-gross = ÷ mean gross_total over the window; annualised = ×2190/1e4;
at 2.0×NAV = per-gross × 2. maxDD likewise. Reads judge.json (levels) — no new numbers, only conversions. Prints a markdown table."""
import json
J = json.load(open("/workspace/review_scratch/seat_round2/judge.json"))
rows = []
print("| cell | arm | window | net_ex bps/anchor (device scale) | gross_total | bps/anchor per gross | ann %/gross | ann % NAV @2× | Sharpe | maxDD bps (device) | maxDD %/gross | maxDD % NAV @2× |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for cell in ("prod/s42", "prod/s2027", "log/s42", "log/s2027"):
    for arm in ("B0", "B1", "B2", "B3", "B4", "B5", "B6"):
        for w in ("2024->26", "2025->26"):
            r = J["levels"][f"{cell}/{arm}"][w]; g = r["gross"]; pg = r["mean"] / g; ann = pg * 2190 / 1e4 * 100; dd = r["maxDD"] / g / 1e4 * 100
            print(f"| {cell} | {arm} | {w} | {r['mean']:+.3f} | {g:.3f} | {pg:+.3f} | {ann:+.1f}% | {2 * ann:+.1f}% | {r['sharpe']:+.2f} | {r['maxDD']:.0f} | {dd:.1f}% | {2 * dd:.1f}% |")
