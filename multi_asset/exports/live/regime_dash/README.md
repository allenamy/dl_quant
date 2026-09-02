# regime_dash(只读监控, 2026-09-02 建, 用户令)
**运行时目录 = `~/regime_dash/`(launchd 后台进程被 macOS TCC 拦在 ~/Desktop 之外, E-0902-G); 本目录 = 代码单源 + 快照。改代码: 改这里 → `cp` 到 ~/regime_dash/。输出(md/html/jsonl/PENDING_RULINGS/周报)在 ~/regime_dash/。**
- `regime_dash.py` 每锚后 50 分(launchd `com.hsy.regime_dash`)→ `REGIME_DASH.md` / `.html` / `regime_dash.jsonl`; `regime_dash_ext.py` = 旗标转移 INFO 页 + 预注册规则建议(R1 双引擎同负→讨论降杠杆 / R2 FTRIM 可撤 / R3 席位换季 / R4 引擎A退潮; 冷却 24 锚)→ `recommendations.jsonl` + `PENDING_RULINGS.md`(待并入 STATE §3)。
- `regime_weekly.py` 每周日 09:00 local(launchd `com.hsy.regime_weekly`)→ `REGIME_WEEKLY_<date>.md` + INFO 页。
- 历史基准 `regime_hist_pct.json` / `regime_hist.npz`(jpline `jp_regime_hist.py`, B 面板 2023+)。
- **网页投递(脚本触发, 不依赖 Claude 会话)**: 每锚采集后把 `REGIME_DASH.html` 作为文件静默发到 Telegram(与告警同 bot/同群), 手机/电脑点开即最新版; 本机 `open REGIME_DASH.html` 亦可。artifact 镜像 https://claude.ai/code/artifact/f8379cee-36ae-4864-acf9-6c32bd890e19 只在会话深查时刷新, 非主渠道。
- 纪律: 不改任何实盘文件; 旗标/建议 = 信息, 动作归用户; 单锚数字噪声大, 判断看 30 锚累计与百分位漂移。
