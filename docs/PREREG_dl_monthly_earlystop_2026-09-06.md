> **创建:** 2026-09-06 02:0xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结先于数字; 单变量机制臂; 研究, 实盘零接触; owner: track-b-dl 执行 / lead 判读) | **受据:** `docs/RESULT_dl_monthly_gate_2026-09-05.md` §11(c280eca): 逐月折 best_ep ≤ 2 出现 10/20(s42 每折新种子)/ 6/20(s2027)/ 4/20(固定种子 42), 年折 0/4(best_ep 5–9); 固定种子只收回约 1/3 缺口, 冻结读法 (c) UNDECIDED | **用户字:** 09-05 "dl 加上最新的月份为什么就噪声抽样了, 这个结论听起来非常不 solid"; 战役令"不易轻易放弃, 轻易下结论" | **作废条件:** 判据在看数字后被改; 任何数字无脚本收据; 触碰实盘文件

# PREREG · DL 逐月折"早停选到近初始化模型"机制检验: best-epoch 下限 / 固定 epoch 两臂(单变量)

## 0. 问题与机制(VERIFIED 来源标注)
- 月折训练器(`retrain_2026-09/dl_monthly_wf_2026-09-05/pod_f10_train_monthly.py` sha 7bb39f8d, 逐字): EPOCHS 15, 余弦 LR, τ 由 0.5 退火到 0.1(L338); 每 epoch 在验证切片(训练锚末 15%)算 `va = mean(net) − LDD·ES5`(L367), 保留 va 最大 epoch 的权重并在训练末重载(L374–378); `best_epoch = argmax(va_curve)`(L428)。
- §11 事实(VERIFIED fold_configs): 逐月折 best_ep ≤ 2 的折 = 10/20(每折新种子 42 系)、6/20(2027 系)、4/20(固定种子 42); 年折 0/4(5–9)。ep0–2 的模型 τ ≈ 0.50–0.44 且只训了 1–3 个 epoch ⇒ 分数接近初始化, 与逐月折种子间一致性仅 0.53 一致。
- 假设 H(待检验): "月折劣于年折"(同种子固定种子配对 −0.116 [−0.284, +0.049]; 每折新种子 −0.172 [−0.342, −0.006], 每 gross bps/锚, 冻结主窗)的主要来源是验证/早停 regime 选到近初始化模型, 不是"新数据有害"。反假设: 早停只是伴随现象, 强制训满不改善书层净额。
- 为何不被既有受据覆盖: §10/§11 只改了种子规则, 没有动 best-epoch 选择; 门臂 R1–R4(RESULT §F)改的是换装规则, 也没动训练内部。

## 1. 臂(锁死; 都在固定种子 42、其余与 CONST(mE1c, sha 6003c2a2)逐字节同的月折训练器上, 只改 best-epoch 选择这一处)
- **FLOOR5**: 只在 ep ≥ 5 内选验证最优: `best_epoch = 5 + argmax(va_curve[5:])`(保留权重的判断同步改为 ep ≥ 5 且 va > best_va); 5 = 年折 best_ep 下沿。
- **FIX7**: `best_epoch = 7` 固定, 不看验证(7 = 年折 best_ep 中位); 训练仍跑满 15 epoch(LR/τ 日程不变), 只是重载 ep 7 的权重。
- **恒等断言(先于臂)**: FLOOR 规则取下限 0 时, 对至少 1 个实跑折的预测数组与 CONST 同折逐位相同(npz sha 相等; 同折 config 除 `best_epoch_rule` 外全等)。除选择规则与自报元数据外, 代码路径零改动(EPOCHS/LR/τ/优化器/禁运 1 锚/验证切片 15%/输出格式全同), diff 归档。
- 元数据: 每折 config 自报 `best_epoch_rule`, `best_epoch`, `va_curve`(全 15 点), `alpha_curve`, `seed_fold = 42`; 白名单断言同 §11。

## 2. 装置与读数(与 §10/§11 同法, 不新造)
- 20 折(2025-01→2026-08 各一)→ `merge_mwf2.py` 拼接(断言 20 月各恰一次)→ 拼行 spl42(2025 前取年折 s42 行)→ `w10_health.py`(sha 8684d9a9)体检主臂形态回放 → `judge_gate_addendum2.py` 同形态判官(冻结主窗 2025-03→2026-08-10 为主, 全窗 2025-01→ 并列; UTC 日块 bootstrap 2000, 种子 20260905; 每 gross bps/锚)。
- 主配对(同种子 42): ARM − yearly_s42; ARM − CONST42。附: ARM − yearly_s2027(拼 spl27)。
- 副读数(只报): best_ep 分布(20 折); 分数层 ΔIC(AD2-4 同法); 相邻月一致性(`agreement.py` 同法); 换手; maxDD; 逐年 2025 全年 / 2026≤cut; 去最佳月。

## 3. 冻结读法(先写后看)
- **(A) 早停是主因**: 两臂中至少一臂满足 ARM − yearly_s42 CI95 ∋ 0 且 Δ ≥ −0.05, **且**同一臂 ARM − CONST42 CI95 下界 > 0。
- **(B) 早停非主因**: 两臂 ARM − yearly_s42 CI95 上界都 < 0。
- **(C) 其余 UNDECIDED**(含"只有一半条件成立")。
- 比较家族: 本文 2 臂 + §10/§11 的 2 格 = 4; 单侧 5% 期望假阳性 0.2。
- **部署含义(先写后看)**: (A) ⇒ 冻结候选 `PREREG_dl_freeze_yearly_2026-09-05.md` 撤回, 改立"月度重训 + best-epoch 规则修正"候选(训练配方改动 = RUNBOOK 改动 + 用户字; 仍需前向影子或第二仪器再验一次, 不直接部署); (B) ⇒ 冻结候选维持, 其受据以"形态依赖 + (c) UNDECIDED"呈用户; (C) ⇒ 两候选都留, 如实报用户。任何情况实盘不动。

## 4. 归档与资源
- `multi_asset/exports/research/retrain_2026-09/dl_monthly_gate_2026-09-05/addendum_earlystop/`(补丁与 diff、恒等收据、fold_configs、shard_results、results、replay_logs、logs/commands.txt、SHA256SUMS、MANIFEST 段); RESULT 写入 `RESULT_dl_monthly_gate_2026-09-05.md` §12 + 首行元信息一行。
- GPU: pod2, 2 臂 × 4 分片(与 §11 同分片法), 预计 ≈ 1 h; 不与其它 GPU 任务并行; 监视器带存活探针(ps/nvidia-smi 计数, 教训 pod 配额静默杀任务); 磁盘先查配额余量(263 GB 顶)。
