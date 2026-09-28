> **创建:** 2026-09-28 03:26 UTC | **Session:** codex-acting-lead-20260927 | **状态:** final-prelaunch-review | **作废条件:** 装置或合同变化须重新核；不为经济结果或发布背书

# RAW/RESID 整书试验启动前复核

预注册d89788736，源码943f3c741，registry bd6f80f06。独立复核review_residual_book_0928指出两项，启动前均处理：

1. P1：复用cap50原基线恒等，不意味着当前外部配置未变。control_binding现在把当前BASE_CFG与原成功控制链的base_config_sha精确核对；两个外部adapter spec共享字段与原成功spec相同；控制PATH的NPZ、config关联与原身份收据核同；四个实际engine源码按原控制device_sha核同，适配器17555e56钉定。原链收据sha入合同，前后两次执行。首次Pod预检暴露exec_sim加载路径不同于另外三个engine文件，拒绝FileNotFound；独立复核也指出相同问题。已改从原钉配置pins.exec_sim.path取源，真实预检12项PASS，没有把缺文件当成功。
2. P2：候选TARGET_RECEIPT旧文仍称在役F10。已携带deterministic_ridge、RAW/RESID、接口seed42非模型种子的说明，删旧误称。

本地与Pod纯测试9/9；错费用、错窗口、错宇宙均拒；残差正交、未知不归零、测试标签变动不影响预测、同标签退化控制、错轴/重叠拒绝都覆盖。首次本地测试文件写入命令用了错误相对路径而失败，随后纠正；该次不是红能力证据，真正红在测试已存在但control_binding尚未实现的运行。没有执行任何实盘套件，没有交易所请求。

本试验未做DL新训练。旧D2效用训练若直接替换标签，离开成员仍持仓的人口缺残差标签，这个问题尚未完成；当前按行Ridge只绕开本次监督对象，不能宣布完整DL训练解决。

45分钟预算从03:23:45Z到04:08:45Z，不续期；启动PID/PGID3572046、start_ticks513571889。父收据/基线路径全复哈希后才训练；CPU2线程，cgroup可用≥24GiB，最多2个引擎，全无GPU。既有invvol已终态。来源合同sha 4fa774deb5505e621b7e358781aa90f4efec915fb28668158eb4e9a2ac41f6e0。没有生产变更。
