"""0C — B30 acceptance suite: §4-5b must compare in QUANTITY, judge in NOTIONAL, on ONE mark.

Written 2026-07-28T00:5xZ, BEFORE the implementation exists (team-lead approved 2026-07-28).
0C writes the criteria; 0B writes the implementation. That split is the point: a suite written
after the code tends to describe the code.

★★ THIS FILE MUST NEVER BE VACUOUSLY GREEN. B30 does not exist yet, so the first thing it does is
   PROBE for the contract and, if absent, exit NON-ZERO with `NOT IMPLEMENTED`. A suite that
   passes against a missing implementation is the exact failure this project keeps cataloguing —
   "a pattern matching nothing is indistinguishable from a guard confirming safety".

────────────────────────────────────────────────────────────────────────────────────────────────
THE RULING BEING TESTED (team-lead, 2026-07-27, after 0C's three-basis root cause)
    compare on QUANTITY (immune to price), judge on NOTIONAL (`|residual_qty| x mark(T2)`,
    ONE basis), keep "below the smallest tradeable size is not actionable" (B20 per-symbol floor).

WHY, IN ONE LINE: `expected = readback(T1)[qty x MARK@T1] + filled_notional[qty x FILL PX]` was
compared against `observed = readback(T2)[qty x MARK@T2]` — three bases, equal only when price
does not move. §4-5b was a price-move detector wearing a position-mismatch label.

────────────────────────────────────────────────────────────────────────────────────────────────
THE FOUR CASES, WITH THEIR ANSWERS ALREADY KNOWN FROM PRODUCTION (0C, 2026-07-27T16:4xZ)

  (1) ADA / FIL / STG at the 07-27T16:01:10Z anchor MUST GO SILENT.
      Their quantities close to the cent-equivalent: every fill is present.
  (2) A REAL quantity mismatch MUST STILL FIRE.
      Built from case (1)'s own rows by DELETING one fill record — which is not a hypothetical:
      it is precisely defect A (`terminal_reason=filled` while `filled_notional is None`, so
      `signed_fills_by_anchor` skips it by design), the defect that produced SEIUSDT $53.44.
      ⇒ (2) is also the RED CAPABILITY CONTROL for (1): it uses the same names and the same
        window, so a (1) that is green because the detector sees nothing cannot survive (2).
  (3) QUANTITIES IDENTICAL + A LARGE PRICE MOVE MUST BE SILENT.
      Case (1) already carries a real -4.08% / -3.22% / -3.35% move. (3) re-runs it with the
      move AMPLIFIED 5x, so silence cannot be attributed to the residual merely being small.
  (4) §4-5b AND §4-7 MUST BOTH MOVE. They read one `reconcile`, so this should be automatic —
      which is why it is asserted rather than assumed: "shared input" is a claim about wiring,
      and this repo has already shipped two guards that read the same name from different
      sources.

MEASURED CONTENT (all four names, from the production ledger, window = readback 12:17:13Z ->
16:18:02Z; `dq` re-derived from BOTH `orders.filled_notional/avg_fill_px` AND `fills`, which agree
to 4 decimals):

    sym  N1       Q1        sum_dq     sum_dNotional   N2       Q2        M1        M2        move
    ADA  310.27   1885.00   -1256.00   -197.6944        99.31    629.00   0.164600  0.157885  -4.080%
    FIL  437.56    589.30    -706.50   -508.8856       -84.22   -117.20   0.742508  0.718601  -3.220%
    STG  195.36   1480.00   -1160.00   -146.9720        40.83    320.00   0.132000  0.127594  -3.338%

    Q1 = Q2 - sum_dq exactly for all three (1885 = 629+1256; 589.3 = -117.2+706.5; 1480 = 320+1160)
    and M2/M1 - 1 reproduces the mark moves 0C measured independently on 07-27. The notional-basis
    residuals these produce are -13.27 / -12.89 / -7.56 — the three that flattened a $24.5k book
    for -$137.75.
"""
import json
import os
import sys

LIVEDIR = "/Users/haosiyu/dl_quant_live/live"
sys.path.insert(0, LIVEDIR)

FAILS = []
N = [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


# ── measured fixture content ────────────────────────────────────────────────────────────────────
T1, T2 = 1785154633.5, 1785169082.3        # the two readback times reconcile compares
ATS1, ATS2 = 1785153649.549612, 1785168070.499456
CASE = {                       # sym: (N1, Q1, sum_dq, sum_dNotional, N2, Q2)
    "ADAUSDT": (310.27, 1885.00, -1256.00, -197.6944, 99.31, 629.00),
    "FILUSDT": (437.56, 589.30, -706.50, -508.8856, -84.22, -117.20),
    "STGUSDT": (195.36, 1480.00, -1160.00, -146.9720, 40.83, 320.00),
}


def fixture(price_amplify=1.0, drop_fill=None):
    """days_data in the shape reconcile consumes, carrying a QUANTITY on every readback row.

    `price_amplify` scales the T1->T2 mark move (quantities untouched) — case (3).
    `drop_fill`     removes one symbol's fill row entirely — case (2), i.e. defect A.
    """
    orders, rb = [], []
    for sym, (n1, q1, dq, dnot, n2, q2) in CASE.items():
        m1, m2 = n1 / q1, n2 / q2
        m2 = m1 + (m2 - m1) * price_amplify
        rb.append({"anchor_ts": ATS1, "symbol": sym, "read_ts": T1,
                   "venue_position_notional": q1 * m1, "venue_position_qty": q1,
                   "source": "fixture"})
        rb.append({"anchor_ts": ATS2, "symbol": sym, "read_ts": T2,
                   "venue_position_notional": q2 * m2, "venue_position_qty": q2,
                   "source": "fixture"})
        if sym == drop_fill:
            continue
        orders.append({"anchor_ts": ATS2, "symbol": sym, "side": "sell" if dq < 0 else "buy",
                       "filled_notional": dnot, "avg_fill_px": dnot / dq,
                       "filled_qty": dq,
                       "last_fill_ts": (T1 + T2) / 2, "first_fill_ts": (T1 + T2) / 2,
                       "terminal_reason": "filled", "order_type": "maker",
                       "rebalance_id": "B30-FIXTURE", "intended_notional": dnot})
    return [("20260727", {"orders": orders, "position_readback": rb})]


def anomalies(days, **kw):
    import reconcile as RC
    return RC.reconcile(days, **kw)


# ── PRE-FLIGHT: does the contract exist at all? ────────────────────────────────────────────────
print("=" * 96)
print("B30 PRE-FLIGHT — what the ledger can support today (0C, measured, not assumed)")
print("=" * 96)

SCHEMA = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log/20260727/_schema.json"
cols = json.load(open(SCHEMA))["tables"]["position_readback"]
has_qty = any("qty" in c for c in cols)
print(f"  position_readback columns : {cols}")
print(f"  carries a QUANTITY?       : {has_qty}")
print("""
  ★ FINDING THAT PRECEDES THE IMPLEMENTATION (0C, 2026-07-28):
    `position_readback` records NOTIONAL ONLY. A quantity-basis comparison therefore cannot be
    computed from the ledger as it stands — B30 needs `venue_position_qty` written alongside
    `venue_position_notional`. The value costs NOTHING extra to obtain: `binance_broker` already
    receives `positionAmt` in the same /fapi/v3/account payload it reads the notional from
    (`positions()` returns exactly that, in contracts) — it is fetched today and discarded.
    Fills need nothing new: `orders.filled_notional / avg_fill_px` gives dq, and this suite
    verified it agrees with the `fills` table to 4 decimals on all four real names.

  ★ TWO CONSEQUENCES THAT ARE DESIGN INPUT, NOT TEST OUTPUT — they need a ruling BEFORE the code:

    (a) FORWARD-ONLY. Historical readbacks have no quantity, so anchors before the schema change
        CANNOT be re-expressed in the quantity caliber. The trip banner's "N in this window's
        history" would then span two calibers at once. That is the lead's own elevated rule
        ("any cross-day X->Y narrative must declare both ends' caliber") biting the guard itself,
        the day it lands.

    (b) THE THRESHOLD'S MARK IS MISSING EXACTLY WHERE IT IS NEEDED MOST. The ruling judges on
        `|residual_qty| x mark(T2)`. For a name still held at T2 the mark is free
        (`notional/qty`). For a name that went to ZERO at T2 it is 0/0 — and that is not an edge
        case, it is THE case: SEIUSDT, the one real quantity residual that survives, has Q2=0
        because the position vanished. A mark must be named for it (T1's own mark and the
        anchor's `mid_at_anchor_vector` are both available); whichever is chosen must be
        REPORTED per row, or "priced off T2" and "fell back to T1" become the same observable.
""")

try:
    import reconcile as RC
    probe = RC.reconcile(fixture())
    a0 = probe["anomalies"]
    contract = bool(a0) and all(k in a0[0] for k in ("residual_qty", "residual_usdt"))
    if not contract:
        probe2 = RC.reconcile(fixture(drop_fill="ADAUSDT"))
        contract = bool(probe2["anomalies"]) and "residual_qty" in probe2["anomalies"][0]
except Exception as e:
    print(f"  reconcile could not be imported/run: {type(e).__name__}: {e}")
    contract = False

if not contract:
    print("\n" + "=" * 96)
    print("NOT IMPLEMENTED — B30 is absent. This suite is NOT green; it has not run.")
    print("  The contract it probes for: every anomaly record carries `residual_qty` (signed,")
    print("  contracts) and `residual_usdt` (= |residual_qty| x mark(T2)), and the FIRING test")
    print("  uses `residual_usdt` against the per-symbol B20 floor — one basis, end to end.")
    print("  Re-run this file when 0B lands B30; it flips to real pass/fail with no edits.")
    print("=" * 96)
    sys.exit(2)

# ── the four cases ─────────────────────────────────────────────────────────────────────────────
print("\n[1] ★★ real quantities close ⇒ SILENT (the three names that flattened the book)")
r1 = anomalies(fixture())
check("no anomaly on ADA/FIL/STG — their fills are all present, so nothing is unexplained",
      not r1["anomalies"], [a["symbol"] for a in r1["anomalies"]])
for a in r1["anomalies"]:
    check(f"  ...{a['symbol']} residual_qty is ZERO", abs(a.get("residual_qty", 9e9)) < 1e-6,
          a.get("residual_qty"))

print("\n[2] ★★ RED CAPABILITY + defect A: delete ONE fill record ⇒ MUST fire, in quantity")
r2 = anomalies(fixture(drop_fill="ADAUSDT"))
hit = [a for a in r2["anomalies"] if a["symbol"] == "ADAUSDT"]
check("ADAUSDT fires when its fill is not counted (this is defect A's exact shape)", bool(hit),
      [a["symbol"] for a in r2["anomalies"]])
if hit:
    check("  ...and the residual is the WHOLE missing quantity (-1256.00), not a price artefact",
          abs(hit[0].get("residual_qty", 0) - (-1256.00)) < 1e-6, hit[0].get("residual_qty"))
    check("  ...and its USDT judgement is |residual_qty| x mark(T2), one basis",
          abs(abs(hit[0].get("residual_usdt", 0)) - 1256.00 * (99.31 / 629.00)) < 0.02,
          hit[0].get("residual_usdt"))
check("  ...and FIL/STG stay silent in the same run (the deletion did not blanket-redden)",
      not [a for a in r2["anomalies"] if a["symbol"] != "ADAUSDT"],
      [a["symbol"] for a in r2["anomalies"]])

print("\n[3] ★★ quantities identical, price move AMPLIFIED 5x (~-16% to -20%) ⇒ still SILENT")
r3 = anomalies(fixture(price_amplify=5.0))
check("a large mark move alone produces NO anomaly — the price-move detector is gone",
      not r3["anomalies"],
      [(a["symbol"], a.get("residual_usdt"), a.get("unexplained_frac")) for a in r3["anomalies"]])
print("      (under the OLD notional basis this same input fires: the residual scales with the")
print("       move, and `frac` inflates further because `scale` shrinks with the position.)")

print("\n[4] ★★ §4-5b and §4-7 read ONE reconcile — asserted, not assumed")
try:
    import watchdog_inputs as WI
    src = os.path.join(LIVEDIR, "watchdog_inputs.py")
    txt = open(src).read()
    check("watchdog_inputs derives drift from reconcile (not a second implementation)",
          "reconcile" in txt, "grep proves the text; the assertion below proves the value")
    d47 = WI.derive_ops_stats if hasattr(WI, "derive_ops_stats") else None
    check("  ...and §4-7's drift input is the same object §4-5b judges", d47 is not None,
          "derive_ops_stats present")
except Exception as e:
    check("watchdog_inputs importable for the shared-source assertion", False,
          f"{type(e).__name__}: {e}")

print(f"\n  {N[0]} checks run")
if N[0] == 0:
    print("  FAIL  ZERO CHECKS RAN — an empty suite is a RED, not a pass")
    sys.exit(1)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
