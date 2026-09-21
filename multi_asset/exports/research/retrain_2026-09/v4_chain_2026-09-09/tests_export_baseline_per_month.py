#!/usr/bin/env python3
"""tests_export_baseline_per_month.py — TRN-15: the export gate's approved pins / baseline are a PER-MONTH approval object.

THE DEFECT UNDER TEST. Check E2b_pins_identity required LIVE_PINS / BUNDLE_BASE to be byte-identical to ONE frozen pair in
gates.BUNDLE_export.approved_baseline, while RUNBOOK_monthly_retrain_2026-10.md §0★ step 0 requires both files to be re-made every
month. October therefore fails E2b BY CONSTRUCTION, for a reason unrelated to October. The ruling (contract
month_contract_rulings.TRN-15_export_baseline_per_month, user word 2026-09-18) is to PARAMETERISE and NOT to relax.

STRUCTURE (the order matters — a red-capability probe on an already-red baseline is vacuous, 2026-09-16):
  [A] BASELINE IS GREEN. Every later probe re-states its own green baseline before flipping one thing.
  [B] THE OLD SHAPE. The ARCHIVED pre-TRN-15 gate source is run on the same fixtures: green for September, red for October —
      the "fails by construction" claim is measured here, not asserted.
  [C] THE NEW SHAPE. Green for October once October's shas are approved; red when they are not.
  [D] NEVER "WHATEVER IS ON DISK". An October run whose contract entry holds September's shas is red.
  [E] CLASS SHAPE, not instance shape. The probes are run over EVERY export-gate variant found by glob (not a hand-written list),
      the population count is asserted, and a mutation of the SHARED helper must flip every variant's verdict — a variant that
      inlined its own copy of the lookup would stay green and be named here.

Run:  python3 tests_export_baseline_per_month.py      exit 0 iff ALL PASS
"""
import glob, hashlib, importlib.util, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok:
        FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def load(fname, alias=None):
    spec = importlib.util.spec_from_file_location(alias or fname[:-3].replace(".", "_"), f"{HERE}/{fname}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


XBL = load("v4e_export_baseline_lib.py", "v4e_export_baseline_lib")
sys.modules.setdefault("v4e_export_baseline_lib", XBL)
# ★ R8-G-01 (2026-09-21): E2b now verifies the helper against the contract's approved sha BEFORE using its answer, through
#   cx.gc.require_approved_helper — so the reduced context below must carry the real shared module, exactly as the gate does.
GC = load("v4_gate_common.py", "v4_gate_common")

# ------------------------------------------------------------------ fixtures: real files, so the gate's own sha256_file runs
FROZEN_SEPT_PINS = "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece"   # the frozen pair, quoted for the [F] identity check only
FROZEN_SEPT_BASE = "dce6a228543b4e3cea014d6494b6bfec5aab92b21d82f50b74c241ea9739a43d"


def sha_of(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def make_month_files(tag, n_live):
    """A month's LIVE_PINS + BUNDLE_BASE + the bundle config.json that agrees with them. Two months => two different sha pairs,
    which is exactly what RUNBOOK §0★ step 0 produces every month."""
    d = tempfile.mkdtemp(prefix=f"trn15_{tag}_")
    pins = {"symbols_live": [f"SYM{i}USDT" for i in range(n_live)], "keep_names": [f"KEEP{i}" for i in range(3)]}
    pp = f"{d}/live_pins.json"
    json.dump(pins, open(pp, "w"))
    bp = f"{d}/slow_scorer_base.json"
    json.dump({"fold24": 0.0548, "fold25": 0.0630, "month": tag}, open(bp, "w"))
    out = f"{d}/bundle"
    os.makedirs(out)
    return {"dir": d, "OUT": out, "LIVE_PINS": pp, "BUNDLE_BASE": bp, "pins": pins,
            "pins_sha": sha_of(pp), "base_sha": sha_of(bp)}


def write_config(mod, fx):
    json.dump({"params": dict(mod.FROZEN_PARAMS), "keep_names": fx["pins"]["keep_names"],
               "symbols_live": fx["pins"]["symbols_live"]}, open(f"{fx['OUT']}/config.json", "w"))


SEPT = make_month_files("2026-09", 400)
OCT = make_month_files("2026-10", 407)          # a different universe => a different sha pair, by construction


def contract(entries, with_block=True):
    """A contract of the shape the gate reads. entries maps month -> (pins_sha, base_sha) or None."""
    ab = {"live_pins_sha256": FROZEN_SEPT_PINS, "bundle_base_sha256": FROZEN_SEPT_BASE}
    # ★ R8-G-01: carry the COMMITTED approved_helper_sha256 verbatim — these fixtures are about the per-month pair, and the
    #   helper-approval probes live in tests_export_helper_approval.py.
    _hb = dict(json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))["gates"]["BUNDLE_export"]["approved_helper_sha256"])
    c = {"gates": {"BUNDLE_export": {"approved_baseline": ab, "approved_helper_sha256": _hb}}, "month_contract_rulings": {}}
    if with_block:
        m = {}
        for mo, v in entries.items():
            m[mo] = None if v is None else {"LIVE_PINS": {"sha256": v[0]}, "BUNDLE_BASE": {"sha256": v[1]},
                                            "approved_utc": "fixture"}
        c["month_contract_rulings"][XBL.RULING_KEY] = {XBL.MAP_KEY: m}
    return c, ab


class Cx:
    """The gate's context, reduced to exactly what E2_config reads."""
    def __init__(self, mod, fx, contract_dict, ab, month):
        write_config(mod, fx)
        self.E = {"LIVE_PINS": fx["LIVE_PINS"], "BUNDLE_BASE": fx["BUNDLE_BASE"]}
        self.OUT = fx["OUT"]
        self.contract, self.ab, self.month, self.gc = contract_dict, ab, month, GC
        self.res = {}

    def chk(self, name, ok, detail):
        self.res[name] = (bool(ok), detail)
        return bool(ok)


def e2b(mod, fx, contract_dict, ab, month):
    """-> (ok, detail) of E2b_pins_identity; ok is None if the check never ran."""
    cx = Cx(mod, fx, contract_dict, ab, month)
    try:
        mod.E2_config(cx)
    except Exception as e:                                    # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    return cx.res.get("E2b_pins_identity", (None, "check did not run"))


# ------------------------------------------------------------------ the population of export-gate variants (glob, never a list)
ARCHIVED = sorted(p for p in glob.glob(f"{HERE}/v4e_gate_export*.py") if ".r" in os.path.basename(p)[len("v4e_gate_export"):])
LIVE_GATES = sorted(p for p in glob.glob(f"{HERE}/v4e_gate_export*.py") if p not in ARCHIVED)
MODS = {os.path.basename(p): load(os.path.basename(p)) for p in LIVE_GATES}
print(f"\n== population: {len(MODS)} live export-gate variant(s) {sorted(MODS)}; {len(ARCHIVED)} archived snapshot(s) ==\n")
check("P0 population is closed and non-empty: every v4e_gate_export*.py is either LIVE or an archived .r<n>_<sha8> snapshot, "
      "and at least two live variants exist (a census that silently found zero would make every probe below vacuous)",
      len(MODS) >= 2 and len(MODS) + len(ARCHIVED) == len(glob.glob(f"{HERE}/v4e_gate_export*.py")),
      {"live": sorted(os.path.basename(p) for p in LIVE_GATES), "archived": sorted(os.path.basename(p) for p in ARCHIVED)})

SEPT_OK = {"2026-09": (SEPT["pins_sha"], SEPT["base_sha"]), "2026-10": None}
OCT_OK = {"2026-09": (SEPT["pins_sha"], SEPT["base_sha"]), "2026-10": (OCT["pins_sha"], OCT["base_sha"])}

# ================================================================== [A] BASELINE IS GREEN
for nm, mod in MODS.items():
    c, ab = contract(SEPT_OK)
    ok, det = e2b(mod, SEPT, c, ab, "2026-09")
    check(f"★ A1 [{nm}] BASELINE GREEN: month 2026-09, files whose shas ARE the approved 2026-09 pair ⇒ E2b PASS", ok is True, det)

# ================================================================== [B] THE OLD SHAPE — measured, not asserted
for p in ARCHIVED:
    nm = os.path.basename(p)
    old = load(nm)
    c, ab = contract(SEPT_OK)
    # the old gate compares against cx.ab, so hand it an ab that IS September's real pair for these fixtures
    ab_sept = {"live_pins_sha256": SEPT["pins_sha"], "bundle_base_sha256": SEPT["base_sha"]}
    ok_s, det_s = e2b(old, SEPT, c, ab_sept, "2026-09")
    check(f"★ B1 [{nm}] OLD SHAPE, GREEN BASELINE: the archived pre-TRN-15 gate passes E2b on the month its frozen pair was "
          f"frozen for (without this the B2 red would prove nothing)", ok_s is True, det_s)
    ok_o, det_o = e2b(old, OCT, c, ab_sept, "2026-10")
    check(f"★ B2 [{nm}] OLD SHAPE FAILS OCTOBER BY CONSTRUCTION: same gate, same frozen pair, October's re-made pins/baseline "
          f"⇒ E2b FAIL — the defect TRN-15 names", ok_o is False, det_o)

# ================================================================== [C] THE NEW SHAPE
for nm, mod in MODS.items():
    c, ab = contract(OCT_OK)
    ok, det = e2b(mod, OCT, c, ab, "2026-10")
    check(f"★ C1 [{nm}] NEW SHAPE GREEN: once October's two shas are approved for month 2026-10, October passes E2b", ok is True, det)

    c, ab = contract(SEPT_OK)                     # 2026-10 present and explicitly null
    ok, det = e2b(mod, OCT, c, ab, "2026-10")
    check(f"C2 [{nm}] a NULL October entry is a refusal, never a skipped check", ok is False and det.get("refused") == "month_not_approved", det)

    c, ab = contract({"2026-09": (SEPT["pins_sha"], SEPT["base_sha"])})   # no 2026-10 key at all
    ok, det = e2b(mod, OCT, c, ab, "2026-10")
    check(f"C3 [{nm}] an ABSENT October entry is a refusal (an absent key is an absent key, not a null verdict)",
          ok is False and det.get("refused") == "month_not_approved", det)

    c, ab = contract({}, with_block=False)        # the OLD contract shape
    ok, det = e2b(mod, SEPT, c, ab, "2026-09")
    check(f"C4 [{nm}] a contract with NO per-month block is refused by name — the frozen global approved_baseline is NOT a "
          f"fallback (a fallback would re-approve one month's files for every later month)",
          ok is False and det.get("refused") == "contract_block_absent", det)

    c, ab = contract(OCT_OK)
    ok, det = e2b(mod, OCT, c, ab, "")
    check(f"C5 [{nm}] a run that does not declare its month is refused by name (a gate that guesses binds nothing, E-0826-D)",
          ok is False and det.get("refused") == "month_not_declared", det)

    for bad, why in (({"2026-10": ("not-a-sha", OCT["base_sha"])}, "entry_malformed_LIVE_PINS_sha256"),):
        c, ab = contract(bad)
        ok, det = e2b(mod, OCT, c, ab, "2026-10")
        check(f"C6 [{nm}] a malformed approved sha is refused by name, not coerced", ok is False and det.get("refused") == why, det)

    c, ab = contract(OCT_OK)
    del c["month_contract_rulings"][XBL.RULING_KEY][XBL.MAP_KEY]["2026-10"]["BUNDLE_BASE"]
    ok, det = e2b(mod, OCT, c, ab, "2026-10")
    check(f"C7 [{nm}] an entry that approves the pins but not the baseline is refused — a half-approval is not an approval",
          ok is False and det.get("refused") == "entry_malformed_BUNDLE_BASE_missing", det)

# ================================================================== [D] NEVER "WHATEVER IS ON DISK"
for nm, mod in MODS.items():
    c, ab = contract({"2026-09": (SEPT["pins_sha"], SEPT["base_sha"]), "2026-10": (SEPT["pins_sha"], SEPT["base_sha"])})
    ok, det = e2b(mod, OCT, c, ab, "2026-10")
    check(f"★ D1 [{nm}] October files against an October entry holding SEPTEMBER's shas ⇒ FAIL: the gate demands the approved "
          f"sha, it does not accept the file it is given", ok is False, det)

    c, ab = contract({"2026-10": (OCT["pins_sha"], OCT["base_sha"])})
    ok_g, _ = e2b(mod, OCT, c, ab, "2026-10")                                     # green baseline for the flip below
    OCT2 = make_month_files("2026-10b", 409)                                      # a DIFFERENT October build
    ok_b, det_b = e2b(mod, OCT2, c, ab, "2026-10")
    check(f"★ D2 [{nm}] with the approval held fixed, swapping the files under it flips PASS→FAIL (green baseline asserted in "
          f"the same probe: {ok_g})", ok_g is True and ok_b is False, det_b)

# ================================================================== [E] CLASS SHAPE: every variant routes through the SHARED helper
saved = XBL.MAP_KEY
for nm, mod in MODS.items():
    c, ab = contract(OCT_OK)
    ok_before, _ = e2b(mod, OCT, c, ab, "2026-10")
    XBL.MAP_KEY = "approved_export_baselines_MUTATED"                             # the shared lookup now points nowhere
    ok_after, det_a = e2b(mod, OCT, c, ab, "2026-10")
    XBL.MAP_KEY = saved
    ok_restored, _ = e2b(mod, OCT, c, ab, "2026-10")
    check(f"★ E1 [{nm}] mutating the SHARED helper's lookup key flips this variant GREEN→RED→GREEN ⇒ the variant really consults "
          f"v4e_export_baseline_lib; a variant that inlined its own copy would stay green and be named here",
          ok_before is True and ok_after is False and ok_restored is True,
          {"before": ok_before, "after": ok_after, "restored": ok_restored, "detail": det_a})

# ================================================================== [F] the COMMITTED contract, as data
CP = f"{HERE}/ELIGIBILITY_CONTRACT.json"
CJ = json.load(open(CP))
ent, why, det = XBL.approved_export_baseline(CJ, "2026-09")
abr = CJ["gates"]["BUNDLE_export"]["approved_baseline"]
check("★ F1 committed contract: the 2026-09 entry carries EXACTLY the frozen pair ⇒ the September verdict is bit-identical "
      "before and after the parameterisation (the set is compared, not a count)",
      ent is not None and ent["live_pins_sha256"] == abr["live_pins_sha256"] == FROZEN_SEPT_PINS
      and ent["bundle_base_sha256"] == abr["bundle_base_sha256"] == FROZEN_SEPT_BASE, (why, det))
ent, why, _ = XBL.approved_export_baseline(CJ, "2026-10")
check("★ F2 committed contract: 2026-10 is not approved ⇒ an October export stops at E2b with a NAMED reason, with a receipt",
      ent is None and why == "month_not_approved", why)
approved = CJ["gates"]["BUNDLE_export"]["approved_source_sha256"]
live_shas = {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in LIVE_GATES}
check("F3 committed contract: the set of approved BUNDLE_export sources == the set of live variant shas on disk (SET, not count)",
      sorted(approved) == sorted(live_shas.values()), {"approved": [a[:12] for a in approved],
                                                       "on_disk": {k: v[:12] for k, v in live_shas.items()}})
sup = CJ["gates"]["BUNDLE_export"].get("superseded_source_sha256") or {}
arch_shas = {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in ARCHIVED}
check("F4 every archived snapshot's sha is declared superseded in the contract, and no superseded sha is still approved",
      set(arch_shas.values()) <= set(sup) and not (set(sup) & set(approved)),
      {"archived": {k: v[:12] for k, v in arch_shas.items()}, "superseded": [s[:12] for s in sup]})
helper = (CJ["gates"]["BUNDLE_export"].get("approved_helper_sha256") or {}).get("v4e_export_baseline_lib.py")
check("F5 the helper both gates import is itself a recorded, approved object (an unrecorded dependency cannot be re-hashed, R14-C2)",
      helper == hashlib.sha256(open(f"{HERE}/v4e_export_baseline_lib.py", "rb").read()).hexdigest(), str(helper)[:16])

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES'} ({N[0]} checks)" + ("" if not FAILS else f"\nfailed: {FAILS}"))
sys.exit(0 if not FAILS else 1)
