# FP2-6b 生产者补丁排练收据(2026-09-17 11:21Z, 锚 1789632000 = 08:00Z)
- 两个沙箱 HOME(各一份 ~/wide_shadow 完整拷贝 + 生产 `dl_quant_live/live` 拷贝, `telegram_notify` 换成只记录不发送的桩): A = 未打补丁 combo_stage.py b5c698f9(= 在役), B = 打补丁 3520d363(补丁 `fp2-6b_combo_stage_f10_sha.patch`, 干跑与实跑均干净应用)。
- 运行: `HOME=<沙箱> COMBO_LIVE=1 COMBO_LIVE_DIR=<沙箱>/wide_shadow/state/target_live_REHEARSAL python -u combo_stage.py`, 两臂 rc=0, 步骤 ⑤ 写者完成, 读者(生产 external_book)验收 ok, 桩页报为空。
- **A vs 在役 08Z combo 文件**: 只有 `written_utc` 不同(逐键相同: weights 242 名、universe、gross 0.8032、universe_sha、booster_sha、weights_sha)。
- **B vs A**: 只多 `f10_sha`(+ `written_utc`); `f10_sha` = sha256(在役 `fea171/f10_live_s42_np.npz`) = `351ae26bd6b4a203…`(全值见 B_target_1789632000.json)。
- 在役树零触碰: `state/combo_live_status.json`、`target_live/`、`target_combo/`、`target_blend/` 的 08Z 文件 mtime 均为 08:20–08:23Z。
- 机制核: 守护 `combo_live_daemon.sh` 每锚以子进程 `COMBO_LIVE=1 python -u combo_stage.py` 运行 ⇒ 替换文件在下一锚生效, 无需重启任何 launchd 任务。
- 应用窗: 12Z 锚读取完成(≥12:29Z)后、16:00Z 前替换在役文件(先备份 + 快照入库); 16:24Z 读到 f10_sha 后再在执行器设 `f10_sha_pin`(20:00Z 前)。
