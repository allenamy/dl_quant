#!/usr/bin/env python3
"""First M3-ON anchor acceptance (FROZEN criteria ../ACCEPTANCE_m3_on_first_anchor.md dac8dbbc6). READ-ONLY, pooled, reads no arm field.
usage: /usr/bin/python3 m3_on_first_anchor.py <A nominal anchor ts> [--expect on|shadow] [--out F]
Every line prints MEASURED vs COMPARED; the last line is  M3_ON_FIRST_ANCHOR <A> expect=<m> VERDICT=PASS|PASS_WITH_WARN|UNDECIDED|FAIL ...
Plan-row caliber (live/binance_executor.py L806-820): target_w = target_notional / sum|target_notional| over the FINAL target, i.e. the record's
gross_final_target_usdt (beta_overlay.after_cap L463) — so target_i = target_w_i x gross_final_target_usdt in both modes."""
import argparse, collections, glob, json, math, os, re, sys, time

HOME = os.path.expanduser("~"); DQ = f"{HOME}/dl_quant_live"; WS = f"{HOME}/wide_shadow"; L = f"{DQ}/state/live/pilot_log"
sys.path.insert(0, f"{DQ}/live"); import pilot_log as PL          # noqa: E402 (collapse_supersedes only)
BTC = "BTCUSDT"; APPLIED = ("applied", "applied_via_combined"); ABSTAIN = ("budget_zero", "combined_dust", "refused")
LINES, RES = [], collections.OrderedDict()
fmt = lambda t: time.strftime("%m-%dT%H:%M:%SZ", time.gmtime(t))


def say(s): LINES.append(s); print(s, flush=True)


def verdict(k, v, detail=""):
    RES[k] = v; say(f"  {v:10s} {k}  {detail}")


def num(x):
    try:
        f = float(x); return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def jl(table, days):
    out = []
    for d in days:
        p = f"{L}/{d}/{table}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("A", type=int); ap.add_argument("--expect", choices=["on", "shadow", "rollback"], default="on")
    ap.add_argument("--out"); a = ap.parse_args(); A, E = a.A, a.expect
    days = sorted({time.strftime("%Y%m%d", time.gmtime(A + d)) for d in (-86400, 0, 86400)})
    say(f"M3 ON first-anchor acceptance A={A} ({fmt(A)}) expect={E}")
    if E == "rollback":
        return rollback(a, A, days)
    rows = [r for r in jl("anchors", days) if int((r.get("external_book") or {}).get("nominal_ts") or -1) == A]
    if not rows:
        verdict("F0 anchors row for A", "FAIL", "none"); return finish(a, E)
    r = rows[-1]; m = r.get("m3_beta_overlay") or {}; at = float(r["anchor_ts"]); rid = r.get("rebalance_id")
    book = json.load(open(f"{DQ}/config/book.json")).get("beta_overlay") or {}
    tl = json.load(open(f"{WS}/state/target_live/{A}.json")); F = tl.get("beta_overlay") or {}
    # F1
    ok1 = (book.get("mode") == E and book.get("max_combined_leverage") == 2.5 and F.get("version") == "m3_beta_v2"
           and F.get("anchor_ts") == A and F.get("data_cutoff_ts") == A and m.get("mode") == E
           and m.get("version_expected") == "m3_beta_v2" and m.get("field_ok") is True)
    verdict("F1 config / versions", "PASS" if ok1 else "FAIL",
            f"book.mode={book.get('mode')} cap={book.get('max_combined_leverage')} field.version={F.get('version')} field.anchor/cutoff="
            f"{F.get('anchor_ts')}/{F.get('data_cutoff_ts')} rec.mode={m.get('mode')} rec.version_expected={m.get('version_expected')} field_ok={m.get('field_ok')}")
    # F2
    st = m.get("status")
    if E == "shadow":
        verdict("F2 status", "PASS" if st == "shadow" else "FAIL", f"status={st} shadow_would_be={m.get('shadow_would_be')}")
    else:
        verdict("F2 status", "PASS" if st in APPLIED else ("UNDECIDED" if st in ABSTAIN or "suspend" in str(st) else "FAIL"),
                f"status={st} reason={m.get('reason')} hedge_gap_usdt={m.get('hedge_gap_usdt')} hedge_gap_reason={m.get('hedge_gap_reason')}")
    # F3
    orders = jl("orders", days); plan = {}
    for o in orders:
        if o.get("rebalance_id") != rid: continue
        s = o.get("symbol"); w = num(o.get("target_w"))
        if w is None: continue
        plan.setdefault(s, w)
    S = num(m.get("gross_final_target_usdt")); G = num(m.get("book_gross_usdt")); be = num(m.get("beta_exec_usdt"))
    btc_book = num(m.get("btc_book_target_usdt")) or 0.0; comb = num(m.get("btc_combined_target_usdt")); hed = num(m.get("hedge_target_usdt"))
    intent = num(m.get("hedge_intent_usdt")); scale = num((m.get("budget") or {}).get("scale"))
    betas = F.get("betas") or {}
    c = {}
    if S and G:
        nonbtc = {s: w for s, w in plan.items() if s != BTC}
        c["c1"] = abs(sum(abs(w) * S for w in nonbtc.values()) / G + abs(btc_book) / G - 1.0) <= 1e-9 if E == "on" else abs(sum(abs(w) for w in plan.values()) - 1.0) <= 1e-9
        bt = plan.get(BTC, 0.0) * S
        c["c2"] = math.isclose(bt, comb if E == "on" else btc_book, rel_tol=1e-9, abs_tol=1e-6)
        book_t = {s: w * S for s, w in nonbtc.items()}; book_t[BTC] = btc_book
        miss = [s for s, v in book_t.items() if v != 0.0 and s not in betas and s != BTC]
        recon = sum(v * (1.0 if s == BTC else float(betas[s])) for s, v in book_t.items() if s in betas or s == BTC) if not miss else None
        c["c3"] = recon is not None and be is not None and math.isclose(recon, be, rel_tol=1e-9, abs_tol=1e-6)
        c["c4"] = (intent is not None and be is not None and abs(intent + be) <= 1e-6 and hed is not None and scale is not None
                   and abs(hed - intent * scale) <= 1e-6 and comb is not None and abs(comb - (btc_book + hed)) <= 1e-6)
        tol = max(0.01 * abs(be), 0.001 * float(m.get("nav_usdt") or 0.0)) if be is not None else None
        verdict("F3 hedge arithmetic (on caliber)", "PASS" if all(c.values()) else "FAIL",
                f"{c} S={S} G={G} beta_exec={be} recon={recon} intent={intent} scale={scale} hedge={hed} btc_book={btc_book} combined={comb} "
                f"B7v2_tol(ref)={tol} missing_beta={miss[:5]}")
    else:
        verdict("F3 hedge arithmetic (on caliber)", "FAIL", f"record lacks gross_final_target_usdt / book_gross_usdt ({S}, {G})")
    # F4
    legrows = [o for o in orders if o.get("rebalance_id") == rid and o.get("symbol") == BTC and o.get("m3_overlay_leg")]
    sent = [o for o in legrows if o.get("submit_ts") is not None]
    if E == "shadow":
        verdict("F4 hedge leg ordered", "PASS" if not legrows else "FAIL", f"shadow: overlay-leg rows={len(legrows)} (must be 0)")
    else:
        held = num(m.get("btc_held_usdt")) or 0.0
        sides = {str(o.get("side")).upper() for o in sent}
        want = "BUY" if (comb or 0.0) - held > 0 else "SELL"
        verdict("F4 hedge leg ordered", "PASS" if sent and sides <= {want} else "FAIL",
                f"overlay-leg rows={len(legrows)} submitted={len(sent)} sides={sorted(sides)} expected={want} (combined {comb} vs held {held})")
    # F5 delivery (readback)
    rb = jl("position_readback", days); by = collections.defaultdict(dict)
    for p in rb: by[float(p["anchor_ts"])][p["symbol"]] = p
    prev_t = max([t for t in by if t < at], default=None); post = by.get(at, {})
    mid = num((json.loads(r["mid_at_anchor_vector"]) if isinstance(r.get("mid_at_anchor_vector"), str) else (r.get("mid_at_anchor_vector") or {})).get(BTC))
    def _q(snap):        # a readback that exists but does not list BTC = not held (0); a missing readback = unknown (None)
        if not snap: return None
        return num((snap.get(BTC) or {}).get("venue_position_qty")) if BTC in snap else 0.0
    qpre = _q(by.get(prev_t, {})) if prev_t else None
    qpost = _q(post)
    if E == "shadow":
        verdict("F5 delivery (readback)", "N/A", "shadow")
    elif mid is None or qpre is None or qpost is None or comb is None:
        verdict("F5 delivery (readback)", "FAIL", f"not measurable: mid={mid} pre={qpre} post={qpost} combined={comb}")
    else:
        den = comb - qpre * mid; dr = (qpost * mid - qpre * mid) / den if abs(den) > 1e-9 else None
        v = "PASS" if dr is not None and 0.8 <= dr <= 1.1 else ("WARN" if dr is not None and (0.5 <= dr < 0.8 or 1.1 < dr <= 1.3) else "FAIL")
        verdict("F5 delivery (readback)", v, f"ratio={dr} pre={qpre * mid:.1f} post={qpost * mid:.1f} combined_target={comb:.1f} (at the anchor mid)")
    # F6
    nav = num(m.get("nav_usdt")); cg = num(m.get("gross_final_target_usdt"))
    rg = sum(abs(num(p.get("venue_position_notional")) or 0.0) for p in post.values()) if post else None
    ok6 = nav is not None and cg is not None and cg <= 2.5 * nav * (1 + 1e-9) and rg is not None and rg <= 2.5 * nav * 1.03
    verdict("F6 combined gross <= 2.5 NAV", "PASS" if ok6 else "FAIL", f"combined_target={cg} readback={rg} nav={nav} limit={2.5 * nav if nav else None}")
    # F7 BTC fills (pooled; no arm field is read or printed)
    fills = [f for f in PL.collapse_supersedes(jl("fills", days)) if f.get("rebalance_id") == rid and f.get("symbol") == BTC]
    comm = [num(f.get("commission")) for f in fills]; fnot = sum(abs(num(f.get("fill_notional")) or 0.0) for f in fills)
    bps = (sum(abs(x) for x in comm if x is not None) / fnot * 1e4) if fnot > 0 else None
    types = collections.Counter(str(f.get("order_type")) for f in fills); mk = collections.Counter(str(f.get("venue_maker_flag")) for f in fills)
    if E == "shadow":
        verdict("F7 BTC leg execution & fees", "N/A" if not fills else "INFO", f"shadow: BTC fills of the book itself={len(fills)}")
    else:
        ok7 = bool(fills) and all(x is not None for x in comm) and bps is not None and bps <= 5.0
        verdict("F7 BTC leg execution & fees", "PASS" if ok7 else "FAIL",
                f"fills={len(fills)} filled_notional={fnot:.1f} commission={sum(abs(x) for x in comm if x is not None):.4f} fee_bps={bps} "
                f"order_types={dict(types)} maker_flags={dict(mk)}")
    # F8 book identity (layered_book reconstruction)
    rs = r.get("reshape") or {}; Gs = num(rs.get("sizing_gross")); W = tl["weights"]; sw = sum(abs(v) for v in W.values())
    L0 = {s: v / sw * Gs for s, v in W.items()}
    e6 = abs(sum(L0.values()) - float(rs.get("net_producer_usdt", float("nan")))) < 1e-6 * Gs
    removed = set(rs.get("removed_names") or [])
    keep = [s for s in L0 if s not in removed]
    import numpy as np
    v = np.array([L0[s] / Gs for s in keep]); v = v - v.mean(); v = v / np.abs(v).sum()
    L1 = {s: float(x * Gs) for s, x in zip(keep, v)}
    for s in rs.get("forced_flat_names") or []: L1[s] = 0.0
    l1ok = abs(sum(L1.values()) - rs["net_after"]) < 1e-6 * Gs and abs(sum(abs(x) for x in L1.values()) - rs["gross_after"]) < 1e-6 * Gs
    L2 = {s: w * S for s, w in plan.items()} if S else {}
    clamped = set((rs.get("clamped_after_reshape") or {}).get("names") or [])
    capped = set()
    na = f"{DQ}/state/notify_audit.jsonl"
    for l in open(na):
        try: d = json.loads(l)
        except ValueError: continue
        if "场所上限截断" in str(d.get("message", "")) and at - 120 <= float(d.get("ts") or 0) <= at + 3600:
            capped |= set(re.findall(r"([A-Z0-9]+USDT) [+\-][\d,]+→", str(d.get("message", ""))))
    diffs = [abs(L2.get(s, 0.0) - L1[s]) for s in L1 if s in L2 and s not in clamped and s not in capped and s != BTC]
    mx = max(diffs) if diffs else None
    btc_ok = True; btc_d = None
    if E == "on" and BTC not in clamped and BTC not in capped and hed is not None:
        btc_d = L2.get(BTC, 0.0) - L1.get(BTC, 0.0) - hed; btc_ok = abs(btc_d) <= 1.0
    if E == "shadow" and BTC in L1 and BTC not in clamped and BTC not in capped:
        diffs.append(abs(L2.get(BTC, 0.0) - L1[BTC])); mx = max(diffs)
    ok8 = e6 and l1ok and mx is not None and mx < 1e-6 * Gs and btc_ok
    verdict("F8 book identity (non-BTC L2 == L1)", "PASS" if ok8 else "FAIL",
            f"E6={e6} L1_reproduces={l1ok} n_checked={len(diffs)} max|L2-L1|={mx} (tol {1e-6 * Gs:.3g}) clamped={len(clamped)} capped={sorted(capped)} "
            f"BTC L2-L1-hedge={btc_d}")
    # F9 no false alarms
    alarms = []
    for l in open(na):
        try: d = json.loads(l)
        except ValueError: continue
        if at <= float(d.get("ts") or 0) <= at + 3600 and str(d.get("severity")) in ("HIGH", "CRITICAL"):
            alarms.append(str(d.get("message", ""))[:200])
    bad9 = [x for x in alarms if re.search(r"净额|中性|neutral|\bnet\b|cond4b|gross", x, re.I)]
    wd = []
    ev = f"{DQ}/state/watchdog/events.jsonl"
    if os.path.exists(ev):
        for l in open(ev):
            try: d = json.loads(l)
            except ValueError: continue
            t = num(d.get("ts") or d.get("t")) or 0.0
            if at <= t <= at + 3600 and re.search(r"trip|halt|flatten", json.dumps(d), re.I): wd.append(json.dumps(d)[:160])
    nog = num(r.get("net_over_gross"))
    ok9 = not bad9 and not wd and nog is not None and abs(nog) <= 0.02
    verdict("F9 no false alarms", "PASS" if ok9 else "FAIL",
            f"HIGH/CRITICAL in [A,A+1h]={len(alarms)} flagged={bad9[:3]} watchdog_events={wd[:2]} net_over_gross={nog} caliber={r.get('neutrality_caliber')}")
    return finish(a, E)


def rollback(a, A, days):
    """AMENDMENT 1 (R1-R5): the first anchor after an explicit on -> shadow."""
    rows = [r for r in jl("anchors", days) if int((r.get("external_book") or {}).get("nominal_ts") or -1) == A]
    if not rows:
        verdict("R0 anchors row for A", "FAIL", "none"); return finish(a, "rollback")
    r = rows[-1]; m = r.get("m3_beta_overlay") or {}; at = float(r["anchor_ts"]); rid = r.get("rebalance_id")
    book = json.load(open(f"{DQ}/config/book.json")).get("beta_overlay") or {}
    verdict("R1 mode shadow", "PASS" if book.get("mode") == "shadow" and book.get("max_combined_leverage") == 2.5 and m.get("mode") == "shadow"
            and m.get("status") == "shadow" else "FAIL", f"book={book.get('mode')}/{book.get('max_combined_leverage')} rec={m.get('mode')}/{m.get('status')}")
    orders = jl("orders", days); plan = {}
    for o in orders:
        if o.get("rebalance_id") == rid and num(o.get("target_w")) is not None: plan.setdefault(o["symbol"], num(o["target_w"]))
    S = num(m.get("gross_final_target_usdt")); bb = num(m.get("btc_book_target_usdt")) or 0.0
    pb = plan.get(BTC, 0.0) * S if S else None
    verdict("R2 BTC plan == book component", "PASS" if pb is not None and math.isclose(pb, bb, rel_tol=1e-9, abs_tol=1e-6) else "FAIL", f"plan_btc={pb} book={bb}")
    rb = jl("position_readback", days); by = collections.defaultdict(dict)
    for p in rb: by[float(p["anchor_ts"])][p["symbol"]] = p
    prev_t = max([t for t in by if t < at], default=None)
    mid = num((json.loads(r["mid_at_anchor_vector"]) if isinstance(r.get("mid_at_anchor_vector"), str) else (r.get("mid_at_anchor_vector") or {})).get(BTC))
    def _q(snap):
        if not snap: return None
        return num((snap.get(BTC) or {}).get("venue_position_qty")) if BTC in snap else 0.0
    qpre, qpost = (_q(by.get(prev_t, {})) if prev_t else None), _q(by.get(at, {}))
    if None in (mid, qpre, qpost):
        verdict("R3 unwind order sent", "FAIL", f"not measurable mid={mid} pre={qpre} post={qpost}"); verdict("R4 closer to book", "FAIL", "")
    else:
        gap_pre, gap_post = qpre * mid - bb, qpost * mid - bb
        sent = [o for o in orders if o.get("rebalance_id") == rid and o.get("symbol") == BTC and o.get("submit_ts") is not None]
        want = "SELL" if gap_pre > 0 else "BUY"
        need = abs(gap_pre) >= 200.0
        verdict("R3 unwind order sent", "PASS" if (not need) or (sent and {str(o.get("side")).upper() for o in sent} <= {want}) else "FAIL",
                f"gap_pre={gap_pre:.1f} need_order={need} sent={len(sent)} sides={sorted({str(o.get('side')).upper() for o in sent})} expected={want}")
        verdict("R4 closer to book", "PASS" if abs(gap_post) < abs(gap_pre) or abs(gap_post) <= 100.0 else "FAIL", f"gap_pre={gap_pre:.1f} gap_post={gap_post:.1f}")
    return finish(a, "rollback")


def finish(a, E):
    vals = list(RES.values())
    if "FAIL" in vals: v = "FAIL"
    elif "UNDECIDED" in vals: v = "UNDECIDED"
    elif "WARN" in vals: v = "PASS_WITH_WARN"
    else: v = "PASS"
    say(f"M3_ON_FIRST_ANCHOR {a.A} expect={E} VERDICT={v} " + " ".join(f"{k.split()[0]}={x}" for k, x in RES.items()))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f: f.write("\n".join(LINES) + "\n")
    return 0 if v in ("PASS", "PASS_WITH_WARN") else 3


if __name__ == "__main__":
    sys.exit(main())
