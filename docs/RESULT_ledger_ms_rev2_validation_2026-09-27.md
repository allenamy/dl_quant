> **创建:** 2026-09-27 07:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 结果(装置验证,不是书层读数) | **作废条件:** d10_build_ledger_ms.py 再改;或参照 e179071d / 旧 P2 bea6f575 被重建

# 结果:ledger_ms rev 2 验证(runbook 1c 的九月扩展装置)

> **读数后修订(解释性)。** 扩展模式下的对账规则是**在第一轮 V2 读到 NOT_RECONCILED(06:49Z)之后**改的。规则的内容是:某个月是本次新加入的归档月,而旧 P2 当时没有这个月的 zip,那么这个月的行由「只有 API」变为「两源都有」,这种变化是允许的;其他一切差异都不允许。
> - 这条规则在 rev 2.1 里写成(提交 7ee2cc6dd),rev 2.2 把所有不允许的差异合成一个计数(2080f76e6)。
> - 理由再充分,也是看过读数以后才改的规则,与 King 月训判据修订 1 同类处理。
> - 它的分辨力由下面 §2 的变异控制证明。三个变异都没有变红的话,规则作废。

## 1. 各轮与读数(均与各自起跑前声明的期望对照)

| 轮 | 装置版本 | 行 | 预声明 | 实测 | 一致 |
|---|---|---|---|---|---|
| r1(06:43Z) | rev 2 | V1:不带新选项 | 与 e179071d 逐位相同 | 数组 IDENTICAL,139 个键 IDENTICAL | 是 |
| r1 | rev 2 | V2:`--extra-months 2026-08` 加前缀对照 | RECONCILED、PREFIX_BITWISE、升级只出现在 2026-08 | PREFIX_BITWISE,升级 103,527 行,全部在 2026-08;**但结果是 NOT_RECONCILED** | **否**,我写的期望本身有误(见下) |
| r21(06:51Z) | rev 2.1 | V1 | 同上 | IDENTICAL | 是 |
| r21 | rev 2.1 | V2 | RECONCILED;允许升级 = 变化数 = 103,527;不允许 0 | RECONCILED 103,527 / 103,527 / 0;PREFIX_BITWISE | 是 |
| r22(06:55Z,07:00–07:36Z 暂停) | rev 2.2 | V1 | IDENTICAL | 数组与 139 个键 IDENTICAL | 是 |
| r22 | rev 2.2 | V2 干净 | RECONCILED;不允许 0;允许 103,527;PREFIX_BITWISE;前缀之后 0 行 | 完全如此 | 是 |

**r1 V2 为什么是 NOT_RECONCILED**:
- 折叠对账拿新账本和旧 P2 比 src 与 zip_iv 两列。旧 P2 的 2026-08 只有 API 数据,补上 8 月 zip 之后,这两列必然要变:src 从 1 变 3,zip_iv 从 NaN 变成有值。
- ft、rate、off 三列全部逐位相同。
- 所以是我当时写的期望错了,不是数据有问题。
- **缺口具名**:第一轮 V2 的收据文件(sha 726d4bf1…)已被 r21 的重跑脚本删除,违反「证据不许覆盖」。它的读数在 pod2 上 r1 的 run.log 与 v2.log 中,已归档进仓库 `r1/`。

## 2. 变异控制(lead 的条件:任一项不红 ⇒ 规则作废)

| 变异(只在内存里改 BTCUSDT 的 1 行) | 行 | 预声明 | 实测 |
|---|---|---|---|
| rate_extra:2026-08-01T00:00:00.001Z 的 rate 改 1 ulp | 544312 | NOT_RECONCILED,不允许 = 1,PREFIX_DIFFERS | NOT_RECONCILED,不允许 1(rate_d 1),PREFIX_DIFFERS 1 个名 |
| ft_extra:同一行的 fundingTime 加 1 秒 | 544312 | 同上 | NOT_RECONCILED,不允许 1(ft_d 1),PREFIX_DIFFERS 1 个名 |
| rate_prefix:2026-07-01T00:00Z 的 rate 改 1 ulp | 544219 | 同上 | NOT_RECONCILED,不允许 1(rate_d 1),PREFIX_DIFFERS 1 个名 |

**三项全红,且不允许的计数恰为 1 ⇒ 读数后修订的规则保留有分辨力,不作废。**

## 3. 收据

- 仓库:`multi_asset/exports/research/news2_2026-09-23/receipts/ledger_ms_rev2_2026-09-27/`,内含 r1/、r21/、r22/ 三个子目录,每个目录下有 run.log、各行的日志与 D10_LEDGER_MS_BUILD.json。
- pod2 产物目录:`/workspace/d10_ledgerms_rev2_2026-09-27/`,其中 v1b、v2b、r22_20260927T065456Z 保留;r1 的 v1、v2 已在 r21 起跑时删除(见上文缺口)。
- 装置:d10_build_ledger_ms.py rev 2.2,sha 1d7c9235…。
