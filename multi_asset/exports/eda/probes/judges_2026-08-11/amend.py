import io, sys

p = '/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/PREREG_chase_opportunity_cost_2026-08-03.md'
s = open(p, encoding='utf-8').read()

subs = []

subs.append((
 '9. **★ 裁定版新增的唯一未决: §5-2bis 的平衡检验在 sd 步是否也跑一次**(§11-1) —— 已提出, 未生效, 等 team-lead 一句话。',
 '9. **§5-2bis 的平衡检验在 sd 步是否也跑 —— 已于 07:5xZ 批准生效**(§11-1), 不再是未决项。**裁定版-A 无新增未决。**'))

subs.append((
 '| **裁定版(本版)** | `PREREG_chase_opportunity_cost_2026-08-03.md` | 见侧车 | 07:44Z | **当前生效** |',
 '| 裁定版 | `…_RULING_0744Z.md` | `e0547c0495a526185cb99bcc1e581c806ab67232925f1ab60a7a8d7594119336` | 07:44Z | 八条裁定回填; §11-1 当时仍标为「提出」 |\n'
 '| **裁定版-A(本版)** | `PREREG_chase_opportunity_cost_2026-08-03.md` | 见侧车 | 07:5xZ | **当前生效** —— §11-1 获批生效 + Q7 措辞升为通则 |'))

subs.append(('## 12. 冻结(裁定版)', '## 12. 冻结(裁定版-A)'))

subs.append((
 '**本版 = 裁定版**, 内容定稿 **2026-08-03T07:44Z**。它在前身冻结版之上只回填了八条裁定(§11), 未改动任何在裁定之前已冻结的口径。',
 '**本版 = 裁定版-A**, 内容定稿 **2026-08-03T07:5xZ**。它在 07:44Z 裁定版之上只做两处: (i) §11-1 的 sd 步平衡检验由「提出」转为「生效」, 并换用 team-lead 更强的论证; (ii) §10 的 Q7 措辞被采纳为通则。**未改动任何在裁定之前已冻结的口径。**'))

subs.append((
 '→ **07:44 UTC 裁定版** | **Session:** 0C (接替 04:5xZ 失能会话) | **状态:** **frozen — 裁定版, 八条裁定已全部回填(§11), 当前生效** | **取代:** `PREREG_chase_opportunity_cost_2026-08-03_FROZEN_pre-ruling_0731Z.md`(SHA `5cc3df11a286d11b8e725d691c80e7bf71ab8e3d90dcb84159f4d5b11cc006a5`, **保留不删** —— 它是"口径写在裁定之前"的唯一证据)',
 '→ 07:44 裁定版 → **07:5x UTC 裁定版-A** | **Session:** 0C (接替 04:5xZ 失能会话) | **状态:** **frozen — 裁定版-A; 八条裁定已全部回填(§11)且 §11-1 已获批生效; 当前生效** | **取代:** `…_RULING_0744Z.md`(SHA `e0547c04…`) 与 `…_FROZEN_pre-ruling_0731Z.md`(SHA `5cc3df11…`), **两份均保留不删** —— 后者是"口径写在裁定之前"的唯一证据'))

for a, b in subs:
    n = s.count(a)
    print(('OK   %d x  ' % n) + repr(a[:46]) if n == 1 else ('*** MISS/DUP n=%d ***  ' % n) + repr(a[:46]))
    s = s.replace(a, b)

open(p, 'w', encoding='utf-8').write(s)
print('written')
