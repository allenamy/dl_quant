"""A skipped anchor cannot exit 0 in silence. [go-live]

*** MOCK ONLY: a temp lock, a temp state dir, a fake notifier. No venue, no credentials. ***

★★★ THE FAILURE THAT LOOKS LIKE SUCCESS

`run_anchor.main()` opens a machine-level lock with `LOCK_NB`; a contended lock raises
`BlockingIOError`, and the branch was:

    log("SKIP: previous anchor still holds the lock")
    return 0

launchd records a clean run. The exit code says success. **The anchor did not happen.** On the day
we go live, "the first live anchor silently did not occur, and every indicator says fine" is the
worst available outcome, because nothing distinguishes it from a good day.

`ops/dryrun_ledger` did read the line and count it as a non-completion — so it was not wholly
unconsumed. What was missing is the half that arrives on its own: **a ledger is read on purpose, a
page finds you.**

★ WHO ACTUALLY TAKES THIS BRANCH — measured, because the answer changed the fix.
NOT a second schedule: `ops/install_launchd.sh` has one LABEL and one plist path and installs by
`unload` then `load` of that same path, so two scheduled anchors cannot coexist (and installing
LIVE therefore ENDS the TESTNET schedule as a side effect, rather than as a decision). The real
contender is a HUMAN RUN — a rehearsal, a hand-run anchor, `ops/live_dry_pass.sh` — overlapping the
scheduled one, which is exactly what a go-live day is made of. [D] asserts the single-job property
rather than leaving it as a claim in this docstring.

★ WHAT IS DELIBERATELY NOT CHANGED: the exit code. Making a skip non-zero alters what launchd
believes happened, which is a change to a guard's consequence and belongs to a ruling, not to a
side effect of adding a page.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _d in ("live", "ops", "scheduler"):
    sys.path.insert(0, os.path.join(REPO, _d))

FAILS, N = [], [0]
_SKIPDIR = tempfile.mkdtemp(prefix="skiprec_")
SKIPS = os.path.join(_SKIPDIR, "anchor_skips.jsonl")
TMPS = [_SKIPDIR]


def check(name, cond, detail=""):
    N[0] += 1
    detail = "" if detail == "" else str(detail)
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}", flush=True)
    if not cond:
        FAILS.append(name)


def run_with_lock_held(mode="LIVE", src_override=None):
    """Hold the lock, then run run_anchor.py in a subprocess and capture what it did."""
    d = tempfile.mkdtemp(prefix="skip_")
    TMPS.append(d)
    lock = os.path.join(d, "anchor.lock")
    holder = open(lock, "w")
    fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ,
               LIVE_ANCHOR_LOCK=lock,
               # ★ the skip RECORD is redirected too. It is the artefact saying "an anchor did not
               #   run"; a test row in it is a fabricated non-event sitting where an operator
               #   looks. (Measured: the first run of this suite put two of them in the real file.)
               LIVE_ANCHOR_SKIPS=SKIPS,
               # ★★ 日志槽也必须重定向, 理由与上面那条【逐字相同】。上一版只堵住了 skip 记录,
               #    而操作员会看的地方有两处 —— `state/anchor_runs.log` 是另一处, 而且是出事时
               #    先看的那一处。实测: 本套件每跑一次就往生产日志写三行
                    #    "SKIP: previous anchor still holds the lock (mode=LIVE) — this anchor did NOT run",
               #    2026-08-06T08:44:17Z 的三行就是这么来的; 09:1xZ 复盘时它们让我一度判定
               #    "锁泄漏, 下一锚会不调仓" —— 一个由测试制造的假事故, 查了十几分钟才排除。
               LIVE_ANCHOR_LOG=os.path.join(d, "anchor_runs.log"),
               LIVE_MODE=mode,
               LIVE_ALARM_SUPPRESS="1",          # a test must never page a human
               LIVE_NOTIFY_AUDIT=os.path.join(d, "notify_audit.jsonl"))
    script = src_override or os.path.join(REPO, "scheduler", "run_anchor.py")
    p = subprocess.run(["/usr/bin/python3", script], capture_output=True, text=True,
                       env=env, timeout=120)
    holder.close()
    return p, d


# ★★ THE EPISODE RECORD IS CLEARED FIRST, AND THE ASYMMETRY IS THE REASON IT MAY BE.
#    `alarm_episode` keys its state on the MODE's root, and there is no env override — so this
#    suite's first run left `state/live/alarm_episodes/anchor_skip.json` behind, and the second
#    run then measured "no page" and reported it as a FAILURE of the page. (Order-dependence on
#    production state, which is the same family as the skip record and the ban file.)
#    ⇒ Clearing an episode fails SAFE — the only consequence is that the next occurrence pages
#      again. That is the opposite of the ban file, where clearing would UNBAN us, and it is why
#      one may be removed by a test and the other may not.
_EPISODE = os.path.join(REPO, "state", "live", "alarm_episodes", "anchor_skip.json")


def _clear_episode():
    try:
        if os.path.exists(_EPISODE):
            os.remove(_EPISODE)
    except Exception:
        pass


_clear_episode()

# ══ [A] the skip is loud, and it names the book it skipped ═════════════════════════════════════
print("[A] a contended lock: what the operator is left with")
# ★ 基线必须在【第一个子进程之前】取, 否则它测的是"最后一次运行之后没再增长", 而不是
#   "本套件一个字都没写进去" —— 那是两条不同的断言, 后者才是我们要的。
_PL = os.path.join(REPO, "state", "anchor_runs.log")
_PROD_BEFORE = os.path.getsize(_PL) if os.path.exists(_PL) else 0

_p, _d = run_with_lock_held("LIVE")
check("★★ the process exits 0 — UNCHANGED on purpose; changing what launchd believes happened is "
      "a ruling, not a side effect of adding a page", _p.returncode == 0, _p.returncode)
_out = _p.stdout + _p.stderr
check("★★★ the log line names the MODE it skipped — the lock is opened before `SR.bind(mode)`, so "
      "this branch used to know nothing about which book it was abandoning, and 'an anchor was "
      "skipped' is a different sentence from 'the LIVE anchor was skipped'",
      "SKIP:" in _out and "mode=LIVE" in _out,
      [l for l in _out.splitlines() if "SKIP" in l][:1])
check("★★ and it says plainly that the anchor did NOT run, rather than only that a lock was held",
      "did NOT run" in _out or "did not run" in _out.lower())

_rows = []
if os.path.exists(SKIPS):
    _rows = [json.loads(l) for l in open(SKIPS) if l.strip()]
check("★★★ a DURABLE record exists outside the run log — the exit code is 0, so this file is the "
      "artefact that says the run was not a success",
      bool(_rows) and _rows[-1]["mode"] == "LIVE" and "not one" in _rows[-1]["meaning"],
      _rows[-1] if _rows else None)

# ★★★ 证明【重定向真的把字写到了别处】—— 改"往哪写"而不断言"没往那写", 等于没改。
#     这条断言存在的理由是它对应的缺陷已经发生过: 本套件此前把三行 SKIP 写进了生产
#     `state/anchor_runs.log`(2026-08-06T08:44:17Z), 而那三行在复盘时被读成了一次真实的锁泄漏。
_PRODLOG = os.path.join(REPO, "state", "anchor_runs.log")
_prod_now = os.path.getsize(_PRODLOG) if os.path.exists(_PRODLOG) else 0
check("★★★ 生产 anchor_runs.log 未被本套件写入(重定向生效, 不是只是设了变量)",
      _prod_now == _PROD_BEFORE,
      f"before={_PROD_BEFORE} now={_prod_now} — 若增长, 说明 run_anchor 的 RUNLOG 没有读 "
      f"LIVE_ANCHOR_LOG, 本套件又在生产日志里制造假事故")
check("★★ 而重定向到的那份【确实】收到了 SKIP 行(否则上一条会因为'哪都没写'而假绿)",
      any("SKIP" in open(os.path.join(_dd, "anchor_runs.log")).read()
          for _dd in TMPS if os.path.exists(os.path.join(_dd, "anchor_runs.log"))),
      "这是上一条的配对: 一个把日志写进 /dev/null 的实现会让上一条通过")

_audit = os.path.join(_d, "notify_audit.jsonl")
_alarms = []
if os.path.exists(_audit):
    _alarms = [json.loads(l) for l in open(_audit) if l.strip()]
check("★★★ AND A PAGE IS ATTEMPTED — a ledger is read on purpose, a page finds you. Suppressed "
      "here because a test must not reach a human, but the attempt is audited either way",
      any(a.get("severity") == "HIGH" and "锚点被跳过" in str(a.get("message"))
          for a in _alarms),
      [(a.get("severity"), a.get("status")) for a in _alarms][:3])
check("★★ the page states the exit code is still 0, so the reader is not left to discover that "
      "the indicators disagree with reality on their own",
      any("退出码仍是 0" in str(a.get("message")) for a in _alarms))

# ══ [B] the page is de-duplicated, so a stuck lock does not become a siren ═════════════════════
print("\n[B] a standing condition pages once")
_p2, _d2 = run_with_lock_held("LIVE")
_a2 = [json.loads(l) for l in open(os.path.join(_d2, "notify_audit.jsonl"))
       if l.strip()] if os.path.exists(os.path.join(_d2, "notify_audit.jsonl")) else []
check("★★ the second identical skip does not page again (episode de-dup) — an alarm that repeats "
      "on a timer is how a channel gets muted, which is the one channel a stop-loss needs",
      not any("锚点被跳过" in str(a.get("message")) for a in _a2),
      [(a.get("severity"), a.get("status")) for a in _a2][:3])
check("★★ but the durable record still grows — suppression removes the PAGE, never the finding",
      len([json.loads(l) for l in open(SKIPS) if l.strip()]) > len(_rows))

# ══ [C] the ledger half still works ════════════════════════════════════════════════════════════
print("\n[C] the consumer that already existed is not disturbed")
import dryrun_ledger as DL                                                   # noqa: E402
_dl_src = open(os.path.join(REPO, "ops", "dryrun_ledger.py")).read()
check("★★ dryrun_ledger still counts a SKIP as a non-completion — the line's prefix is unchanged, "
      "so widening the message did not silently drop its existing reader",
      'msg.startswith("SKIP:")' in _dl_src and '"LOCK_SKIP"' in _dl_src)

# ══ [D] the premise that was WRONG, asserted so it cannot be re-assumed ════════════════════════
print("\n[D] two scheduled anchors cannot coexist — which is why no preflight guards that")
_inst = open(os.path.join(REPO, "ops", "install_launchd.sh")).read()
check("★★★ there is exactly ONE label and ONE plist path, and installing unloads then loads THAT "
      "path — so installing LIVE REPLACES the TESTNET job rather than joining it. The 'two "
      "schedules fight over the lock' scenario is structurally impossible, and a preflight "
      "refusing to install while the other is present would match nothing — indistinguishable "
      "from a guard confirming safety",
      _inst.count('LABEL="com.dlquant.live.anchor"') == 1
      and _inst.count('PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"') == 1
      and 'launchctl unload "$PLIST"' in _inst and 'launchctl load "$PLIST"' in _inst)
check("★★★ what IS reachable is checked instead: after install, EXACTLY ONE anchor job must be "
      "loaded — a hand-added plist or a stale label from a rename is the way a second one can "
      "appear, and nothing checked the count",
      '-ne 1' in _inst and "exactly ONE loaded anchor job" in _inst)
check("★★ and the installer says out loud that this ENDS the other schedule — the operator should "
      "watch the parallel control stop, not believe it is still running",
      "ENDS the TESTNET schedule" in _inst)

# ══ [E2] the boundary warning: a mechanism, not two people's memory ════════════════════════════
print("\n[E2] a manual run started next to a scheduled anchor is WARNED")
import book_config as BC                                                     # noqa: E402
_SLOT = 1785585600.0                                                          # 2026-08-01 12:00Z
check("★★ the slot the window is measured against is the SCHEDULE's own, not a second copy",
      BC.collision_window(_SLOT)["nominal_utc"].endswith("12:00Z"),
      BC.collision_window(_SLOT)["nominal_utc"])
# ★ 2026-08-22: the half-width is one anchor lifetime = config anchor_max_seconds (1500s -> 25 min until the
#   external-book wait raised it to 3000s -> 50 min). DERIVED here too — pinning 25 was a second copy.
_HALF = float(json.load(open(os.path.join(REPO, "config", "book.json"))).get("anchor_max_seconds", 1500)) / 60.0
_in = BC.collision_window(_SLOT - 300)
_out = BC.collision_window(_SLOT + (_HALF + 1) * 60)
check("★★★ 5 min BEFORE the slot contends — a manual run started then may still hold the lock "
      "when the scheduled anchor fires, and the SCHEDULED one takes the silent SKIP",
      _in["would_contend"] is True and "SCHEDULED anchor" in _in["who_loses"], _in["who_loses"])
check(f"★★ {_HALF + 1:.0f} min after it does not — the band is one anchor lifetime (config anchor_max_seconds), "
      "so it closes when the contender can no longer be holding the lock", _out["would_contend"] is False)
check("★★★ the half-width is DERIVED from config/book.json's anchor_max_seconds, not a second "
      "number invented about the same physics — the ask was ±15, the honest figure is one anchor "
      "lifetime (±25 at 1500s; ±50 since the external-book wait raised the cap to 3000s), and "
      "being wrong in the NARROW direction is what costs an anchor",
      abs(_in["half_width_min"] - _HALF) < 1e-9
      and "anchor_max_seconds" in _in["half_width_source"], _in["half_width_source"])
check("★★ outside the band there is no warning at all — a warning that always fires is furniture",
      BC.collision_warning(_SLOT + 60 * 60) is None)
_wtxt = BC.collision_warning(_SLOT - 300)
check("★★ and the warning names which side is expected to lose and why it is not a refusal",
      "Expected loser" in _wtxt and "Not refused" in _wtxt)
_ra = open(os.path.join(REPO, "scheduler", "run_anchor.py")).read()
check("★★★ the anchor warns only when a HUMAN started it (isatty) — launchd has no terminal and "
      "the battery runs it through a pipe, so neither is warned; a warning nobody can act on is "
      "noise that teaches the reader to skip the block",
      "sys.stdin.isatty()" in _ra and "collision_warning()" in _ra)
check("★★ the rehearsal — the commonest contender, because it runs a full anchor — warns too",
      "collision_warning()" in open(os.path.join(REPO, "ops", "live_dry_pass.sh")).read())


# ══ [E3] the lock does not outlive the work ════════════════════════════════════════════════════
print("\n[E3] a blocked stdout must not hold the lock")
_ra_src = open(os.path.join(REPO, "scheduler", "run_anchor.py")).read()
check("★★★ the lock is released BEFORE the reporting tail — a rehearsal piped into a reader that "
      "stopped draining blocked on a `print` with the anchor already finished, holding the lock "
      "for five minutes. Everything after the release touches no venue and writes no ledger row",
      "fcntl.flock(lock_f, fcntl.LOCK_UN)" in _ra_src
      and _ra_src.index("fcntl.flock(lock_f, fcntl.LOCK_UN)")
      < _ra_src.index("import rate_budget as _RB"))
check("★★ the release is ANNOUNCED, so 'the lock is free' is readable rather than inferred from "
      "the absence of contention", "lock released (anchor work complete" in _ra_src)
check("★★ and a failure to release says so rather than passing silently — the process still exits "
      "eventually, but the operator should know which of the two freed it",
      "it will be released at exit" in _ra_src)
# behavioural: after the release point the lock really is takeable while the process still runs
_tmpd = tempfile.mkdtemp(prefix="lockrel_")
TMPS.append(_tmpd)
_lockp = os.path.join(_tmpd, "anchor.lock")
_probe = subprocess.run(
    ["/usr/bin/python3", "-c",
     "import fcntl, os, sys\n"
     f"f = open({_lockp!r}, 'w')\n"
     "fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
     "fcntl.flock(f, fcntl.LOCK_UN)\n"
     "g = open(f.name, 'w')\n"
     "fcntl.flock(g, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
     "print('retakeable')\n"],
    capture_output=True, text=True, timeout=30)
check("★★ LOCK_UN really frees an flock in this environment — the mechanism the fix rests on, "
      "measured rather than assumed", "retakeable" in _probe.stdout, _probe.stderr[-120:])


# ══ [E] red capability ═════════════════════════════════════════════════════════════════════════
print("\n[E] red capability — put the silence back")
RA_PATH = os.path.join(REPO, "scheduler", "run_anchor.py")
RA_SRC = open(RA_PATH).read()
_A = '        _skip_mode = os.environ.get("LIVE_MODE", "DRY_RUN")'
_B = '        return 0\n\n    mode = os.environ.get("LIVE_MODE", "DRY_RUN")'
check("M1 markers each appear exactly once", RA_SRC.count(_A) == 1 and RA_SRC.count(_B) == 1,
      (RA_SRC.count(_A), RA_SRC.count(_B)))
if RA_SRC.count(_A) == 1 and RA_SRC.count(_B) == 1:
    _find = RA_SRC[RA_SRC.index(_A):RA_SRC.index(_B) + len('        return 0')]
    _mut = RA_SRC.replace(_find,
                          '        log("SKIP: previous anchor still holds the lock")\n'
                          '        return 0', 1)
    _mp = os.path.join(tempfile.mkdtemp(prefix="mut_ra_"), "run_anchor.py")
    TMPS.append(os.path.dirname(_mp))
    # ★ the mutant must live INSIDE scheduler/ or its sys.path bootstrap resolves elsewhere
    _mp = os.path.join(REPO, "scheduler", "_mutant_run_anchor.py")
    open(_mp, "w").write(_mut)
    try:
        _before = len([l for l in open(SKIPS) if l.strip()])
        _pm, _dm = run_with_lock_held("LIVE", src_override=_mp)
        _after = len([l for l in open(SKIPS) if l.strip()])
        _am = os.path.join(_dm, "notify_audit.jsonl")
        _alm = [json.loads(l) for l in open(_am) if l.strip()] if os.path.exists(_am) else []
    finally:
        os.remove(_mp)
    check("★★★ M1 restore the one-line silent skip => no durable record, no page, exit 0. That is "
          "the state the repo was in this morning, and [A] goes red",
          _pm.returncode == 0 and _after == _before
          and not any("锚点被跳过" in str(a.get("message")) for a in _alm),
          f"rows {_before}->{_after}, alarms {len(_alm)}")

_clear_episode()          # leave no test-written episode row in the LIVE tree
for t in TMPS:
    shutil.rmtree(t, ignore_errors=True)

print(f"\n{N[0] - len(FAILS)}/{N[0]} passed")
if FAILS:
    print("FAILED: " + "; ".join(FAILS))
sys.exit(1 if FAILS else 0)
