#!/usr/bin/env python3
"""FP3 P-C1 v14 (2026-09-18, after independent review round 15 R15-P1/P2; v13 after round 14; v12 after round 13; v11 after round 12; v10 after round 11):
replay the EXECUTOR's book layer for one anchor as a pure function and compare the replayed plan with the COMPLETE request population the
executor recorded — every request identity, not the first row per name.

What changed in v14 (independent review round 15 — R15-P1/P2, two counterexamples v13 still passed with complete_parity / all_measurable_exact True):
  · R15-P1 an UNREADABLE maker fill no longer becomes ZERO in the top-up residual. The residual is delta MINUS the TOTAL fill notional;
    production takes it from the CLOSED ledger and REFUSES the top-up when the fills are unreadable (409ea16 binance_executor L1735
    `skipped_unknown_fill`, unknown=("intended_notional","filled_notional"): "topping up from an assumed zero would double an existing
    position"). v13's `_fn_of` preferred `filled_known_notional` — the KNOWN PART, non-None even when a further UNKNOWN part exists — so a
    row with `filled_notional=None` contributed 0, the residual became the FULL delta, and the leg was judged against that fabricated number.
    `_fn_total` now reads `filled_notional` (ledger_row_columns L266: `filled_notional = known_n if closed else None`) plus the unknown-part /
    inconsistency markers; a present owning row whose total is not closed makes the residual UNMEASURABLE (`topup_residual_unmeasurable`), never
    delta − 0. `closed`/`qty_closed` are NOT persisted by _order_row (L2280-2342), so readability is read off the columns that ARE.
    ⇒ THIS IS A MEASUREMENT DEFECT OF THE REPLAY DEVICE (it could not reject a record inconsistent with the production rule). It is NOT evidence
    the live book ever topped up from an assumed zero: production refuses, and the only two real `filled_amount_unknown` rows in range sit on a
    REFUSED anchor (09-12 12Z), so the measured aggregate is unchanged;
  · R15-P2 an unsent / missing-quantity sibling chunk no longer MASKS an already-known over-fill. v13 took `if n_not_sent or n_missing_q:` and
    skipped the quantity comparison entirely, so a chunk SENT for 20 against an expected 15 read all_measurable_exact with an empty diff. The
    KNOWN part is now compared for a contradiction no unsent chunk can undo: |known| > |expected| (same direction) or a wrong-direction known
    chunk is a DIFF; |known| ≤ |expected| stays consistent-so-far (a sibling could complete it) and the remainder is reported unmeasurable;
  · R15 wording: the `_sent` predicate's `unknown` state is "submitted with request content, venue outcome unknown" — it does NOT establish the
    venue accepted it, and an absent order_id does not establish it was never submitted. The two populations are reported SEPARATELY in
    `summary.request_state_population`, and the earlier "DID reach the venue" claim is corrected to what the record supports.

What changed in v13 (independent review round 14 — two full false passes and two classification defects v12 still had):
  · R14-P1 a PRE-BUILT, NEVER-SENT ledger entry is INTENT, not a request. The executor writes one entry per planned chunk with
    `state="not_sent"` / `order_id=None` / no confirmed quantity before trying to send it (409ea16 binance_executor L1934-1944,
    "not_sent → confirmed | unknown | rejected"). v12 read `le["qty"]` blind to the state, so a top-up planned at 15 that never left —
    `abandoned_max_attempts` — was measured as a real 15-lot request and the anchor read `complete_parity=True`. `unknown` was SUBMITTED
    with request content (venue outcome unknown, NOT proven accepted) and stays measurable; `not_sent` now yields `*_not_sent_ledger` and an unmeasurable leg;
  · R14-P2 the TOP-UP RESIDUAL is taken from the rows that actually CARRY the R1/R2 entries. v12 validated fields on the owning row but
    still read `filled_*` off `row1`, so an owner row filled 10 beside a first row recording 25 gave residual 0, let the top-up be skipped
    and reported complete. When the owner and the other candidate row disagree on the fill, that contradiction is now a `diffs` entry —
    two rows may not be cherry-picked to prove one lifecycle;
  · R14-P2 a MISSING (or not-sent) quantity no longer hides an already-judgeable field: side / reduce-only / type are validated on the
    owning row for R2 and R3 whether or not a quantity is present (v12 jumped to the unmeasurable branch and never looked);
  · R14-P2 ONE class per ledger entry. An entry refused on identity (malformed / foreign / duplicate) keeps that class and is excluded from
    the measurement sets — v12 counted a duplicate, then re-counted it as `duplicate_first_leg_request`, then again as `EXPLAINED`
    (5 entries, 7 classifications). Every seq-1 entry being refused now yields `first_leg_requests_all_unexplained`.

What changed from v9 (each item is a reviewer counterexample that v9 passed and v10 must not):
  · the ONLY upstream is `plans_A` = the production path replayed from decision-time records (v9 compared a plan rebuilt from the recorded
    `orders.target_w`, which checks planner arithmetic, not the production path);
  · the downstream is the FULL request set per (rebalance_id, symbol): first maker leg (client_id <rid>-<SYM>-1), maker requote (-2), top-up
    chunks (-3 / -3c<n>), every attempt row — identity (client_id), side, order type, reduce-only flag and step-rounded quantity are all checked;
    a request the plan cannot explain (foreign identity, extra top-up, wrong type) is `unexplained_request`, never ignored;
  · a −5022 post-only reject carries NO request ledger: it is `R1_reject_no_qty_evidence` (NOT exact); whether its `intended_notional` equals
    the replayed delta is reported beside it as `intent_consistent`, and never folded into the exact count;
  · book layer: exact (|Δ| ≤ 1e−6 USDT), no one-step / 1 USDT tolerance; reshape report: EVERY recorded key compared, not two numbers;
  · missing evidence is a labelled refusal (NO_PHASE_A / UNAVAILABLE_STOPSET / filters_assumed_current), never a default empty set;
  · executor code is imported from a `git archive` export of the tree that was DEPLOYED at the anchor's run time (production reflog timeline
    below, read-only), so historical anchors are replayed against their own version; the current tree is verified by rev-parse.
What changed in v12 (independent review round 13, R13-P1 — six counterexamples v11 still passed with complete_parity True):
  · a `client_id` is an IDENTITY: two entries carrying the same id are one request recorded twice ⇒ `UNEXPLAINED:duplicate_client_id`
    (v11 summed them, so a top-up pair 7 + 8 passed as the expected 15);
  · every ledger entry is validated against the row that ACTUALLY carries it (side, reduce_only, order type), not against a separately
    chosen row — v11 read the quantity from the entry and the fields from `row1`, so a ledger moved onto another maker row passed;
  · ABSENT field evidence (`row.side` or `row.reduce_only` not recorded) is a GAP, never a pass: it is counted in
    `n_plans_with_field_evidence_gaps` / `field_evidence_gap_kinds` and it blocks `complete_parity`. On the real ledger every row carries
    `reduce_only = None`, so this is why no real anchor can reach complete parity — stated, not hidden;
  · the plan class is the WORST state over every required leg: a measured R1 no longer buries a top-up with `qty = None` or an unknown skip
    (new class `PARTIAL_UNMEASURABLE:<reason>` — measurement and missing evidence coexist in the verdict);
  · the two population identities are EQUALITIES on stated universes (v11 used `>=`, so an orphan row still read "balanced").
What changed in v11 (independent review round 12, R12-P1 — each is a counterexample v10 passed):
  · TWO CLOSED POPULATIONS with a balance identity: every plan in `plans_A` falls in exactly one class (SKIP_VERIFIED / SKIP_MISMATCH /
    SKIP_NO_ROW / MEASURED_EQUAL / MEASURED_DIFFERENT / MISSING_REQUEST / UNMEASURABLE:<reason>), and every recorded `request_ledger` ENTRY
    falls in exactly one class (EXPLAINED / UNEXPLAINED:<reason>). `population_identity` in the receipt reports both balances;
  · `all_measurable_exact` now REQUIRES `n_quantity_comparisons > 0` — four real halted anchors (09-12 20Z, 09-13 00/04/08Z) carried 966 plans,
    every row `blocked_by_halt` with an empty ledger, zero comparisons, and v10 called them "exact";
  · EVERY ledger entry is compared, not `request_ledger[0]` — a second entry with a legal prefix but attempt 99 / qty 999999 used to be invisible;
  · attempt tokens are restricted to what `client_id_for` can mint (1, 2, 3, 3c<n>); anything else is `UNEXPLAINED:attempt_index_not_mintable`;
  · quantities are compared SIGNED (v10 used abs(), so a ledger whose sign opposed the side passed), and top-up chunks are checked for side
    and reduce_only per chunk;
  · the one-lot tolerance on the top-up total is removed (15 vs 16 at step 1 used to pass); equality is exact after step rounding;
  · a residual ≥ 1e-9 with no top-up row at all is `MISSING_REQUEST` (the executor only omits the row when |residual| < 1e-9, L1826).
Same code, imported: scheduler.anchor_loop.apply_withhold_and_reshape (POP → RESHAPE → CLAMP), live.binance_executor.RebalanceExecutor.plan,
SymbolFilters.round_qty, external_book.below_min_notional, split_for_market (top-up chunking). Inputs = decision-time records only (DESIGN v3 §1).
Read-only everywhere. usage: pc1_intent_replay.py <nominal_anchor_ts> <out.json>
env overrides (tests): PC1_REPO PC1_WS PC1_SCRATCH PC1_TREE_DIR (import from this directory instead of the timeline export) PC1_TREE_LABEL"""
import sys, os, json, time, types, collections, subprocess, hashlib, re

A = int(sys.argv[1]); OUT = sys.argv[2]
REPO = os.environ.get("PC1_REPO") or os.path.expanduser("~/dl_quant_live"); WS = os.environ.get("PC1_WS") or os.path.expanduser("~/wide_shadow")
SCRATCH = os.environ.get("PC1_SCRATCH") or "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/exec_trees"
P = f"{REPO}/state/live/pilot_log"
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))
day = time.strftime("%Y%m%d", time.gmtime(A)); prev_day = time.strftime("%Y%m%d", time.gmtime(A - 14400))
rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
TOL_USDT = 1e-6

# ── executor DEPLOY timeline = HEAD of ~/dl_quant_live on the production machine (git reflog HEAD --date=iso, read 2026-09-18 08:1xZ; the executor
#    runs from that working tree). tree(anchor) = last HEAD movement at or before the anchor's phase_A run time. Assumption stated in the receipt:
#    an edit sitting uncommitted in the working tree before its commit time is not observable here (the deployment protocol commits at deploy).
DEPLOY = [("2026-09-05T11:48:11Z", "12aa2a1"), ("2026-09-06T01:01:55Z", "0ae54cc"), ("2026-09-06T10:09:09Z", "c800690"), ("2026-09-06T10:36:54Z", "9ae2e39"),
          ("2026-09-08T06:42:28Z", "64c4a16"), ("2026-09-09T14:07:20Z", "d040c74"), ("2026-09-12T06:05:30Z", "b681ca5"), ("2026-09-12T07:49:49Z", "77d9baf"),
          ("2026-09-12T09:51:55Z", "918559f"), ("2026-09-13T12:04:14Z", "ef60f85"), ("2026-09-17T02:06:20Z", "6661ea3"), ("2026-09-17T09:15:57Z", "6e177c4"),
          ("2026-09-17T12:59:34Z", "58256ed"), ("2026-09-17T17:30:03Z", "81ea654"), ("2026-09-17T17:45:48Z", "d858c36"), ("2026-09-18T02:46:10Z", "409ea16")]
_ts = lambda s: int(time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone)


def tree_for(run_ts):
    sha = None
    for t, s in DEPLOY:
        if _ts(t) <= run_ts: sha = s
    return sha


def export_tree(sha):
    """git archive of <sha> (scheduler/ signal/ live/ config/) into the scratchpad; read-only on the production repository."""
    d = os.path.join(SCRATCH, sha)
    if not os.path.isdir(os.path.join(d, "scheduler")):
        os.makedirs(d, exist_ok=True)
        full = subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", sha + "^{commit}"], capture_output=True, text=True, check=True).stdout.strip()
        ar = subprocess.run(["git", "-C", REPO, "archive", sha, "scheduler", "signal", "live", "config"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", d], input=ar.stdout, check=True)
        open(os.path.join(d, "TREE_SHA"), "w").write(full + "\n")
    return d, open(os.path.join(d, "TREE_SHA")).read().strip() if os.path.exists(os.path.join(d, "TREE_SHA")) else sha


# ── decision-time records ──
def _ltime(l):
    try: return time.mktime(time.strptime(l[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception: return None


pa = None; pa_time = None; pcs = []
for l in open(f"{REPO}/state/anchor_runs.log"):
    if " phase_A: " in l:
        try: d = json.loads(l.split(" phase_A: ", 1)[1])
        except Exception: continue
        if int(d.get("anchor_ts") or 0) == A or (d.get("external_wait") or {}).get("nominal_anchor_ts") == A: pa = d; pa_time = _ltime(l)
    elif " phase_C: " in l:
        tk = _ltime(l)
        if tk is None: continue
        try: pcs.append((tk, json.loads(l.split(" phase_C: ", 1)[1])))
        except Exception: pcs.append((tk, None))
refusals = []
if not pa: refusals.append("NO_PHASE_A")
if pa and not (pa.get("sizing") or {}).get("nav"): refusals.append("PHASE_A_WITHOUT_SIZING")
run_ts = pa_time if pa_time is not None else A + 1440
tree_dir = os.environ.get("PC1_TREE_DIR"); tree_label = os.environ.get("PC1_TREE_LABEL") or "test_tree"
if not tree_dir:
    sha = tree_for(run_ts)
    if sha is None: refusals.append("NO_DEPLOYED_TREE_FOR_RUN_TIME")
    else: tree_dir, tree_label = export_tree(sha)


def bail(status):
    out = {"device": "pc1_intent_replay.py", "version": "v14", "utc": time.strftime("%FT%TZ", time.gmtime()), "anchor": A, "utc_anchor": U(A), "status": status, "refusals": refusals}
    json.dump(out, open(OUT, "w"), indent=1, default=str); print("P-C1 v14", U(A), status, refusals); sys.exit(0)


if refusals: bail("REFUSED")
sys.path.insert(0, tree_dir)
import scheduler.anchor_loop as AL                      # brings live/, signal/ onto sys.path and imports EXT/LG/PNS itself
from live import binance_executor as BX
tree_sha_check = None
if not os.environ.get("PC1_TREE_DIR"):
    try: tree_sha_check = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception: pass
rid = pa["rebalance_id"]; sz = pa["sizing"]; G = float(sz["gross"]); eq_pre = sz["nav"]
an = [r for r in rows(day, "anchors") if r.get("rebalance_id") == rid]
if not an: refusals.append("NO_ANCHORS_ROW"); bail("REFUSED")
an = an[-1]; eb = an["external_book"]; gross_norm = float(eb["gross_norm"])
tgt_path = f"{WS}/state/target_live/{A}.json"
if not os.path.exists(tgt_path): refusals.append("NO_TARGET_LIVE"); bail("REFUSED")
tgt_file = json.load(open(tgt_path)); assert int(tgt_file["anchor_ts"]) == A
target = {s: float(w) / gross_norm * G for s, w in tgt_file["weights"].items()}                     # w / gross_norm × NAV × gross_mult
od = [r for r in rows(day, "orders") if r.get("rebalance_id") == rid]
if od and not any("request_ledger" in r for r in od): refusals.append("UNAVAILABLE_REQUEST_LEDGER_SCHEMA"); bail("REFUSED")   # per-request ledger exists from the 09-12 executor (b681ca5); older rows carry no request identity
by_sym = collections.defaultdict(list)
for r in od: by_sym[r["symbol"]].append(r)
first = {}
for r in sorted(od, key=lambda r: (r["symbol"], int(r.get("attempt_idx") or 0))): first.setdefault(r["symbol"], r)
mids = {s: float(r["mid_at_anchor"]) for s, r in first.items() if r.get("mid_at_anchor")}
rb_prev = [r for r in rows(prev_day, "position_readback") + rows(day, "position_readback") if (A - 14400) <= float(r["anchor_ts"]) < A and r.get("source", "").endswith("@post_anchor")]
held = {r["symbol"]: float(r["venue_position_notional"]) for r in rb_prev}; held_qty = {r["symbol"]: float(r["venue_position_qty"]) for r in rb_prev}
_un = pa.get("untradable_names") or {}
untr_rec = set().union(*[set(v) for v in _un.values()]) if isinstance(_un, dict) else set(_un or [])
untr = untr_rec | set(eb.get("held_exit") or []) | set((eb.get("meta_excluded") or {}).keys() if isinstance(eb.get("meta_excluded"), dict) else (eb.get("meta_excluded") or []))
reasons = pa.get("untradable_reason") or {}
# decision-time STOP set = what the PREVIOUS run's phase_C wrote (stopped names). No previous phase_C with a dict state ⇒ UNAVAILABLE_STOPSET (refusal, not empty set)
pc_prev = None; pc_prev_time = None
for tk, v in pcs:
    if A - 14400 + 1200 <= tk < A + 1200 and isinstance(v, dict) and isinstance(v.get("per_name_stop"), dict): pc_prev = v["per_name_stop"]; pc_prev_time = tk
stop_feature_disabled = any("disabled" in str(v.get("per_name_stop")) for tk, v in pcs if isinstance(v, dict) and A - 14400 + 1200 <= tk < A + 1200)
if pc_prev is None and not stop_feature_disabled: refusals.append("UNAVAILABLE_STOPSET"); bail("REFUSED")
force_flat = set(s for s, why in (reasons.items() if isinstance(reasons, dict) else []) if "per_name_stop" in str(why) and "cooldown" not in str(why))
stopped_prev = set((pc_prev or {}).get("stopped") or []); force_flat |= stopped_prev
# ── filters (offline, from the executor's own cache; the cache is CURRENT — for an anchor older than the cache file this is an assumption, flagged) ──
fcache = f"{REPO}/state/live/exchange_info_cache.json"
sf = BX.SymbolFilters.__new__(BX.SymbolFilters); sf.f = json.load(open(fcache)); sf.cache_path = None
filters_mtime = os.path.getmtime(fcache); filters_assumed_current = bool(filters_mtime > A + 14400)
fl = {s: float((sf.f.get(s) or {}).get("min_notional", 0.0) or 0.0) for s in target}
tradable = set((pa.get("universe") or {}).get("tradable") or []); gate_out = set(s for s in target if tradable and s not in tradable); untr |= gate_out
dust = AL.EXT.below_min_notional(target, fl, float(eb.get("min_notional_mult") or 2.0)); untr |= set(dust["names"])
# ── same-code book layer: POP → RESHAPE → CLAMP ──
G_norm0 = float(an["target_gross"]); held_rec = {s: float(r["prev_w"]) * G_norm0 for s, r in first.items()}   # executor's decision-time positions as it recorded them (state.positions)
import inspect
_awr_params = set(inspect.signature(AL.apply_withhold_and_reshape).parameters); _plan_params = set(inspect.signature(BX.RebalanceExecutor.plan).parameters)
if force_flat and "force_flat" not in _awr_params: refusals.append("TREE_LACKS_FORCE_FLAT_WITH_STOPS"); bail("REFUSED")     # this version cannot replay a stop set
_kw = {"floors_usdt": fl, "floors_source": "executor.filters.f[*].min_notional"}                                                     # the label production writes
if "force_flat" in _awr_params: _kw["force_flat"] = force_flat
clamp, rs = AL.apply_withhold_and_reshape(target, held_rec, untr, G, **_kw)
capd = pa.get("venue_cap_clamp") or {}; reduce_only = set(clamp.get("reduced") or ()) | set(clamp.get("flatten_only") or ()) | set(capd.get("reduce_only_syms") or [])
_capped = capd.get("capped") or {}; cap_applied = {}
_items = _capped.items() if isinstance(_capped, dict) else [(x.get("symbol"), x) for x in _capped if isinstance(x, dict)]
for s_, info in _items:
    if s_ in target and isinstance(info, dict):
        capv = info.get("cap") or info.get("cap_usdt") or info.get("max_notional") or info.get("capped_to")
        _margin = float(capd.get("margin") or 0.0); _lim = float(capv) * (1.0 - _margin) if capv is not None else None
        if _lim is not None and abs(target[s_]) > _lim:
            cap_applied[s_] = {"before": target[s_], "cap": float(capv), "margin": _margin, "after": _lim, "recorded_after": info.get("target_after"),
                               "rule_matches_record": (info.get("target_after") is None or abs(float(info["target_after"]) - _lim) <= 1e-6)}
            target[s_] = _lim * (1.0 if target[s_] > 0 else -1.0)
    elif s_ in target and isinstance(info, (int, float)) and abs(target[s_]) > float(info): cap_applied[s_] = (target[s_], float(info)); target[s_] = float(info) * (1.0 if target[s_] > 0 else -1.0)
stub = types.SimpleNamespace(filters=sf, band_bps=BX.DEFAULT_BAND_BPS)
_pkw = {"reduce_only_syms": reduce_only}
if "held_qty" in _plan_params: _pkw["held_qty"] = held_qty                                                                        # E-0912-A (b) exists from ef60f85; older trees size exits by notional/mid
plans_A = BX.RebalanceExecutor.plan(stub, target, held_rec, mids, **_pkw)                                                         # THE upstream
plan_by = {p["symbol"]: p for p in plans_A}
# ── book layer: exact (no step / 1 USDT tolerance) ──
G_norm = float(an["target_gross"]); rec_target = {s: float(r["target_w"]) * G_norm for s, r in first.items()}
stageA = []
for s_ in sorted(set(rec_target) | set(target)):
    t_rep = float(target.get(s_, 0.0)); t_rec = rec_target.get(s_)
    stageA.append({"symbol": s_, "replayed": t_rep, "recorded": t_rec, "diff": (None if t_rec is None else t_rep - t_rec), "exact": (None if t_rec is None else abs(t_rep - t_rec) <= TOL_USDT)})
A_ok = sum(1 for e in stageA if e["exact"]); A_n = sum(1 for e in stageA if e["recorded"] is not None); A_max = max((abs(e["diff"]) for e in stageA if e["diff"] is not None), default=0.0)
# ── reshape report: EVERY recorded key ──
rec_rs = an.get("reshape") if isinstance(an.get("reshape"), dict) else {}
rs = rs or {}
def _eq(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try: return float(a) == float(b)
        except Exception: return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)): return list(a) == list(b)
    return a == b
def _close(a, b, rel=1e-9):
    """secondary reading: equal up to float summation-order noise (relative 1e-9, absolute 1e-9), recursively for dicts/lists; strings must be equal"""
    if isinstance(a, dict) and isinstance(b, dict): return set(a) == set(b) and all(_close(a[k], b[k], rel) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)): return len(a) == len(b) and all(_close(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool): return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return abs(float(a) - float(b)) <= max(1e-9, rel * max(abs(float(a)), abs(float(b))))
    return a == b
reshape_cmp = {"n_recorded_keys": len(rec_rs), "equal": [], "equal_within_1e-9": [], "mismatch": {}, "not_replayed": []}
for k, v in rec_rs.items():
    if k not in rs: reshape_cmp["not_replayed"].append(k); continue
    if _eq(v, rs[k]): reshape_cmp["equal"].append(k)
    elif _close(v, rs[k]): reshape_cmp["equal_within_1e-9"].append(k); reshape_cmp["mismatch"][k] = {"recorded": v, "replayed": rs[k], "within_1e-9": True}
    else: reshape_cmp["mismatch"][k] = {"recorded": v, "replayed": rs[k], "within_1e-9": False}
reshape_cmp["all_recorded_keys_equal"] = (len(reshape_cmp["equal"]) == len(rec_rs) and len(rec_rs) > 0)
reshape_cmp["all_recorded_keys_within_1e-9"] = (len(reshape_cmp["equal"]) + len(reshape_cmp["equal_within_1e-9"]) == len(rec_rs) and len(rec_rs) > 0)
# ── request population: every row, joined by identity ──
# ── request population (v11, independent review round 12 R12-P1) ───────────────────────────────────────────────────────────────────────────
# v10 compared ONLY request_ledger[0] of the first order row per name, summed top-up chunks in ABSOLUTE value, allowed a full lot of
# tolerance, and let "nothing was measured" read as `all_measurable_exact = True` (four real halted anchors: 966 plans, 0 comparisons).
# v11 replaces the verdict list with TWO CLOSED POPULATIONS and an identity that must balance:
#   · every PLAN in plans_A falls in exactly one class (skip verified / measured equal / measured different / missing request / unmeasurable);
#   · every recorded LEDGER ENTRY falls in exactly one class (explained by an expected request / unexplained with a reason).
# A quantity comparison is only counted when an actual ledger quantity existed, so a zero-measurement anchor can never be "exact".
VALID_SEQ = re.compile(r"^(?:1|2|3|3c\d+)$")                     # the only attempt tokens binance_executor.client_id_for can mint


def cid_parse(cid):
    m = re.match(r"^(.+)-([A-Z0-9]+USDT)-([0-9A-Za-z]+)$", str(cid or ""))
    return (m.group(1), m.group(2), m.group(3)) if m else None


chase = an.get("chase_experiment") if isinstance(an.get("chase_experiment"), dict) else {}
chase_arms = chase.get("arm_assigned") if isinstance(chase.get("arm_assigned"), dict) else (chase.get("arm") if isinstance(chase.get("arm"), dict) else {})   # topup(): _arm = arm_assigned or arm
chase_arms_recorded = bool(chase_arms)


def _sside(q):
    return "buy" if float(q) > 0 else "sell"


def _sent(le):
    """★ R14-P1 (1) (independent review round 14): the executor PRE-BUILDS one ledger entry per PLANNED chunk with
    `state="not_sent"`, `order_id=None` and no confirmed quantity, then tries to send each one (409ea16
    binance_executor L1934-1944: "States: not_sent → confirmed | unknown | rejected"). v12 read `le["qty"]` without
    looking at the state, so a top-up that was planned at 15 and never left — `state=not_sent`, `order_id=None`,
    `confirmed_qty=None`, `terminal=False`, reason `abandoned_max_attempts` — was measured as a real 15-lot request
    and the anchor read `complete_parity=True`. A not-sent entry is evidence of an INTENT; it can never close a
    request lifecycle. ★ R15 wording: `unknown` = SUBMITTED with request content but the venue OUTCOME is unknown — it stays
    measurable because it carries a request identity and quantity, NOT because the venue accepted it; and an absent order_id
    does not by itself prove a request was never submitted. The state populations are reported SEPARATELY in
    `summary.request_state_population`, so neither claim is overstated in the receipt."""
    st = str(le.get("state") or "").lower()
    if st == "not_sent": return False
    if st in ("confirmed", "unknown", "rejected"): return True
    return bool(le.get("order_id") is not None or le.get("confirmed_qty") is not None or le.get("terminal"))


cmp = []; cat = collections.Counter()
PLAN_CLS = collections.Counter(); REQ_CLS = collections.Counter(); STATE_CLS = collections.Counter()   # R15: request-ledger states, reported separately
n_ledger_entries = 0; n_qty_compared = 0; n_qty_equal = 0
for s in sorted(set(by_sym) | set(plan_by)):
    p = plan_by.get(s); rws = sorted(by_sym.get(s, []), key=lambda r: (int(r.get("attempt_idx") or 0), str(((r.get("request_ledger") or [{}])[0] or {}).get("client_id") or "")))
    e = {"symbol": s, "plan": (p.get("skip") if p and p.get("skip") else ({"qty": float(p["qty"]), "side": p["side"], "reduce_only": bool(p.get("reduce_only"))} if p else None)), "rows": [], "requests": []}
    # ── flatten every ledger entry of every row, parse and validate its identity ──
    ents = []
    for r in rws:
        rl = r.get("request_ledger") or []
        e["rows"].append({"attempt_idx": r.get("attempt_idx"), "order_type": r.get("order_type"), "terminal_reason": r.get("terminal_reason"), "side": r.get("side"),
                          "reduce_only": r.get("reduce_only"), "n_ledger": len(rl), "client_ids": [x.get("client_id") for x in rl], "intended_notional": r.get("intended_notional"),
                          "requote_arm": r.get("requote_arm"), "filled_known_notional": r.get("filled_known_notional"), "filled_notional": r.get("filled_notional"),
                          "filled_unknown_qty": r.get("filled_unknown_qty"), "filled_unknown_residual": r.get("filled_unknown_residual"), "ledger_inconsistent": r.get("ledger_inconsistent")})
        for i, le in enumerate(rl):
            n_ledger_entries += 1
            STATE_CLS[str(le.get("state") or "absent").lower()] += 1   # R15: separate submitted (confirmed/unknown/rejected) from not_sent/absent
            pr = cid_parse(le.get("client_id"))
            bad = ("malformed_client_id" if pr is None else ("foreign_rebalance_id" if pr[0] != rid else ("foreign_symbol" if pr[1] != s else
                   ("attempt_index_not_mintable" if not VALID_SEQ.match(pr[2]) else None))))
            ents.append({"row": r, "idx": i, "le": le, "seq": (pr[2] if (pr and not bad) else None), "bad": bad,
                         "qty": (float(le["qty"]) if le.get("qty") is not None else None), "cid": le.get("client_id"),
                         "state": le.get("state"), "order_id": le.get("order_id"), "confirmed_qty": le.get("confirmed_qty"),
                         "terminal": le.get("terminal"), "sent": _sent(le)})
    # ★ R13-P1 (1): a client_id is a REQUEST IDENTITY. Two ledger entries carrying the same id are one request recorded twice, never two
    #   independent requests — v11 merely summed their quantities, so a 7 + 8 pair passed as the expected 15.
    _cid_n = collections.Counter(x["cid"] for x in ents if x["cid"] is not None)
    for x in ents:
        if x["cid"] is not None and _cid_n[x["cid"]] > 1 and not x["bad"]: x["bad"] = "duplicate_client_id"
    if p is None:
        for x in ents: REQ_CLS["UNEXPLAINED:no_plan_for_symbol"] += 1; e["requests"].append({"cid": x["cid"], "class": "UNEXPLAINED:no_plan_for_symbol"})
        if not ents: REQ_CLS["UNEXPLAINED:order_row_without_plan"] += 1
        e["plan_class"] = None; e["verdicts"] = ["unexplained_request:order_only"]; cat["unexplained_request:order_only"] += 1; cmp.append(e); continue
    for x in ents:
        if x["bad"]: REQ_CLS["UNEXPLAINED:" + x["bad"]] += 1; x["cls"] = "UNEXPLAINED:" + x["bad"]
    # ★ R14-P1 (4): an entry already classified above (malformed / foreign / duplicate identity) keeps THAT class and is
    #   never reconsidered for measurement. v12 left it in e1/e2/e3, so `duplicate_client_id` was counted, then the same
    #   entry was re-counted as `duplicate_first_leg_request` and again as `EXPLAINED`: 5 ledger entries, 7 classifications.
    e1 = [x for x in ents if x["seq"] == "1" and not x.get("cls")]
    e2 = [x for x in ents if x["seq"] == "2" and not x.get("cls")]
    e3 = [x for x in ents if x["seq"] and (x["seq"] == "3" or x["seq"].startswith("3c")) and not x.get("cls")]
    n_seq1_unexplained = sum(1 for x in ents if x["seq"] == "1" and x.get("cls"))
    row1 = next((r for r in rws if r.get("order_type") == "maker" and int(r.get("attempt_idx") or 0) <= 1), None)
    row2 = next((r for r in rws if r.get("order_type") == "maker" and r.get("requote_arm") not in (None, "")), None)
    rows3 = [r for r in rws if r.get("order_type") == "topup_taker"]
    verdicts = []; diffs = []; unmeas = []; missing = []; field_gaps = []

    def _own(x, pside, pro, want_type):
        """★ R13-P1 (2)(4)(5): validate a ledger entry against the row that ACTUALLY carries it. v11 took the quantity from the entry but the
        side / reduce_only / type from a separately chosen row, so a ledger moved onto another maker row (attempt 2, side sell, RO True) was
        judged with the first row's correct fields. Absent evidence (side or reduce_only not recorded) is a GAP, never a pass."""
        r = x["row"]; lq = x["qty"]; g = []; bad = []
        rside = r.get("side"); rro = r.get("reduce_only"); rtype = r.get("order_type")
        if rside is None: g.append("row_side_absent")
        elif str(rside).lower() != pside: bad.append("row_side")
        if lq is not None and _sside(lq) != pside: bad.append("ledger_sign")
        if lq is not None and rside is not None and str(rside).lower() != _sside(lq): bad.append("row_side_vs_ledger_sign")
        if rro is None: g.append("row_reduce_only_absent")
        elif bool(rro) != pro: bad.append("row_reduce_only")
        if rtype != want_type: bad.append("row_type")
        return g, bad
    # ── skipped plan: the expectation is a row carrying the skip reason and NO request at all ──
    if p.get("skip"):
        for x in e1 + e2 + e3:
            if x.get("cls"): continue
            REQ_CLS["UNEXPLAINED:request_for_skipped_plan"] += 1; x["cls"] = "UNEXPLAINED:request_for_skipped_plan"; diffs.append("request_for_skipped_plan")
        if row1 is None and not rws:
            e["plan_class"] = "SKIP_NO_ROW"; verdicts.append("skip_MISSING_ROW"); unmeas.append("no_row")
        else:
            tr = (row1 or rws[0]).get("terminal_reason")
            ok = (tr == p["skip"])
            e["plan_class"] = "SKIP_VERIFIED" if (ok and not diffs) else "SKIP_MISMATCH"
            verdicts.append("skip_match" if ok else f"skip_MISMATCH:{tr}")
            if not ok: diffs.append(f"skip_reason:{tr}")
    else:
        psq = float(p["qty"]); pside = p["side"]; pro = bool(p.get("reduce_only"))
        # ---- R1: the first maker leg. Expected identity <rid>-<SYM>-1, signed qty == plan qty, side and reduce_only == plan ----
        if row1 is None:
            missing.append("no_maker_row"); verdicts.append("R1_MISSING")
        else:
            tr1 = row1.get("terminal_reason"); ro1 = row1.get("reduce_only")
            if len(e1) > 1:
                for x in e1[1:]:
                    if x.get("cls"): continue
                    REQ_CLS["UNEXPLAINED:duplicate_first_leg_request"] += 1; x["cls"] = "UNEXPLAINED:duplicate_first_leg_request"; diffs.append("duplicate_first_leg_request")
                e1 = [e1[0]]
            if n_seq1_unexplained and not e1:
                unmeas.append("first_leg_requests_all_unexplained")                                # every seq-1 entry was refused on identity
            if e1:
                x = e1[0]; lq = x["qty"] if x["sent"] else None
                _g, _bad = _own(x, pside, pro, "maker")
                field_gaps += ["R1:" + z for z in _g]
                if not x["sent"]:
                    unmeas.append(f"first_leg_ledger_not_sent:{x['state']}"); verdicts.append("R1_not_sent_ledger")
                    x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                    if _bad: diffs.append("R1:" + ",".join(_bad)); verdicts.append("R1_MISMATCH")
                    e["R1"] = {"plan_qty_signed": psq, "ledger_qty_signed": None, "ledger_state": x["state"], "planned_qty_not_sent": x["qty"],
                               "owner_row_bad": _bad, "owner_row_evidence_gaps": _g}
                elif lq is None:
                    unmeas.append("first_leg_ledger_without_qty"); verdicts.append("R1_no_qty_evidence"); x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                    if _bad: diffs.append("R1:" + ",".join(_bad)); verdicts.append("R1_MISMATCH")
                else:
                    n_qty_compared += 1
                    qok = abs(lq - psq) <= 1e-9
                    ok = qok and not _bad
                    if ok: n_qty_equal += 1
                    verdicts.append("R1_exact" if ok else "R1_MISMATCH")
                    if not ok: diffs.append("R1:" + ",".join((["qty"] if not qok else []) + _bad))
                    x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                    e["R1"] = {"plan_qty_signed": psq, "ledger_qty_signed": lq, "qty_ok": qok, "owner_row_attempt": x["row"].get("attempt_idx"),
                               "owner_row_bad": _bad, "owner_row_evidence_gaps": _g}
            elif tr1 == "venue_reject":
                oi = row1.get("intended_notional"); pi = float(p["delta_notional"])
                ic = (oi is not None and abs(float(oi) - pi) <= 1e-6 * max(1.0, abs(pi)) and str(row1.get("side")).lower() == pside)
                unmeas.append("venue_reject_no_ledger"); verdicts.append("R1_reject_no_qty_evidence")
                e["R1"] = {"plan_qty_signed": psq, "ledger_qty_signed": None, "intent_consistent": bool(ic), "intended_notional": oi, "plan_delta_notional": pi}
            else:
                unmeas.append(f"not_sent:{tr1}"); verdicts.append(f"R1_not_sent:{tr1}")
        # ---- R2: the requote. Legal ONLY when the first leg was refused by the venue ----
        if e2 or row2 is not None:
            if row1 is None or row1.get("terminal_reason") != "venue_reject":
                for x in e2:
                    if not x.get("cls"): REQ_CLS["UNEXPLAINED:requote_without_reject"] += 1; x["cls"] = "UNEXPLAINED:requote_without_reject"
                diffs.append("requote_without_reject"); verdicts.append("unexplained_request:requote_without_reject")
            else:
                if len(e2) > 1:
                    for x in e2[1:]:
                        if x.get("cls"): continue
                        REQ_CLS["UNEXPLAINED:duplicate_requote_request"] += 1; x["cls"] = "UNEXPLAINED:duplicate_requote_request"; diffs.append("duplicate_requote_request")
                    e2 = [e2[0]]
                if e2:
                    x = e2[0]; lq = x["qty"] if x["sent"] else None
                    # ★ R14-P2 (3): a missing (or not-sent) quantity does not make the SIDE / reduce-only / type evidence
                    #   unreadable. v12 jumped straight to the unmeasurable branch and never looked at the owning row.
                    _g, _bad = _own(x, pside, pro, "maker"); field_gaps += ["R2:" + z for z in _g]
                    if _bad and lq is None: diffs.append("R2:" + ",".join(_bad)); verdicts.append("R2_MISMATCH")
                    if not x["sent"]:
                        unmeas.append(f"requote_ledger_not_sent:{x['state']}"); verdicts.append("R2_not_sent_ledger"); x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                    elif lq is None:
                        unmeas.append("requote_ledger_without_qty"); verdicts.append(f"R2_no_qty_evidence:{(row2 or {}).get('terminal_reason')}"); x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                    else:
                        n_qty_compared += 1
                        qok = abs(lq - psq) <= 1e-9
                        ok = qok and not _bad
                        if ok: n_qty_equal += 1
                        verdicts.append("R2_exact" if ok else "R2_MISMATCH")
                        if not ok: diffs.append("R2:" + ",".join((["qty"] if not qok else []) + _bad))
                        x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
                        e["R2"] = {"plan_qty_signed": psq, "ledger_qty_signed": lq, "qty_ok": qok, "owner_row_attempt": x["row"].get("attempt_idx"),
                                   "owner_row_bad": _bad, "owner_row_evidence_gaps": _g}
                else:
                    unmeas.append("requote_row_without_ledger"); verdicts.append("R2_no_qty_evidence:no_ledger")
        # ---- R3: the top-up. residual = delta_notional − known maker fill notional (binance_executor.topup 409ea16 L1744/1826/1867-1873);
        #      |residual| < 1e-9 ⇒ the executor writes the maker row `filled` and NO top-up row; otherwise a top-up row MUST exist ----
        # ★ R14-P2 (2): the residual must come from the rows that ACTUALLY CARRY the R1/R2 requests, not from whichever
        #   maker row happens to be first. v12 validated the fields on the owning row but still read `filled_*` off row1,
        #   so a ledger moved onto a second maker row (owner filled 10) while row1 recorded 25 gave residual 0, let the
        #   top-up be skipped, and reported complete. Two rows may not be cherry-picked to prove one lifecycle.
        # ★ R15-P1 (independent review round 15): the residual is delta MINUS the row's TOTAL fill notional. Production takes the total from
        #   the CLOSED ledger (`got = filled.get(symbol, 0.0)`) and REFUSES the top-up when the fills are unreadable (409ea16 L1735
        #   `skipped_unknown_fill`, unknown=("intended_notional","filled_notional"): "topping up from an assumed zero would double an existing
        #   position. Both the intended size (delta MINUS an unreadable fill) and the filled amount are UNKNOWN on this row, not zero."). The
        #   authoritative "total known" column is `filled_notional` (ledger_row_columns L266: `filled_notional = known_n if closed else None`);
        #   `filled_known_notional` is ONLY the known PART and is non-None even when a further UNKNOWN part remains, so v13's `_fn_of` (which
        #   preferred it) let an unreadable fill contribute 0, `residual` become the FULL delta, and the leg be judged against that fabricated
        #   number. `closed`/`qty_closed` are NOT persisted by _order_row (L2280-2342), so readability is read off `filled_notional` plus the
        #   unknown-portion / inconsistency markers that ARE persisted. ⇒ MEASUREMENT DEFECT OF THE REPLAY DEVICE (it could not reject a record
        #   inconsistent with the production rule); NOT evidence the live book topped up from an assumed zero — production refuses, and the two
        #   real `filled_amount_unknown` rows in range are on a REFUSED anchor (09-12 12Z), so the measured aggregate is unchanged.
        def _fn_total(r):
            if r is None: return 0.0                                                             # an ABSENT leg contributes nothing (not "unknown")
            if r.get("filled_unknown_qty") is not None or r.get("filled_unknown_residual") is not None or r.get("ledger_inconsistent"):
                return None                                                                       # a known PART beside an unknown part is not a total
            fn = r.get("filled_notional")
            return float(fn) if fn is not None else None                                          # filled_notional is None ⟺ ledger not closed ⟺ UNREADABLE
        own1 = e1[0]["row"] if e1 else row1
        own2 = e2[0]["row"] if e2 else row2
        _tot = {_lbl: _fn_total(r) for _lbl, r in (("R1", own1), ("R2", own2)) if r is not None}
        _unreadable = sorted(_lbl for _lbl, v in _tot.items() if v is None)                       # a PRESENT owning row whose total fill is not closed
        got = sum(v for v in _tot.values() if v is not None)
        for _lbl, _ownr, _alt in (("R1", own1, row1), ("R2", own2, row2)):                        # owner vs the other candidate row
            if _ownr is not None and _alt is not None and _ownr is not _alt:
                _vo, _va = _fn_total(_ownr), _fn_total(_alt)
                if _vo is not None and _va is not None and abs(_vo - _va) > 1e-9:
                    diffs.append(f"{_lbl}:owner_row_fill_contradicts_other_row")
                    verdicts.append(f"{_lbl}_owner_row_fill_contradiction")
                    e[_lbl + "_fill_contradiction"] = {"owner_row_attempt": _ownr.get("attempt_idx"), "owner_filled": _vo,
                                                       "other_row_attempt": _alt.get("attempt_idx"), "other_filled": _va}
        resid_unmeasurable = bool(_unreadable)
        if resid_unmeasurable:                                                                    # ★ R15-P1: the top-up decision input is missing; NOT delta − 0
            unmeas.append("topup_residual_unmeasurable:" + ",".join(_unreadable)); verdicts.append("R3_residual_unmeasurable")
        mid = mids.get(s)
        floor = float((sf.f.get(s) or {}).get("min_notional", 5.0) or 5.0)
        residual = None if resid_unmeasurable else float(p["delta_notional"]) - got
        exp_q = sf.round_qty(s, residual / max(mid, 1e-9)) if (mid and residual is not None) else None    # SIGNED expected chunk total
        rule_skip = None if residual is None else ((exp_q is None) or exp_q == 0 or abs(residual) < floor or abs(exp_q) * max(mid or 0.0, 1e-9) < floor)
        rule_no_row = None if residual is None else abs(residual) < 1e-9
        rec_int = [r.get("intended_notional") for r in rows3]
        int_ok = None if residual is None else (all(v is not None and abs(float(v) - residual) <= 1e-6 * max(1.0, abs(residual)) for v in rec_int) if rows3 else True)
        sent3 = [x for x in e3 if not x.get("cls")]
        e["R3"] = {"residual_rule": residual, "residual_unmeasurable": resid_unmeasurable, "unreadable_fill_legs": _unreadable,
                   "owner_fills_readable": {k: v for k, v in _tot.items()}, "recorded_intended": rec_int, "intended_consistent": int_ok,
                   "expected_qty_signed": (float(exp_q) if exp_q is not None else None), "rule_says_skip": rule_skip, "rule_says_no_row": rule_no_row,
                   "n_topup_rows": len(rows3), "n_chunk_requests": len(sent3), "arm_drawn": chase_arms.get(s), "under_stop": s in force_flat}
        if not rows3 and rule_no_row is False and row1 is not None and row1.get("terminal_reason") not in (None, "venue_reject") and e1:
            missing.append("no_topup_row_though_residual_nonzero"); verdicts.append("R3_MISSING_ROW")
        if sent3:
            n_not_sent = sum(1 for x in sent3 if not x["sent"])
            n_missing_q = sum(1 for x in sent3 if x["sent"] and x["qty"] is None)
            n_known = sum(1 for x in sent3 if x["sent"] and x["qty"] is not None)
            tq = sum(x["qty"] for x in sent3 if x["sent"] and x["qty"] is not None)              # the KNOWN sent total (sent chunks with a quantity)
            for x in sent3: x["cls"] = "EXPLAINED"; REQ_CLS["EXPLAINED"] += 1
            # ★ R14-P2 (3): the chunks' SIDE / reduce-only / type are judged whether or not a quantity is present.
            _cside = pside if exp_q is None else _sside(exp_q)
            _bad3 = []; _g3 = []
            for x in sent3:                                                                      # ★ R13-P1 (2): each chunk against ITS OWN row
                gg, bb = _own(x, _cside, pro, "topup_taker"); _g3 += gg; _bad3 += bb
            _bad3 = sorted(set(_bad3)); field_gaps += ["R3:" + z for z in sorted(set(_g3))]
            e["R3"]["chunk_states"] = [x["state"] for x in sent3]
            _sibling_unmeasurable = bool(n_not_sent or n_missing_q or resid_unmeasurable)        # a chunk / the residual we cannot read
            if n_not_sent:
                unmeas.append("topup_chunk_not_sent"); verdicts.append("R3_not_sent_ledger")
                e["R3"].update(n_chunks_not_sent=n_not_sent, planned_qty_not_sent=sum(x["qty"] for x in sent3 if not x["sent"] and x["qty"] is not None))
            if n_missing_q:
                unmeas.append("topup_chunk_without_qty"); verdicts.append("R3_no_qty_evidence")
            if exp_q is None:
                # ★ R15-P1: the expected total is unmeasurable (the maker fill was unreadable) ⇒ NO quantity comparison; a comparison here
                #   would be against a fabricated delta − 0. The residual-unmeasurable class was already recorded above.
                if _bad3: diffs.append("R3:" + ",".join(_bad3)); verdicts.append("R3_MISMATCH")
                e["R3"].update(sent_total_qty_signed_known=tq, expected_qty_signed=None, quantity_comparable=False)
            elif _sibling_unmeasurable:
                # ★ R15-P2: a sibling chunk is unsent / missing-qty (or the residual is unmeasurable), so the top-up total is not fully
                #   measured — but the KNOWN part is still compared for a contradiction NO unsent chunk can undo. A same-direction over-fill
                #   (|known| > |expected|) or a wrong-direction known chunk is a DIFF; |known| ≤ |expected| is consistent-so-far (a sibling
                #   could complete it) ⇒ measured-partial, unmeasurable. v13 took `if n_not_sent or n_missing_q:` and never compared, so a
                #   sent 20 against an expected 15 read all_measurable_exact with an empty diff, the unsent sibling masking a known over-fill.
                _same = (n_known > 0) and (_sside(tq) == _sside(float(exp_q)))
                _overshoot = _same and abs(tq) > abs(float(exp_q)) + 1e-9
                _wrong_dir = (n_known > 0) and (tq != 0.0) and (not _same)
                _q3 = ["qty_overfill_known"] if _overshoot else (["qty_wrong_direction_known"] if _wrong_dir else [])
                if _q3 or _bad3:
                    diffs.append("R3:" + ",".join(_q3 + _bad3))
                    verdicts.append("R3_known_overfill_despite_unmeasured_sibling" if _overshoot else ("R3_known_wrong_direction_despite_unmeasured_sibling" if _wrong_dir else "R3_MISMATCH"))
                e["R3"].update(sent_total_qty_signed_known=tq, expected_qty_signed=float(exp_q), n_known_chunks=n_known,
                               known_overshoot=bool(_overshoot), known_wrong_direction=bool(_wrong_dir), remainder_unmeasurable=True)
            else:
                n_qty_compared += 1
                qok = abs(tq - float(exp_q)) <= 1e-9                                             # v10 allowed one full lot AND compared |sum|
                aok = (not rule_skip) and int_ok and chase_arms.get(s) != "no_chase" and s not in force_flat
                ok = qok and not _bad3 and aok
                if ok: n_qty_equal += 1
                verdicts.append("R3_consistent" if ok else "R3_lifecycle_unexplained")
                if not ok: diffs.append("R3:" + ",".join((["qty"] if not qok else []) + _bad3 + ([] if aok else ["rule"])))
                e["R3"].update(sent_total_qty_signed=tq, qty_ok=qok, chunk_row_bad=_bad3, chunk_row_evidence_gaps=sorted(set(_g3)), rule_ok=aok)
        for r in rows3:
            if r.get("request_ledger"): continue
            tr = r.get("terminal_reason")
            if tr == "skipped_min_notional": ok = rule_skip and int_ok
            elif tr == "skipped_no_chase_arm": ok = chase_arms_recorded and chase_arms.get(s) == "no_chase" and int_ok
            elif tr == "skipped_stop_maker_only": ok = s in force_flat
            else: ok = None
            if ok is True: verdicts.append("R3_skip_consistent")
            elif ok is False: verdicts.append(f"R3_skip_unexplained:{tr}"); diffs.append(f"R3_skip:{tr}")
            else: verdicts.append(f"R3_skip:{tr}"); unmeas.append(f"topup_skip_unverifiable:{tr}")
        # ---- one class per plan ----
        # ★ R13-P1 (3): the class is the WORST state over every required leg. v11 checked "any leg measured" BEFORE "any leg unmeasurable",
        #   so a measured R1 buried a top-up with qty=None or an UNKNOWN_SKIP and the plan read MEASURED_EQUAL with n_unmeasurable = 0.
        _measured = e.get("R1", {}).get("ledger_qty_signed") is not None or e.get("R2") or ("sent_total_qty_signed" in e["R3"])
        if missing: e["plan_class"] = "MISSING_REQUEST"
        elif diffs: e["plan_class"] = "MEASURED_DIFFERENT"
        elif unmeas: e["plan_class"] = ("PARTIAL_UNMEASURABLE:" if _measured else "UNMEASURABLE:") + unmeas[0]
        elif _measured: e["plan_class"] = "MEASURED_EQUAL"
        else: e["plan_class"] = "UNMEASURABLE:no_quantity_evidence"
        e["field_gaps"] = sorted(set(field_gaps))
    for x in ents:
        if not x.get("cls"): x["cls"] = "UNEXPLAINED:unclassified_request"; REQ_CLS["UNEXPLAINED:unclassified_request"] += 1
        e["requests"].append({"cid": x["cid"], "seq": x["seq"], "qty": x["qty"], "class": x["cls"]})
    PLAN_CLS[e["plan_class"]] += 1
    e["diffs"] = diffs; e["unmeasurable"] = unmeas; e["missing"] = missing; e["verdicts"] = verdicts
    for v in verdicts: cat[v] += 1
    cmp.append(e)
# ── the two population identities: nothing may fall outside a class ──
n_plans = len(plans_A); n_plan_classified = sum(PLAN_CLS.values())
n_sym_no_plan = sum(1 for e in cmp if e.get("plan_class") is None)
n_req_classified = sum(REQ_CLS.values())
# ★ R13-P1 (6): v11 used >=, so an orphan row could push n_request_classified above n_ledger_entries and still read "balanced".
#   The universes are now stated: every plan has exactly one class, and every ledger ENTRY has exactly one class.
ident_plan = (n_plan_classified == n_plans) and all(e.get("plan_class") or e["plan"] is None for e in cmp)
ident_req = (n_req_classified == n_ledger_entries)
n_plan_sent = sum(1 for p in plans_A if not p.get("skip"))
n_measured_equal = PLAN_CLS["MEASURED_EQUAL"]; n_measured_diff = PLAN_CLS["MEASURED_DIFFERENT"]; n_missing_req = PLAN_CLS["MISSING_REQUEST"]
n_unmeasurable = sum(v for k, v in PLAN_CLS.items() if k.startswith("UNMEASURABLE") or k.startswith("PARTIAL_UNMEASURABLE") or k == "SKIP_NO_ROW")
n_field_gaps = sum(1 for e in cmp if e.get("field_gaps"))            # plans where side / reduce_only evidence is ABSENT (not wrong): unknown is not parity
n_skip_ok = PLAN_CLS["SKIP_VERIFIED"]; n_skip_bad = PLAN_CLS["SKIP_MISMATCH"]
n_req_unexplained = sum(v for k, v in REQ_CLS.items() if k.startswith("UNEXPLAINED"))
n_R1_exact = cat["R1_exact"]; n_R1_reject = cat["R1_reject_no_qty_evidence"]
n_R1_mismatch = cat["R1_MISMATCH"] + cat["R1_MISSING"]
n_unexpl = n_measured_diff + n_missing_req + n_skip_bad + n_req_unexplained
n_rows = len(od)
summary = {"n_symbols_compared": len(cmp), "n_order_rows": n_rows, "n_plan_sent": n_plan_sent, "n_plan_skipped": len(plans_A) - n_plan_sent,
           "n_ledger_entries": n_ledger_entries, "n_quantity_comparisons": n_qty_compared, "n_quantity_equal": n_qty_equal,
           "plan_population": dict(PLAN_CLS), "request_population": dict(REQ_CLS), "request_state_population": dict(STATE_CLS),
           "population_identity": {"n_plans": n_plans, "n_plan_classified": n_plan_classified, "n_symbols_without_plan": n_sym_no_plan,
                                   "n_ledger_entries": n_ledger_entries, "n_request_classified": n_req_classified,
                                   "plans_balance": bool(ident_plan), "requests_balance": bool(ident_req)},
           "R1_exact": n_R1_exact, "R1_reject_no_qty_evidence": n_R1_reject, "R1_intent_consistent_among_rejects": sum(1 for e in cmp if (e.get("R1") or {}).get("intent_consistent")),
           "R1_mismatch_or_missing": n_R1_mismatch, "R2_exact": cat["R2_exact"], "R2_no_qty_evidence": sum(v for k, v in cat.items() if k.startswith("R2_no_qty")),
           "R3_consistent": cat["R3_consistent"] + cat["R3_skip_consistent"], "n_unexplained_or_mismatch": n_unexpl, "n_unmeasurable": n_unmeasurable,
           "n_plans_with_field_evidence_gaps": n_field_gaps,
           "field_evidence_gap_kinds": dict(collections.Counter(z for e in cmp for z in (e.get("field_gaps") or []))),
           # ★ R12-P1: a zero-measurement anchor can NEVER be "exact". 966 plans with 0 comparisons used to read True.
           "all_measurable_exact": bool(n_qty_compared > 0 and n_unexpl == 0 and n_R1_mismatch == 0 and ident_plan and ident_req),
           "complete_parity": bool(n_qty_compared > 0 and n_unexpl == 0 and n_R1_mismatch == 0 and n_R1_reject == 0 and n_unmeasurable == 0
                                   and n_field_gaps == 0 and ident_plan and ident_req and A_ok == A_n and reshape_cmp["all_recorded_keys_equal"]),
           "categories": dict(cat)}
out = {"device": "pc1_intent_replay.py", "version": "v14", "utc": time.strftime("%FT%TZ", time.gmtime()), "anchor": A, "utc_anchor": U(A), "rebalance_id": rid, "status": "OK",
       "executor_tree": {"label": tree_label, "dir": tree_dir, "rule": "production reflog HEAD at phase_A run time (assumption: no uncommitted working-tree edits before commit time)",
                         "run_time_utc": time.strftime("%FT%TZ", time.gmtime(run_ts)) if run_ts else None, "current_head_rev_parse": tree_sha_check},
       "inputs": {"eq_pre_from_phase_A": eq_pre, "sizing_gross": G, "gross_norm": gross_norm, "target_gross_recorded": G_norm, "n_targets": len(tgt_file["weights"]), "n_held_prev_readback": len(held),
                  "n_untradable": len(untr), "n_gate_out": len(gate_out), "n_dust": len(dust["names"]), "force_flat": sorted(force_flat), "stopped_prev_phase_C": sorted(stopped_prev),
                  "phase_C_prev_time_utc": (time.strftime("%FT%TZ", time.gmtime(pc_prev_time)) if pc_prev_time else None), "stop_feature_disabled": stop_feature_disabled,
                  "filters_cache_mtime_utc": time.strftime("%FT%TZ", time.gmtime(filters_mtime)), "filters_assumed_current": filters_assumed_current, "venue_cap_applied": cap_applied},
       "reshape_replayed": {k: v for k, v in rs.items() if k in ("net_before", "net_after", "gross_before", "gross_after", "names_crossed_floor", "n_popped", "max_name_delta_pp")},
       "reshape_compare": reshape_cmp, "clamp_counts": {k: len(v) for k, v in clamp.items() if hasattr(v, "__len__")},
       "stage_A_book_layer": {"n": A_n, "exact": A_ok, "max_abs_diff_usdt": A_max, "tolerance_usdt": TOL_USDT, "rows_off": [e for e in stageA if e["exact"] is False][:40]},
       "summary": summary, "rows": cmp, "assumptions": ["filters from the CURRENT exchange_info_cache.json" + (" (anchor older than the cache: assumed)" if filters_assumed_current else ""),
                                                        "pre-trade notional = orders.prev_w × target_gross (executor's own decision-time valuation); contracts from the previous post_anchor readback",
                                                        "top-up legs are checked for remaining-quantity consistency only (chunking/skip rules), not replayed end-to-end"]}
json.dump(out, open(OUT, "w"), indent=1, default=str)
print("P-C1 v14", U(A), rid, "tree", tree_label, "| eq_pre", eq_pre, "gross", G, "| targets", len(tgt_file["weights"]), "held", len(held), "untradable", len(untr), "dust", len(dust["names"]), "force_flat", len(force_flat))
print("book layer exact %d / %d (max |Δ| %.6f USDT) | reshape keys equal %d / %d mismatch %s not_replayed %s" % (A_ok, A_n, A_max, len(reshape_cmp["equal"]), len(rec_rs), list(reshape_cmp["mismatch"])[:6], reshape_cmp["not_replayed"][:6]))
print("requests:", {k: summary[k] for k in ("n_order_rows", "n_plan_sent", "R1_exact", "R1_reject_no_qty_evidence", "R1_intent_consistent_among_rejects", "R1_mismatch_or_missing", "R2_exact", "R3_consistent", "n_unexplained_or_mismatch", "all_measurable_exact", "complete_parity")})
print("categories:", dict(cat))
