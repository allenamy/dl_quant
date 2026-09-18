#!/bin/zsh
# 主研究员自跑的 Q6 分段续跑平价 —— 不采信分支自述
# 接缝取 0913/0914(账本纪元切换 + 跨界结算最重), 与分支所选其一相同, 便于互证
set -e
D=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FP3_devices/q6
S=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/q6_lead
rm -rf $S; mkdir -p $S
PY=/usr/bin/python3
echo "装置 sha: $(shasum -a 256 $D/q6_shadow.py | cut -c1-32)"
echo "git 是否干净: $(cd /Users/haosiyu/Desktop/quant_research && git status --porcelain -- docs/fixprogram_2026-09-13/FP3_devices/q6/q6_shadow.py | wc -l | tr -d ' ') (0 = 干净, 跑的是已提交的树)"
echo

echo "[1/3] 单跑 20260808..20260918"
Q6_CHECKPOINT_OUT=$S/cp_single.json $PY $D/q6_shadow.py 20260808 20260918 $S/rec_single.json > $S/log_single.txt 2>&1
echo "     rc=$? $(tail -1 $S/log_single.txt | cut -c1-120)"

echo "[2/3] 上半 20260808..20260913 (接缝在 0913/0914)"
Q6_CHECKPOINT_OUT=$S/cp_h1.json $PY $D/q6_shadow.py 20260808 20260913 $S/rec_h1.json > $S/log_h1.txt 2>&1
echo "     rc=$? $(tail -1 $S/log_h1.txt | cut -c1-120)"

echo "[3/3] 下半 20260914..20260918 从 checkpoint 续跑"
Q6_CHECKPOINT_IN=$S/cp_h1.json Q6_CHECKPOINT_OUT=$S/cp_resumed.json $PY $D/q6_shadow.py 20260914 20260918 $S/rec_h2.json > $S/log_h2.txt 2>&1
echo "     rc=$? $(tail -1 $S/log_h2.txt | cut -c1-120)"

echo
echo "=== 比对 ==="
$PY - <<'EOF'
import json
S="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/q6_lead"
s=json.load(open(S+"/rec_single.json")); r=json.load(open(S+"/rec_h2.json"))
cs=json.load(open(S+"/cp_single.json")); cr=json.load(open(S+"/cp_resumed.json"))
print("counts 单跑:", s.get("counts"))
print("counts 续跑:", r.get("counts"))
print("counts 相同:", s.get("counts")==r.get("counts"))
print()
a,b=cs.get("state_sha256") or cs.get("self_sha256"), cr.get("state_sha256") or cr.get("self_sha256")
print("state_sha256 单跑:", a)
print("state_sha256 续跑:", b)
print("逐位相同:", a==b)
print()
S1=cs.get("symbols") or {}; R1=cr.get("symbols") or {}
print("名数 单跑/续跑:", len(S1), "/", len(R1), "名集相同:", set(S1)==set(R1))
d=[k for k in sorted(set(S1)&set(R1)) if json.dumps(S1[k],sort_keys=True)!=json.dumps(R1[k],sort_keys=True)]
print("逐名状态不同:", len(d), d[:8])
print()
es=json.dumps(s.get("exclusions"),sort_keys=True); er=json.dumps(r.get("exclusions"),sort_keys=True)
print("exclusions 相同:", es==er, "| 条数", len(s.get("exclusions") or []), "/", len(r.get("exclusions") or []))
print()
for lab,d_ in (("单跑",s),("续跑",r)):
    n=d_.get("notes") or {}
    fired={k:v for k,v in n.items() if any(t in k for t in ("post_merge","late","rebuild","contradiction","mismatch")) and v}
    print(lab, "三条新机制是否触发:", fired or "全部未触发")
EOF
echo "=== DONE ==="
