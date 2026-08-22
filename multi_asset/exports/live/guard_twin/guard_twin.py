#!/usr/bin/env python3
"""guard_twin — 双账守卫影子版 (Track 1 §2.1 of docs/DESIGN_optimization_path_2026-08-21.md).

独立第二推导: 直接从交易所账户真值 (/fapi/v3/account, /fapi/v1/income) 重算四条停机线的读数, 与
~/dl_quant_live 看门狗 (state/live/watchdog/last_eval.json) 和 per_name_stop.json 逐次比对。
  - 只读 API (签名 GET), 零下单、零改状态; 第一阶段 **不接线**: 只记录 + 分歧告警文件。
  - 两类比对: (i) 输入孪生 —— 交易所权益 vs daily_nav.nav (看门狗读的输入);
              (ii) 算术孪生 —— 用看门狗的规则对 daily_nav 自算 vs 看门狗给出的读数。
  - 容差 (预注册 §2.1): 日变化/累计 0.10 个百分点; 逐名深度 1 个百分点; 杠杆 0.05×。
运行: launchd com.hsy.guardtwin 每 1200s; 或手动 `python3 guard_twin.py --once`。
状态: ~/guard_twin/state/{snapshots.jsonl, income.jsonl, compare.jsonl, latest.json, alerts.log, guard_twin.log}
"""
import json, os, sys, time, glob, traceback
HOME = os.path.expanduser("~")
LIVE = os.path.join(HOME, "dl_quant_live")
ST = os.path.join(HOME, "guard_twin", "state")
os.makedirs(ST, exist_ok=True)
sys.path.insert(0, os.path.join(LIVE, "live")); sys.path.insert(0, LIVE)
PILOT_START_MS = 1785542400000          # 2026-08-01 00:00Z — first LIVE day (daily_nav 20260801)
# ★ INPUT/DAY/CUM compare quantities sampled MINUTES apart on a live book (the watchdog's nav row vs the
#   twin's snapshot): a 0.1pp gap is ordinary 3-minute drift on a 25k gross. The defects this twin exists
#   for (double count, stale input, wrong account, missing unrealised) are ≥1pp and persistent, so the
#   acting tolerance is 0.5pp; the raw gap is logged every run so the tolerance can be tightened from
#   measured drift once the series is long enough (prereg §2.1 names 0.10pp as the time-matched target).
TOL = {"day_pct": 0.50, "cum_pct": 0.50, "input_pct": 0.50, "name_pct": 1.0, "lev": 0.10}   # lev: gross/equity drifts 2-4% intra-anchor on a live book; defects hunted are ≥0.3×
DEPTH_LIMIT = -0.25   # default; overridden per run from the live config's active per_name_stop profile (see _depth_limit)

def _depth_limit():
    """Per-name stop depth from the LIVE config (base depth_pct or the active profile's), so the twin judges the
    same line the book uses (wide profile −0.30 vs base −0.25; RUNBOOK_wide_live §3 L2 gate)."""
    try:
        cfg = json.load(open(os.path.join(LIVE, "config", "book.json"))).get("per_name_stop") or {}
        prof = cfg.get("active_profile")
        if prof and prof in (cfg.get("profiles") or {}):
            return float((cfg["profiles"][prof]).get("depth_pct", cfg.get("depth_pct", DEPTH_LIMIT)))
        return float(cfg.get("depth_pct", DEPTH_LIMIT))
    except Exception:
        return DEPTH_LIMIT

def log(msg):
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + msg
    with open(os.path.join(ST, "guard_twin.log"), "a") as f: f.write(line + "\n")
    print(line, flush=True)

def jl_append(name, row):
    with open(os.path.join(ST, name), "a") as f: f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

def jl_read(name):
    p = os.path.join(ST, name)
    if not os.path.exists(p): return []
    out = []
    for l in open(p):
        l = l.strip()
        if l:
            try: out.append(json.loads(l))
            except Exception: pass
    return out

def broker():
    import envfile; envfile.load()
    from binance_broker import BinanceBroker
    return BinanceBroker(mode="LIVE")          # read-only calls only below

def fetch_account(b):
    acct = b._request("GET", "/fapi/v3/account", signed=True)
    pos = []
    for p in acct.get("positions", []):
        amt = float(p.get("positionAmt") or 0.0)
        if abs(amt) <= 0: continue
        notional = float(p.get("notional") or 0.0)
        pos.append({"symbol": p.get("symbol"), "amt": amt, "notional": notional,
                    "upnl": float(p.get("unrealizedProfit") or 0.0),
                    "entry": float(p.get("entryPrice") or 0.0)})
    assets = {a.get("asset"): {"wallet": float(a.get("walletBalance") or 0.0), "upnl": float(a.get("unrealizedProfit") or 0.0)}
              for a in acct.get("assets", []) if float(a.get("walletBalance") or 0.0) != 0.0 or float(a.get("unrealizedProfit") or 0.0) != 0.0}
    return {"wallet": float(acct.get("totalWalletBalance")), "upnl": float(acct.get("totalUnrealizedProfit")),
            "margin_balance": float(acct.get("totalMarginBalance")), "positions": pos, "assets": assets}

def fetch_income(b, start_ms, end_ms=None):
    """all income rows since start_ms, paged by time; dedupe on tranId."""
    rows = []; cur = int(start_ms); end_ms = int(end_ms or time.time() * 1000)
    for _ in range(200):
        page = b._request("GET", "/fapi/v1/income", signed=True,
                          params={"startTime": cur, "endTime": end_ms, "limit": 1000})
        if not page: break
        rows.extend(page)
        if len(page) < 1000: break
        # ★ INCLUSIVE restart: funding settlements and multi-fill anchors put dozens of rows on ONE
        #   millisecond; `last_time + 1` would skip the remainder of that batch when a page boundary
        #   falls inside it (measured 2026-08-21: −14.3 USDT identity gap). Overlap + dedupe instead.
        nxt = int(page[-1]["time"])
        if nxt == cur: nxt += 1                      # a full page inside ONE ms: cannot page further
        cur = nxt
    seen = set(); out = []
    for r in rows:
        k = (r.get("tranId"), r.get("incomeType"), r.get("symbol"), r.get("time"), r.get("income"))
        if k in seen: continue
        seen.add(k); out.append({"tranId": r.get("tranId"), "type": r.get("incomeType"), "symbol": r.get("symbol"),
                                 "income": float(r.get("income") or 0.0), "asset": r.get("asset"), "time": int(r.get("time"))})
    return out

def day_of(ms): return time.strftime("%Y%m%d", time.gmtime(ms / 1000))

def daily_nav_rows():
    out = {}
    for f in sorted(glob.glob(os.path.join(LIVE, "state", "live", "pilot_log", "*", "daily_nav.jsonl"))):
        d = os.path.basename(os.path.dirname(f)); rows = []
        for l in open(f):
            l = l.strip()
            if l:
                try: rows.append(json.loads(l))
                except Exception: pass
        if rows: out[d] = rows
    return out

def main(once=False):
    t0 = time.time(); now_ms = int(t0 * 1000); today = day_of(now_ms)
    b = broker()
    acct = fetch_account(b)
    equity = acct["margin_balance"]
    gross = sum(abs(p["notional"]) for p in acct["positions"])
    # ── income: incremental since last stored row (overlap 1h, dedupe) ──────────────────────
    inc_hist = jl_read("income.jsonl")
    last_ms = max([r["time"] for r in inc_hist], default=PILOT_START_MS - 1)
    new = fetch_income(b, max(PILOT_START_MS, last_ms - 3600_000), now_ms)
    known = {(r["tranId"], r["type"], r["symbol"], r["time"], r["income"]) for r in inc_hist}
    added = [r for r in new if (r["tranId"], r["type"], r["symbol"], r["time"], r["income"]) not in known]
    for r in added: jl_append("income.jsonl", r)
    inc = inc_hist + added
    # ── snapshot ───────────────────────────────────────────────────────────────────────────
    snap = {"ts": round(t0, 3), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "day": today,
            "equity": equity, "wallet": acct["wallet"], "upnl": acct["upnl"], "gross": gross,
            "n_pos": len(acct["positions"]),
            "positions": {p["symbol"]: {"notional": p["notional"], "upnl": p["upnl"]} for p in acct["positions"]}}
    snaps = jl_read("snapshots.jsonl"); jl_append("snapshots.jsonl", snap); snaps.append(snap)
    # ── derivations ────────────────────────────────────────────────────────────────────────
    # ★ USDT rows only for the equity/day/cum arithmetic (equity is USD-valued; BNB commissions are a
    #   separate asset ledger, checked by its own identity below). Transfers in BNB are ~0.33 BNB once.
    transfers_today = sum(r["income"] for r in inc if r["type"] == "TRANSFER" and r["asset"] == "USDT" and day_of(r["time"]) == today)
    transfers_all = sum(r["income"] for r in inc if r["type"] == "TRANSFER" and r["asset"] == "USDT")
    pnl_ledger = sum(r["income"] for r in inc if r["type"] != "TRANSFER" and r["asset"] == "USDT")
    # per-asset closed-account identity: wallet(asset) == Σ income(asset) since pilot start (account was empty before)
    ident = {}
    for asset in sorted({r["asset"] for r in inc}):
        w = (acct.get("assets") or {}).get(asset, {}).get("wallet")
        tot = sum(r["income"] for r in inc if r["asset"] == asset)
        ident[asset] = {"wallet": w, "sum_income": tot, "gap": None if w is None else w - tot}
    # previous day close: twin's own last snapshot before today; fallback daily_nav (shared source, flagged)
    prev_close = None; prev_src = None
    own_prev = [s for s in snaps if s["day"] < today]
    if own_prev:
        prev_close = own_prev[-1]["equity"]; prev_src = "twin:" + own_prev[-1]["utc"]
    dn = daily_nav_rows()
    if prev_close is None:
        pdays = [d for d in dn if d < today]
        if pdays:
            r = dn[pdays[-1]][-1]; prev_close = float(r.get("nav") or 0) or None; prev_src = "daily_nav:" + pdays[-1]
    day_pct_twin = None
    if prev_close:
        day_pct_twin = (equity - prev_close - transfers_today) / prev_close * 100.0
    # cum from start (TWR): backfill from daily_nav day closes (shared) up to the twin's first day, then twin closes
    twr = 1.0; chain = []
    days = sorted(dn)
    twin_days = sorted({s["day"] for s in snaps})
    first_twin_day = twin_days[0] if twin_days else None
    prev = None
    for d in days:
        if first_twin_day and d >= first_twin_day: break
        r = dn[d][-1]; nav = r.get("nav")
        if not nav: continue
        flow = 0.0
        try: flow = float(r.get("external_flow_usdt") or 0.0)
        except Exception: pass
        if prev is not None:
            if abs(flow) > 1e-9:
                # flow day: use P&L delta (realised + d unrealised) / prev
                re, un = r.get("realised_pnl"), r.get("unrealised_pnl")
                if re is None or un is None or prev[1] is None: chain.append((d, None, "flow-unpriced")); prev = (float(nav), r.get("unrealised_pnl")); continue
                rd = (float(re) + float(un) - float(prev[1])) / prev[0]
            else:
                rd = float(nav) / prev[0] - 1.0
            twr *= (1 + rd); chain.append((d, rd, "daily_nav"))
        prev = (float(nav), r.get("unrealised_pnl"))
    # twin segment: day closes from own snapshots (last per day), transfer-adjusted via income ledger
    if prev is not None and twin_days:
        by_day = {}
        for s in snaps: by_day[s["day"]] = s
        p_eq = prev[0]
        for d in twin_days:
            e = by_day[d]["equity"]
            tr = sum(r["income"] for r in inc if r["type"] == "TRANSFER" and day_of(r["time"]) == d)
            rd = (e - p_eq - tr) / p_eq
            twr *= (1 + rd); chain.append((d, rd, "twin")); p_eq = e
    cum_twin_pct = (twr - 1.0) * 100.0
    # independent level check: equity − Σtransfers (all history) should equal Σ(non-transfer income) + upnl
    closed_account_gap = (ident.get("USDT", {}).get("gap"))          # USDT wallet − Σ USDT income (should be ≈0)
    if closed_account_gap is None: closed_account_gap = 0.0
    lev_twin = gross / equity if equity else None
    deep = {p["symbol"]: p["upnl"] / abs(p["notional"]) for p in acct["positions"] if abs(p["notional"]) > 5.0}
    _dl = _depth_limit()
    deep_names = sorted([s for s, dpt in deep.items() if dpt <= _dl])
    # ── watchdog readings ─────────────────────────────────────────────────────────────────
    wd = {}; pns = {}
    try: wd = json.load(open(os.path.join(LIVE, "state", "live", "watchdog", "last_eval.json")))
    except Exception as e: log(f"last_eval unreadable: {e}")
    try: pns = json.load(open(os.path.join(LIVE, "state", "live", "per_name_stop.json")))
    except Exception as e: log(f"per_name_stop unreadable: {e}")
    c = (wd.get("conditions") or {})
    c2 = c.get("cond2_day_loss") or {}; c4 = c.get("cond4_drawdown") or {}; c4b = c.get("cond4b_leverage") or {}
    wd_eval = wd.get("evaluated_utc")
    # arithmetic twin: recompute the watchdog's own rule on daily_nav (today's day change = today's last nav vs prev day last nav; flow day ⇒ None)
    arith_today = None
    if today in dn:
        r = dn[today][-1]; nav = r.get("nav"); flow = 0.0
        try: flow = float(r.get("external_flow_usdt") or 0.0)
        except Exception: pass
        pdays = [d for d in dn if d < today]
        if nav and pdays and dn[pdays[-1]][-1].get("nav") and abs(flow) <= 1e-9:
            pn = float(dn[pdays[-1]][-1]["nav"]); arith_today = (float(nav) - pn) / pn * 100.0
    # input twin: the watchdog's latest nav row vs exchange equity now (time-matched within 30 min only)
    nav_latest = None; nav_age_min = None
    if today in dn:
        r = dn[today][-1]; nav_latest = r.get("nav"); ts = r.get("nav_ts")
        if ts: nav_age_min = (t0 - float(ts)) / 60.0
    cmp = {"utc": snap["utc"], "wd_evaluated_utc": wd_eval,
           "equity": equity, "nav_latest": nav_latest, "nav_age_min": None if nav_age_min is None else round(nav_age_min, 1),
           "day_pct_twin": day_pct_twin, "day_pct_arith_on_daily_nav": arith_today, "wd_worst_day_pct": c2.get("worst_day_pct"),
           "prev_close_src": prev_src, "transfers_today": transfers_today,
           "cum_pct_twin": cum_twin_pct, "wd_cum_from_start_pct": c4.get("cum_return_from_start_pct"),
           "closed_account_gap_usdt": closed_account_gap, "ledger_identity_by_asset": ident, "pnl_ledger_usdt": pnl_ledger, "transfers_all": transfers_all,
           "lev_twin": lev_twin, "wd_actual_leverage": c4b.get("actual_leverage"),
           "deep_names_now": deep_names, "depth_limit_used": _dl, "pns_counters": sorted((pns.get("counters") or {}).keys()),
           "pns_stopped": sorted((pns.get("stopped") or {}).keys()), "pns_cooldown": sorted((pns.get("cooldown") or {}).keys()),
           "n_chain_twin_days": sum(1 for x in chain if x[2] == "twin"), "n_chain_dn_days": sum(1 for x in chain if x[2] == "daily_nav")}
    # ── disagreements ─────────────────────────────────────────────────────────────────────
    dis = []
    if nav_latest and nav_age_min is not None and nav_age_min < 30:
        g = (equity - float(nav_latest)) / float(nav_latest) * 100.0
        cmp["input_gap_pp"] = g
        if abs(g) > TOL["input_pct"]: dis.append(f"INPUT equity {equity:.2f} vs daily_nav {float(nav_latest):.2f} ({g:+.3f}pp, age {nav_age_min:.0f}m)")
    # ★ DAY/CUM/LEV are compared ONLY when the watchdog's nav row is fresh (≤30 min): between anchors the twin
    #   reads live equity while daily_nav/last_eval still hold the last anchor's numbers, so a real market move
    #   shows up as a "disagreement" (measured 2026-08-21 19:04Z: +0.94pp recovery 2h45m after the 16:19Z row).
    #   A stale row is NOT comparable; the twin's own readings are still recorded as the independent series.
    _fresh = (nav_age_min is not None and nav_age_min <= 30.0)
    cmp["comparable"] = bool(_fresh)
    if _fresh and day_pct_twin is not None and arith_today is not None and abs(day_pct_twin - arith_today) > TOL["day_pct"]:
        dis.append(f"DAY twin {day_pct_twin:+.3f}% vs daily_nav-arith {arith_today:+.3f}%")
    if _fresh and c4.get("cum_return_from_start_pct") is not None and abs(cum_twin_pct - float(c4["cum_return_from_start_pct"])) > TOL["cum_pct"]:
        dis.append(f"CUM twin {cum_twin_pct:+.3f}% vs wd {float(c4['cum_return_from_start_pct']):+.3f}%")
    if abs(closed_account_gap) > max(2.0, 0.0005 * equity):
        dis.append(f"LEDGER USDT wallet {ident['USDT']['wallet']:.2f} vs Σ USDT income {ident['USDT']['sum_income']:.2f} (gap {closed_account_gap:+.2f})")
    _bnb = ident.get("BNB", {})
    if _bnb.get("gap") is not None and abs(_bnb["gap"]) > 0.002:
        dis.append(f"LEDGER BNB wallet {_bnb['wallet']:.4f} vs Σ BNB income {_bnb['sum_income']:.4f} (gap {_bnb['gap']:+.4f})")
    # during a trip (reduce-only / flattened) the anchor row's leverage predates the flatten ⇒ not comparable
    _halted = False
    try:
        _st = json.load(open(os.path.join(LIVE, "state", "live", "watchdog", "state.json")))
        _halted = bool(_st.get("reduce_only") or _st.get("tripped_at"))
    except Exception:
        _halted = False
    cmp["live_halted"] = _halted
    _flat = (gross < 1.0)   # freshly resumed / flat book: the anchor row's leverage predates the state ⇒ not comparable
    cmp["book_flat"] = bool(_flat)
    if _fresh and (not _halted) and (not _flat) and lev_twin is not None and c4b.get("actual_leverage") is not None and abs(lev_twin - float(c4b["actual_leverage"])) > TOL["lev"]:
        dis.append(f"LEV twin {lev_twin:.3f} vs wd {float(c4b['actual_leverage']):.3f}")
    cmp["disagreements"] = dis; cmp["status"] = "DISAGREE" if dis else ("AGREE" if _fresh else "AGREE(ledger-only; nav row stale)")
    # ── SHADOW of the proposed §4-2 response (PREREG_stop_response_reversible_2026-08-21, log-only) ──
    # rule: cross −4.0% ⇒ pending_confirm (halt opening, no flatten); next reading: flatten only if BOTH ledgers
    # read ≤ −4.0% (|gap| ≤ 0.5pp) AND the loss persists; else release. Here: what the rule would say NOW.
    try:
        _wd_day = c2.get("worst_day_pct")   # watchdog's day reading (worst over window; today if today is worst)
        _tw = day_pct_twin
        _both_below = (_tw is not None and _tw <= -4.0) and (arith_today is not None and arith_today <= -4.0)
        _any_below = (_tw is not None and _tw <= -4.0) or (arith_today is not None and arith_today <= -4.0)
        _agree = (_tw is not None and arith_today is not None and abs(_tw - arith_today) <= 0.5)
        if _both_below and _agree: _shadow = "FLATTEN_CONFIRMED(both ledgers ≤ −4%)"
        elif _any_below: _shadow = "PENDING_CONFIRM(halt opening; one ledger ≤ −4% or ledgers disagree)"
        else: _shadow = "NO_ACTION"
        cmp["shadow_response_4_2"] = {"rule": "halt→confirm-next-anchor→flatten", "would": _shadow,
                                      "twin_day_pct": _tw, "wd_arith_day_pct": arith_today, "ledgers_agree": _agree,
                                      "current_live_rule": "flatten immediately at ≤ −4.0%"}
    except Exception as _e:
        cmp["shadow_response_4_2"] = {"error": repr(_e)[:120]}
    jl_append("compare.jsonl", cmp)
    json.dump(cmp, open(os.path.join(ST, "latest.json"), "w"), indent=1, ensure_ascii=False, default=str)
    if dis:
        with open(os.path.join(ST, "alerts.log"), "a") as f: f.write(snap["utc"] + " " + " | ".join(dis) + "\n")
    log(f"{cmp['status']} eq={equity:.2f} nav={nav_latest} day_twin={None if day_pct_twin is None else round(day_pct_twin,3)} arith={None if arith_today is None else round(arith_today,3)} "
        f"cum_twin={cum_twin_pct:.3f} wd_cum={c4.get('cum_return_from_start_pct')} lev={None if lev_twin is None else round(lev_twin,3)} gap={closed_account_gap:+.2f} deep={deep_names} n_inc_new={len(added)}")

if __name__ == "__main__":
    try: main(once="--once" in sys.argv)
    except Exception as e:
        log("ERROR " + repr(e)[:300]); traceback.print_exc()
