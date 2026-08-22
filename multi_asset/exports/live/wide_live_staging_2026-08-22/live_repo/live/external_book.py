"""external_book — the "external book" adapter (DESIGN_wide_live_deployment_2026-08-22 §1).

WHAT IT IS
    With `config/book.json["book_source"] == "external"` the anchor's target vector is no longer
    composed in-process (king/s2/funding -> compose_book -> EMA -> band); it is READ from a signed
    target file that the wide-book producer (~/wide_shadow/shadow_loop_v2.py, keyless) writes
    once per anchor:  <path>/<anchor_ts>.json  +  <anchor_ts>.json.sha256.
    This module owns everything about that file: config validation, the wait for the producer's
    slot, the read + verification, the age that feeds the staleness ladder, the per-name
    filters that the design KEEPS (venue eligibility, 2x min-notional), and the records.

WHAT IT REFUSES (all fail-CLOSED; none of these ever trades on a guess)
    · any validation failure  -> the anchor HOLDS (no orders) + HIGH alarm naming the reason;
    · it NEVER falls back to the internal composer — "external unavailable" and "internal" are
      two different books and a silent substitution would trade the retired one;
    · an unknown `book_source` value, or an external block that fails validation, is INVALID and
      the anchor is blocked (a typo must not select a book);
    · gross_mult above config target_leverage is refused at config time: §4-4b reads
      target_leverage as the leverage policy, so a larger external gross would be a halt by
      construction, and that disagreement must be settled in config, not discovered by a trip.

WHAT IT DOES NOT DO (stated so nobody infers it from the module's existence)
    · it does not apply EMA / neutral band / risk budget — the producer's weights ARE the target
      (design §1; W2b measured that the mixed-scale composition pipeline loses); the existing
      withhold -> reshape (re-demean / rescale) and the clamp/flatten_only channel still run in
      anchor_loop because those are VENUE facts, not book composition;
    · it does not read the venue — `venue_meta_exclusions` is a pure function over an
      exchangeInfo payload the caller fetched; `read_target` touches only the local file system;
    · it does not decide the ladder — it computes an AGE and anchor_loop's pre-registered
      `staleness_action` decides, exactly as for preds (anchor_loop docstring, "THE STALE-SIGNAL
      LADDER"); with `on_unavailable: "hold"` the first rung is pinned and nothing escalates.

FILE CONTRACT (schema `wide_target_v1`, produced by shadow_loop_v2.write_target_live)
    {"schema": "wide_target_v1", "anchor_ts": <int epoch s, the NOMINAL 4h anchor>,
     "weights": {SYM: w, ...}  (non-zero only; signed; sum|w| == gross_norm),
     "gross_norm": float, "n_names": int, "universe_sha": sha256 hex of the producer's
     symbols_live list (see `universe_sha` for the exact recipe — both sides use this function's
     definition), "booster_sha": str, "weights_sha": sha256 hex of the producer's weights npz,
     "written_utc": "%Y-%m-%dT%H:%M:%SZ", "producer": str}
    sidecar: "<sha256 hex of the json bytes>  <basename>\n"  (shasum -c compatible).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional

import book_config as BC

SCHEMA = "wide_target_v1"
SOURCES = ("internal", "external")
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
# design §2: L3 is 2.5x "上限"; anything above is not a level that exists.
GROSS_MULT_MAX = 2.5
# retryable = the producer may simply not have finished (missing / half-written / sidecar race);
# everything else is a fact about the file that a second read cannot change.
RETRYABLE = ("missing", "sidecar_missing", "sha_mismatch", "bad_json")
_LEVERAGED_TOKEN = re.compile(r"\d+[LS]USDT$")          # e.g. ETH3LUSDT — probe v2's static rule
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

DEFAULTS = {
    "max_age_min": 10.0,
    "anchor_offset_min": 8.0,
    "poll_grace_min": 0.0,
    "gross_mult": 1.0,
    "require_anchor_match": True,
    "universe_sha_pin": None,
    "booster_sha_pin": None,
    "min_notional_mult": 2.0,
    "on_unavailable": "ladder",
    "schema": SCHEMA,
}


# ── config ───────────────────────────────────────────────────────────────────────────────────────
def config(book: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve `book_source` + `external_book` into ONE validated dict. Pure.

    Returns {"source": "internal" | "external" | "INVALID", "error": str|None, ...fields}.
    · key absent, or == "internal"  -> internal (today's behaviour, byte for byte)
    · == "external"                 -> the block is validated; any defect -> INVALID
    · anything else / unreadable     -> INVALID. A value that is not one of the two names must
      not pick a book — not the old one, not the new one.
    """
    out: Dict[str, Any] = {"source": "internal", "error": None, "path": None}
    out.update(DEFAULTS)
    if not isinstance(book, dict):
        out.update(source="INVALID", error="config unreadable (not a dict) — book source unknown")
        return out
    src = book.get("book_source", "internal")
    if src == "internal":
        return out
    if src != "external":
        out.update(source="INVALID", error=f"book_source={src!r} is not one of {SOURCES}")
        return out
    eb = book.get("external_book")
    if not isinstance(eb, dict):
        out.update(source="INVALID", error="book_source=external but `external_book` block is missing")
        return out
    errs: List[str] = []
    path = eb.get("path")
    if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
        errs.append(f"path must be an absolute directory path, got {path!r}")
    def _num(key, lo, hi, default):
        v = eb.get(key, default)
        try:
            f = float(v)
        except (TypeError, ValueError):
            errs.append(f"{key} not a number: {v!r}")
            return default
        if not (lo <= f <= hi) or math.isnan(f):
            errs.append(f"{key}={f} outside [{lo}, {hi}]")
        return f
    max_age = _num("max_age_min", 0.5, 240.0, DEFAULTS["max_age_min"])
    offset = _num("anchor_offset_min", 0.0, 120.0, DEFAULTS["anchor_offset_min"])
    grace = _num("poll_grace_min", 0.0, 30.0, DEFAULTS["poll_grace_min"])
    gm = _num("gross_mult", 1e-9, GROSS_MULT_MAX, DEFAULTS["gross_mult"])
    mnm = _num("min_notional_mult", 0.0, 100.0, DEFAULTS["min_notional_mult"])
    # §4-4b reads config target_leverage as the leverage policy; an external gross above it is a
    # halt by construction (LEVERAGE_HALT_MULT applies to THAT number). Settle it in config.
    try:
        tl = float(book.get("target_leverage") or 0.0)
    except (TypeError, ValueError):
        tl = 0.0
    if tl > 0 and gm > tl + 1e-12:
        errs.append(f"gross_mult={gm} exceeds config target_leverage={tl}; raise target_leverage "
                    f"deliberately (it is the §4-4b leverage policy) or lower gross_mult")
    ram = eb.get("require_anchor_match", True)
    if not isinstance(ram, bool):
        errs.append(f"require_anchor_match must be a bool, got {ram!r}")
    pin_u = eb.get("universe_sha_pin")
    if pin_u is not None and not (isinstance(pin_u, str) and _HEX64.match(pin_u)):
        errs.append("universe_sha_pin must be null or a 64-hex sha256")
    pin_b = eb.get("booster_sha_pin")
    if pin_b is not None and not (isinstance(pin_b, str) and pin_b):
        errs.append("booster_sha_pin must be null or a non-empty string")
    onu = eb.get("on_unavailable", DEFAULTS["on_unavailable"])
    if onu not in ("ladder", "hold"):
        errs.append(f"on_unavailable={onu!r} not in ('ladder', 'hold')")
    schema = eb.get("schema", SCHEMA)
    if not isinstance(schema, str) or not schema:
        errs.append("schema must be a non-empty string")
    if errs:
        out.update(source="INVALID", error="; ".join(errs))
        return out
    out.update(source="external", path=path, max_age_min=max_age, anchor_offset_min=offset,
               poll_grace_min=grace, gross_mult=gm, require_anchor_match=ram,
               universe_sha_pin=pin_u, booster_sha_pin=pin_b, min_notional_mult=mnm,
               on_unavailable=onu, schema=schema)
    return out


def pns_profile_consistent(book: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The coupling rule: book_source=external  <=>  per_name_stop.active_profile == 'wide'.

    Two keys, one decision (design §1: the wide book carries the wide stop layer d30_n2_c42). They
    are separate keys so each is independently revertible and visible; this predicate is what
    stops one being flipped without the other. Pure; consumed by tests_external_book and by the
    anchor (HIGH alarm, not a block — the stop clause still runs on SOME profile either way).
    """
    if not isinstance(book, dict):
        return {"ok": False, "why": "config unreadable"}
    src = book.get("book_source", "internal")
    prof = (book.get("per_name_stop") or {}).get("active_profile")
    if src == "external" and prof != "wide":
        return {"ok": False, "why": f"book_source=external but per_name_stop.active_profile={prof!r} "
                                    f"(expected 'wide': depth -0.30 x 2 anchors x 7d)"}
    if src == "internal" and prof is not None:
        return {"ok": False, "why": f"book_source=internal but per_name_stop.active_profile={prof!r} "
                                    f"(expected null: the base parameters)"}
    return {"ok": True, "why": ""}


# ── the shared recipe for universe_sha (producer AND consumer import this definition) ───────────
def universe_sha(symbols: List[str]) -> str:
    """sha256 of the producer's symbols_live list, ORDER-PRESERVING, compact JSON. One recipe —
    shadow_loop_v2 stamps it, this side pins/records it; tests_target_live_output asserts both
    sides agree on a fixture so the recipe cannot drift on one side only."""
    return hashlib.sha256(json.dumps(list(symbols), separators=(",", ":")).encode()).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ── timing ───────────────────────────────────────────────────────────────────────────────────────
def nominal_anchor_ts(now: float) -> int:
    """The NOMINAL 4h anchor this run belongs to — the nearest scheduled slot (book_config's
    single definition, same as the off-schedule gate and the king cadence key)."""
    return int(round(BC.nominal_anchor_utc(float(now))))


def wait_plan(cfg: Dict[str, Any], now: float) -> Dict[str, Any]:
    """How long to sleep before reading, or 0. Pure.

    We wait ONLY when `now` lies inside [slot, slot + offset] of the nearest slot — i.e. this is
    the scheduled run that started at N+0 and the producer lands at N+offset. A run that is
    already past the offset reads immediately; a run nowhere near a slot (tests, manual runs two
    hours in) never sleeps. The upper bound is offset + 60s so a process that starts a few
    seconds BEFORE the minute still waits the whole way rather than skipping to a missing file.
    """
    nominal = nominal_anchor_ts(now)
    wake = nominal + float(cfg["anchor_offset_min"]) * 60.0
    wait = wake - float(now)
    if 0.0 < wait <= float(cfg["anchor_offset_min"]) * 60.0 + 60.0:
        return {"nominal_anchor_ts": nominal, "wake_at": wake, "wait_s": round(wait, 1),
                "reason": "inside the slot's pre-window: wait for the producer"}
    return {"nominal_anchor_ts": nominal, "wake_at": wake, "wait_s": 0.0,
            "reason": ("already past the producer's offset" if wait <= 0
                       else "not inside a slot pre-window (manual/test run) — no wait")}


def wait_for_slot(cfg: Dict[str, Any], now: float, sleep=time.sleep, clock=time.time,
                  max_wait_s: Optional[float] = None) -> Dict[str, Any]:
    """Sleep per `wait_plan`, in small slices so a KILL file / signal can interrupt. Returns the
    plan + `slept_s`. `LIVE_EXTERNAL_WAIT=0` disables the sleep (manual runs; the battery)."""
    plan = wait_plan(cfg, now)
    plan["slept_s"] = 0.0
    plan["disabled_by_env"] = os.environ.get("LIVE_EXTERNAL_WAIT", "1") == "0"
    if plan["disabled_by_env"] or plan["wait_s"] <= 0:
        return plan
    budget = float(plan["wait_s"]) if max_wait_s is None else min(float(plan["wait_s"]), float(max_wait_s))
    t0 = clock()
    while True:
        left = budget - (clock() - t0)
        if left <= 0:
            break
        sleep(min(30.0, left))
    plan["slept_s"] = round(clock() - t0, 1)
    return plan


# ── the read ─────────────────────────────────────────────────────────────────────────────────────
def _err(reason: str, detail: str = "", **kw) -> Dict[str, Any]:
    d = {"ok": False, "reason": reason, "detail": detail, "retryable": reason in RETRYABLE}
    d.update(kw)
    return d


def verify_file(path: str) -> Dict[str, Any]:
    """Read <path> and <path>.sha256; return {"ok", "raw", "sha", "reason"...}. No JSON yet."""
    if not os.path.exists(path):
        return _err("missing", f"no target file at {path}")
    side = path + ".sha256"
    if not os.path.exists(side):
        return _err("sidecar_missing", f"no {os.path.basename(side)} beside the target")
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        with open(side, "r") as fh:
            want = fh.read().strip().split()[0].lower() if fh else ""
    except Exception as e:                           # noqa: BLE001 — any read failure = unreadable
        return _err("missing", f"unreadable: {type(e).__name__}: {str(e)[:80]}")
    got = sha256_bytes(raw)
    if not _HEX64.match(want or ""):
        return _err("sha_mismatch", f"sidecar does not carry a sha256 ({want[:20]!r})")
    if got != want:
        return _err("sha_mismatch", f"sha256(json)={got[:12]}… sidecar={want[:12]}…")
    return {"ok": True, "raw": raw, "sha": got}


def _parse_utc(s: Any) -> Optional[float]:
    try:
        import calendar
        return float(calendar.timegm(time.strptime(str(s), UTC_FMT)))
    except Exception:                                # noqa: BLE001
        return None


def parse_target(raw: bytes, cfg: Dict[str, Any], nominal_ts: int, now: float) -> Dict[str, Any]:
    """Validate the JSON payload against the contract + the caller's expectations. Pure."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as e:                           # noqa: BLE001
        return _err("bad_json", f"{type(e).__name__}: {str(e)[:80]}")
    if not isinstance(doc, dict):
        return _err("schema", "payload is not a JSON object")
    if doc.get("schema") != cfg["schema"]:
        return _err("schema", f"schema={doc.get('schema')!r}, expected {cfg['schema']!r}")
    # required fields + types
    w = doc.get("weights")
    if not isinstance(w, dict) or not w:
        return _err("schema", "weights must be a non-empty object {symbol: weight}")
    try:
        ats = int(doc.get("anchor_ts"))
    except (TypeError, ValueError):
        return _err("schema", f"anchor_ts not an int: {doc.get('anchor_ts')!r}")
    for k in ("universe_sha", "booster_sha", "weights_sha", "written_utc"):
        if not isinstance(doc.get(k), str) or not doc.get(k):
            return _err("schema", f"{k} missing or not a string")
    if not _HEX64.match(doc["universe_sha"]) or not _HEX64.match(doc["weights_sha"]):
        return _err("schema", "universe_sha / weights_sha must be 64-hex sha256")
    try:
        gn = float(doc.get("gross_norm"))
    except (TypeError, ValueError):
        return _err("schema", f"gross_norm not a number: {doc.get('gross_norm')!r}")
    if not (gn > 0) or math.isnan(gn) or math.isinf(gn):
        return _err("schema", f"gross_norm={gn} must be > 0 and finite")
    clean: Dict[str, float] = {}
    for s, v in w.items():
        if not isinstance(s, str) or not s:
            return _err("bad_weights", f"symbol key {s!r} is not a non-empty string")
        try:
            f = float(v)
        except (TypeError, ValueError):
            return _err("bad_weights", f"{s}: weight {v!r} not a number")
        if math.isnan(f) or math.isinf(f):
            return _err("bad_weights", f"{s}: weight {f} not finite")
        if f != 0.0:
            clean[s] = f
    if not clean:
        return _err("bad_weights", "all weights are zero")
    n_decl = doc.get("n_names")
    if n_decl is not None and int(n_decl) != len(w):
        return _err("schema", f"n_names={n_decl} but weights has {len(w)} entries")
    s_abs = float(sum(abs(v) for v in clean.values()))
    if abs(s_abs - gn) > 1e-6 * max(gn, 1.0):
        return _err("gross_norm_mismatch", f"sum|w|={s_abs:.9f} != gross_norm={gn:.9f}")
    # anchor identity
    if cfg["require_anchor_match"] and ats != int(nominal_ts):
        return _err("anchor_mismatch", f"file anchor_ts={ats} != this anchor {int(nominal_ts)}")
    # freshness
    wts = _parse_utc(doc["written_utc"])
    if wts is None:
        return _err("schema", f"written_utc unparseable: {doc['written_utc']!r}")
    age_s = float(now) - wts
    if age_s > float(cfg["max_age_min"]) * 60.0:
        return _err("stale", f"written {age_s / 60.0:.1f} min ago > max_age_min={cfg['max_age_min']}")
    if age_s < -120.0:
        return _err("stale", f"written_utc is {-age_s / 60.0:.1f} min in the FUTURE — clock skew")
    # pins
    if cfg.get("universe_sha_pin") and doc["universe_sha"] != cfg["universe_sha_pin"]:
        return _err("universe_pin", f"universe_sha {doc['universe_sha'][:12]}… != pin "
                                    f"{str(cfg['universe_sha_pin'])[:12]}…")
    if cfg.get("booster_sha_pin") and doc["booster_sha"] != cfg["booster_sha_pin"]:
        return _err("booster_pin", f"booster_sha {doc['booster_sha'][:12]}… != pin "
                                   f"{str(cfg['booster_sha_pin'])[:12]}…")
    return {"ok": True, "reason": None, "detail": "", "retryable": False, "schema": doc["schema"],
            "anchor_ts": ats, "w": clean, "symbols": sorted(clean), "n_names": len(clean),
            "gross_norm": gn, "universe_sha": doc["universe_sha"], "booster_sha": doc["booster_sha"],
            "weights_sha": doc["weights_sha"], "written_utc": doc["written_utc"],
            "age_s": round(age_s, 1), "producer": doc.get("producer"),
            "n_universe": doc.get("n_universe")}


def read_target(cfg: Dict[str, Any], now: float, nominal_ts: Optional[int] = None,
                poll: bool = False, sleep=time.sleep, clock=time.time) -> Dict[str, Any]:
    """Read + verify this anchor's target. Never raises; `ok` False carries `reason`/`detail`.

    poll=True: retry the RETRYABLE outcomes every ~15s until now + poll_grace_min — the producer
    lands a few minutes into the slot and its write is two renames; a single read at exactly the
    wrong second must not cost an anchor. Non-retryable outcomes return at once.
    """
    nominal = int(nominal_ts if nominal_ts is not None else nominal_anchor_ts(now))
    path = os.path.join(str(cfg["path"]), f"{nominal}.json")
    # ★ ONE clock for freshness: the caller's `now`, advanced by the time this poll has spent.
    #   (A test injects `now`; production passes time.time(). Mixing the two calibers — caller's
    #   `now` for the deadline, wall clock for the age — read a fresh fixture as stale.)
    t0 = clock()
    deadline = float(now) + (float(cfg["poll_grace_min"]) * 60.0 if poll else 0.0)
    attempts = 0
    while True:
        attempts += 1
        vf = verify_file(path)
        if vf["ok"]:
            ext = parse_target(vf["raw"], cfg, nominal, float(now) + (clock() - t0))
            ext["sha_ok"] = True
            ext["json_sha"] = vf["sha"]
        else:
            ext = dict(vf)
            ext.pop("raw", None)
            ext["sha_ok"] = vf["reason"] not in ("sha_mismatch", "sidecar_missing")
        ext.update({"path": path, "nominal_ts": nominal, "attempts": attempts,
                    "gross_mult": cfg["gross_mult"], "min_notional_mult": cfg["min_notional_mult"]})
        now_eff = float(now) + (clock() - t0)
        if ext["ok"] or not ext.get("retryable") or now_eff >= deadline:
            return ext
        sleep(min(15.0, max(1.0, deadline - now_eff)))


# ── age for the ladder ───────────────────────────────────────────────────────────────────────────
def newest_verified_anchor_ts(cfg: Dict[str, Any]) -> Optional[int]:
    """The newest file in the producer's directory whose sidecar verifies. Used only as the
    cold-start reference for the ladder's age when loop state carries no last-good record."""
    try:
        names = [n for n in os.listdir(str(cfg["path"])) if re.fullmatch(r"\d+\.json", n)]
    except Exception:                                # noqa: BLE001
        return None
    for n in sorted(names, key=lambda x: int(x[:-5]), reverse=True)[:3]:
        if verify_file(os.path.join(str(cfg["path"]), n))["ok"]:
            return int(n[:-5])
    return None


def age_anchors(ext: Dict[str, Any], cfg: Dict[str, Any], state: Dict[str, Any], now: float,
                anchor_s: float) -> Dict[str, Any]:
    """Age of the newest USABLE external signal, in anchors — the quantity anchor_loop's
    pre-registered staleness ladder consumes. ok -> this file's anchor; else the last good
    anchor recorded in loop state, else the newest verified file on disk, else inf."""
    if ext.get("ok"):
        ref, src = int(ext["anchor_ts"]), "this_file"
    else:
        lg = (state or {}).get("external_last_good_anchor_ts")
        nv = newest_verified_anchor_ts(cfg)
        cands = [(int(lg), "loop_state_last_good")] if lg else []
        if nv is not None:
            cands.append((nv, "newest_verified_file"))
        if cands:
            ref, src = max(cands)
        else:
            return {"age_anchors": float("inf"), "ref_anchor_ts": None, "ref_source": "none"}
    return {"age_anchors": max(0.0, (float(now) - ref) / float(anchor_s)), "ref_anchor_ts": ref,
            "ref_source": src}


# ── the vector and the two KEPT per-name filters ────────────────────────────────────────────────
def target_vector(ext: Dict[str, Any], symbols: List[str]):
    """w / gross_norm aligned to `symbols` — sum|.| == 1 so `to_notional(. , gross)` gives a book
    whose gross is exactly the sizing gross (design: target = w/gross_norm x NAV x gross_mult)."""
    import numpy as np
    gn = float(ext["gross_norm"])
    return np.array([float(ext["w"].get(s, 0.0)) / gn for s in symbols], dtype=float)


def below_min_notional(target: Dict[str, float], floors: Optional[Dict[str, float]],
                       mult: float) -> Dict[str, Any]:
    """Names whose |target| < mult x venue min_notional. The design's eligibility filter
    ("最小名义额可达 NAV×gross/名 ≥ 2×minNotional"): a position that cannot clear twice its floor
    cannot be ADJUSTED later (every delta lands under the floor), so it is withheld at planning —
    through the existing untradable channel (pop if unheld, clamp if held: reduce-only, never
    opened). floors None -> NOT CHECKED (reported as such, never as 'none below')."""
    if floors is None:
        return {"checked": False, "names": set(), "n": 0, "mass_frac": None,
                "note": "floors unavailable — min-notional eligibility NOT checked"}
    gross = float(sum(abs(v) for v in target.values())) or 1.0
    names = {s for s, v in target.items()
             if abs(float(v)) < float(mult) * float((floors or {}).get(s, 0.0) or 0.0)}
    mass = float(sum(abs(float(target[s])) for s in names)) / gross
    return {"checked": True, "names": names, "n": len(names), "mass_frac": round(mass, 6),
            "mult": float(mult)}


def venue_meta_exclusions(exinfo_symbols: List[Dict[str, Any]], names: List[str]) -> Dict[str, str]:
    """{symbol: reason} for names the wide book must not OPEN — probe v2's data-driven rule
    (exec_probe.symbol_meta_reason) plus its static ASCII/USDT/leveraged-token rule. Pure.
    The in-role universe gate (universe.classify) knows only `status`; the design asks for
    'COIN perp, non-ASCII / equity-token names excluded', which needs underlyingType."""
    meta = {s.get("symbol"): s for s in (exinfo_symbols or []) if isinstance(s, dict)}
    out: Dict[str, str] = {}
    for s in names:
        if not isinstance(s, str) or not s.isascii():
            out[str(s)] = "non_ascii"; continue
        if not s.endswith("USDT"):
            out[s] = "not_usdt"; continue
        if _LEVERAGED_TOKEN.search(s):
            out[s] = "leveraged_token"; continue
        m = meta.get(s)
        if m is None:
            out[s] = "not_in_exchangeInfo"; continue
        if m.get("underlyingType", "COIN") != "COIN":
            out[s] = f"underlyingType={m.get('underlyingType')}"; continue
        if m.get("contractType", "PERPETUAL") != "PERPETUAL":
            out[s] = f"contractType={m.get('contractType')}"; continue
        if m.get("status", "TRADING") != "TRADING":
            out[s] = f"status={m.get('status')}"; continue
    return out


# ── records and words ────────────────────────────────────────────────────────────────────────────
def record(ext: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The compact per-anchor record (no weights): what was read, whether it verified, why not."""
    keys = ("ok", "reason", "detail", "path", "nominal_ts", "anchor_ts", "attempts", "n_names",
            "gross_norm", "gross_mult", "universe_sha", "booster_sha", "weights_sha", "json_sha",
            "written_utc", "age_s", "sha_ok", "producer", "n_universe")
    r = {k: ext.get(k) for k in keys if k in ext}
    if extra:
        r.update(extra)
    return r


def unavailable_text(ext: Dict[str, Any], action: str) -> str:
    return (f"external_book_unavailable: {ext.get('reason')} — {ext.get('detail')}. "
            f"path={ext.get('path')} attempts={ext.get('attempts')}. "
            f"本锚 {action}: 保持现仓不交易(目标=现仓); **绝不回退在役引擎**。"
            f"检查宽书生产方(~/wide_shadow shadow_loop_v2 / state/target_live)。")


def factor_version_stamp(ext: Dict[str, Any]) -> str:
    """The anchors-row `factor_version` string in external mode: WHICH book traded this anchor."""
    return json.dumps({"book_source": "external", "schema": ext.get("schema"),
                       "booster_sha": ext.get("booster_sha"), "weights_sha": ext.get("weights_sha"),
                       "universe_sha": ext.get("universe_sha"), "gross_mult": ext.get("gross_mult")},
                      sort_keys=True)
