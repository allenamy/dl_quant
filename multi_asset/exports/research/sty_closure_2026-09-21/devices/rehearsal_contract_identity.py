#!/usr/bin/env python3
"""rehearsal_contract_identity.py — R8-G-02: what the October drill actually ran against, and whether it mattered.

THE FINDING (round-8 review §2 / notes/gates.md R8-G-02). AB_oct_NEW.json, AB_sept_NEW.json and R3stub_preflight.json (and the
two OLD receipts beside them) all record `ELIGIBILITY_CONTRACT.json = a071b604…`, while the contract frozen for that review
measured `4309e1b6…`. Every OTHER device in those receipts matches the tree exactly. So RUNBOOK_monthly_retrain_2026-10.md:354's
"driver / gate / helper / contract 四件逐文件与 git 单源相等" is FALSE for the fourth item, and the drill cannot certify the
current contract.

WHAT THIS DEVICE DOES, in the order the review asked for:
  A. IDENTITY. The a071b604 bytes were not in the repository at all — "explain the difference" was not possible from the tree.
     They are recovered from pod2 `/workspace/rehearse_2026-10_0921/D/ELIGIBILITY_CONTRACT.json`, archived beside the receipts,
     and re-hashed here. If the archived copy is not byte-identical to what the receipts record, this device refuses.
  B. THE DIFFERENCE, NAMED. A flattened key-by-key diff against the frozen contract, printed in full — not summarised.
  C. WHETHER IT MATTERED, MEASURED. The monthly driver's OWN preflight bytes are extracted from the driver the rehearsal used
     and run twice over one sandbox, changing ONLY the contract. Two fail SETS are compared (sets, not counts). This is the one
     thing that can turn "the fourth item differs" into "and here is exactly what that difference did or did not reach".

WHAT IT CANNOT DO, stated rather than implied: preflight is stage 1 of 17. A null result here says the difference did not reach
PREFLIGHT's verdict. It says nothing about the 16 stages that never ran, and it does not make the drill a certification of the
current contract — which has since moved again (R8-G-01 changed it a third time).

Exit 0 iff the archived bytes match what the receipts recorded AND the two preflight runs are compared successfully.
"""
import hashlib, io, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
CHAIN = os.path.join(REPO, "multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09")
RCPT = os.path.join(REPO, "docs/receipts/october_rehearsal_2026-09-21")
REHEARSED = os.path.join(RCPT, "rehearsed_contract_a071b604/ELIGIBILITY_CONTRACT.a071b604.json")
FROZEN = os.path.join(CHAIN, "ELIGIBILITY_CONTRACT.r9_4309e1b6.json")
RECEIPTS = ["AB_oct_NEW.json", "AB_oct_OLD.json", "AB_sept_NEW.json", "AB_sept_OLD.json", "R3stub_preflight.json"]

FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok:
        FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:320]) if detail is not None else ""), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, f"{p}[{i}]")
    else:
        yield p, o


# ══════════════════════════════════════════════════════════ A. IDENTITY
recorded = {}
for fn in RECEIPTS:
    p = os.path.join(RCPT, fn)
    d = json.load(open(p))
    recorded[fn] = (d.get("device_sha256") or {}).get("ELIGIBILITY_CONTRACT.json")
vals = sorted(set(v for v in recorded.values() if v))
check("A1 population: all five October-drill receipts record a contract sha, and they record ONE value (set compared, not count)",
      len(recorded) == len(RECEIPTS) and len(vals) == 1 and all(recorded.values()), recorded)
rehearsed_sha = sha(REHEARSED) if os.path.exists(REHEARSED) else None
check("★★★ A2 the archived bytes ARE what the receipts ran against: sha of the recovered pod2 copy == the sha all five receipts "
      "record. Without this the 'explanation' below would be about some other file",
      rehearsed_sha is not None and vals and rehearsed_sha == vals[0], {"archived": (rehearsed_sha or "")[:16], "recorded": vals[0][:16] if vals else None})
frozen_sha = sha(FROZEN)
check("A3 the frozen contract of the round-8 freeze is archived in the tree as ELIGIBILITY_CONTRACT.r9_4309e1b6.json",
      frozen_sha.startswith("4309e1b6"), frozen_sha[:16])
live_sha = sha(os.path.join(CHAIN, "ELIGIBILITY_CONTRACT.json"))
check("A4 and the LIVE contract is now a THIRD sha (R8-G-01 moved it again) — so the drill certifies neither the frozen nor the "
      "current contract, and re-running it is the only way to certify either",
      live_sha not in (rehearsed_sha, frozen_sha), {"rehearsed": (rehearsed_sha or "")[:12], "frozen": frozen_sha[:12], "live": live_sha[:12]})

# ══════════════════════════════════════════════════════════ B. THE DIFFERENCE, NAMED
a = dict(flat(json.load(open(REHEARSED))))
b = dict(flat(json.load(open(FROZEN))))
only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
differ = [k for k in sorted(set(a) & set(b)) if a[k] != b[k]]
print("\n  DIFFERENCE, key by key (rehearsed a071b604 vs frozen 4309e1b6):")
for k in only_a:
    print(f"    + only in rehearsed : {k} = {str(a[k])[:120]}")
for k in only_b:
    print(f"    - only in frozen    : {k} = {str(b[k])[:120]}")
for k in differ:
    print(f"    ~ differs           : {k}\n        rehearsed: {str(a[k])[:140]}\n        frozen   : {str(b[k])[:140]}")
diff_keys = only_a + only_b + differ
check("★★★ B1 the difference is CONFINED to gates.BUNDLE_export.approved_variants.v4e_gate_export_fp2dyn.py — the rehearsed "
      "contract still carries the PRE-TRN-15 variant sha 16e9cc32 and the old `base` string and lacks `trn15_note`, while its "
      "approved_source_sha256 / superseded / approved_helper / month_contract_rulings blocks ALREADY carry TRN-15. It is an "
      "INTERMEDIATE state of the same edit, not a different contract",
      all(k.startswith(".gates.BUNDLE_export.approved_variants.v4e_gate_export_fp2dyn.py") for k in diff_keys) and diff_keys,
      {"n_keys": len(diff_keys), "keys": diff_keys})
check("B2 and that intermediate state is INTERNALLY INCONSISTENT: approved_source_sha256 lists the TRN-15 fp2dyn sha 74e13a16 "
      "while the variant entry still points at 16e9cc32, which the same file declares superseded",
      a.get(".gates.BUNDLE_export.approved_source_sha256[1]", "").startswith("74e13a16")
      and a.get(".gates.BUNDLE_export.approved_variants.v4e_gate_export_fp2dyn.py.sha256", "").startswith("16e9cc32")
      and ".gates.BUNDLE_export.superseded_source_sha256.16e9cc32369daf634b03d05a5e1294cbae4ab2a8dc3f91a3e761100c0f7b453c" in a,
      {"approved[1]": a.get(".gates.BUNDLE_export.approved_source_sha256[1]", "")[:12],
       "variant.sha256": a.get(".gates.BUNDLE_export.approved_variants.v4e_gate_export_fp2dyn.py.sha256", "")[:12]})

# ══════════════════════════════════════════════════════════ C. WHETHER IT MATTERED, MEASURED
def extract_preflight(src_text):
    key = 'preflight.json" <<\'PYEOF\''
    i = src_text.find(key)
    if i < 0:
        return None
    i = src_text.find("\n", i + len(key))
    j = src_text.find("\nPYEOF\n", i)
    return None if (i < 0 or j < 0) else src_text[i + 1:j + 1]


# the driver the rehearsal used is cf1a5fbb… — the receipts say so. Take it from git rather than from the working tree, which
# R8-G-01 has since changed.
REHEARSED_DRIVER_SHA = None
for fn in RECEIPTS:
    v = (json.load(open(os.path.join(RCPT, fn))).get("device_sha256") or {}).get("chain_v4_monthly.sh")
    if fn.endswith("NEW.json") or fn.startswith("R3stub"):
        REHEARSED_DRIVER_SHA = v
drv_text = None
for rev in ("HEAD~2", "HEAD~3", "HEAD~4", "HEAD~5", "HEAD"):
    r = subprocess.run(["git", "-C", REPO, "show",
                        f"{rev}:multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/chain_v4_monthly.sh"],
                       capture_output=True)
    if r.returncode == 0 and hashlib.sha256(r.stdout).hexdigest() == REHEARSED_DRIVER_SHA:
        drv_text = r.stdout.decode("utf-8", "replace")
        break
check("★ C0 the DRIVER the rehearsal ran is recovered from git by SHA (not by revision guess): the extracted preflight below is "
      "the rehearsal's own bytes, not today's",
      drv_text is not None, {"wanted": (REHEARSED_DRIVER_SHA or "")[:16]})

PRE = extract_preflight(drv_text) if drv_text else None
check("C1 its preflight block is locatable between its own heredoc delimiters and is non-trivial",
      PRE is not None and len(PRE) > 2000 and "approved_export_baseline" in PRE, None if PRE is None else len(PRE))


def run_preflight(sb, contract_path):
    shutil.copy(contract_path, os.path.join(sb["D"], "ELIGIBILITY_CONTRACT.json"))
    out = os.path.join(sb["R"], "v4_gates", "preflight.json")
    if os.path.exists(out):
        os.remove(out)
    p = subprocess.run([sys.executable, "-B", sb["prog"], out], capture_output=True, text=True, env=sb["env"], cwd=sb["dir"])
    try:
        return p, json.load(open(out))
    except Exception:                                   # noqa: BLE001
        return p, None


sb = None
if PRE:
    d = tempfile.mkdtemp(prefix="r8g02_")
    D = os.path.join(d, "dev"); R = os.path.join(d, "root")
    os.makedirs(D); os.makedirs(os.path.join(R, "v4_gates"))
    # the helper and the shared module AS THE REHEARSAL HAD THEM (receipts: v4_gate_common cc1492d3, helper eeb68b94)
    shutil.copy(os.path.join(CHAIN, "v4_gate_common.r4_cc1492d3.py"), os.path.join(D, "v4_gate_common.py"))
    shutil.copy(os.path.join(CHAIN, "v4e_export_baseline_lib.py"), os.path.join(D, "v4e_export_baseline_lib.py"))
    for f in ("builder_fea82.py", "builder_fea89.py", "base_trainer.py"):
        open(os.path.join(D, f), "w").write("# fixture\n")
    prog = os.path.join(d, "preflight_extracted.py")
    io.open(prog, "w", encoding="utf-8").write(PRE)
    env = dict(os.environ)
    env.update({"D": D, "R": R, "PY": sys.executable, "V4_DEV_FILES": "v4_gate_common.py", "V4_PF_INPUTS": "",
                "V4_MONTH": "2026-10", "V4_MONTH_ENV": os.path.join(D, "v4_gate_common.py"), "V4_ROLL_REQUIRED": "0",
                "V4_ROLL_SRC": "v4_gate_roll_paths.py", "MONTHS_ALL": "202601", "SEEDS": "42",
                "BUNDLE_GENERATION": "fixture", "HC": D, "PREV_BUNDLE": D,
                "GATE_STEP1": "v4_gate_step1.py", "GATE_STEP2": "v4_gate_step2.py",
                "BUILDER_FEA82": os.path.join(D, "builder_fea82.py"), "BUILDER_FEA89": os.path.join(D, "builder_fea89.py"),
                "BASE_TRAINER": os.path.join(D, "base_trainer.py"), "DLW_EXT": D, "F8_EXT": D})
    env.pop("PYTHONOPTIMIZE", None)
    sb = {"dir": d, "D": D, "R": R, "prog": prog, "env": env}

result = {}
if sb:
    p_r, j_r = run_preflight(sb, REHEARSED)
    p_f, j_f = run_preflight(sb, FROZEN)
    fr = set(j_r["fails"]) if j_r else None
    ff = set(j_f["fails"]) if j_f else None
    check("C2 both runs produced an honest preflight receipt (PASS=false WITH named failures); a crash writes nothing and would "
          "read like agreement",
          j_r is not None and j_f is not None and j_r.get("PASS") is False and j_f.get("PASS") is False,
          {"rehearsed_fails": len(fr or []), "frozen_fails": len(ff or []), "stderr": (p_f.stderr or "")[-160:]})
    if fr is not None and ff is not None:
        added, removed = sorted(ff - fr), sorted(fr - ff)
        result = {"rehearsed_n": len(fr), "frozen_n": len(ff), "only_frozen": added, "only_rehearsed": removed}
        check("★★★ C3 SAME DRIVER, SAME SANDBOX, ONLY THE CONTRACT SWAPPED: the two fail SETS are compared (sets, not counts). "
              "The result below is what the a071b604↔4309e1b6 difference did to PREFLIGHT's verdict — which is stage 1 of 17 "
              "and says NOTHING about the 16 stages that never ran",
              True, result)
        check("C4 and the answer is that the difference did not reach preflight's verdict — the variant entry it touches is "
              "consulted by the EXPORT stage's approval lookup, not by preflight, which checks GATE_EXPORT's own source",
              not added and not removed, {"only_frozen": added, "only_rehearsed": removed})

        # ── C5 the control WITHOUT WHICH C4 IS VACUOUS. A null difference is only informative if this comparison can detect a
        #    contract difference at all. Blank the ONE block preflight demonstrably consults (the per-month export-baseline
        #    approval) and the fail set must move. Baseline asserted green first: C2/C3 above.
        ctrl = json.load(open(FROZEN))
        ctrl["month_contract_rulings"].pop("TRN-15_export_baseline_per_month", None)
        cp = os.path.join(sb["dir"], "ctrl_contract.json")
        json.dump(ctrl, io.open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        p_c, j_c = run_preflight(sb, cp)
        fc = set(j_c["fails"]) if j_c else None
        moved = sorted((fc - ff) | (ff - fc)) if fc is not None else None
        check("★★★ C5 RED-CAPABILITY CONTROL for C4 (baseline asserted green in C2/C3): with the per-month export-baseline "
              "approval block REMOVED from the same contract, the same comparison DOES move the fail set — so C4's null is a "
              "measurement, not a comparison that cannot see anything",
              fc is not None and bool(moved), {"moved": [m[:120] for m in (moved or [])][:3], "n_moved": len(moved or [])})
        result["control_moved"] = moved
        run_preflight(sb, FROZEN)                       # leave the sandbox on the frozen contract

print(f"\nREHEARSAL_CONTRACT_IDENTITY VERDICT={'PASS' if not FAILS else 'FAILURES'} checks={N[0]} failed={len(FAILS)} "
      f"{FAILS if FAILS else ''}".strip(), flush=True)
sys.exit(0 if not FAILS else 3)
