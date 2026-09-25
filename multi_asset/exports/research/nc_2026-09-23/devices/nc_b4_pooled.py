#!/usr/bin/env python3
"""Per-anchor acceptance B4 (executor) + B6 anchor_report, POOLED ONLY (blind state, memory rule 2026-09-19). READ-ONLY.
Blind-state mechanics: every key whose name contains "chase" or "arm" (case-insensitive) is DROPPED from each row as it is parsed, before
anything else reads the row; terminal-reason / order-type LABELS that name an arm are folded into one label "<arm-named label, pooled>";
anchor_report lines are printed only if they match the guard / sidecar / summary markers below and name no arm.
Input: nominal anchor A (unix, 4h grid). The executor's anchors row for A is the one whose anchor_ts (the rebalance wall time) is in
[A, A + 4h); orders are joined on rebalance_id. Unknown is not zero: a missing row / field prints MISSING and the exit code is 2.
B4 items (DEPLOY_producer_new_contract §B4): orders placed this anchor (n > 0); opening_halted; external_book ok; m3_beta_overlay
status == "shadow", field_ok == true, hedge_target_usdt finite; no order row carrying an overlay / hedge marker.
usage: /usr/bin/python3 nc_b4_pooled.py <A>"""
import collections, json, math, os, sys, time

A = int(sys.argv[1]); LIVE = os.path.expanduser("~/dl_quant_live/state")
bad = lambda k: "chase" in k.lower() or "arm" in k.lower()
clean = lambda d: {k: v for k, v in d.items() if not bad(k)} if isinstance(d, dict) else d
fold = lambda s: "<arm-named label, pooled>" if isinstance(s, str) and bad(s) else s


def rows(p):
    return [clean(json.loads(l)) for l in open(p) if l.strip()]


def main():
    miss = []
    day = time.strftime("%Y%m%d", time.gmtime(A)); D = f"{LIVE}/live/pilot_log/{day}"
    an = [r for r in rows(f"{D}/anchors.jsonl") if A <= float(r.get("anchor_ts") or 0) < A + 14400]
    if len(an) != 1:
        print(f"B4 anchors rows in [A, A+4h): {len(an)} (expected 1) — MISSING/AMBIGUOUS"); return 2
    a = an[0]; rid = a.get("rebalance_id")
    od = [r for r in rows(f"{D}/orders.jsonl") if r.get("rebalance_id") == rid and rid is not None]
    term = collections.Counter(fold(r.get("terminal_reason")) for r in od)
    otype = collections.Counter(fold(r.get("order_type")) for r in od)
    marker = sum(1 for r in od if any(w in json.dumps(r).lower() for w in ("overlay", "hedge")))
    eb = clean(a.get("external_book") or {})
    print(f"B4 A={A} rebalance anchor_ts={a.get('anchor_ts')} rebalance_id={rid} opening_halted={a.get('opening_halted')} "
          f"external_book ok={eb.get('ok')} reason={eb.get('reason')} book_source={a.get('book_source')}")
    print(f"B4 orders {len(od)} | order_type {dict(otype)} | terminal {dict(term)}")
    print(f"B4 gross target {a.get('target_gross')} realized {a.get('realized_gross')} venue_gross {a.get('venue_gross_usdt')} "
          f"venue_net {a.get('venue_net_usdt')} net/gross {a.get('net_over_gross')}")
    m = clean(a.get("m3_beta_overlay"))
    if not isinstance(m, dict):
        print("B4 m3_beta_overlay MISSING"); miss.append("m3")
    else:
        h = m.get("hedge_target_usdt")
        print(f"B4 m3: mode {m.get('mode')} status {m.get('status')} field_ok {m.get('field_ok')} reason {m.get('field_reason') or m.get('reason')} "
              f"version_expected {m.get('version_expected')} n_betas {m.get('n_betas')} n_fallback {m.get('n_fallback')} data_cutoff_ts {m.get('data_cutoff_ts')} "
              f"betas_sha256 {str(m.get('betas_sha256'))[:16]} beta_exec_usdt {m.get('beta_exec_usdt')} hedge_target_usdt {h} "
              f"shadow_would_be {str(m.get('shadow_would_be'))[:80]}")
        if not (m.get("status") == "shadow" and m.get("field_ok") is True and isinstance(h, (int, float)) and math.isfinite(h)): miss.append("m3 not shadow/field_ok/finite")
    print(f"B4 orders with an overlay/hedge marker: {marker}")
    if not od: miss.append("no orders this anchor")
    if marker: miss.append("overlay/hedge order present")
    rp = f"{LIVE}/anchor_report_last.json"
    r = clean(json.load(open(rp)))
    ls = [l for l in (r.get("lines") or []) if isinstance(l, str) and not bad(l) and any(w in l for w in ("守护", "侧车", "w3m", "gross", "fund_upd", "排查"))]
    print(f"B6 anchor_report anchor_ts {r.get('anchor_ts')} status {r.get('status')} utc {r.get('utc')} warn(non-arm) "
          f"{[w for w in (r.get('warn') or []) if not bad(str(w))]}")
    for l in ls: print("   ", l[:200])
    if int(r.get("anchor_ts") or 0) != A: miss.append("anchor_report not for A")
    print("B4_POOLED", "OK" if not miss else "RED", miss)
    return 0 if not miss else 2


if __name__ == "__main__":
    sys.exit(main())
