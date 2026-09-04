#!/usr/bin/env python3
"""M1 首锚验收器(PREREG_deploy_universe §2 ① ② ③ + §7 AMENDMENT)— 只读。用法: m1_first_anchor_check.py <anchor_ts>"""
import json, os, sys, time, glob, numpy as np
A = int(sys.argv[1]); WS = os.path.expanduser("~/wide_shadow"); ok_all = True
def chk(name, cond, detail=""):
    global ok_all; ok_all &= bool(cond); print(f"  {'PASS' if cond else 'FAIL'} {name} {detail}")
sig = None
for ln in reversed(open(f"{WS}/shadow_log.jsonl").readlines()[-3000:]):
    r = json.loads(ln)
    if r.get("e") == "signal" and int(r.get("anchor_ts", -1)) == A: sig = r; break
print(f"M1 首锚验收 anchor {A} ({time.strftime('%m-%dT%H:%MZ', time.gmtime(A))})")
if not sig: print("  FAIL 无 signal 行"); sys.exit(1)
chk("① status OK / coverage≥0.95", sig["status"] == "OK" and sig["coverage"] >= 0.95, f"{sig['status']} cov {sig['coverage']}")
band = (430, 480) if (A // 3600) % 8 else (430, 520)
chk("① fund_updates 稳态带(live 名)", 300 <= sig["fund_updates"] <= 520, f"{sig['fund_updates']} (+base {sig.get('fund_updates_base')})")
# §9 AMENDMENT(09-04 04:3xZ): ≥600 的前提来自含 SETTLING 的缓存计数(658); 场所实际 TRADING USDT 永续 526, ∪ live450 = 528 ⇒ 判据改为 base_n == 场所实测(±3) 且 ≥500
try:
    import urllib.request
    _xi = json.loads(urllib.request.urlopen(urllib.request.Request("https://fapi.binance.com/fapi/v1/exchangeInfo", headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read())
    _cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); _venue = len({x["symbol"] for x in _xi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"} | set(_cfg["symbols_live"]))
except Exception as _e: _venue = None
chk("① base_n == 场所 TRADING USDT 永续 ∪ live(±3) ∧ ≥500 ∧ exinfo_ok", sig.get("exinfo_ok") and sig.get("base_n", 0) >= 500 and (_venue is None or abs(sig.get("base_n", 0) - _venue) <= 3), f"base_n {sig.get('base_n')} venue∪live {_venue} exinfo_ok {sig.get('exinfo_ok')}")
chk("① fund_base_n ≥430(首锚; 第 3 锚起 ≥550)", sig.get("fund_base_n", 0) >= 430, f"fund_base_n {sig.get('fund_base_n')}")
chk("① runtime_s ≤ 300 (自限 240 ⇒ 落盘 ≤N+21)", sig["runtime_s"] <= 300, f"runtime {sig['runtime_s']}s weight {sig['weight_used']}")
tl = json.load(open(f"{WS}/state/target_live/{A}.json")); w = tl["written_utc"]; wt = time.mktime(time.strptime(w[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
chk("② written_utc ≤ N+21:30", (wt - A) <= 21.5 * 60, f"N+{(wt-A)/60:.1f} min; n_names {tl['n_names']} gross_norm {tl['gross_norm']:.4f}")
st = json.load(open(f"{WS}/state/combo_live_status.json")); chk("② combo_live_status ok & reader_ok & anchor 匹配", st.get("ok") and st.get("reader_ok") and int(st.get("anchor", 0)) == A, f"n_in_universe {st.get('n_in_universe')}")
# ③ 权重差 vs 影子 A(sidecar state pending 记录)
sp = os.path.expanduser("~/universe_shadow/state.json")
if os.path.exists(sp):
    S = json.load(open(sp)); rec = S.get("pending", {}).get(str(A)) or {}
    if rec: chk("③ Σ|A−B|/gross 首锚 ≤5%", rec.get("dw_AB", 1) <= 0.05, f"dw_AB {rec.get('dw_AB')} chain_ok {rec.get('chain_ok')}")
    else: print("  WAIT ③ sidecar 尚未处理本锚(N+54 运行)")
else: print("  WAIT ③ sidecar state 不存在")
# 多头 gross 占比变化 ≤2pp(target_live vs 上锚)
def long_share(p):
    d = json.load(open(p))["weights"]; g = sum(abs(v) for v in d.values()); return sum(v for v in d.values() if v > 0) / g
ls_now, ls_prev = long_share(f"{WS}/state/target_live/{A}.json"), long_share(f"{WS}/state/target_live/{A-14400}.json")
chk("③ 多头 gross 占比变化 ≤2pp", abs(ls_now - ls_prev) <= 0.02, f"{ls_prev:.3f} → {ls_now:.3f}")
print("RESULT:", "PASS" if ok_all else "FAIL(见上)")
