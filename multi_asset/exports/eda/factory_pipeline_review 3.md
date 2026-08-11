> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 独立审计) | **状态:** final | **作废条件:** 工厂管线/DSL/协议变更
> 审对象: `factory/{dsl,ledger,pipeline}.py`。协议: `factory_prereg.md` + `dsl_operator_audit.md` (0C 锁定)。独立对抗测: `exports/eda/factory_adversarial.py` → `/tmp/0c_factory_adv.json`。

# 工厂管线开炉前验收 — 0C

## 判词: **修后 GO** —— 一条一行修 (xsec_z NaN-非-0, 我对抗测发现的 closure(ii) 违反) 后开炉; 另两条非阻断 follow-up。双锁/holdout/null-主门 全部独立验证 sound。

## 1. 双锁独立复测 (不信 smoke, 自写对抗) — **全 PASS**
| 对抗 | 结果 |
|--|--|
| Stage-0 路径写 CANDIDATE (`_append(verdict=CANDIDATE, STAGE0_VERDICTS)`) | **PASS (PermissionError)** — Lock(i) 结构拦截 |
| fdr_q 驱动 CANDIDATE (无 stage1_stats) | **PASS (PermissionError)** |
| 篡改台账行 inc_ic 后 `verify()` | **PASS (verify False)** — hash-chain 抓改 |
| M 计全部行 (Bonferroni 分母) | **PASS (M==3, 含 REJECT 行)** |

- **Lock(ii) 额外确认 (读码):** stage1 门用**固定 z\*=4.42 (=z\*(M_max=10000))**, 非 z\*(当前M) —— 比"随 M 收紧"更保守且**不可 early-stop 游戏**; bonferroni_M 记 `M()+1` (累计含本行, 非幸存计数) 入 stage1_stats 供审。**分母不可被 BH triage 缩小** ✓。

## 2. holdout 排除核 (读码 + 运行) — **PASS**
- `HOLDOUT_YEAR=2026` 模块常量; `load_context` 硬编 `rows = where(base & (year != 2026))`。**非配置项, 无 param 可绕。** 运行确认: eval rows 年份 = **2022-2025**, 2026 不可达。2026 只在别处 (最终幸存者集) 开封一次 (§2.1/2.6)。✓

## 3. null 校准抽查 — **PASS (主 null); 一个非阻断缺口**
- **shuffle-eval null (主门, Reality-Check max-null):** 实测单因子 shuffle-null IC **mean 0.00112 / std 0.00323 ≈ 0** (天-块目标置换打断预测链); 真因子 IC −0.0156 清晰分离。**null 校准正确, z 计算 sane。** Reality-Check = 95 分位 max-over-factors null, 双门叠 Bonferroni 4.42 + day-block CI + 逐年符号。✓
- **⚠️ 非阻断缺口: random-formula 语法-偏置 null (我 §2.2 #2) 未接入门** —— `_random_formulas` 只在 smoke 里当**测试生成器**, 不是 stage1 的 null。主显著门 (shuffle-eval) 完整, 但**语法-偏置标定 null 缺失**。建议: 接为**诊断** (survivor IC vs 同深度随机公式 IC 分布), 早批前或早批中补, 不阻断双锁完整性。

## 4. 5 条闭合条件复测 — **(iii) PASS, (ii) 1 违反**
| 条件 | 对抗 | 结果 |
|--|--|--|
| (iii) 稀疏 leg 禁时序 | `ts_mean(king,6)` | **PASS (parser 拒)** |
| (iii) dense 时序 OK | `ts_mean(mom_4h,6)` | PASS (接受) |
| (iii) leg 进 conditional | `where(gt(rvol_24h,0),king,s2)` | PASS |
| (iii) SPARSE taint 传播 | `ts_mean(xsec_rank(king),6)` | **PASS (拒 — taint 穿过 xsec)** |
| (ii) div-by-0 → NaN | `div(mom_4h, sub(mom_4h,mom_4h))` | **PASS (全 NaN, 非 inf/0)** |
| **(ii) xsec_z 退化截面** | `xsec_z(常数截面)` | **★ VIOLATION (0-填充, sample=0.0; 应 NaN)** |

**★ 唯一阻断项 (一行修):** `dsl.py` `xsec_z` 退化分支 `np.zeros_like(x)` → **`np.full_like(x, np.nan)`**。severity 低 (真数据 100+ 币截面 std 恒 >0, 该分支近 dead; 纯常数行被下游 IC std-guard 排除), **但**: (a) 是我预注册闭合条件 (ii) 的明确违反; (b) 嵌套时 (如 `mul(xsec_z(x), y)`) xsec_z=0 会注入**真 0** (非 NaN) 污染该锚。一行修闭合, 开炉前补 + 重跑 closure(ii) 对抗测确认。

## 5. 其余 (读码)
- **intra-factory 去重 stub**: stage1 `accepted_facs=[]` 从不填充 (注释"would load prior ACCEPTs")。**batch-1 无碍** (无已 accept), **batch-2+ 前必接** (我裁定 (1) 的工厂内互查)。非开炉阻断。
- z\* 用 abs(z)≥4.42 (单侧 z\* 用于双侧幅度) 略宽 (严格双侧应 4.56), 但符号一致预筛使其近单侧, 差异微 —— 非阻断, 记录。

## 第一批口径确认 (GO 后)
确认与预注册一致: LLM proposer 出 K=100 (**永不见 holdout 数据/结果 — 防火墙由管线保证: 2026 不进 eval, LLM 只见 2022-2025 台账**); **LLM 每次迭代提的每条公式都计入累计 M** (台账单调 eval_id = Bonferroni 分母, 迭代非免费); 0B 跑管线台账记全部 (pass+fail); Stage-1 幸存者 (若有) → suppl-v2 五门 + 电池; holdout 2026 终局开封一次。✓

## 判词
**修后 GO** —— 补 xsec_z 一行 (NaN 非 0) + 重跑 closure(ii) 对抗测确认后开炉。双锁 (verdict-path + tamper + M-分母) / holdout 排除 / shuffle-null 主门 全部独立验证 sound, 不可 game。两条非阻断 follow-up: (i) random-formula 语法-偏置 null 接为诊断; (ii) intra-factory 去重 batch-2 前接。

---
**产物:** `exports/eda/factory_pipeline_review.{md,json}` · `factory_adversarial.py` · `/tmp/0c_factory_adv.json`。
