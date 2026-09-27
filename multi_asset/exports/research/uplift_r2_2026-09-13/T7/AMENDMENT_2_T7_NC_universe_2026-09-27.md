> **创建:** 2026-09-27 07:4xZ(`date -u` 07:40:22Z 起草) | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(alloc,受 lead 派) | **状态:** AMENDMENT-2 **草稿,待 lead 冻结**;**写于任何 T7 候选读数之前**:至今没有计算任何「溢价 × 收益」数字,候选数组本身也还没有构建(守卫与构建装置从未运行) | **对象:** `AMENDMENT_T7_NC_2026-09-27.md`(冻结提交 21ecc60f5)§0 表第 1 行 | **裁定依据:** lead 07:3xZ(采纳 AMENDMENT-2,宇宙 = book_universe.py 的产物;缺产物的锚退回「kc 有限且 ≠ 0」并报锚数) | **作废条件:** 下文任一输入 sha 变化;或 lead 改判

# AMENDMENT-2(T7 → NC):宇宙改为在役书的正式宇宙

**只改宇宙这一行**,外加一条由它直接引出的行级规则(§2)。其余条款照 AMENDMENT(21ecc60f5)与冻结版(62c6da52)不变。

## 0. 为什么要改(零收益证据,A 段收据 a327f167a 与 07:3xZ 的 pod2 核对)

每锚平均名数,依次为 2023 / 2024 / 2025 / 2026:

| 集合 | 名 / 锚 |
|---|---|
| TRD-01 W24H 掩码(AMENDMENT 第 1 行原定) | 190 / 277 / 444 / 588 |
| book_legal = book_universe 的 pit ∧ TRD ∧ crypto | 179 / 262 / 398 / 421 |
| **LIVE = book_legal ∧ 当锚成员**(chain 能给权重的集合) | **178 / 261 / 360 / 362** |
| combo 的 kc 有限且 ≠ 0 | 176 / 258 / 343 / 271 |
| A0 C0 合格集(冻结版) | 176 / 258 / 354 / 281 |

- kc ≠ 0 的格全部落在 LIVE 内(越界 0 格)。
- 反过来,LIVE 内 kc = 0 的格:2023 年 3,607,2024 年 8,282,2025 年 38,458,2026 年 141,723。
- 这些主要不是「名数为奇数时中位名 kc 恰为 0」造成的(那每锚最多 1 格)。它们是 King 或资金费分数缺失的名:书能给它们权重,但没有基线分数。
- ⇒ TRD 比书的实际宇宙宽出约 100–310 名 / 锚(2025–26),AMENDMENT 第 1 行须改。

## 1. 新定义

- **U_NC(i) = LIVE(i) = align(pit)(i) ∧ TRD-01 W24H(i) ∧ crypto ∧ members(i)**。这正是 `news2_combo.py`(L41–48 与 members)交给 chain 的那个对象。各部分:
  - `align` 与 pit 来自 `book_universe.py`(sha256 90e332cc…),读 `/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz`(sha256 3ee838cf…);
  - crypto 来自 `P1_members_2025H2on.npz`(2323623f…);
  - members 来自 `NEWS_FEATURES.npz` 的 m / off(3c886a2b…),**只取这两个键**。
- **与 lead 措辞的对应**:lead 写的是「book_universe.py 的产物」。book_universe 本身只给出 pit;在役书在其上还与 TRD、crypto、当锚成员取交集。我采用后者(LIVE),因为它才是「书能交易的名」。
  - 若 lead 只要 pit ∧ TRD ∧ crypto(即 book_legal),请在冻结时改这一处。两者差别只在 2025–26:每锚 398 / 421 对 360 / 362。
- **退回规则**(lead):某锚若没有 universe_ext 的行,该锚改用「combo s42 的 kc 有限且 ≠ 0」;装置报退回的锚数。
  - universe_ext 的轴为 2022-01-31 00Z → 2026-09-18 20Z,覆盖全部 NC 评估锚(2023-01-01 → 2026-08-30 20Z)⇒ 预期退回 0 锚。装置按实际数报,不假设。

## 2. 由新宇宙直接引出的行级规则(写明,不留给装置决定)

- 基线 B = w_k·KZ + w_f·ZFD,在 KZ 或 ZFD 非有限的名上无定义;这类名在 LIVE 内每年成千上万格(见 §0)。
- **规则**:ΔIC 的计算集合 = U_NC(i) ∩ {KZ 与 ZFD 都有限}。
  - O2 主读数:在这个集合上,候选无效处取 0。
  - O1 并列:再与候选有效取交集。
  - 最小子集 30 在 O1 的集合上计,照冻结版。
- 被这条规则剔除的格数(LIVE 内 B 无定义)逐年报出。
- 冻结版在 A0 上没有遇到这个问题:A0 的 king 与 fund 在其合格集上几乎处处有限。它是由 NC 书的构成直接引出的,不是新的自由度。

## 3. 装置

- `t7nc_universe.py`(新,零收益,运行于 pod2,输出写 /dev/shm 后拷回本机并核 sha):
  - 断言上面五个输入的 sha;
  - 用 `book_universe.align` 原函数(从 pod2 的 devices 目录导入,sha 断言)生成 U_NC,并与 combo s42 的 kc ≠ 0 集合核对包含关系(越界必须为 0);
  - 逐年报 §0 表的五种计数、退回锚数、§2 的剔除格数;
  - 输出 `U_NC.npz`(E_ts, symbols, U),sha 取自写入的字节。
- `t7nc_zero.py` B 段改用 U_NC(宇宙)与 §2 的计算集合,以替代 TRD。改动随提交附 diff;A 段不重跑(A 段只涉及输入、重合度与席位,不依赖这一行)。
- 两个装置先入库,再运行。

---
## lead 冻结(2026-09-27 07:4xZ,以提交时刻为准)
- **冻结**。宇宙定为 LIVE = pit ∧ TRD ∧ crypto ∧ 当锚成员,即在役书能交易的名(news2_combo L41–48 的实际交集)。
- 行级规则按草稿冻结:ΔIC 的集合 = U_NC ∩ {KZ 与 ZFD 都有限};O2 在同一集合上,候选无效处取 0。剔除的格数逐年、逐候选报告。
- B 段按 (a) 执行:冻结装置不改,等 integ 报 GAP4 的 W6 完成后,在本机以 nice 19 运行。零收益的 t7nc_universe.py 在装置入库后可以先在 pod2 上跑。
