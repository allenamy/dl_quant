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
