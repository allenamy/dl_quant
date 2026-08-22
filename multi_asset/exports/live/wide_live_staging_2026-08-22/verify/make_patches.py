#!/usr/bin/python3
"""Regenerate the staged live-repo files from the live repo's ORIGINALS + the hunks below.

★ Why a generator and not hand-edited copies: the patch must be re-derivable on a newer base
  (the live repo moves every day). Every hunk is applied by EXACT-MATCH with a uniqueness
  assertion — if the base drifted under a hunk, this script refuses instead of silently
  producing a file that merges two versions.

Reads  (read-only): $LIVE_REPO (default ~/dl_quant_live) and ~/wide_shadow/shadow_loop.py
Writes: <staging>/live_repo/... full copies + *.diff beside them; <staging>/shadow/shadow_loop_v2.py
Never touches the live repo or the running shadow.
"""
import difflib
import hashlib
import json
import os
import subprocess
import sys

LIVE = os.environ.get("LIVE_REPO", os.path.expanduser("~/dl_quant_live"))
SHADOW = os.path.expanduser("~/wide_shadow")
STG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(STG, "live_repo")
BASE_COMMIT_EXPECTED = "cf3fd9fa03ee78239f0893e2441eb56c9e7a6245"   # batch-2 base (batch-1 hunks applied there as cf3fd9f); batch-1 base was ab569b8
BASE_BATCH1 = "ab569b8babf49217f090260c376609750dbc6239"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read(rel, root=LIVE):
    return open(os.path.join(root, rel), encoding="utf-8").read()


def write(rel, text, root=OUT):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)
    return p


ALREADY = []


def apply_hunk(text, old, new, label, sentinel=None):
    """Exact-match apply. Returns (text, applied_now). A hunk whose NEW text (or its `sentinel`, for
    hunks whose new text is re-indented by a later step) is already present and whose OLD text is
    gone is 'already applied on this base' (the live repo moved past batch 1) and is skipped — so one
    generator serves every base; anything else is a refusal, never a guess."""
    # ★ NEW first: an INSERTION hunk keeps its old anchor line inside the new text, so on an
    #   already-applied base `old` still matches once — checking `old` first would apply it twice.
    if text.count(new) == 1 or (sentinel and text.count(sentinel) == 1):
        ALREADY.append(label)
        return text, False
    n = text.count(old)
    if n == 1:
        return text.replace(old, new, 1), True
    raise SystemExit(f"✗ hunk {label}: anchor text matched {n} times (need exactly 1; new-text count "
                     f"{text.count(new)})")


def replace_once(text, old, new, label):
    return apply_hunk(text, old, new, label)[0]


def indent_block(text, start_marker, end_marker, label, spaces=4):
    """Indent every line from the line containing start_marker through the line containing
    end_marker (inclusive). Both markers must be unique."""
    for m in (start_marker, end_marker):
        if text.count(m) != 1:
            raise SystemExit(f"✗ block {label}: marker matched {text.count(m)} times: {m[:60]!r}")
    lines = text.split("\n")
    i0 = next(i for i, l in enumerate(lines) if start_marker in l)
    i1 = next(i for i, l in enumerate(lines) if end_marker in l)
    if i1 < i0:
        raise SystemExit(f"✗ block {label}: end before start")
    pad = " " * spaces
    for i in range(i0, i1 + 1):
        if lines[i].strip():
            lines[i] = pad + lines[i]
    return "\n".join(lines), (i0, i1)


def udiff(a_text, b_text, rel):
    return "".join(difflib.unified_diff(a_text.splitlines(True), b_text.splitlines(True),
                                        fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3))


UNCHANGED = []


def write_diff(rel, a_text, b_text, name=None):
    """Write <name>.diff vs the CURRENT live base; if the staged file equals the base (the hunks were
    applied there already), keep the batch-1 diff file in place and record it — an empty diff would
    overwrite the review artefact with nothing."""
    name = name or (rel + ".diff")
    d = udiff(a_text, b_text, rel)
    if not d:
        UNCHANGED.append(rel)
        return
    write(name, d)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# 1. scheduler/anchor_loop.py
# ════════════════════════════════════════════════════════════════════════════════════════════════
AL_REL = "scheduler/anchor_loop.py"
al = read(AL_REL)
al0 = al

# H1 — import the adapter beside per_name_stop (same style, same noqa).
al = replace_once(al,
    "import per_name_stop as PNS   # noqa: E402  逐名止损条款 cf40ea21(2026-08-20 用户裁定全面启用)\n",
    "import per_name_stop as PNS   # noqa: E402  逐名止损条款 cf40ea21(2026-08-20 用户裁定全面启用)\n"
    "import external_book as EXT   # noqa: E402  外部书适配器(DESIGN_wide_live_deployment_2026-08-22 §1)\n",
    "H1 import")

# H1b — a policy constant for the external dust alarm, beside the other policy fractions.
al = replace_once(al,
    "RESHAPE_RESIDUAL_ALARM_FRAC = 0.02\n",
    "RESHAPE_RESIDUAL_ALARM_FRAC = 0.02\n"
    "# share of an EXTERNAL book's gross withheld by the 2x-min-notional eligibility filter above which\n"
    "# the breadth loss is a finding. ★ A POLICY NUMBER, same reasoning as min_gross_usdt's '排除 ≤10%':\n"
    "# measured on the 2026-08-22 00:00Z shadow weights at NAV 15.4k x 1.0 the filter withholds 6.2% of\n"
    "# gross (195 tail names); at 2.0x 1.7%. Recorded every anchor either way; paged only above this.\n"
    "EXT_DUST_ALARM_FRAC = 0.10\n",
    "H1b constant")

# H2 — resolve the book source ONCE at the top of run_anchor; INVALID blocks; external waits.
al = replace_once(al,
    '        out: Dict[str, Any] = {"anchor_wall_ts": now}\n'
    "        # ── §2.5.9 rehearsal gate, evaluated ONCE and EARLY ──────────────────────────────────\n",
    '        out: Dict[str, Any] = {"anchor_wall_ts": now}\n'
    "        # ── BOOK SOURCE (DESIGN_wide_live_deployment_2026-08-22 §1): internal (today) | external ─\n"
    "        # ★ Resolved ONCE, here, before any state is read. INVALID (a typo, a malformed block, a\n"
    "        #   gross_mult above the §4-4b leverage policy) BLOCKS the anchor outright: a book source\n"
    "        #   that cannot be named must not pick a book — not the retired one, not the new one.\n"
    "        # ★ `now_sched` keeps the ENTRY time for the off-schedule gate: in external mode this\n"
    "        #   process deliberately idles until the producer's slot (N+anchor_offset_min) before it\n"
    "        #   reads state or acts; it is still the scheduled run, and the ledger keys on process\n"
    "        #   START for the same fact. Internal mode: now_sched == now, byte for byte.\n"
    "        try:\n"
    "            _book_cfg = BC.load()\n"
    "        except Exception:                        # noqa: BLE001 — unreadable config = unknown source\n"
    "            _book_cfg = None\n"
    "        _ext_cfg = EXT.config(_book_cfg)\n"
    '        out["book_source"] = _ext_cfg["source"]\n'
    '        if _ext_cfg["source"] == "INVALID":\n'
    '            out["action"] = "BLOCKED_CONFIG"\n'
    '            out["note"] = f"book_source config invalid: {_ext_cfg[\'error\']} — no orders of any kind"\n'
    '            self.alarm("CRITICAL", f"book_source 配置无效: {_ext_cfg[\'error\']} — 本锚不交易(既不读外部书, "\n'
    '                                   f"也不回退在役引擎)。修 config/book.json 后下锚生效。")\n'
    "            return out\n"
    "        now_sched = now\n"
    '        if _ext_cfg["source"] == "external":\n'
    "            _pc = EXT.pns_profile_consistent(_book_cfg)\n"
    '            if not _pc["ok"]:\n'
    '                out["pns_profile_inconsistent"] = _pc["why"]\n'
    '                self.alarm("HIGH", f"外部书与逐名止损 profile 不一致: {_pc[\'why\']} — 条款仍按当前 profile 运行")\n'
    '            if getattr(self.broker, "mode", "DRY_RUN") != "DRY_RUN":\n'
    '                out["external_wait"] = EXT.wait_for_slot(_ext_cfg, now)\n'
    '                if out["external_wait"].get("slept_s"):\n'
    "                    now = time.time()\n"
    "        # ── §2.5.9 rehearsal gate, evaluated ONCE and EARLY ──────────────────────────────────\n",
    "H2 book source + wait")

# H3 — the off-schedule gate is judged at ENTRY (identical to today in internal mode).
al = replace_once(al,
    "        try:\n"
    "            sched = BC.schedule_check(now)\n"
    "        except Exception as e:\n",
    "        try:\n"
    "            sched = BC.schedule_check(now_sched)\n"
    "        except Exception as e:\n",
    "H3 schedule at entry")

# H4 — the external file is the signal: its age feeds the SAME ladder; a failed read never trades.
al = replace_once(al,
    "        # 0/3 — freshness decides the shape of this anchor before anything is priced\n"
    "        preds = _load(PREDS_PATH, None)\n"
    "        age = signal_age_anchors(preds, now)\n"
    "        action = staleness_action(age)\n"
    '        out["signal_age_anchors"] = round(age, 2) if age != float("inf") else "inf"\n'
    '        out["action"] = action\n',
    "        # 0/3 — freshness decides the shape of this anchor before anything is priced\n"
    "        preds = _load(PREDS_PATH, None)\n"
    "        ext = None\n"
    '        if _ext_cfg["source"] == "external":\n'
    "            # ★ THE EXTERNAL FILE IS THE SIGNAL. The preds file is not consulted for freshness;\n"
    "            #   the ladder's AGE comes from the newest USABLE external target — this file if it\n"
    "            #   verified, else the last good one — so the pre-registered rungs apply unchanged\n"
    "            #   (HOLD first, DERISK ≥24h, FLATTEN ≥48h; `on_unavailable: \"hold\"` pins HOLD).\n"
    "            #   A failed read NEVER trades and NEVER falls back to the internal composer.\n"
    "            ext = EXT.read_target(_ext_cfg, now=now,\n"
    '                                  poll=(getattr(self.broker, "mode", "DRY_RUN") != "DRY_RUN"\n'
    '                                        and os.environ.get("LIVE_EXTERNAL_WAIT", "1") != "0"))\n'
    "            _agei = EXT.age_anchors(ext, _ext_cfg, state, now, ANCHOR_S)\n"
    '            age = _agei["age_anchors"]\n'
    '            out["external_book"] = EXT.record(ext, {"age_ref": _agei})\n'
    '            if ext["ok"]:\n'
    '                state["external_last_good_anchor_ts"] = int(ext["anchor_ts"])\n'
    "        else:\n"
    "            age = signal_age_anchors(preds, now)\n"
    "        action = staleness_action(age)\n"
    '        if ext is not None and not ext["ok"]:\n'
    "            # a failed read can never TRADE; `on_unavailable: hold` (config) or an UNKNOWN age (no\n"
    "            # verified target ever seen — cold start / state reset) can never ESCALATE either: an\n"
    "            # irreversible cut on missing information is the one thing worse than holding.\n"
    '            if action == "TRADE" or _ext_cfg["on_unavailable"] == "hold" or age == float("inf"):\n'
    '                action = "HOLD"\n'
    '            self.alarm("HIGH", EXT.unavailable_text(ext, action))\n'
    '        out["signal_age_anchors"] = round(age, 2) if age != float("inf") else "inf"\n'
    '        out["action"] = action\n',
    "H4 external read + ladder age")

# H5 — hand the verified external book to _trade (None in internal mode).
al = replace_once(al,
    "            out.update(self._trade(preds, state, now,\n"
    '                                   rehearsal=bool((out.get("_rehearsal") or {}).get("enabled"))))\n',
    "            out.update(self._trade(preds, state, now,\n"
    '                                   rehearsal=bool((out.get("_rehearsal") or {}).get("enabled")),\n'
    "                                   external=ext))\n",
    "H5 pass external")

# H6 — _size_book accepts the external leverage (gross_mult) and says where it came from.
al = replace_once(al,
    "    def _size_book(self) -> Dict[str, Any]:\n",
    "    def _size_book(self, target_leverage=None, leverage_source=None) -> Dict[str, Any]:\n",
    "H6a size_book signature")
al = replace_once(al,
    '        cfg = _load(os.path.join(_REPO, "config", "book.json"), {}) or {}\n'
    '        tgt_lev = float(cfg.get("target_leverage") or 2.0)\n',
    '        cfg = _load(os.path.join(_REPO, "config", "book.json"), {}) or {}\n'
    "        # ★ external book: the leverage IS `external_book.gross_mult` (design §1 target_gross =\n"
    "        #   NAV x gross_mult). Same arithmetic, same dead zone, same floor — only the number's\n"
    "        #   origin differs, and it is stamped so a row can say which policy sized it.\n"
    '        tgt_lev = (float(cfg.get("target_leverage") or 2.0) if target_leverage is None\n'
    "                   else float(target_leverage))\n"
    '        lev_src = leverage_source or "config/book.json target_leverage"\n',
    "H6b size_book leverage")
al = replace_once(al,
    '            return {"nav": None, "target_leverage": tgt_lev, "actual_leverage": None,\n',
    '            return {"nav": None, "target_leverage": tgt_lev, "leverage_source": lev_src,\n'
    '                    "actual_leverage": None,\n',
    "H6c blind branch stamp")
al = replace_once(al,
    '        out = {"nav": nav, "target_leverage": tgt_lev, "actual_leverage": actual,\n',
    '        out = {"nav": nav, "target_leverage": tgt_lev, "leverage_source": lev_src,\n'
    '               "actual_leverage": actual,\n',
    "H6d normal branch stamp")

# H7 — _trade: signature + the external preamble; the four DL-preds gates become `else:`.
al = replace_once(al,
    "    def _trade(self, preds: Dict[str, Any], state: Dict[str, Any], now: float,\n"
    "               rehearsal: bool = False) -> Dict[str, Any]:\n",
    "    def _trade(self, preds: Dict[str, Any], state: Dict[str, Any], now: float,\n"
    "               rehearsal: bool = False,\n"
    "               external: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n",
    "H7a _trade signature")
al, _did7 = apply_hunk(al,
    "        # ── caliber stamp assertion (audit ②): the split-path guarantee must be a MECHANISM,\n"
    "        # not a convention. preds declare their calibers; we assert against config; mismatch\n"
    "        # BLOCKS the anchor. Closes the chain config -> stamp -> consumption, the same shape\n"
    "        # as the protocol's registry -> declaration -> observation chain.\n"
    '        expected = _load(os.path.join(_REPO, "config", "book.json"), {}).get("factor_versions")\n',
    "        # ── EXTERNAL BOOK (DESIGN_wide_live_deployment_2026-08-22 §1) ──────────────────────\n"
    "        # ★ The four DL-preds gates below (caliber stamp / frozen-input census / column set /\n"
    "        #   universe OOD) judge the PREDS FILE, which does not decide an external anchor's book.\n"
    "        #   They are SKIPPED — and the skip is written into the record rather than faked as a\n"
    "        #   pass. Everything that is a VENUE fact (universe gate, per_name_stop, withhold ->\n"
    "        #   reshape, clamp/flatten_only, executor) runs unchanged below.\n"
    "        _is_ext = external is not None\n"
    "        if _is_ext:\n"
    "            preds = preds or {}\n"
    '            symbols = list(external["symbols"])\n'
    '            out_census = {"skipped": "external_book — the DL artifact census does not decide this book"}\n'
    "            want = None\n"
    '            _ood_report = {"state": "SKIPPED_EXTERNAL", "n_members": len(symbols), "n_ood": None,\n'
    '                           "ood_symbols": [], "blind": True,\n'
    '                           "does_not_establish": "anything — the frozen DL model is not scoring this book"}\n'
    "        else:\n"
    "          # ── caliber stamp assertion (audit ②): the split-path guarantee must be a MECHANISM,\n"
    "          # not a convention. preds declare their calibers; we assert against config; mismatch\n"
    "          # BLOCKS the anchor. Closes the chain config -> stamp -> consumption, the same shape\n"
    "          # as the protocol's registry -> declaration -> observation chain.\n"
    '          expected = _load(os.path.join(_REPO, "config", "book.json"), {}).get("factor_versions")\n',
    "H7b preamble", sentinel="        _is_ext = external is not None\n")
# ...the rest of that block (up to the end of the OOD try/except) is re-indented by 2? No — by 4
# for the code; the comment lines above were written at +2 by hand only to make the hunk visible.
# Fix: normalise the whole block to +4. We do it in two steps: first indent the code lines after
# the `expected = ...` line, then re-indent the five lines we wrote at +2.
if _did7:
  al, (i0, i1) = indent_block(
    al,
    '        stamped = preds.get("factor_versions")\n'.strip("\n"),
    '                               f"a frozen model is scoring {len(symbols)} coins unverified")',
    "H7c DL gates block")
  # the five +2 lines -> +4
  al = al.replace(
    "        else:\n"
    "          # ── caliber stamp assertion (audit ②): the split-path guarantee must be a MECHANISM,\n"
    "          # not a convention. preds declare their calibers; we assert against config; mismatch\n"
    "          # BLOCKS the anchor. Closes the chain config -> stamp -> consumption, the same shape\n"
    "          # as the protocol's registry -> declaration -> observation chain.\n"
    '          expected = _load(os.path.join(_REPO, "config", "book.json"), {}).get("factor_versions")\n',
    "        else:\n"
    "            # ── caliber stamp assertion (audit ②): the split-path guarantee must be a MECHANISM,\n"
    "            # not a convention. preds declare their calibers; we assert against config; mismatch\n"
    "            # BLOCKS the anchor. Closes the chain config -> stamp -> consumption, the same shape\n"
    "            # as the protocol's registry -> declaration -> observation chain.\n"
    '            expected = _load(os.path.join(_REPO, "config", "book.json"), {}).get("factor_versions")\n', 1)

# H8 — after the per_name_stop sets: the venue-eligibility filter the design KEEPS (external only).
al, _did8 = apply_hunk(al,
    '            except Exception as _e:\n'
    '                self.alarm("HIGH", f"per_name_stop 状态读取失败({type(_e).__name__}) — 条款本锚未生效, "\n'
    '                                   f"计数状态未损失(只读路径)")\n'
    "\n"
    "        # signal: split-path caliber is enforced by construction — funding comes from the\n",
    '            except Exception as _e:\n'
    '                self.alarm("HIGH", f"per_name_stop 状态读取失败({type(_e).__name__}) — 条款本锚未生效, "\n'
    '                                   f"计数状态未损失(只读路径)")\n'
    "        # ── external book: venue ELIGIBILITY beyond `status` (design §1 '450 候选 ∩ 交易所\n"
    "        #    TRADING COIN perp', 非 ASCII/股票类名排除) — probe v2's rule, pure fn over exchangeInfo.\n"
    "        #    Excluded names join `_untradable` ⇒ pop if unheld / clamp if held (reduce-only).\n"
    "        #    DRY_RUN skips the fetch exactly as _universe_gate does.\n"
    "        self._ext_meta = None\n"
    '        if _is_ext and self.broker.mode != "DRY_RUN":\n'
    "            try:\n"
    '                _exi = self.src._get("/fapi/v1/exchangeInfo").get("symbols", [])\n'
    "                self._ext_meta = EXT.venue_meta_exclusions(_exi, symbols)\n"
    "                if self._ext_meta:\n"
    "                    self._untradable = set(self._untradable) | set(self._ext_meta)\n"
    "            except Exception as _e:                  # noqa: BLE001\n"
    '                self.alarm("HIGH", f"external book: exchangeInfo 元数据过滤不可用({type(_e).__name__}) — "\n'
    '                                   f"本锚只按 status 门过滤(非 COIN/非 ASCII 名未排除)")\n'
    "\n"
    "        if _is_ext:\n"
    "            # ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,\n"
    "            #   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the\n"
    "            #   book below is exactly w/gross_norm x NAV x gross_mult before venue withholds.\n"
    '            book = {"target_w": EXT.target_vector(external, symbols)}\n'
    '            _bw = {"book_source": "external", "gross_mult": external["gross_mult"]}\n'
    '            self._last_harvest_ema = {"alpha": None, "applied": False, "n_carried": 0,\n'
    '                                      "n_symbols": len(symbols), "reset_by_trip": False,\n'
    '                                      "skipped": "external_book"}\n'
    "        else:\n"
    "          # signal: split-path caliber is enforced by construction — funding comes from the\n",
    "H8a meta filter + external target",
    sentinel='            book = {"target_w": EXT.target_vector(external, symbols)}\n')
if _did8:
  al, _ = indent_block(
    al,
    "        # corrected fapi series HERE; king/s2 arrive precomputed from the as-trained panel.",
    '                                  "reset_by_trip": bool(_tripped)}',
    "H8b compose/EMA block")
  al = al.replace(
    "        else:\n"
    "          # signal: split-path caliber is enforced by construction — funding comes from the\n",
    "        else:\n"
    "            # signal: split-path caliber is enforced by construction — funding comes from the\n", 1)

# H9 — sizing from gross_mult in external mode.
al = replace_once(al,
    "        _sz = self._size_book()\n"
    "        out_sizing = _sz\n",
    '        _sz = self._size_book(target_leverage=(external["gross_mult"] if _is_ext else None),\n'
    '                              leverage_source=("external_book.gross_mult" if _is_ext else None))\n'
    "        out_sizing = _sz\n",
    "H9 sizing")

# H10 — the 2x min-notional eligibility filter (external only), BEFORE the withhold/reshape.
al = replace_once(al,
    "        # _pns_zero_targets: stop 名 target 强制置零(条款动作=flatten, 非 reduce) — 置零后\n",
    "        # ── external book: 2x min-notional ELIGIBILITY (design §1 '最小名义额可达 NAV×gross/名 ≥\n"
    "        #    2×minNotional'): a name that cannot clear twice its floor cannot be ADJUSTED later, so\n"
    "        #    it is withheld here — unheld ⇒ popped (then the reshape re-demeans/rescales the rest),\n"
    "        #    held ⇒ clamped reduce-only. Recorded every anchor; paged only above EXT_DUST_ALARM_FRAC.\n"
    "        self._ext_dust = None\n"
    "        if _is_ext:\n"
    '            self._ext_dust = EXT.below_min_notional(target, _fl, external["min_notional_mult"])\n'
    '            if self._ext_dust["names"]:\n'
    '                self._untradable = set(getattr(self, "_untradable", ())) | set(self._ext_dust["names"])\n'
    '            if (self._ext_dust.get("mass_frac") or 0.0) > EXT_DUST_ALARM_FRAC:\n'
    '                self.alarm("HIGH", f"external book: {self._ext_dust[\'n\']} 个名字的目标名义额低于 "\n'
    '                                   f"{external[\'min_notional_mult\']:g}×minNotional, 合计 gross 的 "\n'
    '                                   f"{self._ext_dust[\'mass_frac\']:.1%} (>{EXT_DUST_ALARM_FRAC:.0%}) 被撤下 — "\n'
    '                                   f"NAV×gross_mult 对 450 名宇宙太小, 广度损失是个发现, 不是噪声。")\n'
    "        # _pns_zero_targets: stop 名 target 强制置零(条款动作=flatten, 非 reduce) — 置零后\n",
    "H10 dust filter")

# H11 — the neutral band is NOT applied to an external book (design §1); internal unchanged.
al, _did11 = apply_hunk(al,
    "        # ★ 中性保持型免交易带(PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)。\n",
    "        if _is_ext:\n"
    "            # ★ design §1: the external book is NOT passed through the neutral band (the producer's\n"
    "            #   weights already carry its own turnover rule; W2b measured the mixed pipeline loses).\n"
    '            _nb = {"applied": False, "skipped": "external_book", "n_in": len(target),\n'
    '                   "n_held": 0, "n_traded": len(target), "n_exempt": 0}\n'
    "            self._last_no_trade_band = _nb\n"
    "        else:\n"
    "          # ★ 中性保持型免交易带(PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)。\n",
    "H11a band guard",
    sentinel='            _nb = {"applied": False, "skipped": "external_book", "n_in": len(target),\n')
if _did11:
  al, _ = indent_block(
    al,
    "        #   必须在 withhold+reshape 之后 —— reshape 的 re-demean 会移动所有名字, 放在其前带就白带了;",
    '            self._last_no_trade_band = {**_nb, "state_write_error": type(_e).__name__}',
    "H11b band block")
  al = al.replace(
    "        else:\n"
    "          # ★ 中性保持型免交易带(PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)。\n",
    "        else:\n"
    "            # ★ 中性保持型免交易带(PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)。\n", 1)

# H12 — the anchor record names WHICH book traded (external stamp / universe sha / filters).
al = replace_once(al,
    '            "factor_version": (json.dumps(preds["factor_versions"], sort_keys=True)\n'
    '                               if preds.get("factor_versions") is not None else\n'
    '                               "UNKNOWN — the preds file carried no factor_versions"),\n'
    '            "panel_hash": (preds.get("panel") or {}).get("columns_sha256", "UNKNOWN"),\n',
    '            "factor_version": (EXT.factor_version_stamp(external) if _is_ext else\n'
    '                               json.dumps(preds["factor_versions"], sort_keys=True)\n'
    '                               if preds.get("factor_versions") is not None else\n'
    '                               "UNKNOWN — the preds file carried no factor_versions"),\n'
    '            "panel_hash": (external["universe_sha"] if _is_ext else\n'
    '                           (preds.get("panel") or {}).get("columns_sha256", "UNKNOWN")),\n'
    "            # ★ WHICH BOOK: 'internal' is today's composer; 'external' names the producer's file\n"
    "            #   (booster/weights/universe shas travel in factor_version + panel_hash above) and\n"
    "            #   the two KEPT per-name filters' verdicts — the ledger can then explain every name\n"
    "            #   the wide book asked for that was not sent.\n"
    '            "book_source": "external" if _is_ext else "internal",\n'
    '            "external_book": (EXT.record(external, {\n'
    '                "meta_excluded": (dict(sorted((getattr(self, "_ext_meta", None) or {}).items())[:40])\n'
    '                                  if getattr(self, "_ext_meta", None) is not None else "NOT CHECKED (DRY_RUN or fetch failed)"),\n'
    '                "n_meta_excluded": (len(getattr(self, "_ext_meta", None) or {})\n'
    '                                    if getattr(self, "_ext_meta", None) is not None else None),\n'
    '                "below_min_notional": ({k: (sorted(v)[:40] if isinstance(v, set) else v)\n'
    '                                        for k, v in (getattr(self, "_ext_dust", None) or {}).items()}\n'
    '                                       if getattr(self, "_ext_dust", None) else None)})\n'
    "                              if _is_ext else None),\n",
    "H12 ctx stamps")

# H13 — the anchors row carries book_source / external_book explicitly (extra keys are allowed by
#       pilot_log.validate; factor_version/panel_hash already carry the external stamp).
al = replace_once(al,
    '                row["reshape"] = ctx.get("reshape")\n',
    '                row["reshape"] = ctx.get("reshape")\n'
    "                # ★ WHICH BOOK, as a column (2026-08-22): downstream readers (watchdog/IC monitor/\n"
    "                #   guard_twin) must not parse factor_version to learn it.\n"
    '                row["book_source"] = ctx.get("book_source", "internal")\n'
    '                if ctx.get("external_book"):\n'
    '                    row["external_book"] = ctx["external_book"]\n',
    "H13 anchors row")

# H14 — the _trade return carries the per-name filter verdicts too (phase_A log line).
al = replace_once(al,
    '                "rebalance_id": rid, "anchor_ts": anchor_ts,\n'
    "                # ★ `live` and `benign_rejected` are handed over SEPARATELY on purpose. `live`\n",
    '                "rebalance_id": rid, "anchor_ts": anchor_ts,\n'
    '                "book_source": "external" if _is_ext else "internal",\n'
    '                **({"external_filters": (self._anchor_ctx.get("external_book") or {})} if _is_ext else {}),\n'
    "                # ★ `live` and `benign_rejected` are handed over SEPARATELY on purpose. `live`\n",
    "H14 return")

# H15 — phase_A's harvest/band reports in external mode: the two records already say skipped.
# (no code: self._last_harvest_ema / self._last_no_trade_band are set in H8/H11.)

# H15 — (batch 3) tails outside the producer's universe: pop is done by the reader (w = in-universe
#       book); the anchor PAGES when the popped share is large (information, never a halt).
al = replace_once(al,
    '            if ext["ok"]:\n'
    '                state["external_last_good_anchor_ts"] = int(ext["anchor_ts"])\n',
    '            if ext["ok"]:\n'
    '                state["external_last_good_anchor_ts"] = int(ext["anchor_ts"])\n'
    '                if float(ext.get("gross_outside_frac") or 0.0) > EXT.OUTSIDE_UNIVERSE_ALARM_FRAC:\n'
    '                    self.alarm("HIGH", f"external book: {ext.get(\'n_outside_universe\')} 个名字 = 生产方 gross 的 "\n'
    '                                       f"{float(ext.get(\'gross_outside_frac\') or 0.0):.1%} 在其自己的宇宙之外(冻结尾巴) — "\n'
    '                                       f"已从目标剔除并按宇宙内 Σ|w| 归一; 信息级(>{EXT.OUTSIDE_UNIVERSE_ALARM_FRAC:.0%} 才报), "\n'
    '                                       f"生产方纸面书仍含尾巴。")\n',
    "H15 outside-universe alarm")
# H16 — (batch 3) symbols = producer's IN-UNIVERSE names ∪ held names; held names the producer no
#       longer targets are exited reduce-only through clamp/flatten_only, never market-exited.
al = replace_once(al,
    '            symbols = list(external["symbols"])\n'
    '            out_census = {"skipped": "external_book — the DL artifact census does not decide this book"}\n',
    "            # ★ symbols = the producer's IN-UNIVERSE non-zero names ∪ every name we HOLD. A held name the\n"
    "            #   producer no longer targets (left its universe / member set, or weight 0) is EXITED through\n"
    "            #   the existing clamp -> flatten_only channel (maker reduce-only, mandatory top-up after) —\n"
    "            #   NOT market-exited by the universe gate, which stays reserved for names whose venue status\n"
    "            #   is no longer TRADING. Out-of-universe names we do NOT hold are simply absent (popped at\n"
    "            #   the reader: `external[\"w\"]` is the in-universe book, normalised by its own sum|w|).\n"
    '            self._ext_held_exit = EXT.held_not_in_target(state.get("positions"), external["symbols"])\n'
    '            symbols = sorted(set(external["symbols"]) | set(self._ext_held_exit))\n'
    '            out_census = {"skipped": "external_book — the DL artifact census does not decide this book"}\n',
    "H16 symbols ∪ held")
# H17 — held names not targeted join the untradable set ⇒ clamp pass-2 ⇒ flatten_only (reduce-only)
al = replace_once(al,
    "        if _is_ext:\n"
    "            # ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,\n",
    '        if _is_ext and getattr(self, "_ext_held_exit", None):\n'
    "            # held names the producer no longer targets ⇒ reduce-only exit via clamp/flatten_only\n"
    "            self._untradable = set(self._untradable) | set(self._ext_held_exit)\n"
    "        if _is_ext:\n"
    "            # ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,\n",
    "H17 held exit -> untradable")
# H18 — the ctx/anchors record names the exited-held set beside the two filters
al = replace_once(al,
    '            "external_book": (EXT.record(external, {\n'
    '                "meta_excluded": (dict(sorted((getattr(self, "_ext_meta", None) or {}).items())[:40])\n',
    '            "external_book": (EXT.record(external, {\n'
    '                "held_exit": list(getattr(self, "_ext_held_exit", None) or [])[:40],\n'
    '                "n_held_exit": len(getattr(self, "_ext_held_exit", None) or []),\n'
    '                "meta_excluded": (dict(sorted((getattr(self, "_ext_meta", None) or {}).items())[:40])\n',
    "H18 ctx held_exit")

write(AL_REL, al)
write_diff(AL_REL, al0, al, AL_REL.replace("anchor_loop.py", "anchor_loop.external.diff"))
print(f"anchor_loop.py: {len(al0.splitlines())} -> {len(al.splitlines())} lines")

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 2. live/per_name_stop.py — profile switch (base values untouched)
# ════════════════════════════════════════════════════════════════════════════════════════════════
PNS_REL = "live/per_name_stop.py"
pn = read(PNS_REL)
pn0 = pn
pn = replace_once(pn,
    "def cfg(path=CFG_PATH):\n"
    "    try:\n"
    "        with open(path) as f:\n"
    '            return json.load(f).get("per_name_stop") or {}\n'
    "    except Exception:\n"
    "        return {}\n",
    "def resolve_profile(base):\n"
    '    """profiles / active_profile 覆盖(2026-08-22 宽书换装, DESIGN_wide_live_deployment §1):\n'
    "    active_profile=None ⇒ 基础键逐位不变(今天的行为); 'wide' ⇒ profiles.wide 覆盖其列出的键\n"
    "    (d30_n2_c42: depth −0.30 × 连续 2 锚 × 冷却 7 天); 未知名 ⇒ 基础值继续生效 + `_profile_error`\n"
    '    (终锚告警; 条款不因配置错而失明 — 失明方向是止损关闭, 比参数回落更危险)。纯函数。"""\n'
    '    out = {k: v for k, v in (base or {}).items() if k not in ("profiles", "active_profile")}\n'
    '    prof = (base or {}).get("active_profile")\n'
    "    if prof is None:\n"
    "        return out\n"
    '    p = ((base or {}).get("profiles") or {}).get(prof)\n'
    "    if not isinstance(p, dict):\n"
    '        out["_profile_error"] = f"unknown per_name_stop profile {prof!r}; base parameters stay in force"\n'
    "        return out\n"
    "    for k, v in p.items():\n"
    '        if not str(k).startswith("_"):\n'
    "            out[k] = v\n"
    '    out["_profile"] = prof\n'
    "    return out\n"
    "\n"
    "\n"
    "def cfg(path=CFG_PATH):\n"
    "    try:\n"
    "        with open(path) as f:\n"
    '            base = json.load(f).get("per_name_stop") or {}\n'
    "    except Exception:\n"
    "        return {}\n"
    "    return resolve_profile(base)\n",
    "PNS cfg profile")
pn = replace_once(pn,
    "    st, ev = evaluate(snapshot, load_state(state_path), cfg(cfg_path), now_ts)\n"
    "    _save(st, state_path)\n"
    '    return {"state": st, "alarms": ev}\n',
    "    conf = cfg(cfg_path)\n"
    "    st, ev = evaluate(snapshot, load_state(state_path), conf, now_ts)\n"
    "    _save(st, state_path)\n"
    '    if conf.get("_profile_error"):\n'
    "        # 配置错不让条款失明: 基础参数已生效(见 resolve_profile), 但必须有人听见\n"
    '        ev = list(ev) + [f"★ per_name_stop profile 配置错误: {conf[\'_profile_error\']}"]\n'
    '    return {"state": st, "alarms": ev}\n',
    "PNS alarm on profile error")
write(PNS_REL, pn)
write_diff(PNS_REL, pn0, pn)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 3. config/book.json — text insertion (keeps the file's own formatting; JSON validity asserted)
# ════════════════════════════════════════════════════════════════════════════════════════════════
BK_REL = "config/book.json"
bk = read(BK_REL)
bk0 = bk
bk = replace_once(bk,
    ' "anchor_max_seconds": 1500,\n',
    ' "anchor_max_seconds": 3000,\n'
    ' "_anchor_max_seconds_external_note": "★ 1500→3000 (2026-08-22, wide-live staging). In external mode the anchor process deliberately idles until the producer\'s slot (external_book.anchor_offset_min, measured shadow landing ≈N+21.5 under SHADOW_OFFSET_MIN=16 + ~5.5 min runtime) BEFORE phase A; budget = offset 23 + poll 5 + phase A 1 + k 15 + phase B/C 3 + reports ≈ 47 min. 1500 would SIGALRM-kill the process mid-phase-B. Internal mode never reaches the old 25 min; the only other consumer is book_config.collision_window (a WARNING half-width for manual runs, now ±50 min).",\n',
    "BK cap")
bk = replace_once(bk,
    '  "_semantics": "深度=unrealizedProfit/|notional| 终锚读回; ≤-25%连续2锚 ⇒ 该名flatten_only(maker出场不追); 平仓后7天禁入; 其余名字全程正常"\n'
    " }\n"
    "}",
    '  "_semantics": "深度=unrealizedProfit/|notional| 终锚读回; ≤-25%连续2锚 ⇒ 该名flatten_only(maker出场不追); 平仓后7天禁入; 其余名字全程正常",\n'
    '  "active_profile": null,\n'
    '  "_active_profile_note": "null ⇒ 上面的基础值逐位生效(今天的行为)。\'wide\' ⇒ profiles.wide 覆盖其列出的键。与 book_source 成对切换(book_source=external ⇔ active_profile=wide), 由 external_book.pns_profile_consistent 守卫(不一致 ⇒ HIGH 告警, 条款仍按当前 profile 运行)。未知名 ⇒ 基础值继续生效 + 终锚告警(条款不失明)。读取经 per_name_stop.resolve_profile。",\n'
    '  "profiles": {\n'
    '   "wide": {\n'
    '    "depth_pct": -0.3,\n'
    '    "consecutive_anchors": 2,\n'
    '    "cooloff_days": 7,\n'
    '    "min_notional_usdt": 20.0,\n'
    '    "_basis": "宽书止损层 d30_n2_c42 (DESIGN_wide_live_deployment_2026-08-22 §1; wide_stop_grid.json: maxDD −33.4%, 净额代价 2.6%, 全网格性价比最优; ~/wide_shadow/stop_overlay.py 同参数自 08-21 影子跟踪)。min_notional_usdt 沿用 20(★ 待裁: L1 1×NAV/~300 名中位 ≈40 USDT, 20 以下的小仓条款看不见)。"\n'
    "   }\n"
    "  }\n"
    " },\n"
    ' "book_source": "internal",\n'
    ' "_book_source_note": "★ DESIGN_wide_live_deployment_2026-08-22 §1. \'internal\' = 今天的书(king/s2/funding → compose_book → EMA → 带), 逐位不变。\'external\' = 目标向量从 external_book.path/<anchor_ts>.json(签名, 宽书生产方 shadow_loop_v2 写)读取; 不经 compose_book/风险预算/EMA/中性带; 保留 universe 门/per_name_stop/撤名重整/clamp/flatten_only/执行层/§4 看门狗全条。任何校验失败 ⇒ 保持现仓不交易 + HIGH 告警 external_book_unavailable, **绝不回退 internal**。非此二值 ⇒ 锚被 BLOCKED_CONFIG(CRITICAL)。切换 = 本键 + per_name_stop.active_profile 成对改(见 _active_profile_note), 守卫 live/tests_external_book.py。回滚 = 停开仓(resume_from_trip 的反向 / KILL), 不回 internal(在役已 08-22 03:15Z 退役)。",\n'
    ' "external_book": {\n'
    '  "path": "/Users/haosiyu/wide_shadow/state/target_live",\n'
    '  "max_age_min": 10,\n'
    '  "anchor_offset_min": 23,\n'
    '  "poll_grace_min": 5,\n'
    '  "gross_mult": 1.0,\n'
    '  "require_anchor_match": true,\n'
    '  "universe_sha_pin": null,\n'
    '  "booster_sha_pin": null,\n'
    '  "min_notional_mult": 2.0,\n'
    '  "on_unavailable": "ladder",\n'
    '  "schema": "wide_target_v1",\n'
    '  "_basis": "DESIGN_wide_live_deployment_2026-08-22 §1-§2; 用户预授权 §3-bis(L1 1× 需五条收据)。gross_mult: L0 镜像 0(停开仓下跑, 不是 0 值 — 见 RUNBOOK)、L1 1.0、L2 2.0、L3 2.5(上限, 另需用户一字; 且不得超过 target_leverage — §4-4b 以 target_leverage 为杠杆政策, external_book.config 在配置层拒绝)。",\n'
    '  "_timing": "★★ 设计写 N+6 产出/N+8 读取; 实测(2026-08-20..22 八锚 shadow_log signal 行)影子以 SHADOW_OFFSET_MIN=16 起跑(进程 85661 环境变量)+ 运行 311-351s ⇒ 权重落盘 N+21:12..N+21:51。故 anchor_offset_min=23 + poll_grace_min=5(N+23 起每 15s 重试至 N+28); 若影子 v2 改回 offset 6 ⇒ 落盘 ≈N+12 ⇒ 改 13/5。max_age_min=10 以 written_utc 计(读取时刻 − 写入时刻), 与 anchor_ts 必须等于本锚并列; 两者都要过。",\n'
    '  "_on_unavailable": "ladder = 读不到/校验失败 ⇒ 本锚 HOLD(保持现仓, 零下单, HIGH 告警), 且年龄按【最近一个校验通过的目标】计入既有预注册阶梯(1-5 锚 HOLD / ≥6 锚 DERISK 50%→25% reduce-only / ≥12 锚 FLATTEN) — 与 preds 阶梯同一机制同一文档(anchor_loop 顶部 docstring)。hold = 永远只 HOLD+告警, 不升级。两者都绝不回退 internal。",\n'
    '  "_rollback": "停开仓: bash ops/KILL.sh(全停)或写 watchdog reduce-only 状态; 不改回 internal。改回 internal 需用户一字 + 先核在役书数据/模型链路仍完整(08-22 后无人维护)。"\n'
    " }\n"
    "}",
    "BK external block")
json.loads(bk)                           # must still parse
write(BK_REL, bk)
write_diff(BK_REL, bk0, bk)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 4. ops/gate_coverage.py — the new suite's boundary statement (the battery REFUSES without it)
# ════════════════════════════════════════════════════════════════════════════════════════════════
GC_REL = "ops/gate_coverage.py"
gc = read(GC_REL)
gc0 = gc
gc = replace_once(gc,
    '    "tests_guard_calibers": "that the guard reads the ACCOUNT — it proves the §4-2/§4-4/§4-4b/per-name/§4-1/3/5/6/7 "\n',
    '    "tests_external_book": "that the WIDE BOOK IS WORTH TRADING — it proves the adapter reads the producer\'s signed target exactly (in-universe w / in-universe sum|w| x NAV x gross_mult, bitwise on a neutral unit-gross fixture; no EMA, no band, no risk budget), that every named defect of the file (missing / sidecar missing / sha mismatch / bad json / schema incl. a missing universe list / universe-list sha / anchor mismatch / stale / future-dated / pin mismatch / bad weights / gross_norm mismatch) HOLDS the anchor with zero orders and a HIGH `external_book_unavailable`, that the hold never falls back to the internal composer, that the age feeds the pre-registered ladder (and `on_unavailable: hold` pins it), that internal mode is byte-identical (the external reader is never invoked; a mutant that forces the external branch goes red), that INVALID config blocks, that names outside the producer\'s universe list are never targets (popped; the book normalised by the in-universe sum so the live gross is undiluted; a >25% tail pages HIGH; a reader that does not split is a red mutant), that a HELD name the file no longer targets is exited reduce-only through clamp/flatten_only (never market-exited), that the two KEPT per-name filters (venue meta: non-COIN/non-ASCII/non-USDT/leveraged/non-TRADING; 2x min-notional) withhold exactly the named names, and that the per_name_stop profile switch resolves (null = base bitwise, wide = d30_n2_c42, unknown = base + alarm) and is coupled to book_source; every fixture is the REAL config pinned to the internal baseline, so the suite is green with the disk in either state. Seven blind spots: (a) every loop test runs DRY_RUN with a stub bookTicker and hand-set filters — no venue, no fills, no real NAV; the first LIVE external anchor is the first; (b) the wait-for-slot is tested as a pure plan (wake time, 0/positive) — whether the real process actually idles to N+offset and the 3000s cap suffices is a wall-clock fact only a scheduled anchor shows; (c) it proves the file is READ FAITHFULLY, never that the producer\'s weights are RIGHT — the wide book\'s alpha, turnover and the N+8/N+23 phase question live in the shadow/audit, not here; (d) the producer side (shadow_loop_v3.write_target_live) is tested in the research repo (tests_target_live_output), and the pair agreement (its output is accepted by this reader; a v2-style file is refused) is asserted THERE, not in this battery; (e) venue eligibility is a pure function over a synthetic exchangeInfo — the real payload\'s field names drifting (underlyingType) would exclude nothing and this stays green; (f) the 2x min-notional rule, the 10% breadth-loss line (EXT_DUST_ALARM_FRAC) and the 25% tail line (OUTSIDE_UNIVERSE_ALARM_FRAC) are policy numbers — none is calibrated here; (g) the universe LIST is trusted once its sha matches the declared universe_sha — whether it is the RIGHT universe (450 = symbols_live) is the producer\'s claim, pinned only if `universe_sha_pin` is set",\n'
    '    "tests_guard_calibers": "that the guard reads the ACCOUNT — it proves the §4-2/§4-4/§4-4b/per-name/§4-1/3/5/6/7 "\n',
    "GC scope entry")
write(GC_REL, gc)
write_diff(GC_REL, gc0, gc)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 5. run_acceptance.sh — explicit registration (the runner REFUSES an unregistered tests_*.py)
# ════════════════════════════════════════════════════════════════════════════════════════════════
RA_REL = "run_acceptance.sh"
ra = read(RA_REL)
ra0 = ra
ra = replace_once(ra,
    '  "tests_guard_calibers:$_SELF/live/tests_guard_calibers.py"\n'
    ")\n",
    '  "tests_guard_calibers:$_SELF/live/tests_guard_calibers.py"\n'
    "  # ★ 外部书适配器 (DESIGN_wide_live_deployment_2026-08-22 §1/§3.2): 宽书签名目标文件 → 目标向量;\n"
    "  #   读取/校验/换算/过滤/告警 + internal 逐位不变 + per_name_stop profile 切换; 每条有会红变异体。\n"
    '  "tests_external_book:$_SELF/live/tests_external_book.py"\n'
    ")\n",
    "RA register")
write(RA_REL, ra)
write_diff(RA_REL, ra0, ra)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 6. live/tests_imports.py — the derived production-module set must name the new module
# ════════════════════════════════════════════════════════════════════════════════════════════════
TI_REL = "live/tests_imports.py"
ti = read(TI_REL)
ti0 = ti
ti = replace_once(ti,
    '    "per_name_stop",  # 逐名止损条款 cf40ea21(2026-08-20 全面启用)\n',
    '    "per_name_stop",  # 逐名止损条款 cf40ea21(2026-08-20 全面启用)\n'
    '    "external_book",  # 外部书适配器 (DESIGN_wide_live_deployment_2026-08-22 §1): anchor_loop imports it\n',
    "TI module")
write(TI_REL, ti)
write_diff(TI_REL, ti0, ti)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 7. live/tests_entrypoint_wiring.py — [D] learns the external-HOLD state (no n_planned there)
# ════════════════════════════════════════════════════════════════════════════════════════════════
TE_REL = "live/tests_entrypoint_wiring.py"
te = read(TE_REL)
te0 = te
te = replace_once(te,
    '    if _j.get("off_schedule_halt"):\n'
    "        # ★ 2026-08-21: 守门对象精确化为【开仓】单(n_live_opening); reduce-only/flatten 路径按设计\n",
    '    if _j.get("book_source") == "external" and _j.get("action") != "TRADE":\n'
    "        # ★ 2026-08-22 external book: a DRY battery run at an arbitrary wall-clock minute will\n"
    "        #   usually find no verified target for the nearest slot (the producer lands ~N+22) ⇒ the\n"
    "        #   loop HOLDS by design: no target vector, no plan, no orders, reason named. That is the\n"
    "        #   property to assert here — `n_planned > 0` cannot hold on a HOLD anchor and must not\n"
    "        #   be demanded of it (the TRADE branch below still demands it when the file IS there).\n"
    '        check("★ external book unavailable ⇒ HOLD with a NAMED reason and no plan",\n'
    '              _j.get("action") in ("HOLD", "DERISK", "FLATTEN")\n'
    '              and bool((_j.get("external_book") or {}).get("reason"))\n'
    '              and "n_planned" not in _j,\n'
    '              f"action={_j.get(\'action\')} external_book={_j.get(\'external_book\')}")\n'
    '    elif _j.get("off_schedule_halt"):\n'
    "        # ★ 2026-08-21: 守门对象精确化为【开仓】单(n_live_opening); reduce-only/flatten 路径按设计\n",
    "TE external hold branch")
write(TE_REL, te)
write_diff(TE_REL, te0, te)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 7b. live/tests_anchor_skip_visible.py — [E2] pinned the collision half-width to the NUMBER 25 min
#     (= anchor_max_seconds 1500/60). The cap is now 3000 (external wait); the suite's own principle
#     is "DERIVED from config, not a second number", so derive it.
# ════════════════════════════════════════════════════════════════════════════════════════════════
TA_REL = "live/tests_anchor_skip_visible.py"
ta = read(TA_REL)
ta0 = ta
ta = replace_once(ta,
    "_in = BC.collision_window(_SLOT - 300)\n"
    "_out = BC.collision_window(_SLOT + 26 * 60)\n",
    "# ★ 2026-08-22: the half-width is one anchor lifetime = config anchor_max_seconds (1500s -> 25 min until the\n"
    "#   external-book wait raised it to 3000s -> 50 min). DERIVED here too — pinning 25 was a second copy.\n"
    '_HALF = float(json.load(open(os.path.join(REPO, "config", "book.json"))).get("anchor_max_seconds", 1500)) / 60.0\n'
    "_in = BC.collision_window(_SLOT - 300)\n"
    "_out = BC.collision_window(_SLOT + (_HALF + 1) * 60)\n",
    "TA derive half-width")
ta = replace_once(ta,
    'check("★★ 26 min after it does not — the band is one anchor lifetime, so it closes when the "\n'
    '      "contender can no longer be holding the lock", _out["would_contend"] is False)\n',
    'check(f"★★ {_HALF + 1:.0f} min after it does not — the band is one anchor lifetime (config anchor_max_seconds), "\n'
    '      "so it closes when the contender can no longer be holding the lock", _out["would_contend"] is False)\n',
    "TA after-band")
ta = replace_once(ta,
    '      "number invented about the same physics — the ask was ±15, the honest figure is ±25, and "\n'
    '      "being wrong in the NARROW direction is what costs an anchor",\n'
    '      abs(_in["half_width_min"] - 25.0) < 1e-9\n',
    '      "number invented about the same physics — the ask was ±15, the honest figure is one anchor "\n'
    '      "lifetime (±25 at 1500s; ±50 since the external-book wait raised the cap to 3000s), and "\n'
    '      "being wrong in the NARROW direction is what costs an anchor",\n'
    '      abs(_in["half_width_min"] - _HALF) < 1e-9\n',
    "TA half-width value")
write(TA_REL, ta)
write_diff(TA_REL, ta0, ta)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 7c. live/tests_signal_and_loop.py — DECOUPLE the fixtures from the disk book source (2026-08-22,
#     lead's batch 20260822T041458Z: with disk book_source=external the suite copied the disk config
#     as its baseline and every internal-path case went red — a battery that reddens on the
#     production switch would lock the switch out). Every disk-derived fixture is pinned to the
#     INTERNAL baseline; the clock/tolerance/anchors it actually tests stay the REAL ones.
# ════════════════════════════════════════════════════════════════════════════════════════════════
TS_REL = "live/tests_signal_and_loop.py"
ts = read(TS_REL)
ts0 = ts
ts = replace_once(ts,
    "_open_clock = json.load(open(BC.BOOK_PATH))\n"
    '_open_clock["anchor_late_tolerance_min"] = 10 ** 6\n',
    "# ★ 2026-08-22 DECOUPLED FROM THE DISK BOOK SOURCE. `book_source` / `per_name_stop.active_profile`\n"
    "#   are PRODUCTION switches (external = the wide book). A suite that copies the disk config as its\n"
    "#   fixture baseline flips its own subject when the operator flips the book — and a battery that\n"
    "#   goes red on the switch then locks the switch out. Every disk-derived fixture below is the REAL\n"
    "#   config (clock, legs, weights, stamps…) with the book source pinned to the INTERNAL baseline,\n"
    "#   which is what these cases test. tests_external_book owns the external branch, both ways.\n"
    "def _internal_baseline(d):\n"
    "    d = dict(d)\n"
    '    d["book_source"] = "internal"\n'
    '    d["per_name_stop"] = dict(d.get("per_name_stop") or {}, active_profile=None)\n'
    "    return d\n"
    "\n"
    "\n"
    "_open_clock = _internal_baseline(json.load(open(BC.BOOK_PATH)))\n"
    '_open_clock["anchor_late_tolerance_min"] = 10 ** 6\n',
    "TS open clock baseline")
ts = replace_once(ts,
    "with BC._using(BC.BOOK_PATH):                     # ← the REAL config, for this block only\n",
    '_REAL_INTERNAL = os.path.join(tmp, "book_real_internal.json")   # the REAL clock/tolerance; book source pinned internal\n'
    'json.dump(_internal_baseline(json.load(open(BC.BOOK_PATH))), open(_REAL_INTERNAL, "w"))\n'
    "with BC._using(_REAL_INTERNAL):                  # ← the REAL clock config (tolerance/anchors), for this block only\n",
    "TS clock block")
ts = replace_once(ts,
    "    _mode_book = json.load(open(BC.BOOK_PATH))\n",
    "    _mode_book = _internal_baseline(json.load(open(BC.BOOK_PATH)))\n",
    "TS mode book")
ts = replace_once(ts,
    "_probe_book = json.load(open(BC.BOOK_PATH))\n",
    "_probe_book = _internal_baseline(json.load(open(BC.BOOK_PATH)))\n",
    "TS probe book")
ts = replace_once(ts,
    "_bad = json.load(open(BC.BOOK_PATH))\n",
    "_bad = _internal_baseline(json.load(open(BC.BOOK_PATH)))\n",
    "TS bad book")
write(TS_REL, ts)
write_diff(TS_REL, ts0, ts)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 7d. live/tests_guard_calibers.py — [F] hand-derives the BASE clause (−25% × 2); inject that profile
#     explicitly instead of reading whatever profile the disk activates.
# ════════════════════════════════════════════════════════════════════════════════════════════════
TG_REL = "live/tests_guard_calibers.py"
tg = read(TG_REL)
tg0 = tg
tg = replace_once(tg,
    "CFG = PNS.cfg(BOOK_CFG)\n"
    'S0 = {"counters": {}, "stopped": {}, "cooldown": {}}\n',
    "# ★ 2026-08-22: the hand derivations below are for the BASE clause (−25% × 2 × 7d). per_name_stop now\n"
    "#   carries profiles (active_profile=wide ⇒ −30% for the wide book — a PRODUCTION switch). The base\n"
    "#   profile is INJECTED here instead of reading whatever profile the disk happens to activate: a\n"
    "#   suite whose subject flips with the operator's switch would lock the switch out. The wide profile\n"
    "#   itself is asserted in tests_external_book [P] (−28%×2 does not fire, −31%×2 does).\n"
    'CFG = PNS.resolve_profile(dict(json.load(open(BOOK_CFG))["per_name_stop"], active_profile=None))\n'
    'S0 = {"counters": {}, "stopped": {}, "cooldown": {}}\n',
    "TG base profile")
write(TG_REL, tg)
write_diff(TG_REL, tg0, tg)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 7e. live/tests_external_book.py — our own suite (full file in staging). Once batch 1 is applied it
#     also exists in the live repo, so a diff vs that copy is written for review.
# ════════════════════════════════════════════════════════════════════════════════════════════════
TX_REL = "live/tests_external_book.py"
if os.path.exists(os.path.join(LIVE, TX_REL)):
    write_diff(TX_REL, read(TX_REL), read(TX_REL, root=OUT))
else:
    print(f"{TX_REL}: not in the live repo (base before batch 1) — full file only")

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 8. shadow_loop_v2.py = ~/wide_shadow/shadow_loop.py + ONE addition (the signed target output)
# ════════════════════════════════════════════════════════════════════════════════════════════════
sl = open(os.path.join(SHADOW, "shadow_loop.py"), encoding="utf-8").read()
sl0 = sl
sl = replace_once(sl,
    "def append_log(row):\n",
    "# ── v2 (2026-08-22, DESIGN_wide_live_deployment §1/§3.1): signed target file for the live adapter ──\n"
    "# ★ ADDITIVE ONLY. Nothing above or below this block changes; the call site in run_anchor is wrapped\n"
    "#   in try/except so a failure here can never alter the shadow's own behaviour or its 84-anchor\n"
    "#   PASS/FAIL caliber. Schema `wide_target_v1`; the reader is dl_quant_live/live/external_book.py and\n"
    "#   tests_target_live_output.py asserts the pair (this writer's output is accepted by that reader).\n"
    "def universe_sha(symbols):\n"
    '    """sha256 of symbols_live, ORDER-PRESERVING compact JSON — the SAME recipe as\n'
    '    dl_quant_live/live/external_book.universe_sha (pinned by the pair test)."""\n'
    '    return hashlib.sha256(json.dumps(list(symbols), separators=(",", ":")).encode()).hexdigest()\n'
    "\n"
    "\n"
    "def write_target_live(cfg, anchor, sm, wnz, npz_path, out_dir=None):\n"
    '    """Write <out_dir>/<anchor>.json (+ .sha256 sidecar), both via atomic_write (tmp + os.replace).\n'
    "    weights = the SAME vector the shadow carries forward as H (float64; the npz archives float32),\n"
    "    non-zero names only; gross_norm = sum|w|; weights_sha = sha256 of the npz bytes on disk;\n"
    '    universe_sha = symbols_live (450) recipe above; booster_sha = MANIFEST sha of slow2026.txt."""\n'
    '    out_dir = out_dir or f"{STATE_DIR}/target_live"\n'
    "    os.makedirs(out_dir, exist_ok=True)\n"
    '    syms = cfg["symbols_panel"]\n'
    "    weights = {}\n"
    "    for j in wnz:\n"
    "        v = float(sm[int(j)])\n"
    "        if v != 0.0:\n"
    "            weights[syms[int(j)]] = v\n"
    "    gross_norm = float(sum(abs(v) for v in weights.values()))\n"
    '    with open(npz_path, "rb") as f:\n'
    "        wsha = hashlib.sha256(f.read()).hexdigest()\n"
    '    live = list(cfg["symbols_live"])\n'
    '    doc = {"schema": "wide_target_v1", "anchor_ts": int(anchor), "weights": weights,\n'
    '           "gross_norm": gross_norm, "n_names": len(weights),\n'
    '           "universe_sha": universe_sha(live), "n_universe": len(live),\n'
    '           "booster_sha": str(cfg.get("_booster_sha", "")), "weights_sha": wsha,\n'
    '           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),\n'
    '           "producer": "shadow_loop_v2",\n'
    '           "anchor_offset_min": int(os.environ.get("SHADOW_OFFSET_MIN", cfg["params"].get("anchor_offset_min", 6)))}\n'
    '    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()\n'
    '    path = f"{out_dir}/{int(anchor)}.json"\n'
    "    jsha = hashlib.sha256(raw).hexdigest()\n"
    "    atomic_write(path, raw)\n"
    '    atomic_write(path + ".sha256", f"{jsha}  {os.path.basename(path)}\\n".encode())\n'
    '    return {"path": path, "n_names": len(weights), "gross_norm": round(gross_norm, 6),\n'
    '            "json_sha": jsha[:12], "weights_sha": wsha[:12]}\n'
    "\n"
    "\n"
    "def append_log(row):\n",
    "SL helpers")
sl = replace_once(sl,
    '    np.savez_compressed(f"{STATE_DIR}/weights/{anchor}.npz", idx=wnz.astype(np.int32),\n'
    "                        val=sm[wnz].astype(np.float32), members=m.astype(np.int32))\n",
    '    np.savez_compressed(f"{STATE_DIR}/weights/{anchor}.npz", idx=wnz.astype(np.int32),\n'
    "                        val=sm[wnz].astype(np.float32), members=m.astype(np.int32))\n"
    "    # v2: the signed target for the live adapter — additive; never allowed to break the anchor.\n"
    "    try:\n"
    '        _tl = write_target_live(cfg, anchor, sm, wnz, f"{STATE_DIR}/weights/{anchor}.npz")\n'
    '        append_log({"e": "target_live", "anchor_ts": anchor, **_tl})\n'
    "    except Exception as _ex:\n"
    '        append_log({"e": "target_live_error", "anchor_ts": anchor, "err": repr(_ex)[:200]})\n',
    "SL call site")
os.makedirs(os.path.join(STG, "shadow"), exist_ok=True)
open(os.path.join(STG, "shadow", "shadow_loop_v2.py"), "w", encoding="utf-8").write(sl)
open(os.path.join(STG, "shadow", "shadow_loop_v2.diff"), "w", encoding="utf-8").write(
    udiff(sl0, sl, "shadow_loop.py"))

# ════════════════════════════════════════════════════════════════════════════════════════════════
# receipts
# ════════════════════════════════════════════════════════════════════════════════════════════════
try:
    head = subprocess.run(["git", "-C", LIVE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception:
    head = "?"
rec = {"live_repo": LIVE, "live_head": head, "base_commit_expected": BASE_COMMIT_EXPECTED,
       "base_matches": head == BASE_COMMIT_EXPECTED,
       "originals_sha256": {r: sha(os.path.join(LIVE, r)) for r in (AL_REL, PNS_REL, BK_REL, GC_REL, RA_REL, TI_REL, TE_REL, TA_REL, TS_REL, TG_REL)},
       "shadow_loop_sha256": sha(os.path.join(SHADOW, "shadow_loop.py")),
       "staged_sha256": {r: sha(os.path.join(OUT, r)) for r in (AL_REL, PNS_REL, BK_REL, GC_REL, RA_REL, TI_REL, TE_REL, TA_REL, TS_REL, TG_REL)},
       "shadow_loop_v2_sha256": sha(os.path.join(STG, "shadow", "shadow_loop_v2.py"))}
rec["hunks_already_applied_on_base"] = ALREADY
rec["files_unchanged_vs_base"] = UNCHANGED
open(os.path.join(STG, "verify", "PATCH_RECEIPT.json"), "w").write(json.dumps(rec, indent=1))
print(json.dumps(rec, indent=1))
if not rec["base_matches"]:
    print("★ WARNING: live repo HEAD is not the base this patch was written against — hunks applied "
          "by exact match, so the result is still consistent, but re-review the diffs.")
