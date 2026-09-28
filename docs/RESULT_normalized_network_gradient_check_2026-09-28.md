> **创建:** 2026-09-28 01:15 UTC | **Session:** codex-acting-lead-20260927 | **状态:** final | **作废条件:** 来源/输入改变；不得替代折外整书评估

接续 `RESULT_first120_rank_action_2026-09-28.md` 和 `AMENDMENT_normalized_network_gradient_check_2026-09-28.md`（b54f6801d）。标准化补回后，重新验证改变后的计算图；不是重训。

实际01:10:18Z终态rc0，guard45.0秒、峰RSS2.044GB/GPU0.679GB、CPU1，原资源门均满足。root另独立复哈希30件实际输入/运行源/模型。17份原始结果完整归档，结果sha256 `23aec964aadb860d7c941fa39d7324f89437da1f09e1ec785b8c7f8a13ae57a4`。

**冻结梯度门仍为UNRESOLVED。** 固定方向下，eps1e−4的9/9分项同分支，AD与有限差分在原容差内；eps1e−3的9/9均跨producer/fill-sign分支，不能以该差分认证局部梯度，也不能删除大eps改判。

硬动作与原连续实现误差≤1e−12、发布/原因相同。该checkpoint硬发布30次，标准化soft发布35次、85次HOLD。模型参数前后hash均 `6cf9079f32dcabb68be806b35c4607ed078cb802c37d21561767d70fc8df1bdd`，optimizer0。原F0全对象不等已定位为未用a梯度的有符号零，本次未重跑；包的旧UNRESOLVED元数据不替代定位原件。

分数标准化解决了任意缩放引起动作变化的问题，没有消除免交易带等离散边界。下一步应区分同分支局部梯度和跨门硬动作现金变化，不能靠缩小eps搜索通过。Jan2023配202608 checkpoint仍是样本内工程；固定NAV、期望成交代理、非完整执行器等边界全部保留，不能推导盈利。

确切Python/命令/source SHA见 `devices/normalized_network_fd_20260928/FORWARD_CONTRACT.json`；原Pod `.../funding/normalized_network_fd_20260928` 已完成，禁止覆盖复跑。归档在 `receipts/NORMALIZED_NETWORK_FD_20260928/`，zip sha256 `b6435580bfb45a3beb058db7678fdeb8512a4da24cf7a5bcccabdb87b7265db7`，ROOT_POSTVERIFY绑定30件。

首次源码传输因Pod无rsync被拒，数值worker未启动；改scp复制同一冻结源码后，guard复核再运行。预算、图、双eps均未因此改变。创建日期曾手写成晚于实际时刻，已按b54f6801d真实提交时刻改为01:08；冻结的先后顺序以git与实际终态为准。生成本文的一次长stdin命令发生编码错误、未写入任何文件，改用文件补丁完成。原运行收据未修改。
