#!/usr/bin/env python3
"""扫描一段【拼装后的完整】定时任务 prompt, 找实验分项结果量(复审 R5B-08)。
规则: 实验臂词(chase / forced / join / behind / requote / direct / 臂 / 重报价 / 重挂 / 二次拒)前后 60 字符内出现
带单位或小数的数值(%, pp, bps, 小数)即判为疑似分项结果; 白名单只含设计常数(behind 占比≈0.50)与计数说明。
退出码 0 = 干净, 1 = 有命中(逐条印出位置与片段, 片段中的数字以 # 遮蔽, 扫描器本身不转述数值)。"""
import re, sys
ARM = re.compile(r"chase|forced|join|behind|requote|direct|臂|重报价|重挂|二次拒", re.I)
NUM = re.compile(r"[-+−]?\d+(?:\.\d+)?\s*(?:%|pp|bps|bp)|[-+−]?\d+\.\d+")
WHITELIST = [re.compile(p) for p in (r"behind\s*占比\s*≈\s*0\.50", r"behind\s*share\s*≈?\s*0\.50")]
# 用户模板原文 ③ 的书级阈值句(逐字; 这些是书级合计阈值, 不是分项结果)—— 只认完全一致的原句
EXACT_OK = ["fills maker 占比(≥90%), 换手(稳态2-5.5%), 费用 bps(maker 1.80-2.3 带), chase_arm_assigned 分臂计数, placement behind 占比≈0.50"]


def scan(text):
    for ok in EXACT_OK:                                   # 白名单原句整段替换为同长占位, 位置不变
        text = text.replace(ok, "·" * len(ok))
    hits = []
    for m in ARM.finditer(text):
        a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
        seg = text[a:b]
        if any(w.search(seg) for w in WHITELIST):
            seg_wo = seg
            for w in WHITELIST: seg_wo = w.sub("", seg_wo)
        else:
            seg_wo = seg
        if NUM.search(seg_wo):
            hits.append((m.start(), re.sub(r"\d", "#", seg.replace("\n", " "))))
    return hits


if __name__ == "__main__":
    t = open(sys.argv[1], encoding="utf-8").read()
    h = scan(t)
    for pos, seg in h: print(f"HIT @{pos}: …{seg}…")
    print(f"scan_blind_prompt: {'CLEAN' if not h else f'{len(h)} HIT(S)'} · chars {len(t)}")
    sys.exit(1 if h else 0)
