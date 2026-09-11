# r12 产物清单

**本机(研究仓)**: `multi_asset/exports/research/uplift_2026-09-11/r12_smoothing/`
- `PREREG_r12_smoothing_2026-09-12.md`(冻结于第一个数字之前)
- `RESULT_r12_smoothing_2026-09-12.md`
- `devices/`(13 个脚本, sha 在 `receipts/SHA256SUMS_devices.txt`; 含钉住的 `w10_sleeve.py` 原件 b88e35a4…)
- `receipts/`(GATE_G1 / GATE_G2 / RESULT_R12 / RESULT_R12_s2027 / RESULT_R12C / LAG12 / LAG12B / BITE12 / LEV12 / MASKS12 / R12_RUN_ENV / R12C_RUN_ENV / 各运行日志)

**pod2**(体积原因不入仓): `/workspace/uplift_2026-09-11/r12_smoothing/`
- `arms/*.npz` 39 个臂(28 网格 + 2 门 + 4 种子2027 + 7 探索/null), 每个含 `rec`(10039×23) `W`(10039×829 f32) `R12T`(未整形目标书) `R12A` `config_json`
- `mask_{ALTSURGE,NULLSHIFT101,NULLSHIFT503,NULLSHIFT1009}.npz`
- `causal_primitives_r12.npz`(r12_regime 代理原件副本) · `REGIME12.npz`(我方自建对照分区, 最终未用作主分区)
- `dev/`(符号链接到 `/workspace/dlw_v4raw`, `dev_v4/f8_2026-08-22`, `r8_inbook/dev/pod_backup_2026-08-21`)+ `dev/logs/*.log` 逐臂

**输入哈希(本轮重算)**
- `w10_sleeve.py` `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`(= PIN)
- `w10_r12.py` `79d7f5709b6602413181ccf69c5580b112ea9bbce0150620a93662b744f32e47`
- `w10_r12c.py` `6a6d2b0a426d4ca6a175873d707e5ecbae9850df1678b2559cf544624e8c2fcd`
- `r3k/costb_PWR_G230k.json` `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53`
- `pod_backup_2026-08-21/wide_fea_hist_meta.npz` sha16 `0e3c09ac86c727ac`(= r12_regime 代理读的同一个文件)
- mask sha16: ALTSURGE `550a0ccaf569d391` / +101 `2e3dd9d177c13a8d` / +503 `85d07805743ab76a` / +1009 `5171706d7bfeb1b1`
