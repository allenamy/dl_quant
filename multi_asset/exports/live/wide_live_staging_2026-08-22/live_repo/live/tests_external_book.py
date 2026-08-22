"""tests_external_book — the "external book" adapter (DESIGN_wide_live_deployment_2026-08-22 §1/§3.2).

*** MOCK ONLY: temp dirs, a DRY_RUN broker with a stubbed bookTicker, hand-set filters. No venue,
    no credentials, no network, no production state (every state path is redirected by env). ***

WHAT IT PROVES (each group carries a mutant that must go RED)
  [C] config: absent/internal ⇒ internal; external ⇒ validated; typo / malformed / gross above the
      §4-4b leverage policy ⇒ INVALID; the per_name_stop profile coupling predicate.
  [W] wait plan (pure): waits only inside [slot, slot+offset]; 0 otherwise; env kill switch.
  [R] the reader: a fixture written exactly as the producer writes it is ACCEPTED; each named
      defect (missing / sidecar missing / sha mismatch / bad json / schema / anchor mismatch /
      stale / future / universe pin / booster pin / bad weights / gross_norm mismatch) is REFUSED
      with that reason; the retryable set is what the poll loop retries.
  [L] the loop, external, DRY_RUN: target == w/gross_norm x NAV x gross_mult BITWISE on a neutral
      unit-gross fixture (the withhold->reshape is the identity there); NOT through EMA / band /
      risk budget (a within-band held name is NOT held; harvest state not written; the two records
      say skipped); the non-zero name set matches the file; the anchors ctx carries the external
      stamp; loop state records the last good anchor.
  [F] the two KEPT per-name filters: below 2x min-notional ⇒ withheld (popped) and recorded; the
      venue-meta rule (pure) excludes non-COIN / non-ASCII / non-USDT / leveraged / non-TRADING.
  [H] unavailable ⇒ HOLD: no plan, no orders, positions untouched, HIGH `external_book_unavailable`
      naming the reason; the ladder escalates from the last good anchor (DERISK at ≥6) and
      `on_unavailable: hold` pins it; an INVALID config BLOCKS with a CRITICAL.
  [I] internal mode is UNCHANGED: the reader is never invoked, the composer path runs (harvest
      state written), and a mutant that forces the external branch goes red.
  [P] per_name_stop profiles: null = base bitwise; wide = d30_n2_c42 over base; unknown = base +
      error + end-of-anchor alarm line.
  [S] statics: import + branch order + band guard + battery registration + coverage entry +
      tests_imports lists the module + the REAL config is internally consistent.
  [M] mutants on a COPY of anchor_loop.py: band re-applied in external ⇒ [L] red; external
      branch forced in internal ⇒ [I] red.

Exit 0 = all pass. Nothing here places an order or reads the venue.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _d in ("live", "signal", "scheduler", "ops"):
    sys.path.insert(0, os.path.join(REPO, _d))

# ── every state path OFF the production trees, BEFORE anchor_loop is imported ───────────────────
TMP = tempfile.mkdtemp(prefix="extbook_")
os.environ["LIVE_LOOP_STATE"] = os.path.join(TMP, "loop_state.json")
os.environ["LIVE_PREDS_PATH"] = os.path.join(TMP, "preds.json")
os.environ["LIVE_KILL_SWITCH"] = os.path.join(TMP, "KILL_SWITCH.json")
os.environ["LIVE_HARVEST_STATE"] = os.path.join(TMP, "harvest_ema.json")
os.environ["LIVE_FEE_BASELINE"] = os.path.join(TMP, "fee_asset_baseline.json")
os.environ["LIVE_WATCHDOG_STATE"] = os.path.join(TMP, "watchdog_state.json")
os.environ["LIVE_EXTERNAL_WAIT"] = "0"                 # never sleep in a test process
os.environ.setdefault("LIVE_MODE", "DRY_RUN")

import numpy as np                    # noqa: E402
import book_config as BC              # noqa: E402
import external_book as EXT           # noqa: E402
import anchor_loop as AL              # noqa: E402
import binance_broker as BB           # noqa: E402
import binance_executor as EX         # noqa: E402
import per_name_stop as PNS           # noqa: E402

FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}", flush=True)
    if not cond:
        FAILS.append(name)


REAL_BOOK = json.load(open(BC.BOOK_PATH))
UTC = "%Y-%m-%dT%H:%M:%SZ"


def _utc(ts):
    return time.strftime(UTC, time.gmtime(ts))


# ── fixtures ─────────────────────────────────────────────────────────────────────────────────────
# a NEUTRAL, UNIT-GROSS, DYADIC book: sum w == 0 and sum|w| == 1 EXACTLY in binary, so the
# withhold->reshape (re-demean / L1 rescale) is the identity bit for bit and "target == file x
# NAV x gross_mult" can be asserted with ==, not with a tolerance.
W8 = {"AAAUSDT": 0.25, "BBBUSDT": -0.25, "CCCUSDT": 0.125, "DDDUSDT": -0.125,
      "EEEUSDT": 0.0625, "FFFUSDT": -0.0625, "GGGUSDT": 0.0625, "HHHUSDT": -0.0625}
assert sum(W8.values()) == 0.0 and sum(abs(v) for v in W8.values()) == 1.0
UNIVERSE = sorted(W8) + ["IIIUSDT", "JJJUSDT", "ZZZUSDT"]
BOOSTER = "b" * 64


def write_target(dir_, anchor_ts, weights, written_ts=None, **override):
    """Write <dir>/<anchor>.json + .sha256 the way shadow_loop_v2.write_target_live does
    (compact sorted JSON; sidecar = sha256 of the json bytes, shasum format)."""
    os.makedirs(dir_, exist_ok=True)
    doc = {"schema": "wide_target_v1", "anchor_ts": int(anchor_ts), "weights": dict(weights),
           "gross_norm": float(sum(abs(v) for v in weights.values())), "n_names": len(weights),
           "universe_sha": EXT.universe_sha(UNIVERSE), "n_universe": len(UNIVERSE),
           "booster_sha": BOOSTER, "weights_sha": "a" * 64,
           "written_utc": _utc(written_ts if written_ts is not None else time.time()),
           "producer": "test_fixture", "anchor_offset_min": 23}
    doc.update(override)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    p = os.path.join(dir_, f"{int(anchor_ts)}.json")
    open(p, "wb").write(raw)
    open(p + ".sha256", "w").write(f"{hashlib.sha256(raw).hexdigest()}  {os.path.basename(p)}\n")
    return p


def book_with(**over):
    """A book.json = the REAL one + overrides, written to TMP; returns the path."""
    d = json.loads(json.dumps(REAL_BOOK))
    for k, v in over.items():
        d[k] = v
    p = os.path.join(TMP, f"book_{len(os.listdir(TMP))}.json")
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    return p


def ext_block(path, **over):
    b = {"path": path, "max_age_min": 10, "anchor_offset_min": 23, "poll_grace_min": 0,
         "gross_mult": 1.0, "require_anchor_match": True, "universe_sha_pin": None,
         "booster_sha_pin": None, "min_notional_mult": 2.0, "on_unavailable": "ladder",
         "schema": "wide_target_v1"}
    b.update(over)
    return b


def pns_wide():
    p = json.loads(json.dumps(REAL_BOOK["per_name_stop"]))
    p["active_profile"] = "wide"
    p.setdefault("profiles", {})["wide"] = {"depth_pct": -0.3, "consecutive_anchors": 2,
                                            "cooloff_days": 7, "min_notional_usdt": 20.0}
    return p


class _DryBroker(BB.BinanceBroker):
    """DRY_RUN broker; nothing here reaches the network."""
    def __init__(self):
        super().__init__(mode="DRY_RUN")
        self.armed = True

    def _request(self, method, path, params=None, signed=False, host=None):
        raise AssertionError(f"network call attempted: {method} {path}")


def make_loop(symbols, gross_ctor=0.0, equity=10_000.0, mids=None, alarms=None, module=None):
    M = module or AL
    b = _DryBroker()
    ex = EX.RebalanceExecutor(b)
    ex.filters.f = {s: {"tick": 0.01, "step": 0.001, "min_notional": 5.0} for s in symbols}
    ex.capture_anchor = lambda syms: (time.time(), {s: (mids or {}).get(s, 100.0) for s in syms})
    al = alarms if alarms is not None else []
    loop = M.AnchorLoop(b, ex, gross_usdt=gross_ctor, alarm=lambda s, m: al.append((s, m)))
    loop._equity = equity           # DRY_RUN never reads the venue; the sizing arithmetic still must
    return b, ex, loop, al


def seed_state(M=None, positions=None, **extra):
    st = {"positions": dict(positions or {}), "stale_ref_positions": None, "alarmed_stages": []}
    st.update(extra)
    (M or AL)._save(os.environ["LIVE_LOOP_STATE"], st)


NOMINAL = EXT.nominal_anchor_ts(time.time())           # the slot a run "now" belongs to
NOW = float(NOMINAL) + 23 * 60 + 30                     # a plausible external read moment


# ════════════════════════════════════════════════════════════════════════════════════════════════
print("[C] config resolution")
c = EXT.config({"target_leverage": 2.0})
check("C1 key absent ⇒ internal", c["source"] == "internal" and c["error"] is None, c)
check("C2 'internal' ⇒ internal", EXT.config({"book_source": "internal"})["source"] == "internal")
c3 = EXT.config({"book_source": "external", "target_leverage": 2.0, "external_book": ext_block("/tmp/x")})
check("C3 'external' + valid block ⇒ external with validated fields",
      c3["source"] == "external" and c3["gross_mult"] == 1.0 and c3["anchor_offset_min"] == 23
      and c3["require_anchor_match"] is True and c3["on_unavailable"] == "ladder", c3)
check("C4 a typo'd value is INVALID (must not pick a book)",
      EXT.config({"book_source": "externa1"})["source"] == "INVALID")
check("C5 external without a block is INVALID", EXT.config({"book_source": "external"})["source"] == "INVALID")
check("C6 unreadable config is INVALID", EXT.config(None)["source"] == "INVALID")
for key, bad in (("gross_mult", 0.0), ("gross_mult", 3.0), ("gross_mult", "two"),
                 ("path", "relative/dir"), ("require_anchor_match", "yes"), ("on_unavailable", "retry"),
                 ("universe_sha_pin", "abc"), ("max_age_min", 0.0)):
    _eb = ext_block("/tmp/x"); _eb[key] = bad
    cc = EXT.config({"book_source": "external", "target_leverage": 2.0, "external_book": _eb})
    check(f"C7 {key}={bad!r} is INVALID", cc["source"] == "INVALID" and key in (cc["error"] or ""), cc["error"])
check("C8 gross_mult above the §4-4b leverage policy (target_leverage) is INVALID",
      EXT.config({"book_source": "external", "target_leverage": 2.0,
                  "external_book": ext_block("/tmp/x", gross_mult=2.5)})["source"] == "INVALID")
check("C8b ...and equal to it is fine (L2 at 2.0 under target_leverage 2.0)",
      EXT.config({"book_source": "external", "target_leverage": 2.0,
                  "external_book": ext_block("/tmp/x", gross_mult=2.0)})["source"] == "external")
check("C9 coupling: external ⇔ active_profile 'wide'",
      EXT.pns_profile_consistent({"book_source": "external", "per_name_stop": {"active_profile": "wide"}})["ok"]
      and not EXT.pns_profile_consistent({"book_source": "external", "per_name_stop": {}})["ok"]
      and EXT.pns_profile_consistent({"book_source": "internal", "per_name_stop": {"active_profile": None}})["ok"]
      and not EXT.pns_profile_consistent({"book_source": "internal", "per_name_stop": {"active_profile": "wide"}})["ok"])

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[W] wait plan (pure)")
cfgw = c3
p0 = EXT.wait_plan(cfgw, float(NOMINAL) + 30)
check("W1 30s into the slot ⇒ wait until N+offset", abs(p0["wait_s"] - (23 * 60 - 30)) < 0.01
      and p0["nominal_anchor_ts"] == NOMINAL, p0)
p1 = EXT.wait_plan(cfgw, float(NOMINAL) + 23 * 60 + 1)
check("W2 past the offset ⇒ no wait", p1["wait_s"] == 0.0, p1)
p2 = EXT.wait_plan(cfgw, float(NOMINAL) + 2 * 3600 + 60)
check("W3 nowhere near a slot (manual/test run) ⇒ no wait, never hours", p2["wait_s"] == 0.0, p2)
slept = []
r = EXT.wait_for_slot(cfgw, float(NOMINAL) + 30, sleep=lambda s: slept.append(s), clock=lambda: float(NOMINAL) + 30)
check("W4 LIVE_EXTERNAL_WAIT=0 disables the sleep (this process)", r["slept_s"] == 0.0 and not slept and r["disabled_by_env"], r)
os.environ["LIVE_EXTERNAL_WAIT"] = "1"
_t = [float(NOMINAL) + 30]
def _clk(): return _t[0]
def _slp(s): _t[0] += s; slept.append(s)
r = EXT.wait_for_slot(cfgw, float(NOMINAL) + 30, sleep=_slp, clock=_clk)
os.environ["LIVE_EXTERNAL_WAIT"] = "0"
check("W5 enabled ⇒ sleeps in slices to the wake time", abs(r["slept_s"] - (23 * 60 - 30)) < 0.5 and len(slept) > 1, r)

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[R] the reader")
TDIR = os.path.join(TMP, "target_live")
cfgr = EXT.config({"book_source": "external", "target_leverage": 2.0, "external_book": ext_block(TDIR)})
write_target(TDIR, NOMINAL, W8, written_ts=NOW - 90)
ok = EXT.read_target(cfgr, now=NOW, nominal_ts=NOMINAL)
check("R1 a well-formed, fresh, matching file is ACCEPTED", ok["ok"] is True and ok["n_names"] == 8
      and ok["w"] == W8 and ok["gross_norm"] == 1.0 and ok["symbols"] == sorted(W8), ok.get("reason"))
check("R1b ...and carries the stamps the ledger needs",
      ok["universe_sha"] == EXT.universe_sha(UNIVERSE) and ok["booster_sha"] == BOOSTER and ok["sha_ok"])
vec = EXT.target_vector(ok, sorted(W8))
check("R1c target_vector = w/gross_norm aligned to symbols, unit gross",
      float(np.abs(vec).sum()) == 1.0 and vec[sorted(W8).index("AAAUSDT")] == 0.25)


def refused(label, reason, setup):
    shutil.rmtree(TDIR, ignore_errors=True)
    p = write_target(TDIR, NOMINAL, W8, written_ts=NOW - 90)
    setup(p)
    e = EXT.read_target(cfgr, now=NOW, nominal_ts=NOMINAL)
    check(f"R2 {label} ⇒ refused as {reason}", e["ok"] is False and e["reason"] == reason,
          f"got ok={e['ok']} reason={e.get('reason')} detail={e.get('detail')}")
    return e


refused("missing file", "missing", lambda p: os.remove(p))
refused("missing sidecar", "sidecar_missing", lambda p: os.remove(p + ".sha256"))
def _tamper(p):
    b = bytearray(open(p, "rb").read()); b[len(b) // 2] ^= 0x01; open(p, "wb").write(bytes(b))
refused("one flipped byte in the json", "sha_mismatch", _tamper)
refused("sidecar carries another hash", "sha_mismatch",
        lambda p: open(p + ".sha256", "w").write("0" * 64 + "  x\n"))
def _badjson(p):
    raw = b"{not json"; open(p, "wb").write(raw)
    open(p + ".sha256", "w").write(f"{hashlib.sha256(raw).hexdigest()}  x\n")
refused("sha-valid but not JSON", "bad_json", _badjson)
def _rewrite(p, **over):
    doc = json.loads(open(p, "rb").read()); doc.update(over)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    open(p, "wb").write(raw); open(p + ".sha256", "w").write(f"{hashlib.sha256(raw).hexdigest()}  x\n")
refused("wrong schema name", "schema", lambda p: _rewrite(p, schema="wide_target_v0"))
refused("anchor_ts of another slot", "anchor_mismatch", lambda p: _rewrite(p, anchor_ts=NOMINAL - 14400))
refused("written 11 min ago (max_age 10)", "stale", lambda p: _rewrite(p, written_utc=_utc(NOW - 11 * 60)))
refused("written 5 min in the FUTURE", "stale", lambda p: _rewrite(p, written_utc=_utc(NOW + 300)))
refused("a NaN weight", "bad_weights", lambda p: _rewrite(p, weights=dict(W8, AAAUSDT=float("nan"))))
refused("gross_norm disagrees with sum|w|", "gross_norm_mismatch", lambda p: _rewrite(p, gross_norm=0.9))
refused("all-zero weights (gross_norm lying 1.0)", "bad_weights", lambda p: _rewrite(p, weights={k: 0.0 for k in W8}, gross_norm=1.0))
refused("gross_norm 0 (declared)", "schema", lambda p: _rewrite(p, weights={k: 0.0 for k in W8}, gross_norm=0.0))
refused("n_names lies", "schema", lambda p: _rewrite(p, n_names=3))
cfg_pin = EXT.config({"book_source": "external", "target_leverage": 2.0,
                      "external_book": ext_block(TDIR, universe_sha_pin="c" * 64)})
shutil.rmtree(TDIR, ignore_errors=True); write_target(TDIR, NOMINAL, W8, written_ts=NOW - 90)
e = EXT.read_target(cfg_pin, now=NOW, nominal_ts=NOMINAL)
check("R2 universe_sha pin mismatch ⇒ universe_pin", e["reason"] == "universe_pin", e.get("reason"))
cfg_pin2 = EXT.config({"book_source": "external", "target_leverage": 2.0,
                       "external_book": ext_block(TDIR, booster_sha_pin="not-this-booster")})
e = EXT.read_target(cfg_pin2, now=NOW, nominal_ts=NOMINAL)
check("R2 booster_sha pin mismatch ⇒ booster_pin", e["reason"] == "booster_pin", e.get("reason"))
cfg_pin3 = EXT.config({"book_source": "external", "target_leverage": 2.0,
                       "external_book": ext_block(TDIR, universe_sha_pin=EXT.universe_sha(UNIVERSE),
                                                  booster_sha_pin=BOOSTER)})
check("R2b matching pins ⇒ accepted (the pin is a check, not a block)",
      EXT.read_target(cfg_pin3, now=NOW, nominal_ts=NOMINAL)["ok"] is True)
# no-match config: an old file is accepted, and its age then feeds the ladder (not TRADE)
cfg_nm = EXT.config({"book_source": "external", "target_leverage": 2.0,
                     "external_book": ext_block(TDIR, require_anchor_match=False, max_age_min=240)})
shutil.rmtree(TDIR, ignore_errors=True)
write_target(TDIR, NOMINAL - 7 * 14400, W8, written_ts=NOW - 90)          # file named for 7 anchors ago
e = EXT.read_target(cfg_nm, now=NOW, nominal_ts=NOMINAL - 7 * 14400)
ag = EXT.age_anchors(e, cfg_nm, {}, NOW, AL.ANCHOR_S)
check("R3 require_anchor_match=false: an old file is READ but its age is the file's anchor (≥7)",
      e["ok"] and ag["age_anchors"] >= 7.0 and AL.staleness_action(ag["age_anchors"]) == "DERISK",
      ag)
# poll: the retryable set is retried until the grace deadline, then gives up with the last reason
shutil.rmtree(TDIR, ignore_errors=True); os.makedirs(TDIR)
cfg_poll = EXT.config({"book_source": "external", "target_leverage": 2.0,
                       "external_book": ext_block(TDIR, poll_grace_min=1)})
_pt = [NOW]; _ps = []
def _pclk(): return _pt[0]
def _pslp(s): _pt[0] += s; _ps.append(s)
e = EXT.read_target(cfg_poll, now=NOW, nominal_ts=NOMINAL, poll=True, sleep=_pslp, clock=_pclk)
check("R4 poll retries a MISSING file until the grace deadline, then reports missing",
      e["ok"] is False and e["reason"] == "missing" and e["attempts"] >= 4 and abs(_pt[0] - NOW - 60) < 16,
      f"attempts={e['attempts']} slept={sum(_ps):.0f}s")
# ...and a file that lands mid-poll is picked up
_pt = [NOW]; _ps = []
def _pslp2(s):
    _pt[0] += s; _ps.append(s)
    if len(_ps) == 2:
        write_target(TDIR, NOMINAL, W8, written_ts=_pt[0] - 5)
e = EXT.read_target(cfg_poll, now=NOW, nominal_ts=NOMINAL, poll=True, sleep=_pslp2, clock=_pclk)
check("R4b a file that lands during the poll is ACCEPTED on the next attempt",
      e["ok"] is True and e["attempts"] == 3, f"ok={e['ok']} attempts={e['attempts']}")
_rewrite(os.path.join(TDIR, f"{NOMINAL}.json"), schema="nope")
_e4 = EXT.read_target(cfg_poll, now=NOW, nominal_ts=NOMINAL, poll=True, sleep=_pslp2, clock=_pclk)
check("R4c non-retryable defects are NOT retried (schema ⇒ one attempt)", _e4["reason"] == "schema" and _e4["attempts"] == 1, _e4.get("attempts"))

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[L] the loop, external, DRY_RUN — target == file x NAV x gross_mult, bitwise; no EMA / band")
shutil.rmtree(TDIR, ignore_errors=True)
write_target(TDIR, NOMINAL, W8, written_ts=time.time() - 60)
_ext_book = book_with(book_source="external", external_book=ext_block(TDIR), per_name_stop=pns_wide(),
                      anchor_late_tolerance_min=10 ** 6)          # clock pinned OPEN (tests_signal_and_loop convention)
with BC._using(_ext_book):
    # a held name whose delta (10 USDT) sits INSIDE the neutral band (0.002 x 10,000 = 20): the
    # band would HOLD it at 2490; the design says the external book bypasses the band ⇒ 2500.
    seed_state(positions={"AAAUSDT": 2490.0})
    b, ex, loop, al = make_loop(sorted(W8))
    out = loop.run_anchor()
    tgt = (loop._anchor_ctx or {}).get("target") or {}
    gross = out["sizing"]["gross"]
    check("L1 action TRADE, book_source external, record ok", out["action"] == "TRADE"
          and out["book_source"] == "external" and out["external_book"]["ok"] is True, out.get("external_book"))
    check("L2 sizing = NAV x gross_mult with the source stamped",
          gross == 10_000.0 and out["sizing"]["target_leverage"] == 1.0
          and out["sizing"]["leverage_source"] == "external_book.gross_mult", out["sizing"])
    check("★ L3 target == w/gross_norm x gross BITWISE for every name (neutral unit-gross fixture)",
          all(tgt.get(s) == W8[s] / 1.0 * gross for s in W8) and len(tgt) == len(W8),
          {s: (tgt.get(s), W8[s] * gross) for s in list(W8)[:3]})
    check("L4 non-zero name set == the file's", set(tgt) == set(W8), sorted(set(tgt) ^ set(W8)))
    check("★ L5 the within-band held name is NOT held (no neutral band on an external book)",
          tgt.get("AAAUSDT") == 2500.0, tgt.get("AAAUSDT"))
    check("L6 harvest EMA skipped: record says so and NO state file was written",
          loop._last_harvest_ema.get("applied") is False and loop._last_harvest_ema.get("skipped") == "external_book"
          and not os.path.exists(os.environ["LIVE_HARVEST_STATE"]))
    check("L7 band record says skipped", loop._last_no_trade_band.get("skipped") == "external_book")
    ctx = loop._anchor_ctx
    fv = json.loads(ctx["factor_version"])
    check("L8 anchors ctx stamps WHICH book: factor_version names external/booster/weights/universe, panel_hash = universe_sha",
          ctx["book_source"] == "external" and fv["book_source"] == "external" and fv["booster_sha"] == BOOSTER
          and ctx["panel_hash"] == EXT.universe_sha(UNIVERSE) and ctx["external_book"]["ok"] is True, fv)
    st = AL._load(os.environ["LIVE_LOOP_STATE"], {})
    check("L9 loop state records the last good external anchor", st.get("external_last_good_anchor_ts") == NOMINAL, st.get("external_last_good_anchor_ts"))
    check("L10 orders were planned for every name and went to the (DRY) broker",
          out["n_planned"] == len(W8) and out["n_live"] >= 1 and any(a["action"] == "submit_dry_run" for a in b.actions),
          f"planned={out.get('n_planned')} live={out.get('n_live')}")
    check("L11 the DL census / column-set / OOD gates are SKIPPED and say so (not faked as pass)",
          out["frozen_input_census"].get("skipped", "").startswith("external_book")
          and out["universe_ood"]["state"] == "SKIPPED_EXTERNAL" and out["columns_verified"] == "SKIPPED",
          (out["frozen_input_census"], out["universe_ood"]["state"], out["columns_verified"]))
    check("L12 no HIGH/CRITICAL alarm on a clean external anchor",
          not [m for s_, m in al if s_ in ("HIGH", "CRITICAL") and "external_book_unavailable" in m], al[:3])

# gross_mult 2.0 scales the same file 2x (L2 level) — the arithmetic, not a new code path
_ext_book2 = book_with(book_source="external", external_book=ext_block(TDIR, gross_mult=2.0), per_name_stop=pns_wide(),
                       anchor_late_tolerance_min=10 ** 6)
with BC._using(_ext_book2):
    seed_state()
    b, ex, loop, al = make_loop(sorted(W8))
    out2 = loop.run_anchor()
    tgt2 = loop._anchor_ctx["target"]
    check("L13 gross_mult=2.0 ⇒ target == w x 2 x NAV bitwise", all(tgt2[s] == W8[s] * 20_000.0 for s in W8)
          and out2["sizing"]["target_leverage"] == 2.0)

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[F] the two KEPT per-name filters")
W10 = dict(W8, IIIUSDT=0.0005, JJJUSDT=-0.0005)          # 5 USDT at 10k gross: below 2 x 5.0
shutil.rmtree(TDIR, ignore_errors=True); write_target(TDIR, NOMINAL, W10, written_ts=time.time() - 60)
with BC._using(_ext_book):
    seed_state()
    b, ex, loop, al = make_loop(sorted(W10))
    outf = loop.run_anchor()
    tgtf = loop._anchor_ctx["target"]
    dust = loop._anchor_ctx["external_book"]["below_min_notional"]
    check("F1 names below 2x min-notional are WITHHELD (popped) and the rest re-scaled to gross",
          "IIIUSDT" not in tgtf and "JJJUSDT" not in tgtf and abs(sum(abs(v) for v in tgtf.values()) - 10_000.0) < 1e-6,
          f"n={len(tgtf)} gross={sum(abs(v) for v in tgtf.values()):.4f}")
    check("F2 ...and the record names them with the withheld mass",
          dust["checked"] is True and sorted(dust["names"]) == ["IIIUSDT", "JJJUSDT"] and dust["n"] == 2
          and abs(dust["mass_frac"] - 0.001 / 1.001) < 1e-9, dust)
    check("F3 the popped dust shows in the untradable disposition (existing channel)",
          set(outf["untradable_names"].get("popped", [])) >= {"IIIUSDT", "JJJUSDT"}, outf.get("untradable_names"))
    check("F4 no dust alarm under the 10% breadth-loss line (0.1% here)",
          not [m for s_, m in al if "minNotional" in m], [m for s_, m in al][:2])
# mutant: min_notional_mult 0 ⇒ nothing withheld (the filter is the config, not an accident)
_ext_book0 = book_with(book_source="external", external_book=ext_block(TDIR, min_notional_mult=0.0),
                       per_name_stop=pns_wide(), anchor_late_tolerance_min=10 ** 6)
with BC._using(_ext_book0):
    seed_state()
    b, ex, loop, al = make_loop(sorted(W10))
    loop.run_anchor()
    check("F5 (control) min_notional_mult=0 ⇒ the dust names stay in the target",
          "IIIUSDT" in loop._anchor_ctx["target"] and loop._anchor_ctx["external_book"]["below_min_notional"]["n"] == 0)
# the venue-meta rule, pure
EXI = [{"symbol": "AAAUSDT", "underlyingType": "COIN", "contractType": "PERPETUAL", "status": "TRADING"},
       {"symbol": "USARUSDT", "underlyingType": "EQUITY", "contractType": "TRADIFI_PERPETUAL", "status": "TRADING"},
       {"symbol": "ETH3LUSDT", "underlyingType": "COIN", "contractType": "PERPETUAL", "status": "TRADING"},
       {"symbol": "OLDUSDT", "underlyingType": "COIN", "contractType": "PERPETUAL", "status": "SETTLING"},
       {"symbol": "QQQUSDT", "underlyingType": "INDEX", "contractType": "PERPETUAL", "status": "TRADING"},
       {"symbol": "BTCUSD_PERP", "underlyingType": "COIN", "contractType": "PERPETUAL", "status": "TRADING"}]
mx = EXT.venue_meta_exclusions(EXI, ["AAAUSDT", "USARUSDT", "ETH3LUSDT", "OLDUSDT", "QQQUSDT", "BTCUSD_PERP",
                                     "GHOSTUSDT", "币安人生USDT"])
check("F6 venue meta: COIN perp TRADING kept; equity/index/leveraged/settling/non-USDT/non-ASCII/unknown excluded",
      "AAAUSDT" not in mx and mx.get("USARUSDT", "").startswith("underlyingType=EQUITY")
      and mx.get("ETH3LUSDT") == "leveraged_token" and mx.get("OLDUSDT") == "status=SETTLING"
      and mx.get("QQQUSDT", "").startswith("underlyingType=INDEX") and mx.get("BTCUSD_PERP") == "not_usdt"
      and mx.get("GHOSTUSDT") == "not_in_exchangeInfo" and mx.get("币安人生USDT") == "non_ascii", mx)
# ...and that the loop WIRES it (the DRY path skips the fetch; prove the wiring by injecting a fake src)
with BC._using(_ext_book):
    shutil.rmtree(TDIR, ignore_errors=True); write_target(TDIR, NOMINAL, W8, written_ts=time.time() - 60)
    seed_state()
    b, ex, loop, al = make_loop(sorted(W8))
    b.mode = "TESTNET"                    # past the DRY skip for THIS call only; every venue call is stubbed
    b.armed = False                       # ...and submit() stays on its dry branch (`not armed`)
    b.positions = lambda: {}
    b.account_snapshot = lambda: {"positions_notional": {}, "equity": 10_000.0, "positions_contracts": {},
                                  "positions_unrealized": {}, "read_ts": time.time()}
    b.open_orders = lambda: []
    b.symbol_config = {}
    class _Src:
        def _get(self, path, params=None, weight=1):
            assert path == "/fapi/v1/exchangeInfo", path
            return {"symbols": [{"symbol": s, "underlyingType": ("EQUITY" if s == "AAAUSDT" else "COIN"),
                                 "contractType": "PERPETUAL", "status": "TRADING"} for s in W8]}
    loop.src = _Src()
    import universe as _UNI
    _vs = _UNI.venue_status
    _UNI.venue_status = lambda src, timeout_ok=True: {s: "TRADING" for s in W8}
    try:
        outm = loop.run_anchor()
    finally:
        _UNI.venue_status = _vs
    check("F7 wired: an EQUITY-underlying name in the file is WITHHELD (popped) by the meta rule on a non-DRY loop",
          outm["action"] == "TRADE" and "AAAUSDT" not in loop._anchor_ctx["target"]
          and loop._anchor_ctx["external_book"]["meta_excluded"].get("AAAUSDT", "").startswith("underlyingType=EQUITY"),
          (outm.get("action"), loop._anchor_ctx["external_book"].get("meta_excluded")))

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[H] unavailable ⇒ HOLD (never internal); the ladder from the last good; INVALID blocks")
shutil.rmtree(TDIR, ignore_errors=True); os.makedirs(TDIR)
with BC._using(_ext_book):
    seed_state(positions={"AAAUSDT": 1000.0, "BBBUSDT": -1000.0})
    b, ex, loop, al = make_loop(sorted(W8))
    outh = loop.run_anchor()
    st = AL._load(os.environ["LIVE_LOOP_STATE"], {})
    check("★ H1 missing file ⇒ HOLD: no plan, no orders, positions untouched",
          outh["action"] == "HOLD" and "_pending" not in outh and "n_planned" not in outh
          and not [a for a in b.actions if a["action"].startswith("submit")]
          and st["positions"] == {"AAAUSDT": 1000.0, "BBBUSDT": -1000.0}, outh.get("action"))
    check("★ H2 HIGH alarm names external_book_unavailable + the reason + 'never internal'",
          any(s_ == "HIGH" and "external_book_unavailable: missing" in m and "绝不回退在役引擎" in m for s_, m in al),
          [m[:80] for s_, m in al][:3])
    check("H3 the record carries ok=False and the reason", outh["external_book"]["ok"] is False
          and outh["external_book"]["reason"] == "missing", outh.get("external_book"))
    check("H4 the internal composer was NOT consulted (no harvest state, no preds read needed)",
          not os.path.exists(os.environ["LIVE_HARVEST_STATE"]) and outh.get("book_source") == "external")
    # ladder from the last good anchor: 7 anchors old ⇒ DERISK (DRY bookkeeping branch)
    seed_state(positions={"AAAUSDT": 1000.0, "BBBUSDT": -1000.0},
               external_last_good_anchor_ts=NOMINAL - 7 * 14400, stale_ref_positions=None)
    b, ex, loop, al = make_loop(sorted(W8))
    outd = loop.run_anchor()
    st = AL._load(os.environ["LIVE_LOOP_STATE"], {})
    check("★ H5 last good 7 anchors old ⇒ the pre-registered ladder DERISKs (reduce-only, bookkeeping halves)",
          outd["action"] == "DERISK" and outd["external_book"]["age_ref"]["ref_source"] == "loop_state_last_good"
          and st["positions"].get("AAAUSDT") == 500.0, (outd.get("action"), st.get("positions")))
    # on_unavailable: hold pins the first rung
    _hold_book = book_with(book_source="external", external_book=ext_block(TDIR, on_unavailable="hold"),
                           per_name_stop=pns_wide(), anchor_late_tolerance_min=10 ** 6)
with BC._using(_hold_book):
    seed_state(positions={"AAAUSDT": 1000.0}, external_last_good_anchor_ts=NOMINAL - 20 * 14400)
    b, ex, loop, al = make_loop(sorted(W8))
    outp = loop.run_anchor()
    st = AL._load(os.environ["LIVE_LOOP_STATE"], {})
    check("H6 on_unavailable=hold ⇒ HOLD even 20 anchors stale (never DERISK/FLATTEN)",
          outp["action"] == "HOLD" and st["positions"].get("AAAUSDT") == 1000.0, outp.get("action"))
# a stale file (written 11 min ago) holds too — the reason travels
with BC._using(_ext_book):
    write_target(TDIR, NOMINAL, W8, written_ts=time.time() - 11 * 60)
    seed_state()
    b, ex, loop, al = make_loop(sorted(W8))
    outs = loop.run_anchor()
    check("H7 a stale file ⇒ HOLD with reason 'stale'", outs["action"] == "HOLD" and outs["external_book"]["reason"] == "stale",
          outs.get("external_book"))
# INVALID config blocks outright
_bad_book = book_with(book_source="externa1")
with BC._using(_bad_book):
    seed_state(positions={"AAAUSDT": 1000.0})
    b, ex, loop, al = make_loop(sorted(W8))
    outb = loop.run_anchor()
    check("★ H8 INVALID book_source ⇒ BLOCKED_CONFIG, CRITICAL, no orders, positions untouched",
          outb["action"] == "BLOCKED_CONFIG" and any(s_ == "CRITICAL" and "book_source" in m for s_, m in al)
          and not b.actions, (outb.get("action"), al[:1]))
_bad_book2 = book_with(book_source="external", external_book=ext_block(TDIR, gross_mult=2.5))   # > target_leverage 2.0
with BC._using(_bad_book2):
    b, ex, loop, al = make_loop(sorted(W8))
    check("H9 gross_mult above target_leverage ⇒ BLOCKED_CONFIG (settled in config, not by a §4-4b trip)",
          loop.run_anchor()["action"] == "BLOCKED_CONFIG")
# profile inconsistency is a HIGH alarm, not a block
_inc_book = book_with(book_source="external", external_book=ext_block(TDIR), anchor_late_tolerance_min=10 ** 6)
with BC._using(_inc_book):
    shutil.rmtree(TDIR, ignore_errors=True); write_target(TDIR, NOMINAL, W8, written_ts=time.time() - 60)
    seed_state()
    b, ex, loop, al = make_loop(sorted(W8))
    outi = loop.run_anchor()
    check("H10 external without the wide stop profile ⇒ trades, but a HIGH names the inconsistency",
          outi["action"] == "TRADE" and outi.get("pns_profile_inconsistent")
          and any("profile 不一致" in m for s_, m in al), outi.get("pns_profile_inconsistent"))

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[I] internal mode is UNCHANGED — the reader is never invoked; the composer runs")
import compute_preds as _CP          # noqa: E402
import live_panel as _LP             # noqa: E402
_LIVE_FV = REAL_BOOK["factor_versions"]
_PANEL_STAMP = _CP.columns_fingerprint(_LP.panel_symbols())
SYM3 = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


def seed_preds(path, at_ts):
    AL._save(path, {"computed_ts": at_ts, "symbols": SYM3,
                    "king": {"BTCUSDT": 0.5, "ETHUSDT": -0.3, "BNBUSDT": 0.1},
                    "s2": {"BTCUSDT": 0.2, "ETHUSDT": -0.1, "BNBUSDT": 0.4},
                    "funding_ema": {"BTCUSDT": 1e-4, "ETHUSDT": 2e-4, "BNBUSDT": 5e-5},
                    "dvol30": {"BTCUSDT": 1e9, "ETHUSDT": 5e8, "BNBUSDT": 2e8},
                    "factor_versions": _LIVE_FV, "panel": _PANEL_STAMP})


_int_book = book_with(anchor_late_tolerance_min=10 ** 6)       # REAL config (book_source absent/internal) + open clock
_calls = []
_orig_read = EXT.read_target
EXT.read_target = lambda *a, **k: (_calls.append(1), _orig_read(*a, **k))[1]
try:
    with BC._using(_int_book):
        seed_state(); seed_preds(os.environ["LIVE_PREDS_PATH"], time.time())
        b, ex, loop, al = make_loop(SYM3, gross_ctor=10_000.0, equity=None)
        outI = loop.run_anchor()
        check("★ I1 internal: TRADE through the composer — harvest state written, book_source internal, reader NEVER called",
              outI["action"] == "TRADE" and outI.get("book_source") == "internal" and not _calls
              and os.path.exists(os.environ["LIVE_HARVEST_STATE"]) and outI["n_live"] >= 1
              and "external_book" not in outI, (outI.get("action"), outI.get("book_source"), len(_calls)))
        check("I2 internal anchors ctx stamps internal and carries the mixture in factor_version (preds stamp)",
              loop._anchor_ctx["book_source"] == "internal" and loop._anchor_ctx["external_book"] is None
              and json.loads(loop._anchor_ctx["factor_version"]) == _LIVE_FV)
        check("I3 sizing source is the config policy in internal mode",
              outI["sizing"]["leverage_source"] == "config/book.json target_leverage", outI["sizing"].get("leverage_source"))
finally:
    EXT.read_target = _orig_read

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[P] per_name_stop profiles")
base = {"enabled": True, "depth_pct": -0.25, "consecutive_anchors": 2, "cooloff_days": 7, "min_notional_usdt": 20.0}
check("P1 active_profile absent ⇒ base bitwise", PNS.resolve_profile(dict(base)) == base)
check("P2 active_profile null ⇒ base bitwise", PNS.resolve_profile(dict(base, active_profile=None, profiles={"wide": {"depth_pct": -0.3}})) == base)
w = PNS.resolve_profile(dict(base, active_profile="wide", profiles={"wide": {"depth_pct": -0.3, "consecutive_anchors": 2, "cooloff_days": 7, "_basis": "x"}}))
check("P3 'wide' overlays d30_n2_c42 and names the profile", w["depth_pct"] == -0.3 and w["consecutive_anchors"] == 2
      and w["cooloff_days"] == 7 and w["min_notional_usdt"] == 20.0 and w["_profile"] == "wide" and "_basis" not in w, w)
u = PNS.resolve_profile(dict(base, active_profile="narrow", profiles={"wide": {"depth_pct": -0.3}}))
check("P4 unknown profile ⇒ base values stay in force + _profile_error (the clause does not go blind)",
      u["depth_pct"] == -0.25 and "_profile_error" in u, u)
_cfgp = os.path.join(TMP, "pns_book.json")
json.dump({"per_name_stop": dict(base, active_profile="narrow", profiles={})}, open(_cfgp, "w"))
_stp = os.path.join(TMP, "pns_state.json")
r = PNS.update_from_snapshot({"positions_notional": {"X": 100.0}, "positions_unrealized": {"X": -1.0}}, time.time(),
                             state_path=_stp, cfg_path=_cfgp)
check("P5 end-of-anchor hook surfaces the profile error as an alarm line", any("profile 配置错误" in m for m in r["alarms"]), r["alarms"])
check("P6 cfg() through the file resolves the profile", PNS.cfg(_cfgp).get("_profile_error") is not None)
_cfgw = os.path.join(TMP, "pns_book_w.json")
json.dump({"per_name_stop": dict(base, active_profile="wide", profiles={"wide": {"depth_pct": -0.3}})}, open(_cfgw, "w"))
check("P7 cfg() with wide ⇒ depth -0.30, enabled unchanged", PNS.cfg(_cfgw)["depth_pct"] == -0.3 and PNS.cfg(_cfgw)["enabled"] is True)
# the trigger arithmetic with the wide profile: -28% twice does NOT fire (needs -30%), -31% twice does
S0 = {"counters": {}, "stopped": {}, "cooldown": {}}
cw = PNS.cfg(_cfgw)
st1, _ = PNS.evaluate({"positions_notional": {"A": 100.0}, "positions_unrealized": {"A": -28.0}}, S0, cw, 1.0)
st1, _ = PNS.evaluate({"positions_notional": {"A": 100.0}, "positions_unrealized": {"A": -28.0}}, st1, cw, 2.0)
st2, _ = PNS.evaluate({"positions_notional": {"B": 100.0}, "positions_unrealized": {"B": -31.0}}, S0, cw, 1.0)
st2, ev2 = PNS.evaluate({"positions_notional": {"B": 100.0}, "positions_unrealized": {"B": -31.0}}, st2, cw, 2.0)
check("P8 wide profile: -28% x2 does not fire (base -25% would have); -31% x2 fires",
      "A" not in st1["stopped"] and "B" in st2["stopped"] and any("触发" in e for e in ev2))

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[S] statics: wiring order, battery registration, coverage, config consistency")
src = open(os.path.join(REPO, "scheduler", "anchor_loop.py")).read()
check("S1 anchor_loop imports external_book", "import external_book as EXT" in src)
i_cfg, i_read, i_trade = src.find("EXT.config(_book_cfg)"), src.find("EXT.read_target("), src.find("def _trade(")
check("S2 source resolved and the file read in run_anchor BEFORE _trade", 0 < i_cfg < i_read < i_trade, (i_cfg, i_read, i_trade))
i_vec, i_compose, i_band = src.find("EXT.target_vector("), src.find("LG.compose_book("), src.find("apply_no_trade_band(")
check("S3 external target vector is set where compose_book would run, and the band call is guarded by `if _is_ext`",
      0 < i_vec < i_compose < i_band and "if _is_ext:\n            # ★ design §1: the external book is NOT passed through the neutral band" in src,
      (i_vec, i_compose, i_band))
check("S4 size_book is called with the external leverage in external mode", 'target_leverage=(external["gross_mult"] if _is_ext else None)' in src)
check("S5 the schedule gate is judged at ENTRY (now_sched) so the deliberate wait cannot self-halt", "sched = BC.schedule_check(now_sched)" in src)
ra = open(os.path.join(REPO, "run_acceptance.sh")).read()
check("S6 registered in the battery", '"tests_external_book:$_SELF/live/tests_external_book.py"' in ra)
gc = open(os.path.join(REPO, "ops", "gate_coverage.py")).read()
check("S7 gate_coverage carries the suite's boundary statement", '"tests_external_book":' in gc)
ti = open(os.path.join(REPO, "live", "tests_imports.py")).read()
check("S8 tests_imports lists external_book as a production module", '"external_book"' in ti)
pc = EXT.pns_profile_consistent(REAL_BOOK)
check("S9 the REAL config is internally consistent (book_source ⇔ stop profile)", pc["ok"], pc)
check("S10 the REAL config's external block validates when switched on (so the switch is one key, not a debugging session)",
      EXT.config(dict(REAL_BOOK, book_source="external"))["source"] == "external",
      EXT.config(dict(REAL_BOOK, book_source="external")).get("error"))
cap = float(REAL_BOOK.get("anchor_max_seconds", 1500))
eb = REAL_BOOK.get("external_book") or {}
need = (float(eb.get("anchor_offset_min", 8)) + float(eb.get("poll_grace_min", 0))) * 60 + float(REAL_BOOK.get("k_seconds", 900)) + 6 * 60
check("S11 anchor_max_seconds covers wait + poll + k + ~6 min of phases (else the cap kills phase B)",
      cap >= need, f"cap={cap} need>={need}")

# ════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[M] mutants on a COPY of anchor_loop.py (the suite must be able to go RED)")
MUT = os.path.join(TMP, "mut")
os.makedirs(os.path.join(MUT, "scheduler"), exist_ok=True)
os.symlink(os.path.join(REPO, "config"), os.path.join(MUT, "config"))
for d in ("live", "signal", "ops", "checkpoints"):
    if os.path.exists(os.path.join(REPO, d)):
        os.symlink(os.path.join(REPO, d), os.path.join(MUT, d))


def mutant(name, old, new):
    s = src
    if s.count(old) != 1:
        raise AssertionError(f"mutant {name}: anchor text not unique ({s.count(old)}): {old[:60]!r}")
    s = s.replace(old, new, 1)
    p = os.path.join(MUT, "scheduler", f"anchor_loop_{name}.py")
    open(p, "w").write(s)
    spec = importlib.util.spec_from_file_location(f"anchor_loop_{name}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# M1: re-apply the neutral band to the external book ⇒ the within-band held name is held ⇒ L5 red
M1 = mutant("band",
            "        if _is_ext:\n            # ★ design §1: the external book is NOT passed through the neutral band",
            "        if False:\n            # ★ design §1: the external book is NOT passed through the neutral band")
shutil.rmtree(TDIR, ignore_errors=True); write_target(TDIR, NOMINAL, W8, written_ts=time.time() - 60)
with BC._using(_ext_book):
    seed_state(M1, positions={"AAAUSDT": 2490.0})
    b, ex, loop, al = make_loop(sorted(W8), module=M1)
    loop.run_anchor()
    check("★ M1 RED-CAPABLE: a mutant that re-applies the band HOLDS the within-band name (2490 ≠ 2500) — L5 would fail",
          loop._anchor_ctx["target"].get("AAAUSDT") == 2490.0, loop._anchor_ctx["target"].get("AAAUSDT"))
# M2: force the external branch in internal mode ⇒ the reader IS invoked ⇒ I1 red
M2 = mutant("force_ext",
            '        if _ext_cfg["source"] == "external":\n            # ★ THE EXTERNAL FILE IS THE SIGNAL.',
            '        if True:\n            # ★ THE EXTERNAL FILE IS THE SIGNAL.')
_calls = []
EXT.read_target = lambda *a, **k: (_calls.append(1), _orig_read(*a, **k))[1]
try:
    with BC._using(_int_book):
        seed_state(M2); seed_preds(os.environ["LIVE_PREDS_PATH"], time.time())
        b, ex, loop, al = make_loop(SYM3, gross_ctor=10_000.0, equity=None, module=M2)
        try:
            loop.run_anchor()
        except Exception:
            pass
        check("★ M2 RED-CAPABLE: forcing the external branch under an internal config invokes the reader — I1 would fail",
              len(_calls) >= 1, len(_calls))
finally:
    EXT.read_target = _orig_read
# M3: a mutant that falls back to the internal composer when the file is missing ⇒ H1/H4 red
M3 = mutant("fallback",
            '            if action == "TRADE" or _ext_cfg["on_unavailable"] == "hold" or age == float("inf"):\n'
            '                action = "HOLD"\n'
            '            self.alarm("HIGH", EXT.unavailable_text(ext, action))\n',
            '            action = "TRADE"; ext = None\n'
            '        if False:\n'
            '            self.alarm("HIGH", EXT.unavailable_text(ext, action))\n')
shutil.rmtree(TDIR, ignore_errors=True); os.makedirs(TDIR)
with BC._using(_ext_book):
    seed_state(M3); seed_preds(os.environ["LIVE_PREDS_PATH"], time.time())
    b, ex, loop, al = make_loop(SYM3, gross_ctor=10_000.0, equity=None, module=M3)
    out3 = loop.run_anchor()
    check("★ M3 RED-CAPABLE: a mutant that falls back to the internal composer TRADES on a missing file — H1 would fail",
          out3.get("action") == "TRADE" and "_pending" in out3, out3.get("action"))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}   ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
