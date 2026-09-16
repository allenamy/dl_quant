"""ROLL_PATHS gate (FX-TRAIN TRN-01, 2026-09-16; AUDIT_TRAIN 7e1ecf9a TRN-01; FACT_TABLE_TRN §TRN-01).

WHY: every git builder for the month-roll inputs writes a SEPTEMBER path by default (make_raw_patch.py, v4_hole_cells.py,
pod_merge_cache_ext.py, pod_panel_splice.py, fund_pull_pod.py, and pod_panel_ext.py's PANEL_OUT default). Run as-is for a new
month they overwrite files that September's gate and export receipts hash — the E-0912-B class — and nothing in the chain would
notice, because preflight only checks that each contract path EXISTS. A path that exists because last month put it there passes.

WHAT THIS DECIDES, and only this: that this month's contract cannot be pointed at any previous month's artifacts.
  P1 rolled_keys_differ    for every ROLLED key, this month's value differs from the previous month's value for the SAME key
  P2 no_cross_key_reuse    no ROLLED value of this month equals ANY value of the previous contract under any key — the dangerous
                           improvisation is not only "same key, same path" but "this month's CACHE is last month's PANEL"
  P3 rolled_under_root     every ROLLED value lies under this month's $R, so the month's products are inside the month's root
                           (exceptions must be declared in ROLL_ALLOW_OUTSIDE_ROOT, and each one is named in the receipt)
  P4 previous_untouched    every previous-month value that still exists on disk has the sha it had when the previous contract's
                           own receipt was written, when ROLL_PREV_SHA_JSON supplies that record; without it the check is
                           reported NOT_EVALUABLE with its reason, never silently skipped
  P5 no_parent_escape      no value contains a '..' component (the lexical-containment escape of FXR-TRN-1, same family)
The ROLLED set is the eight keys the October template leaves as TODO_ plus RAW_PATCH, which the template gives a real path with
no TODO_ marker and which is therefore the easiest one to leave pointing at September.

This gate does NOT decide whether the roll produced correct data; that is the parity gate and the coverage gate. It decides
whether the month is allowed to write where it is about to write.

Receipt through v4_gate_common.finalize (gate ROLL_PATHS; inputs month_env / prev_month_env): rc 0 iff PASS, else 3.
env (all REQUIRED, no defaults): V4_MONTH_ENV, ROLL_PREV_MONTH_ENV, ROLL_OUT.
optional: ROLL_ALLOW_OUTSIDE_ROOT (comma list of ROLLED keys allowed outside $R, each named in the receipt),
          ROLL_PREV_SHA_JSON (a {path: sha256} record of the previous month's artifacts, for P4).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file

# The keys a month roll PRODUCES. RAW_PATCH is here although the October template gives it a real path: that is exactly why it
# is the easiest one to leave pointing at September (AUDIT_TRAIN TRN-02 evidence line).
ROLLED = ("CACHE", "PANEL_SPLICE", "PANEL_KING", "RAW_PATCH", "HOLE_CELLS", "FUND_AUG", "EMA_STATE_JSON", "EXPORT_PANEL")
_KEYRE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")

_OUT = os.environ.get("ROLL_OUT")
if not _OUT:
    print("ROLL_PATHS_REFUSED missing ROLL_OUT (no receipt path: nothing written)", flush=True)
    sys.exit(3)
_KEYS = ("V4_MONTH_ENV", "ROLL_PREV_MONTH_ENV")
E = {k: os.environ.get(k, "") for k in _KEYS}
INPUTS = {"month_env": E["V4_MONTH_ENV"] or None, "prev_month_env": E["ROLL_PREV_MONTH_ENV"] or None}
_ref = {}
if [k for k in _KEYS if not E[k]]:
    _ref["missing_env"] = [k for k in _KEYS if not E[k]]
_miss = {k: v for k, v in INPUTS.items() if not v or not os.path.isfile(v)}
if _miss:
    _ref["missing_files"] = _miss
if _ref:
    print("ROLL_PATHS_REFUSED", json.dumps(_ref), flush=True)
    finalize("ROLL_PATHS", {"PASS": False, "REFUSED": _ref}, _OUT, INPUTS)

ALLOW = [k for k in os.environ.get("ROLL_ALLOW_OUTSIDE_ROOT", "").split(",") if k]
PREV_SHA = os.environ.get("ROLL_PREV_SHA_JSON", "")
t0 = time.time()


def read_env(path):
    """{KEY: raw value} from a month contract, read as DATA — never sourced, never executed (chain_lib's D3 rule). Values are
    returned with $R / ${R} expanded from the file's own R, because that is how the driver will see them."""
    kv = {}
    for line in open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _KEYRE.match(s)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if "R" in kv:
            v = v.replace("${R}", kv["R"]).replace("$R", kv["R"])
        kv[k] = v
    return kv


cur, prev = read_env(E["V4_MONTH_ENV"]), read_env(E["ROLL_PREV_MONTH_ENV"])
checks, fails = {}, []


def chk(name, ok, detail):
    checks[name] = dict(detail, ok=bool(ok))
    if not ok:
        fails.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + " " + json.dumps(detail, default=str)[:400], flush=True)


unevaluated = []


def note_unevaluated(name, detail):
    """★★★ R16-T1 (独立复审 2026-09-16): 「没能评估」不是「通过」。
    旧码在 ROLL_PREV_SHA_JSON 缺席时调 `chk(name, True, {...NOT_EVALUABLE..., "evaluated": False})` ——
    一边写着未评估, 一边记 ok=True 从而不进 `fails`, 总判词仍是 PASS。于是可以拿一个
    「前月工件根本没查」的 PASS 去宣称「前月工件未变」。三态从此分开: PASS / FAIL / UNAVAILABLE。"""
    checks[name] = dict(detail, ok=None, evaluated=False)
    unevaluated.append(name)
    print("  UNAVAIL " + name + " " + json.dumps(detail, default=str)[:400], flush=True)


missing_keys = [k for k in ROLLED if k not in cur]
prev_missing = [k for k in ROLLED if k not in prev]
if missing_keys or prev_missing:
    chk("P0_rolled_keys_present", False,
        {"absent_in_month_contract": missing_keys, "absent_in_previous_contract": prev_missing,
         "why": "a rolled key that is not in the contract cannot be checked, and an unchecked key is the one that gets reused"})
else:
    chk("P0_rolled_keys_present", True, {"n_rolled": len(ROLLED)})

# P0b — a ROLLED key that is present but EMPTY is not a path that can be checked (R16RF-T1, 独立复审第三轮 2026-09-17):
#   P0 only asked whether the key exists, and P4 built its required set with `if prev.get(k)`, so `CACHE=` in the previous
#   contract silently shrank "8 artifacts must be verified" to 7 — and 8 blanks to 0, where a record over one unrelated file
#   PASSED. A blank value is refused BY NAME, in either contract, before any coverage is built; nothing downstream may
#   shrink the required set.
_blank_cur = [k for k in ROLLED if k in cur and not str(cur[k]).strip()]
_blank_prev = [k for k in ROLLED if k in prev and not str(prev[k]).strip()]
chk("P0b_rolled_values_nonempty", not (_blank_cur or _blank_prev),
    {"blank_in_month_contract": _blank_cur, "blank_in_previous_contract": _blank_prev,
     "why": "an empty rolled path cannot be located, hashed or compared; leaving it out of the required set is how a "
            "7-of-8 (or 0-of-8) check reports PASS (R16RF-T1)"})

# P1 — same key, same path
p1 = [{"key": k, "value": cur[k], "previous_month_value": prev[k]}
      for k in ROLLED if k in cur and k in prev and cur[k] and cur[k] == prev[k]]     # blanks are P0b's finding, not P1's
chk("P1_rolled_keys_differ", not p1,
    {"violations": p1, "why": "a rolled key still pointing at the previous month's artifact means this month either reads stale "
                              "data or overwrites a file the previous month's receipts hash (E-0912-B)"})

# P2 — this month's rolled value is some OTHER key of the previous contract
prev_by_value = {}
for k, v in prev.items():
    prev_by_value.setdefault(v, []).append(k)
p2 = [{"key": k, "value": cur[k], "is_previous_month": sorted(prev_by_value[cur[k]])}
      for k in ROLLED if k in cur and cur[k] and cur[k] in prev_by_value and cur[k] != cur.get("R", object())]
p2 = [v for v in p2 if v["is_previous_month"] != [v["key"]]]        # the same-key case is P1's to report, not P2's
chk("P2_no_cross_key_reuse", not p2,
    {"violations": p2, "why": "the improvisation is not only 'same key, same path': a month whose CACHE is the previous month's "
                              "PANEL, or whose FUND_AUG is the previous month's EMA_STATE_JSON, is the same failure"})

# P3 — rolled products live under this month's root
root = cur.get("R", "")
# ★★★ R16-T1: 旧码只做**词法**前缀比较 —— 本月根下挂一个指向上月文件的符号链接就能过,
#   而它自称保证的是「本月产物不指向上月工件」。复审实跑: 直接引用上月 CACHE 返回 3/FAIL,
#   把本月根下的 alias 链到同一个上月 CACHE 则返回 0/PASS 且 samefile=True。
#   ⇒ 前缀比较改在 **realpath 解析后**做(realpath 会展开每一段符号链接与 `..`)。
def _real(x):
    try:
        return os.path.realpath(x)
    except OSError:
        return x
_root_real = _real(root) if root else ""
p3 = []
for k in ROLLED:
    if k not in cur or k in ALLOW or not cur[k]:      # a blank value is refused by P0b; realpath("") would be the cwd
        continue
    _v_real = _real(cur[k])
    lex_ok = bool(root) and (cur[k] == root or cur[k].startswith(root.rstrip("/") + "/"))
    real_ok = bool(_root_real) and (_v_real == _root_real or _v_real.startswith(_root_real.rstrip("/") + "/"))
    if not real_ok:
        p3.append({"key": k, "value": cur[k], "realpath": _v_real, "R": root or None, "R_realpath": _root_real or None,
                   "lexically_inside": lex_ok,
                   "note": ("LEXICALLY inside the month root but its REAL path is not — a symlink/alias points out of "
                            "the month" if lex_ok else "outside the month root")})
chk("P3_rolled_under_root", not p3 and bool(root),
    {"violations": p3, "R": root or None, "R_realpath": _root_real or None, "declared_exceptions": ALLOW,
     "why": "the month's products belong inside the month's root; containment is tested on REALPATH, not on the "
            "string, because a lexical test passes an alias that resolves to last month (R16-T1)"})

# P6 — 别名: 本月的值与上月某个值是**同一个文件**(symlink / hardlink / bind), 词法上看不出来
p6 = []
for k in ROLLED:
    # ★ R16R-T1b: 上一轮这里也跳过了 ROLL_ALLOW_OUTSIDE_ROOT —— 那份名单豁免的是**位置**(WHERE), 从来不豁免
    #   **引用上月工件**(WHOSE); 原 Q3 明写「WHERE, never WHOSE」, P1/P2 也没有对应的身份豁免。
    #   复审实跑: CACHE=新根/alias → 旧月 CACHE, 再设 ROLL_ALLOW_OUTSIDE_ROOT=CACHE, samefile=True 却 PASS 0。
    #   ⇒ P6 对每一个 ROLLED 键都查, 与 ALLOW 无关。跨月共享若真有需要, 另立具名只读、内容钉住的共享合同。
    if k not in cur:
        continue
    for pk, pv in sorted(prev.items()):
        if not isinstance(pv, str) or not pv:
            continue
        try:
            same = os.path.exists(cur[k]) and os.path.exists(pv) and os.path.samefile(cur[k], pv)
        except OSError:
            same = False
        if same:
            p6.append({"key": k, "value": cur[k], "previous_key": pk, "previous_value": pv,
                       "realpath": _real(cur[k]), "samefile": True})
chk("P6_no_alias_to_previous_month", not p6,
    {"violations": p6,
     "why": "a path that differs as a string but is the SAME FILE as a previous-month artifact is the same failure P1/P2 "
            "name; only os.path.samefile can see it (R16-T1)"})

# P4 — the previous month's artifacts are still what its receipts say they are
if not PREV_SHA:
    note_unevaluated("P4_previous_untouched",
        {"NOT_EVALUABLE": "ROLL_PREV_SHA_JSON not supplied: this gate can compare paths, but proving the PREVIOUS month's files "
                          "are unchanged needs the record of what they hashed to. Supply it to turn this into a real check.",
         "why_not_ok": "R16-T1: an unevaluated check is NOT a passed check; the overall verdict is UNAVAILABLE, not PASS"})
elif not os.path.isfile(PREV_SHA):
    chk("P4_previous_untouched", False, {"why": f"ROLL_PREV_SHA_JSON={PREV_SHA} does not exist", "evaluated": False})
else:
    try:
        rec = json.load(open(PREV_SHA))
        # ★ R16R-T1a: 上一轮 `rec if isinstance(rec, dict) else {}` 把 [] 转成 {}, 而 {} 让下面的循环一个文件都不核,
        #   `moved` 为空 ⇒ `not moved` 为 True ⇒ **n_checked=0 却 PASS rc0**。空文件内容不等于有证据。
        #   ⇒ 先验记录 schema: 必须是非空 dict, 每个值都是 64 位十六进制 sha; 再验**覆盖**: 上月合同里每个
        #     ROLLED 工件路径都必须在记录里 —— 一条无关文件的 sha 不能证明上月合同。三者任一不满足 = FAIL
        #     (给了记录却是废的, 比没给更糟, 不是 UNAVAILABLE)。
        _hex = re.compile(r"^[0-9a-f]{64}$")
        _schema_bad = []
        if not isinstance(rec, dict) or not rec:
            _schema_bad.append(f"record is {type(rec).__name__} with {len(rec) if hasattr(rec, '__len__') else '?'} entries — a previous-month record must be a NON-EMPTY {{path: sha256}} map")
        else:
            _schema_bad += [f"{p!r}: value is not a sha256 hex string" for p, w in rec.items() if not (isinstance(w, str) and _hex.match(w))]
        # ★ R16RF-T1: the required set is EVERY rolled key of the previous contract — a blank/missing value stays in it
        #   (as "") and can never be covered, so a shrunken contract cannot certify itself.
        #   Coverage is counted BY KEY: every one of the previous contract's rolled keys must carry a non-blank path that is
        #   in the record. (A set of values would collapse eight blanks to one and mis-state the size of what was skipped.)
        _need_by_key = {k: (prev.get(k) if isinstance(prev.get(k), str) else "") for k in ROLLED}
        _need = sorted({v for v in _need_by_key.values() if v})                       # the distinct paths that CAN be hashed
        _uncovered_keys = sorted(k for k, v in _need_by_key.items() if not v or not (isinstance(rec, dict) and v in rec))
        _uncovered = [p for p in _need if not (isinstance(rec, dict) and p in rec)]
        if _schema_bad or _uncovered or _uncovered_keys:
            chk("P4_previous_untouched", False,
                {"schema_errors": _schema_bad[:10], "previous_rolled_paths_not_in_record": _uncovered,
                 "previous_rolled_keys_not_in_record": _uncovered_keys, "n_required_keys": len(ROLLED), "n_required": len(_need),
                 "evaluated": True,
                 "why": "the record cannot certify the previous month: it is empty, malformed, or does not cover the "
                        "previous contract's ROLLED artifacts — a check over zero or unrelated files is not evidence (R16R-T1a)"})
        else:
            moved, checked, absent = [], 0, []
            for p, want in sorted(rec.items()):
                if not os.path.isfile(p):
                    absent.append(p)
                    continue
                got = sha256_file(p)
                checked += 1
                if got != want:
                    moved.append({"path": p, "recorded": want[:16], "now": got[:16]})
            _absent_required = [p for p in _need if p in absent]
            chk("P4_previous_untouched", not moved and not _absent_required,
                {"n_checked": checked, "n_required": len(_need), "n_absent_now": len(absent), "absent": absent[:20],
                 "absent_required": _absent_required, "moved": moved, "evaluated": True,
                 "why": "a previous-month artifact whose sha moved means something already overwrote it; a required "
                        "artifact that is now absent cannot be certified either"})
    except Exception as e:                                        # noqa: BLE001
        chk("P4_previous_untouched", False, {"why": f"ROLL_PREV_SHA_JSON unreadable: {type(e).__name__}: {e}", "evaluated": False})

# P5 — no '..' component anywhere in the month contract (FXR-TRN-1 family)
p5 = [{"key": k, "value": v} for k, v in sorted(cur.items()) if "/../" in f"/{v}/"]
chk("P5_no_parent_escape", not p5,
    {"violations": p5, "why": "a '..' component makes every containment test above lexical-only (FXR-TRN-1)"})

_verdict = "FAIL" if fails else ("UNAVAILABLE" if unevaluated else "PASS")
res = {"PASS": (_verdict == "PASS"), "VERDICT": _verdict, "unevaluated_checks": unevaluated,
       "failed_checks": fails, "checks": checks,
       "month_env": E["V4_MONTH_ENV"], "prev_month_env": E["ROLL_PREV_MONTH_ENV"],
       "v4_month": cur.get("V4_MONTH"), "previous_v4_month": prev.get("V4_MONTH"), "R": root or None,
       "rolled_keys": list(ROLLED), "rolled_values": {k: cur.get(k) for k in ROLLED},
       "declared_exceptions_outside_root": ALLOW, "prev_sha_record": PREV_SHA or None,
       "wall_s": round(time.time() - t0, 1), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print("ROLL_PATHS", _verdict,
      json.dumps({"month": res["v4_month"], "previous": res["previous_v4_month"],
                  "failed": fails, "unevaluated": unevaluated}), flush=True)
finalize("ROLL_PATHS", res, _OUT, INPUTS)
