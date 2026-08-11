> **创建:** 2026-07-27 00:5xZ | **Session:** ma-v2 0C | **状态:** final (根因确定; **修法与派工假设相反, 待裁定后才动码**)

# shadow 日报 STALE 根因: **闸门被装在了错的产物上** —— 而装它的人是我

## 一、"为什么 7-23/24/25 全过, 7-26 突然 FAIL" —— 不需要新迁移波

```
git log -S'assert_funding_dim' -- data/build_wide_dl.py   ⇒ a58b3a8  2026-07-25T10:59:44Z
git log -S'8.0 / ivh'          -- data/build_wide_panel.py ⇒ a58b3a8  同一提交
cron 07-25 跑于 09:00Z   <  10:59Z   ⇒ 那次**没有闸门**
cron 07-26 跑于 09:00Z   >  10:59Z   ⇒ **闸门武装后的第一次日跑** ⇒ FAIL
```

**⇒ 突然 FAIL 的原因是**闸门刚装上**, 不是数据变了。⇒ 派工里的假设 ②(7-25/26 新一波结算间隔迁移)**不需要成立**即可解释全部现象。(我没有反证它不存在, 只是它不必要。)**

## 二、★ 根因: 两个口径, 一道闸门, 装在了属于**另一个**口径的产物上

**这条流水线**故意**有两个 funding 口径 —— 证据在代码里写着:**

| 产物 | 构建者 | 口径 | 依据 |
|---|---|---|---|
| `wide_dl_full.npz` | `build_wide_panel.py` (全史) | **已修正** (`rate * (8.0/ivh)` 在 EMA 之前) | 该文件第 85 行 |
| **`wide_dl_live.npz`** | `build_tail.py` → `funding_derive.real_funding_ema` | **AS-TRAINED (未归一)** | `funding_derive.py:110` 逐字: *"It does **NOT** normalise the rate; this path emits the AS-TRAINED (un-normalised) caliber **on purpose**"*; `:64`: *"build_tail writes the AS-TRAINED caliber (**the un-normalised one the frozen DL heads** …)"* |

**且监控层也把两者当成两条线**: `monitor.py:35` — `as_trained_4leg  CONTROL  champion curve B, **pre-fix funding**, 4 legs`。

**⇒ 而闸门自己的用法行写的是: `assert_funding_dim.py [--panel <wide_dl_full.npz>]` —— 它的目标是**全史**面板。⇒ 但它被接进 `build_wide_dl.py`, 于是**日跑把它作用在了 `wide_dl_live.npz` 上** —— 一个**按设计就应该是未归一**的面板。**

> **★ 所以这不是"splice 忘了修", 是**闸门装错了产物**: 它在检查一个**故意保持 as-trained** 的面板是否具备**已修正**的签名。两个口径都对, 冲突的是**谁去检查谁**。**

## 三、⚠ 因此派工里的修法 (给 splice 补 `rate*(8/interval)`) **会造成更坏的后果**

**若给 `real_funding_ema` 补上归一化:**
- `wide_dl_live.npz` 的 `funding_ema` / `xsr_fund` 两个**模型输入通道**的口径会改变;
- 而**冻结的 DL 头是在未归一口径上训练的** (`funding_derive.py:64` 明写);
- ⇒ **等于在不重训的情况下悄悄换掉模型的输入口径** —— 影子轨的每一个预测从此在一个它没被训练过的分布上产生, 而且**没有任何东西会报错**(闸门反而会转绿)。

**⇒ 这比"日报停更"坏得多: 日报停更是**可见的缺席**; 换掉模型输入口径是**不可见的漂移**。⇒ 我不动这行码, 交裁定。**

## 四、我建议的修法 (未经裁定)

**把闸门的作用域改对, 而不是把 splice 改成另一个口径:**

```
wide_dl_full.npz  (全史, 已修正)   ⇒ 断言"已修正签名"  (gap 应在 +0.146 带)
wide_dl_live.npz  (日跑, as-trained) ⇒ 断言"as-trained 签名" (gap 应在 −0.374 带)
                                      —— 同一道闸门, 按产物选期望值; 两侧都不许落在中间
```

**⇒ 这样它仍然守着"funding 维度没有被无意改动"这件事 (两个口径各自被钉住), 而不是要求两个口径变成一个。⇒ 红测: 用 7-26 的 `wide_dl_live.npz` 跑 ⇒ 在**新语义**下应 PASS; 把它的 funding 通道人为归一化一次 ⇒ 应 FAIL (证明它真的在守 as-trained 那一侧)。**

## 五、★ 这是我自己的失手

**07-25 我查出 funding 单位 bug、修了源、并把 `assert_funding_dim` 接成硬门。⇒ 我当时没有分清**两个面板**: 全史面板该修, 日跑面板**按设计不该修**。⇒ 我把一道"检查已修正"的闸门装在了"故意未修正"的产物上, 于是它在第一次武装后的日跑就停了整条影子流水线。**

> **⇒ 形态: **修复的作用域比缺陷的作用域大**。缺陷只在全史面板, 修复(连同它的守卫)却被应用到了所有面板。⇒ 与"一个判据引用了一个会自己长大的集合"是同族: 这次是**一个守卫覆盖了它不该覆盖的产物**。**

## 未经单独检验

1. **我没有反证"7-25/26 有新迁移波"** —— 只证明了它**不必要**;
2. **我没有实测 `wide_dl_live.npz` 的 gap 是否恰等于 as-trained 的 −0.3745 带** (读数 −0.3767, 接近但我未做统计判定);
3. **"冻结 DL 头训练于未归一口径"我引的是代码注释**, 未去核对训练时的面板文件本身;
4. **建议的双口径闸门我未实现** —— 待裁定。

---

# ★★ 补证 (00:5xZ): 不再依赖代码注释 —— **文件时间戳定案**

**我上一节把"冻结 DL 头训练于未归一口径"标为"引自注释, 未核"。现在核了:**

```
engine/panel_source.py:11   PANEL = exports/wide_dl_full.npz      ← 引擎/冻结头读的就是它
服务器 mtime:
  exports/wide_dl_full.npz        2026-07-11 12:55:33 UTC   ← 修复(07-25T10:59Z)之前**两周**
  exports/live/wide_dl_live.npz   2026-07-26 09:02:17 UTC
```

**⇒ 冻结 DL 头消费的那份面板建于 07-11, 即**未归一 (as-trained)**, 且**从未**用修复后的 builder 重建过。⇒ `build_tail` 的 live splice 刻意复现同一未归一口径 —— **它是对的, 它在对齐训练面板**。⇒ 闸门要求"已修正"签名, 却被装在这条**正确地保持未归一**的路径上。**

**⇒ 结论不变, 但证据从注释升级为文件事实: 给 splice 补归一 = 让 live 面板与 07-11 训练面板口径不一致 = 不重训换输入分布。**

## ★ 而由此掉出一个**更大的、尚无人指出**的隐患

**`build_wide_panel.py` 已于 07-25 被修好 ⇒ **下一次任何人重建 `wide_dl_full.npz`, 训练面板的口径就会静默改变** ⇒ 冻结的 king/s2 头将在一个它们没被训练过的分布上推理, 而**闸门反而会转绿**(因为新面板"已修正")。**

> **⇒ 这与派工想对 splice 做的事是**同一个错误的镜像**: 一边是把 live 改成 corrected, 一边是把 full 重建成 corrected —— **两者都会在不重训的情况下换掉冻结模型的输入口径**, 且都会让闸门更绿。**

> **★ 而这套系统自己已经写下了正确的原则, 就在 `checkpoints/MANIFEST.json` 的 `why` 里:**
> **"norm stats are hashed alongside the weights because **feeding a frozen model different normalisation is the same failure as loading different weights**."**
> **⇒ 他们为**模型的归一化统计**做了哈希守卫; 而**面板的 funding 口径**是同一类东西, **没有任何守卫**。⇒ 建议 (未经裁定): 把训练面板的 funding 口径签名 (gap 落在 −0.374 带) 纳入 MANIFEST 的哈希/断言体系, 与 norm_stats 同级。**
