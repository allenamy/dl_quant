> **创建:** 2026-09-12(GATE P 与机制门跑完之后、任何 P&L 数字之前) | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME(子代理 r15) | **状态:** 生效, 只改两处程序性细节, **不改臂、不改阈、不改读法** | **主文:** `PREREG_r15_structural_2026-09-12.md` sha256 097769b087fa0834fb780062bf710134d7e3a67555174de5c26c1668c455f6fc(不变)

# PREREG AMENDMENT 1 · r15

## A1. ENV 白名单枚举(§12): 加入 `LC_CTYPE`
pod2 的 venv Python 在 `env -i PATH=... HOME=/root` 下按 PEP 538 把 `LC_CTYPE=C.UTF-8` 写进 `os.environ`; 装置的白名单断言在第一次启动时**如设计般红了**(`ENV WHITELIST VIOLATION ['LC_CTYPE']`, 见 `receipts/r15_drive_stdout.log` 首次运行)。按 §12 的规则(枚举后显式列入, 与 r12 处理 macOS 注入的 `LC_CTYPE`/`__CF_USER_TEXT_ENCODING` 同法), 驱动器/判官/null/机制门的启动白名单 = `PATH,HOME,LC_CTYPE`。被驱动器启动的**装置进程**不受影响: 它们拿到的是驱动器构造的精确 env 字典(收据 `runs.*.env` 逐项列出, 不含 LC_CTYPE 以外的任何注入; 装置进程内 Python 同样会自加 LC_CTYPE)。

## A2. 判官对机制门的断言收窄到主文 §4 的 STOP 条款
主文 §4 有两条: (i) **A0 侧**「(b) ≥ 25% 且 (d) ≥ 0.05 bps, 否则 STOP」; (ii) **ARM-F 侧**「被标记且 smr<0 的名数必须恰为 0, 否则 FTPOS 不是持仓零, **报 FAIL**」。机制门装置 `r15_mechgate.py` 把二者合成一个 `gate.PASS`, 判官原本断言该合成值 —— 这比主文更严(把「报 FAIL」写成了「STOP」)。实测: (i) 两种子 PASS(75.5% / 0.2238 bps; 75.1% / 0.2164 bps); (ii) **FAIL by the letter**: W_ALPHA 上 s42 有 36(双链标记)/ 72(deep)个名-锚、s2027 有 24 / 58 个名-锚 smr<0(每锚 0.004 个; 漏出 gross 均 0.000%, max 0.19%; 付 carry 0.0000 bps)。逐名核查(`receipts/r15_mechgate_stdout.log` 后的一次性诊断, 数字入 RESULT §2): 这些名-锚**全部** `W`(kill 后的 smb)> 0 且**没有一个**是被 kill 的名 —— 它们是执行器 redemean(装置 L314-320 = `dl_quant_live/signal/legs.py:124` 语义)把极小的正权重减去非零集均值后翻负所致(均值位移中位 6.2e-5, max 1.78e-3), 是 FTPOS **下游**的执行器重塑, 不是 FTPOS 的零失效。
处理: 判官改为只断言 (i)(主文的 STOP 条款), (ii) 的结果按主文原样**报 FAIL** 并写进收据 `mechgate_F_position_zero_pass` 与 RESULT。**§11 读法一字未改。**

## A3. 数字标签
本文所有数字来自 `receipts/RECEIPT_r15_mechgate.json` 与 `receipts/r15_mechgate_stdout.log`(VERIFIED, 本轮实测)。
