#!/usr/bin/env python3
"""FX-W6C device — replay a REAL watchdog trip as the watchdog saw it, then apply the proportional gate.

> 创建: 2026-09-13 14:4xZ | Session: FX-W6C (fix worker, EXE-01) | 状态: 测量装置(只读; 写 scratch 与 --out) | 作废条件: 门的规格改变

WHAT IT DOES (no venue, no credentials, no network; the snapshot is a COPY of the live pilot_log):
  1. copy the snapshot's pilot_log days <= the trip day into a scratch tree, dropping every row whose own time key is at or
     after the trip instant (orders/anchors: anchor_ts; position_readback: read_ts else anchor_ts; fills: fill_ts else
     anchor_ts, and rows back-filled at/after the trip; daily_nav: nav_ts; funding: settlement_ts). Same rule as
     tests_reduce_only_clamp T9a ("the 12Z readback in, the ladder's readback/rows out"), applied to every table.
  2. in a SUBPROCESS whose sys.path is --code-tree only (so two code versions never mix), run the production evaluation path
     without the network probe: ops = watchdog_inputs.derive_ops_stats(tree); ev = watchdog.evaluate(tree, [], ops); plus
     reconcile.reconcile over the same days for the FULL latest anomaly list (ev carries only 3 examples).
  3. apply the gate — by default the PROTOTYPE below (written before any executor code, fact table §8); with
     --gate-tree <fixed clone> ALSO the production `watchdog.proportional_gate` on the same evaluation, and report agreement.

THE GATE (prototype; the spec the production code must reproduce):
  scope per trigger: §4-5b → the symbols of reconcile.latest; §4-7 un-recovered drift → the same symbols (ops[-1] drift_names
  when present, else reconcile.latest in this device); §4-5e split_unauth → split_verdict.unauth_names ONLY when the per-name
  clause fired and the portfolio clause did not; EVERY other trigger (and any §4-5e by another gate) → BOOK.
  any BOOK trigger ⇒ LADDER.  names = union; > 5 ⇒ LADDER.
  at-stake(name) = the size of the DOUBT, in the frozen R-14 measure and its analogues — max over the finite terms:
  Σ|intended| over ALL unquantifiable rows of the name in the interval (execution_of_unknown_size; R-14's own measure, joint
  so row order cannot change it; unknown if any row's intended is unreadable), |residual_usdt| (quantity_residual: the
  unexplained part after the authorised band), |unauth_usdt| (§4-5e per-name). The name's whole position is NOT a term: it is
  what the local action removes, not the size of the doubt (its readback notional is reported beside, informational).
  gross = the anchors row's target_gross at/before the reconciled anchor (R-14's frozen denominator); ONLY when that is
  missing / non-finite / <= 0, Σ|readback notional| at that anchor (None if any row is non-finite).
  Σ known at-stake > 2% × gross (gross known) ⇒ LADDER; otherwise LOCAL, with every unknown term named.

Usage:
  python3 -B trip_gate_replay.py --code-tree /Users/haosiyu/cc_tmp/fx_w6c_918559f \
      --snapshot /Users/haosiyu/cc_tmp/fx_w6c_state_snapshot/live/pilot_log --trip-utc 2026-09-12T12:47:37Z --out r.json
"""
import argparse
import calendar
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

MAX_NAMES = 5
MAX_FRAC = 0.02


def _t(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _time_key(table, r):
    if table == "position_readback":
        return _t(r.get("read_ts")) if r.get("read_ts") is not None else _t(r.get("anchor_ts"))
    if table == "fills":
        return _t(r.get("fill_ts")) if r.get("fill_ts") is not None else _t(r.get("anchor_ts"))
    if table == "daily_nav":
        return _t(r.get("nav_ts"))
    if table == "funding":
        v = _t(r.get("settlement_ts"))
        return (v / 1000.0) if (v is not None and v > 1e11) else v
    return _t(r.get("anchor_ts"))


def truncate(snapshot, trip_ts, out_root):
    trip_day = time.strftime("%Y%m%d", time.gmtime(trip_ts))
    kept = {}
    for day in sorted(os.listdir(snapshot)):
        if not (len(day) == 8 and day.isdigit()) or day > trip_day:
            continue
        src, dst = os.path.join(snapshot, day), os.path.join(out_root, day)
        os.makedirs(dst)
        for name in sorted(os.listdir(src)):
            p = os.path.join(src, name)
            if not name.endswith(".jsonl"):
                shutil.copy2(p, os.path.join(dst, name))
                continue
            table = name[:-len(".jsonl")]
            n_in = n_out = 0
            with open(p, encoding="utf-8") as fi, open(os.path.join(dst, name), "w", encoding="utf-8") as fo:
                for line in fi:
                    if not line.strip():
                        continue
                    n_in += 1
                    r = json.loads(line)
                    k = _time_key(table, r)
                    bf = r.get("backfilled_utc")
                    if bf:
                        try:
                            if calendar.timegm(time.strptime(str(bf)[:19], "%Y-%m-%dT%H:%M:%S")) >= trip_ts:
                                continue
                        except ValueError:
                            pass
                    if k is not None and k >= trip_ts:
                        continue
                    fo.write(line if line.endswith("\n") else line + "\n")
                    n_out += 1
            kept[f"{day}/{table}"] = [n_in, n_out]
    return kept


_CHILD = r'''
import json, os, sys, math
tree, code = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(code, d))
import pilot_log as PL, reconcile as RC, watchdog as WD, watchdog_inputs as WI
days = PL.available_days(tree)
data = [(d, PL.read_day(tree, d)) for d in days]
ops = WI.derive_ops_stats(tree)
ev = WD.evaluate(tree, venue_events=[], ops_stats=ops)
rec = RC.reconcile(data)
last = rec["last_reconciled_ats"]
rb = {}; order_rb = []
for d, one in data:
    for r in one.get("position_readback", []):
        rb.setdefault(float(r["anchor_ts"]), {})[r["symbol"]] = r
for ats in sorted(rb):
    order_rb.append(ats)
prev = order_rb[order_rb.index(last) - 1] if (last in order_rb and order_rb.index(last) > 0) else None
t_prev = max(float(r.get("read_ts") or r["anchor_ts"]) for r in rb[prev].values()) if prev is not None else None
t_cur = max(float(r.get("read_ts") or r["anchor_ts"]) for r in rb[last].values()) if last is not None else None
joint = {}
for d, one in data:
    for o in one.get("orders", []):
        dq, why, kind = RC._exec_qty(o)
        if kind != "unquantifiable":
            continue
        t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
        if t is None or t_cur is None or not ((t_prev is None or float(t) > t_prev) and float(t) <= t_cur):
            continue
        it = o.get("intended_full") if o.get("intended_full") is not None else o.get("intended_notional")
        j = joint.setdefault(o["symbol"], {"n_rows": 0, "sum_abs_intended": 0.0, "complete": True, "rebalance_ids": []})
        j["n_rows"] += 1; j["rebalance_ids"].append(o.get("rebalance_id"))
        try:
            v = float(it)
            if not math.isfinite(v):
                raise ValueError
            j["sum_abs_intended"] += abs(v)
        except (TypeError, ValueError):
            j["complete"] = False
anchors = []
for d, one in data:
    for a in one.get("anchors", []):
        anchors.append({"anchor_ts": a.get("anchor_ts"), "target_gross": a.get("target_gross"), "rebalance_id": a.get("rebalance_id")})
c5 = ev["conditions"]["cond5_venue_event"]
pb = c5.get("5e_position_break") or {}
lt = pb.get("latest") or {}
sv = lt.get("split_verdict") or {}
out = {
  "code_tree": code, "days": [days[0], days[-1]] if days else [], "n_days": len(days),
  "tripped": ev["tripped"], "triggers": ev["triggers"], "conditions_blind": ev.get("conditions_blind"),
  "5b": {k: c5["5b_liquidation_anomaly"].get(k) for k in ("state", "n", "last_reconciled_anchor_ts", "n_historical_anomalies")},
  "rec_latest": [{k: a.get(k) for k in ("symbol", "kind", "residual_usdt", "residual_qty", "observed_qty", "expected_qty", "why", "rebalance_id", "order_type", "terminal_reason")} for a in rec["latest"]],
  "rec_last_reconciled_ats": last, "prev_readback_ats": prev, "t_prev": t_prev, "t_cur": t_cur,
  "readback_at_last": {s: {"notional": r.get("venue_position_notional"), "qty": r.get("venue_position_qty"), "source": r.get("source")} for s, r in (rb.get(last) or {}).items()},
  "joint_unquantifiable": joint,
  "5e": {"trip_gate": lt.get("trip_gate"), "anchor_ts": lt.get("anchor_ts"), "triggered": pb.get("triggered"),
         "unauth_portfolio_hit": sv.get("unauth_portfolio_hit"), "unauth_per_name_hit": sv.get("unauth_per_name_hit"),
         "unauth_frac": sv.get("unauth_frac"), "unauth_gross_usdt": sv.get("unauth_gross_usdt"), "target_gross": lt.get("target_gross"),
         "unauth_breaches": sv.get("unauth_breaches"), "n_unauth_names": len(sv.get("unauth_names") or [])},
  "readback_at_5e": {s: r.get("venue_position_notional") for s, r in (rb.get(float(lt["anchor_ts"])) or {}).items()} if lt.get("anchor_ts") is not None else {},
  "cond7": {k: ev["conditions"]["cond7_ops"].get(k) for k in ("unrecovered_drift", "drift_state", "triggered")},
  "ops_last": {k: (ops[-1] if ops else {}).get(k) for k in ("unrecovered_position_drift", "drift_names", "drift_last_reconciled_ats")},
  "anchors_tail": anchors[-6:],
  "proportional_response_prod": ev.get("proportional_response"),
  "local_responses_prod": ev.get("local_responses"),
}
print(json.dumps(out, default=str))
'''


def evaluate_in(code_tree, tree):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", LIVE_MODE="LIVE")
    env.pop("PYTHONPATH", None)
    p = subprocess.run([sys.executable, "-B", "-c", _CHILD, tree, code_tree], capture_output=True, text=True, env=env,
                       cwd=tempfile.gettempdir())
    if p.returncode != 0:
        raise SystemExit(f"evaluation subprocess failed rc={p.returncode}\n{p.stderr[-3000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def _cls(trigger):
    if trigger.startswith("§4-5b"):
        return "§4-5b"
    if trigger.startswith("§4-7 un-recovered"):
        return "§4-7drift"
    if trigger.startswith("§4-5e"):
        return "§4-5e"
    return "BOOK"


def gate_prototype(E, switch=True):
    why, book, per = [], [], {}
    names = set()
    latest = {a["symbol"]: a for a in E["rec_latest"]}
    for t in E["triggers"]:
        c = _cls(t)
        if c == "§4-5b":
            names |= set(latest)
        elif c == "§4-7drift":
            dn = E["ops_last"].get("drift_names")
            names |= set(dn if dn is not None else latest)
        elif c == "§4-5e":
            e5 = E["5e"]
            if e5.get("trip_gate") == "split_unauth" and e5.get("unauth_per_name_hit") and not e5.get("unauth_portfolio_hit"):
                names |= {b["symbol"] for b in (e5.get("unauth_breaches") or [])}
            else:
                book.append(t[:80])
        else:
            book.append(t[:80])
    unauth = {b["symbol"]: b.get("unauth_usdt") for b in (E["5e"].get("unauth_breaches") or [])}
    for s in sorted(names):
        terms, missing = {}, []
        rbn = (E["readback_at_last"].get(s) or {}).get("notional")
        info_rb = (abs(_t(rbn)) if _t(rbn) is not None else None)
        a = latest.get(s)
        if a is not None and a["kind"] == "quantity_residual":
            if _t(a.get("residual_usdt")) is not None:
                terms["residual_usdt"] = abs(_t(a["residual_usdt"]))
            else:
                missing.append("residual_usdt")
        if a is not None and a["kind"] == "execution_of_unknown_size":
            j = E["joint_unquantifiable"].get(s)
            if j and j["complete"]:
                terms["intended_joint"] = j["sum_abs_intended"]
            else:
                missing.append("intended_joint")
        if s in unauth:
            if _t(unauth[s]) is not None:
                terms["unauth_usdt"] = abs(_t(unauth[s]))
            else:
                missing.append("unauth_usdt")
        per[s] = {"terms": terms, "missing": missing, "at_stake_usdt": (max(terms.values()) if terms else None),
                  "readback_notional_info": info_rb}
    tg, tg_at = None, None
    last = E["rec_last_reconciled_ats"]
    for a in E["anchors_tail"]:
        at, g = _t(a.get("anchor_ts")), _t(a.get("target_gross"))
        if at is None or g is None or g <= 0 or last is None or at > float(last) + 1e-9:
            continue
        if tg_at is None or at >= tg_at:
            tg, tg_at = g, at
    vals = [_t(v.get("notional")) for v in E["readback_at_last"].values()]
    realized = (sum(abs(v) for v in vals) if vals and all(v is not None for v in vals) else None)
    realized = realized if (realized is not None and realized > 0) else None
    gross = tg if tg is not None else realized
    s_known = sum(v["at_stake_usdt"] for v in per.values() if v["at_stake_usdt"] is not None)
    unknown = [f"{s}: at-stake unknown" for s, v in per.items() if v["at_stake_usdt"] is None] + \
              [f"{s}: term(s) unreadable {v['missing']}" for s, v in per.items() if v["missing"] and v["at_stake_usdt"] is not None] + \
              (["gross reference unknown"] if gross is None else [])
    if not switch:
        verdict = "LADDER"; why.append("switch off")
    elif book:
        verdict = "LADDER"; why.append(f"book-level trigger(s): {book}")
    elif not names:
        verdict = "LADDER"; why.append("no named scope")
    elif len(names) > MAX_NAMES:
        verdict = "LADDER"; why.append(f"{len(names)} names > {MAX_NAMES}")
    elif gross is not None and s_known > MAX_FRAC * gross:
        verdict = "LADDER"; why.append(f"Σ at-stake {s_known:.2f} USDT = {s_known / gross:.4%} of gross {gross:.2f} > {MAX_FRAC:.0%}")
    else:
        verdict = "LOCAL"; why.append(f"{len(names)} name(s), Σ at-stake {s_known:.2f} USDT"
                                      + (f" = {s_known / gross:.4%} of gross {gross:.2f}" if gross else " (gross unknown)")
                                      + (f"; UNKNOWN inputs {unknown}" if unknown else ""))
    return {"verdict": verdict, "why": why, "n_names": len(names), "names": sorted(names)[:60], "per_name": per if len(per) <= 12 else {"_n": len(per)},
            "sum_at_stake_usdt_known": s_known, "gross_target": tg, "gross_realized_readback": realized, "gross_ref": gross,
            "frac": (s_known / gross if gross else None), "unknown_inputs": unknown, "book_triggers": book}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-tree", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--trip-utc", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    trip_ts = float(calendar.timegm(time.strptime(a.trip_utc, "%Y-%m-%dT%H:%M:%SZ")))
    work = tempfile.mkdtemp(prefix="fxw6c_replay_")
    tree = os.path.join(work, "pilot_log")
    os.makedirs(tree)
    kept = truncate(a.snapshot, trip_ts, tree)
    E = evaluate_in(a.code_tree, tree)
    G = gate_prototype(E, switch=True)
    self_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    rep = {"device": os.path.abspath(__file__), "device_sha256": self_sha, "trip_utc": a.trip_utc, "trip_ts": trip_ts,
           "snapshot": a.snapshot, "code_tree": a.code_tree, "rows_kept_by_table_trip_day": {k: v for k, v in kept.items() if k.startswith(time.strftime("%Y%m%d", time.gmtime(trip_ts)))},
           "evaluation": E, "gate_prototype": G}
    json.dump(rep, open(a.out, "w"), indent=1, default=str)
    print(json.dumps({"trip": a.trip_utc, "code": a.code_tree, "tripped": E["tripped"], "triggers": [t[:120] for t in E["triggers"]],
                      "5b": E["5b"], "rec_latest": [(x["symbol"], x["kind"], x.get("residual_usdt")) for x in E["rec_latest"]],
                      "5e": {k: E["5e"].get(k) for k in ("trip_gate", "unauth_portfolio_hit", "unauth_per_name_hit", "unauth_frac", "n_unauth_names")},
                      "cond7": E["cond7"], "gate": {k: G[k] for k in ("verdict", "why", "n_names", "sum_at_stake_usdt_known", "gross_target", "gross_realized_readback", "gross_ref", "frac", "unknown_inputs")},
                      "device_sha256": self_sha[:16]}, indent=1, default=str))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
