#!/usr/bin/env python3
"""每锚只读排查报告 → Telegram. 会话无关(launchd 驱动). 实盘书零接触.
用法: python3 ops/anchor_report.py [--anchor EPOCH] [--dry]  (缺省=最近一个已过整4h锚)

★★★ LED-08 (FX-EXEC2, 2026-09-13; AUDIT_EXEC 842bbffa). The report builder used to fold every unknown to zero —
    `filled_notional or 0`, `intended_notional or 0`, `fee_paid or 0` — and print a fee bps over ALL filled notional.
    Measured on the live ledger copy: A1785931245 (08-05 12Z) had 103/103 fills with a raw BNB fee
    (`fee_paid 0.0, fee_all_usdt False`) and would print `fee 0.00bps`; A1789215839 (09-12 12Z) had 4 unknown-fill
    rows folded into the denominator. Its warnings were stale: net/gross at 5% (the deep-check template says ±1%, and
    |net/gross| > 1% on 22 of the last 42 traded anchors, so neither constant describes the book), a fixed taker-share
    line at 10% that fired on 51 of 101 reports (maker share has run 0.56–0.89 since 09-08, cause unattributed —
    X-COST), and `funding.jsonl 缺` on a settlement anchor where the book was flat (09-13 08Z).
  ⇒ Fees and fills now go through `live/cost_buckets` (three buckets; bps over MEASURED fills only, None ≠ 0; unknown
    fills counted, never zero). Taker share and |net/gross| are judged against the book's OWN trailing distribution:
    the previous ≤42 traded, non-rebuild anchors from `pilot_log.anchor_series` (median + 3 × 1.4826 × MAD, at least
    12 anchors, otherwise "no baseline" and no warning), with the baseline printed beside the number; a HARD |net/gross|
    line at 5% stays (the report's own documented value), so a slow drift the trailing band absorbs still pages at 5%.
    Rebuild anchors are labelled and not judged on taker share; halted anchors are labelled and their intent is not
    called turnover; a settlement anchor whose previous slot was flat says so instead of "missing".
  ⇒ The builder is a PURE function (`build_report`) over gathered inputs; `gather` does the reads; only `main` sends.
    The policy levels themselves (what taker share / neutrality is acceptable) belong to the deep-check template (K5)
    and the cost attribution (X-COST); this file only reports departures from the current mix.

★★★ LED-08 FOLLOW-UP (FX-EXEC2, 2026-09-16; lead sent the above back, FIXPROGRAM §8). The trailing band is 42 anchors
    = EXACTLY SEVEN DAYS, so it re-centres on a step shift within a week and then reports nothing. Measured on the
    live ledger copy: the 93.1% → 73.9% maker-share collapse X-COST decomposed is already inside the band — the
    band's own taker median is 21.58% and it warns on nothing, while the same book sat at 5.01% in the reference
    window. A self-calibrating instrument cannot see a regime change, only an outlier inside the regime.
  ⇒ `live/cost_drift.py` adds a second, NON-adaptive comparison against a window frozen in
    `config/cost_drift_reference.json`. THIS FILE PRINTS BOTH LEVELS AND RAISES NOTHING: the verdict is raised at
    most once a day by `ops/daily_summary.py`, because this report runs six times a day and a drift is a slow fact,
    not a per-anchor event. The report cannot re-derive the reference — `gather` reads 10 days and the window is
    older — so it prints the PINNED level; the daily summary, which already reads every ledger day, re-derives it
    and names a mismatch. A reference config that cannot be read is NAMED on the line, never skipped.
"""
import json, time, math, sys, os, collections, subprocess, statistics, urllib.request, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.expanduser("~/wide_shadow")
sys.path.insert(0, os.path.join(REPO, "live"))
import cost_buckets as CB     # noqa: E402
import cost_drift as CD       # noqa: E402
import pilot_log as PL        # noqa: E402

DRIFT_REFERENCE_PATH = os.path.join(REPO, "config", "cost_drift_reference.json")
NET_OVER_GROSS_HARD = 0.05          # the report's own pre-LED-08 line, kept as an absolute ceiling
BASELINE_ANCHORS = 42               # one week of 4h anchors
BASELINE_MIN_N = 12
BAND_MADS = 3.0
MAD_TO_SIGMA = 1.4826
REJECT_WARN = 160
SETTLEMENT_HOURS = (0, 8, 16)
FLAT_USDT = PL.REBUILD_FLAT_USDT


def latest_anchor():
    now = time.time()
    return int(now // 14400) * 14400

def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def _fin(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if (v == v and v not in (float("inf"), float("-inf"))) else None


def order_facts(O):
    """One rebalance's order rows as DATA. Pure. None is never folded to 0."""
    b = CB.bucket_fills(O)
    tr = collections.Counter(o.get("terminal_reason") for o in O)
    known = [CB.filled_abs(o) for o in O]
    filled_known = sum(v for v in known if v)
    n_unknown_fill = sum(1 for v in known if v is None)
    taker_known = sum((CB.filled_abs(o) or 0.0) for o in O if o.get("order_type") == "topup_taker")
    ints = [_fin(o.get("intended_notional")) for o in O]
    return {"n_rows": len(O), "terminal": dict(tr), "n_venue_reject": tr.get("venue_reject", 0),
            "filled_known_usdt": filled_known, "n_unknown_fill": n_unknown_fill,
            "intended_known_usdt": sum(abs(v) for v in ints if v is not None),
            "n_unknown_intended": sum(1 for v in ints if v is None),
            "taker_share": ((taker_known / filled_known) if filled_known and not n_unknown_fill else None),
            "taker_share_known_part": ((taker_known / filled_known) if filled_known else None),
            "buckets": b}


def robust_band(values, k=BAND_MADS, min_n=BASELINE_MIN_N):
    v = [x for x in values if x is not None]
    if len(v) < min_n:
        return {"n": len(v), "median": None, "mad": None, "threshold": None}
    med = statistics.median(v)
    mad = statistics.median([abs(x - med) for x in v])
    return {"n": len(v), "median": med, "mad": mad, "threshold": med + k * MAD_TO_SIGMA * mad}


def history_facts(anchor_rows, orders_by_rid, A, n=BASELINE_ANCHORS):
    """Trailing baseline over the previous ≤n TRADED, non-rebuild anchors strictly before slot A. Pure."""
    S = PL.anchor_series(anchor_rows)
    reb = set(S["rebuild_nominal_ts"])
    prior = [(t, r) for t, r in zip(S["nominal_ts"], S["series"]) if t < A and t not in reb][-n:]
    taker, ngabs = [], []
    for t, r in prior:
        f = order_facts(orders_by_rid.get(r.get("rebalance_id"), []))
        taker.append(f["taker_share"])
        ng = _fin(r.get("net_over_gross"))
        ngabs.append(None if ng is None else abs(ng))
    return {"slots": [t for t, _ in prior], "taker": robust_band(taker), "net_over_gross_abs": robust_band(ngabs),
            "is_rebuild": A in reb, "rebuild_slots": sorted(reb)}


def _pct(x, nd=0):
    return "n/a" if x is None else f"{x * 100:.{nd}f}%"


# Producer daemons the report expects, by the producer contract named in config/book.json external_book.producer_contract
# (quant_research DESIGN_producer_new_contract §A7-5, lead 2026-09-23): the NC producer release stops and disables the sidecar (it
# overwrote the F10 chain state with old-contract features) — under "nc_v1" the sidecar is REQUIRED ABSENT and its presence is a warning;
# key missing / null / "legacy" = the three daemons of before. The key moves with the model pins, so a rollback of the executor
# config restores the old expectation in the same commit. An unknown value is itself a warning and is checked as legacy.
PRODUCER_DAEMONS = {"prod": "shadow_loop_v3.py run", "sidecar": "sidecar_daemon.sh", "combo": "combo_live_daemon.sh"}
DAEMON_CONTRACTS = {"legacy": (("prod", "sidecar", "combo"), ()), "nc_v1": (("prod", "combo"), ("sidecar",))}


def daemon_check(ps_text, producer_contract):
    """(line, warnings) for the producer daemons under the named contract. PURE."""
    warn = []
    key = "legacy" if producer_contract in (None, "legacy") else producer_contract
    if key not in DAEMON_CONTRACTS:
        warn.append(f"producer_contract 未知值 {producer_contract!r}(按 legacy 检查)"); key = "legacy"
    required, forbidden = DAEMON_CONTRACTS[key]
    running = lambda tag: sum(1 for l in (ps_text or "").splitlines() if PRODUCER_DAEMONS[tag] in l and "grep" not in l) >= 1   # noqa: E731
    miss = [f"守护缺 {t}" for t in required if not running(t)]
    extra = [f"侧车在跑(producer_contract={key} 下应已停用)" if t == "sidecar" else f"{t} 在跑(应已停用)" for t in forbidden if running(t)]
    warn += miss + extra
    line = f"守护 {len(required)}/{len(required)}" if not (miss or extra) else "; ".join(miss + extra)
    return line, warn


def build_report(A, *, ps_text, shadow_row, combo_status, target_combo, anchor_row, orders, prev_row,
                 funding_rows, twin_line, history, drift=None, producer_contract=None):
    """(text, record) for anchor slot A from already-gathered inputs. PURE — no file, network or clock read."""
    hh = time.strftime("%m-%d %H:%MZ", time.gmtime(A))
    L = [f"锚 {hh} 排查(常驻器)"]
    warn = []
    _dl, _dw = daemon_check(ps_text, producer_contract)
    warn += _dw
    L.append(_dl)
    sh = shadow_row
    if isinstance(sh, Exception):
        warn.append(f"shadow读失败 {sh}")
    elif sh:
        L.append(f"fund_upd {sh.get('fund_updates')} cov {sh.get('coverage')} forced {sh.get('forced_exit_n')}")
        exp = 453 if (A // 3600) % 24 in SETTLEMENT_HOURS else 353
        _fu = _fin(sh.get("fund_updates"))
        if _fu is None or abs(_fu - exp) > 40:
            warn.append(f"fund_updates 异常 {sh.get('fund_updates')} vs ~{exp}")
    else:
        warn.append("shadow_log 无本锚行")
    S = combo_status or {}
    if not (S.get("ok") and S.get("reader_ok")):
        warn.append(f"combo状态 {S.get('ok')}/{S.get('reader_ok')}")
    tc = target_combo or {}
    m = tc.get("meta") or tc
    wm = m.get("w3_masked")
    if wm:
        L.append(f"w3m {[round(x, 3) for x in wm]} kc/fc {m.get('kc_state_source')}/{m.get('fc_state_source')} f10 {m.get('n_f10_scored')}")
        if wm[1] != 0:
            warn.append("rev24 席位非零!")
        if m.get("kc_state_source") != "own" or m.get("fc_state_source") != "own":
            warn.append("kc/fc 状态断链")
    else:
        warn.append("target_combo 缺/无 w3m")
    rec = {"anchor_ts": A}
    row = anchor_row
    if not row:
        warn.append("anchors 行缺(执行器未收官或未交易)")
    else:
        eb = row.get("external_book") or {}
        rs = row.get("reshape") or {}
        halted = bool(row.get("opening_halted"))
        if not eb.get("sha_ok"):
            warn.append("sha_ok=False!")
        f = order_facts(orders or [])
        b = f["buckets"]
        rec["order_facts"] = {k: v for k, v in f.items() if k != "buckets"}
        rec["cost_buckets"] = b
        gb = _fin(rs.get("gross_before"))
        _turn = ("n/a" if not gb else f"{f['intended_known_usdt'] / gb * 100:.1f}%") + \
                (f"(意图未知 {f['n_unknown_intended']} 行)" if f["n_unknown_intended"] else "")
        _fee = b["fee_bps_measured"]
        _fee_s = (f"{_fee:.2f}bps" if _fee is not None else "n/a(未测, 非 0)")
        if b["n_fills"] and b["n_measured"] < b["n_fills"]:
            _fee_s += f" [已测 {b['n_measured']}/{b['n_fills']}, 覆盖 {CB.pct_floor(b['coverage_measured_notional'])}%]"
        _tk = f["taker_share"]
        _tk_s = _pct(_tk) if _tk is not None else (f"≥{_pct(f['taker_share_known_part'])}(成交未知行)" if f["taker_share_known_part"] is not None else "n/a")
        _unk = f" 成交未知 {f['n_unknown_fill']} 行" if f["n_unknown_fill"] else ""
        label = ("停开仓 | " if halted else "") + ("重建锚 | " if history.get("is_rebuild") else "")
        L.append(f"{label}age {eb.get('age_s')}s n {eb.get('n_names')} | 单 {f['n_rows']} 拒 {f['n_venue_reject']} | "
                 f"{'意图(未发送)' if halted else '换手'} {_turn} 成交 {f['filled_known_usdt']:.0f}U{_unk} taker {_tk_s} fee {_fee_s}")
        rg, vn, ng = _fin(row.get("realized_gross")), _fin(row.get("venue_net_usdt")), _fin(row.get("net_over_gross"))
        kg = _fin((row.get("known_gaps") or {}).get("gross_usdt"))
        L.append(f"gross {'n/a' if rg is None else f'{rg:.0f}'} net {'n/a' if vn is None else f'{vn:.0f}'}"
                 f"({'n/a' if ng is None else f'{ng * 100:.2f}%'}) gaps {'n/a' if kg is None else f'{kg:.0f}U'}")
        nb, tb = history.get("net_over_gross_abs") or {}, history.get("taker") or {}
        if ng is not None and abs(ng) > NET_OVER_GROSS_HARD:
            warn.append(f"净敞口越硬线 {ng * 100:.2f}% (>|{NET_OVER_GROSS_HARD * 100:.0f}%|)")
        elif ng is not None and nb.get("threshold") is not None and abs(ng) > nb["threshold"]:
            warn.append(f"净敞口偏离近{nb['n']}锚 |{ng * 100:.2f}%| > 中位 {nb['median'] * 100:.2f}% + 3MAD = {nb['threshold'] * 100:.2f}%")
        if f["n_venue_reject"] > REJECT_WARN:
            warn.append(f"拒单异常 {f['n_venue_reject']}")
        if not halted and not history.get("is_rebuild") and _tk is not None and tb.get("threshold") is not None \
                and _tk > tb["threshold"]:
            warn.append(f"taker 占比 {_pct(_tk)} > 近{tb['n']}锚 中位 {_pct(tb['median'])} + 3MAD = {_pct(tb['threshold'])}")
        L.append(f"基线(近{tb.get('n')}锚, 不含重建/停开仓): taker 中位 {_pct(tb.get('median'))} 线 {_pct(tb.get('threshold'))}"
                 f" | |净/gross| 中位 {_pct(nb.get('median'), 2)} 线 {_pct(nb.get('threshold'), 2)}")
        # ★ LED-08 follow-up: BOTH levels, NO verdict. The band above is self-calibrating and absorbs a step
        #   within 7 days; this line is the frozen yardstick it cannot absorb. The verdict is the daily summary's
        #   (once a day) — this script runs six times a day. A reference that cannot be read is NAMED, not skipped.
        if isinstance(drift, dict) and drift.get("error"):
            L.append(f"参照窗不可读: {drift['error']}(漂移检查未运行, 非「无漂移」)")
        elif isinstance(drift, dict) and drift.get("facts"):
            L.append(CD.reference_line(drift["cfg"], drift["facts"]))
        else:
            L.append("参照窗未加载(漂移检查未运行, 非「无漂移」)")
    if (A // 3600) % 24 in SETTLEMENT_HOURS:
        if funding_rows is None:
            _pg = _fin((prev_row or {}).get("realized_gross")) if prev_row else None
            if prev_row is not None and _pg is not None and _pg < FLAT_USDT:
                L.append("funding 结算时无持仓(上一锚空仓), 无结算行")
            else:
                warn.append("funding.jsonl 缺" + ("(上一锚持仓未知)" if _pg is None else "(结算时持仓中)"))
        else:
            near = [r for r in funding_rows if _fin(r.get("settlement_ts")) is not None and abs(_fin(r.get("settlement_ts")) - A) < 1800]
            vals = [_fin(r.get("funding_paid")) for r in near]
            tot = sum(v for v in vals if v is not None)
            nun = sum(1 for v in vals if v is None)
            L.append(f"funding {len(near)}名 {tot:+.2f}U" + (f" (金额不可读 {nun} 行)" if nun else ""))
    if isinstance(twin_line, Exception) or twin_line is None:
        warn.append("guard_twin 读失败")
    else:
        gl = twin_line
        L.append("twin " + (gl.split("Z ", 1)[1][:70] if "Z " in gl else gl[:70]))
        if "DISAGREE" in gl:
            warn.append("twin 最新 DISAGREE(1-2周期瞬态属常, 连看)")
    status = ("⚠️ " + " | ".join(warn)) if warn else "✅ 全绿"
    text = status + "\n" + "\n".join(L)
    rec.update({"status": "warn" if warn else "green", "warn": warn, "lines": L,
                "baseline": {k: history.get(k) for k in ("taker", "net_over_gross_abs", "is_rebuild")},
                "drift": ({"window_name": (drift.get("cfg") or {}).get("window_name"),
                           "facts": drift.get("facts"), "error": drift.get("error")}
                          if isinstance(drift, dict) else None)})
    return text, rec


def gather(A):
    """Every read the builder needs. Read-only."""
    day = time.strftime("%Y%m%d", time.gmtime(A))
    g = {}
    g["ps_text"] = subprocess.run(["/bin/ps", "axww"], capture_output=True, text=True).stdout
    try:
        g["producer_contract"] = (json.load(open(os.path.join(REPO, "config", "book.json"))).get("external_book") or {}).get("producer_contract")
    except Exception:
        g["producer_contract"] = None                                     # unreadable config: the legacy expectation (the loop itself refuses such a config)
    try:
        sh = None
        for l in open(f"{WS}/shadow_log.jsonl"):
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("anchor_ts") == A and "fund_updates" in d:
                sh = d
        g["shadow_row"] = sh
    except Exception as e:
        g["shadow_row"] = e
    g["combo_status"] = jload(f"{WS}/state/combo_live_status.json")
    g["target_combo"] = jload(f"{WS}/state/target_combo/{A}.json")
    plog = os.path.join(REPO, "state", "live", "pilot_log")
    days = [d for d in PL.available_days(plog)
            if time.strftime("%Y%m%d", time.gmtime(A - 9 * 86400)) <= d <= day]
    anchors, orders_by_rid = [], {}
    for d in days:
        _ap, _op = os.path.join(plog, d, "anchors.jsonl"), os.path.join(plog, d, "orders.jsonl")
        anchors += PL._read_jsonl(_ap) if os.path.exists(_ap) else []
        for o in (PL._read_jsonl(_op) if os.path.exists(_op) else []):
            orders_by_rid.setdefault(o.get("rebalance_id"), []).append(o)
    by_slot = {}
    for r in anchors:
        eb = r.get("external_book")
        if isinstance(eb, dict) and eb.get("nominal_ts") is not None:
            by_slot[int(eb["nominal_ts"])] = r
    row = by_slot.get(A)
    g["anchor_row"] = row
    g["orders"] = orders_by_rid.get(row.get("rebalance_id"), []) if row else []
    g["prev_row"] = by_slot.get(A - 14400)
    fp = os.path.join(plog, day, "funding.jsonl")
    g["funding_rows"] = PL._read_jsonl(fp) if os.path.exists(fp) else None
    try:
        g["twin_line"] = open(os.path.expanduser("~/guard_twin/state/guard_twin.out")).readlines()[-1].strip()
    except Exception as e:
        g["twin_line"] = e
    g["history"] = history_facts(anchors, orders_by_rid, A)
    # ★ LED-08 follow-up: the FROZEN reference. `gather` reads 10 days and the window is older, so the pinned
    #   levels are used as-is; ops/daily_summary.py re-derives them from the whole ledger and names a mismatch.
    try:
        _cfg = CD.load_reference(DRIFT_REFERENCE_PATH)
        _th, _ec = (_cfg.get("threshold") or {}), (_cfg.get("economic") or {})
        g["drift"] = {"cfg": _cfg, "error": None,
                      "facts": CD.drift_facts(CD.pinned_levels(_cfg), CD.band_to_levels(g["history"]),
                                              k=_th.get("k_mads", CD.K_MADS),
                                              min_n=_th.get("min_n", CD.MIN_N),
                                              turnover=_ec.get("turnover_median_filled_over_realized_gross"),
                                              delta_bps=_ec.get("delta_bps_per_anchor_per_gross",
                                                                CD.DELTA_BPS_ANCHOR_GROSS))}
    except Exception as e:
        g["drift"] = {"cfg": None, "facts": None, "error": repr(e)}
    return g


def main():
    A = None; dry = "--dry" in sys.argv
    if "--anchor" in sys.argv:
        A = int(sys.argv[sys.argv.index("--anchor") + 1])
    A = A or latest_anchor()
    text, rec = build_report(A, **gather(A))
    out = {"anchor_ts": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": rec["status"],
           "warn": rec["warn"], "lines": rec["lines"]}
    with open(f"{REPO}/state/anchor_report_last.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(text)
    if not dry:
        env = {}
        for l in open(f"{REPO}/.env"):
            l = l.strip()
            if l.startswith("TELEGRAM_") and "=" in l:
                k, v = l.split("=", 1); env[k] = v.strip().strip('"')
        tok, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
        if tok and chat:
            data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900]}).encode()
            urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
            print("[sent]")

if __name__ == "__main__":
    main()
