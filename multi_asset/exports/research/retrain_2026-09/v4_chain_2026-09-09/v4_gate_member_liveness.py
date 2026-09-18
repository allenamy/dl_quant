#!/usr/bin/env python3
"""v4_gate_member_liveness.py — MEMBER_LIVENESS gate (ELIGIBILITY_CONTRACT gates.MEMBER_LIVENESS; rule text in the contract's rules[]; applied
2026-09-18 by the user's word 「按最佳建议来」 after independent review r7 accepted the rule's boundary).

THE RULE: a symbol is a member of anchor E only if at least one REAL 5-minute bar exists in the 288 cache rows ending at E's row
(rows (r-288, r], r = the cache row whose ts == E); real = NOT a hole-filled cell (HOLE_CELLS) AND log_qv (cache channel 3) finite.
THIS GATE DOES NOT TRUST THE MASK: it re-derives liveness from CACHE + HOLE_CELLS and checks the member sets the builders actually PRODUCED —
KING_META (members per E_ts) and DLW_TARGETS (members per E_ts). PASS iff dead-but-member cells == 0 in BOTH sets.
Same computation as the measuring device fx_member_liveness.py (FX_DATA/receipts/MEMBER_LIVENESS_2026-09-18.json: on the FP2-8 tradable-W24H
masked build 2022 967 / 2026 4,759 dead-but-member cells ⇒ that build FAILS this gate; the liveness mask v4_member_mask_liveness.py is what
makes a build pass).

Refusals are PASS=false with the reason named, never a skip: a member-set file that cannot be read; an anchor E_ts absent from the cache ts
axis; a member index outside the symbols axis; a member-set symbols axis that is not the cache axis; channel 3 not named log_qv; hole cells off
the cache. Anchors with fewer than 288 rows of history are counted over the rows available (n_short_window reported) — identical to the mask
builder, so the two cannot disagree on the boundary.
Boundary (independent review r7): a real bar with zero trades is LIVE — data liveness, not venue eligibility truth. NOT covered here: the export
bundle's live list (contract rules[] names it; binding it is a change to the export gate, still open).

Receipt through v4_gate_common.finalize: gate MEMBER_LIVENESS; inputs cache / hole_cells / wide_fea_v4_meta / dlw_v4raw_targets
(REQUIRED_INPUTS floor) + member_mask when declared (recorded, never used by the verdict). rc 0 iff PASS else 3.
env: CACHE HOLE_CELLS KING_META DLW_TARGETS OUT (required); MEMBER_MASK (optional, recorded only)."""
import collections, json, os, sys, time, zipfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file

W = 288
LOG_QV_CH = 3
GATE = "MEMBER_LIVENESS"


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
    E = {k: os.environ.get(k, "") for k in ("CACHE", "HOLE_CELLS", "KING_META", "DLW_TARGETS", "OUT", "MEMBER_MASK", "BUNDLE_CONFIG")}
    out = E["OUT"] or os.path.join(os.getcwd(), "MEMBER_LIVENESS.json")
    res = {"device": "v4_gate_member_liveness.py", "rule": GATE, "window_rows": W, "env": dict(E), "PASS": False, "refusals": [], "sets": {}}
    inputs = {"cache": E["CACHE"], "hole_cells": E["HOLE_CELLS"], "wide_fea_v4_meta": E["KING_META"], "dlw_v4raw_targets": E["DLW_TARGETS"]}
    if E["MEMBER_MASK"]:
        inputs["member_mask"] = E["MEMBER_MASK"]
    missing = [k for k in ("CACHE", "HOLE_CELLS", "KING_META", "DLW_TARGETS", "OUT") if not E[k]]
    if missing:
        res["refusals"].append(f"env missing {missing}"); finalize(GATE, res, out, inputs)
    try:
        C = np.load(E["CACHE"], allow_pickle=True)
        cts = C["ts"].astype(np.int64); csym = [str(s) for s in C["symbols"]]; ch = [str(x) for x in C["ch"]]
        lq, dshape = load_channel(E["CACHE"], LOG_QV_CH)
        H = np.load(E["HOLE_CELLS"], allow_pickle=True)
        hrow = np.asarray(H["row"]).astype(np.int64); hcol = np.asarray(H["col"]).astype(np.int64); hsym = [str(s) for s in H["symbols"]]
    except Exception as e:   # noqa: BLE001
        res["refusals"].append(f"cache/hole cells unreadable: {e!r}"); finalize(GATE, res, out, inputs)
    nT, nS = lq.shape
    if not (len(cts) == nT and len(csym) == nS and np.all(np.diff(cts) > 0)):
        res["refusals"].append("cache axes inconsistent or ts not strictly increasing")
    if not (len(ch) > LOG_QV_CH and ch[LOG_QV_CH] == "log_qv"):
        res["refusals"].append(f"cache channel {LOG_QV_CH} is not log_qv: {ch}")
    if hsym != csym or (len(hrow) and (int(hrow.min()) < 0 or int(hrow.max()) >= nT or int(hcol.min()) < 0 or int(hcol.max()) >= nS)):
        res["refusals"].append("hole cells: symbols axis != cache or a (row, col) outside the cache")
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
            Ets = np.asarray(m["E_ts"]).astype(np.int64); M = m["members"]
            fsym = [str(s) for s in m["symbols"]] if "symbols" in m.files else None
        except Exception as e:   # noqa: BLE001
            res["refusals"].append(f"{name}: unreadable or missing E_ts/members: {e!r}"); continue
        if fsym is not None and fsym != csym:
            res["refusals"].append(f"{name}: symbols axis != cache symbols ({len(fsym)} vs {len(csym)})"); continue
        S["symbols_axis"] = "file == cache" if fsym is not None else "assumed cache axis (file carries no symbols key; member indices checked < N)"
        if len(Ets) != len(M):
            res["refusals"].append(f"{name}: E_ts ({len(Ets)}) and members ({len(M)}) lengths differ"); continue
        by = collections.defaultdict(lambda: [0, 0]); dead = collections.Counter(); runs = collections.defaultdict(list); bad_idx = []; miss = []
        for i, t in enumerate(Ets):
            r = row_of.get(int(t))
            if r is None:
                miss.append(int(t)); continue
            mem = np.asarray(M[i]).astype(np.int64).ravel()
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
        S["by_year"] = {y: {"member_cells": v[0], "dead_but_member": v[1], "pct": round(v[1] / v[0] * 100, 3) if v[0] else None} for y, v in sorted(by.items())}
        S["n_dead_names"] = len(dead); S["top_names"] = dead.most_common(25)
        S["spans"] = {s: [time.strftime("%Y-%m-%d %HZ", time.gmtime(min(v))), time.strftime("%Y-%m-%d %HZ", time.gmtime(max(v))), len(v)]
                      for s, v in sorted(runs.items(), key=lambda kv: -len(kv[1]))[:25]}
        total_dead += S["dead_but_member"]
    # third end — the EXPORT bundle's live list (config.json symbols_live / keep_names), checked at the cache's LAST 4h anchor (the export anchor):
    # a name shipped for serving must have a real bar in the last 24 h of the cache the bundle was built from. Optional input BUNDLE_CONFIG; when given
    # it is recorded as an input and its dead names fail the gate.
    if E["BUNDLE_CONFIG"]:
        inputs["bundle_config"] = E["BUNDLE_CONFIG"]
        S = {"path": E["BUNDLE_CONFIG"], "checked_at_anchor": None, "n_names": 0, "dead_at_last_anchor": [], "unknown_names": []}
        res["sets"]["bundle_symbols_live"] = S
        try:
            cfg = json.load(open(E["BUNDLE_CONFIG"]))
            names = cfg.get("symbols_live") or cfg.get("keep_names") or []
            if not isinstance(names, list): raise ValueError("symbols_live is not a list")
        except Exception as e:   # noqa: BLE001
            res["refusals"].append(f"bundle config unreadable or without symbols_live: {e!r}"); names = []
        on_grid = np.nonzero(cts % 14400 == 0)[0]
        if not len(on_grid): res["refusals"].append("cache has no 4h anchor for the export-end check")
        else:
            r = int(on_grid[-1]); hi = r + 1; lo = max(hi - W, 0); S["checked_at_anchor"] = int(cts[r]); col = {s: i for i, s in enumerate(csym)}
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
    main()
