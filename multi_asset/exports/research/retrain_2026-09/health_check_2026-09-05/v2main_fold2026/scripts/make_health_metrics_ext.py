"""Derive health_metrics_ext.py from health_check/health_metrics.py (sha 6cdb34f3…) by anchored edits: ROOT -> this campaign's replay dir; windows added
2026->0830, 2026-08-11->0830, 2024->0830, 2025->0830, 2026-Q3->0830 (bootstrapped); 2026-postcut flag made neutral; monthly_to_0830 table added. Nothing else changed."""
import hashlib, sys
s = open(sys.argv[1]).read(); assert hashlib.sha256(s.encode()).hexdigest().startswith("6cdb34f32d3294e4"), "base health_metrics sha mismatch"
def rep(old, new, count=1):
    global s; assert s.count(old) == count, (old[:70], s.count(old)); s = s.replace(old, new)
rep('ROOT = "/workspace/review_scratch/health_check"\n', 'ROOT = "/workspace/review_scratch/v2main_fold2026/replay"   # health_metrics_ext (v2main_fold2026): ROOT redirected; base = health_check/health_metrics.py sha 6cdb34f3…\n')
rep('CUT = T("2026-08-10") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(CUT)) == "2026-08-10 20:00"\n',
    'CUT = T("2026-08-10") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(CUT)) == "2026-08-10 20:00"\n'
    'END = T("2026-08-30") + 20 * 3600; assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(END)) == "2026-08-30 20:00"   # ext2026: last anchor with the F10 leg from the new fold\n')
rep('       "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1), "2026-postcut": (CUT + 1, 2**40)}\n',
    '       "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1), "2025->26": (T("2025-01-01"), CUT + 1), "2026-postcut": (CUT + 1, 2**40),\n'
    '       "2026->0830": (T("2026-01-01"), END + 1), "2026-08-11->0830": (CUT + 1, END + 1), "2024->0830": (T("2024-01-01"), END + 1), "2025->0830": (T("2025-01-01"), END + 1), "2026-Q3->0830": (T("2026-07-01"), END + 1)}\n')
rep('FLAG = {"2024-H1": "seat warm-up (pinned king NaN before 2024; msharpe-900 window fills ~2024-06)", "2026-postcut": "F10 leg absent after 2026-08-10 20:00Z — NOT the live form", "2026-Q3": "→ cut 2026-08-10 20:00Z"}\n',
    'FLAG = {"2024-H1": "seat warm-up (pinned king NaN before 2024; msharpe-900 window fills ~2024-06)", "2026-postcut": "anchors after the health_check cut 2026-08-10 20:00Z (F10 leg present iff FPRED covers them — see config.FPRED)", "2026-Q3": "→ cut 2026-08-10 20:00Z",\n'
    '        "2026->0830": "ext2026: F10 leg from the new 2026 fold over the whole window", "2026-08-11->0830": "ext2026 stretch: F10 leg present (new fold); 120 anchors / 20 days", "2024->0830": "full-through incl. 08-11→08-30", "2025->0830": "full-through incl. 08-11→08-30", "2026-Q3->0830": "Q3 through 08-30"}\n')
rep('BOOT_WINDOWS = ("2024", "2024-H2", "2025", "2026->cut", "2024->26", "2025->26")\n', 'BOOT_WINDOWS = ("2024", "2024-H2", "2025", "2026->cut", "2024->26", "2025->26", "2026->0830", "2026-08-11->0830", "2024->0830", "2025->0830")\n')
rep('        mm = (months == mo) & (ts <= CUT); r = g[mm] * 2.0; out["monthly"][str(mo)] = {"n": int(mm.sum()), "mean_bps_anchor_per_gross": r4(g[mm].mean()), "nav_pct_at_2x": r4(np.expm1(np.log1p(r / 1e4).sum()) * 100), "sharpe_anchor": r4(sharpe(g[mm], APY))}\n',
    '        mm = (months == mo) & (ts <= CUT); r = g[mm] * 2.0; out["monthly"][str(mo)] = {"n": int(mm.sum()), "mean_bps_anchor_per_gross": r4(g[mm].mean()), "nav_pct_at_2x": r4(np.expm1(np.log1p(r / 1e4).sum()) * 100), "sharpe_anchor": r4(sharpe(g[mm], APY))}\n'
    '    um2 = sorted(set(months[(ts >= T("2024-01-01")) & (ts <= END)].tolist())); out["monthly_to_0830"] = {}   # ext2026: same table through 08-30 (2026-08 = full month to 08-30 20:00Z)\n'
    '    for mo in um2:\n'
    '        mm = (months == mo) & (ts <= END); r = g[mm] * 2.0; out["monthly_to_0830"][str(mo)] = {"n": int(mm.sum()), "mean_bps_anchor_per_gross": r4(g[mm].mean()), "nav_pct_at_2x": r4(np.expm1(np.log1p(r / 1e4).sum()) * 100), "sharpe_anchor": r4(sharpe(g[mm], APY))}\n')
open(sys.argv[2], "w").write(s); print("written", sys.argv[2], "sha256", hashlib.sha256(s.encode()).hexdigest())
