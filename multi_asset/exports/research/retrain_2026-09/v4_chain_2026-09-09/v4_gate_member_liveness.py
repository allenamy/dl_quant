#!/usr/bin/env python3
"""v4_gate_member_liveness.py — MEMBER_LIVENESS gate (ELIGIBILITY_CONTRACT gates.MEMBER_LIVENESS; rule text in the contract's rules[]; applied
2026-09-18 by the user's word 「按最佳建议来」 after independent review r7 accepted the rule's boundary).

THE RULE: a symbol is a member of anchor E only if at least one REAL bar exists in the 24 HOURS ending at E's row
(rows (r-W, r], r = the cache row whose ts == E, W = 86400 / the cache's own uniform row spacing); real = NOT a hole-filled
cell (HOLE_CELLS) AND log_qv (cache channel 3) FINITE (not NaN and not +-inf).
THIS GATE DOES NOT TRUST THE MASK: it re-derives liveness from CACHE + HOLE_CELLS and checks the member sets the builders actually PRODUCED —
KING_META (members per E_ts) and DLW_TARGETS (members per E_ts). PASS iff dead-but-member cells == 0 in BOTH sets.
Same computation as the measuring device fx_member_liveness.py (FX_DATA/receipts/MEMBER_LIVENESS_2026-09-18.json: on the FP2-8 tradable-W24H
masked build 2022 967 / 2026 4,759 dead-but-member cells ⇒ that build FAILS this gate; the liveness mask v4_member_mask_liveness.py is what
makes a build pass).

Refusals are PASS=false with the reason named, never a skip: a member-set file that cannot be read; an anchor E_ts absent from the cache ts
axis; a member index outside the symbols axis; a member-set symbols axis that is not the cache axis; channel 3 not named log_qv; hole cells off
the cache. Anchors with fewer than W rows of history are counted over the rows available (n_short_window reported) — identical to the mask
builder, so the two cannot disagree on the boundary.
★ ROUND 12 (R12-C4) — five ways this gate used to pass on nothing, each now a named refusal:
  (a) W was hard-coded at 288 rows, which is 24 h only on a 300 s grid; on a 600 s cache it silently covered 48 h and a name whose
      last real bar was 47h50m old read as LIVE. W is now derived from the axis spacing, and a non-uniform axis is refused outright.
  (b) `ts`/`E_ts` were cast with astype(int64) BEFORE any check, so an axis offset by +0.5 s was truncated back onto the grid and
      passed. Integrality is now checked first (`int_axis`).
  (c) members [0.9, 1.1] became the positions [0, 1] and [False, True] became [0, 1] instead of a two-name boolean mask. dtype is
      now validated before the cast (`member_index`), and bool/float member arrays are refused.
  (d) a member set with 0 anchors, or 0 member cells, PASSed while measuring nothing. Both are refusals.
  (e) the bundle end fell back to `keep_names` (FEATURE names in the exporter, not symbols) and treated an absent or EMPTY
      symbols_live as "no dead names". Both are refusals and the fallback is gone.
Boundary (independent review r7): a real bar with zero trades is LIVE — data liveness, not venue eligibility truth; a name halted less than
24 h ago still passes. It does NOT replace a venue tradability / delisting-settlement rule, which is still open. The export end IS covered
here when BUNDLE_CONFIG is given (symbols_live at the cache's last 4h anchor).

Receipt through v4_gate_common.finalize: gate MEMBER_LIVENESS; inputs cache / hole_cells / wide_fea_v4_meta / dlw_v4raw_targets
(REQUIRED_INPUTS floor) + member_mask when declared (recorded, never used by the verdict). rc 0 iff PASS else 3.
env: CACHE HOLE_CELLS KING_META DLW_TARGETS OUT (required); MEMBER_MASK (optional, recorded only); BUNDLE_CONFIG (optional, turns on the
     export end); EXPORT_ANCHOR_TS (optional, pins the moment the export end judges — see R14-C1; without it the bundle must declare one)."""
import calendar, collections, json, os, re, sys, time, zipfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file

WINDOW_SECONDS = 86400            # the rule's window is 24 HOURS; the row count is derived from the cache's own spacing (R12-C4)
LOG_QV_CH = 3
GATE = "MEMBER_LIVENESS"
ANCHOR_SECONDS = 14400
# ★ R15-C1 (round 15): the SINGLE declaration of every environment variable this gate reads. The receipt's env inventory (main, below) is
#   built from it, and chain_lib.sh's run_gate reads the same list via `--env-keys` to STRIP any of these keys that the ambient shell supplies
#   without them being a governed contract key or an explicit run_gate arg. One list drives BOTH the record and the clean, so a name-by-name
#   unset list (R12-C3 added V4_UMASK_NPZ; R14-C1 then added EXPORT_ANCHOR_TS to none) cannot reopen the class: a new env read is covered the
#   moment it is added here. tests_member_liveness.py asserts this tuple COVERS every os.environ read in this source (no undeclared read).
ENV_KEYS = ("CACHE", "HOLE_CELLS", "KING_META", "DLW_TARGETS", "OUT", "MEMBER_MASK", "BUNDLE_CONFIG", "EXPORT_ANCHOR_TS")
# ★ R15-C2: a declared export anchor as a string is EITHER a pure integer epoch OR the STRICT UTC ISO the exporter writes. The whole string
#   must be 'YYYY-MM-DDTHH:MM:SSZ' (zero-padded, trailing Z required, nothing before or after) — the old `_v[:19]` truncation accepted
#   '…:00.5Z' and '…:00Zgarbage' as a legal anchor.
_ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def int_axis(arr, name):
    """(int64 values, error-or-None). Integrality is checked BEFORE any cast (R12-C4): `astype(np.int64)` on a
    timestamp axis offset by +0.5 s used to truncate it back onto the grid and pass. A bool or non-integral float
    axis is refused, never rounded."""
    a = np.asarray(arr)
    if a.dtype.kind in "iu":
        return a.astype(np.int64), None
    if a.dtype.kind == "b":
        return None, f"{name}: boolean dtype is not a timestamp axis"
    if a.dtype.kind == "f":
        if a.size and not np.all(np.isfinite(a)):
            return None, f"{name}: float axis carries non-finite values"
        if a.size and not np.all(a == np.rint(a)):
            bad = [float(x) for x in np.asarray(a)[np.asarray(a) != np.rint(a)][:3]]
            return None, f"{name}: float axis with non-integral values (first {bad}); casting would silently truncate"
        return a.astype(np.int64), None
    return None, f"{name}: dtype {a.dtype} is not an integer axis"


def member_index(arr, name):
    """(int64 index vector, error-or-None). dtype is validated BEFORE the cast (R12-C4): members [0.9, 1.1] used to
    become [0, 1] and [False, True] used to become the positions [0, 1] instead of a two-name boolean mask."""
    a = np.asarray(arr)
    if a.dtype.kind == "b":
        return None, f"{name}: boolean member array — a bool array selects by mask, not by position; refused rather than cast to [0, 1]"
    if a.dtype.kind == "f":
        return None, f"{name}: float member array (first {[float(x) for x in a.ravel()[:3]]}) — an index must be an integer, casting would truncate"
    if a.dtype.kind not in "iu":
        return None, f"{name}: member dtype {a.dtype} is not an integer index"
    return a.astype(np.int64).ravel(), None


def load_channel(cache_path, ch_idx):
    """One channel of the cache's `data` array as float32 without materialising the whole (T, N, C) array (STORED member ⇒ memmap at its
    offset inside the zip; compressed ⇒ np.load fallback, the measuring device's way). Same helper as v4_member_mask_liveness.py."""
    with zipfile.ZipFile(cache_path) as z:
        zi = z.getinfo("data.npy")
        if zi.compress_type == zipfile.ZIP_STORED:
            with z.open(zi) as fh:
                version = np.lib.format.read_magic(fh)
                rdr = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}.get(tuple(version))
                if rdr is None: raise ValueError(f"unsupported .npy header version {version}")   # public API: numpy renamed the private _read_array_header
                shape, fortran, dtype = rdr(fh)
                hdr_len = fh.tell()
            with open(cache_path, "rb") as raw:
                raw.seek(zi.header_offset)
                fixed = raw.read(30)
                n_name = int.from_bytes(fixed[26:28], "little"); n_extra = int.from_bytes(fixed[28:30], "little")
                data_off = zi.header_offset + 30 + n_name + n_extra + hdr_len
            if fortran or len(shape) != 3:
                raise ValueError(f"cache data.npy shape/order unsupported: {shape} fortran={fortran}")
            mm = np.memmap(cache_path, dtype=dtype, mode="r", offset=data_off, shape=tuple(shape))
            return np.ascontiguousarray(mm[:, :, ch_idx]).astype(np.float32), tuple(shape)
    C = np.load(cache_path, allow_pickle=True)
    d = C["data"]
    return d[:, :, ch_idx].astype(np.float32), tuple(d.shape)


def main():
    E = {k: os.environ.get(k, "") for k in ENV_KEYS}   # ★ R15-C1: EVERY env var this gate reads (incl. EXPORT_ANCHOR_TS) is recorded, from the single ENV_KEYS declaration
    out = E["OUT"] or os.path.join(os.getcwd(), "MEMBER_LIVENESS.json")
    res = {"device": "v4_gate_member_liveness.py", "rule": GATE, "window_seconds": WINDOW_SECONDS, "window_rows": None, "row_spacing_s": None,
           "env": dict(E), "env_keys": list(ENV_KEYS), "PASS": False, "refusals": [], "sets": {}}
    inputs = {"cache": E["CACHE"], "hole_cells": E["HOLE_CELLS"], "wide_fea_v4_meta": E["KING_META"], "dlw_v4raw_targets": E["DLW_TARGETS"]}
    if E["MEMBER_MASK"]:
        inputs["member_mask"] = E["MEMBER_MASK"]
    missing = [k for k in ("CACHE", "HOLE_CELLS", "KING_META", "DLW_TARGETS", "OUT") if not E[k]]
    if missing:
        res["refusals"].append(f"env missing {missing}"); finalize(GATE, res, out, inputs)
    try:
        C = np.load(E["CACHE"], allow_pickle=True)
        cts, err = int_axis(C["ts"], "cache ts")
        if err: res["refusals"].append(err); finalize(GATE, res, out, inputs)
        csym = [str(s) for s in C["symbols"]]; ch = [str(x) for x in C["ch"]]
        lq, dshape = load_channel(E["CACHE"], LOG_QV_CH)
        H = np.load(E["HOLE_CELLS"], allow_pickle=True)
        hrow, e1 = int_axis(H["row"], "hole cells row"); hcol, e2 = int_axis(H["col"], "hole cells col")
        if e1 or e2: res["refusals"].append(e1 or e2); finalize(GATE, res, out, inputs)
        hsym = [str(s) for s in H["symbols"]]
    except Exception as e:   # noqa: BLE001
        res["refusals"].append(f"cache/hole cells unreadable: {e!r}"); finalize(GATE, res, out, inputs)
    nT, nS = lq.shape
    if not (len(cts) == nT and len(csym) == nS and np.all(np.diff(cts) > 0)):
        res["refusals"].append("cache axes inconsistent or ts not strictly increasing")
    if not (len(ch) > LOG_QV_CH and ch[LOG_QV_CH] == "log_qv"):
        res["refusals"].append(f"cache channel {LOG_QV_CH} is not log_qv: {ch}")
    if hsym != csym or (len(hrow) and (int(hrow.min()) < 0 or int(hrow.max()) >= nT or int(hcol.min()) < 0 or int(hcol.max()) >= nS)):
        res["refusals"].append("hole cells: symbols axis != cache or a (row, col) outside the cache")
    # ★ R12-C4: the window is 24 HOURS, so the row count must come from the cache's own spacing. W = 288 was hard-coded
    #   for a 300 s grid; on a 600 s grid it covered 48 h and a name whose last real bar was 47h50m old read as live.
    W = None
    if len(cts) > 1:
        dts = np.unique(np.diff(cts))
        if len(dts) != 1:
            res["refusals"].append(f"cache ts axis is not uniformly spaced ({len(dts)} distinct steps, first {[int(x) for x in dts[:4]]}): the 24 h window cannot be expressed in rows")
        else:
            dt = int(dts[0])
            if dt <= 0 or WINDOW_SECONDS % dt:
                res["refusals"].append(f"cache row spacing {dt}s does not divide the {WINDOW_SECONDS}s window")
            else:
                W = WINDOW_SECONDS // dt; res["row_spacing_s"] = dt; res["window_rows"] = int(W)
    else:
        res["refusals"].append("cache ts axis has fewer than two rows: no spacing to derive the window from")
    if res["refusals"]:
        finalize(GATE, res, out, inputs)
    notlive = ~np.isfinite(lq)
    if len(hrow):
        notlive[hrow, hcol] = True
    cs = np.zeros((nT + 1, nS), np.int32); np.cumsum(notlive, axis=0, dtype=np.int32, out=cs[1:])
    row_of = {int(t): i for i, t in enumerate(cts)}
    res["cache"] = {"shape": list(dshape), "n_hole_cells": int(len(hrow)), "ts_first": int(cts[0]), "ts_last": int(cts[-1])}
    total_dead = 0
    for name, path in (("wide_fea_v4_meta", E["KING_META"]), ("dlw_v4raw_targets", E["DLW_TARGETS"])):
        S = {"path": path, "n_anchors": 0, "n_member_cells": 0, "dead_but_member": 0, "n_short_window": 0, "by_year": {}, "top_names": [], "spans": {}}
        res["sets"][name] = S
        try:
            m = np.load(path, allow_pickle=True)
            Ets, err = int_axis(m["E_ts"], f"{name} E_ts")
            if err: res["refusals"].append(err); continue
            M = m["members"]
            fsym = [str(s) for s in m["symbols"]] if "symbols" in m.files else None
        except Exception as e:   # noqa: BLE001
            res["refusals"].append(f"{name}: unreadable or missing E_ts/members: {e!r}"); continue
        if fsym is not None and fsym != csym:
            res["refusals"].append(f"{name}: symbols axis != cache symbols ({len(fsym)} vs {len(csym)})"); continue
        S["symbols_axis"] = "file == cache" if fsym is not None else "assumed cache axis (file carries no symbols key; member indices checked < N)"
        if len(Ets) != len(M):
            res["refusals"].append(f"{name}: E_ts ({len(Ets)}) and members ({len(M)}) lengths differ"); continue
        if len(Ets) == 0:                     # ★ R12-C4: an empty member set measured nothing; it is not a pass
            res["refusals"].append(f"{name}: empty member population (0 anchors) — nothing was measured, which is not a PASS"); continue
        by = collections.defaultdict(lambda: [0, 0]); dead = collections.Counter(); runs = collections.defaultdict(list); bad_idx = []; miss = []; bad_dtype = []
        for i, t in enumerate(Ets):
            r = row_of.get(int(t))
            if r is None:
                miss.append(int(t)); continue
            mem, merr = member_index(M[i], f"{name} members[{i}]")
            if merr:
                bad_dtype.append((int(t), merr)); continue
            if len(mem) and (int(mem.min()) < 0 or int(mem.max()) >= nS or len(np.unique(mem)) != len(mem)):
                bad_idx.append(int(t)); continue
            hi = r + 1; lo = max(hi - W, 0)
            if hi - lo < W:
                S["n_short_window"] += 1
            cnt = cs[hi, mem] - cs[lo, mem]
            d = cnt >= (hi - lo)
            y = str(time.gmtime(int(t)).tm_year); by[y][0] += int(len(mem)); by[y][1] += int(d.sum())
            S["n_anchors"] += 1; S["n_member_cells"] += int(len(mem)); S["dead_but_member"] += int(d.sum())
            for j in mem[d]:
                dead[csym[j]] += 1; runs[csym[j]].append(int(t))
        if miss:
            res["refusals"].append(f"{name}: {len(miss)} anchors absent from the cache ts axis (first {miss[:5]})")
        if bad_idx:
            res["refusals"].append(f"{name}: {len(bad_idx)} anchors with a member index outside [0, N) or duplicated (first {bad_idx[:5]})")
        if bad_dtype:
            res["refusals"].append(f"{name}: {len(bad_dtype)} anchors whose member array is not an integer index — {bad_dtype[0][1]}")
        if S["n_member_cells"] == 0 and not (miss or bad_idx or bad_dtype):
            res["refusals"].append(f"{name}: 0 member cells over {len(Ets)} anchors — nothing was measured, which is not a PASS")
        S["by_year"] = {y: {"member_cells": v[0], "dead_but_member": v[1], "pct": round(v[1] / v[0] * 100, 3) if v[0] else None} for y, v in sorted(by.items())}
        S["n_dead_names"] = len(dead); S["top_names"] = dead.most_common(25)
        S["spans"] = {s: [time.strftime("%Y-%m-%d %HZ", time.gmtime(min(v))), time.strftime("%Y-%m-%d %HZ", time.gmtime(max(v))), len(v)]
                      for s, v in sorted(runs.items(), key=lambda kv: -len(kv[1]))[:25]}
        total_dead += S["dead_but_member"]
    # third end — the EXPORT bundle's live list (config.json symbols_live), checked at the bundle's OWN anchor: a name shipped for serving must have a
    # real bar in the 24 h before the anchor the bundle was built for. Optional input BUNDLE_CONFIG; when given it is recorded and its dead names fail.
    # ★ 2026-09-18 (first real-bundle run): the anchor used to be the cache's LAST 4h row unconditionally. On the production cache that row is
    #   DEGENERATE — holefix2's synthetic 2026-08-31 is 288 entirely hole-filled rows (229,824 cells; the TRN-16 ruling protects them), so the only
    #   window ending at 09-01 00Z holds no real bar for ANY symbol and the gate called all 450 shipped names dead. The training member sets were
    #   unaffected because they end at 08-31 20Z. An all-dead universe is evidence the ANCHOR is wrong, so: prefer the anchor the bundle itself names,
    #   else the latest anchor whose window has at least one live name anywhere in the universe, and REFUSE if the chosen anchor has none.
    if E["BUNDLE_CONFIG"]:
        inputs["bundle_config"] = E["BUNDLE_CONFIG"]
        S = {"path": E["BUNDLE_CONFIG"], "checked_at_anchor": None, "anchor_source": None, "n_live_in_universe_at_anchor": None,
             "n_names": 0, "dead_at_last_anchor": [], "unknown_names": []}
        res["sets"]["bundle_symbols_live"] = S
        # ★ R12-C4: no `keep_names` fallback — in pod_export_bundle_v4 `keep_names` are FEATURE names, not symbols, so the old
        #   fallback compared feature labels against the symbol axis. An absent or EMPTY symbols_live is a refusal, not 0 dead names.
        names = []; cfg = None
        try:
            cfg = json.load(open(E["BUNDLE_CONFIG"]))
            if not isinstance(cfg, dict) or "symbols_live" not in cfg:
                res["refusals"].append("bundle config carries no symbols_live key (keep_names is the FEATURE list and is NOT a substitute)")
            elif not isinstance(cfg["symbols_live"], list):
                res["refusals"].append(f"bundle config symbols_live is {type(cfg['symbols_live']).__name__}, not a list")
            elif not cfg["symbols_live"]:
                res["refusals"].append("bundle config symbols_live is EMPTY — an empty live list measures nothing, which is not a PASS")
            else:
                names = cfg["symbols_live"]
        except Exception as e:   # noqa: BLE001
            res["refusals"].append(f"bundle config unreadable: {e!r}")
        on_grid = np.nonzero(cts % ANCHOR_SECONDS == 0)[0]
        if not len(on_grid): res["refusals"].append("cache has no 4h anchor for the export-end check")
        else:
            def _n_live(row):                                                # how many names of the WHOLE universe have a real bar in this window
                hi_, lo_ = row + 1, max(row + 1 - W, 0)
                return int(((cs[hi_] - cs[lo_]) < (hi_ - lo_)).sum())
            # ★ R14-C1 (independent review round 14): the export end judges the candidate AT THE MOMENT IT IS BEING EVALUATED FOR and NEVER
            #   searches for a moment where the answer is green. My round-13 rule ("an all-dead universe means the anchor is wrong, so step
            #   back to the latest anchor that still has a live name") was too permissive: the reviewer deleted ONE unrelated non-shipping
            #   name's final bar and the gate walked back 52 h, turning the same dead shipping list from FAIL into PASS while the shipped
            #   name's last real bar was still 72 h before the data end. Selection is now a fixed, declared order and nothing else:
            #     1. EXPORT_ANCHOR_TS — the caller pins the moment explicitly;
            #     2. the bundle's own DATA-AXIS end: config.provenance.data_axis_end_utc (what pod_export_bundle_v4 L266 actually writes),
            #        or a numeric top-level export_anchor_ts / anchor_ts / generation_anchor_ts;
            #     3. the same fields under MANIFEST.provenance.
            #   A TRAINING cutoff (king_train_end_* / train_end_*) is NOT an export time — pod_export_bundle_v4 L262-266 keeps the two apart
            #   on purpose — so it is refused BY NAME instead of silently serving as the anchor. The chosen anchor must sit on the cache's ts
            #   axis AND on the 4h grid. Insufficient coverage at that anchor is a named refusal, never a step backwards.
            _TRAIN_KEYS = ("king_train_end_ts", "king_train_end_utc", "train_end_ts", "train_end_utc", "king_train_last_label_end_utc")
            _EXPORT_NUM = ("export_anchor_ts", "anchor_ts", "generation_anchor_ts")
            _EXPORT_UTC = ("data_axis_end_utc", "export_anchor_utc", "anchor_utc")

            def _as_epoch(v):
                """(epoch or None). A declared anchor is EITHER an integer epoch OR a STRICT UTC ISO stamp 'YYYY-MM-DDTHH:MM:SSZ' (the
                exporter writes the latter). R15-C2, two independent defects fixed here:
                  (a) the timezone is UTC and NEVER the host's. The old code used time.mktime (which reads the struct as LOCAL time and
                      infers DST via tm_isdst=-1) corrected by time.timezone (the NON-DST offset), so wherever DST was in effect the epoch
                      was one hour early and then failed the 4h-grid check — a host-dependent verdict on identical bytes. calendar.timegm
                      reads the struct as UTC with no host dependence.
                  (b) the WHOLE string must match. `_v[:19]` truncation accepted '2026-09-16T00:00:00.5Z' and '…:00Zgarbage' as a legal
                      anchor; the regex pins the exact zero-padded shape (trailing Z, nothing trailing) and strptime validates the field
                      ranges. Integer inputs must be finite whole seconds (float('inf'/'nan').is_integer() is False, so non-finite ⇒ None)."""
                if isinstance(v, bool): return None
                if isinstance(v, (int, float)):
                    try: return int(v) if float(v).is_integer() else None    # finite integer seconds only (inf/nan ⇒ is_integer() False ⇒ None)
                    except Exception: return None   # noqa: BLE001
                if isinstance(v, str):
                    _v = v.strip()
                    if _v and (_v[1:] if _v[:1] == "-" else _v).isdigit():   # an env var / numeric field is a string: "1789689600" is an epoch, not an ISO stamp
                        try: return int(_v)
                        except Exception: return None   # noqa: BLE001
                    if not _ISO_UTC.match(_v): return None                   # STRICT whole-string UTC ISO; no truncation
                    try: return calendar.timegm(time.strptime(_v, "%Y-%m-%dT%H:%M:%SZ"))   # UTC, host-timezone-independent
                    except Exception: return None   # noqa: BLE001
                return None

            def _pick(d, where):
                """(epoch, source) from one mapping, export keys only; a training cutoff found alone is reported, not used"""
                if not isinstance(d, dict): return None, None, None
                for _k in _EXPORT_NUM + _EXPORT_UTC:
                    _e = _as_epoch(d.get(_k))
                    if _e is not None: return _e, f"{where} {_k}", None
                for _k in _TRAIN_KEYS:
                    if d.get(_k) is not None: return None, None, f"{where} {_k}"
                return None, None, None

            want_a = None; _train_only = None
            _env_a = _as_epoch(E["EXPORT_ANCHOR_TS"] or None)   # ★ R15-C1: read from the recorded ENV_KEYS inventory, not a bare os.environ — one governed read site
            if _env_a is not None: want_a, S["anchor_source"] = _env_a, "EXPORT_ANCHOR_TS (pinned by the caller)"
            if want_a is None and isinstance(cfg, dict):
                for _src, _where in ((cfg, "bundle config"), (cfg.get("provenance"), "bundle config provenance")):
                    _e, _s, _t = _pick(_src, _where)
                    if _e is not None: want_a, S["anchor_source"] = _e, _s; break
                    _train_only = _train_only or _t
            # ★ R14-C2: the MANIFEST takes part in anchor selection, so every read of it is a DEPENDENCY. It is recorded in `inputs` whenever
            #   the file exists — the reviewer edited a MANIFEST after a genuine PASS and `require(recorded_extras=True)` still accepted the
            #   receipt, because a dependency that was never recorded cannot be re-hashed.
            _mp = os.path.join(os.path.dirname(os.path.abspath(E["BUNDLE_CONFIG"])), "MANIFEST.json")
            if os.path.isfile(_mp):
                inputs["bundle_manifest"] = _mp; S["manifest_read"] = _mp
                if want_a is None:
                    try:
                        _m = json.load(open(_mp))
                        _e, _s, _t = _pick((_m.get("provenance") or {}) if isinstance(_m, dict) else {}, "bundle MANIFEST provenance")
                        if _e is not None: want_a, S["anchor_source"] = _e, _s
                        else: _train_only = _train_only or _t
                    except Exception as _me:   # noqa: BLE001
                        res["refusals"].append(f"bundle MANIFEST unreadable while it is an anchor-selection input: {_me!r}")
            row = None
            if want_a is None:
                if _train_only:
                    res["refusals"].append(f"export_anchor_is_a_training_cutoff: the only anchor the bundle declares is {_train_only}, which is the "
                                           f"booster's gradient cutoff, not the moment this bundle is exported for; declare an export anchor "
                                           f"(provenance.data_axis_end_utc) or pin EXPORT_ANCHOR_TS")
                else:
                    res["refusals"].append("export_anchor_not_declared: the bundle names no export anchor and none was pinned via EXPORT_ANCHOR_TS — "
                                           "the export end judges a DECLARED moment and never searches the axis for one that passes")
            else:
                _r = row_of.get(int(want_a))
                if _r is None:
                    res["refusals"].append(f"export_anchor_off_cache_axis: the declared anchor {want_a} ({S['anchor_source']}) is not on this cache's "
                                           f"ts axis — the bundle was built from a different cache")
                elif int(cts[_r]) % ANCHOR_SECONDS != 0:
                    res["refusals"].append(f"export_anchor_off_4h_grid: the declared anchor {want_a} ({S['anchor_source']}) is on the cache axis but not "
                                           f"on the {ANCHOR_SECONDS}s anchor grid")
                else: row = _r
            if row is not None:
                nlive = _n_live(row); S["checked_at_anchor"] = int(cts[row]); S["n_live_in_universe_at_anchor"] = nlive
                if nlive == 0:
                    # (c) R14-C1: the DECLARED moment has no real bar anywhere in the universe. That is insufficient coverage at the moment we
                    #     must judge — report it as such. It is NOT a licence to judge at some earlier moment.
                    res["refusals"].append(f"insufficient_coverage_at_export_anchor: at the declared anchor {int(cts[row])} ({S['anchor_source']}) no name "
                                           f"in the universe has a real bar in the {W}-row window; the export end cannot be judged here and does not "
                                           f"move to another anchor")
                else:
                    hi = row + 1; lo = max(hi - W, 0); col = {s: i for i, s in enumerate(csym)}
                    for s in names:
                        j = col.get(str(s))
                        if j is None: S["unknown_names"].append(str(s)); continue
                        if int(cs[hi, j] - cs[lo, j]) >= (hi - lo): S["dead_at_last_anchor"].append(str(s))
                    S["n_names"] = len(names)
                    if S["unknown_names"]: res["refusals"].append(f"bundle live list names not on the cache axis: {S['unknown_names'][:5]}")
                    total_dead += len(S["dead_at_last_anchor"])
    res["dead_but_member_total"] = total_dead
    res["PASS"] = (not res["refusals"]) and total_dead == 0
    res["verdict_rule"] = "PASS iff no refusal and dead-but-member cells == 0 in both produced member sets"
    finalize(GATE, res, out, inputs)


if __name__ == "__main__":
    # ★ R15-C1: the machine-readable declaration chain_lib.sh's run_gate strips the ambient by. Printing ENV_KEYS is the ONE place both the
    #   receipt's env inventory (main) and the driver's ambient-clean read from, so neither can drift from the other.
    if len(sys.argv) == 2 and sys.argv[1] == "--env-keys":
        print(" ".join(ENV_KEYS)); sys.exit(0)
    main()
