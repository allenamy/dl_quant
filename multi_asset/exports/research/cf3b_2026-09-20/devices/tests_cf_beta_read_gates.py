#!/usr/bin/env python3
"""tests_cf_beta_read_gates.py — STY-05: the CF3-B reader's hard gates must control the WRITE, not just the record.

THE DEFECT UNDER TEST (round-7 independent review, notes/style.md STY-05). The frozen reader computed B5, the upstream gate
verdicts and the §5.4 unattributed bound, recorded all three, and then wrote every arm number anyway. The reviewer's own table:

  | case                                              | real gate        | exit | FINAL       | still wrote all arm numbers |
  | baseline                                          | B5 PASS, up PASS |    0 | UNDECIDED   | yes                         |
  | one published B5 cell mutated                     | B5 false         |    0 | UNDECIDED   | yes  <- should have REFUSED |
  | NONE's upstream gate marked REFUSED               | upstream REFUSED |    0 | UNDECIDED   | yes  <- should have REFUSED |
  | §5.1-supporting config whose bound is unreadable  | bound_ok=false   |    0 | **5.1**     | yes  <- should be UNDECIDED |

PREREG §3: "B1–B5 任一不过 ⇒ REFUSED, 不出臂数字". PREREG §5.4: an unreadable bound forces UNDECIDED. The last row is the
sharpest: a gate that was computed and recorded let an UNREADABLE common term be published as a SUPPORTED reading.

THE ORDER MATTERS. Every red probe below re-asserts the same green baseline first, in the same run — a red-capability probe on
an already-red baseline is vacuous. T0 is that baseline and it is asserted before anything is mutated.

Run:  python3 tests_cf_beta_read_gates.py      exit 0 iff every check passes
"""
import copy, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
READER = os.path.join(HERE, "cf_beta_read.py")
ARMS = ["BASE", "NONE", "noFUND", "noFUND_GF"]
PERIODS = ("HIST", "2026", "FULL_RECIPE")
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok:
        FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def period(price, common, resid, bound, beta=-0.03, n=5000):
    return {"n_anchors": n, "price": price, "style_common_risk_and_style": common,
            "style_residual_selection": resid, "unattributed_no_beta": 0.0,
            "unattributed_bound_abs": bound, "gross_share_without_beta": 0.00014,
            "book_ex_ante_net_beta_mean": beta}


def arm(dc, dr, pc, pr, bound=0.01):
    """An AT_BETA.json of the shape the reader reads. `bound` drives the §5.4 rule (bound <= |dc|/2 is readable)."""
    return {"ci_2026_vs_HIST": {"price": {"point": dc + dr, "p": 0.01},
                                "style_common": {"point": dc, "p": pc},
                                "style_residual": {"point": dr, "p": pr}},
            "per_period": {p: period(1.0 + i, 0.5, 0.5, bound) for i, p in enumerate(PERIODS)}}


def make_fixture(*, s_none_like_base=False, bound_bad=False, b5_mutate=False,
                 none_gate="PASS", unread_control_zero=False, drop=None):
    """One receipts directory. Defaults give a GREEN baseline whose §5.1/§5.2 both fail => UNDECIDED (§5.3)."""
    d = tempfile.mkdtemp(prefix="sty05_")
    R = os.path.join(d, "receipts"); os.makedirs(os.path.join(R, "unread"))
    # BASE: s = 1.49 / (1.49 + 1.75) = 46.0%.  NONE: 2.88 / (2.88 + 1.55) = 65.0%  => gap 19pp, §5.1 fails.
    A = {"BASE": arm(1.4903, 1.7500, 0.042, 0.009),
         "NONE": arm(2.8767, 1.5547, 0.0002, 0.031),
         "noFUND": arm(0.2000, 0.8000, 0.18, 0.72),
         "noFUND_GF": arm(0.9000, 0.1000, 0.20, 0.80)}
    if s_none_like_base:
        A["NONE"] = arm(1.4903, 1.7500, 0.0002, 0.031)       # s_NONE == s_BASE and p<0.05 => §5.1 SUPPORTED
    if bound_bad:
        for a in A:
            for p in PERIODS:
                A[a]["per_period"][p]["unattributed_bound_abs"] = 99.0     # >> |d_common|/2 for every arm
    for a in ARMS:
        os.makedirs(os.path.join(R, a))
        json.dump(A[a], open(os.path.join(R, a, "AT_BETA.json"), "w"))
        json.dump({"verdict": (none_gate if a == "NONE" else "PASS"),
                   "failed": ([] if (a != "NONE" or none_gate == "PASS") else ["B1_panel_identity"])},
                  open(os.path.join(R, f"CF_BETA_{a}.json"), "w"))
    json.dump({"mutation_ext_rows": {"n_numbers_changed": 0},
               "control_one_in_run_row": {"n_numbers_changed": (0 if unread_control_zero else 7)}},
              open(os.path.join(R, "unread", "CF_BETA_UNREAD_TEST.json"), "w"))
    cert = copy.deepcopy(A["BASE"])
    if b5_mutate:
        cert["per_period"]["2026"]["price"] += 1e-9          # one published cell, one bit
    cp = os.path.join(d, "CERT_AT_BETA.json")
    json.dump(cert, open(cp, "w"))
    if drop:
        os.remove(os.path.join(R, drop))
    return {"dir": d, "R": R, "cert": cp,
            "outj": os.path.join(d, "out.json"), "outm": os.path.join(d, "out.md")}


def run(fx, reader=None):
    p = subprocess.run([sys.executable, "-B", reader or READER, fx["R"], fx["outj"], fx["outm"], fx["cert"]],
                       capture_output=True, text=True)
    j = json.load(open(fx["outj"])) if os.path.exists(fx["outj"]) else None
    md = open(fx["outm"]).read() if os.path.exists(fx["outm"]) else None
    return p.returncode, j, md, (p.stdout + p.stderr)


def wrote_arm_numbers(j, md):
    """'不出臂数字' measured on BOTH surfaces: the JSON must carry no `arms` block, and the markdown must not render the
    per-arm table. Checking only one of the two would leave the other free to publish."""
    if j is None:
        return None
    return bool(j.get("arms")) or (md is not None and "逐臂 · 逐时段" in md)


# ══════════════════════════════════════════════════════════ T0 — THE GREEN BASELINE
rc0, j0, md0, log0 = run(make_fixture())
check("★★★ T0 GREEN BASELINE: all hard gates pass, the bound is readable ⇒ exit 0, the arm numbers ARE written, FINAL is the "
      "pre-registered §5.3 UNDECIDED. Every red probe below re-states this baseline, because a red-capability check on an "
      "already-red baseline is vacuous",
      rc0 == 0 and j0 is not None and wrote_arm_numbers(j0, md0) and j0["hard_gates"]["n_failed"] == 0
      and j0["verdicts"]["FINAL"].startswith("UNDECIDED (PREREG 5.3)"),
      {"rc": rc0, "FINAL": (j0 or {}).get("verdicts", {}).get("FINAL"), "log": log0.strip()[:150]})

# ══════════════════════════════════════════════════════════ T1 — B5 RED MUST REFUSE AND MUST NOT PUBLISH
rc1, j1, md1, log1 = run(make_fixture(b5_mutate=True))
check("★★★ T1 one published B5 cell mutated ⇒ REFUSED, exit 3, and NO arm numbers on either surface. The reviewer measured the "
      "frozen reader giving exit 0 with all numbers written here",
      rc1 == 3 and j1 is not None and j1.get("REFUSED") is True and wrote_arm_numbers(j1, md1) is False
      and any("B5 control is NOT bit-identical" in r for r in j1["refused_reasons"]),
      {"rc": rc1, "reasons": (j1 or {}).get("refused_reasons"), "arms_written": wrote_arm_numbers(j1, md1)})

# ══════════════════════════════════════════════════════════ T2 — UPSTREAM REFUSED MUST REFUSE
rc2, j2, md2, log2 = run(make_fixture(none_gate="REFUSED"))
check("★★★ T2 NONE's upstream gate is REFUSED ⇒ REFUSED, exit 3, no arm numbers. The frozen reader recorded this verdict and "
      "then wrote every arm's numbers, which is the whole of STY-05",
      rc2 == 3 and j2 is not None and j2.get("REFUSED") is True and wrote_arm_numbers(j2, md2) is False
      and any("upstream gate for arm NONE" in r for r in j2["refused_reasons"]),
      {"rc": rc2, "reasons": (j2 or {}).get("refused_reasons")})

# ══════════════════════════════════════════════════════════ T3 — AN UNREADABLE BOUND CAN NEVER BECOME A SUPPORTED READING
rc3g, j3g, md3g, _ = run(make_fixture(s_none_like_base=True))
rc3, j3, md3, log3 = run(make_fixture(s_none_like_base=True, bound_bad=True))
check("★★★ T3 the sharpest case: a configuration in which §5.1 IS supported, run twice — with a readable bound the verdict is "
      "5.1 (green control, same probe), and with the bound unreadable it is forced to UNDECIDED (§5.4) instead of 5.1. The "
      "receipt also records what it WOULD have been, so the downgrade is visible rather than silent",
      rc3g == 0 and (j3g or {})["verdicts"]["FINAL"] == "5.1"
      and rc3 == 0 and j3 is not None and j3["verdicts"]["FINAL"].startswith("UNDECIDED (PREREG 5.4")
      and j3["verdicts"]["FINAL_priority"]["would_have_been_without_the_bound_rule"] == "5.1"
      and j3["verdicts"]["FINAL_priority"]["downgraded_by_5.4"] is True,
      {"readable_bound_FINAL": (j3g or {}).get("verdicts", {}).get("FINAL"),
       "unreadable_bound_FINAL": (j3 or {}).get("verdicts", {}).get("FINAL")})
check("T3b and the §5.4 downgrade is NOT a refusal: the numbers are still written (PREREG §5.4 downgrades the reading, §3 "
      "blocks the numbers — the two severities must not be collapsed into one)",
      rc3 == 0 and wrote_arm_numbers(j3, md3) is True, {"rc": rc3, "arms_written": wrote_arm_numbers(j3, md3)})

# ══════════════════════════════════════════════════════════ T4 — A CONTROL THAT MOVES NOTHING IS NOT A PASSING CONTROL
rc4, j4, md4, log4 = run(make_fixture(unread_control_zero=True))
check("★★★ T4 the B-A1 unreadability test's ZERO CONTROL moves 0 numbers ⇒ REFUSED: a control that cannot move is not evidence "
      "that the probe is wired, and 'the mutation changed nothing' then means nothing (the vacuous-green family)",
      rc4 == 3 and j4 is not None and j4.get("REFUSED") is True and wrote_arm_numbers(j4, md4) is False
      and any("zero control" in r for r in j4["refused_reasons"]),
      {"rc": rc4, "reasons": (j4 or {}).get("refused_reasons")})

# ══════════════════════════════════════════════════════════ T5 — A MISSING INPUT IS A NAMED REFUSAL, NOT A TRACEBACK
rc5, j5, md5, log5 = run(make_fixture(drop="CF_BETA_noFUND.json"))
check("★★★ T5 a missing input receipt ⇒ a NAMED refusal with a receipt and exit 3, not an unhandled traceback (the frozen "
      "reader raised FileNotFoundError, which leaves no evidence of why it stopped)",
      rc5 == 3 and j5 is not None and j5.get("REFUSED") is True
      and any("input missing on disk" in r for r in j5["refused_reasons"]) and "Traceback" not in log5,
      {"rc": rc5, "reasons": (j5 or {}).get("refused_reasons"), "traceback": "Traceback" in log5})

# ══════════════════════════════════════════════════════════ T6 — the refusal is not silent
check("T6 every refusal above LEFT A RECEIPT naming which gate failed, and printed a machine-readable verdict line: a refusal "
      "that writes nothing reads exactly like a crash",
      all(j is not None and j.get("refused_reasons") for j in (j1, j2, j4, j5))
      and all("CF_BETA_READ REFUSED" in log for log in (log1, log2, log4, log5)),
      {"lines": [l.strip().splitlines()[-1][:80] for l in (log1, log2, log4, log5) if l.strip()]})

# ══════════════════════════════════════════════════════════ [OLD] THE DEFECT, MEASURED ON THE ARCHIVED PRE-FIX READER
#     The reviewer's table is reproduced here rather than quoted, on the same fixtures, so "the fix changed something" is a
#     measurement. The archived reader takes no CERT argument, so its hard-coded path is pointed at the fixture by env.
import glob
ARCHIVED = sorted(glob.glob(os.path.join(HERE, "cf_beta_read.r*_*.py")))
check("OLD0 the pre-fix reader is archived beside the fixed one (a defect measured against a file nobody kept is an assertion)",
      len(ARCHIVED) == 1, [os.path.basename(p) for p in ARCHIVED])
if ARCHIVED:
    old = ARCHIVED[0]
    src = open(old, encoding="utf-8").read()
    patched = os.path.join(tempfile.mkdtemp(prefix="sty05_old_"), "cf_beta_read_old.py")
    open(patched, "w", encoding="utf-8").write(
        src.replace('json.load(open("/workspace/attrib_2026_2026-09-20/receipts/AT_BETA.json"))',
                    'json.load(open(os.environ["CF_BETA_CERT"]))'))
    def run_old(fx):
        env = dict(os.environ); env["CF_BETA_CERT"] = fx["cert"]
        p = subprocess.run([sys.executable, "-B", patched, fx["R"], fx["outj"], fx["outm"]],
                           capture_output=True, text=True, env=env)
        j = json.load(open(fx["outj"])) if os.path.exists(fx["outj"]) else None
        md = open(fx["outm"]).read() if os.path.exists(fx["outm"]) else None
        return p.returncode, j, md, (p.stdout + p.stderr)
    o0 = run_old(make_fixture())
    o1 = run_old(make_fixture(b5_mutate=True))
    o2 = run_old(make_fixture(none_gate="REFUSED"))
    o3 = run_old(make_fixture(s_none_like_base=True, bound_bad=True))
    check("★★★ OLD1 THE DEFECT, MEASURED: on the very same fixtures the archived reader returns exit 0 with ALL arm numbers "
          "written for a mutated B5 cell AND for an upstream REFUSED — the two cases PREREG §3 says must block the numbers",
          o0[0] == 0 and o1[0] == 0 and wrote_arm_numbers(o1[1], o1[2]) is True
          and o2[0] == 0 and wrote_arm_numbers(o2[1], o2[2]) is True,
          {"baseline_rc": o0[0], "b5_red_rc": o1[0], "b5_red_wrote_numbers": wrote_arm_numbers(o1[1], o1[2]),
           "upstream_refused_rc": o2[0], "upstream_refused_wrote_numbers": wrote_arm_numbers(o2[1], o2[2])})
    check("★★★ OLD2 and on the §5.1-supporting configuration with an UNREADABLE bound the archived reader publishes FINAL=5.1 "
          "— an unreadable common term published as a supported reading, which is the worst of the four and the reason "
          "STY-05 blocks any new CF3-B verdict",
          o3[0] == 0 and (o3[1] or {}).get("verdicts", {}).get("FINAL") == "5.1",
          {"rc": o3[0], "FINAL": (o3[1] or {}).get("verdicts", {}).get("FINAL")})

line = f"CF_BETA_READ_GATES {'ALL PASS' if not FAILS else 'FAILURES'} checks={N[0]} failed={len(FAILS)} {FAILS if FAILS else ''}"
print("\n" + line.strip(), flush=True)
sys.exit(0 if not FAILS else 1)
