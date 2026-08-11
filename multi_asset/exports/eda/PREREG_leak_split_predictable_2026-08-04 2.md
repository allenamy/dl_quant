> **创建:** 2026-08-04 15:5x UTC | **Session:** team-lead (6737834a) | **状态:** FROZEN —— 本文在**看到任何读数之前**落盘并封 SHA | **作废条件:** 分解方式改变 ⇒ 另出修订版, 不得静默调整

# PREREG — 把 `leak` 拆成【可预测】与【不可预测】两半, 判 plain 的 −0.054 是本事还是残留泄漏

## 0. 为什么需要这一次(问题陈述, 不含答案)

§8-2 实测: clean_plain 的 `corr(tilt, leak)` = **−0.0543** (95%CI [−0.0867,−0.0220], **不含 0**), clean_xattn = −0.0171 (**含 0**)。
已排除的解释: "被 causal 项渗透" —— 条件化后 plain 略**强**非变弱(见 `RESULT_lookahead_exploitation_2026-08-04.md` §3)。

**剩下的两个互斥解释:**
- **(a) 本事**: `leak[t] = Σ market[t+1…t+11]` 里有一部分**在 t 时刻就可从市场历史预测**(市场自身有动量/反转)。一个真有择时内容的模型, 其 β 倾斜本来就该与这一部分相关 —— **那是 alpha, 不是泄漏。**
- **(b) 残留泄漏**: 相关落在**不可预测**的那一半 ⇒ 模型仍在触及 t 之后才产生的信息 ⇒ 修复不完整。

**⇒ 这是一个可测的事实, 不是一次解读。**

## 1. 装置

```
预测因子(全部因果, 同一条 market 序列):
   m1 = Σ market[t−0…t] · m4 = Σ market[t−3…t] · m12 = Σ market[t−11…t]
   m24 = Σ market[t−23…t] · m72 = Σ market[t−71…t]
拟合: 扩张窗 OLS —— 用【严格早于 i 的行】拟合, 预测第 i 行。burn-in = 前 20% 锚(不出读数)。
   leak_pred[i]   = 该 OLS 在第 i 行的预测值
   leak_unpred[i] = leak[i] − leak_pred[i]
判据量: corr(tilt, leak_unpred), 95%CI 用与 §8-2 同款 moving-block bootstrap(block=60, nboot=2000)
```

**★ 为什么必须扩张窗而不是全样本拟合。** 全样本 OLS 会让 `leak_pred` 吸收噪声, `leak_unpred` 被人为缩小 ⇒ **系统性地把结论推向"plain 清白"** —— 而那正是本文作者已经表达过倾向的方向。**用一个偏向自己结论的估计器, 是本项目今天刚登记过的错误的翻版。** 扩张窗使 `leak_pred` 只含真正事前可得的部分。

## 2. ★ 伙伴判据(先判, 不过则全表作废)

**冻结(脏)run 的 `corr(tilt, leak_unpred)` 必须 CI 排除 0 且明显为正。**
它们**看过真实兑现的 leak**, 其相关必须活在**不可预测**那一半 —— 若连它们也被洗掉, 说明"扣掉可预测部分"这一步把真实泄漏利用一起扣没了, **这台仪器读不出它要读的东西, 本表不得为任何一支背书。**
(与 `RESULT_lookahead_exploitation_2026-08-04.md` §3 的伙伴判据同构; 那一次通过了, 这一次必须重新过。)

## 3. 判读规则(预写死, 看数前)

| 条件 | 结论 |
|---|---|
| 伙伴判据不过 | **全表作废**, 选臂不由本文推进; 回到用户裁定 |
| plain 的 `corr(tilt, leak_unpred)` **CI 含 0** | **(a) 成立** —— plain 的 −0.054 落在可预测那一半 = 择时本事 ⇒ **§8-2 对 plain 的"不过"是判据字面未为此留条款所致, plain 清白** |
| plain 的 CI **排除 0** | **(b) 成立** —— 残留泄漏通路存在 ⇒ **plain 出局, 上 xattn** |

**同时报 xattn 的同一读数**(它 §8-2 已过, 此处是一致性检查): 若 xattn 在 unpred 上反而排除 0 而 plain 含 0, 属于**预期外形态**, 两支都不放行, 回审计。

## 4. 本文不建立什么

- 不建立"部署路径合法"(S1-fallback vs S2 另议, 见 #39 件二)。
- 不建立哪一支 IC 更高(已知打平 t=−0.83)。
- 不建立 §8-2 判据本身该不该改写 —— 本文只回答"plain 那个数是 (a) 还是 (b)"。判据文本的修订须另出。

## 5. 执行

`measure_leak_split.py`(新写), 复用 `measure_lookahead_exploitation_s1.py` 的 tilt/market/重抽样构造(import, 不复制)。四个 run 全测: clean_plain / clean_xattn / frozen_plain / frozen_xattn。
