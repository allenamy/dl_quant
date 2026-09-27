> **创建:** 2026-09-27 18:42 UTC | **Session:** acting-lead/funding_mechanism_0927 | **状态:** frozen-before-run；仅合成 CPU 参数/前向控制 | **作废条件:** 源码/输入身份、双锚事件、阈值或预算改变；失败保留不重启

# 小型 CPU 参数时钟控制

root 在 CUDA 探针 5723603f3 后授权本次独立小控制：CPU1，RSS申报2GiB、软件停止1.75GiB、公共余量8GiB、wall300秒；Pod `/workspace/venv/bin/python`，无CUDA，无市场特征/标签/target输入。新根 `cpu_parameter_control_20260927`，一次运行，失败不重新开始预算。完整120真实输入网络链/整折训练未获授权。所有结果标 NO_ALPHA_IMPLEMENTATION_ONLY。

独立标准来自 root 的 `shared_parameter_cash_oracle.py` SHA26b08644f091713641cfcd389d89e16e80dc906134042255ca31bdb25495fd66 与 ROOT_SHARED_PARAMETER_CLOCK_20260927.json：初仓3、θ=.7，第一目标2θ、第二目标−3θ；四结算为 (1ms,P8,r.005)、(14400s+12ms,P10,r.01)、(15840s,P9,r.03)、(21600s,P12,r−.02)；fills 在1440和15840秒，fund同刻先于fill。共享θ导数−1.46，错删早费−.72、错提前给当前仓+.39。当前目标对早费偏导0、前锚目标偏导−.1、初仓对θ导数0、θ=0仍保留导数。Torch与独立scalar收据对照 atol1e−9，反号与重复cash拒绝必过。

真实原 F10 Net 类只从钉 SHA66bc7c3e…训练器 AST 提取，不运行trainer顶层，不读取checkpoint；结构171→256→256→1、110082参数，seed42。只有两个合成171维样本：第一列2和−3，其余0；模型输出是两个qty目标，初始qty=3 stopgrad。双窗口price从相同inventory/fill现金账构造（起点价8、A1标价10、终点价11；两fill价8.2/9.1）；fee=abs(dq)*fill_px*.0002；cash按上述事件。V0=100000，损失=−mean(net)+.25*ES5%(−net)，两窗ES取1个最差窗。这是合成数量网络接口，不是生产排序/完整组合的端到端训练。

在 float64 eval模式，分别核price/fee/carry/总目标对网络参数的梯度、预定固定方向中心FD eps1e−3及1e−4；两个尺度都报且 atol1e−8、rtol1e−5。若跨fee绝对值/ES门，明确记录并失败保留，不临时换方向/eps。反号carry梯度精确翻转；a仅通过0*a入图，carry对其梯度为0。

一步控制：同初值、同双样本、同dropout RNG20260927，AdamW lr3e−4/wd1e−4、clip1；F=0时两臂loss/全部grad/全部参数/全部AdamW状态逐位相同。随后唯一A0 price−fee、A1 price−fee+carry各一步，无系数搜索，报告参数变化和分项，不要求学习效果为正，不生成候选或OOS分数。

硬forward另用2锚、80个合成成员/84全轴，两个已冻结初始状态（全0、平衡gross1）及literal/scaled两口径；包含ties/NaN/RN8夹子/qv过滤/成员退出。把独立Torch硬rank/chain实现与钉源码的原combo_target.step比较，kc/fc/raw/exec_reshape/accepted/reason，金额无关，float64权重容差1e−12。必须有至少一个发布及一个HOLD；错误将raw混合系数从.55改.5应由同一核对函数拒绝。源只提取原函数，禁止运行combo_stage顶层或任何data/model加载。生产硬rank不对θ宣称可微；硬平价与参数FD是两个各自有边界的小控制。

运行前提交worker、guard、合同，核部署SHA；guard只停止本任务PGID，50ms RSS/HWM监视和worker同截止SIGALRM。软件停止不是Linux硬限；实测峰值及采样间隔保留。资源拒绝即终态，不等待重试。旧六窗NO_RESCHEDULE、单独CUDA形状探针终态均不变。

执行前源码审查补充（2026-09-27 18:47 UTC，尚未数值运行）：F=0控制显式运行 A0(coefficient0) 与 A1(coefficient1, rates0)，不能把 coefficient0 同一分支调用两次冒称臂开关恒等。部署后未发运行命令；原 b99ad8632 保留，新 worker SHA 入 CPU_CONTRACT。
