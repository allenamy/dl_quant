#!/usr/bin/env python3
"""tests_export_helper_approval.py — R8-G-01 / E-0921-F: the export gate's APPROVED HELPER is checked BEFORE it is used.

THE DEFECT UNDER TEST (independent review round 8, 2026-09-21; the lead reproduced it). The contract carried
`gates.BUNDLE_export.approved_helper_sha256 = {v4e_export_baseline_lib.py: eeb68b94…}` and NOTHING consumed it at run time — the
only readers in the whole repo were two TEST files. The gates recorded the helper's CURRENT sha in the receipt and `require`
compared "the file now == the sha the receipt recorded". Swap the helper BEFORE the run and regenerate the receipt, and every one
of those relations still holds while the code that decides the verdict was never approved: the reviewer flipped both real E2b
entries from `month_not_approved` to TRUE by replacing only their helper copy.

THE ACCEPTANCE BAR (E-0921-F, which REPLACED the lead's weaker one — the weaker one asked only that SOME gate enforce the field,
which is exactly what let a mechanism nothing enforced pass). Four clauses, and the block that tests each:
  1. consumed by the PRODUCTION ENTRY, BEFORE use — not a post-receipt re-hash, not a test .......... [A], [B], [E3], [F]
  2. a MISSING value REFUSES, never skips ........................................................... [C]
  3. both gates, the driver preflight and `require` share ONE implementation, not four copies ....... [E]
  4. TWO negative controls — "changed after the receipt" AND "swapped before the run" ............... [D1] and [B]/[D2]
Clause 4 is the one that matters most: control D1 already existed and it passes the swapped-before-the-run case BY
CONSTRUCTION ([D2] measures that, it does not assert it), which is exactly why the old bar was satisfied by a broken mechanism.

ORDER. Every red probe re-states its own GREEN baseline in the same check: a red-capability probe on an already-red baseline is
vacuous (2026-09-16). The variant population is enumerated by GLOB and asserted non-empty and closed — a fix that is
instance-shaped when the defect is class-shaped is not a fix.

Run:  python3 tests_export_helper_approval.py      exit 0 iff every check passes
"""
import glob, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok:
        FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def load(path, alias=None):
    alias = alias or os.path.basename(path)[:-3].replace(".", "_")
    spec = importlib.util.spec_from_file_location(alias, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[alias] = m
    spec.loader.exec_module(m)
    return m


def sha_of(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


GC = load(f"{HERE}/v4_gate_common.py", "v4_gate_common")
XBL = load(f"{HERE}/v4e_export_baseline_lib.py", "v4e_export_baseline_lib")
CJ = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
GATE = "BUNDLE_export"

# ------------------------------------------------------------------ fixtures: real files, so the gate's own sha256_file runs
FROZEN_SEPT_PINS = "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece"
FROZEN_SEPT_BASE = "dce6a228543b4e3cea014d6494b6bfec5aab92b21d82f50b74c241ea9739a43d"


def make_month_files(tag, n_live):
    d = tempfile.mkdtemp(prefix=f"r8g01_{tag}_")
    pins = {"symbols_live": [f"SYM{i}USDT" for i in range(n_live)], "keep_names": [f"KEEP{i}" for i in range(3)]}
    pp = f"{d}/live_pins.json"; json.dump(pins, open(pp, "w"))
    bp = f"{d}/slow_scorer_base.json"; json.dump({"fold24": 0.0548, "fold25": 0.0630, "month": tag}, open(bp, "w"))
    out = f"{d}/bundle"; os.makedirs(out)
    return {"dir": d, "OUT": out, "LIVE_PINS": pp, "BUNDLE_BASE": bp, "pins": pins,
            "pins_sha": sha_of(pp), "base_sha": sha_of(bp)}


SEPT = make_month_files("2026-09", 400)
OCT = make_month_files("2026-10", 407)


def contract(entries, helper_block="real"):
    """A contract of the shape the gate reads. `helper_block`: 'real' = the committed approved_helper_sha256 verbatim;
    None / dict = whatever the probe wants to put there (including nothing at all)."""
    ab = {"live_pins_sha256": FROZEN_SEPT_PINS, "bundle_base_sha256": FROZEN_SEPT_BASE}
    g = {"approved_baseline": ab}
    if helper_block == "real":
        g["approved_helper_sha256"] = dict(CJ["gates"][GATE]["approved_helper_sha256"])
    elif helper_block is not None:
        g["approved_helper_sha256"] = helper_block
    m = {mo: (None if v is None else {"LIVE_PINS": {"sha256": v[0]}, "BUNDLE_BASE": {"sha256": v[1]}, "approved_utc": "fixture"})
         for mo, v in entries.items()}
    c = {"gates": {GATE: g}, "month_contract_rulings": {XBL.RULING_KEY: {XBL.MAP_KEY: m}}}
    return c, ab


class Cx:
    """The gate's context, reduced to exactly what E2_config reads — including `gc`, the shared v4_gate_common module."""
    def __init__(self, mod, fx, contract_dict, ab, month):
        json.dump({"params": dict(mod.FROZEN_PARAMS), "keep_names": fx["pins"]["keep_names"],
                   "symbols_live": fx["pins"]["symbols_live"]}, open(f"{fx['OUT']}/config.json", "w"))
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


def swapped_helper(suffix=b"\n# swapped before the run (R8-G-01 probe)\n"):
    """A COPY of the real helper with different bytes, under the SAME basename — the reviewer's counterexample exactly:
    the gate's own source is untouched, only the module it imports is a different file."""
    d = tempfile.mkdtemp(prefix="r8g01_swap_")
    p = f"{d}/v4e_export_baseline_lib.py"
    with open(p, "wb") as f:
        f.write(open(f"{HERE}/v4e_export_baseline_lib.py", "rb").read() + suffix)
    return load(p, f"swapped_xbl_{os.path.basename(d)}")


# ------------------------------------------------------------------ the population (GLOB, never a hand-written list)
ALL_X = sorted(glob.glob(f"{HERE}/v4e_gate_export*.py"))
ARCHIVED = sorted(p for p in ALL_X if ".r" in os.path.basename(p)[len("v4e_gate_export"):])
LIVE_GATES = sorted(p for p in ALL_X if p not in ARCHIVED)
R2_ARCHIVED = sorted(p for p in ARCHIVED if ".r2_" in os.path.basename(p))
MODS = {os.path.basename(p): load(p) for p in LIVE_GATES}
print(f"\n== population: {len(MODS)} live export-gate variant(s) {sorted(MODS)}; {len(ARCHIVED)} archived "
      f"({len(R2_ARCHIVED)} of them the pre-R8-G-01 .r2_ snapshots) ==\n")
check("P0 population is closed and non-empty: every v4e_gate_export*.py is LIVE or an archived .r<n>_<sha8> snapshot, at least "
      "two live variants exist, and the pre-R8-G-01 .r2_ snapshots that [B2] measures the defect on are present",
      len(MODS) >= 2 and len(MODS) + len(ARCHIVED) == len(ALL_X) and len(R2_ARCHIVED) == 2,
      {"live": sorted(MODS), "archived": sorted(os.path.basename(p) for p in ARCHIVED)})

SEPT_OK = {"2026-09": (SEPT["pins_sha"], SEPT["base_sha"]), "2026-10": None}
OCT_OK = {"2026-09": (SEPT["pins_sha"], SEPT["base_sha"]), "2026-10": (OCT["pins_sha"], OCT["base_sha"])}

# ================================================================== [A] BASELINE IS GREEN (against the COMMITTED contract)
hmap, herr = GC.approved_helpers(GATE, CJ)
check("★ A1 BASELINE GREEN, committed contract: every helper gates.BUNDLE_export.approved_helper_sha256 declares is on disk and "
      "byte-identical to its approved sha (set compared, not count)",
      hmap is not None and all(GC.require_approved_helper(GATE, f"{HERE}/{n}", CJ)[0] for n in hmap),
      {"declared": sorted(hmap or {}), "err": herr})

check("A2 the declared helper set == the code modules the gate REGISTERS as receipt inputs (an approval nobody records cannot be "
      "re-hashed, R14-C2; a recorded module nobody approved is R8-G-01 itself)",
      sorted(hmap or {}) == sorted(["v4e_export_baseline_lib.py", "v4_gate_common.py"]), sorted(hmap or {}))

for nm, mod in MODS.items():
    c, ab = contract(SEPT_OK)
    ok, det = e2b(mod, SEPT, c, ab, "2026-09")
    check(f"★ A3 [{nm}] BASELINE GREEN: real helper, approved contract, month 2026-09, files that ARE the approved pair ⇒ E2b PASS "
          f"(without this green every red below would be vacuous)", ok is True, det)

# ================================================================== [B] NEGATIVE CONTROL 2 — SWAPPED BEFORE THE RUN
#     This is the control the lead's earlier bar did NOT require, and the only one that catches R8-G-01.
SWAP = swapped_helper()
check("B0 the swapped helper really is a different file under the same basename, and it still WORKS (so a green→red flip below "
      "is the approval refusing, not an import error): its answer for 2026-10 on an approving contract is the approved pair",
      sha_of(SWAP.__file__) != sha_of(f"{HERE}/v4e_export_baseline_lib.py")
      and os.path.basename(SWAP.__file__) == "v4e_export_baseline_lib.py"
      and (SWAP.approved_export_baseline(contract(OCT_OK)[0], "2026-10")[0] or {}).get("live_pins_sha256") == OCT["pins_sha"],
      {"swapped_sha": sha_of(SWAP.__file__)[:12], "real_sha": sha_of(f"{HERE}/v4e_export_baseline_lib.py")[:12]})

for nm, mod in MODS.items():
    gate_sha_before = sha_of(f"{HERE}/{nm}")
    c, ab = contract(OCT_OK)
    ok_green, _ = e2b(mod, OCT, c, ab, "2026-10")                       # green baseline with the REAL helper, same probe
    real_xbl = mod.xbl
    mod.xbl = SWAP                                                      # ← swapped BEFORE the run; gate source untouched
    ok_swap, det_swap = e2b(mod, OCT, c, ab, "2026-10")
    mod.xbl = real_xbl
    ok_restored, _ = e2b(mod, OCT, c, ab, "2026-10")
    gate_sha_after = sha_of(f"{HERE}/{nm}")
    check(f"★★★ B1 [{nm}] NEGATIVE CONTROL 2 — helper SWAPPED BEFORE THE RUN, gate source byte-identical throughout: "
          f"E2b GREEN→FAIL(helper_not_approved)→GREEN. This is the reviewer's counterexample, and it is the control whose "
          f"ABSENCE let a mechanism nothing enforced pass the old acceptance line",
          ok_green is True and ok_swap is False and det_swap.get("refused") == "helper_not_approved"
          and ok_restored is True and gate_sha_before == gate_sha_after,
          {"green": ok_green, "swapped": ok_swap, "refused": det_swap.get("refused"), "restored": ok_restored,
           "gate_sha_unchanged": gate_sha_before == gate_sha_after, "why": str(det_swap.get("why"))[:160]})

for p in R2_ARCHIVED:
    nm = os.path.basename(p)
    old = load(p, f"old_{nm[:-3]}")
    old.xbl = SWAP
    c, ab = contract(OCT_OK)
    ok_old, det_old = e2b(old, OCT, c, ab, "2026-10")
    check(f"★★★ B2 [{nm}] THE DEFECT, MEASURED NOT ASSERTED: the archived pre-R8-G-01 gate, on the very same swapped helper, "
          f"returns E2b TRUE — unapproved code decided the verdict and nothing refused",
          ok_old is True, det_old)

# ================================================================== [C] A MISSING VALUE REFUSES (clause 2), never skips
CASES = [
    ("C1 no approved_helper_sha256 block at all (the old contract shape)", None, "is absent"),
    ("C2 block present but no entry for the helper this gate imports", {"some_other_lib.py": "0" * 64}, "not an approved helper"),
    ("C3 the approved value is malformed (not 64 hex)", {"v4e_export_baseline_lib.py": "not-a-sha"}, "not a sha256"),
    ("C4 the approved value is null", {"v4e_export_baseline_lib.py": None}, "not a sha256"),
    ("C5 the block declares nothing but prose", {"why": "we totally check this"}, "declares no helper"),
]
for nm, mod in MODS.items():
    for label, blk, want in CASES:
        blk2 = None if blk is None else {k: v for k, v in blk.items()}
        if blk2 is not None and "v4_gate_common.py" not in blk2 and "why" not in blk2:
            pass                                             # deliberately incomplete: the probe is about the refusal, not the map
        c, ab = contract(OCT_OK, helper_block=blk2)
        ok, det = e2b(mod, OCT, c, ab, "2026-10")
        check(f"{label} [{nm}] ⇒ REFUSED by name, never skipped",
              ok is False and det.get("refused") == "helper_not_approved" and want in str(det.get("why")),
              {"ok": ok, "refused": det.get("refused"), "why": str(det.get("why"))[:200]})

_missing = os.path.join(tempfile.mkdtemp(prefix="r8g01_gone_"), "v4e_export_baseline_lib.py")
ok_m, why_m, _ = GC.require_approved_helper(GATE, _missing, CJ)
check("C6 an approved helper that is NOT ON DISK is refused by name (absence is a refusal, not an unverifiable pass)",
      ok_m is False and "not on disk" in str(why_m), str(why_m)[:200])

# ================================================================== [D] NEGATIVE CONTROL 1, and proof it misses the defect
def receipt(helper_sha, helper_path, *, include_helper=True, self_sha=None):
    """A minimal BUNDLE_export receipt of the shape v4_gate_common.finalize writes."""
    d = tempfile.mkdtemp(prefix="r8g01_rcpt_")
    data = f"{d}/data.bin"; open(data, "wb").write(b"payload")
    inputs_sha = {k: sha_of(data) for k in GC.REQUIRED_INPUTS[GATE]}
    inputs_path = {k: data for k in GC.REQUIRED_INPUTS[GATE]}
    inputs_sha["live_pins"] = sha_of(data); inputs_path["live_pins"] = data
    if include_helper:
        inputs_sha["export_baseline_lib"] = helper_sha
        inputs_path["export_baseline_lib"] = helper_path
        inputs_sha["v4_gate_common"] = sha_of(f"{HERE}/v4_gate_common.py")
        inputs_path["v4_gate_common"] = f"{HERE}/v4_gate_common.py"
    r = {"gate": GATE, "PASS": True, "self_sha256": self_sha or sha_of(f"{HERE}/v4e_gate_export_v2.py"),
         "inputs_sha256": inputs_sha, "inputs_path": inputs_path, "utc": "fixture",
         "interp": {"optimize": 0, "debug": True, "bytes_warning": 0, "warnoptions": []}}
    rp = f"{d}/receipt.json"; json.dump(r, open(rp, "w"))
    return rp, {"live_pins": data}


REAL_H = f"{HERE}/v4e_export_baseline_lib.py"
_floor = GC.REQUIRED_INPUTS[GATE]
rp, decl = receipt(sha_of(REAL_H), REAL_H)
ok_base, why_base = GC.require(rp, dict(decl, **{k: decl["live_pins"] for k in _floor}), expected_gate=GATE,
                               expected_self_sha=sha_of(f"{HERE}/v4e_gate_export_v2.py"))
check("★ D0 GREEN BASELINE for every require probe below: a receipt whose recorded helper sha IS the approved sha, with the full "
      "registered floor declared, is ACCEPTED — without this green the D1/D2/E2 reds would be vacuous",
      ok_base is True, str(why_base)[:220])

# D1 — the control that ALREADY existed
tmp_copy = tempfile.mkdtemp(prefix="r8g01_d1_")
shutil.copy(REAL_H, f"{tmp_copy}/v4e_export_baseline_lib.py")
rp1, decl1 = receipt(sha_of(REAL_H), f"{tmp_copy}/v4e_export_baseline_lib.py")
open(f"{tmp_copy}/v4e_export_baseline_lib.py", "ab").write(b"\n# changed AFTER the receipt\n")
_d1 = dict(decl1, **{k: decl1["live_pins"] for k in _floor})
_d1["export_baseline_lib"] = f"{tmp_copy}/v4e_export_baseline_lib.py"      # declared, as require_main derives it from disk
_d1["v4_gate_common"] = f"{HERE}/v4_gate_common.py"
ok1, why1 = GC.require(rp1, _d1, expected_gate=GATE, expected_self_sha=sha_of(f"{HERE}/v4e_gate_export_v2.py"))
_d1_recorded = json.load(open(rp1))["inputs_sha256"]["export_baseline_lib"]
check("★ D1 NEGATIVE CONTROL 1 (pre-existing): the receipt records the APPROVED sha (measured: recorded == approved) and the "
      "helper file then CHANGES ON DISK ⇒ require refuses. This control was already there and it is the only one the earlier "
      "acceptance line demanded",
      ok1 is False and _d1_recorded == GC.approved_helpers(GATE, CJ)[0]["v4e_export_baseline_lib.py"]
      and sha_of(f"{tmp_copy}/v4e_export_baseline_lib.py") != _d1_recorded,
      {"why": str(why1)[:200], "recorded_is_approved": _d1_recorded[:12]})

# D2 — the SAME shape as the defect: the receipt RECORDS the swapped sha, and the file on disk still equals what it recorded
swap_dir = tempfile.mkdtemp(prefix="r8g01_d2_")
swap_path = f"{swap_dir}/v4e_export_baseline_lib.py"
open(swap_path, "wb").write(open(REAL_H, "rb").read() + b"\n# swapped BEFORE the run\n")
rp2, decl2 = receipt(sha_of(swap_path), swap_path)
_d2 = dict(decl2, **{k: decl2["live_pins"] for k in _floor})
_d2["export_baseline_lib"] = swap_path
_d2["v4_gate_common"] = f"{HERE}/v4_gate_common.py"
ok2, why2 = GC.require(rp2, _d2, expected_gate=GATE, expected_self_sha=sha_of(f"{HERE}/v4e_gate_export_v2.py"))
_d2_recorded = json.load(open(rp2))["inputs_sha256"]["export_baseline_lib"]
_old_control_satisfied = sha_of(swap_path) == _d2_recorded          # D1's premise MEASURED, not asserted from prose
check("★★★ D2 SWAPPED BEFORE THE RUN, consumer side: the receipt records the SWAPPED sha and the file on disk still EQUALS what "
      "it recorded — measured here, so control D1's premise is satisfied and D1 has nothing to say — and require refuses anyway, "
      "on the APPROVAL clause. This is the gap D1 alone left open, and the reason the earlier acceptance line passed a broken "
      "mechanism",
      ok2 is False and _old_control_satisfied and _d2_recorded != GC.approved_helpers(GATE, CJ)[0]["v4e_export_baseline_lib.py"],
      {"why": str(why2)[:200], "disk_equals_recorded": _old_control_satisfied, "recorded": _d2_recorded[:12]})

# D3 moved: "every imported helper must be RECORDED" is a property of the CODE, not of an old receipt. Requiring it inside
#     `require` refused every receipt written by a gate source that predates the helper (the round 4-7 judge fixtures approve
#     archived exporters on purpose, and 37 of them went red). It is checked at the production entry instead, against the
#     modules the process actually imported — measured below, with its own green control.
#     The census is a property of the PROCESS, so it is measured in an isolated directory holding exactly what a production
#     gate process imports — in THIS test process sys.modules also holds every archived variant the harness loaded, which is
#     precisely why the census runs at the production entry and not inside run_all.
_d3dir = tempfile.mkdtemp(prefix="r8g01_census_")
for _f in ("ELIGIBILITY_CONTRACT.json", "v4_gate_common.py", "v4e_export_baseline_lib.py"):
    shutil.copy(f"{HERE}/{_f}", f"{_d3dir}/{_f}")
_ = load(f"{_d3dir}/v4_gate_common.py", "d3_gc"); _ = load(f"{_d3dir}/v4e_export_baseline_lib.py", "d3_xbl")
_rec_ok = {"export_baseline_lib": f"{_d3dir}/v4e_export_baseline_lib.py", "v4_gate_common": f"{_d3dir}/v4_gate_common.py"}
ok_d3g, why_d3g, det_d3g = GC.helper_closure(GATE, _d3dir, f"{_d3dir}/entry.py", CJ, recorded=_rec_ok)
_rec_bad = {"v4_gate_common": f"{_d3dir}/v4_gate_common.py"}
ok_d3, why_d3, det_d3 = GC.helper_closure(GATE, _d3dir, f"{_d3dir}/entry.py", CJ, recorded=_rec_bad)
check("★ D3 GREEN then RED at the PRODUCTION ENTRY: with both imported modules registered as receipt inputs the census passes; "
      "drop one registration and it refuses by name — a dependency that is not RECORDED cannot be re-hashed (R14-C2), and a "
      "producer that silently stopped registering its helper is caught where the imports are visible, not from an old receipt",
      ok_d3g is True and ok_d3 is False and det_d3["unrecorded"] == ["v4e_export_baseline_lib.py"],
      {"green": (ok_d3g, det_d3g.get("recorded")), "red": str(why_d3)[:180]})

check("D4 and the consumer side does NOT impose that requirement (measured): a receipt recording no helper at all is not "
      "refused on the helper clause, because refusing it would reject every receipt written before the helper existed",
      GC.receipt_helpers_approved(GATE, {"inputs_path": {"live_pins": "/x/y.npz"}, "inputs_sha256": {"live_pins": "0" * 64}}, CJ)[0] is True,
      GC.receipt_helpers_approved(GATE, {"inputs_path": {}, "inputs_sha256": {}}, CJ))

# ================================================================== [E] ONE IMPLEMENTATION, not four copies (clause 3)
#     Behavioural, not textual: replace the SHARED resolver with a refusing stub and watch every entry's verdict flip.
_real_resolver = GC.approved_helpers
_stub_reason = "STUB: the shared resolver refused"


def _stub(gate, contract=None):
    return None, _stub_reason


for nm, mod in MODS.items():
    c, ab = contract(OCT_OK)
    ok_g, _ = e2b(mod, OCT, c, ab, "2026-10")
    GC.approved_helpers = _stub
    ok_s, det_s = e2b(mod, OCT, c, ab, "2026-10")
    GC.approved_helpers = _real_resolver
    ok_r, _ = e2b(mod, OCT, c, ab, "2026-10")
    check(f"★ E1 [{nm}] the gate routes through the SHARED v4_gate_common.approved_helpers: stubbing it flips GREEN→RED→GREEN and "
          f"the stub's own reason appears in the receipt — a variant with its own inlined copy would stay green and be named here",
          ok_g is True and ok_s is False and ok_r is True and _stub_reason in str(det_s.get("why")),
          {"green": ok_g, "stubbed": ok_s, "restored": ok_r, "why": str(det_s.get("why"))[:120]})

GC.approved_helpers = _stub
ok_e2, why_e2 = GC.require(rp, dict(decl, **{k: decl["live_pins"] for k in _floor}), expected_gate=GATE,
                           expected_self_sha=sha_of(f"{HERE}/v4e_gate_export_v2.py"))
GC.approved_helpers = _real_resolver
check("★ E2 `require` routes through the same shared resolver: green baseline D0 asserted in this probe, then stubbing the "
      "resolver flips the consumer side red with the stub's OWN reason",
      ok_base is True and ok_e2 is False and _stub_reason in str(why_e2), {"baseline": (ok_base, str(why_base)[:120]), "stubbed": str(why_e2)[:200]})

GC.approved_helpers = _stub
ok_e4, why_e4, _ = GC.helper_closure(GATE, HERE, f"{HERE}/v4e_gate_export_v2.py", CJ)
GC.approved_helpers = _real_resolver
check("★ E4 the production-entry CENSUS routes through the same shared resolver: stubbing it flips the closure red with the "
      "stub's own reason", ok_e4 is False and _stub_reason in str(why_e4), str(why_e4)[:200])

# E3 — the driver. Its OWN bytes, extracted between the heredoc delimiters and executed as a program, twice: once against a
#      sandbox whose helper is approved, once against the same sandbox with the helper swapped. The two runs differ in exactly
#      one named failure. Nothing here re-implements the driver; if the block ever stops existing, the extraction fails loudly.
def extract_preflight(sh_path):
    src = open(sh_path, encoding="utf-8").read()
    key = 'preflight.json" <<\'PYEOF\''
    i = src.find(key)
    if i < 0:
        return None
    i = src.find("\n", i + len(key))          # the heredoc body starts after the rest of that command line (`; rc=$?`)
    if i < 0:
        return None
    i += 1
    j = src.find("\nPYEOF\n", i)
    return None if j < 0 else src[i:j + 1]


PRE = extract_preflight(f"{HERE}/chain_v4_monthly.sh")
check("E3a the monthly driver's preflight block is locatable between its own heredoc delimiters and is non-trivial (this is the "
      "driver's own bytes; the probe below executes them rather than re-implementing them)",
      PRE is not None and len(PRE) > 2000 and "approved_export_baseline" in PRE, None if PRE is None else len(PRE))


def make_preflight_sandbox(chain_dir):
    """ONE sandbox, used for BOTH runs, so the two fail sets differ only by the helper's bytes — the temp paths appear verbatim
    inside the driver's own failure strings, so two different sandboxes would differ everywhere and the set comparison would
    measure the tmpdir instead of the mechanism."""
    d = tempfile.mkdtemp(prefix="r8g01_pf_")
    D = f"{d}/dev"; R = f"{d}/root"; os.makedirs(D); os.makedirs(f"{R}/v4_gates")
    for f in ("ELIGIBILITY_CONTRACT.json", "v4_gate_common.py", "v4e_export_baseline_lib.py"):
        shutil.copy(f"{chain_dir}/{f}", f"{D}/{f}")
    for f in ("builder_fea82.py", "builder_fea89.py", "base_trainer.py"):
        open(f"{D}/{f}", "w").write("# preflight fixture\n")
    prog = f"{d}/preflight_extracted.py"; open(prog, "w", encoding="utf-8").write(PRE)
    env = dict(os.environ)
    env.update({"D": D, "R": R, "PY": sys.executable, "V4_DEV_FILES": "v4_gate_common.py", "V4_PF_INPUTS": "",
                "V4_MONTH": "2026-10", "V4_MONTH_ENV": f"{D}/ELIGIBILITY_CONTRACT.json", "V4_ROLL_REQUIRED": "0",
                "V4_ROLL_SRC": "v4_gate_roll_paths.py", "MONTHS_ALL": "202601", "SEEDS": "42",
                "BUNDLE_GENERATION": "fixture", "HC": D, "PREV_BUNDLE": D,
                "GATE_STEP1": "v4_gate_step1.py", "GATE_STEP2": "v4_gate_step2.py",
                "BUILDER_FEA82": f"{D}/builder_fea82.py", "BUILDER_FEA89": f"{D}/builder_fea89.py",
                "BASE_TRAINER": f"{D}/base_trainer.py", "DLW_EXT": D, "F8_EXT": D})
    env.pop("PYTHONOPTIMIZE", None)
    return {"dir": d, "D": D, "R": R, "prog": prog, "env": env}


def run_preflight(sb, swap_helper):
    """Run the driver's OWN extracted preflight bytes against the sandbox, with the helper either approved or swapped."""
    real = open(f"{HERE}/v4e_export_baseline_lib.py", "rb").read()
    with open(f"{sb['D']}/v4e_export_baseline_lib.py", "wb") as f:
        f.write(real + (b"\n# swapped before the run (R8-G-01 probe)\n" if swap_helper else b""))
    out = f"{sb['R']}/v4_gates/preflight.json"
    if os.path.exists(out):
        os.remove(out)
    p = subprocess.run([sys.executable, "-B", sb["prog"], out], capture_output=True, text=True, env=sb["env"], cwd=sb["dir"])
    try:
        res = json.load(open(out))
    except Exception:                                          # noqa: BLE001
        res = None
    return p, res


if PRE:
    _sb = make_preflight_sandbox(HERE)
    p_ok, r_ok = run_preflight(_sb, swap_helper=False)
    p_sw, r_sw = run_preflight(_sb, swap_helper=True)
    f_ok = set(r_ok["fails"]) if r_ok else set()
    f_sw = set(r_sw["fails"]) if r_sw else set()
    added = sorted(f_sw - f_ok)
    removed = sorted(f_ok - f_sw)
    _r8 = [a for a in added if "helper NOT approved" in a and "R8-G-01" in a]
    _xb = "no approved export baseline"
    _other_added = [a for a in added if a not in _r8 and _xb not in a]
    _other_removed = [a for a in removed if _xb not in a]
    check("★★★ E3b the DRIVER consumes the approval BEFORE the chain runs: same extracted driver bytes, same sandbox, only the "
          "helper's bytes swapped ⇒ the fail SET gains the named R8-G-01 refusal and NOTHING ELSE moves (sets compared, not "
          "counts), and the approved run records the helper block ok",
          r_ok is not None and r_sw is not None and len(_r8) == 1 and not _other_added and not _other_removed
          and (r_ok["inputs"].get("_export_helper_approval") or {}).get("ok") is True
          and (r_sw["inputs"].get("_export_helper_approval") or {}).get("ok") is False,
          {"r8_line": [a[:130] for a in _r8], "other_added": _other_added, "other_removed": _other_removed,
           "ok_helpers": (r_ok or {}).get("inputs", {}).get("_export_helper_approval", {}).get("ok"),
           "sw_helpers": (r_sw or {}).get("inputs", {}).get("_export_helper_approval", {}).get("ok"),
           "stderr": (p_sw.stderr or "")[-160:]})
    _reason_ok = (r_ok["inputs"].get("_export_baseline_approval") or {}).get("refused") if r_ok else None
    _reason_sw = (r_sw["inputs"].get("_export_baseline_approval") or {}).get("refused") if r_sw else None
    check("★★★ E3c and the driver does NOT USE the unapproved helper's answer: with the helper approved the October refusal is "
          "'month_not_approved' (the helper was consulted); with it swapped the refusal becomes 'helper_not_approved' — the "
          "helper's answer was never obtained, which is what 'before use' means",
          _reason_ok == "month_not_approved" and _reason_sw == "helper_not_approved",
          {"approved_run": _reason_ok, "swapped_run": _reason_sw})

# ================================================================== [F] CLASS SHAPE: a NEW unregistered sibling is refused
sand = tempfile.mkdtemp(prefix="r8g01_new_")
for f in ("ELIGIBILITY_CONTRACT.json", "v4_gate_common.py", "v4e_export_baseline_lib.py"):
    shutil.copy(f"{HERE}/{f}", f"{sand}/{f}")
open(f"{sand}/brand_new_helper_2027.py", "w").write("VALUE = 1\n")
_ = load(f"{sand}/v4e_export_baseline_lib.py", "sand_xbl")
_ = load(f"{sand}/v4_gate_common.py", "sand_gc")
_ = load(f"{sand}/brand_new_helper_2027.py", "sand_new")
ok_f0, _w0, det_f0 = GC.helper_closure(GATE, sand, f"{sand}/entry.py", CJ)
check("★★★ F1 CLASS SHAPE, not instance shape: a module nobody registered, imported from the gate's own directory, is refused by "
      "the production-entry census — the answer to 'if someone adds a NEW helper tomorrow, is it caught?' is measured here, not "
      "promised. The census is also shown non-empty (a census that silently found zero would make this vacuous)",
      ok_f0 is False and det_f0["n_census"] >= 3 and any(b["module"] == "brand_new_helper_2027.py" for b in det_f0["unapproved"]),
      {"census": det_f0["census"], "unapproved": [b["module"] for b in det_f0["unapproved"]]})

os.remove(f"{sand}/brand_new_helper_2027.py")
sys.modules.pop("sand_new", None)
ok_f1, why_f1, det_f1 = GC.helper_closure(GATE, sand, f"{sand}/entry.py", CJ)
check("F2 GREEN CONTROL for F1: with that module gone the same census over the same directory passes, so F1's red is the "
      "unregistered module and not the census refusing everything",
      ok_f1 is True and set(det_f1["census"]) == {"v4_gate_common.py", "v4e_export_baseline_lib.py"},
      {"census": det_f1["census"], "why": str(why_f1)[:160]})

# ================================================================== [G] the COMMITTED contract, as data
approved = CJ["gates"][GATE]["approved_source_sha256"]
live_shas = {os.path.basename(p): sha_of(p) for p in LIVE_GATES}
check("G1 committed contract: the set of approved BUNDLE_export sources == the set of live variant shas on disk (SET, not count)",
      sorted(approved) == sorted(live_shas.values()),
      {"approved": [a[:12] for a in approved], "on_disk": {k: v[:12] for k, v in live_shas.items()}})
sup = CJ["gates"][GATE].get("superseded_source_sha256") or {}
arch = {os.path.basename(p): sha_of(p) for p in ARCHIVED}
check("G2 every archived snapshot's sha is declared superseded, and no superseded sha is still approved (so the pre-R8-G-01 "
      "sources [B2] measures the defect on cannot confer candidacy on anything)",
      set(arch.values()) <= set(sup) and not (set(sup) & set(approved)),
      {"archived": {k: v[:12] for k, v in arch.items()}, "superseded": [s[:12] for s in sup]})

line = f"EXPORT_HELPER_APPROVAL {'ALL PASS' if not FAILS else 'FAILURES'} checks={N[0]} failed={len(FAILS)} {FAILS if FAILS else ''}"
print("\n" + line.strip(), flush=True)
sys.exit(0 if not FAILS else 1)
