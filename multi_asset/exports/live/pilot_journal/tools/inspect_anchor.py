#!/usr/bin/env python3
"""Per-anchor deep inspection, read-only. Usage: inspect_anchor.py <anchor_ts>"""
import json, sys, os, glob, collections, re
from datetime import datetime, timezone
A = int(sys.argv[1]); W = "/Users/haosiyu/wide_shadow"; L = "/Users/haosiyu/dl_quant_live"
# ★ 2026-09-19 盲态默认(复审 R5B-08 同族; AMENDMENT 2): CFG-04 / CFG-06 停止点之前, 本工具默认只打印臂平衡(分配计数)与书级合计,
#   不打印任何逐臂结果量(重挂腿落单 / 二次拒、分臂成交 / 滑点等)。停止点之后才可 `--unblind "<理由>"`, 理由会印在输出首行。
UNBLIND = sys.argv[sys.argv.index("--unblind") + 1] if "--unblind" in sys.argv[2:] and len(sys.argv) > sys.argv.index("--unblind") + 1 else None
BLIND = UNBLIND is None
ARM_TOK = re.compile(r"\bchase\w*|\bforced\b|\bjoin\b|\bbehind\b|\brequote\w*|\bdirect\b|分臂|逐臂|重报价|重挂|二次拒", re.I)
# ★ 2026-09-20: 原先用子串匹配, "direct" 命中了 "directory", 把一条运维告警(台账公证失败)误挡。
#   改成词边界, 并把裸「臂」换成「分臂 / 逐臂」—— 单字「臂」在中文里也会误命中。
def utc(t): return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%m-%d %H:%M:%SZ")
def jl(path):
    out = []
    if not os.path.exists(path): return out
    for l in open(path, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
print(f"### anchor {A} = {utc(A)}" + ("  [BLIND: per-arm outcomes withheld until the CFG-04/CFG-06 stop points]" if BLIND else f"  [UNBLINDED: {UNBLIND}]"))
# ② producer
rows = jl(f"{W}/shadow_log.jsonl")
anc = [r for r in rows if r.get("anchor_ts") == A and r.get("e") in ("anchor", "signal", "target")]
sc = [r for r in rows if r.get("e") == "score" and r.get("anchor_ts") == A - 14400]
for r in anc[-1:]:
    keys = ["e", "members", "sel", "coverage", "fund_updates", "forced_exit_n", "w3", "n_fetched", "n_missing", "booster", "runtime_s", "fetched", "missing"]
    print("producer:", {k: r.get(k) for k in keys if k in r})
    w3 = r.get("w3")
    if w3: print(f"  masked king = {w3[0]/(w3[0]+w3[2]):.4f}")
for r in sc[-1:]: print("score(prev anchor):", {k: r.get(k) for k in ("gross_bps", "net_bps", "carry_bps", "cost_bps", "gross_bps_total", "net_bps_total") if k in r})
skips = [r for r in rows if r.get("anchor_ts") == A and r.get("e") == "anchor_skip"]; print("anchor_skip rows:", len(skips))
# combo
cl = open(f"{W}/fea171/combo_live.log", errors="ignore").read().splitlines()
seg = [l for l in cl if str(A) in l or "④ COMBO" in l or "五层" in l or "ABORT" in l]
for l in seg[-4:]: print("combo:", l[:220])
tc = f"{W}/state/target_combo/{A}.json"
if os.path.exists(tc):
    d = json.load(open(tc)); print("target_combo:", {k: d.get(k) for k in ("w3_masked", "kc_src", "fc_src", "book_form", "kc_gross", "fc_gross", "rho_kc_fc", "n_f10", "phi") if k in d}, "n weights", len(d.get("weights", {})))
tl = json.load(open(f"{W}/state/target_live/{A}.json")); tk_p = f"{W}/state/target_live_king/{A}.json"
wl = tl.get("weights", {}); print("target_live:", {k: tl.get(k) for k in ("producer", "gross", "book_form", "universe_sha") if k in tl}, "n", len(wl), "gross", round(sum(abs(v) for v in wl.values()), 4))
if os.path.exists(tk_p):
    wk = json.load(open(tk_p)).get("weights", {}); syms = set(wl) | set(wk)
    dw = sum(abs(wl.get(s, 0) - wk.get(s, 0)) for s in syms); g = sum(abs(v) for v in wk.values())
    print(f"counterfactual rewrite: sum|Δw|/gross_king = {dw/g*100:.1f}% (king n {len(wk)}, live n {len(wl)})")
# ③ executor funnel by anchor_ts
day = datetime.fromtimestamp(A, tz=timezone.utc).strftime("%Y%m%d"); days = sorted(set([day, datetime.fromtimestamp(A + 14400, tz=timezone.utc).strftime("%Y%m%d")]))
orders = [r for d in days for r in jl(f"{L}/state/live/pilot_log/{d}/orders.jsonl") if A <= (r.get("anchor_ts") or 0) < A + 14400]
# ★ 2026-09-13 LED-01 (FX-EXEC2, lead ruling B): fills.jsonl is append-only with supersede rows (the +60s markout arrives as a
#   second row for the same execution). One execution = (symbol, trade_id) — Binance trade ids are per-SYMBOL, so the old
#   key `trade_id` alone could merge two symbols' executions. Last row in write order wins (it carries the mark), exactly
#   pilot_log.collapse_supersedes / read_fills in the executor. Rows without a trade id are kept apart (never merged).
fills, _no_tid = {}, []
for d in days:
    for r in jl(f"{L}/state/live/pilot_log/{d}/fills.jsonl"):
        if A <= (r.get("anchor_ts") or 0) < A + 14400:
            if r.get("trade_id") is None:
                _no_tid.append(r)
            else:
                fills[(r.get("symbol"), r.get("trade_id"))] = r
fills = list(fills.values()) + _no_tid
term = collections.Counter(r.get("terminal_reason") for r in orders); print("orders n", len(orders), "terminal:", dict(term.most_common(8)))
n5022_1 = sum(1 for r in orders if r.get("attempt_idx") == 1 and r.get("terminal_reason") == "venue_reject" and "-5022" in (r.get("note") or ""))
rested1 = sum(1 for r in orders if r.get("order_type") == "maker" and r.get("attempt_idx") == 1 and r.get("submit_ts") is not None and r.get("mid_at_submit") == r.get("mid_at_anchor"))
print(f"post-only refusals: first-attempt -5022 {n5022_1}, rested attempt-1 {rested1} ⇒ true rate {n5022_1/max(n5022_1+rested1,1)*100:.1f}%")
ra = collections.Counter(r.get("requote_arm") for r in orders if r.get("requote_arm")); print("requote_arm on rows:", dict(ra))
pa = collections.Counter(r.get("placement_arm") for r in orders if r.get("order_type") == "maker" and r.get("attempt_idx") == 1); print("placement arms:", dict(pa), "behind share", round(pa.get("behind", 0) / max(pa.get("behind", 0) + pa.get("join", 0), 1), 3))
ca = collections.Counter(r.get("chase_arm_assigned") for r in orders if r.get("chase_arm_assigned")); print("chase arms:", dict(ca))
mk = sum(abs(f.get("fill_notional") or 0) for f in fills if f.get("venue_maker_flag")); tk = sum(abs(f.get("fill_notional") or 0) for f in fills if not f.get("venue_maker_flag")); tot = mk + tk
fee_by = collections.Counter()
for f in fills: fee_by[(f.get("commission_asset") or "?")] += float(f.get("commission") or 0)
fee_txt = " ".join(f"{v:.6f} {a}" for a, v in sorted(fee_by.items()))  # 09-06: 佣金按资产分列; BNB 抵扣为用户配置(08-05), USDT 换算不在本脚本(旧版把 BNB 当 USDT 求和 ⇒ 0.00 假读数)
print(f"fills n {len(fills)} notional {tot:.0f} maker share {mk/max(tot,1):.3f} commission by asset [{fee_txt}] (no USDT conversion here); markout coverage {sum(1 for f in fills if f.get('mid_at_fill_plus_60s') is not None)}/{len(fills)}")
# launchd log: requote report + new alarm lines for this rebalance
rid = None
for r in orders:
    rid = r.get("rebalance_id"); break
lo = open(f"{L}/state/launchd_out.log", errors="ignore").read()
if rid:
    m = re.findall(r'"rebalance_id": "%s".*?"requote": (\{[^}]*\})' % rid, lo)
    if not BLIND:
        print("requote report:", m[-1] if m else "NOT FOUND")
    elif m:
        try:
            rq = json.loads(m[-1]); keep = ("n_candidates", "n_requoted", "n_direct", "n_exempt", "p_requote", "error")
            print("requote report (blind: assignment/balance fields only):", {k: rq.get(k) for k in keep if k in rq})
        except Exception:
            print("requote report: [blind: unparsable, withheld]")
    else:
        print("requote report: NOT FOUND")
    m2 = re.findall(r'\[%s\] (拒单率 post-only[^\n]{0,260})' % rid, lo)
    if m2 and BLIND:
        print("reject-rate log line (blind: book-level first attempt only):", re.split(r"[;；]\s*重报价", m2[-1])[0][:200])
    else:
        print("reject-rate log line:", (m2[-1][:260] if m2 else "NOT FOUND"))
    m3 = re.findall(r'"post_only_refusals": (\{[^}]*\})', lo)
    if m3 and BLIND:
        try:
            pr0 = json.loads(m3[-1] if m3[-1].endswith("}") else m3[-1] + "}")
            print("post_only_refusals (last, blind: first-attempt book-level keys only):", {k: v for k, v in pr0.items() if k == "n_reached" or k.endswith("_1")})
        except Exception:
            print("post_only_refusals: [blind: unparsable, withheld]")
    else:
        print("post_only_refusals (last):", m3[-1][:300] if m3 else "NOT FOUND")
# ④ accounting
pr = [r for d in days for r in jl(f"{L}/state/live/pilot_log/{d}/position_readback.jsonl") if A <= (r.get("anchor_ts") or 0) < A + 14400]
if pr:
    last = pr[-1]; keys = [k for k in last if k not in ("positions", "rows")][:14]; print("readback:", {k: last.get(k) for k in keys})
    pos = last.get("positions") or last.get("rows") or []
    if isinstance(pos, list) and pos:
        g = sum(abs(float(p.get("notional") or p.get("notional_usdt") or 0)) for p in pos); n = sum(float(p.get("notional") or p.get("notional_usdt") or 0) for p in pos)
        print(f"  venue gross {g:.0f} net {n:+.0f} net/gross {n/max(g,1)*100:+.2f}% names {len(pos)}")
an = [r for d in days for r in jl(f"{L}/state/live/pilot_log/{d}/anchors.jsonl") if A <= (r.get("anchor_ts") or 0) < A + 14400]
for r in an[-1:]: print("anchors row:", {k: r.get(k) for k in ("regime", "n_skipped", "n_orders", "n_filled", "fill_ratio", "turnover", "gross_target", "nav") if k in r})
dn = jl(f"{L}/state/live/pilot_log/{days[-1]}/daily_nav.jsonl"); 
for r in dn[-1:]: print("daily_nav:", {k: r.get(k) for k in list(r)[:10]})
ar = open(f"{L}/state/anchor_runs.log", errors="ignore").read().splitlines(); print("anchor_runs tail:", [l[:120] for l in ar[-3:]])
na = jl(f"{L}/state/notify_audit.jsonl"); recent = [r for r in na if (r.get("ts") or r.get("time") or 0) and float(r.get("ts") or r.get("time") or 0) >= A]
import hashlib as _hl
for r in recent[-12:]:
    _t = str(r.get("msg") or r.get("message") or r.get("text") or r)
    if BLIND and ARM_TOK.search(_t):
        print("alarm:", (r.get("severity") or r.get("sev")), f"[blind: alarm text mentions an experiment arm — withheld; sha256 {_hl.sha256(_t.encode()).hexdigest()[:16]}]")
    else:
        print("alarm:", (r.get("severity") or r.get("sev")), _t[:200])
pns = f"{L}/state/live/per_name_stop.json"
if os.path.exists(pns):
    d = json.load(open(pns)); print("per_name_stop:", {k: (v if not isinstance(v, (list, dict)) else len(v)) for k, v in d.items() if k in ("stopped", "cooldown", "counts", "n_stopped", "n_cooldown")} or list(d)[:8])
print("DONE")
