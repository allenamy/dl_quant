#!/usr/bin/env python3
"""t4b_tables.py — renders receipts/TABLES_T4b.md from the T4b receipts (formatting only). Mac, read-only on receipts.
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4b_tables.py"""
import json, os, hashlib, time
HERE = os.path.dirname(os.path.abspath(__file__)); T4B = os.path.dirname(HERE); R = T4B + "/receipts"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
L = json.load(open(R + "/RECEIPT_T4b_live_judge.json")); F = json.load(open(R + "/RECEIPT_T4b_facts_v2main.json")); Z = json.load(open(R + "/RECEIPT_T4b_freeze_inputs.json"))
out = ["> 由 `devices/t4b_tables.py` 渲染: `RECEIPT_T4b_live_judge.json`(%s)、`RECEIPT_T4b_facts_v2main.json`(%s)、`RECEIPT_T4b_freeze_inputs.json`(%s), %s" % (
    sha(R + "/RECEIPT_T4b_live_judge.json")[:16], sha(R + "/RECEIPT_T4b_facts_v2main.json")[:16], sha(R + "/RECEIPT_T4b_freeze_inputs.json")[:16], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), ""]
f1 = F["result"]["F1_served_model_normalisation"]; f2 = F["result"]["F2_stored_zeros"]
out += ["## T1 · 在役 V2MAIN 标准化识别与存储零", "",
        "| 量 | 模型 | 按存储列重算 | 第 80 列换 v1 重算 |", "|---|---|---|---|",
        "| 第 80 列 mu | %.6e | %.6e | %.6e |" % (f1["col80"]["model_mu"], f1["col80"]["stored_mu"], f1["col80"]["v1_alt_mu"]),
        "| 第 80 列 sd | %.6e | %.6e | %.6e |" % (f1["col80"]["model_sd"], f1["col80"]["stored_sd"], f1["col80"]["v1_alt_sd"]),
        "| 第 81 列 mu / sd | %.6e / %.6e | %.6e / %.6e | — |" % (f1["col81"]["model_mu"], f1["col81"]["model_sd"], f1["col81"]["stored_mu"], f1["col81"]["stored_sd"]),
        "", "171 列最大相对差: mu %.2e, sd %.2e(子样本 %d 行, %d 个训练锚); 判读: %s" % (f1["mu_relmax_all171"], f1["sd_relmax_all171"], f1["n_rows"], f1["n_anchors_tr1"], f1["verdict_col80_caliber"]), "",
        "存储零(第 80 列): 全体零占 %.4f; 零格属于 450 名内的占 %.4f; 450 名内零占 %.4f; 零格中面板 v0 非零占 %.4f; 450 名内零占逐年 %s" % (
            f2["col80"]["zero_share"], f2["col80"]["zero_cells_in_live450_share"], f2["col80"]["zero_share_among_live450_cells"], f2["col80"]["zero_cells_with_panel_v0_nonzero_share"],
            json.dumps({k: round(v, 5) for k, v in f2["col80"]["zero_share_live450_by_year"].items()})), ""]
out += ["## T2 · 冻结输入与成员事实", "", "前向锚: %s; GATE CACHE: %s" % (", ".join(time.strftime("%m-%d %HZ", time.gmtime(a)) for a in Z["forward_anchors"]), json.dumps(Z["gate_CACHE"])), "",
        "成员事实: " + "; ".join("%s 成员 %d 陈旧 %d 非450 %d" % (time.strftime("%m-%d %HZ", time.gmtime(x["anchor"])), x["members"], x["stale_members"], x["nonlive_members"]) for x in Z["member_facts"]), ""]
G = L["gates"]
out += ["## T3 · 门", "", "| 门 | 读数 | 判 |", "|---|---|---|",
        "| PCB served ≡ 线上 | " + "; ".join("%s king %.1e/%s combo %s/%s" % (time.strftime("%m-%d %HZ", time.gmtime(p["anchor"])), p["king_Linf"], p["king_content_sha_equal"], p["target_live_Linf"], p["target_combo_Linf"]) for p in G["PCB"]["per_anchor"]) + " | %s |" % ("PASS" if G["PCB"]["PASS"] else "FAIL"),
        "| PC-INJ | " + ", ".join("%s %s" % (k, v) for k, v in G["PC_INJ"].items() if k != "PASS") + " | %s |" % ("PASS" if G["PC_INJ"]["PASS"] else "FAIL"),
        "| ONE-PLACE | " + ", ".join("%s %s" % (k, v) for k, v in G["ONE_PLACE"].items() if k != "PASS") + " | %s |" % ("PASS" if G["ONE_PLACE"]["PASS"] else "FAIL"),
        "| ZH | " + json.dumps({k: v for k, v in G["ZH"].items() if k != "PASS"}) + " | %s |" % ("PASS" if G["ZH"]["PASS"] else "FAIL"),
        "| V1R | " + json.dumps({k: v for k, v in G["V1R"].items() if k != "PASS"}) + " | %s |" % ("PASS" if G["V1R"]["PASS"] else "FAIL"),
        "| SA | " + json.dumps({k: v for k, v in G["SA"].items() if k != "PASS"}) + " | %s |" % ("PASS" if G["SA"]["PASS"] else "FAIL"),
        "| SL | " + json.dumps({k: v for k, v in G["SL"].items() if k != "PASS"}) + " | %s |" % ("PASS" if G["SL"]["PASS"] else "FAIL"), ""]
out += ["## T4 · 汇总", "", "```", json.dumps(L["summary"], indent=1, default=str), "```", "",
        "## T5 · 逐锚: V2MAIN 第 80 列 v0 臂 − served 臂", "",
        "| 锚 | 打分名 | V2MAIN 分数 Spearman | 十分位变动 全部 / 4h / 1h / 8h | 列 80 served/v0 中位 4h / 8h | fc 状态 归一 L1 | combo target_live L∞ / 归一 L1 / 相关 | w3m 相同 |", "|---|---|---|---|---|---|---|---|"]
for r in L["per_anchor"]:
    v = r["v2"]; d = v["decile_change"]; sh = lambda c: "%d/%d" % (d[c]["changed"], d[c]["n"])
    rr = v["col80_served_over_v0_median"]; ct = v["combo_target_live"]
    out.append("| %s | %d | %.5f | %s / %s / %s / %s | %s / %s | %s | %.2e / %.4f / %.6f | %s |" % (r["utc"], r["scored"], v["f10_spearman"], sh("all"), sh("4h"), sh("1h"), sh("8h"),
               ("%.6f" % rr["4h"]) if rr["4h"] is not None else "—", ("%.6f" % rr["8h"]) if rr["8h"] is not None else "—", ("%.4f" % v["state_fc"]["L1_norm"]) if v["state_fc"]["L1_norm"] is not None else "—",
               ct["Linf"], ct["L1_norm"], ct["corr"], v["w3m_equal"]))
out += ["", "## T6 · 逐锚: 席位播种行 K1 臂 − served 臂", "", "| 锚 | w3m king served → seatK1 | king 段目标 L∞ / 归一 L1 | combo target_live L∞ / 归一 L1 | kc 状态 归一 L1 | fc 状态 归一 L1 | king X/pred 逐位同 |", "|---|---|---|---|---|---|---|"]
for r in L["per_anchor"]:
    s = r["seat"]; kt = s["king_target"]; ct = s["combo_target_live"]
    out.append("| %s | %.4f → %.4f | %.2e / %.4f | %.2e / %.4f | %s | %s | %s |" % (r["utc"], s["w3m_served"][0], s["w3m_seatK1"][0], kt["Linf"], kt["L1_norm"], ct["Linf"], ct["L1_norm"],
               ("%.4f" % s["state_kc"]["L1_norm"]) if s["state_kc"]["L1_norm"] is not None else "—", ("%.4f" % s["state_fc"]["L1_norm"]) if s["state_fc"]["L1_norm"] is not None else "—", s["king_stage_X_pred_bitwise"]))
open(R + "/TABLES_T4b.md", "w").write("\n".join(out) + "\n"); print("wrote", R + "/TABLES_T4b.md", len(out))
