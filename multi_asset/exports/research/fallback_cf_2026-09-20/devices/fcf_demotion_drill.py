#!/usr/bin/env python3
"""fcf_demotion_drill.py — EXERCISE the demotion path instead of asserting it is easy (lead's closing request).

THE CLAIM BEING TESTED: "if the reviewer rules A1 binds, pulling F4b' is ONE LINE and no other number moves."
A claim that a change is cheap is itself a claim, and the cheap way to believe it is to never try it. So this device
actually rebuilds the tables with the arm removed and compares, rather than reasoning about independence.

═══ 2026-09-21 REPAIR — round-7 independent review, finding FB-04 ═══════════════════════════════════════════════════
The previous step 4 rebuilt a no-arm table and then ran `fcf_doc_check --without-arm F4bp` against the **SHIPPED**
table, whose hardcoded receipt path still contained the arm. Pointing the checker at a table that genuinely lacked the
arm raised `KeyError: 'F4bp'`. So the drill's own headline — "the remaining prose still verifies with the arm gone" —
was a statement about a path that had never executed. Independently reproduced before the repair:
    frozen device, frozen input, full          FCF_DOC_CHECK VERDICT=PASS checked=329 mismatching=0            exit 0
    frozen device, frozen input, --without-arm FCF_DOC_CHECK VERDICT=PASS checked=286 ... skipped: 43          exit 0
    frozen device, ARM ACTUALLY REMOVED        KeyError: 'F4bp'                                                exit 1

WHAT IT DOES NOW:
  1. rebuilds the main tables from the PRIMARY frozen config only (no F4b' extra config) -> a genuine "F4b' pulled" artefact;
  2. compares it against the shipped tables cell by cell, over EVERY arm except F4b' and EVERY cell except the two that exist only
     to describe F4b';
  3. REFUSES unless every one of those numbers is BITWISE unchanged. If anything moves, "one line" is false and the doc needs a
     rewrite, not an edit.
  4. runs the doc check AGAINST THE PULLED TABLE — the drill it claims to be running — and asserts, as SETS and not as
     counts, that (full checked) − (pulled checked) == (pulled skipped), with a non-zero number skipped;
  5. positive control on step 4: the SAME pulled table WITHOUT the flag must fail loudly, so a step-4 green cannot be
     produced by the checker silently falling back to the full input;
  6. the renderer is a consumer too: the pulled table must render zero rows of the arm, the shipped table must render
     every row of it carrying the marker taken from FCF_ARM_STATUS, and a table containing an arm with NO declared
     status must make the renderer refuse.
Comparison is on the JSON-serialised value, so a change of type or of precision counts as a change.

usage: fcf_demotion_drill.py <out.json>
"""
import hashlib, json, os, re, subprocess, sys, tempfile, time

OUT = "/workspace/fallback_cf_2026-09-20"
PY = "/workspace/venv/bin/python"
SHIPPED = f"{OUT}/receipts/FCF_TABLES.json"
RISK = f"{OUT}/receipts/FCF_RISK_WEIGHTS.json"
STATUS = f"{OUT}/receipts/FCF_ARM_STATUS_2026-09-21.json"
DRILL = f"{OUT}/work/FCF_TABLES_without_F4bp.json"
ARM = "F4bp"
F4BP_ONLY_CELLS = set()          # cells that exist only because of F4b' — none; the arm adds rows, not cells


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def walk(o, pre=""):
    """flatten to {json-path: scalar}"""
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, f"{pre}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{pre}[{i}]")
    else:
        yield pre, o


def doc_check(tmp, tag, tables, without=None):
    emit = os.path.join(tmp, f"emit_{tag}.json")
    cmd = [PY, "-B", f"{OUT}/devices/fcf_doc_check.py", "--tables", tables, "--status", STATUS, "--emit", emit]
    if without: cmd += ["--without-arm", without]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=OUT)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    return {"returncode": r.returncode, "verdict_line": last,
            "emit": json.load(open(emit)) if os.path.exists(emit) else None,
            "stderr_tail": (r.stderr.strip().splitlines() or [""])[-1]}


def render(tmp, tag, tables, status=STATUS):
    out = os.path.join(tmp, f"render_{tag}.md")
    r = subprocess.run([PY, "-B", f"{OUT}/devices/fcf_render.py", tables, RISK, status, out],
                       capture_output=True, text=True, cwd=OUT)
    txt = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    last = (r.stdout.strip().splitlines() or [""])[-1]
    body = txt.split("### A ·", 1)[-1]
    rows = {}
    for line in body.splitlines():
        if not line.startswith("| "): continue
        tok = line.split("|")[1].strip().split(" ")[0]
        rows.setdefault(tok, []).append(line)
    return {"returncode": r.returncode, "verdict_line": last, "rows": rows, "text": txt}


def main():
    OUTP = sys.argv[1]
    rec = {"device": "fcf_demotion_drill.py", "self_sha256": sha(os.path.abspath(__file__)),
           "claim_under_test": "pulling F4b' is a one-line change and no other number moves",
           "repair": "round-7 review FB-04; written after the reviewer showed step 4 had never run against a no-arm input",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
    FAILS = []

    def step(n, ok, d=None):
        rec["steps"].append(dict(step=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, ensure_ascii=False, default=str)[:400] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    # 1 · rebuild with the arm pulled
    r = subprocess.run([PY, "-B", f"{OUT}/devices/fcf_tables.py",
                        f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json", DRILL],
                       capture_output=True, text=True, cwd=OUT)
    step("1.rebuild_tables_with_the_arm_pulled", r.returncode == 0, dict(returncode=r.returncode, tail=r.stdout.strip().splitlines()[-1:] or r.stderr[-200:]))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(OUTP, "w"), indent=1); sys.exit(3)

    A = json.load(open(SHIPPED)); B = json.load(open(DRILL))
    step("2.the_pulled_build_really_has_no_F4bp", ARM not in B.get("arms", {}) and ARM not in B.get("paired_vs_F0", {}),
         dict(arms_in_pulled=sorted(B.get("arms", {})), arms_in_shipped=sorted(A.get("arms", {}))))

    # 3 · every number that is not about F4b' must be bitwise unchanged
    def strip(doc):
        d = json.loads(json.dumps(doc))
        d.get("arms", {}).pop(ARM, None); d.get("paired_vs_F0", {}).pop(ARM, None)
        # keys that exist ONLY to describe this arm are removals, not moves. The drill originally missed the §5 block and
        # correctly reported a difference — that is the drill working, so the fix is here rather than in the tolerance.
        for k in [k for k in d.get("prereg_s5_falsification", {}) if ARM in k]:
            d["prereg_s5_falsification"].pop(k)
        for k in ("utc", "self_sha256", "run_config", "bt_tables_sha256"): d.pop(k, None)
        for a in d.get("arms", {}).values(): a.pop("path_npz_sha256", None)
        return d
    fa = dict(walk(strip(A))); fb = dict(walk(strip(B)))
    only_a = sorted(set(fa) - set(fb)); only_b = sorted(set(fb) - set(fa))
    moved = sorted(k for k in set(fa) & set(fb) if json.dumps(fa[k], sort_keys=True) != json.dumps(fb[k], sort_keys=True))
    step("3.no_other_number_moves_when_the_arm_is_pulled", not moved and not only_a and not only_b,
         dict(n_compared=len(set(fa) & set(fb)), n_moved=len(moved), moved=moved[:8],
              only_in_shipped=only_a[:8], only_in_pulled=only_b[:8]))

    with tempfile.TemporaryDirectory() as tmp:
        # 4 · the doc check verifies against the PULLED table, and the populations balance AS SETS
        full = doc_check(tmp, "full", SHIPPED)
        pulled = doc_check(tmp, "pulled", DRILL, without=ARM)
        fe, pe = full["emit"] or {}, pulled["emit"] or {}
        set_full = set(fe.get("checked_labels", [])); set_ck = set(pe.get("checked_labels", []))
        set_sk = set(pe.get("skipped_labels", []))
        # A "passes with the arm excluded" step is worthless if nothing was actually excluded — that is how this step read
        # the first time it ran (checked=284 either way, because --without-arm had silently not been wired), and the second
        # time it ran (checked=286 either way, because the table still had the arm). So: non-zero skip, AND the three
        # populations must close AS SETS, not as counts.
        step("4.doc_check_passes_against_the_PULLED_table_and_the_populations_close_as_sets",
             full["returncode"] == 0 and pulled["returncode"] == 0
             and "VERDICT=PASS" in full["verdict_line"] and "VERDICT=PASS" in pulled["verdict_line"]
             and len(set_sk) > 0 and (set_full - set_ck) == set_sk and not (set_ck - set_full),
             dict(full_verdict_line=full["verdict_line"], pulled_verdict_line=pulled["verdict_line"],
                  tables_used_by_the_pulled_run=pe.get("tables"), n_checked_full=len(set_full),
                  n_checked_pulled=len(set_ck), n_skipped=len(set_sk),
                  set_identity="(full checked) − (pulled checked) == (pulled skipped)",
                  set_identity_holds=(set_full - set_ck) == set_sk,
                  leaked_into_pulled_only=sorted(set_ck - set_full)[:5],
                  example_skipped=sorted(set_sk)[:3]))

        # 5 · positive control: the same pulled table WITHOUT the flag must fail loudly
        nc = doc_check(tmp, "pulled_noflag", DRILL)
        step("5.positive_control_the_pulled_table_without_the_flag_fails_loudly",
             nc["returncode"] != 0 and f"'{ARM}'" in (nc["stderr_tail"] or ""),
             dict(returncode=nc["returncode"], stderr_tail=nc["stderr_tail"],
                  why=("if this were green, step 4's green could have come from the checker silently reading the shipped "
                       "table instead of the pulled one")))

        # 6 · the renderer is a consumer of the status, in both directions
        st = json.load(open(STATUS))
        mark = st["arms"][ARM]["label_short"]
        r_ship = render(tmp, "shipped", SHIPPED)
        r_pull = render(tmp, "pulled", DRILL)
        ship_rows = r_ship["rows"].get(ARM, [])
        step("6a.renderer_marks_every_row_of_the_demoted_arm_from_the_status_receipt",
             r_ship["returncode"] == 0 and len(ship_rows) > 0 and all(mark in l for l in ship_rows),
             dict(verdict_line=r_ship["verdict_line"], n_rows=len(ship_rows), marker=mark,
                  unmarked=[l[:80] for l in ship_rows if mark not in l][:3],
                  before_the_repair="32 rows of F4bp with no label at all"))
        step("6b.renderer_emits_no_row_of_a_pulled_arm",
             r_pull["returncode"] == 0 and not r_pull["rows"].get(ARM),
             dict(verdict_line=r_pull["verdict_line"], n_rows=len(r_pull["rows"].get(ARM, []))))
        # 6c · RED capability: an arm with no declared status must stop the renderer, so a NEW arm cannot be published
        #      before somebody says what it is. Baseline for this control is 6a, asserted green above.
        undecl = os.path.join(tmp, "tables_with_an_undeclared_arm.json")
        d2 = json.loads(json.dumps(A)); d2["arms"]["F9zz"] = json.loads(json.dumps(A["arms"]["F0"]))
        d2["paired_vs_F0"]["F9zz"] = json.loads(json.dumps(A["paired_vs_F0"]["F1"]))
        json.dump(d2, open(undecl, "w"))
        r_bad = render(tmp, "undeclared", undecl)
        step("6c.RED_renderer_refuses_an_arm_with_no_declared_status",
             r_bad["returncode"] == 3 and "arm_with_no_declared_status" in r_bad["verdict_line"],
             dict(returncode=r_bad["returncode"], verdict_line=r_bad["verdict_line"],
                  baseline_asserted_green_first="6a"))

    rec["VERDICT"] = "PASS" if not FAILS else "REFUSED"; rec["failed"] = FAILS
    rec["conclusion"] = ("the demotion is genuinely a one-line change: rebuilding without the arm leaves every other number bitwise "
                         "identical, the remaining prose verifies AGAINST THE PULLED TABLE with a balanced skip population, and "
                         "the renderer both marks the arm and refuses an undeclared one" if not FAILS else
                         "the demotion is NOT a one-line change; the doc would need a rewrite")
    json.dump(rec, open(OUTP + ".tmp", "w"), ensure_ascii=False, indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_DEMOTION_DRILL VERDICT={rec['VERDICT']} steps={len(rec['steps'])} failed={len(FAILS)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
