"""Demonstrate — not assert — that `_baseline_provenance` goes GREEN on a baseline it should reject.

> created 2026-08-04 13:1x UTC | Session: B4-retrain | ledger #31 (the part that needs no caliber ruling)

★ THE CLAIM UNDER TEST, in the form that can fail: I told team-lead that a BASELINE_BY_YEAR built
  from PRODUCTION-FOLD (in-sample) predictions would pass both existing provenance checks and still
  be wrong. **That is a claim about a guard's reach, and a claim about reach must be executed, not
  argued** — the whole night's lesson is that "a guard exists" gets read as "a guard covers this".

  So this feeds `_baseline_provenance` a baseline derived from the in-sample arm and shows what it
  returns. If it comes back green, the blind spot is real and demonstrated. If it comes back red,
  my claim was wrong and I retract it.

★ AND THE PARTNER THAT MUST GO RED (§8-e): the same function fed a value that is NOT a measurement
  at all (a made-up number). If that also comes back green, the function is not checking anything
  and the demonstration above proves nothing.

★★★ OUTCOME (2026-08-04): **MY CLAIM WAS REFUTED, and the refutation is more useful than being
   right would have been.** `_baseline_provenance` went RED on all five in-sample years —
   `matches_declared=False` — because it compares the DECLARED constant against
   `engine_fullhist_replay.json`, and that artifact still holds the OLD generation's numbers. So it
   objects, but **not for the reason I gave**: it is not detecting in-sampleness, it is detecting
   *table != artifact*.

   ⇒ WHERE THE BLIND SPOT ACTUALLY LIVES, one level up: #31 requires regenerating the replay
     artifact for the new generation. **Once the artifact is regenerated from the same predictions
     the table is built from, both are in-sample together and the guard goes green.** The check
     enforces CONSISTENCY between table and artifact — it has no opinion on whether the predictions
     behind both were out-of-sample.
   ⇒ So the caliber question I raised still stands, and the extra provenance question I proposed
     should be attached to the ARTIFACT's generation, not to the table's value.
   ⇒ And the practical constraint for #31 is now explicit: **the new table and a regenerated
     `engine_fullhist_replay.json` must ship together**, or every year returns UNKNOWN.

READ-ONLY. Imports the live monitor module; writes nothing.
"""
import json
import sys

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False
import monitor as M     # noqa: E402  the live shadow module itself, not a copy

print("REPLAY_ARTIFACT = %s" % M.REPLAY_ARTIFACT)
rep = json.load(open(M.REPLAY_ARTIFACT))
per_year = rep.get("per_year", {})
print("artifact per_year keys: %s" % sorted(per_year.keys()))

# The coded constants (old generation, leak-contaminated) — the status quo.
print("\n=== ARM 1: the CODED value (status quo, old generation) ===")
for y, v in sorted(M.BASELINE_BY_YEAR.items()):
    p = M._baseline_provenance(y, v)
    print("  %d declared %.4f -> is_measurement=%s matches_declared=%s"
          % (y, v, p.get("is_measurement"), p.get("matches_declared")))

# ARM 2: what a PRODFOLD-derived (in-sample) baseline would look like. Measured today by
# b4_baseline_by_year.py on the same book/grid/caliber; 18% above the OOS arm on average.
PRODFOLD_INSAMPLE = {2022: 0.0792, 2023: 0.0644, 2024: 0.0673, 2025: 0.0740, 2026: 0.0639}
print("\n=== ARM 2: a PRODFOLD (IN-SAMPLE) baseline — the thing I claim the guard cannot see ===")
green = 0
for y, v in sorted(PRODFOLD_INSAMPLE.items()):
    p = M._baseline_provenance(y, v)
    ok = bool(p.get("is_measurement")) and bool(p.get("matches_declared"))
    green += ok
    print("  %d declared %.4f -> is_measurement=%s matches_declared=%s   %s"
          % (y, v, p.get("is_measurement"), p.get("matches_declared"),
             "GREEN (guard does not object)" if ok else "red"))

# ARM 3 — the partner that MUST go red: a value that is not a measurement of anything.
print("\n=== ARM 3 (partner that must go RED): a made-up number ===")
red = 0
for y in sorted(PRODFOLD_INSAMPLE):
    p = M._baseline_provenance(y, 0.4242)
    ok = bool(p.get("is_measurement")) and bool(p.get("matches_declared"))
    red += (not ok)
    print("  %d declared 0.4242 -> is_measurement=%s matches_declared=%s   %s"
          % (y, p.get("is_measurement"), p.get("matches_declared"), "red (good)" if not ok else "GREEN"))

print("\n=== VERDICT ===")
if red == len(PRODFOLD_INSAMPLE):
    print("  partner control: all made-up values REJECTED -> the function does check something.")
else:
    print("  *** partner control did NOT go red on every made-up value — this demonstration is void.")
    sys.exit(1)
print("  in-sample arm: %d/%d years came back GREEN." % (green, len(PRODFOLD_INSAMPLE)))
if green:
    print("  ⇒ CLAIM CONFIRMED, and demonstrated rather than argued: `_baseline_provenance` checks")
    print("    (a) is-it-a-measurement and (b) time-disjointness. An IN-SAMPLE baseline is a genuine")
    print("    measurement and is time-disjoint, so it passes — while being ~18% too high, which")
    print("    raises DECAY_FRAC x baseline and makes the guard fire on a HEALTHY model.")
    print("  ⇒ the missing question is not 'same generation?' — PRODFOLD and the 5-fold ARE the same")
    print("    generation. It is 'were these predictions out-of-sample for the years they score?'")
else:
    print("  ⇒ CLAIM REFUTED — the guard does object. I withdraw the concern.")
