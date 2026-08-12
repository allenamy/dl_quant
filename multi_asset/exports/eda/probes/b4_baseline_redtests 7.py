"""Acceptance for the BASELINE_BY_YEAR generation swap — RED observed, not just green. (#31)

SPEC 0f8be1fe §2-5 acceptance:
  (1) every new baseline year from ONE remeasure, with panel / member-set / generation recorded
  (2) generation binding landed — running with an OLD generation's hash must go **RED**
  (3) the disjoint check reads a DECLARED window, and an artificial overlap must go **RED**
  (4) DECAY_FRAC bitwise unchanged

★ WHY EVERY CHECK HAS A RED TWIN: "a guard observed only in green is indistinguishable from a guard
  that is blind" — the static-gate lesson. Each arm below states which way it must come out BEFORE
  the assertion, so a check that silently stops discriminating shows up as a green where a red was
  demanded.

★ AND ONE ARM EXISTS BECAUSE THE HASH CANNOT COVER IT: (d) out-of-sample. A production-fold arm is
  the SAME generation and differs only by being in-sample — measured 1.18x higher, which would raise
  DECAY_FRAC*baseline and fire the guard on a healthy model. The generation hash passes it happily.
"""
import json
import os
import shutil
import sys
import tempfile

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False
import monitor as M  # noqa: E402

FAILS = []


def check(label, cond, expect_pass=True):
    ok = bool(cond) == bool(expect_pass)
    print("  %-58s %-16s %s" % (label, "PASS" if cond else "RED", "ok" if ok else "*** WRONG WAY ***"))
    if not ok:
        FAILS.append(label)


def prov_all(years=(2022, 2023, 2024, 2025, 2026)):
    return [M._baseline_provenance(y, M.BASELINE_BY_YEAR[y]) for y in years]


print("REPLAY_ARTIFACT = %s" % os.path.basename(M.REPLAY_ARTIFACT))
print("EXPECTED_GENERATION = %s" % M.EXPECTED_GENERATION)
rep = json.load(open(M.REPLAY_ARTIFACT))

# ---------------------------------------------------------------- (1) one remeasure, recorded
print("\n=== (1) one remeasure, provenance recorded ===")
check("all 5 years present in the artifact", len(rep["per_year"]) == 5)
check("generation block recorded", bool(rep.get("generation", {}).get("members")))
check("panel + ch31 arm recorded", rep.get("panel", {}).get("ch31_arm") == "SERVE")
check("baseline window declared", rep.get("baseline_window", {}).get("last_anchor_ts_ms") is not None)
p = prov_all()
check("every year: is_measurement", all(x["is_measurement"] for x in p))
check("every year: matches_declared", all(x["matches_declared"] for x in p))
check("every year: generation_matches", all(x["generation_matches"] for x in p))
check("every year: out_of_sample", all(x["out_of_sample"] for x in p))

# ---------------------------------------------------------------- (2) generation RED twin
print("\n=== (2) generation binding — the OLD generation must go RED ===")
tmp = tempfile.mkdtemp()
alt = os.path.join(tmp, "alt.json")
bad = json.loads(json.dumps(rep))
bad["generation"]["id"] = "0000badgeneration"
json.dump(bad, open(alt, "w"))
real = M.REPLAY_ARTIFACT
try:
    M.REPLAY_ARTIFACT = alt
    check("a DIFFERENT generation id -> generation_matches",
          all(x["generation_matches"] for x in prov_all()), expect_pass=False)
finally:
    M.REPLAY_ARTIFACT = real

# ---------------------------------------------------------------- (d) out-of-sample RED twin
print("\n=== (d) out-of-sample declaration — an in-sample artifact must go RED ===")
bad2 = json.loads(json.dumps(rep))
bad2["predictions_out_of_sample"] = False
alt2 = os.path.join(tmp, "alt2.json")
json.dump(bad2, open(alt2, "w"))
try:
    M.REPLAY_ARTIFACT = alt2
    check("predictions_out_of_sample=False -> out_of_sample",
          all(x["out_of_sample"] for x in prov_all()), expect_pass=False)
finally:
    M.REPLAY_ARTIFACT = real

# ---------------------------------------------------------------- (3) disjoint: declared + RED twin
print("\n=== (3) disjoint reads the DECLARED window, and an overlap must go RED ===")
end = int(rep["baseline_window"]["last_anchor_ts_ms"])
d_ok = M._baseline_window_disjoint(end + 3600_000)
check("scoring AFTER the declared window -> disjoint", d_ok.get("disjoint") is True)
check("window_source is the declared one",
      d_ok.get("window_source", "").startswith("declared"))
d_bad = M._baseline_window_disjoint(end - 30 * 24 * 3600_000)
check("scoring INSIDE the declared window -> disjoint", d_bad.get("disjoint") is True,
      expect_pass=False)

# ---------------------------------------------------------------- (4) DECAY_FRAC untouched
print("\n=== (4) DECAY_FRAC unchanged ===")
check("DECAY_FRAC == 0.5 exactly", M.DECAY_FRAC == 0.5)

shutil.rmtree(tmp, ignore_errors=True)
print("\n=== RESULT ===")
if FAILS:
    print("  *** %d arm(s) came out the WRONG WAY: %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("  all arms came out the way they were required to, greens AND reds.")
print("  new BASELINE_BY_YEAR = %s" % M.BASELINE_BY_YEAR)
