#!/usr/bin/env python3
"""Behavioural tests for Q6 R5–R9: the JOINT checkpoint (PREREG §1d.5), same-cross-section restart, and the late-evidence prefix rebuild (§1d.3).

Every red case has a green baseline asserted before it. The checkpoint cases run the COMPLETE device as a subprocess over a synthetic two-day
pilot_log, split at a day boundary, and compare the resumed full-window state against the uninterrupted one by sha256 of its canonical bytes.
The late-evidence cases drive the pure `late_evidence_rebuild` on a checkpoint the device itself wrote.
Run: python3 tests_q6_checkpoint.py   (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS).
"""
import hashlib, importlib.util, json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "q6_shadow.py")
BASE = 1786147200                                                           # 2026-08-08 00:00 UTC, four-hour aligned
N = [0]; FAILS = []; table = []

_spec = importlib.util.spec_from_file_location("q6_shadow_lib", DEV)
Q6 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(Q6)   # import for the pure helpers; main() is never called here


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:240]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def day_of(k):
    return time.strftime("%Y%m%d", time.gmtime(BASE + k * 14400))


def rb(k, q, s="AAA", source="exec@post_anchor", delay=20):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + delay, symbol=s, venue_position_qty=q, venue_position_notional=q * 10, source=source)


def order(k, cap, cq=0, terminal=False, final=False, s="AAA", rid="r1", side="buy"):
    return dict(anchor_ts=BASE + k * 14400, symbol=s, side=side,
                request_ledger=[dict(client_id=rid, qty=cap, confirmed_qty=cq, terminal=terminal, confirmed_qty_final=final, state="confirmed")])


def fill(k, q, s="AAA", tid=1, side="buy", delay=10):
    return dict(fill_ts=BASE + k * 14400 + delay, symbol=s, side=side, fill_px=10, fill_notional=q * 10, trade_id=tid)


ROOT = tempfile.mkdtemp(prefix="q6cp_tests_", dir=os.environ.get("TMPDIR") or None)


def write_root(name, reads, orders=(), fills=()):
    """one pilot_log root, rows filed under the UTC day of their own anchor/fill time"""
    root = os.path.join(ROOT, name)
    for rows, fname, tkey in ((reads, "position_readback", "anchor_ts"), (orders, "orders", "anchor_ts"), (fills, "fills", "fill_ts")):
        byday = {}
        for r in rows: byday.setdefault(time.strftime("%Y%m%d", time.gmtime(float(r[tkey]))), []).append(r)
        for d, rs in byday.items():
            log = os.path.join(root, "state", "live", "pilot_log", d); os.makedirs(log, exist_ok=True)
            open(os.path.join(log, fname + ".jsonl"), "a").write("".join(json.dumps(x) + "\n" for x in rs))
    for d in sorted({time.strftime("%Y%m%d", time.gmtime(float(r["anchor_ts"]))) for r in reads}):
        log = os.path.join(root, "state", "live", "pilot_log", d); os.makedirs(log, exist_ok=True)
        for f in ("orders", "fills", "anchors"):
            open(os.path.join(log, f + ".jsonl"), "a").close()
    return root


def run(root, f_day, t_day, tag, cp_in=None, cp_out=None):
    out = os.path.join(root, f"receipt_{tag}.json")
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=os.path.join(root, "no_filters.json"), Q6_PROCS="1", Q6_DETAIL="1")
    if cp_in: env["Q6_CHECKPOINT_IN"] = cp_in
    if cp_out: env["Q6_CHECKPOINT_OUT"] = cp_out
    r = subprocess.run([sys.executable, DEV, f_day, t_day, out], capture_output=True, text=True, env=env)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit(f"device failed on {tag}: rc {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-1800:]}")
    return json.load(open(out))


def state_sha(cp_path, symbols=None):
    """the comparable state: hard constraints, observations, admitted / excluded equations, baseline, pending requests — canonical bytes"""
    cp = json.load(open(cp_path))
    syms = {k: v for k, v in cp["symbols"].items() if symbols is None or k in symbols}
    return hashlib.sha256(Q6.canon({k: {kk: v[kk] for kk in ("hard", "observations", "admitted", "excluded", "q0_lots", "step", "pending_requests")}
                                    for k, v in syms.items()})).hexdigest()


def dists(cp_path, s="AAA"):
    return [r.get("distance_lots") for r in json.load(open(cp_path))["symbols"][s]["records"] if r["k"] > 0]


def excl_k(cp_path, s="AAA"):
    return [r["k"] for r in json.load(open(cp_path))["symbols"][s]["records"] if r.get("excluded")]


print("device sha:", Q6.sha(DEV)[:16], "| policy:", Q6.POLICY["name"], Q6.POLICY["revision"][-6:])
try:
    from scipy.optimize import milp  # noqa: F401
except Exception as e:   # noqa: BLE001
    print("FAILURES: scipy.optimize.milp missing:", repr(e)); sys.exit(1)

# ─────────────────────────── [C] joint checkpoint and same-cross-section restart ───────────────────────────
print("\n[C] green baseline: one uninterrupted pass, then the same window split in two with a checkpoint handover")
READS = [rb(0, 0), rb(1, 1), rb(2, 2), rb(6, 3), rb(7, 4)]                  # k 0..2 on day 1, k 6..7 on day 2
ORDERS = [order(1, 5, rid="a")]
FILLS = [fill(1, 1, tid=11), fill(6, 1, tid=61)]
D1, D2 = day_of(0), day_of(6)
r_single = write_root("single", READS, ORDERS, FILLS)
cp_single = os.path.join(r_single, "cp_full.json")
rec_single = run(r_single, D1, D2, "single", cp_out=cp_single)
check("[C0] baseline single pass runs and writes a checkpoint for the symbol", os.path.exists(cp_single) and "AAA" in json.load(open(cp_single))["symbols"], rec_single.get("counts"))
check("[C0] baseline: every observation admitted, distance 0 (the fixture is consistent)", dists(cp_single) == [0, 0, 0, 0] and excl_k(cp_single) == [], (dists(cp_single), excl_k(cp_single)))

r_split = write_root("split", READS, ORDERS, FILLS)
cp_half = os.path.join(r_split, "cp_half.json"); cp_resumed = os.path.join(r_split, "cp_resumed.json")
run(r_split, D1, D1, "half1", cp_out=cp_half)
run(r_split, D2, D2, "half2", cp_in=cp_half, cp_out=cp_resumed)
check("[C1] RESTART PARITY: the resumed full-window state is BIT-IDENTICAL to the uninterrupted one (sha256 of canonical bytes)",
      state_sha(cp_resumed) == state_sha(cp_single), (state_sha(cp_resumed)[:16], state_sha(cp_single)[:16]))
check("[C1] the resumed run reproduces every per-observation distance and exclusion", dists(cp_resumed) == dists(cp_single) and excl_k(cp_resumed) == excl_k(cp_single),
      (dists(cp_resumed), dists(cp_single)))
check("[C1] the checkpoint carries the policy identity and refuses to be replayed under another one",
      json.load(open(cp_half))["policy"] == Q6.POLICY and json.load(open(cp_half))["schema"] == Q6.CHECKPOINT_SCHEMA, json.load(open(cp_half))["policy"])
table.append(("C1 restart parity", state_sha(cp_single)[:12], "identical"))

_bad = os.path.join(r_split, "cp_badpolicy.json"); _b = json.load(open(cp_half)); _b["policy"] = {"name": "max_cardinality", "revision": "not rev 4"}
json.dump(_b, open(_bad, "w"))
_env = dict(os.environ, Q6_REPO=r_split, Q6_FILTERS=os.path.join(r_split, "nf.json"), Q6_PROCS="1", Q6_CHECKPOINT_IN=_bad)
_p = subprocess.run([sys.executable, DEV, D2, D2, os.path.join(r_split, "o.json")], capture_output=True, text=True, env=_env)
check("[C2] RED: a checkpoint written under a DIFFERENT recovery policy is refused, not replayed", _p.returncode != 0 and "policy identity" in (_p.stdout + _p.stderr), (_p.returncode, (_p.stdout + _p.stderr)[-160:]))

print("\n[D7-4] the checkpoint must save the JOINT object, never per-request marginals")
J_READS = [rb(0, 0), rb(1, 1), rb(6, 0)]                                    # two open BUY1; read 1 then read 0 — the reviewer's (1,0) → (0,0)
J_ORDERS = [order(1, 1, rid="a"), order(1, 1, rid="b")]
r_j = write_root("joint", J_READS, J_ORDERS)
cp_j1 = os.path.join(r_j, "cp1.json"); cp_j2 = os.path.join(r_j, "cp2.json")
run(r_j, D1, D1, "j1", cp_out=cp_j1)
check("[D0] green: after read 1 the joint set is {(1,0),(0,1)} and the equation is ADMITTED", json.load(open(cp_j1))["symbols"]["AAA"]["admitted"] == [[1, 1]], json.load(open(cp_j1))["symbols"]["AAA"]["admitted"])
run(r_j, D2, D2, "j2", cp_in=cp_j1, cp_out=cp_j2)
check("[D1] resumed read 0 is REFUSED: monotonicity from the joint Σ = 1 forbids returning to 0 (distance 1, excluded)",
      dists(cp_j2)[-1] == 1 and excl_k(cp_j2) == [2], (dists(cp_j2), excl_k(cp_j2)))
_marg = os.path.join(r_j, "cp1_marginal.json"); _m = json.load(open(cp_j1)); _m["symbols"]["AAA"]["admitted"] = []
json.dump(_m, open(_marg, "w"))
cp_j2m = os.path.join(r_j, "cp2m.json")
run(r_j, D2, D2, "j2m", cp_in=_marg, cp_out=cp_j2m)
check("[D2] RED CONTROL: a checkpoint that dropped the admitted equations (= per-request marginals [0,1] each) WRONGLY accepts the same read 0 at distance 0",
      dists(cp_j2m)[-1] == 0 and excl_k(cp_j2m) == [], (dists(cp_j2m), excl_k(cp_j2m)))
table.append(("D7-4 joint vs marginal", dists(cp_j2)[-1], dists(cp_j2m)[-1]))

print("\n[D8-2] the contract's own acceptance example: after the checkpoint, readings {1, 2} are legal and 3 is refused")
for later, want_d, label in ((1, 0, "1 legal"), (2, 0, "2 legal"), (3, 1, "3 refused")):
    rr = write_root(f"d82_{later}", [rb(0, 0), rb(1, 1), rb(6, later)], J_ORDERS)
    c1 = os.path.join(rr, "c1.json"); c2 = os.path.join(rr, "c2.json")
    run(rr, D1, D1, f"d82a{later}", cp_out=c1); run(rr, D2, D2, f"d82b{later}", cp_in=c1, cp_out=c2)
    check(f"[D3] two open BUY1 checkpointed at Σ = 1, later reading {later}: {label} (distance {want_d})", dists(c2)[-1] == want_d, (later, dists(c2)))

print("\n[P] §1c.3 an open request is CARRIED in the checkpoint with its feasible interval, never dropped")
cpj = json.load(open(cp_single))["symbols"]["AAA"]
pend = cpj["pending_requests"]
check("[P1] the open BUY5 is carried with rid, side, capacity and a feasible interval",
      len(pend) == 1 and pend[0]["rid"] == "a" and pend[0]["side"] == 1 and pend[0]["cap"] == 5 and pend[0]["feasible_interval_lots"][1] == 5, pend)
check("[P2] its evidence floor at the end of the window is the attributed fills (2 lots), not zero and not the capacity",
      pend[0]["feasible_interval_lots"][0] == 2, pend)
check("[P3] the carried hard set keeps the request's own fills and their event times (the generators, not a collapsed interval)",
      len(cpj["hard"]["requests"]) == 1 and len(cpj["hard"]["requests"][0]["fills"]) == 2 and "floor_ts" in cpj["hard"]["requests"][0], cpj["hard"]["requests"][0])

# ─────────────────────────── [L] §1d.3 late evidence ⇒ prefix rebuild ───────────────────────────
print("\n[L] late evidence rebuilds the prefix; the original online receipts are preserved")
r_l = write_root("late", [rb(0, 0), rb(1, 80)], [order(1, 100, rid="r1")])
cp_l = os.path.join(r_l, "cp.json")
run(r_l, D1, D1, "late_before", cp_out=cp_l)
cps = json.load(open(cp_l))["symbols"]["AAA"]
check("[L0] green: the reading of 80 is explained by the open BUY100 and is ADMITTED at distance 0", dists(cp_l) == [0] and cps["admitted"] == [[1, 80]], (dists(cp_l), cps["admitted"]))
T1 = cps["observations"][1]["t"]
LATE = [{"rid": "r1", "side": 1, "exact": 50, "exact_ts": T1 - 100, "floor": 50, "floor_ts": T1 - 100, "terminal": T1 - 100}]
reb = Q6.late_evidence_rebuild(cps, LATE)
check("[L1] a late credible total of 50 (event time BEFORE the admitted reading) excludes that reading at distance dist(80, {50}) = 30",
      reb["records"][1].get("distance_lots") == 30 and reb["records"][1].get("excluded") is True, [{k: v for k, v in r.items() if k in ("k", "distance_lots", "excluded")} for r in reb["records"]])
check("[L2] the exclusion is tagged `late_evidence` and names the distance it used to have", reb["newly_excluded"] == [{"k": 1, "rhs_lots": 80, "distance_lots": 30, "was_distance_lots": 0}], reb["newly_excluded"])
check("[L3] the ORIGINAL online receipt is preserved unchanged (it still reads distance 0)",
      [r.get("distance_lots") for r in reb["records_before"] if r["k"] > 0] == [0] and reb["records_before"][1].get("admitted") is True, reb["records_before"])
check("[L4] the rebuild starts at the late fact's own event time τ, not at the window start", abs(reb["tau"] - (T1 - 100)) < 1e-6, reb["tau"])
table.append(("L1 late C50 on admitted 80", 30, "was 0"))

r_e = write_root("early", [rb(0, 0), rb(1, 80)], [order(1, 100, cq=50, terminal=True, final=True, rid="r1")])
cp_e = os.path.join(r_e, "cp.json")
run(r_e, D1, D1, "early", cp_out=cp_e)
check("[L5] ORDER INDEPENDENCE: the same fact present from the start gives the same distance 30 (both arrival orders end at 30)",
      dists(cp_e) == [30], dists(cp_e))
check("[L6] and it is excluded there too, so the two orders agree on the audit state as well", excl_k(cp_e) == [1], excl_k(cp_e))

_noop = Q6.late_evidence_rebuild(json.load(open(cp_l))["symbols"]["AAA"], [{"rid": "r1", "side": 1, "floor": 0, "floor_ts": T1 - 100}])
check("[L7] CONTROL: a late fact that tightens nothing rebuilds nothing and changes no receipt", _noop["no_change"] is True and _noop["records"] == _noop["records_before"], _noop["tau"])

print("\n" + "-" * 110)
for a, b, c in table: print(f"  {a:34s} {str(b):>14s}  {c}")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
