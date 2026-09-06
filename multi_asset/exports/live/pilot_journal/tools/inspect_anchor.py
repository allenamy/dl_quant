#!/usr/bin/env python3
"""Per-anchor deep inspection, read-only. Usage: inspect_anchor.py <anchor_ts>"""
import json, sys, os, glob, collections, re
from datetime import datetime, timezone
A = int(sys.argv[1]); W = "/Users/haosiyu/wide_shadow"; L = "/Users/haosiyu/dl_quant_live"
def utc(t): return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%m-%d %H:%M:%SZ")
def jl(path):
    out = []
    if not os.path.exists(path): return out
    for l in open(path, errors="ignore"):
        try: out.append(json.loads(l))
        except Exception: pass
    return out
print(f"### anchor {A} = {utc(A)}")
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
fills = {}
for d in days:
    for r in jl(f"{L}/state/live/pilot_log/{d}/fills.jsonl"):
        if A <= (r.get("anchor_ts") or 0) < A + 14400: fills[r.get("trade_id") or (r["symbol"], r["fill_ts"])] = r
fills = list(fills.values())
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
    print("requote report:", m[-1] if m else "NOT FOUND")
    m2 = re.findall(r'\[%s\] (拒单率 post-only[^\n]{0,260})' % rid, lo); print("reject-rate log line:", (m2[-1][:260] if m2 else "NOT FOUND"))
    m3 = re.findall(r'"post_only_refusals": (\{[^}]*\})', lo); print("post_only_refusals (last):", m3[-1][:300] if m3 else "NOT FOUND")
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
for r in recent[-12:]: print("alarm:", (r.get("severity") or r.get("sev")), str(r.get("msg") or r.get("text") or r)[:200])
pns = f"{L}/state/live/per_name_stop.json"
if os.path.exists(pns):
    d = json.load(open(pns)); print("per_name_stop:", {k: (v if not isinstance(v, (list, dict)) else len(v)) for k, v in d.items() if k in ("stopped", "cooldown", "counts", "n_stopped", "n_cooldown")} or list(d)[:8])
print("DONE")
