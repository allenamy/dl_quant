# RUNBOOK: 宽书月度重训+换装 v2(2026-10 执行用; 定稿于 09-01 首跑收官)

> **创建:** 2026-09-01 | **Session:** 6737834a(重训战役) | **状态:** 待执行(10-01 前后) | **作废条件:** 被更新月版取代或 combo 方案退役
> 首跑全受据: `multi_asset/exports/research/retrain_2026-09/MANIFEST.md`(脚本×机器×门表+偏差D1-D5)+ `journal_2026-09-01_retrain_king_v3.md` + PREREG addendum(c24b8d2f)+ AMENDMENT A1(d2d20f5)。
> **脚本单一真相源 = `multi_asset/exports/research/retrain_2026-09/`(git); pod/jpline 上只放运行副本。**

## §0 原则(不变式)

1. 重训 = **两个分离的显式版本事件**: king bundle(RUNBOOK 主流程)与 f10(addendum §A), 各自静默窗换、各自首锚验收、单变量留痕; 宇宙刷新 = 第三事件(§B, ≥3 天间隔 + 用户字)。
2. 判据冻结先于数字; 任一门红 = 不换版, 红因走「对账→干预实验→修复或呈裁定」链(09-01 守卫红为模板); 判据修订只经 AMENDMENT 显式落墨。
3. 产物 `_ext/_v3splice` 命名不覆盖上代(D1 教训); 换装必备份旧件(bundle 目录+tar; f10 np 文件)。
4. 复跑/重启命令逐字抄本文, 不凭记忆; ssh 全内联(**zsh 不分词**: 禁 `$SSH` 缩写/`set -- $var`, E-0901 两咬)。
5. 验证只认输出增长与终态标记; 长任务 nohup + 落盘标记(CHAIN_DONE 类), 守望 grep 终态。

## §1 前置(pod 到手后 15 分钟)

```bash
# 环境引导(幂等): multi_asset/exports/research/retrain_2026-09/pod_env_bootstrap.sh
scp -P <PORT> -i ~/.ssh/id_ed25519 multi_asset/exports/research/retrain_2026-09/*.py \
    multi_asset/exports/research/retrain_2026-09/*.sh root@<POD>:/workspace/
ssh ... 'bash /workspace/pod_env_bootstrap.sh'   # pandas/sklearn/lightgbm + torch>=2.7 cu128(Blackwell sm_120), 全断言
```
- 卷上必在: `dlnative_5m_wide829_f16_ext.npz`(上月缓存)· `wide_panel_4h_v3splice.npz` + `fund_state_canoncont.json`(**滚动正典**: 本月平价基线=上月 splice 产物)· `wide_multisrc/funding/`(zip 库, 增量)· `panel_symbols_wide.txt` · `dlw_ext/` `f8_ext/`(上月 f10 输入, 作旧代对照)。
- **live_pins.json 每月重抄**自在役 bundle config(symbols_live/keep_names 可能因宇宙事件变更): mac `python3 -c "...wide_shadow/shadow_bundle/config.json..."` → scp。
- **基线 json 每月重立**(slow_scorer_v3base.json 模式): 门② = 上月记录折 IC; 门③ = 在役 bundle provenance.pinned_ic2026。**2026-10 用值: fold24 +0.0548 / fold25 +0.0630 / ic26 +0.0584**(09-01 v3 记录)。

## §2 数据层(~40 分钟, 全 CPU)

| 步 | 命令(pod /workspace) | 门(冻结) | 09-01 实测 |
|---|---|---|---|
| 1 vision 增量 | `EXT_DAYS=<上月逐日> python3 pod_extend_vision.py` | 404=新币缺日正常 | err 0 |
| 2 funding zip 增量 | `python3 pod_fund_zips.py`(MONTHS 改含上月; 幂等跳过已有) | err=0(残留单文件由门①裁) | 19,608 zip |
| 3 AUG 尾巴 | `python3 fund_pull_pod.py`(≤3.5req/s, 锚窗外) | 对实盘账本抽查 | 0.00e+00 |
| 4 缓存合并 | `EXT_END=<月末+1> python3 pod_merge_cache_ext.py` | 重叠逐位 exact_eq≥0.999 | 1.000000 |
| 5 面板重算 | `bash pod_run_chain.sh`(panel_ext+fea_ext; PANEL 基线env指**上月 splice**) | 内建7列 + **pod_gate1_full.py 全列≥0.999** | 18/18(15列=1.0) |
| 6 splice 滚动 | `python3 pod_panel_splice.py`(CAN=上月splice, cut=其末锚) | cut行逐位==正典; 尾部kline==ext | 断言过 |

> 门①若 funding EMA 列红: 先查 zip 覆盖(D3), 再走 09-01 对账链; **corr≥0.999 过门≠够用**——splice 滚动是常规步不是应急步(D5)。

## §3 king 轨(~30 分钟)+ bundle 换装

1. `python3 pod_export_bundle_v3.py`(env: `EXPORT_PANEL=<splice> EMA_STATE_JSON=<canoncont>`)。内建门:
   门② 2024/25 折 IC |Δ|≤0.004 · 门③ ic26 ±0.006 · 守卫 2.27..2.57(带心重标=裁定项; 红先归因: 窗口新尾 vs 仪器, 09-01 干预实验为模板)· keep/宇宙断言=pins。
2. **门V4-king**(jpline): `jp_king_v4.py <fea.npy> <meta.npz>`(基线改本月 pod 数)→ 三折 |Δ|≤0.004。09-01: Δ=±0.0000。
3. 换装(锚间静默窗, mac):
```bash
scp ...:/workspace/shadow_bundle_v3.tar.gz ~/wide_shadow/   # sha 两端比对
launchctl bootout gui/$(id -u)/com.hsy.shadowloop
cd ~/wide_shadow && mv shadow_bundle shadow_bundle.<代号>_backup && mv shadow_bundle.tar.gz shadow_bundle.tar.gz.<代号>_backup
tar xzf shadow_bundle_v3.tar.gz && venv/bin/python acceptance.py   # 必须 ALL_GREEN 4/4
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist
# 验: shadow.lock PID 命令行含 shadow_loop_v3.py run; launchctl print 含 SHADOW_OFFSET_MIN=16
```
4. 首锚验收: shadow_log booster_sha 翻版 + kc/fc own + 改写幅度无跳变>3pp(09-01: 15.98%, −0.45pp)。

## §4 f10 轨(~90 分钟)+ 换装

1. 输入链: `bash pod_f10_inputs_chain.sh`(targets→**pod_gate_dlw_ext.py**→fea82→fea89; targets/fea82 env 指 splice 面板)。
   门: y4s/qvk corr≥0.999(实测 1.000000)· YRZ ≥0.999(0.999910)· members 全等或 TIE_EXEMPT(qvk 逐位相等的 NTOP 平位才豁免)。
2. legs: `python3 pod_legs_ext.py`(旧行逐字+新锚同公式; 自验证 Z24/ZFD exact≥0.999, 实测 1.0000)。
3. 部署重训: `SEED=42 python3 pod_f10_refit_ext.py`(+2027; GPU 各 ~7.5min)。配方硬编码=冻结(COST 3.52/LDD 0.25/15ep/3e-4)。
4. 门V1: `SEED=<s> python3 pod_f10_np_export.py` → Spearman≥0.99999 & maxabs≤1e-5(实测 1.0000000/1e-7)。
5. 门V2(**同装置双数据法**, 全史件不评历史): `ARM=V2MAIN V2=1 SEED=<s> F10_DLW=<旧|新> F10_OUT=<旧|新> python3 pod_f10_train_ext.py` ×4 → preds 中继 jpline `f8_2026-08-22/preds/` → `bash jp_w10_v2gate_runner.sh`(conda python; hardened 装置 9f15dea0131f 逐字)→ `jp_w10_v2gate_judge.py`: 双种子 ΔNet(2023+) CI 下界 ≥−0.10, >+0.30=SUSPECT。09-01: −0.009/−0.030。
6. 门V3′(AMENDMENT A1): `python3 pod_f10_v3_leakcheck_v2.py` → 未来侧无峰 + 谱形与在役代逐k |Δ|≤0.03 + 折外泄出=0。09-01: 0.019/0.024/0。
7. 门V4-np(jpline): `jp_v4_np_check.py` → maxabs≤1e-5(实测 2.78e-16)。
8. 换装(全门绿 + 静默窗; 消费者每锚新进程加载 ⇒ 原子 mv 即生效零重启):
```bash
cp <新np> ~/wide_shadow/fea171/f10_live_s42_np.npz.tmp
mv ~/wide_shadow/fea171/f10_live_s42_np.npz ~/wide_shadow/fea171/f10_live_s42_np.npz.<代号>_backup
mv ~/wide_shadow/fea171/f10_live_s42_np.npz.tmp ~/wide_shadow/fea171/f10_live_s42_np.npz
shasum -a 256 ...   # == pod 训练产物
```
9. 首锚验收(=换版锚): kc/fc own + n_f10 400 + 改写无跳变>3pp。

## §5 收口(30 分钟)

journal 追记(门表全数+换版锚+sha)→ STATE 横幅+§1 事实行 → MANIFEST 增补 → memory 更新 → 双仓 commit。上月 pod 大件(fea/panel/preds)留卷即可, 小件(models/results/config)git 归档。

## §6 提速账(09-01 实测 → 10 月预算)

DL refit 7.5min ×2 / walk-forward 4折 20min ×4(并发=25min)/ king+bundle 21min / w10 回放 5min / 数据层 40min ⇒ **关键路径 ~2.5h**。09-01 耗 12h 的三类一次性成本已治: 环境熵(→pod_env_bootstrap.sh)/ 脚本散落(→git 单源)/ 基线缺位(→splice+state 滚动留卷)。剩余人窗: 静默窗对齐(换装只能锚间)。
