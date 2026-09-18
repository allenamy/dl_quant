#!/usr/bin/env python3
"""Behavioural tests for R12-C5 (independent review round 12, closing 「十月特别说明」).

Three defects, all of which let a month run with inputs nobody approved:
  (a) `v4_month_2026-10.env.template` declared no MEMBER_MASK / v2 builders / UMASK_NPZ / GATE_LIVENESS / CONTROLS_REF_*, so an October
      run would build members with the v1 builders and NO liveness mask — and the MEMBER_LIVENESS gate would then fail the very month it
      governs. Nothing refused that shape; it simply produced the wrong members.
  (b) the controls stage compares this month's build against reference builds the month contract names, and nothing bound those references
      to an approved identity: a month could aim the comparison anywhere and still be told PASS.
  (c) `fp2_decision.py`'s FORMAL profile is pre-registered for ONE month (its frozen window, anchor counts and bound gate identities are
      September's), but the month was not a condition: an October run failed later, on a missing September artefact, as UNAVAILABLE.

Everything here is local and offline. The preflight cases run the real driver with V4_STAGES=preflight against a scratch root, which writes
a receipt and exits; no stage that could launch training is reached. The decision cases run the real device, which refuses before it opens
any artefact. Nothing is written outside the scratch directory.
Run: python3 tests_chain_month_contract_r12c5.py   (exit 0 iff ALL PASS)"""
import hashlib, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
TMP = tempfile.mkdtemp(prefix="chain_r12c5_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1; print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if detail and not cond else ""))
    if not cond: FAILS.append(name)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


STUB = os.path.join(TMP, "local_stub.npz"); open(STUB, "wb").write(b"local stub: not any approved artefact")


def month_env(name, month, drop=(), extra=""):
    """a scratch month contract derived from the September FP2 one: R/PY point into the scratch tree, V4_MONTH is rewritten,
    `drop` removes keys by name, `extra` is appended. Every path stays inside TMP, so nothing real can be read or written."""
    root = os.path.join(TMP, name, "root"); os.makedirs(os.path.join(root, "v4_gates"), exist_ok=True)
    os.makedirs(os.path.join(root, "masks"), exist_ok=True)
    open(os.path.join(root, "masks", "member_mask_tradable_W24H_cachegrid.npz"), "wb").write(b"stub")
    t = open(f"{HERE}/v4_month_2026-09_fp2.env").read()
    t = re.sub(r"(?m)^R=.*$", f"R={root}", t); t = re.sub(r"(?m)^PY=.*$", f"PY={PY}", t); t = re.sub(r"(?m)^V4_MONTH=.*$", f"V4_MONTH={month}", t)
    # the real contract points at pod2 paths; the driver refuses a declared-but-absent file before preflight even runs, which would make every
    # case below pass vacuously. Every such key is rewritten to a LOCAL stub whose sha is deliberately NOT any approved value.
    for k in ("UMASK_NPZ", "MEMBER_MASK", "CONTROLS_REF_KING_FEA", "CONTROLS_REF_KING_META", "CONTROLS_REF_DL_TARGETS"):
        t = re.sub(rf"(?m)^{k}=.*$", f"{k}={STUB}", t)
    for k in drop: t = re.sub(rf"(?m)^{k}=.*\n", "", t)
    p = os.path.join(TMP, name, "month.env"); open(p, "w").write(t.rstrip("\n") + "\n" + extra)
    return p, root


def preflight_fails(name, month, drop=(), extra=""):
    """run the real driver's preflight stage and return its receipt's `fails` list (a scratch root fails for many reasons; these tests
    assert that ONE NAMED failure is present or absent, which is what discriminates)."""
    envf, root = month_env(name, month, drop, extra)
    subprocess.run(["bash", f"{HERE}/chain_v4_monthly.sh", envf], capture_output=True, text=True, cwd=HERE,
                   env=dict(os.environ, PY=PY, V4_STAGES="preflight", L="/dev/null"))
    pf = os.path.join(root, "v4_gates", "preflight.json")
    if not os.path.exists(pf):                                              # no receipt ⇒ the driver died before preflight; every assertion below
        return ["<NO PREFLIGHT RECEIPT: the driver stopped earlier>"]       # would then pass vacuously, so the caller asserts the receipt exists
    return json.load(open(pf)).get("fails") or []


print("[1] R12-C5(a): the October template now declares every key the mask path needs")
tpl = open(f"{HERE}/v4_month_2026-10.env.template").read()
kv = dict(re.findall(r"(?m)^([A-Z0-9_]+)=(.*)$", tpl))
for k in ("MEMBER_MASK", "UMASK_NPZ", "GATE_LIVENESS", "CONTROLS_REF_KING_FEA", "CONTROLS_REF_KING_META", "CONTROLS_REF_DL_TARGETS"):
    check(f"October template declares {k}", k in kv, sorted(kv))
check("the October template selects the v2 builders (the v1 defaults ignore MEMBER_MASK_NPZ entirely)",
      kv.get("BUILDER_TARGETS") == "pod_dlw_targets_raw_v2.py" and kv.get("BUILDER_KING_FEA") == "pod_fea_ext_clamp_v2.py",
      (kv.get("BUILDER_TARGETS"), kv.get("BUILDER_KING_FEA")))
check("every October artefact that does not exist yet is still a TODO_ value (the template cannot be run by accident)",
      all("TODO_" in kv[k] for k in ("MEMBER_MASK", "UMASK_NPZ", "CONTROLS_REF_KING_FEA", "CONTROLS_REF_KING_META", "CONTROLS_REF_DL_TARGETS")),
      {k: kv.get(k) for k in ("MEMBER_MASK", "UMASK_NPZ")})

print("\n[2] R12-C5(a): preflight REFUSES a post-September month that omits the mask keys; September is unchanged")
f_sep = preflight_fails("sep_control", "2026-09")
check("the preflight receipt is actually written (otherwise every assertion in this section would pass vacuously)",
      not any("NO PREFLIGHT RECEIPT" in x for x in f_sep), f_sep[:2])
check("GREEN BASELINE: the September contract raises NEITHER mask complaint (the new rule does not touch it)",
      not [x for x in f_sep if "does not declare MEMBER_MASK" in x or "does not declare UMASK_NPZ" in x], [x for x in f_sep if "declare" in x][:3])
f_oct = preflight_fails("oct_nomask", "2026-10", drop=("MEMBER_MASK", "UMASK_NPZ"))
check("a 2026-10 contract without MEMBER_MASK is refused by name", any("does not declare MEMBER_MASK" in x for x in f_oct), [x for x in f_oct if "declare" in x][:3])
check("a 2026-10 contract without UMASK_NPZ is refused by name", any("does not declare UMASK_NPZ" in x for x in f_oct), [x for x in f_oct if "declare" in x][:3])
f_oct2 = preflight_fails("oct_withmask", "2026-10")
check("MUTATION CONTROL: the same 2026-10 month WITH both keys raises neither complaint (the rule reads the keys, not the month alone)",
      not [x for x in f_oct2 if "does not declare MEMBER_MASK" in x or "does not declare UMASK_NPZ" in x], [x for x in f_oct2 if "declare" in x][:3])

print("\n[3] R12-C5(b): the controls references are a per-month approval object bound by sha")
con = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
appr = (((con.get("month_contract_rulings") or {}).get("CONTROLS_REF_identity") or {}).get("approved_controls_refs") or {})
check("the contract carries an approved CONTROLS_REF entry for 2026-09 with all three references", isinstance(appr.get("2026-09"), dict)
      and all(k in appr["2026-09"] for k in ("CONTROLS_REF_KING_FEA", "CONTROLS_REF_KING_META", "CONTROLS_REF_DL_TARGETS")), list(appr))
check("2026-10 is deliberately unapproved (null), so October refuses instead of comparing against anything", appr.get("2026-10") is None, appr.get("2026-10"))
# provenance control: the approved values are the ones two committed FP2 controls receipts recorded, not numbers invented here
rec_dir = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "docs", "fixprogram_2026-09-13", "FP2_receipts"))
got = []
for fn in ("regate2_CONTROLS.json", "regate_f0x_CONTROLS.json"):
    p = os.path.join(rec_dir, fn)
    if os.path.exists(p): got.append(json.load(open(p)).get("inputs_sha256") or {})
want = appr.get("2026-09") or {}
check("PROVENANCE: the three approved shas equal `sept_king_fea / sept_king_meta / sept_dl_targets` in BOTH committed FP2 controls receipts",
      len(got) == 2 and all(g.get(a) == (want.get(b) or {}).get("sha256") for g in got
                            for a, b in (("sept_king_fea", "CONTROLS_REF_KING_FEA"), ("sept_king_meta", "CONTROLS_REF_KING_META"), ("sept_dl_targets", "CONTROLS_REF_DL_TARGETS"))),
      (len(got), [(g.get("sept_king_fea") or "")[:12] for g in got], ((want.get("CONTROLS_REF_KING_FEA") or {}).get("sha256") or "")[:12]))
f_bad = preflight_fails("sep_badref", "2026-09")                          # the harness points the three references at the local stub
check("the preflight receipt is written for the bad-reference case too", not any("NO PREFLIGHT RECEIPT" in x for x in f_bad), f_bad[:2])
check("a September run pointed at a reference whose sha is NOT the approved one is refused by name",
      any("CONTROLS_REF_KING_FEA sha" in x and "!= approved" in x for x in f_bad), [x for x in f_bad if "CONTROLS_REF" in x][:2])
f_unl = preflight_fails("oct_ref_unlisted", "2026-10")
check("a month with NO approved entry (2026-10) is refused by name, not compared against whatever is on disk",
      any("no approved CONTROLS_REF for month 2026-10" in x for x in f_unl), [x for x in f_unl if "CONTROLS_REF" in x][:2])

print("\n[4] R12-C5(c): the decision device refuses a month its frozen profile does not cover")


def decide(month, extra_env=None):
    d = os.path.join(TMP, f"dec_{month}"); os.makedirs(os.path.join(d, "v4_gates"), exist_ok=True)
    oj = os.path.join(d, "DECISION.json")
    env = dict(os.environ, R=d, D=HERE, PROFILE="formal", OUT_JSON=oj, OUT_MD=os.path.join(d, "DECISION.md"))
    env.pop("V4_MONTH", None)
    if month: env["V4_MONTH"] = month
    env.update(extra_env or {})
    r = subprocess.run([PY, f"{HERE}/fp2_decision.py"], capture_output=True, text=True, env=env)
    j = json.load(open(oj)) if os.path.exists(oj) else {}
    return r.returncode, j, (r.stdout + r.stderr)


rc, j, out = decide("2026-10")
check("a 2026-10 run is REFUSED_PROFILE_MONTH rc 3 — named, not a missing-September-artefact UNAVAILABLE",
      rc == 3 and j.get("RECOMMENDATION") == "REFUSED_PROFILE_MONTH" and j.get("PASS") is False, (rc, j.get("RECOMMENDATION"), out[-150:]))
check("the receipt says which month the profile covers, which month ran, and what a new month needs",
      (j.get("profile_month") or {}).get("covers") == "2026-09" and (j.get("profile_month") or {}).get("run_month") == "2026-10"
      and "pre-registered decision profile" in ((j.get("profile_month") or {}).get("a_new_month_needs") or ""), j.get("profile_month"))
rc9, j9, out9 = decide("2026-09")
check("GREEN BASELINE: a 2026-09 run is NOT refused for the month (it proceeds and fails on the scratch root's missing artefacts instead)",
      j9.get("RECOMMENDATION") != "REFUSED_PROFILE_MONTH", (rc9, j9.get("RECOMMENDATION"), (j9.get("reasons") or [None])[0]))
rcn, jn, outn = decide(None)
check("no V4_MONTH and no preflight receipt ⇒ the month check cannot fire, and the device fails for its real reason instead of guessing",
      jn.get("RECOMMENDATION") != "REFUSED_PROFILE_MONTH", (rcn, jn.get("RECOMMENDATION")))
d = os.path.join(TMP, "dec_pf"); os.makedirs(os.path.join(d, "v4_gates"), exist_ok=True)
json.dump({"gate": "PREFLIGHT", "PASS": True, "root": d, "month": "2026-10"}, open(os.path.join(d, "v4_gates", "preflight.json"), "w"))
env = dict(os.environ, R=d, D=HERE, PROFILE="formal", OUT_JSON=os.path.join(d, "DECISION.json"), OUT_MD=os.path.join(d, "DECISION.md"))
env.pop("V4_MONTH", None)
r = subprocess.run([PY, f"{HERE}/fp2_decision.py"], capture_output=True, text=True, env=env)
jp = json.load(open(os.path.join(d, "DECISION.json"))) if os.path.exists(os.path.join(d, "DECISION.json")) else {}
check("with no V4_MONTH but a preflight receipt saying 2026-10, the month is taken from the receipt and still refused by name",
      r.returncode == 3 and jp.get("RECOMMENDATION") == "REFUSED_PROFILE_MONTH", (r.returncode, jp.get("RECOMMENDATION")))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
