#!/usr/bin/env python3
"""universe_shadow — 影子三书纸面对照(PREREG_deploy_universe_2026-09-04 §6)。只读生产者/执行器文件, 零实盘接触。
书 A = 旧秩基(prev_rec.fund_z_old)∧ 冻结成员;  书 B = 新秩基(prev_rec.legz.fund)∧ 冻结成员(Phase A 生产者书);
书 C = 生产者书(Phase B 起为动态成员)。链 = 生产者同链(z→sel 去均值→L1→cap→L1→EMA→带→强制出场)。
自检: 用 legz.fund 复算的 B 必须与 state/weights/<anchor>.npz 的 sm 逐位同(链复制正确性), 否则记 chain_mismatch 不计入。
P&L: 执行器 anchors.jsonl mid_at_anchor_vector(t→t+4h)+ funding.jsonl 结算; 成本 = 3.5 bps × Σ|trade|(两书同式, 差分中近似抵消)。
用法: universe_shadow.py bootstrap <aux_pre_m1.json>   # H_A := 换装前 H
      universe_shadow.py run                          # 处理 aux.prev_rec 的最新锚(幂等)"""
import json, os, sys, glob, time
import numpy as np
WS = os.path.expanduser("~/wide_shadow"); LIVE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
RT = os.environ.get("UNIVERSE_SHADOW_HOME", os.path.expanduser("~/universe_shadow")); os.makedirs(RT, exist_ok=True)
STATE = f"{RT}/state.json"; OUT = f"{RT}/shadow_pnl.jsonl"; COST_BPS = 3.5
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); P = cfg["params"]; syms = cfg["symbols_panel"]; NW = len(syms)
live_mask = np.zeros(NW, bool); live_mask[[i for i, s in enumerate(syms) if s in set(cfg["symbols_live"])]] = True
def chain(H, m, legz_king, legz_rev24, fund_z, sel_pos, w3):
    m = np.asarray(m, np.int64); z = w3[0]*np.nan_to_num(np.asarray(legz_king, float)) + w3[1]*np.nan_to_num(np.asarray(legz_rev24, float)) + w3[2]*np.nan_to_num(np.asarray(fund_z, float))
    sel = np.zeros(len(m), bool); sel[np.asarray(sel_pos, np.int64)] = True
    w = np.where(sel, z, 0.0); w[sel] -= w[sel].mean(); g = np.abs(w).sum()
    if g < 1e-9: return H.copy(), 0.0
    w /= g; capw = P["cap_mult"] / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw); g2 = np.abs(w).sum()
    if g2 > 1e-9: w /= g2
    tgt = np.zeros(NW); tgt[m] = w
    sm = H + P["alpha"] * (tgt - H); trade = sm - H; sm = np.where(np.abs(trade) < P["band"], H, sm)
    keep = live_mask.copy(); mm = np.zeros(NW, bool); mm[m] = True; keep &= mm; kl = np.zeros(NW, bool); kl[m[sel]] = True; keep &= kl
    sm = np.where(keep, sm, 0.0)
    return sm, float(np.abs(sm - H).sum())
def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"H_A": {}, "H_B": {}, "done": [], "pending": {}}
def save_state(st): tmp = STATE + ".tmp"; json.dump(st, open(tmp, "w")); os.replace(tmp, STATE)
def vec(d): H = np.zeros(NW); [H.__setitem__(int(k), float(v)) for k, v in d.items()]; return H
def dct(H): return {str(int(j)): float(H[j]) for j in np.where(np.abs(H) > 1e-12)[0]}
def w3_for(anchor):
    for ln in reversed(open(f"{WS}/shadow_log.jsonl").readlines()[-4000:]):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("e") == "signal" and int(r.get("anchor_ts", -1)) == anchor: return np.array(r["w3"], float), r
    return None, None
def mids_at(nominal):   # 执行器锚行的 mid 向量(执行器 anchor_ts = 名义 + 偏移, 按 4h 取整对齐)
    day = time.strftime("%Y%m%d", time.gmtime(nominal)); cands = sorted(glob.glob(f"{LIVE}/{day}/anchors.jsonl") + glob.glob(f"{LIVE}/{time.strftime('%Y%m%d', time.gmtime(nominal + 86400))}/anchors.jsonl"))
    for p in cands:
        for ln in open(p):
            try: r = json.loads(ln)
            except Exception: continue
            if int(float(r.get("anchor_ts", 0))) // 14400 * 14400 == nominal and r.get("mid_at_anchor_vector"):
                v = r["mid_at_anchor_vector"]; return v if isinstance(v, dict) else json.loads(v)
    return None
def funding_between(t0, t1):
    out = {}
    for day in {time.strftime("%Y%m%d", time.gmtime(t)) for t in (t0, t1)}:
        p = f"{LIVE}/{day}/funding.jsonl"
        if not os.path.exists(p): continue
        for ln in open(p):
            try: r = json.loads(ln)
            except Exception: continue
            ts = int(float(r.get("settlement_ts", 0)))
            if t0 < ts <= t1 and r.get("funding_rate") is not None: out[r["symbol"]] = out.get(r["symbol"], 0.0) + float(r["funding_rate"])
    return out
def pnl(sm, t0, t1):
    m0, m1 = mids_at(t0), mids_at(t1)
    if not m0 or not m1: return None
    fr = funding_between(t0, t1); g = np.abs(sm).sum(); price = 0.0; cov = 0.0; carry = 0.0
    for j in np.where(np.abs(sm) > 1e-12)[0]:
        s = syms[j]
        if s in m0 and s in m1 and float(m0[s]) > 0: price += sm[j] * (float(m1[s]) / float(m0[s]) - 1.0); cov += abs(sm[j])
        carry += -sm[j] * fr.get(s, 0.0)   # 多头付正费率
    return {"gross": round(float(g), 4), "price_bps": round(price * 1e4, 3), "carry_bps": round(carry * 1e4, 3), "mid_cov": round(cov / max(g, 1e-9), 3)}
def run():
    aux = json.load(open(f"{WS}/state/aux.json")); pr = aux["prev_rec"]; A = int(pr["anchor_ts"]); st = load_state()
    if A in st["done"]: print(f"anchor {A} already done"); return settle(st)
    if "fund_z_old" not in pr: print(f"anchor {A}: prev_rec 无 fund_z_old(M1 前记录), 跳过"); return
    w3, sig = w3_for(A)
    if w3 is None: print("no signal row"); return
    H_B_prev = vec(st["H_B"]) if st["H_B"] else None
    prevz = np.load(f"{WS}/state/weights/{A-14400}.npz"); Hp = np.zeros(NW); Hp[prevz["idx"].astype(int)] = prevz["val"].astype(float)
    if H_B_prev is None: H_B_prev = Hp
    smB, trB = chain(Hp, pr["members"], pr["legz"]["king"], pr["legz"]["rev24"], pr["legz"]["fund"], pr["sel_idx"], w3)
    prod = np.zeros(NW); prod[np.array(pr["sm_idx"], int)] = np.array(pr["sm"], float)
    mism = float(np.abs(smB - prod).max()); chain_ok = mism < 1e-9
    H_A_prev = vec(st["H_A"]) if st["H_A"] else Hp
    smA, trA = chain(H_A_prev, pr["members"], pr["legz"]["king"], pr["legz"]["rev24"], pr["fund_z_old"], pr["sel_idx"], w3)
    st["H_A"] = dct(smA); st["H_B"] = dct(prod); st["done"].append(A)
    st["pending"][str(A)] = {"A": dct(smA), "B": dct(prod), "trA": trA, "trB": float(np.abs(prod - Hp).sum()), "chain_ok": chain_ok, "chain_max_abs_diff": mism,
                             "dw_AB": round(float(np.abs(smA - prod).sum() / max(np.abs(prod).sum(), 1e-9)), 4), "base_n": pr.get("base_n"), "fund_base_n": pr.get("fund_base_n"), "w3": [round(float(x), 4) for x in w3]}
    print(f"anchor {A}: chain_ok={chain_ok} (max|diff| {mism:.2e}) | Σ|A−B|/gross {st['pending'][str(A)]['dw_AB']:.4f} | base_n {pr.get('base_n')} fund_base_n {pr.get('fund_base_n')}")
    save_state(st); settle(st)
def settle(st):   # 为已有 t+4h mid 的待结锚算 P&L
    for k in sorted(list(st["pending"].keys()), key=int):
        t0 = int(k); rec = st["pending"][k]; t1 = t0 + 14400
        pa, pb = pnl(vec(rec["A"]), t0, t1), pnl(vec(rec["B"]), t0, t1)
        if pa is None or pb is None: continue
        rowA = dict(pa, cost_bps=round(COST_BPS * rec["trA"], 3)); rowB = dict(pb, cost_bps=round(COST_BPS * rec["trB"], 3))
        netA = rowA["price_bps"] + rowA["carry_bps"] - rowA["cost_bps"]; netB = rowB["price_bps"] + rowB["carry_bps"] - rowB["cost_bps"]
        row = {"anchor_ts": t0, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(t0)), "A": rowA, "B": rowB, "netA_bps": round(netA, 3), "netB_bps": round(netB, 3), "d_BA_bps": round(netB - netA, 3),
               "dw_AB": rec["dw_AB"], "chain_ok": rec["chain_ok"], "base_n": rec["base_n"], "fund_base_n": rec["fund_base_n"], "w3": rec["w3"]}
        open(OUT, "a").write(json.dumps(row) + "\n"); del st["pending"][k]; print(f"settled {row['utc']}: netA {netA:+.2f} netB {netB:+.2f} Δ(B−A) {netB-netA:+.2f} bps (mid_cov {rowA['mid_cov']})")
    save_state(st)
def bootstrap(aux_pre):
    aux = json.load(open(aux_pre)); st = load_state(); st["H_A"] = {str(int(k)): float(v) for k, v in aux["H"].items()}; st["H_B"] = dict(st["H_A"]); st["boot_from"] = aux_pre; st["boot_anchor"] = int(aux["last_anchor"]); save_state(st)
    print(f"bootstrapped H_A/H_B from {aux_pre} (last_anchor {aux['last_anchor']}, {len(st['H_A'])} names)")
if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "bootstrap": bootstrap(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "selfcheck":   # 用现有(M1 前)prev_rec 验证链复制: 复算 B 与 weights/<A>.npz 逐位比
        aux = json.load(open(f"{WS}/state/aux.json")); pr = aux["prev_rec"]; A = int(pr["anchor_ts"]); w3, sig = w3_for(A)
        prevz = np.load(f"{WS}/state/weights/{A-14400}.npz"); Hp = np.zeros(NW); Hp[prevz["idx"].astype(int)] = prevz["val"].astype(float)
        cur = np.load(f"{WS}/state/weights/{A}.npz"); cu = np.zeros(NW); cu[cur["idx"].astype(int)] = cur["val"].astype(float)
        sel_pos = pr.get("sel_idx")
        if sel_pos is None:   # M1 前无 sel_idx: 用 |sm|>0 的成员近似不可行 → 从 qv 门重建需 rolling; 改用"非零目标"反推: sel = 成员中 |cu|>0 ∪ 被带冻结的 —— 只报差异量级
            print("prev_rec 无 sel_idx(M1 前), 仅报 members/sm 维度:", len(pr["members"]), len(pr["sm"])); sys.exit(0)
        smB, _ = chain(Hp, pr["members"], pr["legz"]["king"], pr["legz"]["rev24"], pr["legz"]["fund"], sel_pos, w3)
        print(f"selfcheck anchor {A}: max|复算B − weights.npz| = {np.abs(smB - cu).max():.3e}")
    else: run()
