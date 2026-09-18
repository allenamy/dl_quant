#!/usr/bin/env python3
"""FP3 P-C1 v10 (2026-09-18, after independent review round 11 R11-PC1): replay the EXECUTOR's book layer for one anchor as a pure function and
compare the replayed plan with the COMPLETE request population the executor recorded — every request identity, not the first row per name.

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
    out = {"device": "pc1_intent_replay.py", "version": "v10", "utc": time.strftime("%FT%TZ", time.gmtime()), "anchor": A, "utc_anchor": U(A), "status": status, "refusals": refusals}
    json.dump(out, open(OUT, "w"), indent=1, default=str); print("P-C1 v10", U(A), status, refusals); sys.exit(0)


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
def cid_seq(cid):
    m = re.match(r"^(.+?)-([A-Z0-9]+USDT)-(\d+|3c\d+)$", str(cid or ""))
    return (m.group(1), m.group(2), m.group(3)) if m else None
chase = an.get("chase_experiment") if isinstance(an.get("chase_experiment"), dict) else {}
chase_arms = chase.get("arm_assigned") if isinstance(chase.get("arm_assigned"), dict) else (chase.get("arm") if isinstance(chase.get("arm"), dict) else {})   # topup(): _arm = arm_assigned or arm
chase_arms_recorded = bool(chase_arms)
cmp = []; cat = collections.Counter()
for s in sorted(set(by_sym) | set(plan_by)):
    p = plan_by.get(s); rws = sorted(by_sym.get(s, []), key=lambda r: (int(r.get("attempt_idx") or 0), str((r.get("request_ledger") or [{}])[0].get("client_id") if r.get("request_ledger") else "")))
    e = {"symbol": s, "plan": (p.get("skip") if p and p.get("skip") else ({"qty": abs(float(p["qty"])), "side": p["side"], "reduce_only": bool(p.get("reduce_only"))} if p else None)), "rows": []}
    if p is None:
        e["verdict"] = "unexplained_request:order_only"; cat[e["verdict"]] += 1; cmp.append(e); continue
    pq = None if p.get("skip") else abs(float(p["qty"])); pside = None if p.get("skip") else p["side"]
    r1 = r2 = None; r3 = []; other = []
    for r in rws:
        rl = r.get("request_ledger") or []; cids = [x.get("client_id") for x in rl]; seqs = [cid_seq(c) for c in cids]
        bad_id = [c for c, q in zip(cids, seqs) if q is None or q[0] != rid or q[1] != s]
        typ = r.get("order_type")
        rec = {"attempt_idx": r.get("attempt_idx"), "order_type": typ, "terminal_reason": r.get("terminal_reason"), "side": r.get("side"), "client_ids": cids,
               "ledger_qty": [x.get("qty") for x in rl], "confirmed_qty": [x.get("confirmed_qty") for x in rl], "intended_notional": r.get("intended_notional"), "requote_arm": r.get("requote_arm"), "reduce_only": r.get("reduce_only")}
        e["rows"].append(rec)
        if bad_id: other.append(("foreign_identity", rec)); continue
        sq = seqs[0][2] if seqs else None
        if typ == "maker" and (sq == "1" or (not rl and r.get("requote_arm") in (None, "") )):
            if r1 is None: r1 = (r, rec, rl)
            else: other.append(("duplicate_first_leg", rec))
        elif typ == "maker" and (sq == "2" or (not rl and r.get("requote_arm") not in (None, ""))):
            if r2 is None: r2 = (r, rec, rl)
            else: other.append(("duplicate_requote", rec))
        elif typ == "topup_taker" and (sq is None or sq == "3" or sq.startswith("3c")): r3.append((r, rec, rl))
        else: other.append(("unclassified", rec))
    verdicts = []
    if p.get("skip"):
        if r1 is None and not r2 and not r3 and not other: verdicts.append("skip_MISSING_ROW")          # submit_maker writes a row for every plan skip: no row is a mismatch
        if r1 is not None:
            verdicts.append("skip_match" if r1[1]["terminal_reason"] == p["skip"] and not r1[2] else f"skip_MISMATCH:{r1[1]['terminal_reason']}")
        if r2 or r3: verdicts.append("unexplained_request:legs_after_skip")
    else:
        if r1 is None: verdicts.append("R1_MISSING")
        else:
            r, rec, rl = r1
            side_ok = str(rec["side"]).lower() == pside; ro_ok = (rec["reduce_only"] is None) or (bool(rec["reduce_only"]) == bool(p.get("reduce_only")))
            if rl:
                q1 = abs(float(rl[0]["qty"])) if rl[0].get("qty") is not None else None
                ok = q1 is not None and abs(q1 - pq) <= 1e-9 and side_ok and ro_ok and rec["order_type"] == "maker"
                verdicts.append("R1_exact" if ok else "R1_MISMATCH"); e["R1"] = {"plan_qty": pq, "ledger_qty": q1, "side_ok": side_ok, "reduce_only_ok": ro_ok}
            elif rec["terminal_reason"] == "venue_reject":
                oi = r.get("intended_notional"); pi = float(p["delta_notional"])
                ic = (oi is not None and abs(float(oi) - pi) <= 1e-6 * max(1.0, abs(pi)) and side_ok)
                verdicts.append("R1_reject_no_qty_evidence"); e["R1"] = {"plan_qty": pq, "ledger_qty": None, "intent_consistent": bool(ic), "intended_notional": oi, "plan_delta_notional": pi}
            else:
                verdicts.append(f"R1_not_sent:{rec['terminal_reason']}")
        if r2 is not None:
            r, rec, rl = r2
            if r1 is None or r1[1]["terminal_reason"] != "venue_reject": verdicts.append("unexplained_request:requote_without_reject")
            else:
                q2 = abs(float(rl[0]["qty"])) if rl and rl[0].get("qty") is not None else None
                if q2 is None: verdicts.append(f"R2_no_qty_evidence:{rec['terminal_reason']}")
                else: verdicts.append("R2_exact" if abs(q2 - pq) <= 1e-9 and str(rec["side"]).lower() == pside else "R2_MISMATCH"); e["R2"] = {"plan_qty": pq, "ledger_qty": q2}
        if r3:
            # top-up rule (binance_executor.topup, 409ea16 L1744/1867-1873): residual = delta_notional − got (known maker fill notional);
            # qty = round_qty(residual / mid_at_anchor); skipped_min_notional iff qty == 0 or |residual| < floor or |qty|·mid < floor;
            # skipped_no_chase_arm iff the name DREW no_chase (anchors.chase_experiment.arm_assigned); skipped_stop_maker_only iff under the stop
            got = 0.0
            for x in (r1, r2):
                if x:
                    fn = x[0].get("filled_known_notional"); fn = x[0].get("filled_notional") if fn is None else fn
                    if fn is not None: got += float(fn)
            residual = float(p["delta_notional"]) - got; mid = mids.get(s)
            floor = float((sf.f.get(s) or {}).get("min_notional", 5.0) or 5.0); step = float((sf.f.get(s) or {}).get("step") or 0.0)
            exp_q = sf.round_qty(s, residual / max(mid, 1e-9)) if mid else None
            rule_skip = (exp_q is None) or exp_q == 0 or abs(residual) < floor or abs(exp_q) * max(mid or 0.0, 1e-9) < floor
            sent = [x for x in r3 if x[2]]; skipped = [x for x in r3 if not x[2]]
            tq = sum(abs(float(le["qty"])) for x in sent for le in x[2] if le.get("qty") is not None)
            rec_int = [x[0].get("intended_notional") for x in r3]
            int_ok = all(v is not None and abs(float(v) - residual) <= 1e-6 * max(1.0, abs(residual)) for v in rec_int)
            e["R3"] = {"residual_rule": residual, "recorded_intended": rec_int, "intended_consistent": int_ok, "expected_qty": (abs(float(exp_q)) if exp_q is not None else None),
                       "rule_says_skip": rule_skip, "sent_total_qty": tq, "n_chunks_sent": len(sent), "arm_drawn": chase_arms.get(s), "under_stop": s in force_flat}
            if sent:
                ok = (not rule_skip) and exp_q is not None and abs(tq - abs(float(exp_q))) <= max(step, 1e-9) and int_ok and chase_arms.get(s) != "no_chase" and s not in force_flat
                verdicts.append("R3_consistent" if ok else "R3_lifecycle_unexplained")
            for x in skipped:
                tr = x[1]["terminal_reason"]
                if tr == "skipped_min_notional": verdicts.append("R3_skip_consistent" if (rule_skip and int_ok) else "R3_skip_unexplained:min_notional")
                elif tr == "skipped_no_chase_arm": verdicts.append("R3_skip_consistent" if (chase_arms_recorded and chase_arms.get(s) == "no_chase" and int_ok) else ("R3_skip_unexplained:no_chase_arm" if chase_arms_recorded else "R3_skip_unverifiable:no_arm_record"))
                elif tr == "skipped_stop_maker_only": verdicts.append("R3_skip_consistent" if s in force_flat else "R3_skip_unexplained:stop")
                else: verdicts.append(f"R3_skip:{tr}")
    for why, rec in other: verdicts.append(f"unexplained_request:{why}")
    e["verdicts"] = verdicts
    for v in verdicts: cat[v] += 1
    cmp.append(e)
n_plan_sent = sum(1 for p in plans_A if not p.get("skip"))
n_R1_exact = cat["R1_exact"]; n_R1_reject = cat["R1_reject_no_qty_evidence"]; n_R1_mismatch = cat["R1_MISMATCH"] + cat["R1_MISSING"]
n_unexpl = sum(v for k, v in cat.items() if k.startswith("unexplained_request") or k.startswith("R3_lifecycle_unexplained") or k.startswith("R3_skip_unexplained") or k.endswith("_MISMATCH") or k.startswith("skip_MISMATCH") or k == "skip_MISSING_ROW")
n_rows = len(od)
summary = {"n_symbols_compared": len(cmp), "n_order_rows": n_rows, "n_plan_sent": n_plan_sent, "n_plan_skipped": len(plans_A) - n_plan_sent,
           "R1_exact": n_R1_exact, "R1_reject_no_qty_evidence": n_R1_reject, "R1_intent_consistent_among_rejects": sum(1 for e in cmp if (e.get("R1") or {}).get("intent_consistent")),
           "R1_mismatch_or_missing": n_R1_mismatch, "R2_exact": cat["R2_exact"], "R2_no_qty_evidence": sum(v for k, v in cat.items() if k.startswith("R2_no_qty")),
           "R3_consistent": cat["R3_consistent"] + cat["R3_skip_consistent"], "n_unexplained_or_mismatch": n_unexpl,
           "all_measurable_exact": (n_unexpl == 0 and n_R1_mismatch == 0), "complete_parity": (n_unexpl == 0 and n_R1_mismatch == 0 and n_R1_reject == 0 and A_ok == A_n and reshape_cmp["all_recorded_keys_equal"]),
           "categories": dict(cat)}
out = {"device": "pc1_intent_replay.py", "version": "v10", "utc": time.strftime("%FT%TZ", time.gmtime()), "anchor": A, "utc_anchor": U(A), "rebalance_id": rid, "status": "OK",
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
print("P-C1 v10", U(A), rid, "tree", tree_label, "| eq_pre", eq_pre, "gross", G, "| targets", len(tgt_file["weights"]), "held", len(held), "untradable", len(untr), "dust", len(dust["names"]), "force_flat", len(force_flat))
print("book layer exact %d / %d (max |Δ| %.6f USDT) | reshape keys equal %d / %d mismatch %s not_replayed %s" % (A_ok, A_n, A_max, len(reshape_cmp["equal"]), len(rec_rs), list(reshape_cmp["mismatch"])[:6], reshape_cmp["not_replayed"][:6]))
print("requests:", {k: summary[k] for k in ("n_order_rows", "n_plan_sent", "R1_exact", "R1_reject_no_qty_evidence", "R1_intent_consistent_among_rejects", "R1_mismatch_or_missing", "R2_exact", "R3_consistent", "n_unexplained_or_mismatch", "all_measurable_exact", "complete_parity")})
print("categories:", dict(cat))
