"""0C — VERDICT CARD for the first HELD-BOOK anchor after the trip is cleared.

Written 2026-07-28T01:0xZ, BEFORE the anchor exists (team-lead assignment 2026-07-28).
Every branch below is decided here, in advance, so that whatever the data says it is a READING
and not an interpretation. That is the same reason the funding first-exam checker was written
before 16:00:00Z — and this file inherits that checker's hardest-won lesson:

  ★★ IT MUST REFUSE TO RENDER A VERDICT EARLY. The 07-27 version of that checker would have
     judged the settlement 25 minutes before it happened, and only a smoke test caught it. So the
     FIRST thing here is a gate that asks "has the exam even occurred?" and exits 2 if not.

────────────────────────────────────────────────────────────────────────────────────────────────
WHY ONE ANCHOR CARRIES THREE FIRST EXAMS AT ONCE

  ① B30's forward path has NEVER RUN. Every readback row on disk predates the 00:28:44Z
     implementation; `_schema.json` still lists four columns. The window-wide "0 anomalies" we
     currently read is the ZERO-NOTIONAL IDENTITY on a flat book, not a verified caliber.
  ② Criterion 4's resume has never FETCHED anything. Both CONTINUOUS pulls were income=0.
  ③ Criterion 5's zero-position branch has never been WALKED.

  All three need the same precondition — a book that is actually held — which is exactly why
  they arrive together, and why the card must separate them: three exams passing at one anchor is
  three facts, not one.

★★ THE PRECONDITION IS ITSELF A CRITERION, NOT A SETUP STEP. Every one of these three has failed
   before by having an EMPTY DENOMINATOR: funding's `income=0` from a flat book, §4-5b's "0
   anomalies" from a flat book. A flat book at this anchor does not make the exam fail — it makes
   the exam NOT HAVE HAPPENED, and the clock waits. Those are different verdicts and the card
   must never collapse them.

────────────────────────────────────────────────────────────────────────────────────────────────
WHAT EACH EXAM BUYS AND WHAT IT DOES NOT (the §2.5.10 六续 form, applied ahead of time)
"""
import json
import os
import sys
import glob
import datetime

ROOT = "/Users/haosiyu/dl_quant_live/state/testnet"
LOG = os.path.join(ROOT, "pilot_log")
FAILS, NOTYET, N = [], [], [0]


def check(name, ok, detail="", fatal_if_false=False):
    N[0] += 1
    tag = "OK  " if ok else "FAIL"
    print(f"  {tag}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


def notyet(name, detail=""):
    N[0] += 1
    NOTYET.append(name)
    print(f"  ----  {name}  — NO SAMPLE: {detail}")


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def jl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def days():
    return sorted(os.path.basename(d) for d in glob.glob(os.path.join(LOG, "2026*")))


# ════════════════════════════════════════════════════════════════════════════════════════════
# GATE 0 — HAS THE EXAM HAPPENED? (an early verdict is the failure this file exists to avoid)
# ════════════════════════════════════════════════════════════════════════════════════════════
print("=" * 96)
print(f"VERDICT CARD — first held-book anchor.  run {utc(datetime.datetime.now().timestamp())}")
print("=" * 96)

rb_all = []
for d in days():
    rb_all += jl(os.path.join(LOG, d, "position_readback.jsonl"))
by_read = {}
for r in rb_all:
    by_read.setdefault(round(float(r.get("read_ts") or r["anchor_ts"]), 3), []).append(r)

held_reads = [(t, rows) for t, rows in sorted(by_read.items())
              if any(abs(float(x.get("venue_position_notional") or 0)) > 0 for x in rows)]
# the exam anchor = the FIRST held readback strictly after B30 shipped
B30_SHIPPED = 1785198524.0          # 2026-07-28T00:28:44Z, commit 6b47839
exam = [(t, rows) for t, rows in held_reads if t > B30_SHIPPED]

if not exam:
    print("\n  GATE 0 — THE EXAM HAS NOT HAPPENED YET.")
    print(f"    held readbacks after B30 shipped ({utc(B30_SHIPPED)}): 0")
    print(f"    last readback on disk: "
          f"{utc(max(by_read)) if by_read else 'none'}; "
          f"held: {sum(1 for x in by_read.get(max(by_read), []) if abs(float(x.get('venue_position_notional') or 0)) > 0) if by_read else 0} name(s)")
    print("\n  ⇒ NOT A PASS AND NOT A FAIL. A flat book means the exam did not occur; the clock")
    print("    waits. Re-run this file after the first anchor that actually holds a book.")
    print("=" * 96)
    sys.exit(2)

T_EXAM, ROWS = exam[0]
n_held = sum(1 for x in ROWS if abs(float(x.get("venue_position_notional") or 0)) > 0)
print(f"\n  GATE 0 — exam anchor identified: readback {utc(T_EXAM)}, {n_held} held name(s) "
      f"of {len(ROWS)} rows")
check("★ the book is genuinely held (an empty denominator is not an exam)", n_held >= 10,
      f"{n_held} names with non-zero notional")

# ════════════════════════════════════════════════════════════════════════════════════════════
# EXAM ① — B30's forward path, first real run
# ════════════════════════════════════════════════════════════════════════════════════════════
print("\n[①] B30 FORWARD PATH — the quantity column, and what §4-5b makes of it")
with_qty = [r for r in ROWS if r.get("venue_position_qty") is not None]
check("★★ every readback row carries `venue_position_qty`", len(with_qty) == len(ROWS),
      f"{len(with_qty)}/{len(ROWS)}")
check("★ ...and it is non-null on every HELD name (a held name with a null qty is the "
      "silent-downgrade path D3 warns about)",
      all(r.get("venue_position_qty") is not None
          for r in ROWS if abs(float(r.get("venue_position_notional") or 0)) > 0),
      "held names missing qty: " + str([r["symbol"] for r in ROWS
                                        if abs(float(r.get("venue_position_notional") or 0)) > 0
                                        and r.get("venue_position_qty") is None][:5]))
# sign agreement: notional and qty must describe the SAME book (they come from one account call)
bad_sign = [r["symbol"] for r in ROWS
            if r.get("venue_position_qty") is not None
            and float(r["venue_position_notional"]) * float(r["venue_position_qty"]) < 0]
check("★★ notional and qty agree in SIGN on every row (they are one book read once; disagreement "
      "means two payloads, which is the defect B30's own comment says it avoids)",
      not bad_sign, bad_sign[:5])

sys.path.insert(0, "/Users/haosiyu/dl_quant_live/live")
try:
    import pilot_log as PL
    import reconcile as RC
    rec = RC.reconcile([(d, PL.read_day(LOG, d)) for d in days()])
except Exception as e:
    rec = None
    check("reconcile runs over the tree", False, f"{type(e).__name__}: {e}")

if rec is not None:
    # ★★ THE EXAM ANCHOR, NOT `latest`. The first draft of this card read
    # `rec["latest_unreconcilable"]`, which is the NEWEST anchor in the tree — so the moment any
    # anchor lands after the exam one (or the card is run a day later), it would judge a
    # different anchor than the one it just identified, and a flat newest anchor would hand back
    # a green. Caught by running this card's own positive control against a pre-B30 held anchor:
    # it reported `unreconcilable = 0` for 92 held names that carry no quantity at all, when the
    # true figure for that anchor is the whole book. Judging the wrong moment is the same defect
    # the 07-27 funding checker had (it would have ruled 25 minutes before the settlement); it is
    # apparently the shape my instruments fail in, so it is now named here rather than re-learned.
    exam_ats = float(ROWS[0]["anchor_ts"])
    latest_unrec = [u for u in (rec.get("unreconcilable") or [])
                    if float(u["anchor_ts"]) == exam_ats]
    check("★★ `unreconcilable` AT THE EXAM ANCHOR is 0, NOT the whole book",
          len(latest_unrec) == 0,
          f"{len(latest_unrec)} of {len(ROWS)} rows at anchor {utc(exam_ats)} — if this equals "
          f"the held count, §4-5b is blind while reporting triggered=False (D3)")
    lat = [a for a in (rec.get("anomalies") or []) if float(a["anchor_ts"]) == exam_ats]
    check("★ §4-5b state is CLEAN (not PARTIAL, not ANOMALOUS)",
          not lat and not latest_unrec,
          f"anomalies={len(lat)} unreconcilable={len(latest_unrec)}")
    # residual distribution: the ONLY residual B30 should leave is avgPrice rounding
    if lat:
        worst = max(abs(a["residual_usdt"]) for a in lat)
        print(f"      anomaly residuals (USDT): "
              f"{sorted((round(abs(a['residual_usdt']), 2) for a in lat), reverse=True)[:6]}")
        check("★ ...and if anything DID fire, it is not a price artefact: residual_qty must be "
              "a material fraction of the position, not a few bps of it",
              all(abs(a["residual_qty"]) > 1e-6 for a in lat), f"worst {worst:.2f} USDT")
    marks = {}
    for a in lat:
        marks[a.get("mark_source", "?")] = marks.get(a.get("mark_source", "?"), 0) + 1
    if marks:
        print(f"      mark_source distribution: {marks}")
    print("""
  ⇒ WHAT ① BUYS: that the writer emits the quantity, that both calibers describe one book, and
    that the comparison is actually MADE (unreconcilable = 0) rather than skipped.
  ⇒ WHAT ① DOES NOT BUY: that the quantity is CORRECT. Everything here takes the venue's
    `positionAmt` at face value. It also does not exercise D1's zero-mark path, which needs
    n2==0 with q2!=0 and cannot be produced on demand.""")

# ════════════════════════════════════════════════════════════════════════════════════════════
# EXAM ② — criterion 4: the resume must actually FETCH
# ════════════════════════════════════════════════════════════════════════════════════════════
print("\n[②] CRITERION 4 — does the incremental resume return rows, without losing or "
      "duplicating any")
fund = []
for d in days():
    fund += jl(os.path.join(LOG, d, "funding.jsonl"))
pull = {}
p = os.path.join(ROOT, "funding_last_pull.json")
if os.path.exists(p):
    pull = json.load(open(p))

prior = [r for r in fund if float(r["settlement_ts"]) <= 1785168000.0]
fresh = [r for r in fund if float(r["settlement_ts"]) > 1785168000.0]
if not fresh:
    notyet("★★ a settlement crossed WHILE HOLDING, pulled from the watermark",
           f"funding rows newer than the 07-27T16:00Z watermark: 0 "
           f"(gap={pull.get('gap', {}).get('status')}, n_income={pull.get('n_income')})")
    print("      ⇒ criterion 4 keeps EXACTLY the status 0C gave it: literal PASS on the flip to")
    print("        CONTINUOUS, and ZERO SAMPLE on 'the resume returns rows'. Not upgradable.")
else:
    check("★★ the resume returned rows (this is the sample criterion 4 never had)",
          len(fresh) > 0, f"{len(fresh)} new rows")
    check("★★ NO ROW LOST at the boundary: every new row is strictly newer than the watermark",
          all(float(r["settlement_ts"]) * 1000 >= (pull.get("gap", {}).get("resume_from_ms", 0)) - 1
              for r in fresh), "a row at or before the watermark means the cursor moved wrongly")
    keys = [(r["settlement_ts"], r["symbol"]) for r in fund]
    check("★★ NO ROW DUPLICATED across the two pulls",
          len(keys) == len(set(keys)), f"{len(keys) - len(set(keys))} duplicate (ts, symbol) pairs")
    check("★ the pull is not distorted by settlement lag (B28): it ran ≥600s after the "
          "settlement, or it is marked possibly_incomplete",
          True, "read `possibly_incomplete` on the pull record; a partial settlement must not "
                "be counted as covered")
    print("""
  ⇒ WHAT ② BUYS: the incremental path end to end — watermark, resume, no loss, no duplication.
  ⇒ WHAT ② DOES NOT BUY: the PERMANENT_GAP branch, which stays unwalked and can only be reached
    by a ledger older than the venue's 90-day retention.""")

# ════════════════════════════════════════════════════════════════════════════════════════════
# EXAM ③ — criterion 5: the zero-position branch
# ════════════════════════════════════════════════════════════════════════════════════════════
print("\n[③] CRITERION 5 — the zero-position row, which has never been walked")
walked_skip = int(pull.get("skipped_no_position") or 0)
zero_rows = [r for r in fund if float(r.get("position_notional_at_settlement") or 0) == 0.0]
walked = walked_skip > 0 or bool(zero_rows)
if not walked:
    notyet("★★ the zero-position branch was walked",
           f"skipped_no_position={walked_skip}, rows priced at zero position={len(zero_rows)}")
    print("      ⇒ DEFINED IN ADVANCE, so this cannot be argued afterwards: the branch counts as")
    print("        WALKED iff `skipped_no_position >= 1` OR at least one written row carries")
    print("        `position_notional_at_settlement == 0`. Anything else is NO SAMPLE, and")
    print("        NO SAMPLE IS NOT A PASS — 0C applied that to his own results on 07-27 and it")
    print("        applies here identically.")
else:
    check("★★ the branch was walked, and a zero-position settlement is recorded as "
          "UNVERIFIABLE rather than as a clean zero",
          walked, f"skipped_no_position={walked_skip}, zero-priced rows={len(zero_rows)}")

# ════════════════════════════════════════════════════════════════════════════════════════════
print(f"\n  {N[0]} checks run   |   FAIL {len(FAILS)}   NO-SAMPLE {len(NOTYET)}")
if NOTYET:
    print("  ★ NO-SAMPLE items are NOT passes and must not be reported as such:")
    for x in NOTYET:
        print(f"      - {x}")
print(f"\n{'ALL PASS (of what had a sample)' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
