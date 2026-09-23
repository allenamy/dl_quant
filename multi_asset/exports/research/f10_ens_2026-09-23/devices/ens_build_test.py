#!/usr/bin/env python3
"""ens_build_test.py — red/green test of ens_build.py on the REAL F10 inputs (no fixture), prereg 45aba1f3f step 2 tests ① ② ③.
The three checks (each is a function below; the same function is used for the green baseline and for the red mutations):
  C1 identical seeds: ENS(P42, P42) consumed exactly as combo_target.step() consumes F10 (zf = rankdata(s[okf])/max(okf.sum()-1,1)-.5 over the
     anchor's MEMBERS, lines asserted verbatim in the pinned combo_target.py) equals zf(P42) bit for bit (uint64 view) on every combo-axis anchor.
  C2 one-seed-only: a copy of P2027 with ONE member name at ONE anchor set to NaN ⇒ that name is NaN in ENS, the anchor's one-only count is 1,
     and every OTHER anchor of ENS is bit-equal to the unmutated ENS.
  C3 round trip: the written ENS file has the source OOF's key set, dtypes, shapes, E_ts and symbols, and P read back equals the in-memory ENS
     bit for bit (ens_build.roundtrip).
Order: BASELINE (all three GREEN with measured values printed) must pass first; then each mutation must go RED with its NAMED reason:
  M1 builder with the second seed's sign flipped (rank average of s and −s is constant)      → C1 red 'C1 zf differs'
  M2 builder that fills a one-seed-only name with the available seed's normalised rank      → C2 red 'C2 one-only name finite'
  M3 writer that reverses the symbols axis                                                   → C3 red 'roundtrip symbols differ'
  M4 writer that stores P as float64                                                         → C3 red 'roundtrip dtype/shape P'
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ens_build_test.py PATH,HOME,LC_CTYPE <f10_s42.npz> <sha> <f10_s2027.npz> <sha>
       <dlw_targets.npz> <sha> <combo_target.py> <sha> <universe_ext.npz> <sha> <scratch_dir> <out.json>
"""
import os, sys, json, time

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ens_build as EB

p42, s42, p27, s27, pt, st, pct, sct, pu, su, SCR, OUT = sys.argv[2:14]
os.makedirs(SCR, exist_ok=True)
assert EB.sha(pct) == sct and EB.sha(pu) == su and EB.sha(pt) == st, "pinned inputs"
CT = open(pct).read()
for q in ("okf=np.isfinite(f10_score);zf=np.full(n,np.nan)", "zf[okf]=rankdata(np.asarray(f10_score)[okf])/max(okf.sum()-1,1)-.5"):
    assert q in CT, "combo_target consumption line absent: " + q
D42, _ = EB.load_oof(p42, s42); D27, _ = EB.load_oof(p27, s27)
T = np.load(pt, allow_pickle=True); U = np.load(pu, allow_pickle=True)
a = D42["E_ts"]; COMBO = np.nonzero((a >= 1672531200) & (a <= U["ts"][-1]))[0]
MEM = [np.asarray(T["members"][i], int) for i in range(len(a))]
rec = {"device": "ens_build_test.py", "self_sha256": EB.sha(os.path.abspath(__file__)), "builder_sha256": EB.sha(os.path.join(HERE, "ens_build.py")),
       "utc_start": EB.iso(time.time()), "combo_axis_anchors": int(len(COMBO)), "cases": []}


class Red(Exception):
    pass


def zf(s):
    """combo_target.step's F10 consumption, verbatim arithmetic"""
    n = len(s); okf = np.isfinite(s); z = np.full(n, np.nan)
    z[okf] = rankdata(np.asarray(s)[okf]) / max(okf.sum() - 1, 1) - .5
    return z


def C1(build):
    E, _, _ = build(D42["P"], D42["P"].copy())
    for i in COMBO:
        m = MEM[i]
        if not np.array_equal(zf(E[i, m]).view(np.uint64), zf(D42["P"][i, m]).view(np.uint64)): raise Red(f"C1 zf differs at {EB.iso(a[i])}")
    return {"anchors_checked": int(len(COMBO)), "zf_bitwise_equal": True}


PICK_I = int(COMBO[len(COMBO) // 2]); PICK_J = int(MEM[PICK_I][len(MEM[PICK_I]) // 2])


def C2(build, E0):
    P27m = D27["P"].copy(); assert np.isfinite(P27m[PICK_I, PICK_J]); P27m[PICK_I, PICK_J] = np.nan
    E, nb, no = build(D42["P"], P27m)
    if np.isfinite(E[PICK_I, PICK_J]): raise Red(f"C2 one-only name finite at {EB.iso(a[PICK_I])} col {PICK_J}")
    if no[PICK_I] != 1: raise Red(f"C2 one-only count {int(no[PICK_I])} != 1")
    other = np.ones(len(a), bool); other[PICK_I] = False
    if not np.array_equal(E[other].view(np.uint32), E0[other].view(np.uint32)): raise Red("C2 other anchors changed")
    return {"anchor": EB.iso(a[PICK_I]), "col": PICK_J, "ens_is_nan": True, "one_only_count": int(no[PICK_I]), "other_anchors_bitwise_equal": True,
            "one_only_total_elsewhere": int(no[other].sum())}


def C3(write, E0, name):
    p = os.path.join(SCR, f"ENS_{name}.npz")
    try:
        write(p, E0, D42["E_ts"], D42["symbols"])
        try:
            return EB.roundtrip(p, E0, D42)
        except EB.EnsError as e:
            raise Red(str(e))
    finally:
        if os.path.exists(p): os.remove(p)


def case(name, fn, expect=None):
    try:
        detail = fn(); res = {"case": name, "outcome": "GREEN", "detail": detail}
    except Red as e:
        res = {"case": name, "outcome": "RED", "error": str(e)[:300]}
    if expect is None: res["as_expected"] = res["outcome"] == "GREEN"
    else: res["expected_red_reason"] = expect; res["as_expected"] = res["outcome"] == "RED" and expect in res.get("error", "")
    rec["cases"].append(res); print(json.dumps(res)[:500], flush=True); return res


# ---------- baseline: the real builder, all three checks GREEN ----------
E0, NB0, NO0 = EB.build(D42["P"], D27["P"])
rec["baseline_one_only_total"] = int(NO0.sum())
base = [case("baseline_C1", lambda: C1(EB.build)), case("baseline_C2", lambda: C2(EB.build, E0)), case("baseline_C3", lambda: C3(EB.write_oof, E0, "base"))]
if not all(c["as_expected"] for c in base):
    rec["VERDICT"] = "RED_BASELINE"; json.dump(rec, open(OUT, "w"), indent=1); print("ENS_BUILD_TEST VERDICT=RED_BASELINE", flush=True); sys.exit(3)


# ---------- mutations ----------
def build_m1(P42, P27): return EB.build(P42, -P27)


def build_m2(P42, P27):
    E, nb, no = EB.build(P42, P27)
    for i in np.nonzero(no)[0]:
        f42 = np.isfinite(P42[i]); f27 = np.isfinite(P27[i]); one = f42 ^ f27
        src = np.where(f42, P42[i], P27[i]); fin = f42 | f27
        E[i, one] = ((rankdata(src[fin]) - 1) / max(fin.sum() - 1, 1))[one[fin]].astype(E.dtype)
    return E, nb, no


def write_m3(p, P, E_ts, symbols): return EB.write_oof(p, P, E_ts, symbols[::-1].copy())
def write_m4(p, P, E_ts, symbols): return EB.write_oof(p, P.astype(np.float64), E_ts, symbols)


case("M1_second_seed_sign_flipped", lambda: C1(build_m1), "C1 zf differs")
case("M2_one_only_filled_from_available_seed", lambda: C2(build_m2, E0), "C2 one-only name finite")
case("M3_symbols_reversed", lambda: C3(write_m3, E0, "m3"), "roundtrip symbols differ")
case("M4_P_float64", lambda: C3(write_m4, E0, "m4"), "roundtrip dtype/shape P")
ok = all(c["as_expected"] for c in rec["cases"])
rec["VERDICT"] = "PASS" if ok else "FAIL"; rec["utc_end"] = EB.iso(time.time())
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print("ENS_BUILD_TEST VERDICT=%s baseline=GREEN(3/3) mutations_red_as_named=%d/%d out_sha256=%s" % (
    rec["VERDICT"], sum(c["as_expected"] for c in rec["cases"][3:]), len(rec["cases"]) - 3, EB.sha(OUT)), flush=True)
sys.exit(0 if ok else 3)
