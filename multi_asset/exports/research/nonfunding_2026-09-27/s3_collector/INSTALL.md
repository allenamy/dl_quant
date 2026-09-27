> **创建:** 2026-09-27 02:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(alloc) | **状态:** 安装步骤,交 lead 执行(判据 DECISION_RULE_nonfunding_sources_2026-09-27 §0-4) | **作废条件:** xvenue_collect.py 或 plist 的 sha 与下文不符

# S3 前向采集器:安装步骤(由 lead 执行)

- 采集器 `xvenue_collect.py` sha256 `db3d1ac2affb73e44c22eab8621aa3ada66483de4f7a8b5cc94cfcec8bfd0f9c`
- launchd 配置 `com.hsy.xvenuecollector.plist` sha256 `c96cce2806c23405d2c23517f539105d1436c9e98022a41ddceb161df50e2d28`
- 只读三个非币安场所的公共行情接口:OKX、Bybit、Hyperliquid。每次运行每个场所最多请求一次(launchd 每 60 秒触发一次)。出错按指数退避(60 秒 × 2^k,上限 30 分钟)。不用任何密钥,不碰账户接口,不碰币安。
- 仅用标准库,由 macOS 自带的 /usr/bin/python3 执行。目录放在 ~ 下,不在 ~/Desktop(见 launchd 的 TCC 限制)。
- **试运行**(本地,测试根目录,02:15Z):三所各一次快照,OKX 492 行、Bybit 891 行、HL 234 行。60 秒内第二次运行按限速跳过。gzip 多成员可以正常读回。
- **磁盘**:每次快照压缩后约 40 KB,折合约 58 MB/天、6 个月约 10 GB。可用空间低于 20 GB 时停写,只记 DISK_LOW。本机当前可用约 60 GB。若要减半,可把 StartInterval 改为 120。

## 安装
```bash
SRC=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/nonfunding_2026-09-27/s3_collector
mkdir -p ~/xvenue_collector/logs
cp $SRC/xvenue_collect.py ~/xvenue_collector/ && chmod 755 ~/xvenue_collector/xvenue_collect.py
shasum -a 256 ~/xvenue_collector/xvenue_collect.py        # 必须等于 db3d1ac2affb73e44c22eab8621aa3ada66483de4f7a8b5cc94cfcec8bfd0f9c
cp $SRC/com.hsy.xvenuecollector.plist ~/Library/LaunchAgents/
shasum -a 256 ~/Library/LaunchAgents/com.hsy.xvenuecollector.plist   # 必须等于 c96cce2806c23405d2c23517f539105d1436c9e98022a41ddceb161df50e2d28
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.xvenuecollector.plist
```

## 验证(安装后约 2 分钟)
```bash
launchctl print gui/$(id -u)/com.hsy.xvenuecollector | grep -E 'state|runs|last exit code'
cat ~/xvenue_collector/state/heartbeat.json               # run_utc 距当前不超过 2 分钟;三所为 ok:N
tail -3 ~/xvenue_collector/logs/collect_$(date -u +%F).log  # 每分钟一行 RUN
ls ~/xvenue_collector/data/$(date -u +%F)/                 # okx.csv.gz bybit.csv.gz hl.csv.gz
```

## 巡检与终态
- 活着的证据:heartbeat.json 的 run_ms 不老于 3 分钟。
- 终态标记(写在当天的日志里):`DISK_LOW`。
- 某个场所的 `fail_streak` 与 `last_error` 记在 ~/xvenue_collector/state/venues.json。

## 卸载 / 回滚
```bash
launchctl bootout gui/$(id -u)/com.hsy.xvenuecollector
rm ~/Library/LaunchAgents/com.hsy.xvenuecollector.plist     # 数据目录 ~/xvenue_collector/data 保留
```
