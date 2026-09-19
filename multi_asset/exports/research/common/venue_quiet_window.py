#!/usr/bin/env python3
"""研究侧访问 Binance 场所(fapi / api, 公开或只读密钥)的静默窗守卫。只读。

为什么: 本机出口 IP 与实盘执行器共用场所的每 IP 请求权重(REQUEST_WEIGHT 2400/分钟)。2026-09-19 两次研究侧请求落在实盘锚内:
  04:41–04:52Z 平仓闭合重拉 + 全量收入拉取 ⇒ 场所报告的 1 分钟用量峰值 2010/2400 = 83.8%(执行器自己 60–945), 越过执行器 80% 的等待线;
  08:49Z 执行器克隆电池的 DRY_RUN 入口格 566 次公开 GET ⇒ 1316/2400(执行器自己 600)。
  两次都没有触发等待或封禁, 但封禁会让实盘锚失败。错题 E-0919-V。

静默窗(本机时钟, UTC; N ∈ {00,04,08,12,16,20}Z 为最近一个已开始的锚):
  开放 ⇔ ① 当前时刻 ∈ [N + 1:00, N + 3:40](生产者 N+0:00 起拉数据, 执行器 N+0:24 起下单, 收尾常到 N+0:55; 下一锚生产者 N+4:00 起)
         ② 执行器锚日志里最后一条「anchor start」之后已有「anchor done」, 或那条 start 已超过 STALE_START_MIN 分钟(崩掉的锚不永久锁死, 但仍受 ① 约束)
         ③ 锚日志可读(读不到 ⇒ 关闭: 未知不是开放)
  剩余分钟 = N + 3:40 − 现在。
用法:
  from venue_quiet_window import require_quiet_window, wait_for_quiet_window
  require_quiet_window(min_remaining_min=20)   # 开始一次拉取前: 不开放或剩余不足 ⇒ SystemExit(具名原因)
  wait_for_quiet_window(min_remaining_min=5)    # 长拉取的请求之间: 不开放就睡到下一次开放(不中途越窗)
命令行: python3 venue_quiet_window.py [--json]  打印当前状态, 退出码 0 = 开放, 3 = 关闭。
覆盖: 环境变量 VENUE_QUIET_WINDOW_OVERRIDE=<理由> 可绕过, 理由会写入返回值与 stderr; 只用于用户明确批准的情形。
data.binance.vision(公开归档下载)不走 fapi 权重, 不需要本守卫。"""
import calendar, json, os, sys, time

ANCHOR_LOG = os.path.expanduser("~/dl_quant_live/state/anchor_runs.log")
OPEN_AFTER_MIN = 60          # N + 1:00
CLOSE_AT_MIN = 220           # N + 3:40
STALE_START_MIN = 90         # 超过 90 分钟仍无 done 的 start 视为已结束(崩溃), 只报不锁
TAIL_BYTES = 262144


def _parse_ts(line):
    try:
        return calendar.timegm(time.strptime(line[:20], "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, IndexError):
        return None


def _last_start_done(path):
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END); size = fh.tell()
        fh.seek(max(0, size - TAIL_BYTES)); tail = fh.read().decode("utf-8", "replace")
    last_start = last_done = None
    for ln in tail.splitlines():
        head = ln[20:33]                          # 行格式: "YYYY-MM-DDTHH:MM:SSZ anchor start mode=…" / "… anchor done rc=…"
        if head == " anchor start":               # 只认行首位置, 不认 JSON 里引用的同名文本
            t = _parse_ts(ln); last_start = t if t is not None else last_start
        elif ln[20:32] == " anchor done":
            t = _parse_ts(ln); last_done = t if t is not None else last_done
    return last_start, last_done


def quiet_window_status(now=None, log_path=ANCHOR_LOG):
    now = time.time() if now is None else float(now)
    N = int(now // 14400) * 14400
    since_min = (now - N) / 60.0
    st = {"now_utc": time.strftime("%FT%TZ", time.gmtime(now)), "anchor_N_utc": time.strftime("%FT%TZ", time.gmtime(N)),
          "minutes_since_N": round(since_min, 1), "window": f"[N+{OPEN_AFTER_MIN}m, N+{CLOSE_AT_MIN}m]",
          "remaining_min": round(CLOSE_AT_MIN - since_min, 1), "open": False, "reason": None, "override": None}
    ov = os.environ.get("VENUE_QUIET_WINDOW_OVERRIDE")
    try:
        last_start, last_done = _last_start_done(log_path)
    except OSError as e:
        st["reason"] = f"anchor log unreadable ({type(e).__name__}) — unknown is not open"
        return _apply_override(st, ov)
    st["last_anchor_start_utc"] = time.strftime("%FT%TZ", time.gmtime(last_start)) if last_start else None
    st["last_anchor_done_utc"] = time.strftime("%FT%TZ", time.gmtime(last_done)) if last_done else None
    if last_start is None:
        st["reason"] = "no 'anchor start' line found in the log tail — unknown is not open"
        return _apply_override(st, ov)
    in_progress = (last_done is None or last_done < last_start)
    stale = in_progress and (now - last_start) / 60.0 > STALE_START_MIN
    st["anchor_in_progress"] = in_progress and not stale
    st["stale_start"] = stale
    if since_min < OPEN_AFTER_MIN:
        st["reason"] = f"inside the live anchor span (N+{since_min:.0f}m < N+{OPEN_AFTER_MIN}m)"
    elif since_min >= CLOSE_AT_MIN:
        st["reason"] = f"too close to the next anchor (N+{since_min:.0f}m ≥ N+{CLOSE_AT_MIN}m)"
    elif in_progress and not stale:
        st["reason"] = "executor anchor still in progress (last 'anchor start' has no later 'anchor done')"
    else:
        st["open"] = True
        st["reason"] = "open" + (" (last start had no done after >90 min — treated as ended, reported)" if stale else "")
    return _apply_override(st, ov)


def _apply_override(st, ov):
    if ov and not st["open"]:
        st["override"] = ov; st["open"] = True
        print(f"[venue_quiet_window] OVERRIDE used: {ov} (would have been closed: {st['reason']})", file=sys.stderr)
    return st


def require_quiet_window(min_remaining_min=20, now=None, log_path=ANCHOR_LOG):
    st = quiet_window_status(now, log_path)
    if not st["open"]:
        raise SystemExit(f"[venue_quiet_window] REFUSED: {st['reason']} · now {st['now_utc']} · anchor N {st['anchor_N_utc']}")
    if st["override"] is None and st["remaining_min"] < min_remaining_min:
        raise SystemExit(f"[venue_quiet_window] REFUSED: only {st['remaining_min']} min left in the quiet window (< {min_remaining_min})")
    return st


def wait_for_quiet_window(min_remaining_min=5, poll_s=60, log_path=ANCHOR_LOG, _sleep=time.sleep, _now=time.time):
    waited = 0.0
    while True:
        st = quiet_window_status(_now(), log_path)
        if st["open"] and (st["override"] is not None or st["remaining_min"] >= min_remaining_min):
            st["waited_s"] = waited
            return st
        _sleep(poll_s); waited += poll_s


if __name__ == "__main__":
    st = quiet_window_status()
    print(json.dumps(st, indent=1, ensure_ascii=False) if "--json" in sys.argv else f"{'OPEN' if st['open'] else 'CLOSED'} · {st['reason']} · remaining {st['remaining_min']} min")
    sys.exit(0 if st["open"] else 3)
