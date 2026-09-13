#!/usr/bin/env python3
"""X-COST (AUDIT_EXEC CHK-03): why the maker share of rebalance fills fell — decomposition device.

COMMITTED BEFORE IT IS RUN. Every definition below is frozen before any decomposition number exists. The only data
look before the freeze was the schema census (x_cost_schema_census.py, value SETS only) and a field-semantics check of
prev_w on four named anchors (row sums over attempt-1 maker rows, before de-duplication by symbol: Σ|prev_w| =
0 / 0 / 0.305 / 1.116 on 09-13 12Z / 09-07 04Z / 09-03 16Z / 09-11 12Z) and of the '[-5022]' note prefix.

READ-ONLY. Reads ~/dl_quant_live/state/live/pilot_log/<day>/{orders,fills,anchors}.jsonl; writes only under the X_COST
receipts directory given on the command line. No venue call, no credential, no state write.

======================================================================================================================
INFORMATION BARRIER (binding; team-lead 2026-09-13 X-COST brief §A.3)
  Not computed, by construction: the chase prereg outcome H (residual direction x next-anchor mid drift) or H-X, any
  requote-arm markout or outcome (price/cost vs mid), any placement behind/join markout or fill-rate split by arm.
  Mechanism: rows are PROJECTED onto the allow-lists below at parse time, so price, mid, markout, placement-arm and
  timing fields never enter memory; `_barrier_selfcheck()` fails the run if a forbidden field name appears anywhere
  in this file outside the FORBIDDEN declaration. Arm-level taker NOTIONAL, FEES and COUNTS are cost-side and allowed
  (lead's brief; chase prereg allows cost upper bound and arm balance monitoring). Placement arm is not loaded at all.
======================================================================================================================

FROZEN DEFINITIONS
D1 Population window: anchors with nominal time in [2026-08-28T00:00Z, 2026-09-13T12:00Z] (inclusive).
   Nominal time of a rebalance id = anchors.jsonl external_book.nominal_ts; if the id has no anchors row, floor of the
   row's own anchor_ts to the 4h grid (source recorded). FLATTEN-<ts> batches map to the 4h slot containing <ts>.
D2 Fill identity: fills de-duplicated on (symbol, trade_id), last row wins in (day, line) order across all days read
   (the file is append-only; supersede copies carry the same trade). Rows without trade_id are kept as-is and counted.
   The canonical pilot_log.collapse_supersedes keys on trade_id alone; the number of trade_ids shared by two different
   symbols is reported as a data-quality check.
D3 Maker denominator: M = Σ|fill_notional| over de-duplicated fills with venue_maker_flag == true and order_type in
   {maker, topup_taker}. Rebalance taker notional: T = Σ|fill_notional| over fills with venue_maker_flag == false and
   order_type in {maker, topup_taker}. D = M + T. Maker share = M / D (this is the AUDIT_EXEC CHK-03 caliber).
   Protective FLATTEN fills (order_type protective_flatten) are outside D and reported as K1.
D4 Exact identity (per anchor, per period): T = K2d + K2q + K2e + K2n + K3ci + K3co + K3f + K3nc + K3n + K4 + K5 + K6 + K7
   Each taker fill is assigned to exactly one component, in this order:
     K5  maker-type order row filled with venue_maker_flag == false (post-only should make this 0)
     K7  order_type not in {maker, topup_taker, protective_flatten}
     for order_type == topup_taker, join the order row on (rebalance_id, symbol, order_type):
     K6  no order row found (unjoined)
     K4  joined row has no topup_source
     K2* topup_source == from_reject, by the row's requote_arm: d = direct, q = requote, e = exempt, n = null/absent
     K3* topup_source == from_partial, by the row's treated chase_arm (fallback chase_arm_assigned, source recorded):
         ci = chase and anchor chase_experiment.in_sample true; co = chase and in_sample not true;
         f = chase_forced; nc = no_chase (should be 0: no_chase is skipped); n = no arm recorded
     If several topup rows share a key and disagree on (topup_source, requote_arm, chase arm), the fill goes to the
     FIRST row with a non-null filled_notional and the disagreement is counted (K_ambiguous_keys).
   Identity check: |T - Σ components| <= 1e-6 USDT per anchor, else the run exits 3.
D5 Overlay tags on taker fills (NOT additive, reported beside the identity):
     exit  = joined order row target_w == 0.0 exactly
     clamp = symbol in the anchor's reshape.clamped_after_reshape.names, reshape.forced_flat_names or
             external_book.held_exit
D6 Anchor classes (fields known before the anchor trades):
     rho_pre = Σ over symbols of |prev_w| from attempt-1 maker rows, one row per (rebalance_id, symbol) (first row).
               prev_w = pre-trade venue notional / target gross (executor plan(), binance_executor.py:801-803).
     REBUILD  iff not HALTED and rho_pre < 0.50. Sub-type RESUME iff the previous nominal anchor was halted (opening_halted true) or a
              FLATTEN batch lies between the previous nominal anchor and this one; otherwise STEP_UP.
     HALTED   iff anchors.jsonl opening_halted is true.
     Sensitivity thresholds reported, not used for conclusions: 0.25 and 0.75.
D7 Periods (team-lead brief): P1 [08-28 00Z, 09-03 00Z), P2 [09-03 00Z, 09-08 00Z), P3 [09-08 00Z, 09-13 12Z].
   Driver sub-periods (declared here, before computing): S1a [08-28 00Z, 09-01 16Z) pre chase restart / eps 0.50;
   S1b [09-01 16Z, 09-03 00Z); S2a [09-03 00Z, 09-05 12Z) incl. deposit step-up and gross 2.0; S2b [09-05 12Z,
   09-08 00Z) requote randomisation live; S3 = P3.
D8 Period statistics: sums over anchors (notional-weighted), plus the median of per-anchor maker share over anchors
   with D > 0. Reported twice: all anchors, and excluding REBUILD anchors. Halted anchors are counted and listed.
   Component share c_k = K_k / D; Σ_k c_k = T / D = 1 - maker share exactly. Δ against S1a per component, exact sum.
D9 Driver indicators (pooled over arms unless the arm IS the component):
     chase restart        K3ci share; count of in_sample anchors; Σ chase_experiment.arm_counts
     requote experiment   K2d share; counts of from_reject topup rows by requote_arm (counts only)
     post-only rejects    first-attempt -5022 plans / attempt-1 plans (attempt_idx 1, maker, terminal venue_reject,
                          note contains "[-5022]"), one plan per (rebalance_id, symbol)
     residual size        from_partial topup rows: Σ|intended_residual| by terminal_reason group
                          (sent = filled/filled_amount_unknown/abandoned_max_attempts/venue_reject;
                          skipped_min_notional; skipped_no_chase_arm; skipped_unknown_fill; blocked_by_halt; other),
                          each divided by maker intent (Σ|intended_full| over attempt-1 plans)
     scale                target_gross / external_book.n_names per anchor (median per period); gross_mult
     pooled maker fill    M_maker / maker intent (pooled over placement arms; any link to eps is INFERRED only)
     rebuilds             maker share with and without REBUILD anchors; REBUILD anchors' share of T
D10 Fees: commission summed by component for commission_asset USDT; BNB rows counted, not converted.
D11 Input binding: guarded sha256 (dataless flag checked, bytes read == st_size) of every input file at start and end;
    any change => exit 4 (run invalid). Self sha256 printed and written.

Usage: python3 x_cost_decompose.py <receipts_dir>
Exit codes: 0 ok; 2 input missing/dataless/short read; 3 identity violated; 4 inputs changed during run; 5 barrier.
"""
import hashlib
import json
import os
import stat
import sys
import time
from collections import defaultdict
from statistics import median

ROOT = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
DAYS = [f"202608{d:02d}" for d in range(28, 32)] + [f"202609{d:02d}" for d in range(1, 14)]
import calendar


def _utc(y, mo, d, h=0):
    return calendar.timegm((y, mo, d, h, 0, 0))


T0 = _utc(2026, 8, 28)            # 2026-08-28T00:00:00Z
T_END = _utc(2026, 9, 13, 12)     # 2026-09-13T12:00:00Z (inclusive)
H4 = 14400
BOUNDS = {"P1": (_utc(2026, 8, 28), _utc(2026, 9, 3)),            # [08-28 00Z, 09-03 00Z)
          "P2": (_utc(2026, 9, 3), _utc(2026, 9, 8)),             # [09-03 00Z, 09-08 00Z)
          "P3": (_utc(2026, 9, 8), T_END + 1)}                    # [09-08 00Z, 09-13 12Z]
SUB = {"S1a": (_utc(2026, 8, 28), _utc(2026, 9, 1, 16)),          # pre chase restart / eps 0.50
       "S1b": (_utc(2026, 9, 1, 16), _utc(2026, 9, 3)),
       "S2a": (_utc(2026, 9, 3), _utc(2026, 9, 5, 12)),           # deposit step-up, gross 2.0
       "S2b": (_utc(2026, 9, 5, 12), _utc(2026, 9, 8)),           # requote randomisation live
       "S3": (_utc(2026, 9, 8), T_END + 1)}
REBUILD_RHO = 0.50
RHO_SENS = (0.25, 0.75)

FORBIDDEN = ("mid_at_fill_plus_60s", "fill_px", "avg_fill_px", "mid_at_anchor", "mid_at_submit", "price_submit", "intended_limit_px", "spread_at_submit_bps", "placement_arm", "placement_eps", "mark_ts_actual", "mark_lag_s", "neutrality_price", "mid_at_anchor_vector", "request_ledger", "first_fill_ts", "last_fill_ts")
ALLOW_ORDERS = ("anchor_ts", "rebalance_id", "symbol", "side", "order_type", "attempt_idx", "topup_source",
                "terminal_reason", "filled_notional", "filled_known_notional", "intended_notional",
                "intended_residual", "intended_full", "target_w", "prev_w", "chase_arm", "chase_arm_assigned",
                "requote_arm", "fee_paid", "note")
ALLOW_FILLS = ("trade_id", "symbol", "rebalance_id", "order_type", "attempt_idx", "anchor_ts", "fill_notional",
               "commission", "commission_asset", "venue_maker_flag", "side")
ALLOW_ANCH = ("anchor_ts", "rebalance_id", "opening_halted", "target_gross", "realized_gross", "venue_gross_usdt")
ALLOW_EB = ("nominal_ts", "gross_mult", "n_names", "held_exit")
ALLOW_CE = ("in_sample", "excluded_because", "weights", "arm_counts", "n_in_population", "n_randomised",
            "n_forced_by_neutrality", "residual_gross_usdt", "arm_notional_usdt", "book_gross_usdt")
COMPONENTS = ("K2d", "K2q", "K2e", "K2n", "K3ci", "K3co", "K3f", "K3nc", "K3n", "K4", "K5", "K6", "K7")
COMP_LABEL = {
    "K2d": "from_reject top-up, requote arm = direct",
    "K2q": "from_reject top-up, requote arm = requote (refused again or not rested)",
    "K2e": "from_reject top-up, requote arm = exempt (reduce-only)",
    "K2n": "from_reject top-up, no requote arm (before 09-05 12Z or not assigned)",
    "K3ci": "from_partial top-up, chase arm, anchor in_sample",
    "K3co": "from_partial top-up, chase arm, anchor NOT in_sample (fallback: everyone chases)",
    "K3f": "from_partial top-up, chase_forced (neutrality fill set)",
    "K3nc": "from_partial top-up, no_chase arm (should be 0)",
    "K3n": "from_partial top-up, no chase arm recorded",
    "K4": "top-up row without topup_source",
    "K5": "maker-type order filled as taker (post-only should prevent)",
    "K6": "top-up fill with no order row",
    "K7": "other order_type",
}


def _barrier_selfcheck():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    bad = {}
    for tok in FORBIDDEN:
        n = src.count('"' + tok + '"')
        n1 = src.count("'" + tok + "'")
        if n != 1 or n1 != 0:
            bad[tok] = (n, n1)
    for tok in FORBIDDEN:
        if tok in ALLOW_ORDERS + ALLOW_FILLS + ALLOW_ANCH + ALLOW_EB + ALLOW_CE:
            bad[tok] = "in allow-list"
    if bad:
        print(f"BARRIER VIOLATION {bad}")
        sys.exit(5)
    return {"forbidden_tokens": len(FORBIDDEN), "each_quoted_exactly_once": True}


def guarded_sha(p):
    st = os.stat(p)
    if st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000):
        raise SystemExit(f"REFUSE dataless {p}")
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    if n != st.st_size:
        raise SystemExit(f"REFUSE short read {p} {n}/{st.st_size}")
    return h.hexdigest(), n


def proj(r, allow):
    return {k: r[k] for k in allow if k in r}


def read_rows(path, allow, anomalies, tag):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                anomalies.append(f"{tag}:{i}:unparsable"); continue
            if not isinstance(r, dict):
                anomalies.append(f"{tag}:{i}:not_a_dict"); continue
            pr = proj(r, allow)
            if tag.startswith("anchors"):
                eb = r.get("external_book") if isinstance(r.get("external_book"), dict) else {}
                ce = r.get("chase_experiment") if isinstance(r.get("chase_experiment"), dict) else {}
                rs = r.get("reshape") if isinstance(r.get("reshape"), dict) else {}
                pr["_eb"] = proj(eb, ALLOW_EB)
                pr["_ce"] = proj(ce, ALLOW_CE)
                cap = rs.get("clamped_after_reshape") if isinstance(rs.get("clamped_after_reshape"), dict) else {}
                pr["_clamp_names"] = sorted(set(cap.get("names") or []) | set(rs.get("forced_flat_names") or [])
                                            | set(eb.get("held_exit") or []))
            pr["_line"] = i
            out.append(pr)
            del r
    return out


def fnum(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def slot_of(ts):
    return int(float(ts) // H4 * H4)


def label(ts, table):
    for k, (a, b) in table.items():
        if a <= ts < b:
            return k
    return None


def main(outdir):
    t_start = time.time()
    barrier = _barrier_selfcheck()
    self_sha, _ = guarded_sha(os.path.abspath(__file__))
    inputs = []
    for d in DAYS:
        for t in ("orders", "fills", "anchors"):
            p = os.path.join(ROOT, d, f"{t}.jsonl")
            if os.path.exists(p):
                inputs.append(p)
    sha0 = {p: guarded_sha(p) for p in inputs}
    anomalies = []

    # ---------------- anchors ----------------
    anchors = {}          # rid -> record
    nominal_rows = {}     # nominal -> rid (last row wins; duplicates counted)
    dup_nominal = 0
    for d in DAYS:
        for r in read_rows(os.path.join(ROOT, d, "anchors.jsonl"), ALLOW_ANCH, anomalies, f"anchors:{d}"):
            rid = r.get("rebalance_id")
            nts = fnum(r["_eb"].get("nominal_ts"))
            src = "external_book.nominal_ts"
            if nts is None and fnum(r.get("anchor_ts")) is not None:
                nts, src = float(slot_of(r["anchor_ts"])), "floor(anchor_ts)"
            if nts is None:
                anomalies.append(f"anchors:{d}:{rid}:no_time"); continue
            nts = int(nts)
            if nts in nominal_rows:
                dup_nominal += 1
            nominal_rows[nts] = rid
            anchors[rid] = {"rid": rid, "nominal": nts, "nominal_src": src, "halted": r.get("opening_halted") is True,
                            "target_gross": fnum(r.get("target_gross")), "realized_gross": fnum(r.get("realized_gross")),
                            "gross_mult": fnum(r["_eb"].get("gross_mult")), "n_names": r["_eb"].get("n_names"),
                            "ce": r["_ce"], "clamp_names": set(r["_clamp_names"])}

    # ---------------- orders ----------------
    topup_rows = defaultdict(list)     # (rid, sym) -> rows
    plans = {}                         # (rid, sym) -> first attempt-1 maker row
    reject_plans = set()
    rid_time_from_orders = {}
    resid_pool = defaultdict(lambda: defaultdict(float))   # rid -> terminal group -> Σ|intended_residual|
    topup_counts = defaultdict(lambda: defaultdict(int))  # rid -> "src:arm:terminal" -> count
    maker_intent = defaultdict(float)
    for d in DAYS:
        for r in read_rows(os.path.join(ROOT, d, "orders.jsonl"), ALLOW_ORDERS, anomalies, f"orders:{d}"):
            rid, sym, ot = r.get("rebalance_id"), r.get("symbol"), r.get("order_type")
            if fnum(r.get("anchor_ts")) is not None and rid not in rid_time_from_orders:
                rid_time_from_orders[rid] = slot_of(r["anchor_ts"])
            if ot == "topup_taker":
                topup_rows[(rid, sym)].append(r)
                src = r.get("topup_source")
                arm = r.get("chase_arm") or r.get("chase_arm_assigned")
                term = r.get("terminal_reason")
                key = f"{src}:{r.get('requote_arm') if src == 'from_reject' else arm}:{term}"
                topup_counts[rid][key] += 1
                if src == "from_partial":
                    ir = fnum(r.get("intended_residual"))
                    if ir is None:
                        ir = fnum(r.get("intended_notional"))
                    g = ("sent" if term in ("filled", "filled_amount_unknown", "abandoned_max_attempts", "venue_reject")
                         else term if term in ("skipped_min_notional", "skipped_no_chase_arm", "skipped_unknown_fill",
                                               "blocked_by_halt") else "other")
                    resid_pool[rid][g] += abs(ir or 0.0)
            elif ot == "maker" and r.get("attempt_idx") == 1:
                k = (rid, sym)
                if k not in plans:
                    plans[k] = r
                    fi = fnum(r.get("intended_full"))
                    if fi is None:
                        fi = fnum(r.get("intended_notional"))
                    maker_intent[rid] += abs(fi or 0.0)
                if r.get("terminal_reason") == "venue_reject" and "[-5022]" in str(r.get("note") or ""):
                    reject_plans.add(k)

    rho_pre = defaultdict(float); n_plans = defaultdict(int); n_rej = defaultdict(int)
    for (rid, sym), r in plans.items():
        rho_pre[rid] += abs(fnum(r.get("prev_w")) or 0.0)
        n_plans[rid] += 1
        if (rid, sym) in reject_plans:
            n_rej[rid] += 1

    def nominal_of(rid, fallback_ts=None):
        if rid in anchors:
            return anchors[rid]["nominal"], anchors[rid]["nominal_src"]
        if isinstance(rid, str) and rid.startswith("FLATTEN-"):
            try:
                t = time.strptime(rid[len("FLATTEN-"):], "%Y%m%dT%H%M%SZ")
                return slot_of(calendar.timegm(t)), "FLATTEN rid time"
            except ValueError:
                pass
        if rid in rid_time_from_orders:
            return rid_time_from_orders[rid], "floor(orders.anchor_ts)"
        if fallback_ts is not None and fnum(fallback_ts) is not None:
            return slot_of(fallback_ts), "floor(fills.anchor_ts)"
        return None, "unmapped"

    # ---------------- fills ----------------
    last = {}; order = []; no_tid = []; tid_syms = defaultdict(set); n_fill_rows = 0
    for d in DAYS:
        for r in read_rows(os.path.join(ROOT, d, "fills.jsonl"), ALLOW_FILLS, anomalies, f"fills:{d}"):
            n_fill_rows += 1
            tid = r.get("trade_id")
            if tid is None:
                no_tid.append(r); continue
            key = (r.get("symbol"), str(tid))
            tid_syms[str(tid)].add(r.get("symbol"))
            if key not in last:
                order.append(key)
            last[key] = r
    tid_collisions = sum(1 for s in tid_syms.values() if len(s) > 1)
    fills = [last[k] for k in order] + no_tid

    per = {}   # nominal -> stats
    ambiguous = 0; unmapped = 0; map_src = defaultdict(int)

    def stat_for(nominal):
        if nominal not in per:
            per[nominal] = {"M": 0.0, "M_maker": 0.0, "M_topup": 0.0, "T": 0.0, "K1": 0.0,
                            **{k: 0.0 for k in COMPONENTS}, "tag_exit_T": 0.0, "tag_clamp_T": 0.0,
                            "fee_usdt": defaultdict(float), "n_bnb_rows": 0, "n_taker_fills": 0, "n_maker_fills": 0}
        return per[nominal]

    for f in fills:
        rid, sym, ot = f.get("rebalance_id"), f.get("symbol"), f.get("order_type")
        nominal, src = nominal_of(rid, f.get("anchor_ts"))
        map_src[src] += 1
        if nominal is None:
            unmapped += 1; continue
        if not (T0 <= nominal <= T_END):
            continue
        s = stat_for(nominal)
        notional = abs(fnum(f.get("fill_notional")) or 0.0)
        maker = f.get("venue_maker_flag") is True
        fee = fnum(f.get("commission")) or 0.0
        asset = f.get("commission_asset")
        if ot == "protective_flatten":
            if not maker:
                s["K1"] += notional
            comp = "K1"
        elif ot in ("maker", "topup_taker"):
            if maker:
                s["M"] += notional; s["n_maker_fills"] += 1
                if ot == "maker":
                    s["M_maker"] += notional
                else:
                    s["M_topup"] += notional
                comp = "M"
            else:
                s["T"] += notional; s["n_taker_fills"] += 1
                if ot == "maker":
                    comp = "K5"
                else:
                    rows = topup_rows.get((rid, sym)) or []
                    if not rows:
                        comp = "K6"
                    else:
                        nonzero = [x for x in rows if abs(fnum(x.get("filled_notional")) or 0.0) > 0.0]
                        base = nonzero[0] if nonzero else rows[0]
                        sig = {(x.get("topup_source"), x.get("requote_arm"), x.get("chase_arm") or x.get("chase_arm_assigned")) for x in rows}
                        if len(sig) > 1:
                            ambiguous += 1
                        srcv = base.get("topup_source")
                        if srcv is None:
                            comp = "K4"
                        elif srcv == "from_reject":
                            ra = base.get("requote_arm")
                            comp = {"direct": "K2d", "requote": "K2q", "exempt": "K2e"}.get(ra, "K2n")
                        elif srcv == "from_partial":
                            arm = base.get("chase_arm") or base.get("chase_arm_assigned")
                            if arm == "chase":
                                ins = (anchors.get(rid) or {}).get("ce", {}).get("in_sample") is True
                                comp = "K3ci" if ins else "K3co"
                            elif arm == "chase_forced":
                                comp = "K3f"
                            elif arm == "no_chase":
                                comp = "K3nc"
                            else:
                                comp = "K3n"
                        else:
                            comp = "K4"
                        if fnum(base.get("target_w")) == 0.0:
                            s["tag_exit_T"] += notional
                    if sym in (anchors.get(rid) or {}).get("clamp_names", set()):
                        s["tag_clamp_T"] += notional
                s[comp] += notional
        else:
            if not maker:
                s["K7"] += notional; s["T"] += notional; s["n_taker_fills"] += 1
            comp = "K7"
        if asset == "USDT":
            s["fee_usdt"][comp] += fee
        elif asset == "BNB":
            s["n_bnb_rows"] += 1

    # ---------------- per-anchor records + identity ----------------
    halted_nominals = {a["nominal"] for a in anchors.values() if a["halted"]}
    flatten_slots = set()
    for f in fills:
        rid = f.get("rebalance_id")
        if isinstance(rid, str) and rid.startswith("FLATTEN-"):
            flatten_slots.add(rid)
    flatten_times = []
    for rid in flatten_slots:
        try:
            flatten_times.append(calendar.timegm(time.strptime(rid[len("FLATTEN-"):], "%Y%m%dT%H%M%SZ")))
        except ValueError:
            pass
    recs = []
    nominal_to_rid = {a["nominal"]: a["rid"] for a in anchors.values()}
    all_nominals = sorted(set(per) | {a["nominal"] for a in anchors.values() if T0 <= a["nominal"] <= T_END})
    worst_identity = 0.0
    for n in all_nominals:
        if not (T0 <= n <= T_END):
            continue
        s = stat_for(n)
        comp_sum = sum(s[k] for k in COMPONENTS)
        idiff = abs(s["T"] - comp_sum)
        worst_identity = max(worst_identity, idiff)
        rid = nominal_to_rid.get(n)
        a = anchors.get(rid) or {}
        rho = rho_pre.get(rid) if rid in rho_pre else None
        prev_n = n - H4
        resume = (prev_n in halted_nominals) or any(prev_n < t <= n + 1800 for t in flatten_times)
        halted = bool(a.get("halted"))
        rebuild = (not halted) and rho is not None and rho < REBUILD_RHO
        D = s["M"] + s["T"]
        pool = resid_pool.get(rid, {})
        recs.append({
            "nominal": n, "nominal_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(n)), "rid": rid,
            "period": label(n, BOUNDS), "sub": label(n, SUB),
            "halted": bool(a.get("halted")), "rho_pre": (round(rho, 6) if rho is not None else None),
            "rebuild": rebuild, "rebuild_type": (("RESUME" if resume else "STEP_UP") if rebuild else None),
            "rebuild_rho025": ((not halted) and rho is not None and rho < RHO_SENS[0]),
            "rebuild_rho075": ((not halted) and rho is not None and rho < RHO_SENS[1]),
            "target_gross": a.get("target_gross"), "gross_mult": a.get("gross_mult"), "n_names": a.get("n_names"),
            "in_sample": (a.get("ce") or {}).get("in_sample"), "arm_counts": (a.get("ce") or {}).get("arm_counts"),
            "M": round(s["M"], 6), "M_maker": round(s["M_maker"], 6), "M_topup": round(s["M_topup"], 6),
            "T": round(s["T"], 6), "D": round(D, 6), "maker_share": (round(s["M"] / D, 6) if D > 0 else None),
            "components": {k: round(s[k], 6) for k in COMPONENTS}, "K1_flatten_taker": round(s["K1"], 6),
            "tag_exit_T": round(s["tag_exit_T"], 6), "tag_clamp_T": round(s["tag_clamp_T"], 6),
            "identity_abs_diff": idiff,
            "fee_usdt_by_comp": {k: round(v, 6) for k, v in s["fee_usdt"].items()}, "n_bnb_fee_rows": s["n_bnb_rows"],
            "n_taker_fills": s["n_taker_fills"], "n_maker_fills": s["n_maker_fills"],
            "maker_intent": round(maker_intent.get(rid, 0.0), 6), "n_plans": n_plans.get(rid, 0),
            "n_first_5022": n_rej.get(rid, 0),
            "resid_pool": {k: round(v, 6) for k, v in pool.items()},
            "topup_counts": dict(topup_counts.get(rid, {})),
        })
    if worst_identity > 1e-6:
        print(f"IDENTITY VIOLATED worst {worst_identity}")
        sys.exit(3)

    # ---------------- aggregation ----------------
    def agg(rows):
        o = {"n_anchors": len(rows), "n_halted": sum(1 for r in rows if r["halted"]),
             "n_rebuild": sum(1 for r in rows if r["rebuild"]),
             "rebuild_list": [f"{r['nominal_utc']} {r['rebuild_type']} rho={r['rho_pre']}" for r in rows if r["rebuild"]]}
        M = sum(r["M"] for r in rows); T = sum(r["T"] for r in rows); D = M + T
        o.update({"M": round(M, 4), "T": round(T, 4), "D": round(D, 4), "maker_share": (round(M / D, 6) if D else None),
                  "taker_share": (round(T / D, 6) if D else None)})
        o["component_notional"] = {k: round(sum(r["components"][k] for r in rows), 4) for k in COMPONENTS}
        o["component_share"] = {k: (round(o["component_notional"][k] / D, 6) if D else None) for k in COMPONENTS}
        o["identity_share_residual"] = (abs(sum(o["component_notional"].values()) - T) / D) if D else None
        o["K1_flatten_taker"] = round(sum(r["K1_flatten_taker"] for r in rows), 4)
        o["tag_exit_T_share"] = (round(sum(r["tag_exit_T"] for r in rows) / D, 6) if D else None)
        o["tag_clamp_T_share"] = (round(sum(r["tag_clamp_T"] for r in rows) / D, 6) if D else None)
        shares = [r["maker_share"] for r in rows if r["maker_share"] is not None]
        o["median_anchor_maker_share"] = (round(median(shares), 6) if shares else None)
        o["min_anchor_maker_share"] = (round(min(shares), 6) if shares else None)
        o["max_anchor_maker_share"] = (round(max(shares), 6) if shares else None)
        mi = sum(r["maker_intent"] for r in rows)
        o["maker_intent"] = round(mi, 4)
        o["pooled_maker_fill_ratio"] = (round(sum(r["M_maker"] for r in rows) / mi, 6) if mi else None)
        npl = sum(r["n_plans"] for r in rows); nrj = sum(r["n_first_5022"] for r in rows)
        o["first_attempt_5022_rate"] = (round(nrj / npl, 6) if npl else None)
        pool = defaultdict(float)
        for r in rows:
            for k, v in r["resid_pool"].items():
                pool[k] += v
        o["resid_pool_over_maker_intent"] = {k: (round(v / mi, 6) if mi else None) for k, v in sorted(pool.items())}
        tc = defaultdict(int)
        for r in rows:
            for k, v in r["topup_counts"].items():
                tc[k] += v
        o["topup_row_counts"] = dict(sorted(tc.items()))
        tg = [r["target_gross"] / r["n_names"] for r in rows if r["target_gross"] and r["n_names"]]
        o["median_target_notional_per_name"] = (round(median(tg), 2) if tg else None)
        o["gross_mult_values"] = sorted({r["gross_mult"] for r in rows if r["gross_mult"] is not None})
        o["n_in_sample"] = sum(1 for r in rows if r["in_sample"] is True)
        fee = defaultdict(float)
        for r in rows:
            for k, v in r["fee_usdt_by_comp"].items():
                fee[k] += v
        o["fee_usdt_by_comp"] = {k: round(v, 4) for k, v in sorted(fee.items())}
        o["n_bnb_fee_rows"] = sum(r["n_bnb_fee_rows"] for r in rows)
        return o

    out = {"device": os.path.basename(__file__), "self_sha256": self_sha, "barrier": barrier,
           "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_start)),
           "window": ["2026-08-28T00:00Z", "2026-09-13T12:00Z"], "rebuild_rho": REBUILD_RHO,
           "bounds_epoch": {"periods": BOUNDS, "subperiods": SUB, "T0": T0, "T_END": T_END},
           "data_quality": {"n_fill_rows_read": n_fill_rows, "n_fills_dedup": len(fills), "n_rows_without_trade_id": len(no_tid),
                            "trade_ids_shared_by_two_symbols": tid_collisions, "ambiguous_topup_keys_hit": ambiguous,
                            "unmapped_fills": unmapped, "nominal_map_sources": dict(map_src), "duplicate_nominal_anchor_rows": dup_nominal,
                            "parse_anomalies": anomalies[:50], "n_parse_anomalies": len(anomalies),
                            "worst_identity_abs_diff_usdt": worst_identity},
           "periods": {}, "subperiods": {}, "periods_ex_rebuild": {}, "subperiods_ex_rebuild": {}, "sensitivity_rho": {}}
    for name, table, key in (("periods", BOUNDS, "period"), ("subperiods", SUB, "sub")):
        for lab in table:
            rows = [r for r in recs if r[key] == lab]
            out[name][lab] = agg(rows)
            out[name + "_ex_rebuild"][lab] = agg([r for r in rows if not r["rebuild"]])
            for thr, fld in ((RHO_SENS[0], "rebuild_rho025"), (RHO_SENS[1], "rebuild_rho075")):
                o = agg([r for r in rows if not r[fld]])
                out["sensitivity_rho"][f"{name}:{lab}:ex_rho<{thr}"] = {"maker_share": o["maker_share"], "n_anchors": o["n_anchors"]}
    base = out["subperiods"]["S1a"]
    out["delta_vs_S1a"] = {}
    for lab, o in list(out["subperiods"].items()) + [("P1", out["periods"]["P1"]), ("P2", out["periods"]["P2"]), ("P3", out["periods"]["P3"])]:
        if o["D"] and base["D"]:
            dd = {k: round(o["component_share"][k] - base["component_share"][k], 6) for k in COMPONENTS}
            out["delta_vs_S1a"][lab] = {"delta_taker_share": round(o["taker_share"] - base["taker_share"], 6),
                                        "delta_by_component": dd, "sum_check": round(sum(dd.values()) - (o["taker_share"] - base["taker_share"]), 9)}
    sha1 = {p: guarded_sha(p) for p in inputs}
    changed = [p for p in inputs if sha0[p] != sha1[p]]
    out["inputs"] = {p: {"sha256": sha0[p][0], "bytes": sha0[p][1]} for p in inputs}
    out["inputs_changed_during_run"] = changed
    os.makedirs(outdir, exist_ok=True)
    json.dump(recs, open(os.path.join(outdir, "x_cost_per_anchor.json"), "w"), indent=1, ensure_ascii=False, default=list)
    json.dump(out, open(os.path.join(outdir, "x_cost_periods.json"), "w"), indent=1, ensure_ascii=False, default=list)
    if changed:
        print(f"INPUTS CHANGED DURING RUN {changed}")
        sys.exit(4)
    print(f"SUMMARY x_cost_decompose anchors={len(recs)} fills_dedup={len(fills)} worst_identity={worst_identity:.3e} "
          f"collisions={tid_collisions} ambiguous={ambiguous} unmapped={unmapped} anomalies={len(anomalies)} "
          f"self_sha256={self_sha[:16]} rc=0")


if __name__ == "__main__":
    main(sys.argv[1])
