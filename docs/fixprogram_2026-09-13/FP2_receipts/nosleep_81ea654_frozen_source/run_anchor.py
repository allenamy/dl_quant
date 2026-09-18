#!/usr/bin/python3
"""One anchor, end to end: phase A (signal + passive maker) -> wait k -> phase B (top-up + rows).

Invoked by launchd at each UTC anchor (00/04/08/12/16/20 = SGT 08/12/16/20/00/04).

★ A single 15-minute process is DELIBERATE — two separate wakeups would need the pending state to
survive a process boundary: one more state file that can go stale, one more half-written handoff.
One process, one lifetime, no handoff.

★ Shebang is /usr/bin/python3 EXPLICITLY: this machine has three pythons and bare `python3`
resolves to the one WITHOUT torch — two people independently concluded "no torch" in one day.
Knowledge like this lives at the ENTRANCE, not in an implementation comment.

★ Locking uses fcntl.flock on a file: macOS has no flock(1) COMMAND (a Linux util), but the
syscall exists everywhere. A stuck previous anchor must not be joined by a second one — the
lock-skip is logged, because a silently skipped anchor and a missed cron look identical otherwise.
"""
import fcntl
import json
import os
import signal as _signal
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ★★★ `ops` BELONGS HERE, AND ITS ABSENCE KILLED A WHOLE ALERT TIER (2026-07-30).
# `alarm_episode` lives in ops/, and ops/ was only inserted at the funding/factor-health blocks
# far below — so any code ABOVE those lines that imported it raised ModuleNotFoundError, was
# swallowed by its own `except Exception`, and left one log line. Measured: 6 occurrences of
# "investigate-tier alert failed: No module named 'alarm_episode'", including the real 00:17Z
# anchor. `check_factor_health` used the same module successfully only because its call site
# happens to sit BELOW the late insert. **A module's availability depended on where in this file
# you stood** — which is not a property anyone can be expected to hold in their head.
# ★ Listed FIRST so it ends up LAST in sys.path (the loop inserts at 0), i.e. the lowest
#   precedence of the four — the most conservative placement. Verified 2026-07-30: no module
#   name is shared between scheduler/ live/ signal/ ops/, so precedence changes nothing today;
#   the ordering is chosen so it also changes nothing if a collision appears later.
for d in ("ops", "scheduler", "live", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))

# ★★ IMPORTED AT MODULE LOAD, DELIBERATELY, NOT INSIDE THE ALERT BLOCKS. A missing alarm module
# must kill this process at startup, loudly, rather than be discovered at the moment an alarm is
# supposed to fire — which is the one moment nobody is watching the logs. That is what happened:
# the tier was dead from birth and its failure looked exactly like "no alert was warranted".
import alarm_episode as AE                                              # noqa: E402

# ★ Load .env OURSELVES — launchd does not source shell profiles or .env files. Every manual
# test passed because the interactive shell had sourced .env; the launchd context had no
# TELEGRAM_* at all, so the first scheduled anchor's alert died as NOT_CONFIGURED. An entry
# point must not assume its launcher prepared the environment.
# ★★ THE LOADER IS NOW SHARED (2026-08-01). This file had the only working copy, so the lesson
#    above was learned per-FILE: `ops/unseed_rehearsal_halt.py` paged HIGH about clearing the LIVE
#    halt and the receipt came back NOT_CONFIGURED — composed, audited locally, never sent. See
#    live/envfile.py.
import envfile as _envfile                                              # noqa: E402
_envfile.load()

STATE = os.path.join(REPO, "state")
os.makedirs(STATE, exist_ok=True)
# ★ 可重定向, 与 LIVE_ANCHOR_LOCK / LIVE_ANCHOR_SKIPS / LIVE_NOTIFY_AUDIT 同一族, 且理由是
#   tests_anchor_skip_visible 自己写下的那句: "a test row in it is a fabricated non-event sitting
#   where an operator looks." 那个套件重定向了 skip【记录】, 却没有重定向【日志】—— 于是它每跑
#   一次就往生产 anchor_runs.log 里写三行
#     "SKIP: previous anchor still holds the lock (mode=LIVE) — this anchor did NOT run"
#   实测: 2026-08-06T08:44:17Z 三行, 由 08:44:47Z 那次提交前的验收电池产生; 而在 2026-08-06
#   09:1xZ 复盘时, 这三行让我一度判定"锁泄漏, 12:00Z 会不调仓"。**它制造的是假事故。**
#   操作员会看的地方有两处, 上一版只堵住了其中一处。
RUNLOG = os.environ.get("LIVE_ANCHOR_LOG", os.path.join(STATE, "anchor_runs.log"))


def log(msg: str):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line)
    with open(RUNLOG, "a") as f:
        f.write(line + "\n")


def _page_phase_crash(notifier, phase: str, exc: BaseException) -> None:
    """E-0909-D: an exception out of a trading phase must PAGE before it kills the process.

    ★ The arm() block in main() already does this for arming refusals (E-0825-I); phase A and B
      had no such wrapper, so the 2026-09-09 12:00Z transport crash left only a traceback in
      anchor_runs.log — "the anchor failed" and "nobody was told" are two different incidents.
    ★ The page must never change the exception's propagation: alarm failure is swallowed here
      and the caller re-raises. The body embeds the exception text, so the 24h body-sha dedup
      cannot swallow a repeat with a different cause.
    """
    try:
        notifier.alarm("CRITICAL",
                       f"锚点{phase}异常退出: {type(exc).__name__}: {str(exc)[:400]}\n"
                       f"进程即将以非零码退出。若发生在下单之后, 在飞单已由 submit_with_cleanup "
                       f"处理(见同一时刻的告警); 否则下一锚开场扫单兜底。请核对 openOrders 与账本。")
    except Exception:                                           # noqa: BLE001 — must not mask
        pass


def main() -> int:
    # ★ THE LOCK PATH IS OVERRIDABLE, AND THAT IS A SAFETY FIX, NOT A TEST CONVENIENCE.
    # tests_entrypoint_wiring runs this file for real. On the production lock, a suite started at
    # :59 holds it into :00 and the SCHEDULED anchor takes the SKIP branch — §2.5 loses a
    # completion to a test run. (Same shape in reverse: acceptance run while an anchor is in
    # flight fails for a reason that has nothing to do with the code.) Same pattern, and the same
    # reason, as LIVE_LOOP_STATE / LIVE_KILL_SWITCH: production state must not leak into tests,
    # and a test must not be able to touch the real one. The scheduled path never sets it.
    # ⇒ NOTE THE COST, STATED RATHER THAN HIDDEN: with the override in use, that suite no longer
    # exercises the real lock file. The lock's own behaviour (a second anchor SKIPs) is covered
    # by the SKIP line in the run log and by ops/dryrun_ledger counting it as a non-completion.
    # ★★ A HUMAN STARTING AN ANCHOR NEXT TO A SCHEDULED ONE IS WARNED — BEFORE the lock, because
    #    after it the interesting case is already the silent SKIP. `isatty` is the discriminator:
    #    launchd gives no terminal, and the acceptance battery runs this through a pipe, so
    #    neither is warned. It is a WARNING and never a refusal — being locked out beside an
    #    anchor boundary is worst precisely during an incident, which is when a human runs this
    #    by hand. Until now this rule existed only in two people's memory.
    try:
        if sys.stdin.isatty():
            import book_config as _BCw
            _w = _BCw.collision_warning()
            if _w:
                log(_w)
    except Exception:
        pass

    lock_f = open(os.environ.get("LIVE_ANCHOR_LOCK", os.path.join(STATE, "anchor.lock")), "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # ★★★ A SILENT SKIP IS THE ONE FAILURE THAT LOOKS LIKE SUCCESS (2026-08-01).
        # `LOCK_NB` -> BlockingIOError -> one log line -> `return 0`. launchd records a clean run,
        # the exit code says success, and the anchor did not happen. `ops/dryrun_ledger` does read
        # the line and counts it as a non-completion — so it was not entirely unconsumed — but
        # nothing PAGED, and a ledger is read on purpose while a page arrives on its own.
        # ★ WHO ACTUALLY TAKES THIS BRANCH: not a second schedule. There is exactly one launchd
        #   label and one plist, and installing re-loads that same path, so two scheduled anchors
        #   cannot coexist. The real contender is a HUMAN RUN — a rehearsal, a hand-run anchor,
        #   `ops/live_dry_pass.sh` — overlapping the scheduled one, which is precisely what a
        #   go-live day is full of.
        # ★ THE MODE IS NAMED. The lock is opened before `SR.bind(mode)`, so this branch used to
        #   know nothing about which book it was skipping; "an anchor was skipped" and "the LIVE
        #   anchor was skipped" are not the same sentence.
        # ★ The exit code is deliberately UNCHANGED. Making a skip non-zero would alter what
        #   launchd believes happened — a change to a guard's consequence, which is not mine to
        #   make as a side effect of adding a page.
        _skip_mode = os.environ.get("LIVE_MODE", "DRY_RUN")
        log(f"SKIP: previous anchor still holds the lock (mode={_skip_mode}) — this anchor did "
            f"NOT run; the process holding the lock is a concurrent anchor or a manual run")
        try:
            # ★ REDIRECTABLE, for the reason the ban state learned an hour earlier today:
            #   this file is the record that an anchor DID NOT RUN, and a suite that writes
            #   into it puts an honest-looking record of an event that never happened in
            #   front of an operator. Same firebreak as LIVE_ANCHOR_LOCK / LIVE_NOTIFY_AUDIT.
            _srec = os.environ.get("LIVE_ANCHOR_SKIPS",
                                   os.path.join(STATE, "anchor_skips.jsonl"))
            with open(_srec, "a") as _sf:
                _sf.write(json.dumps({
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "mode": _skip_mode,
                    "lock": os.environ.get("LIVE_ANCHOR_LOCK",
                                           os.path.join(STATE, "anchor.lock")),
                    "meaning": ("this scheduled anchor did not run. The exit code is 0, so "
                                "launchd recorded a successful run — this file is the record "
                                "that it was not one.")}) + "\n")
        except Exception:
            pass
        try:
            import telegram_notify as _TNs
            _d = AE.decide("anchor_skip", [f"{_skip_mode}:lock_held"], mode=_skip_mode)
            if _d["alarm"]:
                _r = _TNs.TelegramNotifier().alarm(
                    "HIGH", f"锚点被跳过 (mode={_skip_mode}): 锁被另一个进程持有, **这一锚没有发生**。"
                            f"退出码仍是 0, 所以 launchd 记的是一次成功运行 —— 这条消息是唯一会主动"
                            f"找到你的记录。并发方通常是手工运行(彩排/手跑锚点), 而非第二套调度: "
                            f"launchd 只有一个 anchor 标签, 装新的会替换旧的。")
                if _r.get("delivered_offbox") or _r.get("status") == "SUPPRESSED":
                    AE.record("anchor_skip", _d["episode"], [f"{_skip_mode}:lock_held"],
                              mode=_skip_mode)
        except Exception as _e:
            log(f"SKIP: alarm failed ({type(_e).__name__}: {str(_e)[:80]}) — the skip is recorded "
                f"in state/anchor_skips.jsonl but nobody was paged")
        return 0

    mode = os.environ.get("LIVE_MODE", "DRY_RUN")   # DRY_RUN until the operator exports LIVE_MODE
    log(f"anchor start mode={mode}")

    # ── state root: ONE variable moves with the mode, and it is asserted ────────────────────
    # A book computed from TESTNET mids must never become the live pilot's opening ledger; the
    # prices are close enough (median 2.4bps) that the mistake would not be visible afterwards.
    # But the isolation is one root, not two code paths — if testnet ran a different path set,
    # the configuration certified by five days would not be the one that goes live.
    import state_root as SR
    try:
        _paths = SR.bind(mode)
        SR.export_env(_paths)
        _delta = SR.assert_single_delta(mode)
        log(f"state root: {_paths['root']} (mode={mode}, single_delta={_delta['single_delta']})")
    except SR.StateRootError as e:
        log(f"STATE ROOT REFUSED: {e}")
        try:
            import telegram_notify as _TN
            _TN.TelegramNotifier().alarm("CRITICAL", f"状态根与模式不符, 锚点拒绝启动: {e}")
        except Exception:
            pass
        return 2

    # ── hard cap on this process ────────────────────────────────────────────────────────────
    # ★ fcntl.flock above is NON-BLOCKING: a hung run does not just fail itself, it makes the
    # NEXT anchor take the SKIP branch — and §2.5 (30 calls, >=98% completion) tolerates zero
    # skips. So a stuck process must die rather than take its successors down with it. SIGALRM
    # is used because it interrupts time.sleep(k), which is where most of the lifetime is spent.
    _cap = int(json.load(open(os.path.join(REPO, "config", "book.json"))).get("anchor_max_seconds",
                                                                             1500))

    def _too_slow(_sig, _frm):
        log(f"ANCHOR TIMEOUT: exceeded {_cap}s — self-terminating so the lock is released and the "
            f"next anchor is not skipped. Anything in flight is left to the venue; the next "
            f"anchor reconciles against venue truth before planning.")
        try:
            import telegram_notify as _TN
            _TN.TelegramNotifier().alarm(
                "HIGH", f"锚点进程超过 {_cap}s 上限, 已自杀以释放锁。若连续出现, 用 ops/KILL.sh 停机。")
        except Exception:
            pass
        os._exit(3)

    _signal.signal(_signal.SIGALRM, _too_slow)
    _signal.alarm(_cap)
    # the same instant SIGALRM is armed from, so "how long do I have left" is answerable by
    # anything downstream that can run long (today: the markout backfill)
    _T_START = time.time()

    import anchor_loop as AL
    import binance_broker as BB
    import binance_executor as EX
    import telegram_notify as TN

    _preds_st = None
    # ── 0. produce this anchor's prediction IN PLACE (fapi -> panel -> king/s2 -> preds file) ──
    # ★ It writes the SAME artefact the server shadow used to produce, so a failure needs no new
    # branch: nothing is written, the previous file keeps its old computed_ts, and the staleness
    # ladder below does what it already does. The one thing forbidden is writing a fresh
    # computed_ts with degraded content -- that turns "no signal" into "a wrong signal", which is
    # the single case the ladder cannot protect against. See signal/compute_preds.py.
    if os.environ.get("LIVE_COMPUTE_PREDS", "1") != "0":
        try:
            import compute_preds as CP
            import fapi_source as FS
            st = CP.refresh_preds(FS.FapiSource(), progress=lambda m: log(f"  preds: {m}"))
            _preds_st = st                      # kept for the gap alert, which needs `notifier`
                                                # and therefore cannot fire this early
            log(f"preds: {json.dumps(st, ensure_ascii=False, default=str)}")
            if not st.get("ok"):
                # not fatal: this is exactly the condition the ladder exists for. But it must be
                # SAID -- a silent skip and a healthy anchor look identical in the log otherwise.
                log(f"preds NOT refreshed ({st.get('reason')}) — this anchor runs on the previous "
                    f"prediction and the staleness ladder decides.")
        except Exception as e:
            log(f"preds producer crashed: {e} — falling back to the existing preds file")
    else:
        log("preds: in-place computation disabled (LIVE_COMPUTE_PREDS=0), using existing file")

    b = BB.BinanceBroker(mode=mode)
    try:
        log(f"arm: {json.dumps(b.arm(), ensure_ascii=False)}")
    except Exception as _arm_e:
        # ★★ E-0825-I (2026-08-25 16:23Z 实盘). arm() 的拒绝发生在告警阶梯**之前**: 场所把 HUSDT
        #    降到 4x, 本函数在此抛出未捕获异常, 进程 rc=1 退出 ⇒ 该锚零交易, **逐名止损层同处本
        #    进程因而一并停摆**, 而 notify_audit 里没有任何一条与之对应的投递 —— launchctl 只留下
        #    一个 "- 1"。**"拒绝启动"和"没人知道我拒绝了"是两件不同的事。**
        # ★ 告警自身失败不得改变原异常的传播(拒绝仍然是拒绝); 正文内嵌异常原文 ⇒ 每次 body 不同,
        #   不会被 24h body-sha 去重吞掉(该去重曾吞过 3 次止损页)。
        try:
            TN.TelegramNotifier().alarm(
                "CRITICAL",
                f"锚点拒绝启动(arm 断言失败): 本锚零交易, 且逐名止损层同处本进程一并停摆。\n"
                f"{type(_arm_e).__name__}: {str(_arm_e)[:400]}\n"
                f"修复: cd ~/dl_quant_live && LIVE_MODE={mode} python3 ops/setup_live_account.py "
                f"--mode {mode} --apply   (该脚本默认只读, --apply 是例外)")
        except Exception as _ae:
            log(f"arm-refusal alarm FAILED: {type(_ae).__name__}: {str(_ae)[:100]}")
        raise
    ex = EX.RebalanceExecutor(b)
    # ★ filters are loaded in EVERY mode now. /fapi/v1/exchangeInfo is public and unauthenticated,
    # and without it DRY_RUN never exercised tick/lot/minNotional rounding at all. Delistings and
    # new listings surface through this call, so it is refreshed per anchor rather than cached
    # forever — with a fallback to the last good cache if the fetch fails.
    try:
        ex.filters.load(max_age_s=0)          # 0 => always refresh; falls back to cache on error
        log(f"filters: {len(ex.filters.f)} symbols")
    except Exception as e:
        log(f"filters refresh failed ({e}); falling back to cached filters")
        try:
            ex.filters.load()
        except Exception as e2:
            log(f"filters cache also unavailable: {e2}")
    notifier = TN.TelegramNotifier()
    cfg = json.load(open(os.path.join(REPO, "config", "book.json")))
    # ★ read ONCE, early: several later blocks ask "is the certification window running?" to decide
    # whether a red state is expected (before the clock) or an alarm (during it). Deriving it twice
    # is how the same question gets two answers; deriving it late is how a NameError inside a
    # protective try-block turns into "the watchdog could not evaluate".
    clock_started = bool(cfg.get("dryrun_clock_start"))
    # ★ THE LOG SINK. Without this every row the anchor builds is discarded: `PilotLogger` was
    # never instantiated anywhere in production, so all six schema-v2 tables had zero rows and
    # SIX OF SEVEN STOP-LOSSES had no input at all. The pilot's entire output (M1-M6) is
    # reconstructed from these files after the fact -- "not written down" is not recoverable.
    import pilot_log as PLOG
    log_root = _paths["pilot_log"]
    plog = PLOG.PilotLogger(log_root)
    log(f"pilot_log: writing to {plog.dir}")
    # ★ 0, NOT the deprecated `gross_usdt_pilot_p0`. Since 2026-07-29 the book is sized as
    # nav x target_leverage inside the loop; seeding from the old constant would make the
    # FIRST anchor compute a leverage drift against a number that is no longer policy. A zero
    # seed means "no previous gross", which is exactly true at process start and forces the
    # first anchor to size from equity.
    loop = AL.AnchorLoop(b, ex, gross_usdt=0.0,
                         alarm=notifier.alarm, log=plog)

    outB = None
    try:
        outA = loop.run_anchor()
    except Exception as _ph_e:                                  # noqa: BLE001 — page, re-raise
        _page_phase_crash(notifier, "阶段 A (run_anchor)", _ph_e)
        raise
    # ★ leading underscore = in-process only, never logged. Was `k != '_pending'`, an enumerated
    # exemption that the next internal key would silently escape — and one arrived the same day
    # (`_rehearsal`, whose `checks` dict would have gone into every run log line for nothing). The
    # PUBLIC half of that state is surfaced as `rehearsal` when it is enabled, which is the part a
    # reader of the log needs.
    log(f"phase_A: {json.dumps({k: v for k, v in outA.items() if not k.startswith('_')}, default=str, ensure_ascii=False)}")

    if outA.get("action") == "TRADE" and "_pending" in outA:
        # ★ THE k WINDOW MUST BE REAL DURING THE CERTIFICATION WINDOW.
        # DRY_RUN used to sleep 1s instead of 900s, so a dry-run process lived ~1 minute against
        # ~16 minutes live. Everything measured against process lifetime was therefore measured on
        # the wrong scale by a factor of 16: lock contention, the anchor_max_seconds self-kill,
        # overlapping anchors, and "protection lasts as long as the process" all behave
        # differently at 1 minute than at 16. A 4-hour cadence has ample room for the real value.
        # `dryrun_fast_k` exists only for interactive smoke tests and is FALSE by default, so the
        # scheduled path always uses the real window unless somebody deliberately says otherwise.
        k = cfg.get("k_seconds", 900)
        # A test may opt in explicitly via LIVE_FAST_K=1; the scheduled path never sets it, so
        # the certification window cannot get the fast path by accident. Opting in is visible at
        # the call site rather than hidden in config.
        fast = ((bool(cfg.get("dryrun_fast_k", False)) or os.environ.get("LIVE_FAST_K") == "1")
                and mode == "DRY_RUN")
        k_used = 1 if fast else k
        log(f"k window: sleeping {k_used}s"
            f"{' (FAST — not representative; certification requires the real window)' if fast else ''}")
        time.sleep(k_used)
        try:
            outB = loop.complete_anchor(outA["_pending"], outA["anchor_ts"], outA["rebalance_id"])
        except Exception as _ph_e:                              # noqa: BLE001 — page, re-raise
            _page_phase_crash(notifier, "阶段 B (complete_anchor)", _ph_e)
            raise
        log(f"phase_B: {json.dumps(outB, default=str, ensure_ascii=False)}")

    # ── 5b. the three account-state tables ──────────────────────────────────────────────────
    # ★ ONE call site, deliberately: anchors / position_readback / daily_nav all derive from a
    # single post-anchor account read, and three separate writers would give three tables three
    # different opinions about what the book was. It runs BEFORE the watchdog so the stop-losses
    # evaluate against rows that are already on disk — the watchdog reads FILES, so a table
    # written after it would be one anchor stale at every anchor, forever.
    # ★ bound BEFORE the try: the watchdog call below reads `fin` for W6C-B13's producer verdict,
    #   and a phase_C that raised must leave the watchdog running on the record's own test — not
    #   kill it with a NameError, which would turn one failed table write into no stop-losses.
    fin = None
    try:
        fin = loop.finalize_anchor(outA, outB)
        log(f"phase_C: {json.dumps(fin, default=str, ensure_ascii=False)}")
    except Exception as e:
        log(f"phase_C FAILED: {e}")
        notifier.alarm("HIGH", f"账户状态三表本轮未写入 ({e}) — anchors/position_readback/"
                               f"daily_nav 缺这一个锚点, 事后无法补。")

    # ── 5c. funding ledger — the M6 stream, which had no writer at all ──────────────────────
    # ★ AFTER 5b, AND THAT IS NOT COSMETIC. The ledger prices each settlement off the newest
    # position_readback STRICTLY BEFORE it, so it must run once this anchor's readback is on
    # disk — otherwise every settlement inside the current anchor is priced off the PREVIOUS
    # anchor's book, which is the stalest reading still inside the assertion's bound.
    # ★ WHY IT EXISTS AT ALL: `FundingLedger` was fully implemented, fully tested, and never
    # constructed on the production path — `binance_funding` was imported only by its own test
    # suite. funding.jsonl's zero rows were not "no settlement yet"; there was no writer.
    try:
        import binance_funding as BF                                          # noqa: E402
        import book_config as _BC                                             # noqa: E402
        _fw = BF.write_funding_rows(b, plog, os.path.dirname(plog.dir),
                                    max_age_s=_BC.anchor_interval_s(),
                                    alarm=notifier.alarm)
        log(f"funding: income={_fw['n_income']} rows={_fw['rows_written']} "
            f"skipped_no_position={_fw['skipped_no_position']} "
            f"gap={_fw.get('gap', {}).get('status')} "
            f"sign={(_fw.get('sign_check') or {}).get('verdict')}")
    except Exception as e:
        log(f"funding ledger FAILED: {e}")
        notifier.alarm("HIGH", f"funding 账本本轮未写入 ({e}) — M6 缺这些结算, 且 income "
                               f"只保留 90 天。")

    # ── 6. watchdog — evaluate the stop-loss conditions on what just happened ────────────────
    # ★ Until now this existed only as a comment in the loop's docstring: the code was ported,
    # tested, and NEVER CALLED from this machine's entry point. A stop-loss nobody invokes is
    # indistinguishable from no stop-loss — and it would have looked healthy in every test,
    # because the tests call watchdog.run() directly. Same family as the two conditions that
    # were structurally dead in production: the gap is never inside a component, it is between
    # the component and whoever was supposed to call it.
    # ★ these imports live INSIDE the try. They used to sit outside it, so an import-time error
    # anywhere in the metrics/watchdog chain (a NameError from a refactor, say) would kill the
    # anchor before `anchor done rc=0` was ever written — i.e. it would silently leave the frozen
    # set. Rather than argue in prose about whether the metrics layer counts as "inside the loop",
    # a try makes it not count. Definition disputes become code facts.
    try:
        import watchdog as WD
        import watchdog_inputs as WI
        ops_stats, venue_events, wi_diag = WI.collect(log_root)   # (ops, events, diagnostics)
        ev, br, st = WD.run(log_root, broker=b,
                            venue_events=venue_events, ops_stats=ops_stats,
                            verbose=False,
                            state_dir=_paths["watchdog_dir"],
                            # ★ W6C-B13: the end-of-anchor producer's own verdict on whether it
                            #   managed to look at the book. Four different facts write zero
                            #   readback rows and the log shows one observable; only `fin` knows
                            #   which it was, and without this the watchdog falls back to the
                            #   record's weaker test (and says so in book_observability.reference).
                            book_observation=(fin or {}).get("book_observation"),
                            # ★ [e] the ONE production row writer, named explicitly: every other
                            # caller (scorer, resume gate, tests) scopes into its own state_dir.
                            rows_root=log_root)
        # ★ stamp the mode INTO the state file, so a reader can tell whose tree it is. See
        # state_root.stamp_mode: the isolation stops us writing to the wrong tree and does
        # nothing about reading one — and reading one is what happened during the first
        # real incident.
        try:
            SR.stamp_mode(os.path.join(_paths["watchdog_dir"], "state.json"), mode)
            SR.stamp_mode(os.path.join(_paths["watchdog_dir"], "last_eval.json"), mode)
        except Exception:
            pass
        tripped = bool(ev.get("tripped"))
        log(f"watchdog: tripped={tripped} n_days={wi_diag.get('n_days')} "
            f"public_path={wi_diag.get('public_path_probe')} "
            f"blind={ev.get('conditions_blind')} partial={ev.get('conditions_partial')}")
        # ★ A BLIND CONDITION LOOKS EXACTLY LIKE A SATISFIED ONE from the outside. Once the clock
        # is running, "seven stop-losses are watching" is a claim the certification rests on, so a
        # condition with no input has to be said out loud rather than inferred from a missing row.
        # ★★ THE PER-SYMBOL DUST FLOOR MUST BE AUDIBLE WHEN IT DEGRADES (0C, 2026-07-27).
        # `reconcile` reports `dust_floor.n_symbols_with_own_minimum` so that "the per-symbol
        # lookup is wired" and "the lookup came back empty" are different observables — but until
        # now NOTHING READ IT, so in practice they were the same observable after all. A ruling
        # that hands out a property and no action is inert.
        # ⇒ It degrades for TWO different reasons and this covers both: the filter cache is
        #   missing, or it was written by ANOTHER VENUE and the venue-stamp gate correctly refused
        #   it. The second is live right now: a DRY_RUN process writes mainnet filters into the
        #   shared cache, a TESTNET anchor writes testnet ones, and which of them last ran decides
        #   whether the floor is per-symbol at all. Measured 2026-07-27: 634 (TESTNET anchors at
        #   08:01Z/12:00Z) alternating with 653 (six DRY_RUN runs, 14:38-15:14Z).
        # ⇒ The numbers are already protected — the gate stops mainnet minimums reaching a testnet
        #   guard. What was NOT protected is anyone KNOWING the floor had silently fallen back to
        #   the global 5.0, which is the state B20 was written to leave behind.
        try:
            _df = ((ev.get("conditions", {}).get("cond5_venue_event", {})
                    .get("5b_liquidation_anomaly", {})) or {})
            if _df.get("dust_floor_degraded") and mode != "DRY_RUN":
                notifier.alarm("HIGH",
                               f"逐币尘埃地板已退化为全局 5.0 —— "
                               f"{(_df.get('dust_floor') or {}).get('source')}. "
                               f"§4-5b 现在对每个符号用同一个门槛; BTC(50)/ETH(20) 这类名字上的"
                               f"残差会被当作可行动而告警。下一个锚点刷新 filters 后自愈。")
            # ★★ [D3] AND THE SAME DEFECT HAD A TWIN ONE FIELD OVER, WRITTEN THE SAME DAY.
            # B30 added `n_unreconcilable_latest` and the `_5b_state` vocabulary
            # (CLEAN/PARTIAL/ANOMALOUS/UNKNOWN) so that "compared, and clean" would stop looking
            # like "could not compare a single name" — and then gave neither a reader, so on
            # `triggered` they remained exactly the same value. Six hours after closing the dust
            # floor's zero-consumer defect, in the fix for the guard the dust floor belongs to.
            # ⇒ PARTIAL is the state that must be audible: §4-5b reports triggered=False while
            #   some of the book was never compared at all. It does NOT trip — a gap in our own
            #   record is not evidence of a position anomaly — but it is not silence either.
            _st, _nu = _df.get("state"), (_df.get("n_unreconcilable_latest") or 0)
            if _nu and mode != "DRY_RUN":
                notifier.alarm("HIGH",
                               f"§4-5b 本锚点有 {_nu} 个名字【根本没能比较】(state={_st}): "
                               f"{[u.get('symbol') for u in (_df.get('unreconcilable_examples') or [])]} "
                               f"— triggered=False 在这些名字上不是'查过且干净', 是'没查'。"
                               f"分类: {_df.get('n_unreconcilable_window')} 条/窗口。"
                               f"最常见成因是 readback 行缺 venue_position_qty(旧行), "
                               f"新写入已由 schema 强制。")
        except Exception as e:
            log(f"dust_floor check failed: {type(e).__name__}: {e}")
        # ★★ §4-5e FLAT-INTENT RESIDUALS: NAMED AND PAGED, WITHOUT STOPPING THE BOOK
        # (ruling 2026-07-29). On a halted anchor the intent is ZERO, so any name above the venue
        # dust floor is exposure we believe we do not have. The portfolio limit (1%) decides
        # whether to STOP; this decides whether anyone is TOLD. 24 USDT is not worth a halt and is
        # absolutely worth a sentence.
        # ★ IT IS PAGED HERE RATHER THAN LEFT AS A FIELD ON PURPOSE. `investigate`, the existing
        #   alert-only convention (§4-2's -2.68% level, the leverage alert), is written by two
        #   conditions and READ BY NOBODY — so following that convention would have produced a
        #   rule that is satisfied on paper and silent in practice. An alert-only threshold whose
        #   alert has no consumer is not a lower rung; it is a comment.
        try:
            _5e = (ev.get("conditions", {}).get("cond5_venue_event", {})
                     .get("5e_position_break") or {})
            _5e_latest = _5e.get("latest") or {}
            _named = _5e_latest.get("flat_intent_named_symbols") or []
            if _named and not tripped:
                # ★★ EPISODE-DEDUPED, AND I HAD TO COME BACK AND ADD THIS. The first version paged
                # unconditionally every anchor — the exact defect I diagnosed in check_factor_health
                # this morning (throw before `_AE.record` => no dedup => pages every cycle at
                # wake-up severity => the channel gets muted by its users). Writing the diagnosis
                # does not immunise you against the disease; only the shared mechanism does.
                # ★ The fingerprint is (symbol, rounded qty), so a residual that CHANGES pages
                #   again — a ghost that grew is a new fact, not a repeat of an old one.
                _find = [f"{d['symbol']}:{d['dev_usdt']:.2f}" for d in _named]
                _txt = ", ".join(f"{d['symbol']} {d['dev_usdt']:+.2f}" for d in _named[:8])
                _msg = (f"§4-5e 停机锚点仍持有 {len(_named)} 个名字(意图=平): {_txt} — "
                        f"合计 {_5e_latest.get('portfolio_dev_usdt', 0):.2f} USDT "
                        f"({_5e_latest.get('portfolio_dev_frac', 0):.2%} of gross, 停机线 "
                        f"{_5e_latest.get('portfolio_limit_frac', 0):.1%})。未达停机线, 不停机 —— "
                        f"但这是我们以为不存在的敞口, 它自己不会消失。")
                _d5 = AE.decide("pb_flat_intent_residual", _find, mode=mode)
                if _d5["alarm"]:
                    _r5 = notifier.alarm("HIGH", _msg)
                    if _r5.get("delivered_offbox") or _r5.get("status") == "SUPPRESSED":
                        AE.record("pb_flat_intent_residual", _d5["episode"], _find, mode=mode)
                else:
                    log(f"5e flat-intent residual: {_d5['reason']}")
        except Exception as e:
            log(f"5e flat-intent alert failed: {type(e).__name__}: {e}")
        # ★★ [B, 2026-08-03] THE ALARM HALF OF THE SPLIT — UNDERFILL / UNMEASURABLE / LINE ORDER.
        # These three are the reason the split is not just a narrower stop-loss: each is a real
        # finding whose correct response is a sentence, never a flatten.
        #   UNDERFILL    the book did not finish building. The next anchor re-targets it; the
        #                repair path already exists and a second one would trade the same gap
        #                twice (prereg §6bis.4). It may NEVER become a halt at any magnitude.
        #   UNMEASURABLE the residual is UNKNOWN, not zero. Counted apart and deliberately kept out
        #                of the halt, or the split would merely demote "benign + dangerous in one
        #                number" to "data gap + dangerous in one number" (lead's ruling, §4).
        #   LINE ORDER   §4-6's effective limit has fallen below §4-5e's unauth line, i.e. the gate
        #                that waits three days has become the more sensitive of the two. That is a
        #                configuration fault, not a book fault — page, do not stop.
        # ★★★ THE PROVENANCE SENTENCE IS READ FROM THE RECORD. `unauth` is inherited whole from
        #     `expected_qty = qty(T1) + sum dq_fills`; if that is wrong BOTH buckets are wrong
        #     together, and the person reading this page needs to know that instantly. Composing
        #     the sentence here would be a fact asserted by the side that does not produce it.
        # ★ THE COMPOSITION LIVES IN `watchdog.split_alarm`, A PURE FUNCTION OF `ev`. Written
        #   inline it would inherit every local the block above defines — so a failure THERE would
        #   silently disarm this — and it could not be exercised without running an anchor, which
        #   is how the flat-intent alert above stayed dead and latent for a day.
        try:
            _sa = WD.split_alarm(ev)
            if _sa and not tripped:
                _d6 = AE.decide("pb_split_alarm", _sa["fingerprint"], mode=mode)
                if _d6["alarm"]:
                    _r6 = notifier.alarm("HIGH", _sa["message"])
                    if _r6.get("delivered_offbox") or _r6.get("status") == "SUPPRESSED":
                        AE.record("pb_split_alarm", _d6["episode"], _sa["fingerprint"], mode=mode)
                else:
                    log(f"5e split alarm: {_d6['reason']}")
        except Exception as e:
            log(f"5e split alarm failed: {type(e).__name__}: {e}")
        # ── [GAP-OBS] members whose recent bars are missing are trading on fabricated inputs ──
        # ★ REPORT ONLY. The training panel washes gaps exactly as inference does
        #   (build_wide_dl.py) and the trainer standardises in the same order with the same clip
        #   (wide_panel_dataset.py:97), so the frozen heads were FITTED on this convention.
        #   Excluding a gapped name here would create a train/serve inconsistency that does not
        #   exist today. The behavioural fix belongs to the next retrain, both sides at once.
        # ★ Episode-deduped on (symbol, count): a halt that persists pages ONCE, and a halt that
        #   GROWS pages again. A three-day outage must not page eighteen times.
        try:
            _fresh = ((_preds_st or {}).get("data_gaps_fresh_members") or {})
            _dead = ((_preds_st or {}).get("data_gaps_fresh_non_members") or {})
            # ★★★ TWO CLASSES, AND ONLY ONE OF THEM IS ABOUT US. Until 2026-07-31 this alarm
            #   fired on the union and told the reader "**它们仍持有权重**" — while the three names
            #   that actually triggered it (EOSUSDT/MATICUSDT/RNDRUSDT) were NON-members that
            #   member derivation had already excluded, each missing 24 of 24 fresh bars because
            #   they are delisted. **The alert was asserting a fact that was not true**, about
            #   names the system had handled correctly.
            #   The two cases carry the SAME NUMBER and OPPOSITE meanings: a member with fresh
            #   gaps is being weighted on fabricated extremes; a non-member with fresh gaps is a
            #   dead ticker not participating. Paging on the second teaches the reader to discount
            #   the first.
            if _dead:
                # ★ RECORDED, NOT PAGED. It is not nothing — a panel column that stopped printing
                #   is worth seeing — but it demands no action, and an alarm that demands none is
                #   how a channel gets muted.
                log(f"signal_data_gaps: {len(_dead)} NON-member name(s) with fresh gaps "
                    f"(excluded by member derivation, hold nothing): "
                    f"{', '.join(f'{s_}:{n}' for s_, n in sorted(_dead.items())[:8])}")
            if _fresh:
                _gf = [f"{sy}:{n}" for sy, n in sorted(_fresh.items())]
                _dg = AE.decide("signal_data_gaps", _gf, mode=mode)
                if _dg["alarm"]:
                    _txt = ", ".join(f"{sy} 缺 {n} 根" for sy, n in sorted(_fresh.items())[:8])
                    _rg = notifier.alarm(
                        "HIGH",
                        f"信号缺口: {len(_fresh)} 个**在册成员**最近 24h 有缺失 K 线 — {_txt}。"
                        f"缺失处被 nan_to_num 洗成 0 再标准化为 (0-mu)/sd; 在比值型通道上那是 "
                        f"clip 上限, 即模型能表示的最强读数。**它们仍持有权重** —— "
                        f"本条只报告, 不停机、不剔除(训练侧同约定, 单边剔除会制造不一致)。")
                    if _rg.get("delivered_offbox") or _rg.get("status") == "SUPPRESSED":
                        AE.record("signal_data_gaps", _dg["episode"], _gf, mode=mode)
                else:
                    log(f"signal_data_gaps: {_dg['reason']}")
        except Exception as e:
            log(f"gap observation alert failed: {type(e).__name__}: {e}")
        # ★★ THE §4-2 INVESTIGATION LEVEL SPEAKS FOR THE FIRST TIME (ruling 2026-07-29).
        # `DAY_LOSS_ALERT_PCT_OF_EQUITY = -2.68` has always been written into the condition's
        # detail as `investigate: True`, and NOTHING IN THE REPOSITORY EVER READ THAT FIELD —
        # not here, not in any report. Its own comment says operations "should expect three or
        # four a year", which was a claim about a channel that did not exist.
        # ⇒ **An alert tier whose alert has no consumer is not a lower rung; it is a comment.**
        #   Same defect in the leverage alert (`_lev_alert`), fixed in the same loop below.
        # ★ HIGH, NOT INFO, DELIBERATELY, and the text carries the tier. INFO is where a channel
        #   puts things it has decided not to act on; a day at -2.68% of EQUITY is 3-4x a year and
        #   is exactly the thing someone should look at. What makes it "alert only" is that it
        #   does NOT stop the book — that belongs in the WORDS, not in a severity nobody reads.
        try:
            _inv = []
            for _cname, _cond in (ev.get("conditions") or {}).items():
                if isinstance(_cond, dict) and _cond.get("investigate"):
                    _inv.append((_cname, _cond))
            if _inv and not tripped:
                # ★ THE REAL KEY IS `worst_day_pct_of_equity`. `worst_day_pct` does not exist
                #   on cond2, so every fingerprint fell through to '?' and two DIFFERENT
                #   investigate events would have deduped into one episode — the second one
                #   silently suppressed as "already alarmed". A dedup key that cannot vary is a
                #   mute button wearing an episode's name.
                # ★ 2026-09-06: cond2 的判据取值改为「最近一个已定价日」(recent_day_pct), 而
                #   `worst_day_pct_of_equity` 是全史最小值 —— 一旦出现过一个很差的日子, 它就不再变化。
                #   继续拿它当指纹, `investigate` 会按新的一天点亮而指纹恒定 ⇒ 第二次起被 dedup 静默吞掉,
                #   正是本行原注释所说的「不能变化的 dedup 键 = 披着 episode 外衣的静音键」。
                #   ⇒ 指纹优先取该条款【判据实际用的那个数】; 没有该键的条款(如 cond4b)回退原路径。
                _ifind = [f"{n}:{c.get('recent_day_pct', c.get('worst_day_pct_of_equity', c.get('actual_leverage', '?')))}"
                          for n, c in _inv]
                _di = AE.decide("watchdog_investigate", _ifind, mode=mode)
                if _di["alarm"]:
                    _body = "; ".join(
                        f"{n}: {c.get('investigate_note') or c.get('note') or '见记录'}"
                        for n, c in _inv)
                    _ri = notifier.alarm(
                        "HIGH",
                        f"调查档(INVESTIGATE-ONLY, 不停机) — {_body} | "
                        f"这一档预期一年响三四次, 响了不代表它坏了; 但在此之前它从未响过一次, "
                        f"因为没有任何代码读 `investigate` 字段。")
                    if _ri.get("delivered_offbox") or _ri.get("status") == "SUPPRESSED":
                        AE.record("watchdog_investigate", _di["episode"], _ifind, mode=mode)
                else:
                    log(f"watchdog investigate: {_di['reason']}")
        except Exception as e:
            log(f"investigate-tier alert failed: {type(e).__name__}: {e}")
        # ── [N1] the pages that never left the box get one more chance, once per anchor ────────
        # ★ Until 2026-07-31 an undelivered page was simply lost: the record was honest
        #   (`delivered_offbox=False`, body and sha preserved) and NOTHING ever tried again — so
        #   a trip page that failed to send meant the book had stopped and the operator would
        #   never learn it. The audit file already knows what we owe; it just had no reader.
        # ★ ONE PASS PER ANCHOR, never an in-process loop: the anchor cadence is the rate limiter,
        #   and a retry loop is what turns a refusal into a longer refusal (the -1003 lesson,
        #   arriving through a different door).
        try:
            import redeliver_alarms as _RD
            _rdo = _RD.run(notifier=notifier, log=log)
            if _rdo.get("still_failing"):
                log(f"alarm_redelivery: {_rdo['still_failing']} page(s) STILL undelivered — "
                    f"they stay owed and the next anchor tries again")
        except Exception as e:
            log(f"alarm redelivery failed: {type(e).__name__}: {e}")
        if ev.get("conditions_blind") and clock_started:
            notifier.alarm("HIGH",
                           f"止损条件本轮无输入(blind): {', '.join(ev['conditions_blind'])} — "
                           f"它们报的 triggered=False 只是'没得看', 不是'看过了没事'。")
        # ★★ DEGRADED IS A CLOCK-START PRECONDITION, NOT A PAGE (lead's ruling 3, 2026-07-28).
        # Its first draft was an alarm here, gated on `clock_started` — i.e. a property with no
        # consumer before the window and a page inside it. Both halves were wrong:
        #   · before the clock, a red that everyone expects trains the operator to ignore the
        #     channel, which is worse than no alarm at all (the same reasoning as the sleep guard);
        #   · and "is the mark producer keeping up" is not a per-anchor question, it is exactly
        #     the ONE question worth answering before the window opens — did B34's capacity fix
        #     actually raise coverage.
        # ⇒ It moved to ops/check_markout_readiness.py, wired as a step of
        #   ops/start_dryrun_clock.sh: quiet, and a hard precondition. It is deliberately NOT in
        #   the resume gate — a start gate that blocks is a decision not yet taken; a resume gate
        #   that blocks is a stop-loss that cannot be cleared until a measurement job catches up.
        _ = ev.get("conditions_degraded")           # consumed at the clock gate, not here
        if tripped:
            # The ladder already ran inside WD.run (halt -> flatten -> alert). This is the
            # anchor-level record of it, so a trip is visible in the run log too, not only in
            # the watchdog's own state — one more place the operator might actually look.
            log(f"watchdog TRIPPED: {json.dumps(ev, default=str, ensure_ascii=False)[:800]}")
            # ★ AND IT MUST LEAVE THE MACHINE. This block had a CRITICAL alarm for "the watchdog
            # could not EVALUATE" and none at all for "the watchdog actually TRIPPED" — an alarm
            # for the meta-failure, none for the main event. Measured 2026-07-26: a stop-loss
            # fired at 18:46:36, the book was flattened and reduce-only engaged, and the last
            # delivered notification was from 15:24. ALARM.log was written; nothing left the box.
            # A stop-loss whose notification nobody receives is a B3 by construction.
            # ★ [j] SEVERITY AND WORDING COME FROM THE LADDER, NOT FROM LITERALS. This call used
            # to pass a constant "CRITICAL" and a constant "书已平仓" — so on 2026-07-26 12:18:43Z
            # it paged "the book is flat" while the flatten had failed and 656.34 USDT was stuck.
            # One composition now serves this page and ALARM.log; see watchdog.trip_page.
            # ★ [j2] eval_detail carries THIS trip's own facts (evaluated_utc + per-day series)
            # into the page body — distinct trips can no longer compose an identical sha and get
            # swallowed by the denoiser as "repetition" (measured 2026-08-05 12:19Z: the re-trip
            # after an owner-override resume was RECORDED_NOT_PUSHED because its text was
            # byte-identical to the 00:18Z page).
            _pg = WD.trip_page(ev.get("degradation") or {}, ev.get("triggers", []),
                               eval_detail=ev)
            rcpt = notifier.alarm(_pg["severity"], _pg["message"])
            log(f"watchdog trip alarm receipt: {json.dumps(rcpt, default=str, ensure_ascii=False)[:300]}")
            # ★ AND IT IS PERSISTED BESIDE THE TRIP. The run log has it, but the watchdog's own
            # state.json carried only the ladder's local-write flag — so a later reconstruction
            # from state alone would say "delivery unknown", which in an audit is indistinguish-
            # able from "never delivered". The receipt is the only proof the alarm left the box.
            try:
                _rp = os.path.join(_paths["watchdog_dir"], "trip_receipt.json")
                json.dump({"tripped_at": ev.get("evaluated_utc"),
                           "triggers": ev.get("triggers"),
                           "receipt": rcpt,
                           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                          open(_rp, "w"), indent=1, default=str)
                log(f"trip receipt persisted: {_rp}")
            except Exception as _e:
                log(f"could not persist the trip receipt ({_e}) — the run log is now its only "
                    f"record, and state.json will read as 'delivery unknown'")
        elif ev.get("local_response"):
            # ★★★ EXE-01: A PROPORTIONAL LOCAL RESPONSE MUST LEAVE THE MACHINE TOO. It halted opening and flattened
            # named names; `tripped` is False on purpose (it is not a trip), which is exactly why the block above would
            # never page it — the W6(c) design text said "the anchor pages off-box from state.json's tripped_at" and no
            # code did. Same two properties as the trip page: the words and the severity come from the record
            # (`watchdog.local_response_page`), and the receipt is persisted beside the state.
            _lp = WD.local_response_page(ev.get("local_response") or {}, ev)
            _lrc = notifier.alarm(_lp["severity"], _lp["message"])
            log(f"watchdog LOCAL RESPONSE: names={_lp.get('names')} severity={_lp['severity']} "
                f"receipt={json.dumps(_lrc, default=str, ensure_ascii=False)[:300]}")
            try:
                _lrp = os.path.join(_paths["watchdog_dir"], "local_response_receipt.json")
                json.dump({"evaluated_utc": ev.get("evaluated_utc"), "names": _lp.get("names"),
                           "severity": _lp["severity"], "receipt": _lrc,
                           "proportional_response": ev.get("proportional_response"),
                           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                          open(_lrp, "w"), indent=1, default=str)
            except Exception as _e:
                log(f"could not persist the local response receipt ({_e}) — the run log is now its only record")
    except Exception as e:
        # A watchdog that cannot evaluate must SAY SO loudly. Swallowing this would recreate
        # exactly the failure it exists to prevent: protection that looks present and is not.
        log(f"watchdog FAILED to evaluate: {e}")
        notifier.alarm("CRITICAL", f"看门狗本轮无法评估 ({e}) — 止损保护本锚点缺席。"
                                   f"若持续, 用 ops/KILL.sh 停机。")

    # ── 7. dry-run ledger — independent reconciliation of schedule vs reality ───────────────
    # ★ Nothing was counting. The §2.5 gate is "30 scheduled calls, completion >=98%" — which at
    # n=30 means ZERO tolerance — and yesterday an anchor died on a permission error with NO
    # alarm at all: the user noticed the missing push, the system did not. A dead process does
    # not report that it died, so the completion figure cannot come from the runs themselves.
    try:
        # (ops/ is already on sys.path from the top of this file — see the note
        #  there; this line is kept as a no-op only because removing it would be a
        #  behaviour change to import PRECEDENCE, which is not what this fix is.)
        sys.path.insert(0, os.path.join(REPO, "ops"))
        import dryrun_ledger as DL
        # ★ the fallback is None, NOT a date. `.get(k, default)` returns None while the key exists
        # with a null value, so the old `"2026-07-26"` default was inert — but it was one deleted
        # config line away from re-arming the exact failure d4ee190 removed: a window that starts
        # because the calendar reached it rather than because someone decided it had.
        clock = json.load(open(os.path.join(REPO, "config", "book.json"))).get(
            "dryrun_clock_start")
        rep = DL.reconcile(clock)
        log(f"ledger: {rep['completed']}/{rep['expected']} completed "
            f"({rep['completion']:.1%}), day {rep['calendar_days_elapsed']}, gate={rep['gate']}")
        if rep["missed"]:
            # A miss is reported every anchor until the window rolls past it — not once. Unlike
            # a stale-signal episode (one state, alarm once), each miss is a permanent fact
            # about the gate: the operator must keep seeing that the count cannot reach 98%.
            notifier.alarm("HIGH", f"干跑对账: 缺失 {len(rep['missed'])} 次锚点 — "
                                   f"完成率 {rep['completion']:.1%} < 98%。"
                                   f"最近缺失: {', '.join(rep['missed'][-3:])}")
    except Exception as e:
        log(f"ledger FAILED: {e}")

    _signal.alarm(0)          # made it; disarm before a clean return
    # ── 8. artefact assertions — did the system leave the traces it should have? ────────────
    # ★ The 11 acceptance suites ask "is this component correct?" and were green through every
    # defect found today. This asks a question they structurally cannot: after the run, is the
    # trace actually on disk? Counts come from READING THE FILES, never from the writer's tally.
    try:
        # (ops/ is already on sys.path from the top of this file — see the note
        #  there; this line is kept as a no-op only because removing it would be a
        #  behaviour change to import PRECEDENCE, which is not what this fix is.)
        sys.path.insert(0, os.path.join(REPO, "ops"))
        import assert_anchor_artifacts as AAA
        AAA.run_and_report(rebalance_id=outA.get("rebalance_id"),
                           emitted=(outB or {}).get("rows_emitted"),
                           anchor_ts=outA.get("anchor_ts"),
                           notifier=notifier, log=log, mode=mode,
                           # passed from the bind result, not re-derived: this checker held its
                           # own copy of the path and read the wrong tree on the first TESTNET run
                           root=_paths["pilot_log"], wd_state=_paths["watchdog_dir"],
                           # the SAME fact the producer keys on, passed rather than re-derived:
                           # a rebalance happened iff a target vector was built.
                           rebalanced=bool(outA.get("rebalance_id")))
    except Exception as e:
        # this layer failing is itself a finding: it is the thing that watches the watchers
        log(f"artefact assertions FAILED to run: {e}")
        notifier.alarm("HIGH", f"产物断言层本轮无法运行 ({e}) — 无人在检查系统是否留下痕迹。")

    # ── 9. is the position-rank monitor (#55) running and reporting? ─────────────────────────
    # ★★ ALM-03 / W5 (FX-EXEC 2026-09-13). This step called `check_factor_health.run()`, which ssh-reads a research-box report whose
    #   producer was retired by user ruling on 2026-08-06 — so since then every anchor recorded "UNKNOWN" at INFO and nothing watched
    #   the traded book. The instrument that does is #55 on this box; this step now checks ITS evaluations ledger (local file, no ssh,
    #   no network) and pages only when that source is missing, stale, unreadable or self-contradicting — #55 pages its own levels.
    #   `check_factor_health` is RETIRED and no longer called from the anchor.
    # ★ The failure branch is HIGH, not the INFO of the old branch: that INFO existed because the old source was a RESEARCH box the
    #   live loop does not depend on (ruling 2026-08-06). This check reads a local file; if it cannot run, that is a defect on the
    #   live box, and the monitor's liveness goes unchecked this anchor.
    try:
        import check_rank_monitor_input as RMI
        RMI.run(notifier=notifier, log=log)
    except Exception as e:
        log(f"rank monitor input check FAILED to run: {e}")
        notifier.alarm("HIGH", f"持仓排序监控输入检查本轮无法运行 ({e}) — #55 是否在跑、是否写出评估, 本轮无人核对。")

    # ── 9b. is the funding-span table still what the venue says? ───────────────────────────
    # ★ A STALE SPAN DOES NOT RAISE — it smooths the wrong number of settlements for that symbol
    # and returns a plausible number. Measured 2026-07-26: 15 symbols we still mark 8h are 4h on
    # production. The data is a public endpoint we can reach every anchor, and until now nothing
    # looked at it — the same shape as the delisting check, where the fact was always available
    # and only the consumer was missing.
    try:
        import check_funding_span as CFS
        CFS.run(notifier=notifier, log=log)
    except Exception as e:
        log(f"funding span check FAILED to run: {e}")
        notifier.alarm("HIGH", f"funding span 对账本轮无法运行 ({e}) — 表是否过期无人检查。")

    # ── 9c. is the metrics code still the version the window was certified with? ───────────
    # ★ Every headline number comes from pilot_metrics.py, and each report already stamps its
    # hash — but a hash with nothing to compare it against answers no question: two reports from
    # different days with different hashes look exactly like two reports from different days.
    # The frozen record supplies the other side. It is not a promise not to change; it is what
    # makes a change VISIBLE AND DATABLE.
    try:
        import check_metrics_freeze as CMF
        CMF.run(notifier=notifier, log=log, clock_started=clock_started)
    except Exception as e:
        log(f"metrics freeze check FAILED to run: {e}")

    # ── 10. the machine must still be awake ─────────────────────────────────────────────────
    # ★ The guard is a launchd job holding a caffeinate assertion; it can die, be unloaded, or be
    # replaced by somebody else's assertion, and nothing downstream would notice — the first
    # symptom would be a missed anchor, i.e. a §2.5 failure discovered by absence. The CHEAP
    # reading (no sleep-log parse) runs here: it answers "is the guard held by our process right
    # now", which is the part that can change between anchors. It deliberately does NOT claim the
    # machine has not slept — `sleep_log_verified` is False and the start gate is what reads the
    # log. Only alarms once the clock is running: before that a red guard is expected, and an
    # alarm the operator is trained to ignore is worse than no alarm.
    # ★ THE SLEEP LOG IS NOW READ EVERY ANCHOR, over exactly the gap since the last check.
    # Before this, the per-anchor reading answered "is the guard held right now" and the window
    # could therefore DETECT a sleep (a completion goes missing) without being able to ATTRIBUTE
    # it — "one short" reads the same whether the machine slept, lost a lock race, or crashed.
    # With 30-of-30 and zero tolerance, a failed window has to be diagnosable at the time; the
    # evidence does not exist retroactively. Cost measured at 3.1s against a 1500s budget.
    # ⇒ It also UPGRADES the claim: `sleep_log_verified` goes False -> True, i.e. from "nothing
    # detectably wrong at this instant" to "the machine did not sleep during this interval".
    # Those are different strengths and they used to be printed identically.
    # Recording, not judging (per the ruling): the only alarm remains the pre-existing one —
    # clock started AND a sleep occurred while our guard was held, which says the guard does not
    # cover that cause.
    try:
        import check_nosleep as CNS
        _lb = CNS.since_last_check_h()
        _ns = CNS.report(lookback_h=_lb, read_log=True)
        _reasons = sorted({e["reason"] for e in (_ns.get("sleep_events") or [])
                           if isinstance(e, dict)})
        log(f"nosleep: ok={_ns['ok']} agent_pid={_ns['agent']['pid']} "
            f"guard_age_h={_ns['guard_age_h']} power={_ns['power_source']} "
            f"| interval={_lb:.1f}h log_verified={_ns['sleep_log_verified']} "
            f"slept_since_guard={_ns['n_sleep_since_guard']} "
            f"slept_before_guard={_ns['n_sleep_before_guard']}"
            f"{' reasons=' + str(_reasons) if _reasons else ''}"
            f" src={_ns.get('sleep_log_source')}")
        if not _ns["ok"] and clock_started:
            notifier.alarm("HIGH", f"防休眠守卫本轮不合格: {'; '.join(_ns['blocking'])[:220]} — "
                                   f"机器可能在下一个锚点前休眠, 那会直接打掉 §2.5 完成率。")
    except Exception as e:
        log(f"nosleep check FAILED to run: {e}")

    # ── alarm delivery: the numerator and the denominator ───────────────────────────────────
    # ★ 15 `self.alarm(...)` call sites and not one captured the receipt, while
    # telegram_notify.alarm() returns delivered_offbox/message_id. So a FAILED alarm was recorded
    # locally and read by nobody — "the stop-loss fired, the message never went out, and nobody
    # knew it never went out". One line here covers all of them.
    try:
        audit = notifier.audit_summary() if hasattr(notifier, "audit_summary") else None
        if audit:
            # ★ recorded_only is printed and NOT starred (2026-08-04): those rows are the denoising
            # policy working (episode repeats filed to the ledger on purpose). The ★ banner below is
            # reserved for what it was written for — attempted deliveries that did not leave the
            # box. Before this split the banner fired every anchor on deliberate record-only rows;
            # ledger audit found 0 FAILED rows ever, and the false banner cost an incident review.
            log(f"alarms: raised={audit.get('raised')} delivered_offbox={audit.get('delivered')}"
                f" recorded_only={audit.get('recorded_only', 0)}"
                f" undelivered={audit.get('undelivered')}")
            if audit.get("undelivered"):
                log(f"★ {audit['undelivered']} alarm(s) ATTEMPTED AND NEVER LEFT THIS MACHINE "
                    f"this run — local ALARM.log is not delivery. Run ops/redeliver_alarms.py.")
    except Exception as e:
        log(f"alarm audit failed: {e}")

    # ── B10: complete the +60s marks whose moment has passed ────────────────────────────────
    # ★ PLACED LAST, DELIBERATELY. It is the only step that can SLEEP on the rate budget
    # (aggTrades is weight 20 per fill), and nothing protective may queue behind a measurement.
    # If the anchor's hard cap fires during it, everything that matters has already run and the
    # marks stay pending for the next anchor — which is exactly the state this job is built to
    # tolerate, since a pending mark is a normal state and not an error.
    # ★★ AND IT NOW GETS A DEADLINE, BECAUSE IT NOW RUNS LONG ENOUGH TO MATTER. The comment above
    # says "if the anchor's hard cap fires during it, everything that matters has already run" —
    # true for THIS process, and false for the next one: the cap fires SIGALRM -> os._exit(3), and
    # the whole reason the cap exists is that a process which dies without releasing its lock
    # makes the NEXT anchor SKIP (§2.5 tolerates zero skips). At the old 150 weight-1-priced calls
    # this was ~25s and could not reach the cap; at the corrected weight-20 price and the capacity
    # this batch gives it, it can. So it is told how much of the process's life is left, minus a
    # margin, and stops on its own rather than being killed inside the one job that must not take
    # the successor down.
    try:
        import backfill_markout as BMK
        _left = max(0.0, _cap - (time.time() - _T_START) - 90.0)
        _bf = BMK.run(b, log=log, max_seconds=_left)
        if _bf.get("n_quarantined"):
            # ★ LED-01 (2026-09-13): one page for the run — a markout row refused by the fills write contract
            notifier.alarm("HIGH", f"fills 写入合同违例(markout 回填): {_bf['n_quarantined']} 行被拒入 fills.jsonl, "
                                   f"已隔离到 <日目录>/fills_quarantine.jsonl — 回填照常完成, 隔离行待人工核对")
        if _bf["n_pending"]:
            log(f"markout_backfill: pending={_bf['n_pending']} written={_bf['n_written']} "
                f"no_trade={_bf['n_no_trade']} requests={_bf.get('n_requests')} "
                f"budget_s={_left:.0f} stopped_by={_bf.get('stopped_by')}")
    except Exception as e:
        log(f"markout backfill FAILED to run: {e}")

    # ★★★ THE LOCK IS RELEASED HERE — BEFORE THE REPORTING TAIL (2026-08-01, demonstrated).
    # A rehearsal was piped into `tail -30` and then backgrounded; the reader stopped draining, the
    # 16 KB pipe filled, and the process BLOCKED ON A `print` — with the anchor already finished
    # (`rc=0` had been emitted) and the machine lock still held for five minutes. Everything below
    # is REPORTING: it touches no venue and writes no ledger row, so holding the lock across it
    # buys nothing and can cost a whole anchor. Production writes to files under launchd and never
    # meets this; every manual and rehearsal invocation can.
    # ★ THE TRADE-OFF, STATED: after this point a second anchor may start while this one is still
    #   writing its reports. That is the intended outcome — the second one does real work while
    #   this one only narrates — and it is strictly better than the alternative, which is a live
    #   anchor silently skipped because a terminal stopped reading.
    try:
        fcntl.flock(lock_f, fcntl.LOCK_UN)
        lock_f.close()
        log("lock released (anchor work complete; what follows is reporting only)")
    except Exception as _e:
        log(f"lock release failed ({type(_e).__name__}: {_e}) — it will be released at exit")

    # ── what WE spent, against the caps THEY publish ────────────────────────────────────────
    # ★ `RateBudget.stats` has been accumulated since the budget was written and read by NOTHING.
    # It is the one quantity that lets us say something provable about rate limiting: we cannot
    # establish "we will not be throttled" (that depends on the venue's production thresholds,
    # which they control), but we can establish exactly what WE emit per anchor — and that number,
    # set beside the published caps (2400 weight/min MAINNET; testnet publishes 6000 — the
    # authoritative figures are read from exchangeInfo, see venue_limits), is a conclusion reachable
    # unaided. A tracked-and-unread counter is the same shape as `alarms_raised` with no
    # `delivered`: an honest number pointing at nothing.
    try:
        import rate_budget as _RB
        from rate_budget import (BUDGET as _B, WEIGHT_PER_MIN as _WPM, ORDERS_PER_MIN as _OPM,
                                 REQUESTS_PER_MIN as _RPM)
        _st = dict(_B.stats)
        # ★ [①] peaks are logged beside the totals: the caps are PER MINUTE, so only the peak is
        # the comparable quantity — a whole-anchor total can neither establish nor exclude a breach.
        # ★ [T2] REQUESTS ARE REPORTED BESIDE WEIGHT AND ORDERS. At 12:00Z the weight peak sat
        # exactly on its cap while the ban cited a REQUEST limit — a dimension this line could not
        # show because nothing counted it. A budget line that omits a quota reads as a budget with
        # no pressure on it.
        # ★ OPS-03 C (2026-09-16): `weight` below is now the SLIDING 60 s peak, because the shaper became a
        #   sliding window (OPS-03 A). It used to be a FIXED window's running total, and reading "990/1000 = 99%"
        #   as headroom was wrong twice over: it was the limiter's own bookkeeping, not emission, and it was
        #   reached with waits=0. The comparable headroom figures are on the `venue_rate` line below: venue
        #   used/published. Both are printed so neither has to be inferred from the other.
        log(f"rate_budget: peak/min weight={_st.get('weight_peak_per_min')} (SLIDING 60s) "
            f"orders={_st.get('orders_peak_per_min')} "
            f"requests={_st.get('requests_peak_per_min')} | "
            f"weight_spent={_st.get('weight_spent')} "
            f"orders_spent={_st.get('orders_spent')} "
            f"requests_spent={_st.get('requests_spent')} "
            f"waits={_st.get('weight_waits', 0) + _st.get('order_waits', 0) + _st.get('request_waits', 0)} "
            f"wait_s={round(_st.get('wait_seconds', 0.0), 2)} "
            f"| self-imposed caps {_WPM} weight/min, {_OPM} orders/min, "
            f"{_RPM} requests/min "
            f"(the request cap is INFERRED from the -1003 text seen 2026-07-29T12:00Z, which "
            f"named 6000 requests without a window)")
        # ★★★ PER HOST, BECAUSE THE VENUE COUNTS PER IP x HOST (2026-08-01). The aggregate above
        # mixed the market-data host with the broker's, so on TESTNET it summed two venues and was
        # then compared against ONE venue's header — `6152 vs 1000` was never a measurement of a
        # single quantity. In LIVE the two hosts are the same string, so this line will show one
        # entry: that collapse IS the reason production is weaker than what we tested on, and it
        # should be visible rather than inferred.
        try:
            for _h, _hs in sorted(_RB.host_snapshots().items()):
                log(f"rate_budget[{_h}]: weight={_hs.get('weight_spent')} "
                    f"requests={_hs.get('requests_spent')} orders={_hs.get('orders_spent')} "
                    f"peak/min w={_hs.get('weight_peak_per_min')} "
                    f"r={_hs.get('requests_peak_per_min')} o={_hs.get('orders_peak_per_min')}")
        except Exception as _e:
            log(f"rate_budget[per-host]: UNAVAILABLE ({type(_e).__name__}: {str(_e)[:60]})")

        # ★★ THE PER-REQUEST TIMELINE (0C §3 plan A). Three questions were undecidable from
        # extrema alone — the cancel burst's real emission rate, each endpoint's true weight, and
        # whether the venue's ORDER-COUNT includes DELETE (both hypotheses predict the same 97,
        # because we kept a max). All three need the SEQUENCE. It sends no probe: every row is a
        # request we were making anyway plus a header we were already receiving.
        try:
            import state_root as _SR3
            _tl = _RB.TIMELINE.dump()
            _tdir = os.path.join(_SR3.paths_for(os.environ.get("LIVE_MODE", "DRY_RUN"))["root"],
                                 "rate_timeline")
            os.makedirs(_tdir, exist_ok=True)
            _rid = (outA.get("rebalance_id") if isinstance(outA, dict) else None) or "anchor"
            _tp = os.path.join(_tdir, f"{_rid}.json")
            with open(_tp, "w") as _tf:
                json.dump(_tl, _tf, default=str)
            log(f"rate_timeline: {_tl['n_rows']} rows (dropped {_tl['dropped']}) -> {_tp}")
        except Exception as _e:
            log(f"rate_timeline: NOT WRITTEN ({type(_e).__name__}: {str(_e)[:80]}) — the "
                f"instrument is absent for this anchor, which is not the same as a quiet anchor")

        # ★★ AND THE VENUE'S OWN COUNT, WHICH IS THE ONE THAT BANS. Until 2026-07-31 this line
        # reported only our private reconstruction, and it said "venue publishes 2400 weight" —
        # the MAINNET figure printed beside a TESTNET run, where the published limit is 6000.
        # On 07-30 we were banned mid-anchor with all three of our counters comfortably inside
        # both our caps and the venue's real limits, and the incident could not be attributed
        # from our records because the deciding quantity was never kept.
        # ★ `gap` is the measurement of OUT-OF-BAND traffic: our tally counts this process, the
        #   header counts this IP. Everything else that spends the same quota — a health check, a
        #   setup script, a probe — appears here and nowhere else.
        try:
            _v = BB.VENUE_RL
            _lim = BB.venue_limits(b)
            # ★★ THE REPORTED PEAK AND THE DECIDED-ON QUANTITY ARE NAMED SEPARATELY, because
            #    printing them side by side is what made "peak=4681, backstop_waits=0" read as
            #    "4681 never reached 4800" — when the backstop had never looked at 4681 at all.
            #    Two different quantities may not share one reading. (Today's rule, applied to a
            #    log line: the wording follows the data, and these are two data.)
            log(f"venue_rate: DECIDED_ON=window_high_water(aligned 1m) "
                f"peak_window_weight={_v.get('peak_window_weight')} "
                f"| REPORTED_ONLY peak_used_weight_1m={_v.get('peak_weight_1m')} "
                f"peak_order_count_1m={_v.get('peak_order_1m')} "
                f"(anchor-wide max; the backstop never compares this) "
                f"observed={_v.get('n_observed')} "
                f"backstop_waits={_v.get('waits', 0)} "
                f"backstop_wait_s={round(_v.get('wait_s', 0.0), 1)} "
                f"| HEADROOM used/published={_v.get('peak_weight_1m')}/{_lim.get('REQUEST_WEIGHT')}"
                f"{('=' + str(round(100.0 * float(_v.get('peak_weight_1m') or 0) / float(_lim.get('REQUEST_WEIGHT')), 1)) + '%') if _lim.get('REQUEST_WEIGHT') else ''} "
                f"| published REQUEST_WEIGHT={_lim.get('REQUEST_WEIGHT')}/1m "
                f"ORDERS={_lim.get('ORDERS_1M')}/1m (source: {_lim.get('_source')}) "
                f"| wait at {int(BB.VENUE_RL_WAIT_FRAC * 100)}% "
                f"| gap_vs_this_process={_v.get('peak_gap_vs_local')} "
                f"(CALIBER UNKNOWN — the banned IP is a CloudFront edge (130.176.187.x, AWS SG), "
                f"not our egress (103.252.201.68). Whether the venue counts that edge or a "
                f"forwarded source is UNVERIFIED, so this number's attribution is undetermined "
                f"and it feeds no decision)")
            _gap = int(_v.get("peak_gap_vs_local") or 0)
            _lw = _lim.get("REQUEST_WEIGHT")
            if _lw and _gap > 0.25 * _lw:
                # ★ USES THE MODULE-LEVEL `AE`. My first draft imported alarm_episode locally
                #   here — re-creating, one day later, the exact position-dependence that left the
                #   investigate tier dead from birth. tests_alert_tiers_live caught it on the
                #   first run, which is what that assertion is for: the rule outlives my memory
                #   of why it exists.
                _gf = [f"gap:{_gap}"]
                _dgp = AE.decide("venue_rate_gap", _gf, mode=mode)
                if _dgp["alarm"]:
                    _rgp = notifier.alarm(
                        "HIGH",
                        f"限流计数差值: 场所记的用量比本进程自己算的高 {_gap} 权重/分钟 "
                        f"(公布限额 {_lw}/分钟)。**差值的归属未确定** —— 封禁消息里的 IP 是 "
                        f"CloudFront 边缘节点(130.176.187.x, AWS 新加坡), 不是我们的出口 "
                        f"(103.252.201.68); 场所按那个边缘计数、还是按转发来的真实来源计数, "
                        f"我们没有证据。若按边缘计数, 这个差值里含其他 testnet 用户的流量。"
                        f"**本条只报告差值存在, 不断言它是我们的。**")
                    if _rgp.get("delivered_offbox") or _rgp.get("status") == "SUPPRESSED":
                        AE.record("venue_rate_gap", _dgp["episode"], _gf, mode=mode)
        except Exception as _e:
            log(f"venue_rate report failed: {type(_e).__name__}: {_e}")
    except Exception as e:
        log(f"rate budget report failed: {e}")

    try:
        plog.close()
    except Exception as e:
        log(f"pilot_log close failed: {e}")
    log("anchor done rc=0")
    return 0


if __name__ == "__main__":
    _rc = main()
    # 场外死人开关 (healthchecks.io, 用户提供 URL 2026-08-11 裁定): rc=0 ping 主 URL,
    # rc≠0 ping /fail(显式快报, 不等宽限期)。任何网络失败静默 —— ping 绝不允许改变 rc
    # 或抛出; 断网时本来就 ping 不出去, 死人开关恰由"无 ping"在场外触发。
    # ★ 只在 LIVE mode 发 ping, 判别式与 main() L162 逐字同源(不造第二棵 mode 树):
    #   电池的 live_dry_pass.sh:88 以脚本方式跑本文件(默认 DRY_RUN), 若不设门, 任何一次
    #   电池运行都会重置场外死人钟 —— 真锚坏掉时电池给出假绿(mode 污染家族, 实测抓获
    #   于部署当日 14:00Z 自己的电池运行)。
    if os.environ.get("LIVE_MODE", "DRY_RUN") == "LIVE":
        try:
            import urllib.request as _urlreq
            _hc = "https://hc-ping.com/dfb4810b-2786-40c5-afd8-8364534e650c"
            _urlreq.urlopen(_hc + ("" if _rc == 0 else "/fail"), timeout=10).read()
        except Exception:
            pass
    sys.exit(_rc)
