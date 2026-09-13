#!/usr/bin/env python3
"""t8_tables.py <T8 dir> <env whitelist> — render receipts/TABLES_T8.md from the pod2 receipts copied to receipts/pod2/ (read-only; no statistic is
recomputed except means of receipt values and ranking of already-stored model internals). Mac, /usr/bin/python3. Asserts receipt/device shas."""
import os, sys, json, glob, hashlib
WHITE = set(x for x in sys.argv[2].split(",") if x) if len(sys.argv) > 2 else None
assert WHITE, "launch with an env whitelist as argv[2]"
extra = sorted(k for k in os.environ if k not in WHITE); assert extra == [], ("ENV WHITELIST VIOLATION", extra)
import numpy as np
T8 = os.path.abspath(sys.argv[1]); RP = T8 + "/receipts/pod2"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
PRE = "53da0bcc948b2ed417ec505888f95c96c615e201ad2c57bdf549ea4ece884f8a"; AM1 = "d5928ee3272c30b1ceb64a9c675b3d0d900cea7160e474d9538f6f266340be56"
assert sha(T8 + "/PREREG_T8.md") == PRE and sha(T8 + "/PREREG_AMENDMENT_1_T8.md") == AM1
L = lambda n: json.load(open(RP + "/" + n))
S, B, F, J = L("RECEIPT_T8_selftest.json"), L("RECEIPT_T8_build.json"), L("RECEIPT_T8_fit.json"), L("RECEIPT_T8_judge.json")
for R, dev in ((S, "t8_selftest.py"), (B, "t8_build.py"), (F, "t8_fit.py"), (J, "t8_judge.py")):
    assert R["self_sha256"] == sha(T8 + "/devices/" + dev), ("device sha differs from receipt", dev)
    assert R["common_sha256"] == sha(T8 + "/devices/t8_common.py"), ("common sha differs", dev)
    assert R["prereg_sha256"] == {"prereg": PRE, "amendment_1": AM1}, dev
assert J["build_receipt_sha256"] == sha(RP + "/RECEIPT_T8_build.json") and J["fit_receipt_sha256"] == sha(RP + "/RECEIPT_T8_fit.json")
NULLS = sorted(glob.glob(RP + "/RECEIPT_T8_null_*.json"))
for p in NULLS:
    assert J["null_receipts"][os.path.basename(p)] == sha(p) and json.load(open(p))["self_sha256"] == sha(T8 + "/devices/t8_null.py")
FE = ["BTC4", "BTC24", "BTC72", "ALT4", "ALT24", "ALT72", "BR4", "BR24", "DISP4", "DISP24", "RVM24", "RVM168", "MUF", "SIGF", "DMUF24", "DSIGF24", "TKR24", "CSF", "CSR72", "CLF", "CLR72", "TR1", "TR6", "TR42"]
TG = ("NET", "LONG", "SHORT", "CARRY"); MD = ("R", "L"); SD = ("42", "2027"); FO = ("F1", "F2", "F3", "F4", "F5")
f4 = lambda v: "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:+.4f}"
ci = lambda c: f"[{c[0]:+.4f}, {c[1]:+.4f}]"
yn = lambda b: "✓" if b else "✗"
out = []; w = out.append
w("> **创建:** 渲染于收据(`devices/t8_tables.py`) | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T8) | **状态:** 表格, 数字全部取自 `receipts/pod2/*.json` | **作废条件:** 收据或装置被替换(本装置断言其 sha)\n")
w("# TABLES · T8 · 书层收益可感知门\n")
w(f"预注册 `PREREG_T8.md` `{PRE[:8]}…` + AMENDMENT 1 `{AM1[:8]}…`。单位: 目标 bps / 4h 锚 / 单位 gross; 相关为 W_ALPHA 样本外(n = 9138)除非另注。\n")

w("## T0 · 门、运行与正控\n")
w("| 项 | 读数 | 通过 |\n|---|---|---|")
w(f"| 合成自检(8 项) | " + "; ".join(f"{k}" for k in S["checks"]) + f" | {yn(S['ALL_PASS'])} |")
g = B["gates"]
w(f"| G-IN | shas、config_json、rec R18 = T1 逐位、ts 对齐、W_FULL 10038 / W_ALPHA 9138 | {yn(g['G_IN']['PASS'])} |")
w(f"| G-T | max\\|L+S−PRICE\\| s42 {g['G_T']['42']['max_abs_long_plus_short_minus_price']:.2e} / s2027 {g['G_T']['2027']['max_abs_long_plus_short_minus_price']:.2e}; max\\|PRICE−CARRY−COST−NET\\| {g['G_T']['42']['max_abs_price_minus_carry_cost_net']:.2e} / {g['G_T']['2027']['max_abs_price_minus_carry_cost_net']:.2e} | {yn(all(g['G_T'][s]['PASS'] for s in SD))} |")
w(f"| G-T2 | 独立多空复算 max\\|Δ\\| LONG {g['G_T2']['42']['max_abs_long']:.2e} / {g['G_T2']['2027']['max_abs_long']:.2e}, SHORT {g['G_T2']['42']['max_abs_short']:.2e} / {g['G_T2']['2027']['max_abs_short']:.2e} bps | {yn(all(g['G_T2'][s]['PASS'] for s in SD))} |")
w(f"| G2a(修订 1) | c_L(0) {g['G2a']['42']['c_L']['0']:+.4f} / {g['G2a']['2027']['c_L']['0']:+.4f}; c_S(0) {g['G2a']['42']['c_S']['0']:+.4f} / {g['G2a']['2027']['c_S']['0']:+.4f}; argmax 全为 0; c_N(0) 只报 {g['G2a']['42']['c_N']['0']:+.4f} / {g['G2a']['2027']['c_N']['0']:+.4f} | {yn(all(g['G2a'][s]['PASS'] for s in SD))} |")
w(f"| G3 shuffle-future | 60 行逐位相等 s42 {g['G3']['bitwise_equal']['42']}/60, s2027 {g['G3']['bitwise_equal']['2027']}/60 | {yn(g['G3']['PASS'])} |")
w(f"| G3-NEG | BTC4 变 {g['G3_NEG']['btc4_changed']}/60, TR1 变 {g['G3_NEG']['tr1_changed']}/60, MUF 变 {g['G3_NEG']['muf_changed']}/60 | {yn(g['G3_NEG']['PASS'])} |")
nn = sum(len(json.load(open(p))["rows"]) for p in NULLS); und = sum(json.load(open(p))["undefined_replaced_by_0"] for p in NULLS)
w(f"| G1 零分布 | {nn} 次置换, 分块 {', '.join(os.path.basename(p)[16:-5] for p in NULLS)}; 未定义值 {und} | {yn(nn == 500)} |")
w(f"| PC(CARRY r_pool ≥ 0.5) | R: {F['cells']['R_CARRY_s42']['pool']['r']:+.4f} / {F['cells']['R_CARRY_s2027']['pool']['r']:+.4f}; L: {F['cells']['L_CARRY_s42']['pool']['r']:+.4f} / {F['cells']['L_CARRY_s2027']['pool']['r']:+.4f} | R {yn(J['positive_control']['R'])} L {yn(J['positive_control']['L'])} |")
w(f"| 数据 | `out/T8_data.npz` sha `{B['out']['sha256'][:16]}…`(首跑与重跑逐位相同); `out/T8_oos.npz` sha `{F['out']['sha256'][:16]}…` | — |")
w(f"| 环境 | {F['env']['python']} / numpy {F['env']['numpy']} / lightgbm {F['lightgbm']}; 亲和核 {F['env']['affinity'][0]}–{F['env']['affinity'][-1]}; GPU 前后 `{F['sys_before']['gpu']}` / `{F['sys_after']['gpu']}`; PID 333197/339489 `{' '.join(F['sys_after']['protected_pids'].split()[2:])}` | — |\n")

w("## T1 · 冻结读法(§8)\n")
w(f"族最大值零分布 q95 = **{J['null']['q95_family_max']:.5f}**。**T8 = {J['T8']}**。\n")
w("| 目标 | R | L | 目标判决 | 分解标签(R / L, 只报) |\n|---|---|---|---|---|")
for t in TG[:3]:
    tv = J["target"][t]; w(f"| {t} | {tv['R']} | {tv['L']} | **{tv['verdict']}** | {J['model_target']['R_'+t]['decomposition_label']} / {J['model_target']['L_'+t]['decomposition_label']} |")
w("\n| 格 | r_pool | CI95 k=0 | CI95 k=9 | 正折 | C1 | C2 | C3 | C4 | G1 (p_族) | G2b (前向 argmax) | CORE | PASS |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for t in TG:
    for m in MD:
        for s in SD:
            k = f"{m}_{t}_s{s}"; c = J["criteria"][k]; o = F["cells"][k]
            c4 = (yn(c["C4"]) + f" ({c['r_price']:+.4f})") if "C4" in c else "—"
            g1 = (yn(c["G1"]) + f" ({c['null_p_family']:.3f})") if "G1" in c else "—"
            w(f"| {k} | {f4(c['r_pool'])} | {ci(o['pool']['ci95_k0'])} | {ci(o['pool']['ci95_k9'])} | {c['n_folds_positive']}/5 | {yn(c['C1'])} | {yn(c['C2'])} | {yn(c['C3'])} | {c4} | {g1} | {yn(c['G2b'])} ({c['spectrum_forward_argmax']}) | {yn(c.get('CORE', False)) if 'CORE' in c else '—'} | {yn(c.get('PASS_cell', False)) if 'PASS_cell' in c else '—'} |")

w("\n## T2 · 逐折样本外相关(Pearson / Spearman)\n")
w("| 格 | F1 2022H2 | F2 2023 | F3 2024 | F4 2025 | F5 2026→08-30 | 合并 r | 合并 ρ | 折内去均值 r | 仅 2023–26 r |\n|---|---|---|---|---|---|---|---|---|---|")
for t in TG:
    for m in MD:
        for s in SD:
            k = f"{m}_{t}_s{s}"; o = F["cells"][k]
            w(f"| {k} | " + " | ".join(f"{f['r']:+.4f} / {f['rho']:+.4f}" for f in o["folds"]) + f" | {o['pool']['r']:+.4f} | {o['rho_pool']:+.4f} | {o['r_within']:+.4f} | {o['r_2326']:+.4f} |")

w("\n## T3 · 幅度读数(描述)\n")
w("| 格 | 样本外 R² | 校准斜率 | 命中率 / 基率 | 预测五分位 q0…q4 的目标均值(n) |\n|---|---|---|---|---|")
for t in TG:
    for m in MD:
        for s in SD:
            k = f"{m}_{t}_s{s}"; o = F["cells"][k]
            w(f"| {k} | {o['oos_r2_vs_train_mean']:+.5f} | {o['calibration_slope']:+.3f} | {o['hit_rate']:.3f} / {o['base_rate']:.3f} | " + " · ".join(f"{q['mean_target']:+.2f} ({q['n']})" for q in o["quintiles"]) + " |")

w("\n## T4 · 偏移谱 r(k) = corr(p_i, T_{i+k})(k ∈ {0..3} 判; k < 0 只报, 机械)\n")
w("| 格 | k=−2 | k=−1 | **k=0** | k=+1 | k=+2 | k=+3 |\n|---|---|---|---|---|---|---|")
for t in TG:
    for m in MD:
        for s in SD:
            k = f"{m}_{t}_s{s}"; sp = F["cells"][k]["spectrum"]
            w(f"| {k} | " + " | ".join((f"**{sp[str(q)]['r']:+.4f}**" if q == 0 else f"{sp[str(q)]['r']:+.4f}") for q in (-2, -1, 0, 1, 2, 3)) + " |")

w("\n## T5 · 主导率分解(前向等权山寨−BTC 价差 S; β 逐折训练估计)\n")
w("| 格 | β_f(F1…F5) | Share_S | r(p, S) | r(p, e) | r(p, e) CI95 k=0 | k=9 |\n|---|---|---|---|---|---|---|")
for t in TG[:3]:
    for m in MD:
        for s in SD:
            k = f"{m}_{t}_s{s}"; d = F["cells"][k]["decomp"]
            w(f"| {k} | " + " / ".join(f"{b:.0f}" for b in d["beta_by_fold"]) + f" | {d['share_S']:+.3f} | {d['r_S']:+.4f} | {d['r_e']:+.4f} | {ci(d['r_e_ci95_k0'])} | {ci(d['r_e_ci95_k9'])} |")

w("\n## T6 · 零分布(日块置换, s42 特征, 500 次)\n")
w("| 量 | 值 |\n|---|---|")
w(f"| 族最大值 M 分位 50 / 90 / 95 / 99 | " + " / ".join(f"{J['null']['M_quantiles'][q]:.5f}" for q in ("50", "90", "95", "99")) + f" |\n| M 最大 | {J['null']['M_max']:.5f} |")
for t in TG[:3]:
    for m in MD:
        w(f"| 单格零分布 q95 {m}_{t} | {J['criteria'][m+'_'+t+'_s42']['null_q95_cell']:.5f} |")

w("\n## T7 · G2a 读数(W_FULL 同期关系)\n")
w("| 相关 | 种子 | k=−2 | k=−1 | k=0 | k=+1 | k=+2 | k=+3 |\n|---|---|---|---|---|---|---|---|")
for nm, key in (("c_N(NET, S) 只报", "c_N"), ("c_L(LONG, MKT)", "c_L"), ("c_S(SHORT, MKT)", "c_S")):
    for s in SD:
        w(f"| {nm} | s{s} | " + " | ".join(f"{g['G2a'][s][key][str(q)]:+.4f}" for q in (-2, -1, 0, 1, 2, 3)) + " |")

w("\n## T8 · 模型内部(描述; 不参与判决)\n")
w("Ridge: 五折标准化系数均值(括号 = 与均值同号的折数); LGBM: 五折 gain 占比均值。\n")
w("| 格 | 前 8 列 |\n|---|---|")
for t in TG:
    for s in SD:
        o = F["cells"][f"R_{t}_s{s}"]; Bm = np.array([[f["beta"][x] for x in FE] for f in o["ridge"]]); mu = Bm.mean(0); order = np.argsort(-np.abs(mu))[:8]
        w(f"| R_{t}_s{s} | " + ", ".join(f"{FE[i]} {mu[i]:+.3f} ({int((np.sign(Bm[:, i]) == np.sign(mu[i])).sum())}/5)" for i in order) + " |")
        o = F["cells"][f"L_{t}_s{s}"]; G = np.array([[f["gain"][x] for x in FE] for f in o["lgbm"]]); G = G / G.sum(1, keepdims=True); mg = G.mean(0); order = np.argsort(-mg)[:8]
        w(f"| L_{t}_s{s} | " + ", ".join(f"{FE[i]} {mg[i]:.3f}" for i in order) + " |")

w("\n## T9 · 折与覆盖\n")
w("| 折 | 训练行(保留 / 丢弃) | 测试行 | 测试插补格 | 零方差列 | 目标均值 NET s42 / s2027 | 训练目标均值 NET s42 |\n|---|---|---|---|---|---|---|")
for q, fo in enumerate(FO):
    a = F["cells"]["R_NET_s42"]["folds"][q]; b2 = F["cells"]["R_NET_s2027"]["folds"][q]
    w(f"| {fo} | {a['n_train']} / {a['n_train_dropped']} | {a['n_test']} | {a['n_test_imputed']} | {', '.join(a['zero_std_features']) or '—'} | {a['mean_target']:+.3f} / {b2['mean_target']:+.3f} | {a['train_mean_target']:+.3f} |")
w("")
open(T8 + "/receipts/TABLES_T8.md", "w").write("\n".join(out) + "\n")
print(f"T8_TABLES_DONE T8={J['T8']} lines={len(out)}")
