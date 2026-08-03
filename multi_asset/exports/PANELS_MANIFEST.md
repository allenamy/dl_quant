> **创建:** 2026-08-03 17:0x UTC | **Session:** B4-retrain | **状态:** final — 生效中 | **派工:** team-lead(S1 SERVE 面板的配套义务) | **作废条件:** 新增或删除任何一代面板 ⇒ 本表必须同批更新(不更新即失效, 因为一张漏了一行的清单比没有清单更危险)

# 面板代际清单 (PANELS MANIFEST)

> ## ★★ 拿错代不会有任何断言变红。这份清单是唯一防线。
>
> 四份面板的 `ts / symbols / ch_names / baseline_cols / Y* / YR* / CL* / MEMBER110` **全部逐位相同**, 32 个通道里最多差 **2 个**。
> ⇒ 拿错一代, 加载成功、形状正确、训练收敛、断言全绿、结果看起来完全正常 —— **只是回答了另一个问题。**
> ⇒ 2026-08-03 已为此付过一次学费: 一份预注册把**腿**的面板写在了**模型**面板的位置上, 而两个候选**都是活的生产产物**, 没有哪一个看起来像残留。三条独立证据才把它钉死。

## 1. 两条正交的口径轴 —— 先问两个问题, 不要背四个文件名

| | **ch31 市场窗口** (`betaadj_ret24` 里的 `mkt24`) | **funding 口径** (`funding_ema` / `xsr_fund`) |
|---|---|---|
| 取值 | `TRAIN` 居中-24 `sum(market[t−12…t+11])` **含 11 项未来** · `SERVE` 尾部-13 `sum(market[t−12…t])` · `CAUSAL` 尾部-24 `sum(market[t−23…t])` | `as_trained` 未归一(每结算期原始费率) · `corrected` 归一到 8h 等价 |
| 谁定的 | `data/build_wide_dl.py:124` | 上游 `data/build_wide_panel.py` 的 `FUND_EMA` |
| 差几个通道 | **1** (ch31) | **2** (ch0 `funding_ema`, ch28 `xsr_fund`) |

**⇒ 只有这 3 个通道会变。其余 29 个通道与全部标签/掩码/网格, 四份之间逐位相同。**

## 2. 清单

| 文件 (`multi_asset/exports/`) | ch31 | funding | SHA-256 | **谁该吃它** |
|---|---|---|---|---|
| `wide_dl_full.npz` | **TRAIN** | **as_trained** | `2e36dda1d2498c0f…` | **冻结模型的 as-trained 训练输入。** `king`/`s2`(`wideA_*_5yr/fold_*`)就是在它上面拟合的 ⇒ 一切"冻结模型 serving"、`margin_dirty`、以及任何"当年训练时看到了什么"的问题, 用它。**回测的 0.135 出自它(含前视, 高估)。** |
| `wide_dl_full_fundfix.npz` | TRAIN | **corrected** | `5b1b68cc1e4bb974…` | **腿的面板**: funding/size 腿 + `Y4`/`CL4`/`MEMBER110`/`rvol_72h` 的装配链。**不是任何 DL 模型的输入。** |
| `wide_dl_full_causal_v1.npz` | **CAUSAL** | as_trained | `e947df635355a6be…` | **S1 训练输入(本次重训)。** 唯一变量 = ch31 修因果; 与 as-trained 逐位对照 55/55 绿。 |
| `wide_dl_full_serve_v1.npz` | **SERVE** | as_trained | `667cf8161452f9f4…` | **评测用**: 冻结模型在"实盘实际收到的口径"下的读数 ⇒ **`0.079′` 出自它**, 以及三口径并列表的 SERVE 列。**不用于训练。** |

四份**字节数完全相同**(1,052,380,498)—— 所以**文件大小不能用来区分它们**, 只有 SHA 能。

*(另有 `exports/live/wide_dl_live{,_fundfix}.npz` = 每日拼接的实盘面板, 同一套轴, 不在本表范围。)*

## 3. 三个 ch31 口径的数, 不要合并(出处: `RESULT_channel_cutoff_audit_2026-08-03.md` SHA `eedab22a…` §9)

| ch31 口径 | 冻结 king IC | 是什么 |
|---|---|---|
| TRAIN | **0.135** | 回测展示的, **含前视, 高估** |
| SERVE | **0.0294**(=0.079′, walk-forward) | **实盘实际拿到的口径下的诚实成绩**; 窄窗读数 0.079(160 重叠逐时锚)高估 2.7×, 只作那个窄口径陈述 |
| CAUSAL | **0.0216**(walk-forward; 窄窗 0.041) | 用泄漏训出来的模型喂给它没有泄漏的输入 = 三者里最差的组合。**不是"修好之后的样子"。** |

**`SERVE` 是第三种东西, 不是"因果版"。** 实盘面板止于信号行, `"same"` 把未来那 11 项零填充 ⇒ 模型收到的是**居中窗删掉未来抽头**(13 项), 既不是训练那份也不是它的因果修复。**SERVE 也是因果的**(只读过去)—— "因果"与"模型训练时的口径"是两个独立属性, 把它们混为一谈, 正是 0.079 与 0.041 互相认错的方式。

## 4. 选面板的判定流程

```
我要回答的问题是关于……
├─ 冻结模型当年学到了什么 / 回测复现 ────────────→ wide_dl_full.npz
├─ 冻结模型在实盘实际拿到什么 / 0.079′ / 三口径 ──→ wide_dl_full_serve_v1.npz
├─ 重训一个不含前视的模型 (S1) ─────────────────→ wide_dl_full_causal_v1.npz
└─ funding/size 腿 或 书级装配 ─────────────────→ wide_dl_full_fundfix.npz
```

**登记状态:** 三代新旧面板**均未**登记在 `engine/live/factor_version_registry.py` 中的除 `wide_dl_full` 外的条目 ⇒ `assert_funding_dim.py --caliber auto` 对 `causal_v1` / `serve_v1` 会返回 **exit 2 "CANNOT JUDGE"**(不是失败, 是"没有人声明过它该是什么口径")。S1 期间用 `--caliber as_trained` 显式跑(门的文档明文许可); **登记留到部署批。**

## 5. 血统

三份新面板(`causal_v1` / `serve_v1`)由 `data/build_wide_dl_causal.py` 与 `data/build_wide_dl_serve.py` **包装**原构造器产出, 而非复制其逻辑; 二者都钉住原 `build_wide_dl.py` 在 `np.savez` **之前**的前缀哈希 `ca023f9d…` —— 该前缀在建成 as-trained 面板的 `efecc05` 与服务器现行 `a58b3a8` 上**逐字节相同**。⇒ 断言的是"**产生数组的字节就是产生 as-trained 数组的字节**", 而不是"文件同名"。
