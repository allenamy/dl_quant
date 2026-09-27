> **创建:** 2026-09-27 04:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(lead) | **状态:** 迁移收据(旧机 Intel x86_64 → 新机 Mac mini arm64) | **作废条件:** 环境再次变更

# 实盘主机迁移收据

- **拦截**:03:59:28Z,新机上被迁移助手带过来的 21 个实盘 launchd 作业全部 bootout,并持久 disable;只留 caffeinate。旧机由用户确认已关机。
- **网络**:出口 IP 103.252.201.68,与旧机日志一致 ⇒ 交易所白名单不变;pod2 的 ssh 正常。
- **环境重建(arm64,包版本与旧机逐一相同)**:
  - 生产者 venv:python 3.14.7(旧 3.14.4),numpy 2.5.2 / scipy 1.18.0 / pandas 3.0.5 / lightgbm 4.7.0(另装 libomp);
  - 执行器与大部分作业:/usr/bin/python3 3.9.6,用户包 48 个按原版本重装;
  - brew python3.14 的用户包 18 个按原版本重装;
  - node / gh 已装;
  - pyflakes 4.0.0 放在 ~/tools/pyflakes_venv,链接到 /opt/anaconda3/bin/pyflakes(测试按此路径找);
  - `pmset sleep 0 autorestart 1`(经用户在 GUI 授权)。
  - 旧 x86 环境保留在 *.x86_64_bak_20260927。
- **平价**:combo_parity_replay 00Z(1790467200)在 arm64 上权重逐位相同(319/319,n_differing 0);beta_overlay 有 18/450 个 beta 差 ≤ 2.2e-16(M3 仍是 shadow)。
- **执行器离线全电池**(克隆 d01e35d):
  - run 1 只复制了 pilot_log:162/166,4 红,3 个是环境原因;
  - run 2 复制了完整 state:164/166,tests_static_names 在装好 pyflakes 后单独重跑 ALL PASS ⇒ **165/166**;
  - 剩下的 tests_nosleep A10 是「红控能力」项:它要求旧读取器在一个超大的 pmset 日志上超时,新机日志只有 0.1s,这种情形在新机上无法复现。这是环境属性,不是实盘代码缺陷;活的 nosleep 断言全部通过。具名例外。
