> **创建:** 2026-09-23 12:4xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(NEW_S 执行代理,受 lead 派) | **状态:** 冻结 —— 写于任何 NEW_S 书层 / 判词数字之前;停链时尚未产生任何模型或数字 | **作废条件:** 预注册 db0123df7 / 修订 1 63ca0d0bb 改动

# 预注册 db0123df7 修订 2:King 训练环境缺 scikit-learn —— 按 lead 裁定 (a) 改 King 一行的解释器,链从 King 步续跑;news_stats R-P 选运行修复

## 1. 停因原文

- 12:34:19Z 历史特征重放合并完成:`NEWS_FEATURES.npz` sha256 `a490c294d90e0cdb2bb1dca503f3468dc1a4384396e3f7bae3e3020e161f79ac`,10,333 锚、2,785,450 对、43 锚跳过(均在 2022-01 缓存开头:成员 < 50,或 combo_stage L102 btcv 断言,生产者在该处同样会中止)。收据 `receipts/P2B_FEATURES.json`。
- 12:34:23Z King 训练 `news_train_king.py`(NEW 配方 `lgb.LGBMRegressor`)在第一折建模前报错,日志原文(`logs/chain_king_try1_no_sklearn.log` 末行):
  `lightgbm.basic.LightGBMError: scikit-learn is required for lightgbm.sklearn. You must install scikit-learn and restart your session to use this module.`
  原因:King 那一行用的是为逐位平价装的生产同版本环境 `/root/news_2026-09-23_env/venv314`(Python 3.14.4 / numpy 2.5.2 / scipy 1.18.0 / pandas 3.0.5 / lightgbm 4.7.0),其中没有 scikit-learn。链因 `set -e` 退出。
- **此时尚未产生任何模型或数字**:`work/king/` 只有一个空目录(已删除后续跑),没有模型文件、分数、腿、组合或书层数字。
- 按 lead 11:4xZ 约束(在跑的链上不改代码,必须改则先停下报告并写进修订),本代理停下报告;lead 12:3xZ 裁定选 (a)。

## 2. 修复(lead 裁定 (a))

King 这一步改用 `/workspace/venv/bin/python`(= NEW King 实际训练的环境:Python 3.11.10 / numpy 2.4.6 / scipy 1.17.1 / scikit-learn 1.9.0 / lightgbm 4.7.0);生产同版本环境零改动(9 锚逐位平价的结论建立在它上面,不 pip 装包)。

- 续跑版 `devices/news_chain_resume.sh` sha256 `5d2b80c6a30b8a39184d43326d311dda1652f06a1f31628ad8e97d87e17d0850`(原文件 `news_chain.sh` sha256 `6a7240840717693c2c72ab4931c3661d430cab3277a921904029d73fdd4fc4e6`)。
- 与原文件的逐行 diff(`devices/news_chain_resume.diff`,全文):
```
1a2
> # news_chain_resume.sh = news_chain.sh (6a724084) with ONLY (i) the completed wait/merge steps removed and (ii) the King line interpreter $P314 -> $PV (AMENDMENT 2, lead ruling (a), 2026-09-23)
11,14c12
< # 0. wait for all 104 P2 shards
< step wait_shards
< while [ "$(ls $W/work/p2_shards/*.npz.json 2>/dev/null | wc -l)" -lt 104 ]; do sleep 30; done
< done_ wait_shards
---
> # RESUME (AMENDMENT 2): the two completed steps (wait for 104 shards; merge → NEWS_FEATURES a490c294…) are removed; every other line is unchanged
16,17c14
< step merge;  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 5 $P314 -u news_p2_build.py merge > $L/chain_merge.log 2>&1; done_ merge
< step king;   nice -n 5 $P314 -u news_train_king.py > $L/chain_king.log 2>&1; done_ king
---
> step king;   nice -n 5 $PV -u news_train_king.py > $L/chain_king.log 2>&1; done_ king
```
- 12:39:27Z 续跑启动(PGID 2281139),King 12:40:26Z 完成。King 实际环境收据 `receipts/P3_KING_ENV.json`(解释器、python / numpy / scipy / sklearn / lightgbm 版本;链继承的 `NPY_DISABLE_CPU_FEATURES` 对该 numpy 2.4.6 同样生效)。

## 3. news_stats.py R-P 选运行修复(复审 R10-E02,lead 12:3xZ 要求在链跑到 stats 前修)

原 `halted()` 断言读数收据只含一个运行,而 Stage 1 的 `BT_P_READING_OVN_OLD.json` 含 scaled 与 lit 两个运行,NEWS 自己的读数收据也可能含多个 ⇒ 判定步必崩。修法(不取首项、不删断言,按冻结对象选):只选主读数 scaled 那一个运行,以其 `dir` 与 S 表所用的 base 格目录(`<runs_root>/<prefix>_scaled_rule_raw_UAFE`)精确相等匹配;匹配不到或多于一个 ⇒ 拒绝;并核对阈值 −0.25、基点 `FULL_RECIPE window start @ 2023-06-30T04:00:00Z`、32 条路径 seed 恰为 0..31 各一次、窗口末锚 = `2026-08-31T00:00:00Z`。红测试(先断言基线为绿):错臂、阈值 −0.99、32 份相同 seed 0、截止 2024 的收据,都必须拒绝。新 sha 与测试收据见 §4。

## 4. 新文件 sha(本修订提交时)

| 文件 | sha256 | 说明 |
|---|---|---|
| `devices/news_chain_resume.sh` | `5d2b80c6a30b8a39184d43326d311dda1652f06a1f31628ad8e97d87e17d0850` | 续跑版(§2) |
| `devices/news_stats.py` | `7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c` | R10-E02 修复(§3);统计函数逐字未改,只改结构(导入无副作用)与 R-P 选运行 |
| `devices/test_news_stats_rp.py` | `23846cb4d9553f94f2d31000cf971ab5b8f73e6488db72c1081e5b71570ad1a1` | 红绿测试:基线绿(OLD 2 运行 → 32、OLD_HOLD 1 运行 → 10、NEW_s42 2 运行 → 0,与 Stage 1 发表值一致),7/7 变异按具名原因拒绝(错臂 / 阈值 −0.99 / 32 份 seed 0 / 截止 2024 整收据 / 仅逐路径截止 2024 / 同目录两运行 / 装置 sha 不符);Mac 与 pod2 各跑一次均 `VERDICT=PASS`,退出码 0 |
| 原 `devices/news_stats.py`(修复前,已在 7815fa449 入库) | `10cb1d9e56f63355dc5fdf107b4c8d399f12aa768cb60aa4f36d5f9dffbc5672` | 原文另存 `devices/news_stats_v1_before_R10E02.py` |

pod2 上 `devices/news_stats.py` 于 12:5xZ 替换为上表版本;链在 stats 一步执行 `cp -p $D/news_stats.py $E/`,所以替换在该步生效(此时链在「腿」一步,尚未产生任何书层或判词数字)。

## 5. 不变的

特征(已冻结,sha 如上)、King/F10 配方、两种子、组合、认证引擎、S1–S5 判据、平价门。LightGBM 训练的数值不经过 scikit-learn(`LGBMRegressor.fit` 只把参数转交 `lightgbm.train`)。
