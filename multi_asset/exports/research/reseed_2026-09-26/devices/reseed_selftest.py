#!/usr/bin/env python3
"""Red-control self-test of reseed_leg_returns.py on SYNTHETIC producer state (temp dirs only; the real producer module is imported for
build_generation_record / _read_verified_generation / atomic_write; nothing under ~/wide_shadow is written).
Lead's required controls: position→anchor measured from snapshots; tail timestamp asserted against prev_rec; incomplete coverage ⇒
non-zero exit; seam discontinuity ⇒ stop. Plus: ambiguous step ⇒ stop; live producer lock ⇒ install refuses; changed input ⇒ install
refuses; generation re-issue is necessary (red control) and verifies; rollback restores bitwise. Baseline first.
usage: ~/wide_shadow/venv/bin/python reseed_selftest.py <scratch dir>"""
import importlib.util, json, os, random, shutil, subprocess, sys, tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "reseed_leg_returns.py")
PROD = os.path.expanduser("~/wide_shadow/shadow_loop_v3.py"); PY = sys.executable
S = os.path.abspath(sys.argv[1]); os.makedirs(S, exist_ok=True)
STEP = 14400; LEGS = ("king", "rev24", "fund"); NKEEP = 950
FAILS = []; N = [0]


def check(name, cond, extra=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)[:260]) if extra != '' else ''}")
    if not cond: FAILS.append(name)


sys.path.insert(0, os.path.dirname(PROD))
spec = importlib.util.spec_from_file_location("prod_ref", PROD); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)

R_END = 1790000000 // STEP * STEP            # replay end (synthetic)
G = R_END + 60 * STEP                         # generation anchor (the last processed anchor)
SKIP = R_END + 30 * STEP                      # the run at SKIP appends nothing ⇒ no entry for SKIP - 4h
MISSING_SNAP = R_END + 45 * STEP              # no snapshot here ⇒ a 2-append step
OUT_T = R_END + 50 * STEP                     # rev 1: outage world — runs at OUT_T+4h/+8h never happen, the run at OUT_T+12h appends
                                              # nothing (12 h gap) ⇒ entries OUT_T, OUT_T+4h, OUT_T+8h missing (the 09-26 12Z/16Z shape)


def world(tag, rep_drop_tail=0, rep_n=1200, ambiguous=False, cur_mismatch=False, lag_file=False, rep_extend=0, outage=False):
    """Build a synthetic state + snap + legs.npz. Returns dict of paths and the ground truth."""
    rnd = random.Random(7); d = tempfile.mkdtemp(prefix=f"rs_{tag}_", dir=S)
    st, snap = os.path.join(d, "state"), os.path.join(d, "state", "snap"); os.makedirs(snap)
    # replay: rep_n entries ending at R_END (then drop some from the tail for the seam case)
    E = np.array([R_END - STEP * (rep_n - 1 - i) for i in range(rep_n + rep_extend)], np.int64)   # rev 1: rep_extend anchors past R_END
    LR = np.array([[rnd.gauss(0, 10) for _ in range(3)] for _ in range(rep_n + rep_extend)])
    if rep_drop_tail: E, LR = E[:-rep_drop_tail], LR[:-rep_drop_tail]
    legs = os.path.join(d, "legs.npz"); np.savez(legs, E_ts=E, LR=LR)
    # live truth: a seeded prefix (junk) + one entry per processed anchor from R_END+4h..G-4h, except SKIP-4h
    junk = [tuple(rnd.gauss(0, 10) for _ in range(3)) for _ in range(NKEEP)]
    truth = {}
    series = list(junk)
    snaps = {}
    first_snap = R_END + STEP                    # its file already ends with... nothing assignable; assignment starts at the next step
    for t in range(first_snap, G + STEP, STEP):
        if outage and t in (OUT_T + STEP, OUT_T + 2 * STEP): continue   # no run, no snapshot
        if t > first_snap and t != SKIP and not (outage and t == OUT_T + 3 * STEP):         # the run at t appends the entry for t - 4h
            if ambiguous and t == R_END + 20 * STEP:   # the run at t appends nothing although the gap is 2 anchors (see below)
                pass
            else:
                v = tuple(rnd.gauss(0, 10) for _ in range(3)); truth[t - STEP] = v; series.append(v)
        doc = {leg: [float(x[j]) for x in series[-NKEEP:]] for j, leg in enumerate(LEGS)}
        snaps[t] = doc
    for t, doc in snaps.items():
        if t == MISSING_SNAP: continue
        if ambiguous and t == R_END + 19 * STEP: continue      # removes the snapshot before the non-appending run ⇒ 1 append across 2 anchors
        if lag_file and t == G: continue                        # the prev_rec case: the current file is the only observation at G
        os.makedirs(os.path.join(snap, str(t))); json.dump(doc, open(os.path.join(snap, str(t), "leg_returns_live.json"), "w"))
    cur = snaps[G - STEP] if lag_file else snaps[G]
    if cur_mismatch:
        cur = json.loads(json.dumps(cur)); cur["king"][-1] += 1.0
    P.atomic_write(os.path.join(st, "leg_returns_live.json"), json.dumps(cur).encode())
    for f in ("rolling.npz", "boundary_raw.npz", "members_hist.npz"): open(os.path.join(st, f), "wb").write(os.urandom(64))
    json.dump({"last_anchor": G, "prev_rec": {"anchor_ts": G}}, open(os.path.join(st, "aux.json"), "w"))
    P.atomic_json(os.path.join(st, "generation.json"), P.build_generation_record(st, G))
    rep_keep = [(int(E[i]), tuple(LR[i])) for i in range(len(E))]
    rep_end = rep_keep[-1][0]
    exp = [x for x in rep_keep if x[0] <= rep_end] + sorted((t, v) for t, v in truth.items() if t > rep_end)
    return {"d": d, "state": st, "snap": snap, "legs": legs, "truth": truth, "expected": exp[-NKEEP:], "cur": cur, "rep_end": rep_end}


def run(*args):
    p = subprocess.run([PY, "-B", DEV, *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def build(w, tag="b"):
    out = os.path.join(w["d"], f"out_{tag}")
    sh = __import__("hashlib").sha256(open(w["legs"], "rb").read()).hexdigest()
    rc, o = run("build", "--state", w["state"], "--snap", w["snap"], "--legs", w["legs"], "--legs-sha", sh, "--producer", PROD, "--out", out)
    return rc, o, out


print("[0] BASELINE: consistent synthetic world ⇒ build OK, candidate == expected, positions == true anchors")
# rev 1: the rev-0 baseline carried a 1-anchor hole (the SKIP run) BEYOND the replay end and was green — i.e. it certified a
# hole-carrying build. The baseline replay now extends 40 anchors past R_END, so the SKIP hole is covered by the replay (path A).
w = world("base", rep_extend=40); rc, o, out = build(w)
check("★★★ baseline build exit 0", rc == 0, o[-240:])
if rc == 0:
    B = json.load(open(os.path.join(out, "BUILD.json"))); cand = json.load(open(os.path.join(out, "leg_returns_live.NEW.json")))
    exp = w["expected"]
    check("★★★ candidate values == expected series (replay ≤ end, then the live truth), 950 positions", all(cand[l] == [float(v[j]) for _, v in exp] for j, l in enumerate(LEGS)) and len(cand["king"]) == NKEEP)
    check("★★★ positions_anchor_ts == the true anchors", B["positions_anchor_ts"] == [t for t, _ in exp])
    steps = B["position_to_anchor"]["steps"]
    check("★★ a 0-append step (the skipped run) and a 2-append step (the missing snapshot) were both MEASURED",
          any(s["appended"] == 0 for s in steps) and any(s["appended"] == 2 and s["anchors_elapsed"] == 2 for s in steps), [s for s in steps if s["appended"] != 1])

print("[1] RED CONTROL: position→anchor by position ('k-th from the end is k anchors back') is WRONG here")
naive = [G - STEP * (len(w["cur"]["king"]) - i) for i in range(len(w["cur"]["king"]))]
true_tail = sorted(w["truth"])
kept = [t for t in B["positions_anchor_ts"] if t > w["rep_end"]] if rc == 0 else []
check("★★★ the naive positional rule mislabels the live tail (it ignores the skipped run), the measured rule does not",
      naive[-len(true_tail):] != true_tail and kept == [t for t in true_tail if t > w["rep_end"]] and len(kept) > 0, (naive[-3:], true_tail[-3:]))

print("[2] tail timestamp asserted against prev_rec")
w2 = world("lag", lag_file=True); rc2, o2, out2 = build(w2)
check("★★★ file one anchor behind prev_rec (last entry ≠ prev_rec − 4h) ⇒ STOP, nothing written", rc2 != 0 and "prev_rec" in o2 and not os.path.exists(out2), o2[-200:])
w2b = world("aux"); a = json.load(open(os.path.join(w2b["state"], "aux.json"))); a["prev_rec"]["anchor_ts"] = G - STEP
json.dump(a, open(os.path.join(w2b["state"], "aux.json"), "w")); P.atomic_json(os.path.join(w2b["state"], "generation.json"), P.build_generation_record(w2b["state"], G))
rc2b, o2b, _ = build(w2b)
check("★★ aux.last_anchor / prev_rec / generation disagree ⇒ STOP", rc2b != 0 and "disagree" in o2b, o2b[-200:])

print("[3] incomplete coverage ⇒ non-zero exit, never an equal-weight fallback")
w3 = world("short", rep_n=880); rc3, o3, out3 = build(w3)
check("★★★ fewer than 950 timestamped entries ⇒ exit non-zero, 'NOT falling back', nothing written", rc3 != 0 and "NOT falling back" in o3 and not os.path.exists(out3), o3[-200:])

print("[4] seam discontinuity ⇒ STOP")
w4 = world("seam", rep_drop_tail=1); rc4, o4, out4 = build(w4)
check("★★★ replay ends 4h early (gap at the seam) ⇒ STOP 'seam NOT continuous'", rc4 != 0 and "seam NOT continuous" in o4 and not os.path.exists(out4), o4[-200:])

print("[5] ambiguous step (1 append across 2 anchors) ⇒ STOP")
w5 = world("amb", ambiguous=True); rc5, o5, _ = build(w5)
check("★★ ambiguous ownership ⇒ STOP", rc5 != 0 and "ambiguous" in o5, o5[-200:])

print("[6] current file differs from its own anchor's snapshot ⇒ STOP")
w6 = world("cur", cur_mismatch=True); rc6, o6, _ = build(w6)
check("★★ current != snapshot of the same anchor ⇒ STOP", rc6 != 0 and "differs from the snapshot" in o6, o6[-200:])

print("[9] rev 1 — window contiguity (lead ruling after the 09-26 outage): a hole the replay does not cover ⇒ STOP")
w9a = world("hole1"); rc9a, o9a, out9a = build(w9a)
check("★★★ RED: 1-anchor hole (skipped run) beyond the replay end ⇒ STOP naming it, nothing written",
      rc9a != 0 and "window NOT contiguous: 1 missing" in o9a and not os.path.exists(out9a), o9a[-220:])
w9b = world("outage3", rep_extend=40, outage=True); rc9b, o9b, out9b = build(w9b)
want = RS_u = __import__("datetime").datetime.fromtimestamp(OUT_T, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
check("★★★ RED: the 3-anchor outage hole (12 h gap, 0 appends) beyond the replay end ⇒ STOP naming all 3, nothing written",
      rc9b != 0 and "window NOT contiguous: 3 missing" in o9b and want in o9b and not os.path.exists(out9b), o9b[-220:])
w9c = world("outage3_covered", rep_extend=55, outage=True); rc9c, o9c, out9c = build(w9c)
ok9c = rc9c == 0 and json.load(open(os.path.join(out9c, "BUILD.json")))["window"]["gap_histogram_in_anchors"] == {"1": NKEEP - 1}
check("★★★ POSITIVE: the same outage with a replay that covers it ⇒ build OK, window contiguous ({1: 949}), path A fills the hole",
      ok9c and json.load(open(os.path.join(out9c, "leg_returns_live.NEW.json")))["king"] == [float(v[0]) for _, v in w9c["expected"]], o9c[-220:])

print("[7] install: producer must be stopped; inputs unchanged; generation re-issued (red control: without it the loader refuses)")
lock = os.path.join(w["d"], "shadow.lock"); open(lock, "w").write(str(os.getpid()))
rc7, o7 = run("install", "--state", w["state"], "--build", out, "--stamp", "T1", "--lock", lock, "--producer", PROD)
check("★★★ a LIVE producer pid in the lock ⇒ install refuses, nothing changed", rc7 != 0 and "LIVE pid" in o7 and not os.path.exists(os.path.join(w["state"], "leg_returns_live.json.pre_reseed_T1")), o7[-160:])
# red control: replace the file WITHOUT re-issuing generation
wr = world("rc_gen"); body = open(os.path.join(out, "leg_returns_live.NEW.json"), "rb").read()
P.atomic_write(os.path.join(wr["state"], "leg_returns_live.json"), body)
try: P._read_verified_generation(wr["state"]); refused = False
except ValueError as e: refused = "mismatch" in str(e)
check("★★★ RED CONTROL: file replaced without re-issuing generation.json ⇒ the producer's loader refuses (why install re-issues it)", refused)
open(lock, "w").write("999999")                                        # stale lock: a pid that is not alive
w_before = open(os.path.join(w["state"], "leg_returns_live.json"), "rb").read(); g_before = open(os.path.join(w["state"], "generation.json"), "rb").read()
rc8, o8 = run("install", "--state", w["state"], "--build", out, "--stamp", "T1", "--lock", lock, "--producer", PROD)
inst = json.load(open(os.path.join(out, "INSTALL_T1.json"))) if rc8 == 0 else {}
check("★★★ stale lock (dead pid) ⇒ install proceeds, exit 0, and records it", rc8 == 0 and str(inst.get("producer_lock", "")).startswith("stale lock"), (o8[-160:], inst.get("producer_lock")))
if rc8 == 0:
    now = open(os.path.join(w["state"], "leg_returns_live.json"), "rb").read()
    check("★★★ installed file == candidate bytes", now == open(os.path.join(out, "leg_returns_live.NEW.json"), "rb").read())
    try: P._read_verified_generation(w["state"]); gen_ok = True
    except ValueError: gen_ok = False
    check("★★★ the producer's own _read_verified_generation accepts the re-issued generation", gen_ok)
    check("★★ backups .pre_reseed_T1 inside state/ equal the pre-install bytes",
          open(os.path.join(w["state"], "leg_returns_live.json.pre_reseed_T1"), "rb").read() == w_before
          and open(os.path.join(w["state"], "generation.json.pre_reseed_T1"), "rb").read() == g_before)
    rc9, o9 = run("install", "--state", w["state"], "--build", out, "--stamp", "T2", "--lock", lock, "--producer", PROD)
    check("★★ a second install against changed inputs ⇒ refuses ('changed since the build')", rc9 != 0 and "changed since the build" in o9, o9[-160:])
    print("[8] rollback restores bitwise and the generation verifies")
    rc10, o10 = run("rollback", "--state", w["state"], "--stamp", "T1", "--lock", lock, "--producer", PROD)
    check("★★★ rollback exit 0; both files bitwise == pre-install", rc10 == 0 and open(os.path.join(w["state"], "leg_returns_live.json"), "rb").read() == w_before
          and open(os.path.join(w["state"], "generation.json"), "rb").read() == g_before, o10[-160:])
    open(lock, "w").write(str(os.getpid()))
    rc11, o11 = run("rollback", "--state", w["state"], "--stamp", "T1", "--lock", lock, "--producer", PROD)
    check("★★ rollback with a LIVE producer pid ⇒ refuses", rc11 != 0 and "LIVE pid" in o11, o11[-120:])

print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
print("RESEED_SELFTEST " + ("ALL GREEN" if not FAILS else f"RED {FAILS}"))
sys.exit(1 if FAILS else 0)
