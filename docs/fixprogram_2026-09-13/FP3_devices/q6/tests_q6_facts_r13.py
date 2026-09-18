#!/usr/bin/env python3
"""Behavioural tests for the FACT-TIME layer of q6_shadow.py (independent review round 13, commit 7ba79b75).

Every red case is one of the reviewer's four counterexamples, built with THEIR fixture shapes (agents/q6/audit_q6_v4.py: `rb` / `order`), and
every expected value is taken from THEIR independent enumeration `timed_reference`, reproduced here verbatim in shape. That enumeration keeps each
floor/exact fact as a (value, event index) pair, holds the request constant after its terminal, and rebuilds chronological admission at every new
prefix — it never calls the MILP or any device method, so it is an oracle and not a mirror. The green baselines are asserted FIRST: a red verdict
only means something when the baseline is green.

  R13-Q1  a larger floor replaced the older floor AND its effective time  ⇒ the earlier anomaly vanished
  R13-Q2  an exact total arriving AFTER the terminal pin had no variable to bind  ⇒ the fact vanished
  R13-Q3  a hard fact that contradicts an ADMITTED observation was treated as a self-contradiction ⇒ permanent UNMEASURABLE instead of a rebuild
  P2      an OFF_LATTICE reading was labelled but still ADMITTED ⇒ the rounded quantity poisoned the next observation

Run: python3 tests_q6_facts_r13.py   (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS)."""
import itertools, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "q6_shadow.py")
BASE = 1786147200                                                           # 2026-08-08 00:00 UTC, four-hour aligned (the reviewer's harness)
DAY = "20260808"
N = [0]; FAILS = []; TABLE = []
ROOT = tempfile.mkdtemp(prefix="q6r13_tests_", dir=os.environ.get("TMPDIR") or None)


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:240]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


# ── the reviewer's fixture builders (audit_q6_v4.py), shape for shape ────────────────────────────────
def rb(k, q):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol="AAA",
                venue_position_qty=q, venue_position_notional=q * 100, source="exec@post_anchor")


def order(snapshot, cq, terminal=False, final=False, cap=2):
    """one order row for client_id 'one'; `snapshot` is the observation index whose time stamps the confirmed_qty snapshot (via cancel_ts)"""
    return dict(anchor_ts=BASE + 14400, submit_ts=BASE + 14400, symbol="AAA", side="buy",
                cancel_ts=BASE + snapshot * 14400 + 10,
                request_ledger=[dict(client_id="one", qty=cap, confirmed_qty=cq, terminal=terminal, confirmed_qty_final=final, state="confirmed")])


def run(name, reads, orders=()):
    root = os.path.join(ROOT, name); log = os.path.join(root, "state", "live", "pilot_log", DAY); os.makedirs(log, exist_ok=True)
    for f, rows in (("position_readback", reads), ("orders", orders), ("fills", []), ("anchors", [])):
        open(os.path.join(log, f + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    filt = os.path.join(root, "filters.json"); open(filt, "w").write(json.dumps({"AAA": {"step": 1}}))
    out = os.path.join(root, "receipt.json")
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=filt, Q6_PROCS="1", Q6_DETAIL="1", PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, DEV, DAY, DAY, out], capture_output=True, text=True, env=env)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit(f"device failed on {name}: rc {r.returncode}\n{r.stdout[-800:]}\n{r.stderr[-1500:]}")
    rec = json.load(open(out)); rec["_obs"] = rec["detail"]["AAA"]["observations"]
    return rec


obs = lambda r: r["_obs"]
dist = lambda r: [o["distance_lots"] for o in obs(r)]
cats = lambda r: [o["category"] for o in obs(r)]
adm = lambda r: [bool(o.get("admitted")) for o in obs(r)]
excl = lambda r: [o["k"] for o in obs(r) if o.get("excluded")]


# ── the reviewer's independent time-indexed enumeration (audit_q6_v4.py `timed_reference`) ───────────
def timed_reference(y, cap, floors=(), exacts=(), terminal=None):
    """One request, cap ≤ 2, enumerated over every monotone trajectory. Each floor/exact is a (event index, value) pair applying from that index
    on; the request is constant from `terminal`; admission is rebuilt chronologically at every prefix. No device code is used."""
    result = []
    for k in range(1, len(y)):
        pool = []
        for tr in itertools.product(range(cap + 1), repeat=k + 1):
            if tr[0] != 0 or any(a > b for a, b in zip(tr, tr[1:])): continue
            if terminal is not None and terminal <= k and any(tr[j] != tr[terminal] for j in range(terminal, k + 1)): continue
            if any(t <= j and tr[j] < v for t, v in floors for j in range(k + 1)): continue
            if any(t <= j and tr[j] != v for t, v in exacts for j in range(k + 1)): continue
            pool.append(tr)
        assert pool, "hard contradiction in reference"
        excluded = []
        for j in range(1, k):
            keep = [tr for tr in pool if tr[j] == y[j]]
            if keep: pool = keep
            else: excluded.append(j)
        d = min(abs(tr[k] - y[k]) for tr in pool)
        if d: excluded.append(k)
        result.append({"distance": d, "rebuilt_excluded": excluded})
    return result


print("[G] green baselines — the device must agree with the reference where nothing is late or off-lattice")
g = run("g_open_buy2_grows", [rb(0, 10), rb(1, 11), rb(2, 12)], [order(1, 0)])
ref = timed_reference([0, 1, 2], 2)
check("[G0] open BUY2, increments 0 → +1 → +2: both observations admitted, distance 0, CLEAN",
      dist(g) == [0, 0] and cats(g) == ["CLEAN", "CLEAN"] and adm(g) == [True, True], obs(g))
check("[G1] the independent enumeration agrees on the baseline", [x["distance"] for x in ref] == dist(g), ref)
check("[G2] the receipt names the snapshot-time source as a weak bound, not a moment",
      "weak_bound:max(cancel_ts,last_fill_ts)" in str(g.get("snapshot_time_source")), g.get("snapshot_time_source"))
check("[G3] per_anchor carries the OFF_LATTICE column (v4 omitted it)", all("OFF_LATTICE" in a for a in g["per_anchor"]), g["per_anchor"][:1])
TABLE.append(("G0 open_buy2_grows", dist(g), cats(g)))

print("\n[R13-Q1] a larger floor must not erase the earlier floor or its event time")
r = run("larger_floor_erases_earlier_floor", [rb(0, 10), rb(1, 10), rb(2, 12)], [order(1, 1), order(2, 2)])
ref = timed_reference([0, 0, 2], 2, floors=[(1, 1), (2, 2)])
check("[Q1a] C ≥ 1 known at t1 and C ≥ 2 at t2, increments 0 then +2 ⇒ distance 1 at t1, 0 at t2 (v4: 0, 0 — both CLEAN)",
      dist(r) == [1, 0], obs(r))
check("[Q1b] the independent enumeration gives the same ladder verdict", [x["distance"] for x in ref] == dist(r), ref)
check("[Q1c] the t1 observation is EXCLUDED, the t2 one is admitted", excl(r) == [1] and adm(r) == [False, True], (excl(r), adm(r)))
check("[Q1d] the oracle is refused by name (a static Request cannot carry a two-rung ladder)",
      (r["oracle_crosscheck"].get("skipped_why") or {}).get("time_varying_floor") == 1, r["oracle_crosscheck"])
TABLE.append(("Q1 larger_floor_erases_earlier_floor", dist(r), cats(r)))

print("\n[R13-Q2] an exact total arriving after the terminal pin must bind the shared pinned variable")
r = run("late_exact_after_terminal_pin_ignored", [rb(0, 10), rb(1, 11), rb(2, 11)], [order(1, 0, True), order(2, 2, True, True)])
ref = timed_reference([0, 1, 1], 2, floors=[(2, 2)], exacts=[(2, 2)], terminal=1)
check("[Q2a] terminal at t1 with unknown total, trustworthy total 2 at t2, increments +1 then +1 ⇒ online receipts 0 then 1 (v4: 0, 0 — the fact vanished)",
      dist(r) == [0, 1], obs(r))
check("[Q2b] the independent enumeration gives the same verdict", [x["distance"] for x in ref] == dist(r), ref)
check("[Q2c] the late total EXCLUDES both observations (the reference's rebuilt_excluded [1, 2]) and the second is FLAGGED, not UNMEASURABLE",
      excl(r) == [1, 2] and cats(r)[1] == "FLAGGED" and obs(r)[0].get("excluded_because") == "late_evidence", (excl(r), cats(r), obs(r)[0]))
check("[Q2d] the reference's rebuilt_excluded matches what the device excluded", ref[-1]["rebuilt_excluded"] == excl(r), (ref[-1], excl(r)))
TABLE.append(("Q2 late_exact_after_terminal_pin", dist(r), cats(r)))

print("\n[R13-Q3] a hard fact that contradicts an ADMITTED observation triggers a prefix rebuild, not permanent UNMEASURABLE")
r = run("late_exact_needs_prefix_rebuild", [rb(0, 10), rb(1, 12), rb(2, 11)], [order(2, 1, True, True)])
ref = timed_reference([0, 2, 1], 2, floors=[(2, 1)], exacts=[(2, 1)], terminal=2)
check("[Q3a] increments +2 then +1 with a trustworthy total 1 at t2 ⇒ current distance 0, CLEAN (v4: UNMEASURABLE, and it stayed that way)",
      dist(r)[-1] == 0 and cats(r)[-1] == "CLEAN", obs(r))
check("[Q3b] the independent enumeration agrees: current distance 0, the t1 observation rebuilt out",
      ref[-1] == {"distance": 0, "rebuilt_excluded": [1]}, ref)
check("[Q3c] the earlier observation is downgraded to EXCLUDED and tagged late_evidence",
      obs(r)[0].get("excluded") is True and obs(r)[0].get("excluded_because") == "late_evidence", obs(r)[0])
check("[Q3d] the record that triggered it says the prefix was rebuilt and names which k came out",
      obs(r)[1].get("prefix_rebuilt") is True and obs(r)[1].get("rebuilt_excluded_k") == [1], obs(r)[1])
check("[Q3e] the ORIGINAL online receipt is preserved (§1d.3 forbids rewriting it): distance_lots still 0, the rebuilt value in its own field",
      obs(r)[0].get("distance_lots") == 0 and obs(r)[0].get("distance_lots_after_rebuild") == 1, obs(r)[0])
TABLE.append(("Q3 late_exact_needs_prefix_rebuild", dist(r), cats(r)))

print("\n[P2] an OFF_LATTICE reading is never ADMITTED as an exact equation")
r = run("off_lattice_still_admitted", [rb(0, 0), rb(1, .51), rb(2, 0)], [dict(order(1, 0), cancel_ts=None)])
check("[P2a] the 0.51 reading is OFF_LATTICE and NOT admitted (v4 labelled it yet wrote the rounded x=1 into the hard constraints)",
      cats(r)[0] == "OFF_LATTICE" and adm(r)[0] is False and obs(r)[0].get("off_lattice_not_admitted") is True, obs(r)[0])
check("[P2b] the next observation is therefore CLEAN, not FLAGGED against a quantity the venue never reported",
      dist(r)[1] == 0 and cats(r)[1] == "CLEAN", obs(r)[1])
check("[P2c] the per-anchor summary counts the OFF_LATTICE observation", sum(a.get("OFF_LATTICE", 0) for a in r["per_anchor"]) == 1,
      r["per_anchor"])
check("[P2d] a row with neither cancel_ts nor last_fill_ts is NAMED, not silently defaulted",
      r["notes"].get("requests_without_snapshot_time", 0) >= 1, r["notes"])
TABLE.append(("P2 off_lattice_still_admitted", dist(r), cats(r)))

print("\n[C] controls — the fixes must not fire where they should not")
c = run("c_on_lattice_admitted", [rb(0, 0), rb(1, 1), rb(2, 1)], [dict(order(1, 0), cancel_ts=None)])
check("[C0] an ON-lattice reading is still admitted (the off-lattice refusal is not blanket)", adm(c) == [True, True] and dist(c) == [0, 0], obs(c))
c = run("c_single_floor_unchanged", [rb(0, 10), rb(1, 11), rb(2, 12)], [order(1, 1)])
check("[C1] a single floor rung behaves exactly as before: both CLEAN", dist(c) == [0, 0] and cats(c) == ["CLEAN", "CLEAN"], obs(c))
c = run("c_hard_contradiction_still_unmeasurable", [rb(0, 0), rb(1, 1)],
        [dict(anchor_ts=BASE + 14400, submit_ts=BASE + 14400, symbol="AAA", side="buy", cancel_ts=BASE + 14410,
              request_ledger=[dict(client_id="one", qty=1, confirmed_qty=2, terminal=True, confirmed_qty_final=True, state="confirmed")])])
check("[C2] facts that contradict EACH OTHER (exact 2 > capacity 1) are still UNMEASURABLE — the rebuild did not swallow that branch",
      cats(c)[0] == "UNMEASURABLE", obs(c))

print("\n%-44s %-14s %s" % ("case", "distances", "categories"))
for n_, d_, c_ in TABLE: print("  %-42s %-14s %s" % (n_, d_, c_))
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
