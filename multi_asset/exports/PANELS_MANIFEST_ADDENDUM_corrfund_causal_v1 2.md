> **创建:** 2026-08-04 06:4x UTC | **Session:** B4-retrain | **状态:** final | **作废条件:** 当 `PANELS_MANIFEST.md` 的服务器副本被更新到含第五代时, 本旁挂件即可删除

# PANELS MANIFEST 旁挂件 — 第五代面板登记

**为什么是旁挂件而不是直接改 `PANELS_MANIFEST.md`:** 本会话对 jpline 的授权是**只增不改**。清单本体已在本地 git 更新(权威版), 服务器这份仍是旧四行版。**两边不一致是已知且声明的。**

## 第五代

| 文件 (`multi_asset/exports/`) | ch31 | funding | SHA-256 | 谁该吃它 |
|---|---|---|---|---|
| `wide_dl_full_corrfund_causal_v1.npz` | **CAUSAL**(尾部-24) | **corrected**(8h 等价) | `c53d84206f8bd76af79b18717143a0242c32ca48f5ab3a6648d6370935d71f23` | S1F 归因实验(`wideA_lamorth0{,_xattn}_5yr_corrfund_v1`)· **干净 s2**(`wideA_s2_y24_5yr_corrfund_v1`)· **两条 PRODUCTION_FOLD**(`wideA_lamorth0{,_xattn}_5yr_PRODFOLD_corrfund_v1`) |

**两轴皆新**, 是目前唯一"既无前视、funding 又归一到 8h 等价"的训练面板。

## ★★★ `panel_ref.npz` 对 ch31 轴是盲的 —— 用它验\"有没有吃前视\"会得到假绿

2026-08-04 逐位实测: `wideA_lamorth0_xattn_5yr`(脏)与 `wideA_lamorth0_xattn_5yr_causal_v1`(因果)的 `panel_ref.npz` **九个键哈希全同**(`ts/day/Yraw/YR/member/CL/funding/resid_sigma/horizon`)。原因: `panel_ref` 存标签+掩码+funding, 而 ch31 的修复只动 `X`。

- **能区分 funding 轴**: `as_trained` = `dbaae69795db` · `corrected` = `c6a1f9e9e5a0`
- **区分不了 ch31 轴**: 脏与因果完全同哈希

⇒ 核 ch31 只能靠面板文件本身的 SHA, 或 run 的 provenance。

## 附带实测更正

`corrected` funding **会连带改 `YR*`**(残差标签的构造吃 funding), `Yraw` 不变。早前"只动 ch0/ch28 两个通道"的说法在**标签侧不完整**。

## 部署产物出处

两条 PRODFOLD 的 `PRODUCTION_FOLD_PROVENANCE.json` 按**路径**记面板, 而本清单的全部论点是"路径与大小都区分不了面板, 只有 SHA 能" ⇒ 最可能被部署的产物出处最弱。已 additively 补 `PANEL_SHA_RETROSPECTIVE.json`(自陈为**回溯**口径: 证的是此刻该路径上文件的 SHA, 不能追认训练当时读到的字节)。真修法 = trainer 在训练时写入 SHA, **本次未做**(需改既有文件), 具名跟查 `prodfold_panel_sha_at_train_time`。
