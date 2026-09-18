#!/usr/bin/env python3
"""Tests for fp3_cash_recon.py (v4). The seven fixtures are the independent reviewer's round-7 probes (a5bda8bf cash/probe_engine.py), re-hosted through
the FP3_LEDGER_ROOT override so the EXACT module runs; plus one timing control. Red→green for v3→v4: wrong_calendar_funding_window (v3 RECONCILED, must be
PARTIAL with residual +5) and future_readback_mark (v3 PARTIAL/100, must be RECONCILED/0). usage: tests_fp3_cash_recon.py"""
import json, os, sys, subprocess, tempfile, calendar, pathlib
HERE = pathlib.Path(__file__).resolve().parent; ENGINE = HERE / "fp3_cash_recon.py"; T = calendar.timegm((2026, 9, 12, 0, 0, 0)); DAY = "20260912"
def fill(tid, sec, qty=1, px=100, side="BUY", fee=0, anchor=None):
    return dict(order_type="maker", trade_id=tid, symbol="AUSDT", side=side, fill_ts=T + sec, anchor_ts=T + (sec // 14400 * 14400 if anchor is None else anchor), fill_notional=qty * px, fill_px=px, commission=fee, commission_asset="USDT", venue_maker_flag=True)
def nav(cut=20 * 3600, rp=0, fee=0, fund=0):
    return dict(day=DAY, mode="LIVE", nav_ts=T + cut, nav=10000, prev_nav=10000, unrealised_pnl=0, external_flow_usdt=0, realised_by_type={"REALIZED_PNL": rp, "COMMISSION": -fee, "FUNDING_FEE": fund}, realised_by_type_asset={"COMMISSION": {"USDT": -fee}})
def rb(sec, q, px): return dict(anchor_ts=T + sec // 14400 * 14400, read_ts=T + sec, symbol="AUSDT", venue_position_qty=q, venue_position_notional=q * px, source="fapi/v3/account@post_anchor")
def run(name, data):
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"cash_{name}_")); led = root / "ledger"; (led / DAY).mkdir(parents=True)
    for n in ("fills", "orders", "funding", "position_readback", "daily_nav", "anchors"): (led / DAY / f"{n}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in data.get(n, [])))
    for day, extra in data.get("_extra_days", {}).items():
        (led / day).mkdir()
        for n in ("fills", "orders", "funding", "position_readback", "daily_nav", "anchors"): (led / day / f"{n}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in extra.get(n, [])))
    out = root / "out.json"; r = subprocess.run([sys.executable, str(ENGINE), str(out), "20260912", "20260913"], capture_output=True, text=True, env=dict(os.environ, FP3_LEDGER_ROOT=str(led), PYTHONDONTWRITEBYTECODE="1"))
    assert r.returncode == 0, (name, r.stderr[-800:]); return json.loads(out.read_text())
res = {}; fails = []
def check(name, cond, extra=""):
    res[name] = bool(cond); print(("PASS " if cond else "FAIL ") + name, "" if cond else extra)
    if not cond: fails.append(name)
j = run("unknown_cost_basis", {"fills": [fill("closing", 4 * 3600 + 10, 10, 110, "SELL")], "position_readback": [rb(60, 10, 100), rb(4 * 3600 + 60, 0, 110)], "daily_nav": [nav(rp=100)]})
u = j["positions_vs_readback"]["realised_unknown"]; check("R01 unknown cost basis: no realised number is invented", j["daily"][0]["local_realized_known"] == 0 and u["n_fills"] == 1 and u["notional"] == 1100, (j["daily"][0], u))
j = run("slip_population", {"fills": [fill("a", 10, 100, 100), fill("b", 4 * 3600 + 10, 1, 100)], "orders": [dict(anchor_ts=T, filled_notional=100, avg_fill_px=99.9, mid_at_anchor=100, intended_notional=100), dict(anchor_ts=T + 4 * 3600, filled_notional=100, avg_fill_px=100.1, mid_at_anchor=100, intended_notional=100)], "daily_nav": [nav()]})
b = j["cost_summary"]["all_anchors"]; check("R02 slippage on the matched population only", b["slippage_bps_matched"] == 0 and b["slip_coverage"] == 0.020, b)
j = run("cutoff_native_fee", {"fills": [fill("pre", 8 * 3600, 1, 100, fee=1), fill("post", 16 * 3600, 1, 100, fee=2)], "funding": [dict(settlement_ts=T + 8 * 3600, funding_paid=-5), dict(settlement_ts=T + 16 * 3600, funding_paid=-7)], "daily_nav": [nav(cut=12 * 3600, fee=1, fund=-5)]})
c = j["daily"][0]; check("R03 one cutoff for USDT-equivalent, native and funding", c["d_commission_total"] == 0 and c["d_commission_by_asset"]["USDT"] == 0 and c["d_funding"] == 0, c)
f = fill("same", 8 * 3600, 1, 100, fee=1); new = dict(f, commission=2, backfilled_utc="2026-09-13T00:00:00Z")
j = run("dedup_positive", {"fills": [f, new], "daily_nav": [nav(fee=2)]}); check("dedup: latest backfilled row wins", j["fills"]["distinct_trade_ids"] == 1 and j["cost_summary"]["all_anchors"]["fee_bps_of_traded"] == 200, j["fills"])
t0 = T + 20 * 3600 + 1800; t1 = t0 + 86400
n0 = dict(nav(), nav_ts=t0, nav=1000); n1 = dict(nav(), day="20260913", nav_ts=t1, nav=1000)
base = {"daily_nav": [n0], "position_readback": [rb(20 * 3600 + 1800, 0, 100)], "_extra_days": {"20260913": {"daily_nav": [n1], "position_readback": [rb(86400 + 20 * 3600 + 1800, 0, 100)]}}}
j = run("identity_positive", base); check("identity positive control: same-time marks, no activity ⇒ RECONCILED, residual 0", j["VERDICT"] == "RECONCILED" and j["nav_identity"]["n_ok"] == 1 and j["nav_identity"]["windows"][0]["residual"] == 0, j["nav_identity"])
case = {**base, "position_readback": [rb(20 * 3600 + 1800, 10, 100)], "_extra_days": {"20260913": {"daily_nav": [n1], "position_readback": [rb(86400 + 20 * 3600 + 1800, 10, 100)]}}, "funding": [dict(symbol="AUSDT", settlement_ts=T + 22 * 3600, funding_paid=-5, funding_interval_h=1)]}
j = run("wrong_calendar_funding_window", case); w = j["nav_identity"]["windows"][0]
check("★ R7-C1 (v3 RECONCILED): a −5 settlement inside the NAV window but outside the end-day calendar income ⇒ residual +5 > tol ⇒ PARTIAL; the calendar substitute is a diagnostic only", j["VERDICT"] == "PARTIAL" and w["residual"] == 5 and w["ok"] is False and w["diag_calendar_substitute"]["NOT_A_GATE"] is True, (j["VERDICT"], w))
r0q = rb(20 * 3600 + 1800, 10, 100); r1q = rb(86400 + 20 * 3600 + 1800, 10, 110); later = rb(86400 + 20 * 3600 + 2400, 10, 100)
case = {"daily_nav": [n0], "position_readback": [r0q], "_extra_days": {"20260913": {"daily_nav": [dict(n1, nav=1100)], "position_readback": [r1q, later]}}}
j = run("future_readback_mark", case); w = j["nav_identity"]["windows"][0]
check("★ R7-C2 (v3 PARTIAL/100): the same-call snapshot (mark 110) is used, not the later readback in the same 4h bucket ⇒ residual 0, RECONCILED; snapshot times recorded", j["VERDICT"] == "RECONCILED" and w["residual"] == 0 and w["snapshot_minus_nav_s"] == [0.0, 0.0], (j["VERDICT"], w))
case = {"daily_nav": [n0], "position_readback": [r0q], "_extra_days": {"20260913": {"daily_nav": [dict(n1, nav=1100)], "position_readback": [later]}}}
j = run("no_snapshot_at_nav", case); w = j["nav_identity"]["windows"][0]
check("timing control: the only readback is 10 min after the NAV row ⇒ UNAVAILABLE_TIMING, not a residual", j["VERDICT"] == "UNAVAILABLE" and w.get("status", "").startswith("UNAVAILABLE_TIMING"), (j["VERDICT"], w))
print(f"RESULT {len(res) - len(fails)}/{len(res)} pass", "FAILS:" if fails else "", fails); sys.exit(1 if fails else 0)
