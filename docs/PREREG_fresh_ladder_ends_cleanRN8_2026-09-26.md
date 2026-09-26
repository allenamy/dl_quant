> **创建:** 2026-09-26 17:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(fresh) | **状态:** 读法与重判规则冻结;**四格引擎序列已存在(09-26 00:44Z–04:59Z 产出, 宕机前), 任何读数未计算** | **作废条件:** 下列任一被钉 sha 改变;或 §3 任一控制不过(⇒ 本读数 UNAVAILABLE, 不出任何 G)

# 冻结:FRESH 阶梯两端在干净 RN8 上的读法 + 逐臂重判规则(R25-05)+ Q2 四格映射

## 0. 时序声明(按「写于读数之前」须核「已产出/已送达」, 不是「我读没读」)

- 四格引擎序列**已经产出**(宕机前跑完, 见 `receipts/RECOVERY_INVENTORY_2026-09-26.json`)。
- **没有任何读数被计算或送达**:pod2 上除两个管线脚本外无任何文件引用 `SER_LAD2_*`(grep 实测);
  管线只打印 `BT_LAUNCH VERDICT=` 与 `FA_LADSAVE <sha>` 两类行, 不算 dbar;驱动的 stdout 在 Mac 端随宕机丢失,
  其内容也只可能是这两类行(`lad2_pipe.sh` f3805fba 全文可核)。
- ⇒ 本文**写于序列之后、读数之前**。这是比「写于运行之前」弱的保证, 照实写。

## 1. 四格(= Q2 的 模型 旧/新 × RN8 旧/真;其余数据、成员、32 条成交路径、现金引擎全同)

| 格 | 模型(King + 席位 + F10) | RN8 | 序列(sha256 前 12) |
|---|---|---|---|
| `N_old` | NEW_S | `news_2026-09-23/work/legs.npz` 18999e16(污染) | `SER_LAD_BASE_NEWS_s{42,2027}X` 1aa6a4cd8386 / 4d7dc7444b36 |
| `N_cln` | NEW_S | `news2_2026-09-23/work/legs.npz` **9ee5886f**(干净) | `SER_LAD2_CLEANRN8_NONE_s{42,2027}` 9ecf57b0fbb9 / eb9d2f04cf90 |
| `F_old` | FRESH | 18999e16(污染;FRESH 与 NEW_S 的 RN8 逐位相同) | `SER_LAD_BASE_FRESH_s{42,2027}X` 5244bf989691 / 14162531e8ee |
| `F_cln` | FRESH | **9ee5886f** | `SER_LAD2_CLEANRN8_ALLNEW_s{42,2027}` 30649459b7cc / 881cbe030d35 |

两端只换 `RN8` 一个数组(`fa_ladder` 自报 `swap_diff_cells RN8 = 639`, 四格相同;donor sha 9ee5886f 在 `FA_COMBO_RECEIPT` 内)。
**具名限定**:模型侧(King 的 `fund_now` 特征;FRESH f10_s42 与 NEW_S f10_s2027 的训练特征)仍带 `fund_replay`
污染(`7f0f4a464`:成员内 12 格)。本四格**只修组合层 RN8**, 不修训练层;Q2 的「随后用干净特征重训」仍未做。

## 2. 读数(全部用冻结 `news_stats.dbar` 7141ba42, import 调用;掩码与 `fa_ladread.py` 78fcb4b8 相同)

对每个种子 s ∈ {42, 2027}:

- `G_old = dbar(F_old − N_old)`(= 在案 `FA_LADREAD.json` 7600123b 的 G, 见控制 C0)
- `G_cln = dbar(F_cln − N_cln)`
- `ΔG = G_cln − G_old` —— **即 Q2 的交互差**;由 dbar 对两条序列的线性, 恒等于 `e_F − e_N`
- `e_N = dbar(N_cln − N_old)`, `e_F = dbar(F_cln − F_old)` —— RN8 更正对两端各自的效应
- 段:`pre2026`(**进门的唯一段**)、`2026_to_axis_end`(并排报 `2026_SEG_truncated`)、`fullwin_to_axis_end`
- 每个量的逐日序列按冻结 `news_stats.boot(·, 30)` 报 30 日块 95% 区间 —— **照报不作门**(E-0923-B)
- 四通道 `pnl / car / cst / unk / g` 与 `NET = pnl − car`(pre2026 与 2026 段);`tau / hold / halt` 逐格均值(Q5 要求的换手/持有/停机, 只报)

## 3. 控制(**任一 FAIL ⇒ UNAVAILABLE, 不出 G_cln / ΔG**)

- **C0 复现旧值**:本装置从 `SER_LAD_BASE_*` 与 `SER_LAD_{KZ,WL,F10,KZWL}_s*` 重算的 `G_old` 与 8 个 `d_old`,
  与 `FA_LADREAD.json` 的值 `|差| ≤ 1e-9`;每条输入序列按上表**字面 sha** 核对(不从任何收据抄 sha)。
- **C1 目标层因果**(先复现旧目标):对 FRESH 端, 用 `ADAPTER_SPEC_FRESH_s{seed}.json` 重新生成 FRESH 基线目标,
  **sha 必须等于 X 配置钉住的 5ee47aa2… / 88dd4d9a…**(旧目标文件已释放, 重生成即逐位复现旧值);NEW_S 端基线目标
  按钉住 sha 1014579872… / ac329ad9… 读现存文件。然后对四格:**第一个目标行不同的锚 ≥ 第一个 RN8 不同的锚**。
  若第一个 RN8 差异早于引擎轴起点, 本条**没有分辨力**, 如实记 `VACUOUS`(不记 PASS, 也不判 FAIL)。
- **C2 引擎层因果**:每格 32 条路径的 `r` 在「第一个目标行不同的锚」之前与对应旧格**逐位相同**, 且之后至少一条路径不同
  (非空转)。这条能抓「两端引擎配置除目标外还有别的不同」(那会让序列从第 0 锚就不同)。
- **C3 已知答案**:在 `F_cln` 的 pre2026 锚上每锚加 δ = 1e-5 ⇒ `G_cln` 必须**变大**, 且增量在「每日锚数 × δ × 1e4」的 ±5% 内;
  `dbar(N_old − N_old) == 0` 逐位;`dbar(F_old − N_old) == −dbar(N_old − F_old)`。
- **恒等式(自洽性, 不是控制, 单列)**:`|ΔG − (e_F − e_N)| ≤ 1e-9`。

## 4. 逐臂重判规则(判的是**在案**判词能否保留;逐臂 d 本身没有干净版)

判词函数 = 冻结 §4 原样:`d/G ≥ 0.5 且 |d| ≥ 2σ ⇒ CARRIES`;`|d| ≤ σ ⇒ DOES_NOT_CARRY`;其余 `INDISTINGUISHABLE`;σ = 1.0437(借用尺, 限定照旧)。

对每臂 a ∈ {KZ, WL, F10, KZWL} × 每种子:

- **R1(只换 G)**:`d = d_old`, `G = G_cln` 重套判词;与在案判词不同 ⇒ **RE-JUDGE**。
- **R2(d 的带)**:`B = |e_N| + max(|e_N|, |e_F|)`(pre2026)。在 `G = G_cln` 下, 判词在 `[d_old − B, d_old + B]` 上
  (端点 + 4001 点等距网格)不是常数 ⇒ **RE-JUDGE**。
  **具名假设 A1**:混合臂的 RN8 效应 `|e_a|` 不大于两端之一的最大值。它**未经验证**;R2 的「保留」只在 A1 下成立, 结果件必须照写。
- **R3(全局)**:`max_s B(s) ≥ σ` ⇒ **全部 8 格 RE-JUDGE**(RN8 更正的量级已达阶梯分辨尺, A1 承担的分量过大, 不再逐臂分)。
- **R4(2026 段结论 §6-4「FRESH 的 King 在 2026 反而有利」)**:以 2026_to_axis_end 段的 `e` 按 R2 式算 `B26`;
  任一种子 `d_KZ,2026 − B26 ≤ 0` ⇒ 结论 4 **RE-JUDGE**。`KZWL` 的 2026 段同法只报。
- **§6-1「资金费侧按构造不承载」**:无论读数如何, 措辞改为「本阶梯的替换没有改动资金费数组;RN8 更正使 G 变化 ΔG(区间 …)」
  —— 即复审 Q5 的限定成立与否由 ΔG 直接给出, 不再用「按构造」推出「不调节」。
- 输出:`RE_JUDGE` 清单(臂 × 种子 × 触发规则);未触发的臂**解除「待重判」**, 但带 A1 限定。

另报(不作门):每臂在 `G_old` 与 `G_cln` 下到最近判词边界的距离(lead 要求的「2σ 门两侧位置变化」)。

## 5. 不做什么

- 不据本读数改任何阈值;不补跑种子;不把 `ΔG` 的区间当门。
- 本文**不**对「月度 King 是否更好」下结论(那是 §6 的训练层/2026 主门问题, 见月度重训设计备忘)。
- 若 R1–R4 触发重判, 逐臂干净版需要 `fa_ladder` 的双 donor(RN8 取自 NC、被测数组取自 FRESH);该装置改动另行提交, 先于任何运行。

## 6. 装置

`multi_asset/exports/research/fanom_2026-09-24/devices/fa_lad2read.py`(与本文同一提交, 先于运行);
运行命令逐字写进收据 `receipts/FA_LAD2READ.json`。
