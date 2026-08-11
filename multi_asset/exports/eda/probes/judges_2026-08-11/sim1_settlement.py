"""SIM ① — the 08:00Z settlement anchor, whole chain, with every known edge injected at once.

READ-ONLY: the real tree is COPIED; nothing under state/ is written.

Injected together, because they have never been exercised together:
  B23   one settlement stamped at ONE millisecond, 107 rows, across a page boundary
  B28   progressive crediting: the first pull sees 12 rows, the second sees all 107
  zero  a name whose funding rate is 0 (GMT-like) — must be legitimately absent, not a shortfall
  SEI   a `filled`-with-no-amount order row — must FIRE, not be filed unreconcilable
"""
import json
import os
import shutil
import sys
import tempfile
import time

REPO = "/Users/haosiyu/dl_quant_live"
sys.path.insert(0, os.path.join(REPO, "live"))
sys.path.insert(0, os.path.join(REPO, "ops"))
import binance_funding as BF          # noqa: E402
import pilot_log as PL                # noqa: E402
import reconcile as RC                # noqa: E402

FAILS, N = [], [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


# ★ COMPUTED, NOT TYPED. My first version hardcoded 1785312000000 and called it 08:00Z —
# it is 2026-07-29T08:00:00Z, one day late, so every readback was 27.7h old and all 101 rows
# were correctly REFUSED as stale. The sim reported that as a defect; it was the guard working
# on a fixture whose clock was wrong.
import calendar                                                              # noqa: E402
SET_MS = calendar.timegm(time.strptime("2026-07-28T08:00:00Z", "%Y-%m-%dT%H:%M:%SZ")) * 1000
NOW_MS = SET_MS + 20 * 60_000   # the pull happens ~20 min after, as production does


def copy_tree():
    d = tempfile.mkdtemp(prefix="sim1_")
    src = os.path.join(REPO, "state", "testnet", "pilot_log")
    dst = os.path.join(d, "pilot_log")
    shutil.copytree(src, dst)
    return dst


# ── the real book at the last readback (04:17:28Z, 101 non-zero of 109) ──────────────────────
def real_book(root):
    rows = PL.read_day(root, "20260728").get("position_readback", [])
    last = max(r["anchor_ts"] for r in rows)
    return {r["symbol"]: float(r["venue_position_notional"])
            for r in rows if r["anchor_ts"] == last}


class SimBroker:
    """A venue that credits a settlement PROGRESSIVELY and stamps every row at one millisecond."""

    def __init__(self, book, rates, progressive=False, page_limit=None, instants=(0,)):
        """`instants` = settlement offsets in ms. >1 is what puts a PAGE BOUNDARY inside a
        millisecond — with every row at ONE instant the first page is short and the boundary
        logic never runs, so a single-instant fixture cannot exercise B23's repair at all
        (it exercises only its refusal). Measured the hard way on the first draft."""
        self.mode = "TESTNET"
        self.book = book
        self.rates = rates
        self.progressive = progressive
        self.calls = 0
        self.page_limit = page_limit or BF.PAGE_LIMIT
        self.income_rows = []
        n = 0
        for off in instants:
            for sym, notional in sorted(book.items()):
                if abs(notional) < 1e-9:
                    continue
                rate = rates.get(sym, 0.0)
                if rate == 0.0:
                    continue        # a zero-rate name is charged nothing, so the venue emits NO
                                    # row. The first draft emitted a 0.00 row and then asserted
                                    # the name was absent — testing the fixture, not the code.
                # venue convention: a long paying positive funding is a NEGATIVE income
                amt = -notional * rate
                self.income_rows.append({
                    "symbol": sym, "incomeType": "FUNDING_FEE", "income": f"{amt:.8f}",
                    "asset": "USDT", "time": SET_MS + off, "tranId": 900000 + n})
                n += 1

    def _request(self, method, path, params=None, signed=False):
        params = params or {}
        if path == "/fapi/v1/income":
            self.calls += 1
            rows = [r for r in self.income_rows
                    if params["startTime"] <= r["time"] <= params.get("endTime", 1 << 62)]
            if self.progressive and self.calls == 1:
                rows = rows[:12]            # B28: the venue has only credited 12 so far
            return rows[:params.get("limit", self.page_limit)]
        if path == "/fapi/v1/fundingRate":
            s = params["symbol"]
            return [{"fundingTime": SET_MS, "fundingRate": f"{self.rates.get(s, 0.0):.8f}"}]
        if path == "/fapi/v1/fundingInfo":
            return [{"symbol": s, "fundingIntervalHours": 8} for s in self.book]
        return {}


print("=" * 96)
print("SIM ① — 08:00Z settlement, whole chain, all known edges injected together")
print("=" * 96)

root = copy_tree()
book = real_book(root)
nonzero = {s: v for s, v in book.items() if abs(v) > 1e-9}
print(f"\n  book from the REAL 04:17:28Z readback: {len(nonzero)} non-zero of {len(book)} names")

# a GMT-like zero-rate name: present in the book, rate 0 => the venue charges nothing => NO row
RATES = {s: (0.0001 if i % 3 else -0.0001) for i, s in enumerate(sorted(nonzero))}
ZERO_RATE = sorted(nonzero)[0]
RATES[ZERO_RATE] = 0.0

print("\n[1a] B23 — one settlement, one millisecond, across a page boundary")
# THREE settlement instants x 101 names, page limit 150 => every page boundary lands strictly
# inside a millisecond, which is B23's exact production shape (a 90-day pull cuts inside a
# settlement roughly once per page).
b = SimBroker(nonzero, RATES, instants=(0, 8 * 3600_000, 16 * 3600_000))
lg = BF.FundingLedger(b)
_saved_limit = BF.PAGE_LIMIT
BF.PAGE_LIMIT = 150
try:
    got = lg.fetch_income(SET_MS - 1000, SET_MS + 20 * 3600_000)
except RuntimeError as e:
    got, err = [], str(e)
else:
    err = None
BF.PAGE_LIMIT = _saved_limit
_expect = len([r for r in b.income_rows])
check("★★ every row of the single-millisecond settlement is fetched (B23's exact shape)",
      err is None and len(got) == _expect,
      f"fetched {len(got)} of {_expect}" + (f" | RAISED: {err[:110]}" if err else ""))
check("★ ...with no duplicates (the boundary re-query deliberately overlaps)",
      len({r["tranId"] for r in got}) == len(got), f"{len(got)} rows, {len({r['tranId'] for r in got})} ids")

print("\n[1b] B23 — the refusal when ONE millisecond exceeds what the endpoint can enumerate")
BF.PAGE_LIMIT = 10
b2 = SimBroker(nonzero, RATES)   # 101 rows at ONE instant, limit 10 => no correct continuation
try:
    lg2 = BF.FundingLedger(b2)
    lg2.fetch_income(SET_MS - 1000, NOW_MS)
    raised = None
except RuntimeError as e:
    raised = str(e)
BF.PAGE_LIMIT = _saved_limit
check("★★ it RAISES rather than advancing past a millisecond it cannot enumerate",
      raised is not None and "Refusing to advance" in raised, (raised or "no raise")[:110])

print("\n[1c] B28 — progressive crediting: a half-credited settlement must not be written as whole")
root_b = copy_tree()
logb = PL.PilotLogger(root_b, day="20260728")
bp = SimBroker(nonzero, RATES, progressive=True)
alarms = []
rep1 = BF.write_funding_rows(bp, logb, root_b, now_ms=SET_MS + 60_000,
                             alarm=lambda s, m: alarms.append((s, m)),
                             since_ms=SET_MS - 1000,
                             state_path=os.path.join(root_b, "_pull.json"))
logb.close()
fresh = list((rep1.get("freshness") or {}).values())
check("★★ a pull 60s after the settlement is marked possibly_incomplete",
      fresh and all(f["possibly_incomplete"] for f in fresh),
      [f"lag {f['lag_s']}s incomplete={f['possibly_incomplete']}" for f in fresh][:1])
check("★★ ...and it says coverage must NOT be computed from it",
      fresh and not fresh[0]["usable_as_coverage_evidence"], fresh[0] if fresh else None)
check("★ the partial pull really was partial (else this block proves nothing)",
      rep1["n_income"] == 12, rep1["n_income"])

# the second pull, 20 minutes later: the venue now has everything
root_c = copy_tree()
logc = PL.PilotLogger(root_c, day="20260728")
bf = SimBroker(nonzero, RATES)
alarms2 = []
rep2 = BF.write_funding_rows(bf, logc, root_c, now_ms=NOW_MS,
                             alarm=lambda s, m: alarms2.append((s, m)),
                             since_ms=SET_MS - 1000,
                             state_path=os.path.join(root_c, "_pull.json"))
logc.close()
fresh2 = list((rep2.get("freshness") or {}).values())
check("★★ the 20-minute pull is NOT flagged incomplete (1200s > the 600s bound)",
      fresh2 and not any(f["possibly_incomplete"] for f in fresh2),
      [f"lag {f['lag_s']}s" for f in fresh2][:1])

print("\n[1d] the row count, the gap, and the sign convention")
_expected_rows = len([s for s in nonzero if RATES[s] != 0.0])
check("★★ one funding row per name the venue actually charged",
      rep2["rows_written"] == _expected_rows,
      f"written {rep2['rows_written']} | charged {_expected_rows} | skipped_no_position "
      f"{rep2['skipped_no_position']}")
check("★★ the zero-rate name is legitimately ABSENT, not a shortfall",
      ZERO_RATE not in {r["symbol"] for r in PL.read_day(root_c, "20260728")["funding"]}
      and ZERO_RATE not in (rep2.get("skipped_symbols") or []),
      f"{ZERO_RATE} rate=0 ⇒ no income row ⇒ no funding row, and NOT counted as unpriceable "
      f"(skipped={rep2['skipped_no_position']})")
check("★★ the gap stays CONTINUOUS (no retention hole opened by this pull)",
      rep2["gap"]["status"] != "PERMANENT_GAP", rep2["gap"]["status"])
_rows = PL.read_day(root_c, "20260728")["funding"]
_sign = BF.FundingLedger(bf).sign_consistency(_rows)
check("★★ sign convention holds on every row (long + positive rate ⇒ we PAY)",
      _sign.get("verdict") == "OK", _sign)
check("★ every written row is priced off OUR readback, with its age recorded",
      all(r.get("position_read_age_s") is not None for r in _rows),
      f"ages present on {sum(1 for r in _rows if r.get('position_read_age_s') is not None)}/"
      f"{len(_rows)} rows")
_ages = {round(r["position_read_age_s"] / 3600, 2) for r in _rows}
check("★★ ...and that readback is the 04:17Z one, 3.71h old — INSIDE the 4h bound",
      _ages and max(_ages) < 4.0, f"ages(h)={sorted(_ages)} bound=4.0")

print("\n[1e] §4-5b must stay SILENT across the settlement (funding moves cash, not contracts)")
_rec = RC.reconcile([(d, PL.read_day(root_c, d))
                     for d in sorted(os.listdir(root_c)) if d.isdigit()])
check("★★ the settlement writes no position change ⇒ latest reconciliation is clean",
      len(_rec["latest"]) == 0 and len(_rec["latest_unreconcilable"]) == 0,
      (_rec["latest"][:2], _rec["latest_unreconcilable"][:2]))

print("\n[1f] SEI-shape row in the SAME window: must FIRE, and must not disturb funding")
root_d = copy_tree()
_day_rows = PL.read_day(root_d, "20260728")
_last = max(r["anchor_ts"] for r in _day_rows["position_readback"])
_sym = sorted(nonzero)[1]
# an order that left the process and whose amount we cannot read, landing after the last readback
_new_anchor = _last + 4 * 3600
with open(os.path.join(root_d, "20260728", "orders.jsonl"), "a") as f:
    f.write(json.dumps({
        "anchor_ts": _new_anchor, "symbol": _sym, "side": "sell", "submit_ts": _new_anchor,
        "filled_notional": None, "avg_fill_px": None, "first_fill_ts": _new_anchor,
        "last_fill_ts": _new_anchor, "order_type": "protective_flatten",
        "rebalance_id": "FLATTEN-SIM", "terminal_reason": "filled"}) + "\n")
with open(os.path.join(root_d, "20260728", "position_readback.jsonl"), "a") as f:
    # ★ THE REAL PRIOR QUANTITIES, not invented ones. My first draft wrote qty = notional/100
    # while the previous readback carries the venue's actual contracts, so EVERY name mismatched
    # and the sim reported 101 anomalies — a fixture artefact that looked exactly like a defect.
    _prev_q = {r["symbol"]: r.get("venue_position_qty")
               for r in _day_rows["position_readback"] if r["anchor_ts"] == _last}
    for s, v in sorted(nonzero.items()):
        f.write(json.dumps({"anchor_ts": _new_anchor, "symbol": s, "read_ts": _new_anchor + 60,
                            "source": "sim", "venue_position_notional": (0.0 if s == _sym else v),
                            "venue_position_qty": (0.0 if s == _sym else _prev_q.get(s))}) + "\n")
_rec_d = RC.reconcile([(d, PL.read_day(root_d, d))
                       for d in sorted(os.listdir(root_d)) if d.isdigit()])
_hit = [a for a in _rec_d["latest"] if a["symbol"] == _sym]
check("★★ the unreadable flatten leg FIRES (D2), rather than filing as unreconcilable",
      len(_hit) == 1 and _hit[0]["kind"] == "execution_of_unknown_size",
      (_hit[:1], _rec_d["latest_unreconcilable"][:1]))
check("★ ...and only that name — the other 100 still reconcile",
      len(_rec_d["latest"]) == 1, [a["symbol"] for a in _rec_d["latest"]][:5])

for d in (root, root_b, root_c, root_d):
    shutil.rmtree(os.path.dirname(d), ignore_errors=True)

print("\n[1g] ★★ RED CAPABILITY — the sim must be able to SEE a defect, or its green means nothing")
root_e = copy_tree()
# make every readback older than the bound: the settlement then cannot be priced at all
_p = os.path.join(root_e, "20260728", "position_readback.jsonl")
_lines = [json.loads(l) for l in open(_p)]
for _l in _lines:
    _l["read_ts"] = _l["read_ts"] - 6 * 3600      # push it past the 4h bound
open(_p, "w").write("".join(json.dumps(l) + "\n" for l in _lines))
_loge = PL.PilotLogger(root_e, day="20260728")
_repe = BF.write_funding_rows(SimBroker(nonzero, RATES), _loge, root_e, now_ms=NOW_MS,
                              since_ms=SET_MS - 1000, alarm=lambda s, m: None,
                              state_path=os.path.join(root_e, "_pull.json"))
_loge.close()
check("★★ a stale book ⇒ ZERO rows written and every settlement counted as unpriceable",
      _repe["rows_written"] == 0 and _repe["skipped_no_position"] == len(
          [s for s in nonzero if RATES[s] != 0.0]),
      f"written={_repe['rows_written']} skipped={_repe['skipped_no_position']}")
check("★ ...i.e. the assertions above are load-bearing, not vacuous",
      _repe["rows_written"] != rep2["rows_written"],
      f"broken={_repe['rows_written']} vs healthy={rep2['rows_written']}")
shutil.rmtree(os.path.dirname(root_e), ignore_errors=True)

print(f"\n  {N[0]} checks run")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
