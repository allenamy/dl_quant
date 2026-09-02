# regime_dash(只读监控, 2026-09-02 建, 用户令)
- `regime_dash.py` 每锚后 50 分(launchd `com.hsy.regime_dash`)→ `REGIME_DASH.md` / `.html` / `regime_dash.jsonl`; `regime_dash_ext.py` = 旗标转移 INFO 页 + 预注册规则建议(R1 双引擎同负→讨论降杠杆 / R2 FTRIM 可撤 / R3 席位换季 / R4 引擎A退潮; 冷却 24 锚)→ `recommendations.jsonl` + `PENDING_RULINGS.md`(待并入 STATE §3)。
- `regime_weekly.py` 每周日 09:00 local(launchd `com.hsy.regime_weekly`)→ `REGIME_WEEKLY_<date>.md` + INFO 页。
- 历史基准 `regime_hist_pct.json` / `regime_hist.npz`(jpline `jp_regime_hist.py`, B 面板 2023+)。
- 网页(私有 artifact, 每锚深查时由会话重发布同路径 REGIME_DASH.html): https://claude.ai/code/artifact/f8379cee-36ae-4864-acf9-6c32bd890e19
- 纪律: 不改任何实盘文件; 旗标/建议 = 信息, 动作归用户; 单锚数字噪声大, 判断看 30 锚累计与百分位漂移。
