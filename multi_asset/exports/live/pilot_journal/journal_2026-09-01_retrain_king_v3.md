> **创建:** 2026-09-01 06:1xZ | **Session:** 6737834a(重训战役) | **状态:** 完成 | **作废条件:** bundle v3 被后续版本替换

# 月度重训首跑 · king bundle v3 换装(RUNBOOK_monthly_retrain_2026-09 全流程)

## 门收据(全部冻结判据, 无一调整)
- 门①全列(pod_gate1_full): 18/18 corr≥0.9990(15列 1.000000; ema_v1 0.999715/v2 0.999075/iv 0.999932), 重叠 9,943 锚
- 门② fold IC: 2024 +0.0548(基线 0.0574, Δ−0.0026) / 2025 +0.0630(0.0628, Δ+0.0002), 带 |Δ|≤0.004
- 门③ ic26: +0.0584(在役 pinned 0.0571, Δ+0.0013), 带 ±0.006
- 守卫: 净 1.024 bps/锚, 夏普 2.28 ∈ [2.27,2.57]
- acceptance: 4/4 ALL_GREEN(A2 平价 179 锚中位 corr 0.9999 min 0.9987)
- bundle sha256: 59546b545d51213d(两端一致); files 8, 93MB; symbols_live=450 keep=78 钉死

## 守卫红→绿的完整判官链(判据未动)
初跑守卫 1.92 红 → 拒绝换版 ✓ → 对账(vs 八月 leg_returns 原件): rev24 corr 1.000000 精确 / fund 0.86-0.94 散开
→ 干预实验(同码换 v1 正典面板): fund 腿 vs 八月逐位一致 + 守卫 2.49 带内 ⇒ 我的 v2ext ema_v1(对正典 0.9997)为偏离仪器
→ 修复 = splice 面板(≤08-15 正典逐字; 尾 96 锚 EMA 以正典末行续算)→ 守卫 2.28 带内 ⇒ 换版
归因: 2.49(正典无尾) − 08-15后96锚真实拖累(该窗 v1iv 形态净 −3.6bps/锚) = 2.28。带下沿属实况非仪器。

## 换装执行(静默窗 06:0x-06:1xZ)
launchctl bootout → 备份(shadow_bundle.aug20260816_backup + tar)→ untar v3 → acceptance 4/4 → bootstrap 重启
producer state=running, SHADOW_OFFSET_MIN=16(launchd env), next=08:16:00Z。首个新代锚 = 09-01 08:00Z(booster_sha 变更即留痕)。

## 战役捕获的缺陷(D1-D5 全册 retrain_2026-09/MANIFEST.md)
D2 宇宙 glob 旁路(险: symbols_live=funding目录数, 已播829 ⇒ 原样跑=宇宙静默刷新, 违分离部署裁定) · D3 interval 推断污染(zip 真值修复) · D5 列门 0.999 放行载荷偏差(秩+递归放大 0.4 夏普, 守卫层按设计兜住; 修复=正典续算 splice)· 另: zsh 变量不分词静默死守望 + fee 布尔求和自误(锚排查内当场纠) 
