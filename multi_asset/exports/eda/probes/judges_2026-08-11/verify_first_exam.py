"""0C independent verification of the funding FIRST EXAM at 2026-07-27T16:00:00Z.

★ WRITTEN BEFORE THE DATA (2026-07-27 ~14:5xZ, settlement is 16:00:00Z). Every branch below is
decided in advance, so nothing here can be tuned to what came back.

The five criteria are §2.5.9's, pre-registered by 0C, inherited verbatim by §2.5.2-5 (rewritten
by lead at 1316a6b):
   1. rows 量级        — one row per name we actually held
   2. sign 约定        — long + positive rate => funding_paid < 0
   3. positions 取自 readback, 非 paid/rate 反推
   4. gap 转 CONTINUOUS
   5. 零仓行计 unverifiable

★ AND THE PRE-DECIDED VERDICT TABLE (so the observation cannot pick its own meaning):
   venue rows > 0 and we held names  -> FIRST EXAM HAPPENED. judge by the five criteria.
   venue rows = 0 and we held names  -> the FIRST INFORMATIVE ZERO. n=1 observation that the
                                        venue does not credit under exposure. NOT yet a venue
                                        property (needs >=3, per §2.5.10 四 1).
   we held nothing at 16:00:00Z      -> no exam. the registered-expected branch. Says nothing
                                        about the venue.
"""
import json
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/"
                   "6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get                                          # noqa: E402

SETTLE_MS = 1785168000000            # 2026-07-27T16:00:00Z
LOGROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
STAMP = "/Users/haosiyu/dl_quant_live/state/testnet/funding_last_pull.json"
now = int(time.time() * 1000)

print(f"now {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now/1000))}  "
      f"settlement {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(SETTLE_MS/1000))}  "
      f"({(now-SETTLE_MS)/60000:+.0f} min)")

# ── 1. THE VENUE: did it credit funding? (type-filtered, whole retention, no pagination) ──────
print("\n[1] VENUE — incomeType=FUNDING_FEE over the whole 90-day retention, single request")
fee = get("/fapi/v1/income", {"incomeType": "FUNDING_FEE",
                              "startTime": now - 90 * 86400_000, "endTime": now,
                              "limit": 1000}, signed=True)
n_fee = len(fee) if isinstance(fee, list) else -1
print(f"    rows = {n_fee}"
      + ("  (<1000 => exact, no page boundary)" if 0 <= n_fee < 1000 else "  ★ PAGINATED — recount"))

# ── 2. OUR BOOK AT THE SETTLEMENT, from the venue's own trade record ──────────────────────────
print("\n[2] OUR EXPOSURE at 16:00:00Z — rebuilt from userTrades, independent of our readback")
syms = sorted({json.loads(l)["symbol"]
               for l in open(f"{LOGROOT}/20260727/position_readback.jsonl")})
held = {}
for s in syms:
    time.sleep(0.32)
    r = get("/fapi/v1/userTrades", {"symbol": s, "startTime": now - 5 * 86400_000,
                                    "endTime": now, "limit": 1000}, signed=True)
    if not isinstance(r, list):
        continue
    q = sum(float(x["qty"]) * (1 if x["side"] == "BUY" else -1)
            for x in r if int(x["time"]) <= SETTLE_MS)
    px = [float(x["price"]) for x in r if int(x["time"]) <= SETTLE_MS]
    if abs(q) > 1e-9 and px and abs(q * px[-1]) > 1.0:
        held[s] = q * px[-1]
print(f"    names held through the settlement: {len(held)}   gross ${sum(abs(v) for v in held.values()):,.0f}")

# ── 3. THE PRE-DECIDED VERDICT ────────────────────────────────────────────────────────────────
# ★★ THE GUARD THIS SCRIPT NEEDED AND DID NOT HAVE (0C, found by smoke-testing it 26 min early).
# Run before the settlement, every input is already in its "final" shape and nothing says so:
# `held` counts trades with `time <= SETTLE_MS`, which before the settlement is simply "every
# trade so far" = 108; and FUNDING_FEE is 0 because the charge has not happened yet. The script
# therefore printed "THE FIRST INFORMATIVE ZERO" — a verdict about an event that had not occurred.
# ⇒ The refusal has to live HERE, not in the caller's sleep: a guard that exists only in the
#   scheduler is a guard that anyone running the script by hand does not have. Same family as
#   every "it was green because nothing had happened yet" in this project.
print("\n[3] VERDICT (branch chosen before the data)")
if now < SETTLE_MS + 60_000:
    print(f"    => TOO EARLY. The settlement is at 16:00:00Z and it is now "
          f"{time.strftime('%H:%M:%SZ', time.gmtime(now/1000))} "
          f"({(SETTLE_MS-now)/60000:+.0f} min). NO VERDICT.")
    print("       Every reading above is pre-event: `held` is just 'all trades so far' and")
    print("       FUNDING_FEE=0 only means the charge has not happened. Re-run after the event.")
    raise SystemExit(0)
if not held:
    print("    => NO EXAM. Book was flat at the settlement — the registered-expected branch.")
    print("       This says NOTHING about whether the venue credits funding.")
elif n_fee == 0:
    print("    => ★ THE FIRST INFORMATIVE ZERO. We held "
          f"{len(held)} names through a real settlement and the venue credited nothing.")
    print("       Observation n=1 that the venue does not credit under exposure.")
    print("       NOT a venue property yet (§2.5.10 四 1 requires >=3 independent crossings).")
else:
    print(f"    => ★★ FIRST EXAM HAPPENED. {n_fee} FUNDING_FEE rows exist. Judging below.")

# ── 4. IF ROWS EXIST: the untested inference, and the five criteria ───────────────────────────
if isinstance(fee, list) and fee:
    this = [r for r in fee if abs(int(r["time"]) - SETTLE_MS) < 60_000]
    print(f"\n[4] rows at THIS settlement: {len(this)} (of {len(fee)} total)")
    ts = Counter(int(r["time"]) for r in this)
    print(f"    ★ MY UNTESTED INFERENCE — do all rows share ONE millisecond?  "
          f"distinct timestamps = {len(ts)}  -> "
          f"{'CONFIRMED' if len(ts) == 1 else 'REFUTED — they do NOT share one ms'}")
    print(f"      (this decides whether B23's same-ms page-boundary defect bites funding)")
    print(f"    sum funding_paid = {sum(float(r['income']) for r in this):+.6f} USDT")
    print(f"    symbols: {len(set(r['symbol'] for r in this))}; "
          f"we held {len(held)} -> "
          f"{'MATCH' if len(set(r['symbol'] for r in this)) == len(held) else 'DIFFERS (investigate)'}")

# ── 5. WHAT OUR LEDGER DID WITH IT ────────────────────────────────────────────────────────────
print("\n[5] OUR LEDGER")
try:
    stamp = json.load(open(STAMP))
    print(f"    funding_last_pull.json: evaluated_utc={stamp.get('evaluated_utc')} "
          f"n_income={stamp.get('n_income')} rows_written={stamp.get('rows_written')} "
          f"gap={(stamp.get('gap') or {}).get('status')} sign={stamp.get('sign_verdict')} "
          f"skipped_no_position={stamp.get('skipped_no_position')}")
    print(f"    [criterion 4] gap CONTINUOUS? -> "
          f"{(stamp.get('gap') or {}).get('status')}")
except Exception as e:
    print(f"    stamp unreadable: {e}")

rows = []
for d in ("20260727", "20260728"):
    try:
        for l in open(f"{LOGROOT}/{d}/funding.jsonl"):
            rows.append(json.loads(l))
    except FileNotFoundError:
        pass
print(f"    funding.jsonl rows on disk: {len(rows)}")
if rows:
    mine = [r for r in rows if abs(float(r["settlement_ts"]) * 1000 - SETTLE_MS) < 60_000]
    print(f"    rows for THIS settlement: {len(mine)}")
    bad_sign = [r for r in mine
                if r.get("funding_rate") and r.get("position_notional_at_settlement")
                and abs(float(r["position_notional_at_settlement"])) > 1e-9
                and abs(float(r["funding_paid"])) > 1e-12
                and (float(r["funding_paid"]) > 0) !=
                    (-(float(r["position_notional_at_settlement"]) * float(r["funding_rate"])) > 0)]
    print(f"    [criterion 2] sign convention violations: {len(bad_sign)}/{len(mine)}")
    taut = [r for r in mine
            if r.get("funding_rate") and abs(float(r["funding_rate"])) > 1e-12
            and abs(float(r["position_notional_at_settlement"])
                    + float(r["funding_paid"]) / float(r["funding_rate"])) < 1e-6]
    print(f"    [criterion 3] rows whose position EQUALS -paid/rate (would be the tautology): "
          f"{len(taut)}/{len(mine)}"
          + ("  ★ check these against the readback by hand" if taut else "  -> none, good"))
    zero = [r for r in mine if abs(float(r["position_notional_at_settlement"] or 0)) < 1e-9]
    print(f"    [criterion 5] zero-position rows (must count unverifiable, not pass): {len(zero)}")
    print(f"    [criterion 1] rows written {len(mine)} vs names we held {len(held)} -> "
          f"{'MATCH' if len(mine) == len(held) else 'DIFFERS — account for every missing name'}")
print("\ndone.")
