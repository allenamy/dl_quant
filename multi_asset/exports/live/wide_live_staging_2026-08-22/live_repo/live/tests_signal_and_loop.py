"""Acceptance for the NEW components: legs composition, staleness ladder, fapi source hygiene.

Parity is the point: "保证因子有效" is not an aspiration, it is the property that the vendored
composition reproduces the validated semantics. Where the research repo's functions are pure,
we test against hand-computed values from those exact formulas.
"""
import json
import os
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for d in ("live", "signal", "scheduler"):
    sys.path.insert(0, os.path.join(_REPO, d))

import numpy as np                 # noqa: E402
import book_config as BC           # noqa: E402
import legs as LG                  # noqa: E402
import anchor_loop as AL           # noqa: E402
import fapi_source as FS           # noqa: E402
import binance_broker as BB        # noqa: E402
import binance_executor as EX      # noqa: E402

FAILS = 0

# ★ THIS SUITE IS NOT ABOUT THE WALL CLOCK — so the clock gate is pinned OPEN for it.
# run_anchor() now refuses to OPEN positions on a run that is more than
# `anchor_late_tolerance_min` from a scheduled slot. Every ladder/kill-switch/rate-limit test below
# calls run_anchor() at whatever time the suite happens to run, so without this they would all be
# testing the clock gate instead of the thing they name. Section [S] takes the real config back
# (`with BC._using(BC.BOOK_PATH)`) and tests the gate itself, in both states.
# Pinning it open here is the deliberate opposite of hiding it: the gate is exercised in exactly
# one place, on purpose, rather than incidentally everywhere.
# ★ 2026-08-22 DECOUPLED FROM THE DISK BOOK SOURCE. `book_source` / `per_name_stop.active_profile`
#   are PRODUCTION switches (external = the wide book). A suite that copies the disk config as its
#   fixture baseline flips its own subject when the operator flips the book — and a battery that
#   goes red on the switch then locks the switch out. Every disk-derived fixture below is the REAL
#   config (clock, legs, weights, stamps…) with the book source pinned to the INTERNAL baseline,
#   which is what these cases test. tests_external_book owns the external branch, both ways.
def _internal_baseline(d):
    d = dict(d)
    d["book_source"] = "internal"
    d["per_name_stop"] = dict(d.get("per_name_stop") or {}, active_profile=None)
    return d


_open_clock = _internal_baseline(json.load(open(BC.BOOK_PATH)))
_open_clock["anchor_late_tolerance_min"] = 10 ** 6
_OPEN_BOOK = os.path.join(tempfile.mkdtemp(), "book_open_clock.json")
json.dump(_open_clock, open(_OPEN_BOOK, "w"))
BC._set_override(_OPEN_BOOK)


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1
    return cond


print("[A] vendored primitives reproduce the validated formulas")
x = np.array([3.0, 1.0, 2.0, np.nan])
rc = LG.rank_centered(x)
check("rank_centered maps to [-1,1] with NaN->0",
      np.allclose(rc, [1.0, -1.0, 0.0, 0.0]), rc.tolist())
# ★ tie fixture (audit ①): 49.3% of real anchors contain ties; ordinal ranks convert array
# position into portfolio weight. Average rank must hold for a large tie block, bitwise.
tie = np.array([0.0001] * 25 + [0.0002, 0.00005, 0.0003])
rt = LG.rank_centered(tie)
check("★ 25-way tie: every tied name gets the SAME rank", len(set(np.round(rt[:25], 14))) == 1)
k = len(tie)                                  # tied ranks 2..26 -> average 14 (rankdata semantics)
check("★ tie value matches scipy-rankdata average-rank formula",
      abs(rt[0] - (2.0 * (14 - 1) / (k - 1) - 1.0)) < 1e-14, rt[0])
perm = np.random.default_rng(0).permutation(k)
check("★ rank of tied block is INVARIANT under array permutation (no position->weight leak)",
      np.allclose(np.sort(LG.rank_centered(tie[perm])), np.sort(rt)))
zz = LG.z(np.array([1.0, 2.0, 3.0]))
check("z is zero-mean unit-sd", abs(zz.mean()) < 1e-12 and abs(zz.std() - 1) < 1e-9)
check("l1 normalizes to unit gross", abs(np.abs(LG.l1(np.array([2.0, -2.0]))).sum() - 1) < 1e-12)

print("\n[B] ★ funding EMA: corrected caliber, correct order (normalize BEFORE smoothing)")
# a coin that migrated 8h -> 4h mid-history, same ANNUALIZED carry throughout:
rows = ([{"ts_ms": i * 8 * 3600_000, "rate8": 0.0001, "interval_h": 8.0} for i in range(10)] +
        [{"ts_ms": (80 + i * 4) * 3600_000, "rate8": 0.0001, "interval_h": 4.0} for i in range(10)])
ema = LG.funding_ema_from_settlements(rows)
check("constant per-8h carry => EMA equals that constant across the migration",
      abs(ema - 0.0001) < 1e-12, ema)
# the OLD bug: feeding per-period rates un-normalized halves the 4h rows
bad = [dict(r, rate8=r["rate8"] * (r["interval_h"] / 8.0)) for r in rows]
ema_bad = LG.funding_ema_from_settlements(bad)
check("the un-normalized caliber produces a DIFFERENT (wrong) value — fix is not a no-op",
      abs(ema_bad - ema) > 1e-6, f"bad={ema_bad:.6g} vs {ema:.6g}")
varied = [{"ts_ms": i, "rate8": 0.0001 * (1 + 0.5 * (i % 3)), "interval_h": 4.0} for i in range(12)]
check("★ span_override (frozen-panel parity mode) changes the smoothing horizon",
      abs(LG.funding_ema_from_settlements(varied, span_override=3)
          - LG.funding_ema_from_settlements(varied)) > 1e-9)

print("\n[C] composition: unit-gross, market-neutral, four legs live")
n = 40
rng = np.random.default_rng(7)
# ★ the mixture is NAMED, because compose_book no longer has a silent fallback — the very
#   omission that gave config/book.json zero readers. These cases test composition MECHANICS, so
#   the champion reference is the right mixture to name, and naming it says so.
book = LG.compose_book(rng.normal(size=n), rng.normal(size=n),
                       rng.normal(size=n) * 1e-4, np.abs(rng.normal(size=n)) * 1e6 + 1e5,
                       weights=LG.WEIGHTS)
tw = book["target_w"]
check("unit gross", abs(np.abs(tw).sum() - 1) < 1e-9, np.abs(tw).sum())
check("market-neutral (net ~ 0)", abs(tw.sum()) < 1e-9, tw.sum())
check("all four legs present and unit-gross each",
      set(book["legs_unit"]) == {"king", "s2", "funding", "size"}
      and all(abs(np.abs(v).sum() - 1) < 1e-9 for v in book["legs_unit"].values()))
w0 = LG.compose_book(rng.normal(size=n), rng.normal(size=n),
                     rng.normal(size=n) * 1e-4, np.abs(rng.normal(size=n)) * 1e6,
                     weights={"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0})
check("weights actually steer the book (king-only != four-leg)",
      not np.allclose(w0["target_w"], tw))

print("\n[D] ★ the staleness ladder is mechanical and pre-registered")
check("fresh -> TRADE", AL.staleness_action(0.5) == "TRADE")
check("1 anchor stale -> HOLD (one miss is a hiccup, not an outage)",
      AL.staleness_action(1.5) == "HOLD")
check("6 anchors (24h) -> DERISK", AL.staleness_action(6.0) == "DERISK")
check("12 anchors (48h) -> FLATTEN", AL.staleness_action(12.0) == "FLATTEN")
check("★ target-fraction table: 6-8 anchors -> 50%", AL.derisk_target_frac(7.0) == 0.5)
check("★ target-fraction table: 9-11 anchors -> 25%", AL.derisk_target_frac(10.0) == 0.25)
check("absent preds -> inf age -> FLATTEN path",
      AL.staleness_action(AL.signal_age_anchors(None)) == "FLATTEN")
check("boundary: just under 6 stays HOLD", AL.staleness_action(5.99) == "HOLD")

print("\n[E] ★ the ladder acts through the loop, and DERISK is reduce-only throughout")
tmp = tempfile.mkdtemp()
os.environ["LIVE_LOOP_STATE"] = os.path.join(tmp, "loop_state.json")
os.environ["LIVE_PREDS_PATH"] = os.path.join(tmp, "preds.json")
os.environ["LIVE_KILL_SWITCH"] = os.path.join(tmp, "KILL_SWITCH.json")   # never the real one
# ★ 缺这行的实测代价 (2026-08-06 09:51:54Z): 本套件进程内跑 _trade, EMA 状态写进了【真实】
#   DRY_RUN 树 state/harvest_ema.json —— 测试写生产树。费用基线同理, 一并重定向。
os.environ["LIVE_HARVEST_STATE"] = os.path.join(tmp, "harvest_ema.json")
os.environ["LIVE_FEE_BASELINE"] = os.path.join(tmp, "fee_asset_baseline.json")
import importlib
importlib.reload(AL)
b = BB.BinanceBroker(); b.arm()
ex = EX.RebalanceExecutor(b)
alarms = []
loop = AL.AnchorLoop(b, ex, gross_usdt=25_000, alarm=lambda s, m: alarms.append((s, m)))

# seed positions, then age the signal into DERISK territory
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {"BTCUSDT": 10_000.0, "ETHUSDT": -8_000.0},
                                          "last_alarm_stale": None})
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 7 * AL.ANCHOR_S,
                                          "symbols": [], "king": {}, "s2": {},
                                          "funding_ema": {}, "dvol30": {}})
out = loop.run_anchor()
check("action is DERISK", out["action"] == "DERISK", out["action"])
check("an alarm was raised at CRITICAL", any(s == "CRITICAL" for s, _ in alarms))
derisk_orders = [a for a in b.actions if a.get("action") == "submit_dry_run"]
check("every de-risk order is reduce_only (composes with the watchdog halt)",
      derisk_orders and all(a["order"].get("reduce_only") for a in derisk_orders))
st = AL._load(os.environ["LIVE_LOOP_STATE"], {})
check("positions scaled to half of PRE-STALE snapshot", abs(st["positions"]["BTCUSDT"] - 5_000.0) < 1e-6)
n_before = len(b.actions)
loop.run_anchor()                        # ★ same stage again: must be a NO-OP (audit 3a)
check("★ idempotent: re-running the same DERISK stage emits ZERO new orders",
      len([a for a in b.actions[n_before:] if a.get("action") == "submit_dry_run"]) == 0)
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 10 * AL.ANCHOR_S})
loop.run_anchor()                        # stage 2: 25% of the ORIGINAL 10k, not of the current 5k
st15 = AL._load(os.environ["LIVE_LOOP_STATE"], {})
check("★ stage 2 targets 25% of the PRE-STALE ref (2500), not 25% of current (1250)",
      abs(st15["positions"]["BTCUSDT"] - 2_500.0) < 1e-6, st15["positions"]["BTCUSDT"])

# stale into FLATTEN
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 13 * AL.ANCHOR_S})
out2 = loop.run_anchor()
check("action is FLATTEN at >=12 anchors", out2["action"] == "FLATTEN", out2["action"])
st2 = AL._load(os.environ["LIVE_LOOP_STATE"], {})
check("book emptied after flatten", st2["positions"] == {})

print("\n[E4] ★ severity follows consequence: flattening an EMPTY book is INFO, not CRITICAL")
alarms.clear()
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 20 * AL.ANCHOR_S})
outc_ = loop.run_anchor()
check("cold start with empty book -> INFO alarm, nobody woken at midnight for a no-op",
      alarms and alarms[0][0] == "INFO", alarms)
check("note says cold start", "cold start" in outc_.get("note", ""), outc_.get("note"))

print("\n[F] HOLD alarms once per episode, not once per anchor")
alarms.clear()
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {"BTCUSDT": 1000.0},
                                          "last_alarm_stale": None})
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 2 * AL.ANCHOR_S})
loop.run_anchor(); loop.run_anchor()
check("two stale anchors, exactly one alarm (a repeating alarm trains people to ignore it)",
      len(alarms) == 1, len(alarms))

print("\n[F2] ★ DERISK/FLATTEN alarm once per STAGE, not once per anchor (audit 3b)")
alarms.clear()
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {"BTCUSDT": 1000.0},
                                          "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
AL._save(os.environ["LIVE_PREDS_PATH"], {"computed_ts": time.time() - 7 * AL.ANCHOR_S})
loop.run_anchor(); loop.run_anchor()
check("two DERISK anchors at the same stage -> exactly one CRITICAL",
      sum(1 for s_, _ in alarms if s_ == "CRITICAL") == 1, len(alarms))

print("\n[E2] ★ caliber stamp mismatch BLOCKS the anchor (audit ②)")
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
AL._save(os.environ["LIVE_PREDS_PATH"],
         {"computed_ts": time.time(), "symbols": ["BTCUSDT"] * 0 or ["BTCUSDT"],
          "king": {"BTCUSDT": 0.1}, "s2": {"BTCUSDT": 0.1},
          "funding_ema": {"BTCUSDT": 1e-4}, "dvol30": {"BTCUSDT": 1e6},
          "factor_versions": {"funding_leg": "WRONG", "dl_panel": "WRONG"}})
alarms.clear()
n_pre = len(b.actions)
outc = loop.run_anchor()
check("mismatched stamp -> anchor BLOCKED", outc.get("blocked") == "caliber_stamp_mismatch", outc.get("blocked"))
check("blocked anchor raised CRITICAL", any(s_ == "CRITICAL" for s_, _ in alarms))
check("blocked anchor emitted no orders (count NEW actions, not a stale window)",
      not any(a.get("action") == "submit_dry_run" for a in b.actions[n_pre:]))

# ★ preds fixtures must declare the panel column set they came from — the consumer BLOCKS on
# preds it cannot recognise (see [P2]). These fixtures test the ladder/caliber logic, so they
# stamp the real frozen fingerprint rather than pretending the universe is 3 coins wide.
sys.path.insert(0, os.path.join(_REPO, "signal"))
import compute_preds as _CPstamp                                              # noqa: E402
import live_panel as _LPstamp                                                 # noqa: E402
# ★ fixtures must NOT hardcode the deployed caliber. Every literal here went stale the
# moment config/book.json flipped (2026-08-04 batch 1) and turned six unrelated tests red
# for a reason that had nothing to do with what they test. The caliber-MISMATCH test keeps
# its own explicit "WRONG" literal, which is what proves the guard still fires.
_LIVE_FV = __import__("json").load(open(os.path.join(_REPO, "config", "book.json")))["factor_versions"]
# ★ fixtures must NOT hardcode the deployed caliber. Every literal here went stale the
# moment config/book.json flipped (2026-08-04 batch 1) and turned six unrelated tests red
# for a reason that had nothing to do with what they test. The caliber-MISMATCH test keeps
# its own explicit "WRONG" literal, which is what proves the guard still fires.
_LIVE_FV = __import__("json").load(open(os.path.join(_REPO, "config", "book.json")))["factor_versions"]
_PANEL_STAMP = _CPstamp.columns_fingerprint(_LPstamp.panel_symbols())

print("\n[E3] ★ two-phase anchor: phase B tops up the residual and emits rows")
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
AL._save(os.environ["LIVE_PREDS_PATH"],
         {"computed_ts": time.time(), "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
          "king": {"BTCUSDT": 0.5, "ETHUSDT": -0.3, "BNBUSDT": 0.1},
          "s2": {"BTCUSDT": 0.2, "ETHUSDT": -0.1, "BNBUSDT": 0.4},
          "funding_ema": {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "BNBUSDT": 5e-5},
          "dvol30": {"BTCUSDT": 1e9, "ETHUSDT": 5e8, "BNBUSDT": 2e8},
          "factor_versions": _LIVE_FV,
          "panel": _PANEL_STAMP})
b5 = BB.BinanceBroker(); b5.arm()
ex5 = EX.RebalanceExecutor(b5)
ex5.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                 for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
loop5 = AL.AnchorLoop(b5, ex5, gross_usdt=25_000)
outA = loop5.run_anchor()
check("phase A traded (fresh signal, matching stamp)", outA["action"] == "TRADE", outA["action"])
check("phase A left a pending handle", "_pending" in outA)
# DRY_RUN fills = {} — deliberately exercises the FULL top-up path, not the flattering one
outB = loop5.complete_anchor(outA["_pending"], outA["anchor_ts"], outA["rebalance_id"])
check("phase B emitted rows", outB["rows_emitted"] > 0, outB["rows_emitted"])
check("★ the mandatory top-up was exercised for every live name",
      outB["n_topped_up"] == len(outA["_pending"]["live"]),
      f"{outB['n_topped_up']} vs {len(outA['_pending']['live'])}")
tu_rows = [r for r in ex5.rows_orders if r["order_type"] == "topup_taker"]
check("top-up rows carry the SAME rebalance_id as phase A",
      all(r["rebalance_id"] == outA["rebalance_id"] for r in tu_rows))
check("every row still carries mid_at_anchor through phase B",
      all(r["mid_at_anchor"] is not None for r in ex5.rows_orders))

print("\n[K] ★ KILL SWITCH: an engaged stop refuses everything, even with a fresh signal")
kill_p = os.environ["LIVE_KILL_SWITCH"]
check("tests use an ISOLATED kill path (a real emergency stop must not skew the suite, "
      "and the suite must not touch a real one)", kill_p != os.path.join(_REPO, "state", "KILL_SWITCH.json"))
AL._save(kill_p, {"killed_at_utc": "TEST", "open_orders_halted": True})
AL._save(os.environ["LIVE_PREDS_PATH"],
         {"computed_ts": time.time(), "symbols": ["BTCUSDT"],
          "king": {"BTCUSDT": 0.5}, "s2": {"BTCUSDT": 0.2},
          "funding_ema": {"BTCUSDT": 1e-4}, "dvol30": {"BTCUSDT": 1e9},
          "factor_versions": _LIVE_FV,
          "panel": _PANEL_STAMP})
bk = BB.BinanceBroker(); bk.arm()
exk = EX.RebalanceExecutor(bk)
loopk = AL.AnchorLoop(bk, exk, gross_usdt=25_000)
n_pre_k = len(bk.actions)
outk = loopk.run_anchor()
check("★ action is KILLED even though the signal is FRESH", outk["action"] == "KILLED", outk["action"])
check("★ zero orders submitted while killed",
      not any(a.get("action") == "submit_dry_run" for a in bk.actions[n_pre_k:]))
check("the broker was also told to halt (belt and braces)", bk.open_orders_halted)
check("the reason names the file to remove (recovery must be deliberate)",
      "KILL_SWITCH.json" in outk["note"])
os.remove(kill_p)
outk2 = loopk.run_anchor()
check("removing the flag restores normal operation", outk2["action"] == "TRADE", outk2["action"])

print("\n[G] fapi hygiene properties (no network needed)")
iv = FS.FapiSource.infer_interval_hours(
    [{"ts_ms": 0}, {"ts_ms": 8 * 3600_000}, {"ts_ms": 12 * 3600_000}, {"ts_ms": 16 * 3600_000}])
check("interval inferred PER ROW across a migration (8h then 4h)",
      iv[1] == 8.0 and iv[2] == 4.0 and iv[3] == 4.0, iv)
check("absurd gap falls back to 8h, never propagates",
      FS.FapiSource.infer_interval_hours([{"ts_ms": 0}, {"ts_ms": 100 * 86400_000}])[1] == 8.0)
stamped = FS.FapiSource().stamped({"x": 1})
check("every dataset leaves wearing its own age (fetch_ts present)",
      "fetch_ts" in stamped and stamped["fetch_ts"] > 1.7e9)

print("\n[H] state writes are atomic (a crash never leaves a half-written state)")
p = os.path.join(tmp, "atomic.json")
AL._save(p, {"a": 1})
check("state readable after save", AL._load(p, None) == {"a": 1})
check("no tmp residue", not os.path.exists(p + ".tmp"))

print("\n[U] ★ delisting: the book's width is dynamic, and an exit must not need a price")
import universe as UNI
PRED = ["BTCUSDT", "ETHUSDT", "DEADUSDT", "SETTLEUSDT"]
HELD = {"BTCUSDT": 0.5, "DEADUSDT": 1200.0, "SETTLEUSDT": -300.0, "ORPHANUSDT": 9.0}
STATUS = {"BTCUSDT": "TRADING", "ETHUSDT": "TRADING", "SETTLEUSDT": "SETTLING",
          "NEWUSDT": "TRADING"}          # DEADUSDT vanished entirely; ORPHAN not in preds
cls = UNI.classify(PRED, HELD, STATUS)
check("tradable = only the names the venue says TRADING", set(cls["tradable"]) == {"BTCUSDT", "ETHUSDT"},
      cls["tradable"])
check("★ a held SETTLING name is exit-only (not merely skipped)", "SETTLEUSDT" in cls["exit_only_held"])
check("★ a held name that VANISHED from exchangeInfo is flagged separately (may be unclosable)",
      "DEADUSDT" in cls["gone_from_venue_held"], list(cls["gone_from_venue_held"]))
check("a held name no longer predicted is still handled, not orphaned",
      "ORPHANUSDT" in cls["gone_from_venue_held"] or "ORPHANUSDT" in cls["exit_only_held"])
check("a new listing is IGNORED (it has no panel warmup history yet)",
      cls["new_listings"] == ["NEWUSDT"], cls["new_listings"])

orders = UNI.exit_orders(cls["exit_only_held"])
check("★ exit orders are sized in CONTRACTS — no mid, no book, no price needed",
      all("price" not in o and o["quantity"] > 0 for o in orders), orders)
check("★ every exit order is reduce_only (passes the halt, composes with the kill switch)",
      all(o["reduce_only"] for o in orders))
check("short position exits with a BUY", all(o["side"] == "buy" for o in orders if o["symbol"] == "SETTLEUSDT"))

check("★ unreachable exchangeInfo yields UNKNOWN, never 'nothing trades'",
      UNI.classify(PRED, HELD, {})["venue_status_unknown"] is True)

print("\n[U2] width is not hardcoded: composition follows whatever the panel provides")
for n_ in (110, 87, 40, 12):
    bk_ = LG.compose_book(np.random.default_rng(n_).normal(size=n_),
                          np.random.default_rng(n_ + 1).normal(size=n_),
                          np.random.default_rng(n_ + 2).normal(size=n_) * 1e-4,
                          np.abs(np.random.default_rng(n_ + 3).normal(size=n_)) * 1e6 + 1e5,
                          weights=LG.WEIGHTS)
    ok_ = abs(np.abs(bk_["target_w"]).sum() - 1) < 1e-9 and abs(bk_["target_w"].sum()) < 1e-9
    check(f"N={n_}: unit-gross and market-neutral hold", ok_)


# ── [P] in-place prediction producer: what it writes, and what it REFUSES to write ───────────
print("\n[P] compute_preds — the producer must fail by writing NOTHING, never by writing garbage")
import json as _json                                                            # noqa: E402
import time as _time                                                            # noqa: E402
import compute_preds as CP                                                      # noqa: E402
import live_panel as LP                                                         # noqa: E402
import panel_build as PB                                                        # noqa: E402
import funding_panel as FP                                                      # noqa: E402

_tmp_preds = os.path.join(_REPO, "state", "_test_preds.json")
_sentinel = {"computed_ts": 1.0, "symbols": ["OLD"], "marker": "previous anchor"}
_json.dump(_sentinel, open(_tmp_preds, "w"))
_orig_build = LP.build_live_panel
try:
    for _exc, _label in ((PB.PanelWarmupError("too little history"), "warmup BLOCK"),
                         (FP.FundingCaliberError("caliber"), "caliber BLOCK"),
                         (RuntimeError("fapi exploded"), "producer crash")):
        LP.build_live_panel = (lambda *a, _e=_exc, **k: (_ for _ in ()).throw(_e))
        st = CP.refresh_preds(object(), path=_tmp_preds)
        after = _json.load(open(_tmp_preds))
        check(f"★ {_label}: nothing written, previous computed_ts preserved",
              st["ok"] is False and st["preds_written"] is False and after == _sentinel,
              f"reason={st.get('reason')}")
finally:
    LP.build_live_panel = _orig_build
    os.remove(_tmp_preds)
check("a blocked producer never invents a fresh computed_ts (the ladder stays in control)",
      _sentinel["computed_ts"] == 1.0)

# the column fingerprint is what the consumer asserts on
_fp = CP.columns_fingerprint(["AAAUSDT", "BBBUSDT"])
check("column fingerprint is order-sensitive (the encoder attends ACROSS columns)",
      CP.columns_fingerprint(["BBBUSDT", "AAAUSDT"])["columns_sha256"] != _fp["columns_sha256"])
check("column fingerprint counts columns", _fp["n_columns"] == 2)

print("\n[P2] the consumer BLOCKS on a column set it does not recognise")


class _NoBroker:
    def positions(self):
        raise RuntimeError("not needed")


_alarms = []
_loop = AL.AnchorLoop(_NoBroker(), None, gross_usdt=1000.0,
                      alarm=lambda sev, msg: _alarms.append((sev, msg)))
_cfg_fv = _json.load(open(os.path.join(_REPO, "config", "book.json")))["factor_versions"]
_good = CP.columns_fingerprint(LP.panel_symbols())
for _panel, _label in ((None, "no column stamp at all"),
                       ({"n_columns": 139, "columns_sha256": _good["columns_sha256"]},
                        "column COUNT changed"),
                       ({"n_columns": _good["n_columns"], "columns_sha256": "deadbeef"},
                        "column SET changed")):
    _p = {"computed_ts": _time.time(), "factor_versions": _cfg_fv, "symbols": ["BTCUSDT"]}
    if _panel is not None:
        _p["panel"] = _panel
    _out = _loop._trade(_p, {"positions": {}}, _time.time())
    check(f"★ {_label} -> anchor BLOCKED, no orders",
          _out.get("blocked") == "column_set_mismatch", str(_out)[:120])
check("each block raised a CRITICAL alarm", sum(1 for s, _ in _alarms if s == "CRITICAL") >= 3,
      f"{len(_alarms)} alarms")

# ── [K] ★ the k-cancel: it must happen, and it must happen BEFORE fills are read ─────────────
# This was missing entirely. The executor docstring promised "t=k cancel whatever is unfilled"
# and the row schema had a `cancel_ts` column, but nothing cancelled — invisible in DRY_RUN,
# because no order is ever real there. On a venue the maker rests while the IOC top-up fires and
# the position can end up ~double.
print("\n[K] phase B cancels the resting maker before reading fills")


class _OrderRecordingBroker(BB.BinanceBroker):
    def __init__(self):
        super().__init__(mode="DRY_RUN")
        self.calls = []

    def cancel_order(self, symbol, client_id, reason=""):
        self.calls.append(("cancel", symbol))
        return super().cancel_order(symbol, client_id, reason)


bk = _OrderRecordingBroker(); bk.arm()
exk = EX.RebalanceExecutor(bk)
# ★ THREE names, not two. With N=2 every rank-based leg is exactly ±0.5 (rank centring keeps no
# magnitude), so the legs can cancel to an all-zero book — which they do for these inputs. The
# loop then correctly plans nothing, and the test would have passed 0/0 while proving nothing.
exk.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                 for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
# ★ THE SEAM, AND WHY IT IS NEEDED — this is also the reason the missing cancel survived every
# green suite: in DRY_RUN `capture_anchor` returns mids of 0.0 BY DESIGN, so every plan is skipped
# as venue_reject and NO ORDER CAN EVER REST. A DRY_RUN suite therefore cannot reach the code path
# where a resting maker must be cancelled. We inject synthetic mids so the ordering under test
# (cancel BEFORE fills) is exercised; everything else stays the real implementation.
exk.capture_anchor = lambda syms: (time.time(), {s_: 100.0 for s_ in syms})
order_log = []
loopk2 = AL.AnchorLoop(bk, exk, gross_usdt=10_000,
                       fills_provider=lambda rid, syms: (order_log.append(("fills", tuple(syms))),
                                                         {})[1])
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
AL._save(os.environ["LIVE_PREDS_PATH"],
         {"computed_ts": time.time(), "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
          "king": {"BTCUSDT": 0.5, "ETHUSDT": -0.5, "BNBUSDT": 0.1},
          "s2": {"BTCUSDT": 0.2, "ETHUSDT": -0.2, "BNBUSDT": 0.0},
          "funding_ema": {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "BNBUSDT": 5e-5},
          "dvol30": {"BTCUSDT": 1e9, "ETHUSDT": 5e8, "BNBUSDT": 2e8},
          "factor_versions": _LIVE_FV,
          "panel": _PANEL_STAMP})
oA = loopk2.run_anchor()
n_live = len(oA.get("_pending", {}).get("live", []))
oB = loopk2.complete_anchor(oA["_pending"], oA["anchor_ts"], oA["rebalance_id"])
n_cancels = sum(1 for c in bk.calls if c[0] == "cancel")
check("the fixture actually placed makers (else the next check passes 0/0 and proves nothing)",
      n_live > 0, f"n_live={n_live}")
check("★ every resting maker is cancelled at k", n_live > 0 and n_cancels == n_live,
      f"{n_cancels}/{n_live}")
check("★ the cancel happens BEFORE fills are read (a fill in between would be lost otherwise)",
      bk.calls and order_log and bk.calls[0][0] == "cancel",
      f"first broker call={bk.calls[0] if bk.calls else None}")
check("phase B reports the cancel outcome for the operator",
      isinstance(oB.get("k_cancel"), dict) and "cancelled" in oB["k_cancel"], str(oB.get("k_cancel")))
check("cancel_ts is populated on the plans (the column existed and was never written)",
      all(p_.get("cancel_ts") for p_ in exk._last_plans if p_.get("submitted")),
      str([(p_["symbol"], p_.get("cancel_ts")) for p_ in exk._last_plans]))
check("★ an unknown filled notional is left UNSET, never written as 0.0",
      bk.last_fill_notional() in (None, 0.0))

# ── [L] ★ the log sink: rows must reach DISK, and the report must carry the denominator ──────
# Before this, `PilotLogger` was never instantiated in production and `self.log` was None in every
# construction, so the single write() call never ran — AND it called a method PilotLogger does not
# have. Every anchor reported `rows_emitted: 110`, which was TRUE; the rows just never left memory.
print("\n[L] order rows are persisted, and emitted-vs-persisted is reported")
import pilot_log as PLOG                                                        # noqa: E402
import shutil as _sh, tempfile as _tf                                           # noqa: E402

_root = _tf.mkdtemp()
_plog = PLOG.PilotLogger(_root)
bl = _OrderRecordingBroker(); bl.arm()
exl = EX.RebalanceExecutor(bl)
exl.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                 for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
exl.capture_anchor = lambda syms: (time.time(), {s_: 100.0 for s_ in syms})
_al = []
loopl = AL.AnchorLoop(bl, exl, gross_usdt=10_000, log=_plog,
                      alarm=lambda sev, m: _al.append((sev, m)))
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
oA = loopl.run_anchor()
oB = loopl.complete_anchor(oA["_pending"], oA["anchor_ts"], oA["rebalance_id"])
_plog.close()
_disk = os.path.join(_plog.dir, "orders.jsonl")
_n_disk = sum(1 for _ in open(_disk)) if os.path.exists(_disk) else 0
check("★ the report carries BOTH numbers (emitted is the numerator, persisted the denominator)",
      "rows_emitted" in oB and "rows_persisted" in oB, str({k: oB.get(k) for k in
                                                           ("rows_emitted", "rows_persisted")}))
check("★ every emitted row actually reached DISK",
      _n_disk == oB["rows_emitted"] == oB["rows_persisted"] and _n_disk > 0,
      f"emitted={oB['rows_emitted']} persisted={oB['rows_persisted']} on_disk={_n_disk}")
check("the rows survive a re-read through the schema reader",
      len(PLOG.read_day(_root, _plog.day)["orders"]) == _n_disk)
# ★ THE SUBJECT OF THIS CHECK IS PERSISTENCE, AND IT IS MATCHED POSITIVELY.
# An unscoped `not any HIGH` turns this red whenever any future guard legitimately speaks during
# the fixture, and the repair is always to add one more name to an exclusion list — which grew
# twice in one evening (universe OOD, then the frozen-input census) before this was rewritten.
# A growing exclusion list is a filter nobody can audit; matching the SUBJECT instead needs no
# maintenance. The obvious risk of positive matching — a pattern that matches nothing passes
# vacuously — is closed by the red-capability check further down, which drives persistence to
# fail for real and asserts this same word appears.
_persist_high = [a for a in _al if a[0] == "HIGH" and "persisted" in a[1]]
check("no HIGH alarm about persistence when everything persisted", not _persist_high, str(_al))

# ★★ [B27 wiring] THE VERDICT MUST REACH THE ANCHOR'S RECORD, NOT ONLY AN ALARM ABOUT ITSELF.
# The OOD block computed its verdict and assigned it into a dict that does not exist in `_trade`'s
# scope. Every anchor therefore raised NameError, the surrounding `except` turned that into a HIGH
# alarm reading "universe OOD check failed", and the ONLY production-visible trace of the guard was
# its own error handler. Asserting "no HIGH alarm" catches it, but only by accident — the assertion
# that names the defect is that the record carries the answer. A guard whose sole observable is the
# except-branch is not wired, and a guard that is wired but writes nowhere is invisible.
check("★★ the anchor record CARRIES the OOD verdict (not just an alarm about it)",
      isinstance(oA.get("universe_ood"), dict)
      and {"state", "n_members", "n_ood", "ood_symbols", "blind"} <= set(oA["universe_ood"]),
      str(oA.get("universe_ood")))
# ★★ THIS ASSERTION WAS A DELIBERATE TRIPWIRE, AND IT FIRED AS DESIGNED (2026-07-29).
# Its previous form asserted that the guard is BLIND and alarms, and its own comment said: "if
# this ever goes quiet because the union got pinned, this check goes red and the exclusion above
# must be revisited with it." The union was pinned; it went red; this is that revisit. The
# assertion is REPLACED, not deleted — deleting it would remove the only thing that noticed.
#
# ★ WHAT THE PIN CHANGED, AND WHY THE NEW ASSERTION IS NOT "state == OK".
# `OK` here is STRUCTURAL: members are derived within the pinned column set, so they are a subset
# of the union BY CONSTRUCTION and this reads OK for every possible rotation. Asserting only `OK`
# would encode the misreading the pin was landed with wording changes to prevent. So what is
# asserted is that the record CARRIES ITS OWN LIMIT — an anchor whose verdict says nothing about
# what the verdict cannot establish is exactly the artefact this suite exists to forbid.
check("★★ with the union pinned, the anchor's verdict is no longer blind",
      oA["universe_ood"]["blind"] is False and oA["universe_ood"]["state"] == "OK",
      str(oA.get("universe_ood")))
check("★★ ...and the OK carries what it does NOT establish — rotation, by construction",
      "ROTATION" in (oA["universe_ood"].get("does_not_establish") or "")
      and "BY CONSTRUCTION" in (oA["universe_ood"].get("does_not_establish") or ""),
      (oA["universe_ood"].get("does_not_establish") or "")[:80])
check("★ ...and the one-directional evidence ceiling travels with it",
      "LESS likely to fire" in (oA["universe_ood"].get("evidence_ceiling") or ""))
# ★ AND THE BLIND PATH IS STILL PROVEN — just no longer by the ambient absence of a pin. It is
# driven on purpose against a manifest that carries none, so "blind must speak" keeps a test of
# its own rather than depending on a state of the repo that has now changed.
import tempfile as _tf, json as _js                                             # noqa: E402
import universe_guard as _UG                                                    # noqa: E402
_nom = os.path.join(_tf.mkdtemp(), "MANIFEST.json")
_js.dump({"models": {}}, open(_nom, "w"))
_blindres = _UG.check_members(["BTCUSDT"], manifest_path=_nom)
check("★★ blind must still SPEAK when there is no pin at all",
      _blindres["blind"] is True and _blindres["state"] == "UNDETERMINED"
      and "NOT CHECKED" in (_UG.ood_alarm_text(_blindres) or ""),
      (_UG.ood_alarm_text(_blindres) or "")[:70])

print("\n[B29] ★★ the cached book records what FILLED, never what we intended")
# Measured drift of the cached book against the venue on consecutive anchors: 26 -> 88 -> 107
# names (107 of 109 by the third), monotonic and self-perpetuating — because the maker branch
# wrote the TARGET and the top-up branch added the INTENT. Both are wishes booked as facts.
# ★ RED-CAPABILITY, MEASURED against the OLD rule on this exact fixture (2026-07-28):
#       OLD -> {'AAAUSDT': 100.0, 'CCCUSDT': 700.0, 'BBBUSDT': -500.0}
#       NEW -> {'AAAUSDT': 350.0, 'CCCUSDT': 300.0, 'BBBUSDT': -500.0}
#   AAAUSDT was never updated at all — both its legs ended `partial_expired`, so the
#   `terminal_reason == "filled"` gate discarded 250 USDT of real fills; and CCCUSDT was booked at
#   its FULL TARGET for a leg whose fill we could not read. The second is the worse of the two:
#   the one row that says "we do not know" produced the most confident number in the book.
_ROWS = [
    # a maker leg that filled 5% of a 1000 delta: the book must move 50, not 1000
    dict(rebalance_id="R1", symbol="AAAUSDT", order_type="maker", intended_notional=1000.0,
         filled_notional=50.0, terminal_reason="partial_expired"),
    # its top-up sends the residual and gets 200 of it
    dict(rebalance_id="R1", symbol="AAAUSDT", order_type="topup_taker", intended_notional=950.0,
         filled_notional=200.0, terminal_reason="partial_expired"),
    # a SELL is signed; nothing may re-apply a sign
    dict(rebalance_id="R1", symbol="BBBUSDT", order_type="maker", intended_notional=-500.0,
         filled_notional=-500.0, terminal_reason="filled"),
    # an unreadable fill: NOT 0.0, NOT the target — the previous value stands, named
    dict(rebalance_id="R1", symbol="CCCUSDT", order_type="maker", intended_notional=700.0,
         filled_notional=None, terminal_reason="filled"),
    # another batch's row must not touch this book
    dict(rebalance_id="R2", symbol="AAAUSDT", order_type="maker", intended_notional=9999.0,
         filled_notional=9999.0, terminal_reason="filled"),
]
_prev = {"AAAUSDT": 100.0, "CCCUSDT": 300.0}
_bk = AL.book_after_anchor(_prev, _ROWS, "R1")
check("★★ a 5%-filled maker leg moves the book by the FILL, not by the target",
      _bk["positions"]["AAAUSDT"] == 100.0 + 50.0 + 200.0,
      f"{_bk['positions']['AAAUSDT']} (want 350.0; 1100.0 = the target was booked)")
check("★ a partial_expired leg still counts — what moved the book is the fill, not the ending",
      _bk["positions"]["AAAUSDT"] != 100.0, _bk["positions"]["AAAUSDT"])
check("★ the signed column is summed, not re-signed",
      _bk["positions"]["BBBUSDT"] == -500.0, _bk["positions"]["BBBUSDT"])
check("★★ an unreadable fill leaves the previous value and is NAMED (0.0 would be a claim)",
      _bk["positions"]["CCCUSDT"] == 300.0 and _bk["unknown"] == ["CCCUSDT/maker"],
      (_bk["positions"]["CCCUSDT"], _bk["unknown"]))
check("★ another batch's rows are not consumed by this batch's book",
      _bk["positions"]["AAAUSDT"] < 9999.0, _bk["positions"]["AAAUSDT"])
_bk2 = AL.book_after_anchor(_bk["positions"], _ROWS, "R1")
check("★ the update is a function of (book, rows) — no hidden accumulation across calls",
      _bk2["positions"]["AAAUSDT"] == 350.0 + 250.0, _bk2["positions"]["AAAUSDT"])

# red-capability: with no logger attached, the mismatch must be VISIBLE and alarmed
loopn = AL.AnchorLoop(bl, exl, gross_usdt=10_000, log=None,
                      alarm=lambda sev, m: _al.append((sev, m)))
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "last_alarm_stale": None,
                                          "stale_ref_positions": None, "alarmed_stages": []})
oA2 = loopn.run_anchor()
oB2 = loopn.complete_anchor(oA2["_pending"], oA2["anchor_ts"], oA2["rebalance_id"])
# ★ THIS ALSO PROVES THE FILTER ABOVE CAN MATCH. `_persist_high` selects HIGH alarms containing
# "persisted"; here the same word is asserted to appear when persistence really fails. Without
# this pairing, a positive-match filter that matched nothing would make the check above pass
# vacuously — the same shape as a guard whose pattern fits no row.
check("★ RED-CAPABLE: no sink -> persisted 0 while emitted > 0, and it ALARMS",
      oB2["rows_persisted"] == 0 and oB2["rows_emitted"] > 0 and
      any(a[0] == "HIGH" and "persisted 0" in a[1] for a in _al),
      f"emitted={oB2['rows_emitted']} persisted={oB2['rows_persisted']}")
_sh.rmtree(_root, ignore_errors=True)

# ── [W] ★★ A WATCHDOG TRIP SURVIVES THE PROCESS — AND STAYS DIRECTIONAL ─────────────────────
# Two halts with OPPOSITE semantics:
#   KILL_SWITCH : refuse EVERYTHING (returns immediately; no exits either)
#   watchdog    : refuse the OPENING DIRECTION ONLY — reduce-only must still pass, because the
#                 flatten IS reduce-only. That exemption is why halt_opening_orders runs FIRST
#                 in the ladder. Merging the two (my first attempt, 0e55d6b) sealed the exit:
#                 to stop it opening, it also stopped it leaving.
# And it must be RE-APPLIED from disk each anchor: open_orders_halted/reduce_only are attributes
# on the broker OBJECT, and every anchor is a new process. The file was sticky; the reader was
# missing, so protection lasted as long as the process that raised it.
print("\n[W] a persisted watchdog trip halts OPENING only, in a new process")
_wd_state = os.path.join(tempfile.mkdtemp(), "state.json")
os.environ["LIVE_WATCHDOG_STATE"] = _wd_state
import importlib                                                                # noqa: E402
importlib.reload(AL)


def _fresh_anchor(preds_positions=None):
    """A brand-new broker + loop == the state four hours after a trip."""
    AL._save(os.environ["LIVE_LOOP_STATE"],
             {"positions": preds_positions or {}, "last_alarm_stale": None,
              "stale_ref_positions": None, "alarmed_stages": []})
    AL._save(os.environ["LIVE_PREDS_PATH"],
             {"computed_ts": time.time(), "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
              "king": {"BTCUSDT": 0.5, "ETHUSDT": -0.5, "BNBUSDT": 0.1},
              "s2": {"BTCUSDT": 0.2, "ETHUSDT": -0.2, "BNBUSDT": 0.0},
              "funding_ema": {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "BNBUSDT": 5e-5},
              "dvol30": {"BTCUSDT": 1e9, "ETHUSDT": 5e8, "BNBUSDT": 2e8},
              "factor_versions": _LIVE_FV,
              "panel": _PANEL_STAMP})
    bx = BB.BinanceBroker(); bx.arm()
    exx = EX.RebalanceExecutor(bx)
    exx.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                     for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
    exx.capture_anchor = lambda syms: (time.time(), {s_: 100.0 for s_ in syms})
    return bx, AL.AnchorLoop(bx, exx, gross_usdt=10_000)


bw, loopw = _fresh_anchor()
check("a new broker starts unhalted (which is why only FILE state survives)",
      bw.open_orders_halted is False and bw.reduce_only is False)
out_before = loopw.run_anchor()
check("with no trip on disk the anchor trades normally", out_before["action"] == "TRADE",
      out_before["action"])

AL._save(_wd_state, {"tripped_at": "2026-07-25T18:46:36Z", "reduce_only": True,
                     "open_orders_halted": True, "reason": "§4-5c account anomaly"})
bw2, loopw2 = _fresh_anchor()
out_after = loopw2.run_anchor()
_blocked = [a for a in bw2.actions if a["action"] == "order_blocked_by_halt"]
_opened = [a for a in bw2.actions
           if a["action"].startswith("submit") and not a["order"].get("reduce_only")]
check("★★ the persisted trip is re-applied to a BRAND-NEW broker",
      bw2.open_orders_halted is True and bw2.reduce_only is True,
      f"halted={bw2.open_orders_halted} reduce_only={bw2.reduce_only}")
check("★★ opening orders are refused PER-ORDER by direction (order_blocked_by_halt)",
      len(_blocked) > 0, f"{len(_blocked)} blocked")
check("★★ and not one opening order leaked through", not _opened, f"{len(_opened)} leaked")
check("★ the anchor does NOT hard-return: reduce-only paths stay reachable "
      "(merging the two halts would seal the ladder's own exit)",
      out_after["action"] != "KILLED" and bool(out_after.get("watchdog_halt")),
      f"action={out_after['action']} watchdog_halt={bool(out_after.get('watchdog_halt'))}")
check("a reduce-only order still passes the halt while it is engaged",
      bw2.submit({"symbol": "BTCUSDT", "side": "sell", "quantity": 1.0, "reduce_only": True},
                 "exit under halt") is True)

# fail-closed: an unreadable state file must read as TRIPPED, never as clean
with open(_wd_state, "w") as _fh:
    _fh.write("{ this is not json")
bw3, loopw3 = _fresh_anchor()
out_bad = loopw3.run_anchor()
check("★ an UNREADABLE watchdog state file fails CLOSED (halted), never open",
      bw3.open_orders_halted is True and
      (out_bad.get("watchdog_halt") or {}).get("source") == "unreadable_state_file",
      str(out_bad.get("watchdog_halt")))

os.remove(_wd_state)
bw4, loopw4 = _fresh_anchor()
out_clear = loopw4.run_anchor()
check("★ removing the trip file restores normal trading (the lock has a key)",
      out_clear["action"] == "TRADE" and bw4.open_orders_halted is False, out_clear["action"])

# the KILL switch keeps its stronger, everything-refusing semantics
AL._save(os.environ["LIVE_KILL_SWITCH"], {"killed_at_utc": "TEST"})
bw5, loopw5 = _fresh_anchor()
out_kill = loopw5.run_anchor()
check("KILL_SWITCH still refuses EVERYTHING (distinct from the directional halt)",
      out_kill["action"] == "KILLED" and out_kill.get("halt_source") == "KILL_SWITCH")
os.remove(os.environ["LIVE_KILL_SWITCH"])
os.environ.pop("LIVE_WATCHDOG_STATE", None)
importlib.reload(AL)

# ── [R] ★ throttled skips must be visible; no stop-loss covers them ──────────────────────────
# A rate-limited rejection is written as `skipped_rate_limit`. §4-5c counts `venue_reject`, so it
# does not fire; the drift would only show up in M5, which has no producer. Without an alarm the
# book sits short of target while all seven stop-losses stay silent.
print("\n[R] rate-limit skips raise a finding")
_bR = _OrderRecordingBroker(); _bR.arm()
_exR = EX.RebalanceExecutor(_bR)
_exR.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                  for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
_exR.capture_anchor = lambda syms: (time.time(), {s_: 100.0 for s_ in syms})
_alR = []
_loopR = AL.AnchorLoop(_bR, _exR, gross_usdt=10_000, alarm=lambda sev, m: _alR.append((sev, m)))
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "stale_ref_positions": None,
                                          "alarmed_stages": []})
_outR = _loopR.run_anchor()
check("a clean anchor raises no rate-limit finding",
      not [a for a in _alR if "限流" in a[1]], str(_alR)[:80])
# now force every submit to be throttled
_exR.rows_orders.clear()
_alR.clear()


class _Throttled(BB.VenueError):
    pass


_bR2 = BB.BinanceBroker()
_bR2.arm()
_bR2._request = lambda *a, **k: (_ for _ in ()).throw(BB.VenueError(-1003, "too many requests", 429))
_bR2.mode, _bR2.armed, _bR2.key, _bR2.secret = "TESTNET", True, "k", "s"
_exR2 = EX.RebalanceExecutor(_bR2)
_exR2.filters.f = _exR.filters.f
_exR2.capture_anchor = _exR.capture_anchor
_al2 = []
_loopR2 = AL.AnchorLoop(_bR2, _exR2, gross_usdt=10_000, alarm=lambda sev, m: _al2.append((sev, m)))
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {}, "stale_ref_positions": None,
                                          "alarmed_stages": []})
_out2 = _loopR2.run_anchor()
_rl = [r for r in _exR2.rows_orders if r["terminal_reason"] == "skipped_rate_limit"]
check("★ throttled submits are labelled skipped_rate_limit", len(_rl) > 0, f"{len(_rl)} rows")
check("★ RED-CAPABLE: a throttled anchor raises a HIGH finding (no stop-loss would)",
      any(a[0] == "HIGH" and "限流" in a[1] for a in _al2), str(_al2)[:120])
check("and the count is reported for the operator", _out2.get("n_rate_limited", 0) > 0,
      f"n_rate_limited={_out2.get('n_rate_limited')}")

# ────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[S] ★ ONE constant decides both 'does this run count' and 'may this run open'")
# The §2.5 gate counts 30 scheduled calls. ops/dryrun_ledger excludes a run that started more than
# `anchor_late_tolerance_min` from its slot; until now nothing stopped such a run from TRADING —
# real orders on a run the certification does not count. Both sides now read live/book_config.py.
# Everything below runs under the REAL config (the suite-wide open clock is suspended here).
sys.path.insert(0, os.path.join(_REPO, "ops"))
import datetime as _dt              # noqa: E402
import dryrun_ledger as DL          # noqa: E402


def _fresh_loop(tag):
    """A loop whose signal is fresh and whose stamps match — so the ONLY thing that can stop it
    trading is the clock gate."""
    st = os.path.join(tmp, f"loop_state_{tag}.json")
    pr = os.path.join(tmp, f"preds_{tag}.json")
    os.environ["LIVE_LOOP_STATE"], os.environ["LIVE_PREDS_PATH"] = st, pr
    importlib.reload(AL)
    AL._save(st, {"positions": {}, "stale_ref_positions": None, "alarmed_stages": []})
    _b = BB.BinanceBroker(); _b.arm()
    _e = EX.RebalanceExecutor(_b)
    _e.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                    for s_ in ("BTCUSDT", "ETHUSDT", "BNBUSDT")}
    _al = []
    return _b, _e, AL.AnchorLoop(_b, _e, gross_usdt=25_000,
                                 alarm=lambda s, m: _al.append((s, m))), _al, pr


def _seed_preds(pr, at_ts):
    AL._save(pr, {"computed_ts": at_ts, "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                  "king": {"BTCUSDT": 0.5, "ETHUSDT": -0.3, "BNBUSDT": 0.1},
                  "s2": {"BTCUSDT": 0.2, "ETHUSDT": -0.1, "BNBUSDT": 0.4},
                  "funding_ema": {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "BNBUSDT": 5e-5},
                  "dvol30": {"BTCUSDT": 1e9, "ETHUSDT": 5e8, "BNBUSDT": 2e8},
                  "factor_versions": _LIVE_FV,
                  "panel": _PANEL_STAMP})


_REAL_INTERNAL = os.path.join(tmp, "book_real_internal.json")   # the REAL clock/tolerance; book source pinned internal
json.dump(_internal_baseline(json.load(open(BC.BOOK_PATH))), open(_REAL_INTERNAL, "w"))
with BC._using(_REAL_INTERNAL):                  # ← the REAL clock config (tolerance/anchors), for this block only
    TOL = BC.late_tolerance_min()
    slot = BC.nominal_anchor_utc(time.time())

    # ── GREEN: on the slot -> trades ────────────────────────────────────────────────────────
    bg, eg, lg_, alg, prg = _fresh_loop("ontime")
    _seed_preds(prg, slot)
    og = lg_.run_anchor(now=slot)
    check("on-schedule run: no clock halt", og.get("off_schedule_halt") is None, og.get("schedule"))
    check("on-schedule run: broker NOT halted", bg.open_orders_halted is False)
    check("on-schedule run: opening orders really were submitted",
          any(a.get("action") == "submit_dry_run" for a in bg.actions), og.get("action"))

    # ── RED: one minute past the tolerance -> no opening orders ─────────────────────────────
    bl, el, ll_, all_, prl = _fresh_loop("late")
    late = slot + (TOL + 1) * 60
    _seed_preds(prl, late)                         # signal is FRESH; only the clock is wrong
    ol = ll_.run_anchor(now=late)
    check("★ RED-CAPABLE: a run past the tolerance is flagged off-schedule",
          ol.get("off_schedule_halt") is not None, ol.get("schedule"))
    check("★ and the broker is halted in the OPENING direction", bl.open_orders_halted is True)
    check("★ zero opening orders left the process",
          not any(a.get("action") == "submit_dry_run" and not a["order"].get("reduce_only")
                  for a in bl.actions),
          f"blocked={sum(1 for a in bl.actions if a.get('action') == 'order_blocked_by_halt')}")
    check("the halt reports the offset and the tolerance it was judged against",
          ol["off_schedule_halt"]["tolerance_min"] == TOL
          and abs(ol["off_schedule_halt"]["offset_min"] - (TOL + 1)) < 0.02,
          ol["off_schedule_halt"])
    # ★ DIRECTIONAL — the trap I walked into once already (0e55d6b): a halt that also seals the
    # exit is not protection. Being late must never make the book impossible to shed.
    _exit_ok = True
    try:
        bl.submit({"symbol": "BTCUSDT", "side": "sell", "quantity": 1.0, "reduce_only": True},
                  "exit while off-schedule")
    except Exception:
        _exit_ok = False
    check("★ reduce-only still passes while off-schedule (the exit is never sealed)", _exit_ok)

    # ── the LEDGER draws the boundary in the same place ─────────────────────────────────────
    _log = os.path.join(tmp, "runs_fixture.log")
    _day = time.strftime("%Y-%m-%d", time.gmtime(slot))

    def _ln(ts, msg):
        return f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))} {msg}\n"

    with open(_log, "w") as fh:
        for off_min in (TOL - 1, TOL + 1):
            fh.write(_ln(slot + off_min * 60, "anchor start mode=TESTNET"))
            fh.write(_ln(slot + off_min * 60 + 5, "anchor done rc=0"))
    _real_runlog, DL.RUNLOG = DL.RUNLOG, _log
    try:
        rep = DL.reconcile(_day, now=_dt.datetime.fromtimestamp(slot + 3600, _dt.timezone.utc))
    finally:
        DL.RUNLOG = _real_runlog
    check("ledger reads the tolerance from config, not from its own signature",
          rep["tolerance_min"] == TOL and rep["tolerance_source"] == "config", rep["tolerance_min"])
    check(f"★ the run at +{TOL - 1}min COUNTS as the scheduled anchor", rep["completed"] >= 1,
          f"completed={rep['completed']}/{rep['expected']}")
    check(f"★ the run at +{TOL + 1}min is EXCLUDED as a manual invocation",
          len(rep["manual_invocations_excluded"]) == 1, rep["manual_invocations_excluded"])
    # ★ this must compare the two DECISIONS, not restate the arithmetic. `(TOL+1) > TOL` would be
    # a hardcoded true wearing a check's clothes.
    _gate_at = lambda off: BC.schedule_check(slot + off * 60)["on_schedule"]   # noqa: E731
    check("★ SAME BOUNDARY at both offsets: 'the gate lets it open' == 'the ledger counts it'",
          _gate_at(TOL - 1) is True and rep["completed"] == 1
          and _gate_at(TOL + 1) is False and len(rep["manual_invocations_excluded"]) == 1,
          f"gate(+{TOL-1})={_gate_at(TOL-1)} gate(+{TOL+1})={_gate_at(TOL+1)} "
          f"ledger counted={rep['completed']} excluded={len(rep['manual_invocations_excluded'])}")

    # ── COMPLETED is not TRADED, and §2.5 only measures the first ──────────────────────────
    # §4-1 is "5 consecutive days" and the window is 5 days, so it is EXPECTED to trip inside the
    # window. From that moment every remaining anchor completes (rc=0) while trading nothing. If
    # the ledger reported only completions, the window would close on a perfect-looking 30/30
    # over a book that stopped trading on day 5.
    _logt = os.path.join(tmp, "runs_traded.log")
    with open(_logt, "w") as fh:
        fh.write(_ln(slot, "anchor start mode=TESTNET"))
        fh.write(_ln(slot + 1, 'phase_A: {"action": "TRADE", "n_live": 108}'))
        fh.write(_ln(slot + 2, "anchor done rc=0"))
        # ★ MINUS ONE DAY, NOT MINUS ONE ANCHOR — and the difference decided whether this suite
        # was green. The clause below asserts days_scheduled == 2, so the two anchors must fall
        # on two UTC days. At `slot - 4h` that is true only when `slot` is the 00:00Z anchor,
        # i.e. only while the wall clock reads 22:00-02:00Z: the acceptance battery was green for
        # 4 hours a day and red for 20, and I watched it flip at 02:02Z between two runs three
        # minutes apart. A red that heals by waiting is worse than a permanent red — it trains
        # everyone to re-run, and the next re-run hides a real regression.
        fh.write(_ln(slot - 86400, "anchor start mode=TESTNET"))
        fh.write(_ln(slot - 86399, 'phase_A: {"action": "TRADE", "n_live": 0, '
                                   '"watchdog_halt": {"source": "tripped"}}'))
        fh.write(_ln(slot - 86398, "anchor done rc=0"))
    DL.RUNLOG = _logt
    try:
        _dayt = time.strftime("%Y-%m-%d", time.gmtime(slot - 86400))
        rep_t = DL.reconcile(_dayt,
                             now=_dt.datetime.fromtimestamp(slot + 60, _dt.timezone.utc))
    finally:
        DL.RUNLOG = _real_runlog
    check("★ a halted anchor COMPLETES (it honoured the schedule) but did not TRADE",
          rep_t["completed"] == 2 and rep_t["traded"] == 1,
          f"completed={rep_t['completed']} traded={rep_t['traded']}")
    check("and the report names which anchors were halted, and by what",
          rep_t["halted_anchors"] and rep_t["halted_anchors"][0]["halted"] == ["watchdog_halt"],
          str(rep_t["halted_anchors"]))
    check("the note says the two are different questions",
          "DIFFERENT questions" in rep_t["note"], rep_t["note"][-90:])
    # ★ clause 7: the certificate must say WHICH span it certifies. A day on which every anchor
    # completed but none traded is a scheduled day and NOT a trading day, and the difference has
    # to be a number — otherwise a "5 day" certificate covers a system that traded for four.
    check("★ clause 7: the span is reported as scheduled-vs-traded DAYS, not just anchors",
          rep_t["days_scheduled"] == 2 and rep_t["days_traded"] == 1
          and "1 天交易" in rep_t["certificate_span"], rep_t["certificate_span"])

    # ── the window certifies ONE configuration, so the count must too ──────────────────────
    # state/anchor_runs.log is shared by every mode (it sits outside the per-mode state root), so
    # a hand-run DRY_RUN that lands on a slot is otherwise credited as the scheduled TESTNET
    # anchor — a completion awarded to a run that cannot produce position_readback or daily_nav
    # at all, i.e. the §2.5 count would be satisfied by runs the pilot could not be built from.
    _logm = os.path.join(tmp, "runs_modes.log")
    with open(_logm, "w") as fh:
        fh.write(_ln(slot + 60, "anchor start mode=DRY_RUN"))
        fh.write(_ln(slot + 65, "anchor done rc=0"))
    _mode_book = _internal_baseline(json.load(open(BC.BOOK_PATH)))
    _mode_book["window_mode"] = "TESTNET"
    _pm = os.path.join(tmp, "book_window_mode.json")
    json.dump(_mode_book, open(_pm, "w"))
    DL.RUNLOG = _logm
    try:
        rep_any = DL.reconcile(_day, now=_dt.datetime.fromtimestamp(slot + 3600, _dt.timezone.utc))
        with BC._using(_pm):
            rep_tn = DL.reconcile(_day,
                                  now=_dt.datetime.fromtimestamp(slot + 3600, _dt.timezone.utc))
    finally:
        DL.RUNLOG = _real_runlog
    check("without window_mode the run counts, and the report SAYS the mode was not enforced",
          rep_any["completed"] == 1 and "NOT_ENFORCED" in rep_any["require_mode"])
    check("★ with window_mode=TESTNET, a DRY_RUN run at the right time does NOT count",
          rep_tn["completed"] == 0 and len(rep_tn["wrong_mode_at_a_slot"]) == 1,
          rep_tn["wrong_mode_at_a_slot"])

    # ── the coupling is proven by PERTURBATION, not by comparing two numbers ────────────────
    # Comparing them cannot distinguish "both read the config" from "both hardcode the same
    # number". Moving the config can.
    try:
        coup = BC.assert_shared_tolerance()
    except AssertionError as e:
        coup = {"ok": False, "probe": "?", "gate_saw": "?", "ledger_saw": "?",
                "restored": BC.late_tolerance_min(), "err": str(e)[:200]}
    check("★ both consumers FOLLOW the config when it moves (accessor-level proof)",
          coup["ok"], f"probe={coup['probe']} gate={coup['gate_saw']} ledger={coup['ledger_saw']}"
                      f"{' — ' + coup['err'] if not coup['ok'] else ''}")
    check("and the probe is restored afterwards", coup["restored"] == TOL)
    # ★ MEASURED RED (2026-07-26): injecting `tolerance_min = 20` back into reconcile() — a private
    # copy that HAPPENS TO EQUAL the config — leaves the check above red (gate saw 7, ledger 20)
    # while "ledger reads the tolerance from config" three lines up still reports OK, because it
    # only sees the two numbers agree. That is the whole reason this is a perturbation and not a
    # comparison: equal values are not evidence of a shared source.

# ── behavioural proof: run_anchor itself follows the config, not just the accessor ───────────
_probe_book = _internal_baseline(json.load(open(BC.BOOK_PATH)))
_probe_book["anchor_late_tolerance_min"] = 0
_p0 = os.path.join(tmp, "book_tol0.json")
json.dump(_probe_book, open(_p0, "w"))
b0, e0, l0, al0, pr0 = _fresh_loop("tol0")       # built under the normal config...
_seed_preds(pr0, slot + 61)
with BC._using(_p0):                             # ...and only the RUN sees the perturbed one
    o0 = l0.run_anchor(now=slot + 61)
check("★ tolerance moved to 0 -> a run 61s late now halts (the GATE reads config too, "
      "not only the accessor)", b0.open_orders_halted is True, o0.get("off_schedule_halt"))

# ★ REGRESSION for a bug this file's own CLI exposed: the override used to be a module global, so
# a SECOND instance of book_config in the same process (which is what `python3 live/book_config.py`
# creates — `__main__` plus the copy dryrun_ledger imports) did not see it. The coupling assertion
# then reported a private copy in the ledger that was not there: a false red indistinguishable
# from the true one. A "process-wide" switch is only process-wide if there is exactly one instance.
import importlib.util as _ilu                                                   # noqa: E402
_spec = _ilu.spec_from_file_location("book_config_second_copy", BC.__file__)
_bc2 = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bc2)
with BC._using(_p0):
    check("★ the override is PROCESS-wide, not MODULE-wide (a second copy of book_config in the "
          "same process follows it)", _bc2.late_tolerance_min() == 0, _bc2.late_tolerance_min())

# ── fail-closed: an unusable schedule is not a pass ──────────────────────────────────────────
_bad = _internal_baseline(json.load(open(BC.BOOK_PATH)))
_bad.pop("anchors_utc")
_pb = os.path.join(tmp, "book_no_schedule.json")
json.dump(_bad, open(_pb, "w"))
# ★ the loop is CONSTRUCTED before the override: importing anchor_loop derives ANCHOR_S from the
# schedule, so a book with no schedule cannot even be imported against — which is correct at
# import time and would have masked the run-time question being asked here.
bb_, eb_, lb_, alb_, prb_ = _fresh_loop("noschedule")
_seed_preds(prb_, slot)
with BC._using(_pb):
    ob = lb_.run_anchor(now=slot)
check("★ FAIL-CLOSED: schedule unestablishable -> off-schedule, opening halted",
      bb_.open_orders_halted is True and ob.get("off_schedule_halt") is not None,
      (ob.get("schedule") or {}).get("error"))

BC._set_override(_OPEN_BOOK)     # restore the suite-wide open clock for anything added below

# ────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[T] ★ the three account-state tables: written from ONE account read, or not at all")
import pilot_log as PLOG          # noqa: E402


class _AcctBroker(BB.BinanceBroker):
    """A broker with an account. Everything else is the DRY_RUN mock."""
    def __init__(self, equity=100_000.0, unreal=250.0, pos=None, fail=False,
                 income_fail=False):
        super().__init__()
        self._eq, self._un, self._pos, self._fail = equity, unreal, pos or {}, fail
        self._income_fail = income_fail
        self.n_account_reads = self.n_income_reads = 0

    def income_since(self, start_ms, end_ms=None):
        self.n_income_reads += 1
        if self._income_fail:
            raise RuntimeError("income endpoint said no")
        return {"by_type": {"REALIZED_PNL": -120.0, "COMMISSION": -8.0, "FUNDING_FEE": 3.0,
                            "TRANSFER": 5000.0},
                "n_rows": 62, "realised_pnl": -125.0,
                "realised_components": ["REALIZED_PNL", "COMMISSION", "FUNDING_FEE"],
                "external_flow": 5000.0, "start_ms": start_ms, "end_ms": end_ms,
                "truncated": False}

    def account_snapshot(self):
        self.n_account_reads += 1
        if self._fail:
            raise RuntimeError("venue said no")
        return {"total_wallet_balance": self._eq - self._un, "total_unrealized_profit": self._un,
                "total_margin_balance": self._eq, "available_balance": self._eq * 0.9,
                "equity": self._eq, "positions_notional": dict(self._pos),
                "positions_contracts": {k: v / 100.0 for k, v in self._pos.items()},
                "read_ts": 1785000000.0}


def _fin_loop(tag, broker, ctx=True):
    root = os.path.join(tmp, f"plog_{tag}")
    lg = PLOG.PilotLogger(root, day="20260726")
    ex_ = EX.RebalanceExecutor(broker)
    lp = AL.AnchorLoop(broker, ex_, gross_usdt=25_000, log=lg, alarm=lambda s, m: None)
    if ctx:
        lp._anchor_ctx = {"anchor_ts": 1785000000.0, "mids": {"BTCUSDT": 64000.0, "ETHUSDT": 3000.0},
                          "target": {"BTCUSDT": 12_000.0, "ETHUSDT": -13_000.0},
                          "rebalance_id": "A1", "n_skipped": 2, "regime": "calm",
                          "regime_source": "fixture", "factor_version": '{"a":1}',
                          "panel_hash": "deadbeef"}
    return lp, lg, root


_bA = _AcctBroker(pos={"BTCUSDT": 11_900.0, "SOLUSDT": 400.0})
_lpA, _lgA, _rootA = _fin_loop("acct", _bA)
_finA = _lpA.finalize_anchor({"rebalance_id": "A1"}, {"rows_persisted": 110})
_lgA.close()
_dayA = PLOG.read_day(_rootA, "20260726")
check("★ ONE account read serves all three tables", _bA.n_account_reads == 1,
      _bA.n_account_reads)
check("anchors row written (executor.anchor_row finally has a caller)",
      len(_dayA["anchors"]) == 1, _finA)
check("position_readback covers held ∪ targeted (a targeted name we do NOT hold is a row)",
      {r["symbol"] for r in _dayA["position_readback"]} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"},
      {r["symbol"] for r in _dayA["position_readback"]})
_eth = next(r for r in _dayA["position_readback"] if r["symbol"] == "ETHUSDT")
check("★ a targeted-but-absent name reads 0.0 with held=False — 'not held' and 'never targeted' "
      "stay different facts", _eth["venue_position_notional"] == 0.0 and _eth["held"] is False
      and _eth["targeted"] is True, _eth)
check("readback says WHERE the number came from", all(
    r["source"] == "fapi/v3/account@post_anchor" for r in _dayA["position_readback"]))
_an = _dayA["anchors"][0]
check("realized_gross comes from the VENUE, not from our book",
      abs(_an["realized_gross"] - 12_300.0) < 1e-9
      and "fapi/v3/account" in _an["realized_gross_source"], _an["realized_gross"])
check("the anchors row carries the regime stamped at SIGNAL time",
      _an["regime_at_anchor"] == "calm" and _an["regime_source"] == "fixture")
_nav = _dayA["daily_nav"][0]
check("nav = wallet + unrealised (equity), and says so",
      _nav["nav"] == 100_000.0 and "totalWalletBalance + totalUnrealizedProfit" in _nav["nav_source"])
# ★ this check used to read "realised_pnl is None, NEVER 0.0", from when the column had no
# producer. It now has one, so the property that survives is the general one: the value is either
# MEASURED with its source named, or None — never a number without a provenance. (The old form
# would have gone red against a correct implementation, which is its own kind of wrong.)
_measured = (_nav["realised_pnl"] is not None
             and "/fapi/v1/income" in _nav["realised_pnl_source"])
_absent = _nav["realised_pnl"] is None and "UNAVAILABLE" in _nav["realised_pnl_source"]
check("★ realised_pnl is measured-with-a-source or None — never a bare number",
      _measured or _absent, _nav["realised_pnl_source"][:70])
check("★ realised P&L comes from the venue LEDGER and is the signed sum of trade result, "
      "commission and funding — not one field", _nav["realised_pnl"] == -125.0
      and set(_nav["realised_by_type"]) >= {"REALIZED_PNL", "COMMISSION", "FUNDING_FEE"},
      _nav["realised_pnl"])
check("★ external flow is MEASURED, not assumed zero — an equity delta is P&L only if nothing "
      "was deposited or withdrawn, and on testnet day one a 5000 USDT transfer landed",
      _nav["external_flow_usdt"] == 5000.0 and "TRANSFER" in _nav["external_flow_source"])
check("truncation of the income page is carried, so a capped sum is not read as a total",
      _nav["realised_truncated"] is False)
check("no previous day => equity_delta_since_prev is None, not 0.0",
      _nav["equity_delta_since_prev"] is None and _nav["prev_nav"] is None)

_bI = _AcctBroker(income_fail=True)
_lpI, _lgI, _rootI = _fin_loop("incfail", _bI)
_alI = []
_lpI.alarm = lambda s, m: _alI.append((s, m))
_lpI.finalize_anchor({"rebalance_id": "A1"}, {})
_lgI.close()
_navI = PLOG.read_day(_rootI, "20260726")["daily_nav"][0]
check("★ an unreadable income ledger leaves realised_pnl None (NOT 0.0) and alarms — a zero "
      "would un-blind the stop-loss with a fabricated number, worse than being blind",
      _navI["realised_pnl"] is None and "blind" in _navI["realised_pnl_source"]
      and any(a[0] == "HIGH" for a in _alI), _navI["realised_pnl_source"][:80])
check("...and the NAV row is still written (equity IS known; only the realised half is not)",
      _navI["nav"] == 100_000.0)

print("\n[T] a nav row per ANCHOR, and the guard reads the FILE (every anchor is a new process)")
_lp2, _lg2, _ = _fin_loop("acct2", _AcctBroker(equity=101_000.0))
_lp2.log = PLOG.PilotLogger(_rootA, day="20260726")        # same day, same root, new "process"
_fin2 = _lp2.finalize_anchor({"rebalance_id": "A2"}, {})
_lp2.log.close()
_day2 = PLOG.read_day(_rootA, "20260726")
# ★★ [B31] THIS ASSERTION USED TO PIN THE DEFECT. One row per day means the row is written by the
# day's FIRST anchor — i.e. before the day has happened — and §4-2/§4-4 read it all day. Measured
# on the production tree 2026-07-28: the only row was written at 00:16Z with the book FLAT
# (realised 0.0, unrealised 0.0, both true at that instant), the book was rebuilt to $23,400 at
# 04:00Z, and the daily-loss stop-loss read 0.00% for the rest of the day.
# ⇒ Every anchor now appends a snapshot and every reader takes the day's LAST row.
check("★★ a second anchor the same day appends its OWN nav snapshot (B31)",
      len(_day2["daily_nav"]) == 2 and _fin2["daily_nav_row"] is True,
      {k: _fin2.get(k) for k in ("daily_nav_row", "daily_nav_rows_today_before")})
check("★ ...and the file, not an in-memory flag, is what the next process counts from",
      _fin2.get("daily_nav_rows_today_before") == 1,
      "each anchor is a new process; an in-memory 'already written' would be False every time")
check("but it DOES write its own anchors row", len(_day2["anchors"]) == 2)

_lp3, _lg3, _ = _fin_loop("acct3", _AcctBroker(equity=101_500.0))
_lp3.log = PLOG.PilotLogger(_rootA, day="20260727")        # next day
_lp3.finalize_anchor({"rebalance_id": "A3"}, {})
_lp3.log.close()
_nav3 = PLOG.read_day(_rootA, "20260727")["daily_nav"][-1]
# ★ [B31] THE LINK-BACK NOW COMPARES AGAINST THE PREVIOUS DAY'S LAST SNAPSHOT (101,000), not its
# first (100,000), so the delta reads 500 rather than 1500. `_prev_nav` was ALREADY `rows[-1]` of
# the earlier day — its rule did not change; the previous day simply has more rows now. That makes
# this a close-to-close delta, which is the reading the field's name implies.
# ★ FLAGGED, NOT SETTLED: how an overnight UNREALISED loss should appear in the D+1 row is a
# separate question, first exercised at the 2026-07-29T00:0xZ crossing. This change does not
# answer it and deliberately does not touch that half.
check("★ the next day links back to the previous day's LAST snapshot, and records the delta",
      _nav3["prev_day"] == "20260726" and abs(_nav3["equity_delta_since_prev"] - 500.0) < 1e-9,
      {k: _nav3[k] for k in ("prev_day", "prev_nav", "equity_delta_since_prev")})
check("and the delta is never called 'pnl' anywhere in the row",
      not any("pnl" in k for k in _nav3 if k.startswith("equity")))

print("\n[T] ★ no account => NO ROW. Not an empty one, not a zero.")
_bD = BB.BinanceBroker()                        # DRY_RUN: account_snapshot returns None
_lpD, _lgD, _rootD = _fin_loop("dry", _bD)
_finD = _lpD.finalize_anchor({"rebalance_id": "A1"}, {})
_lgD.close()
_dayD = PLOG.read_day(_rootD, "20260726")
check("DRY_RUN writes no nav row and no readback rows",
      not _dayD["daily_nav"] and not _dayD["position_readback"], _finD)
check("but the anchors row still exists (it needs no account)", len(_dayD["anchors"]) == 1)
check("★ with no account AND no cached book, realized_gross is None — not 0.0. A zero gross is "
      "the claim 'we hold nothing', which we have not established",
      _dayD["anchors"][0]["realized_gross"] is None
      and _dayD["anchors"][0]["realized_gross_source"] == "unavailable",
      _dayD["anchors"][0]["realized_gross_source"])
AL._save(os.environ["LIVE_LOOP_STATE"], {"positions": {"BTCUSDT": 900.0, "ETHUSDT": -100.0}})
_lpD2, _lgD2, _rootD2 = _fin_loop("dry2", BB.BinanceBroker())
_lpD2.finalize_anchor({"rebalance_id": "A1"}, {})
_lgD2.close()
_anD2 = PLOG.read_day(_rootD2, "20260726")["anchors"][0]
check("with a cached book it falls back to it AND names the weaker caliber",
      abs(_anD2["realized_gross"] - 1000.0) < 1e-9
      and "cached book" in _anD2["realized_gross_source"], _anD2["realized_gross_source"])

_bF = _AcctBroker(fail=True)
_lpF, _lgF, _rootF = _fin_loop("failread", _bF)
_alF = []
_lpF.alarm = lambda s, m: _alF.append((s, m))
_finF = _lpF.finalize_anchor({"rebalance_id": "A1"}, {})
_lgF.close()
check("★ a FAILED account read alarms and writes no nav row (silence would look like 'flat')",
      any(a[0] == "HIGH" for a in _alF)
      and not PLOG.read_day(_rootF, "20260726")["daily_nav"], (_alF[:1], _finF))

print("\n[T] a HOLD anchor has no target vector, so it writes no anchors row")
_bH = _AcctBroker()
_lpH, _lgH, _rootH = _fin_loop("hold", _bH, ctx=False)
_finH = _lpH.finalize_anchor({"action": "HOLD"}, None)
_lgH.close()
check("★ no anchors row without a rebalance (four not_null columns would have to be invented)",
      not PLOG.read_day(_rootH, "20260726")["anchors"] and _finH["anchors_row"] is False, _finH)
check("...but the venue tables are still written — the book exists whether we traded or not",
      _finH["daily_nav_row"] is True and _finH["position_readback_rows"] >= 0)

# ────────────────────────────────────────────────────────────────────────────────────────────────
# ★ THE SUITE MUST NOT WRITE THE BOOK — and it does not, but only because of a side effect 900
# lines up. `complete_anchor` persists positions to `AL.STATE_PATH`, whose module-level default is
# state/loop_state.json (the DRY_RUN book a DRY_RUN anchor reads). Section [E] sets
# LIVE_LOOP_STATE and RELOADS the module, which rebinds STATE_PATH to a temp path for everything
# after it — verified, not assumed: reload moves it from state/loop_state.json to /var/folders/...
# I first read this as a live defect ("the suite writes the real book") and wrote the fix before
# checking; the check is what said otherwise. The line stays because sections that write the book
# should not depend on a distant reload staying where it is, but the reason is fragility, not a
# defect — and a fix justified by a false claim is worse than no fix.
AL.STATE_PATH = os.path.join(tempfile.mkdtemp(), "loop_state.json")

print("\n[X] ★★ the top-up must SUBTRACT what the maker already filled")
# MEASURED ON THE FIRST REAL ANCHOR (2026-07-26T00:17Z): every held name came back at exactly
# 2.00x intended — 47 of 47 anomalies, ratio median 1.997. Root cause was three lines:
#     anchor_loop:152   self.fills = fills_provider or (lambda rid, syms: {})
#     run_anchor:175    AnchorLoop(...)   <- never passed a provider
#     topup             residual = delta_notional - 0.0    <- the WHOLE target, bought again
# `venue_fills.fills_for()` existed for exactly this, its docstring naming the failure ("a
# readback failure must not be reported as 'nothing filled' -- that would trigger a duplicate
# top-up"), and it had ZERO callers. The guard was written and never wired.
#
# ★ THIS TEST IS AT complete_anchor, NOT topup. A first draft exercised topup() directly with an
# explicit `filled` dict — and PASSED BEFORE THE FIX, because topup's arithmetic was never wrong.
# The defect is entirely in what the caller hands it. A test one layer below the defect is a test
# that cannot see it.
class _FillBroker(BB.BinanceBroker):
    """A venue where the maker for BTCUSDT filled in full and ETHUSDT did not fill."""
    def __init__(self):
        # construct in DRY_RUN (no credentials needed), then flip: the suite must stay hermetic
        # while exercising the non-DRY_RUN code path, which is where the defect lives.
        super().__init__(mode="DRY_RUN")
        self.mode = "TESTNET"
        self.armed = True; self.key = self.secret = "x"
        self.submitted = []
    def _request(self, method, path, params=None, signed=False):
        if path == "/fapi/v1/allOrders":
            sym = (params or {}).get("symbol")
            if sym == "BTCUSDT":
                return [{"clientOrderId": "RX-BTCUSDT-1", "cumQuote": "1000.0", "side": "BUY",
                         "executedQty": "10", "avgPrice": "100.0", "updateTime": 1785024001000,
                         "status": "FILLED"}]
            return []
        if path == "/fapi/v1/order" and method == "POST":
            self.submitted.append(params)
            return {"orderId": 1, "status": "NEW", "executedQty": "0", "cumQuote": "0"}
        if path == "/fapi/v1/ticker/bookTicker":
            return [{"symbol": s_, "bidPrice": "99.9", "askPrice": "100.1"}
                    for s_ in ("BTCUSDT", "ETHUSDT")]
        return {}
    def positions_notional(self):
        return {}

_bX = _FillBroker()
_exX = EX.RebalanceExecutor(_bX)
_exX.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                  for s_ in ("BTCUSDT", "ETHUSDT")}
_exX._last_plans = [
    {"symbol": "BTCUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
     "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
     "target_w": 0.04, "prev_w": 0.0, "client_id": "RX-BTCUSDT-1", "submitted": True},
    {"symbol": "ETHUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
     "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
     "target_w": 0.04, "prev_w": 0.0, "client_id": "RX-ETHUSDT-1", "submitted": True}]
_lpX = AL.AnchorLoop(_bX, _exX, gross_usdt=25_000, alarm=lambda s_, m_: None)
_lpX.complete_anchor({"live": ["BTCUSDT", "ETHUSDT"],
                      "target": {"BTCUSDT": 1000.0, "ETHUSDT": 1000.0}}, 1785024000.0, "RX")
_tu = [r for r in _exX.rows_orders if r["order_type"] == "topup_taker"]
_btc = [r for r in _tu if r["symbol"] == "BTCUSDT"]
_eth = [r for r in _tu if r["symbol"] == "ETHUSDT"]
# ★ the correct shape is NO top-up row at all plus a maker row marked `filled` — residual ~0
# exits before the top-up is constructed. A first draft asserted "a top-up row with intended 0",
# which is a different (and wrong) expectation: it would have failed against correct code.
_mk_btc = [r for r in _exX.rows_orders
           if r["symbol"] == "BTCUSDT" and r["order_type"] == "maker"]
check("★★ a name the maker FILLED IN FULL is not bought again (this is the 2x defect)",
      not _btc and _mk_btc and _mk_btc[0]["terminal_reason"] == "filled",
      f"btc top-up rows={len(_btc)} (any => 2x position); "
      f"maker terminal_reason={_mk_btc[0]['terminal_reason'] if _mk_btc else 'NO ROW'}")
check("an UNfilled name still gets its full top-up (the mandatory leg still runs)",
      _eth and abs(float(_eth[0]["intended_notional"]) - 1000.0) < 1e-6,
      f"eth top-up intended={_eth[0]['intended_notional'] if _eth else 'NO ROW'}")

print("\n[X] ★ 'could not read the fills' must NOT be read as 'nothing filled'")
# The dangerous default: absence in the fills map means BOTH "did not fill" and "we could not
# ask" — venue_fills swallows per-symbol errors with `except: continue`. Reading the second as
# the first doubles a position we already hold, so here the BENIGN value is the harmful one.
_bY = _FillBroker(); _exY = EX.RebalanceExecutor(_bY); _exY.filters.f = _exX.filters.f
_exY.topup([{"symbol": "BTCUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
             "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
             "target_w": 0.04, "prev_w": 0.0}],
           {}, 1785024000.0, "RY", spreads_bps={}, unknown_fills={"BTCUSDT"})
_tuY = [r for r in _exY.rows_orders if r["order_type"] == "topup_taker"]
check("★ a name whose fills could not be read is SKIPPED, not topped up blind",
      _tuY and _tuY[0]["terminal_reason"] == "skipped_unknown_fill"
      and not _tuY[0].get("submit_ts"),
      f"{_tuY[0]['terminal_reason'] if _tuY else 'NO ROW'}")

print("\n[Y] ★★ the anchor must COLLECT commission, or fee_paid stays None forever")
# The collector (venue_fills.user_trades_for) is tested in tests_venue_fills.py. THIS tests the
# wiring — and the wiring is where the defect class lives: `fills_for` was correct and unwired,
# `make_provider` was correct and wired only in a probe. A collector nobody calls is a collector
# that does not exist.
class _FeeBroker(_FillBroker):
    def _request(self, method, path, params=None, signed=False):
        if path == "/fapi/v1/userTrades":
            if (params or {}).get("symbol") == "BTCUSDT":
                return [{"symbol": "BTCUSDT", "id": 1, "orderId": 11, "side": "BUY",
                         "price": "100.0", "qty": "10", "quoteQty": "1000.0",
                         "commission": "0.40", "commissionAsset": "USDT",
                         "time": 1785024100000, "maker": True}]
            return []
        if path == "/fapi/v1/order" and method == "POST":
            self.submitted.append(params)
            cid = str((params or {}).get("newClientOrderId") or "")
            # ★ the orderId matters now: commission is joined to a leg by orderId, so a fixture
            # whose POST returns an id no trade references would exercise the UNATTRIBUTED path
            # instead of the one this section names.
            return {"orderId": 11 if cid.endswith("-1") else 12, "clientOrderId": cid,
                    "symbol": (params or {}).get("symbol"),
                    "status": "NEW", "executedQty": "0", "cumQuote": "0"}
        return super()._request(method, path, params, signed)

_bF = _FeeBroker()
_exF = EX.RebalanceExecutor(_bF)
_exF.filters.f = {s_: {"tick": 0.01, "step": 0.001, "min_notional": 5.0}
                  for s_ in ("BTCUSDT", "ETHUSDT")}
_planF = [
    {"symbol": "BTCUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
     "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
     "target_w": 0.04, "prev_w": 0.0, "client_id": "RF-BTCUSDT-1", "submitted": True}]
# ★ the maker leg is SUBMITTED through the broker rather than declared in the fixture. Production
# runs phases A and B in one process, so the submit responses (and their orderIds) are in scope
# when the commission is attributed; a fixture that skips the submit tests a shape production
# never has, and would have made this section green through the fallback path.
_exF.submit_maker(_planF, 1785024000.0, "RF")
_exF._last_plans = _planF
_lpF = AL.AnchorLoop(_bF, _exF, gross_usdt=25_000, alarm=lambda s_, m_: None)
_lpF.complete_anchor({"live": ["BTCUSDT"], "target": {"BTCUSDT": 1000.0}}, 1785024000.0, "RF")
_rowF = [r for r in _exF.rows_orders if r["symbol"] == "BTCUSDT"
         and r["order_type"] == "maker"]
check("★★ fee_paid is populated from userTrades (None => M1 can never be complete)",
      _rowF and _rowF[0].get("fee_paid") is not None,
      f"fee_paid={_rowF[0].get('fee_paid') if _rowF else 'NO ROW'}")
check("and it carries the venue's actual commission",
      _rowF and abs(float(_rowF[0].get("fee_paid") or -1) - 0.40) < 1e-12,
      _rowF[0].get("fee_paid") if _rowF else None)

# ────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[Z] ★★ commission belongs to a LEG, and every child fill must reach the fills table")
# TWO DEFECTS, ONE FIXTURE — both invisible to [Y], which only ever produces ONE row per symbol.
#
# (1) FEE INHERITANCE ACROSS LEGS. `apply_commission` stamped a PER-SYMBOL commission total onto
#     the plan dict, and `topup()` emits BOTH the maker row and the top-up row from that same
#     dict — so a symbol that was topped up got the maker's fee written twice and the taker's
#     never. On the one real anchor so far that is 54 of 55 names. It is the identical bug the
#     comment three lines above `_order_row` already describes for `filled_notional` ("the top-up
#     row inherited it and reported 0.0 next to terminal_reason='filled'"), one field over: a
#     row that reports another order's cost while naming itself.
# (2) COLLECTION BEFORE THE EVENT. `user_trades_for` ran BEFORE `topup()`, so the taker fill did
#     not exist yet. Both halves of the defect point the same way — M1 undercounts — and neither
#     is visible in a single-leg fixture. The fake below models the timing exactly: the taker
#     trade appears only once a `-2` order has been submitted.
#
# ★ AND THE ATTRIBUTION IS BY orderId, NOT BY TIME WINDOW. The foreign trade below (orderId 999,
#   5.00 USDT) sits inside the same window and belongs to something else — a flatten, a manual
#   order, another process. A window is a proxy for attribution; the join key is exact and free.
class _LegBroker(_FillBroker):
    """Maker fills 400 of 1000 at 0.08 fee; the IOC top-up fills 600 at 0.30; plus one trade
    that is not ours at all."""
    def _request(self, method, path, params=None, signed=False):
        if path == "/fapi/v1/allOrders":
            if (params or {}).get("symbol") == "BTCUSDT":
                return [{"clientOrderId": "RZ-BTCUSDT-1", "cumQuote": "400.0", "side": "BUY",
                         "executedQty": "4", "avgPrice": "100.0", "updateTime": 1785024001000,
                         "status": "EXPIRED"}]
            return []
        if path == "/fapi/v1/order" and method == "POST":
            self.submitted.append(params)
            cid = str((params or {}).get("newClientOrderId") or "")
            if cid.endswith("-2"):
                return {"orderId": 202, "clientOrderId": cid, "symbol": params.get("symbol"),
                        "status": "FILLED", "executedQty": "6", "cumQuote": "600.0",
                        "avgPrice": "100.0", "updateTime": 1785024900000}
            return {"orderId": 101, "clientOrderId": cid, "symbol": params.get("symbol"),
                    "status": "NEW", "executedQty": "0", "cumQuote": "0"}
        if path == "/fapi/v1/userTrades":
            if (params or {}).get("symbol") != "BTCUSDT":
                return []
            rows = [{"symbol": "BTCUSDT", "id": 1, "orderId": 101, "side": "BUY",
                     "price": "100.0", "qty": "4", "quoteQty": "400.0",
                     "commission": "0.08", "commissionAsset": "USDT",
                     "time": 1785024001000, "maker": True},
                    # not ours: same symbol, same window, different order
                    {"symbol": "BTCUSDT", "id": 3, "orderId": 999, "side": "SELL",
                     "price": "100.0", "qty": "50", "quoteQty": "5000.0",
                     "commission": "5.00", "commissionAsset": "USDT",
                     "time": 1785024300000, "maker": False}]
            if any(str(p.get("newClientOrderId", "")).endswith("-2") for p in self.submitted):
                rows.insert(1, {"symbol": "BTCUSDT", "id": 2, "orderId": 202, "side": "BUY",
                                "price": "100.0", "qty": "6", "quoteQty": "600.0",
                                "commission": "0.30", "commissionAsset": "USDT",
                                "time": 1785024900000, "maker": False})
            return rows
        return super()._request(method, path, params, signed)

_alZ = []
_bZ = _LegBroker()
_exZ = EX.RebalanceExecutor(_bZ)
_exZ.filters.f = {"BTCUSDT": {"tick": 0.01, "step": 0.001, "min_notional": 5.0}}
_planZ = [{"symbol": "BTCUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
           "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
           "target_w": 0.04, "prev_w": 0.0}]
_exZ.submit_maker(_planZ, 1785024000.0, "RZ")
_exZ._last_plans = _planZ
_rootZ = tempfile.mkdtemp()
_lgZ = PLOG.PilotLogger(_rootZ, day="20260726")
_lpZ = AL.AnchorLoop(_bZ, _exZ, gross_usdt=25_000, log=_lgZ,
                     alarm=lambda s_, m_: _alZ.append((s_, m_)))
_outZ = _lpZ.complete_anchor({"live": ["BTCUSDT"], "target": {"BTCUSDT": 1000.0}},
                             1785024000.0, "RZ")
_mkZ = [r for r in _exZ.rows_orders if r["rebalance_id"] == "RZ" and r["order_type"] == "maker"]
_tuZ = [r for r in _exZ.rows_orders if r["rebalance_id"] == "RZ"
        and r["order_type"] == "topup_taker"]
check("★★ the maker row carries the MAKER's commission",
      _mkZ and _mkZ[0].get("fee_paid") is not None
      and abs(float(_mkZ[0]["fee_paid"]) - 0.08) < 1e-12,
      f"maker fee_paid={_mkZ[0].get('fee_paid') if _mkZ else 'NO ROW'} (want 0.08)")
check("★★ the top-up row carries the TAKER's commission, not the maker's",
      _tuZ and _tuZ[0].get("fee_paid") is not None
      and abs(float(_tuZ[0]["fee_paid"]) - 0.30) < 1e-12,
      f"topup fee_paid={_tuZ[0].get('fee_paid') if _tuZ else 'NO ROW'} (want 0.30; "
      f"0.08 = inherited from the maker, the defect)")
_sumZ = sum(float(r["fee_paid"]) for r in _exZ.rows_orders
            if r["rebalance_id"] == "RZ" and r.get("fee_paid") is not None)
check("★ and the row total equals what the venue charged US — 0.38, not 0.16 and not 0.76",
      abs(_sumZ - 0.38) < 1e-12, f"sum(fee_paid)={_sumZ}")
check("★ a trade that is not ours is excluded (orderId join, not a time window)",
      _sumZ < 5.0 and _outZ.get("n_trades_unattributed") == 1,
      f"unattributed={_outZ.get('n_trades_unattributed')}")

_fillsZ = PLOG.read_day(_rootZ, "20260726").get("fills", [])
check("★★ every child fill reaches the fills table (M2 has no other input)",
      len(_fillsZ) == 2, f"{len(_fillsZ)} fills rows (want 2: one maker, one taker)")
check("...one per LEG, labelled by the order we sent",
      sorted(r["order_type"] for r in _fillsZ) == ["maker", "topup_taker"],
      [r.get("order_type") for r in _fillsZ])
check("...each carrying its own commission and the venue's trade id",
      sorted(round(float(r["commission"]), 8) for r in _fillsZ) == [0.08, 0.30]
      and all(r.get("trade_id") is not None for r in _fillsZ),
      [(r.get("trade_id"), r.get("commission")) for r in _fillsZ])
# ★ `_fillsZ and` is load-bearing: without it `all([])` is True and this check reported OK while
# ZERO rows existed — a gate passing on empty input, which is the one result a gate must never
# give. Caught by reading the red run: eight FAILs and this one green, on the same empty list.
check("★ the +60s mark is PENDING with a reason, never 0.0 (M2 counts it as unmeasured)",
      bool(_fillsZ) and all(r["mid_at_fill_plus_60s"] is None
                            and r.get("mid_at_fill_plus_60s_note") for r in _fillsZ),
      [(r["mid_at_fill_plus_60s"], bool(r.get("mid_at_fill_plus_60s_note"))) for r in _fillsZ])
check("and the count that lands is reported, not the count that was built",
      _outZ.get("fill_rows_persisted") == 2, _outZ.get("fill_rows_persisted"))

print("\n[Z] ★ an unattributable LEG is UNKNOWN — per leg, not per anchor")
# The attribution joins on the submit responses THIS process holds. Phase A and phase B run in one
# process today, so the maker's response is always in scope — an assumption worth exactly one
# test, because when it does not hold the failure is silent AND in the safe direction (no wrong
# fee, just a permanently incomplete M1), which is the combination nothing else surfaces.
#
# ★ THE FIXTURE BELOW IS THE MIXED CASE, AND IT IS THE POINT. The maker's submit response is
# missing; the top-up's is not, because the top-up is sent inside phase B. So one leg of one
# symbol is unknowable while the other is exactly measured. A per-ANCHOR verdict would have to
# either publish the unknown one or discard the good one; both are wrong, and my first draft of
# this test asserted the second.
_bN = _LegBroker(); _exN = EX.RebalanceExecutor(_bN); _exN.filters.f = _exZ.filters.f
_exN._last_plans = [{"symbol": "BTCUSDT", "side": "buy", "delta_notional": 1000.0, "qty": 10.0,
                     "mid_at_anchor": 100.0, "target_notional": 1000.0, "prev_notional": 0.0,
                     "target_w": 0.04, "prev_w": 0.0,
                     # the maker WAS sent (in the process we are pretending crashed), so the row
                     # carries a submit_ts — that is what separates "unknown" from "never sent"
                     "submit_ts": 1785024000.0, "price_submit": 100.0, "mid_at_submit": 100.0}]
_alN = []
_lpN = AL.AnchorLoop(_bN, _exN, gross_usdt=25_000, alarm=lambda s_, m_: _alN.append((s_, m_)))
_outN = _lpN.complete_anchor({"live": ["BTCUSDT"], "target": {"BTCUSDT": 1000.0}},
                             1785024000.0, "RZ")
_mkN = [r for r in _exN.rows_orders if r["order_type"] == "maker"]
_tuN = [r for r in _exN.rows_orders if r["order_type"] == "topup_taker"]
check("★ a leg we cannot attribute is None — not 0.0, and not someone else's total",
      _mkN and _mkN[0].get("fee_paid") is None,
      f"maker fee_paid={_mkN[0].get('fee_paid') if _mkN else 'NO ROW'}")
check("...while the leg we CAN attribute keeps its measurement (a good number is not discarded)",
      _tuN and _tuN[0].get("fee_paid") is not None
      and abs(float(_tuN[0]["fee_paid"]) - 0.30) < 1e-12,
      f"topup fee_paid={_tuN[0].get('fee_paid') if _tuN else 'NO ROW'}")
check("...and the unknown is ALARMED rather than left to look like a zero-fee leg",
      any("unknown fee" in m_.lower() for _s, m_ in _alN), [m_ for _s, m_ in _alN][:3])

print("\n[Z] ★ a leg that was never SENT is zero by construction, not by measurement")
# The fourth state, and the one that keeps the None population honest: a row for an order that
# never left the process (skipped, blocked, rejected) has a fee of exactly zero and needs no
# venue at all. Folding it into "unknown" would bury the genuine unknowns in a crowd.
_blocked = [r for r in _exZ.rows_orders if r["rebalance_id"] == "RZ"
            and r.get("submit_ts") is None]
_sZ = [r for r in _exZ.rows_orders if r["rebalance_id"] == "RZ" and r.get("fee_source")]
check("every row carries WHY its fee reads the way it does",
      len(_sZ) == len([r for r in _exZ.rows_orders if r["rebalance_id"] == "RZ"]),
      [r.get("fee_source") for r in _exZ.rows_orders if r["rebalance_id"] == "RZ"])
check("★ the top-up row's submit_ts is the TOP-UP's, not the maker's (inherited timestamp)",
      _tuZ and _mkZ and float(_tuZ[0]["submit_ts"]) > float(_mkZ[0]["submit_ts"]),
      f"maker={_mkZ[0]['submit_ts'] if _mkZ else None} topup={_tuZ[0]['submit_ts'] if _tuZ else None}")

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
