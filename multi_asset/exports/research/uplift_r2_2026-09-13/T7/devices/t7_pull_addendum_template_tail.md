
## §3 对后续(S1 草案冻结时)需要 lead 决定的数据问题(本步不改草案)
1. **KRW 成交量两种粒度不自洽**(C3 734 个市场日): 草案 K3 与两所合并权重用到 KRW 成交额, 冻结时须写死用 60m 求和还是日 K, 并声明不等日的处理(本步只标)。
2. **币安指数价缺日**(896 个符号-日): 这些日溢价无效, 会降低命中率; 是否用日 zip 补(约 979 个请求)须 lead 决定; G2 命中率须在最终面板上按全史复算。
3. **同一性旗标**(11 对): 草案 G4「越界对×月剔除」若被采纳, KAVA / CRV / ENJ / SOLV / TAIKO 等对应月份将被剔除, 须在冻结时确认。
4. 2026-09-01..09-13 的 KRW bar 已拉, 但无对应币安月 zip, **未做同一性检查**。

## §4 未验证与风险
- 墙钟回拨解释是推断(见 §0-3); 日 zip 内容未检视; 已下市韩国市场仍不在数据里(幸存者, RESULT §6)。
- 数据只在 `/Users/haosiyu/cc_tmp/krw_pull/`(不在 git); 若被清理, 须按入库的页清单(逐页 body sha256)复拉并逐字节核对。派生数组可由 `t7_pull_checks.py` 重建。
- 磁盘剩余约 12–15 GiB(使用率 97–98%)。

## §5 装置与复跑命令(逐字)
全部装置在 `devices/`, 运行副本在 `/Users/haosiyu/cc_tmp/krw_pull/devices/`(sha 记录于冻结计划与修订 1)。
```
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices
python3 t7_pull_plan_freeze.py --root /Users/haosiyu/cc_tmp/krw_pull
bash t7_pull_launch.sh /Users/haosiyu/cc_tmp/krw_pull
# (修订 1: 停 v1 后以同一命令重启, 续拉)
cd /Users/haosiyu/cc_tmp/krw_pull/devices
python3 t7_pull_checks.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_identity_guard.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_offset_spectrum.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_c3_detail.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_c3_repull.py --root /Users/haosiyu/cc_tmp/krw_pull --venue upbit
python3 t7_pull_c3_repull.py --root /Users/haosiyu/cc_tmp/krw_pull --venue bithumb
python3 t7_pull_binance_gaps.py --root /Users/haosiyu/cc_tmp/krw_pull --probe 3
python3 t7_pull_binance_format_breakdown.py --root /Users/haosiyu/cc_tmp/krw_pull
python3 t7_pull_summarize.py --root /Users/haosiyu/cc_tmp/krw_pull
cd /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices
python3 t7_pull_collect.py --root /Users/haosiyu/cc_tmp/krw_pull --tests /Users/haosiyu/cc_tmp/krw_pull_test /Users/haosiyu/cc_tmp/krw_pull_test2 /Users/haosiyu/cc_tmp/krw_pull_test3
python3 t7_pull_addendum_tables.py
python3 t7_pull_assemble_addendum.py
```
测试根(`krw_pull_test`、`_test2`、`_test3`)的计划、控制、退出与检查收据复制在 `pull/tests/`。

## §6 数表(全部由 `devices/t7_pull_addendum_tables.py` 从 `pull/` 收据生成)
{{P-1}}

{{P-2}}

{{P-3}}

{{P-4}}

{{P-5}}

{{P-11}}

{{P-6}}

{{P-7}}

{{P-9}}

{{P-10}}

{{P-8}}
