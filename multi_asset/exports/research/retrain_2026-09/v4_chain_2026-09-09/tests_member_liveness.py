#!/usr/bin/env python3
"""Behavioural tests for the MEMBER_LIVENESS pair — v4_member_mask_liveness.py (build side) and v4_gate_member_liveness.py (gate side) — written
after independent review round 11 (R11-LIVE / CHAIN C3): the measuring device fx_member_liveness.py used isnan (an +inf cell counted as live),
`continue`d on a missing anchor, wrote statistics with rc 0 when nothing was measured, and never refused a dead member. Every one of the reviewer's
seven tiny probes is reproduced here against the gate (and the mask builder where it applies), with the green baseline asserted first.
Synthetic caches only: 289 five-minute rows (one 24 h window + the anchor row), one to three symbols, channel 3 = log_qv.
Run: python3 tests_member_liveness.py   (exit 0 iff ALL PASS)"""
import json, os, subprocess, sys, tempfile, time, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
GATE = os.path.join(HERE, "v4_gate_member_liveness.py"); MASK = os.path.join(HERE, "v4_member_mask_liveness.py")
CH = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
BASE = 1789689600 - 288 * 300; N = [0]; FAILS = []
TMP = tempfile.mkdtemp(prefix="liveness_", dir=os.environ.get("TMPDIR") or None)


def check(name, cond, detail=""):
    N[0] += 1; print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail and not cond else ""))
    if not cond: FAILS.append(name)


def fixture(name, syms=("XUSDT",), rows=289, edit=None, holes=(), E=None, members=None, ts_edit=None, dl_members=None, compressed=False):
    d = os.path.join(TMP, name); os.makedirs(d, exist_ok=True)
    ts = BASE + np.arange(rows, dtype=np.int64) * 300
    data = np.zeros((rows, len(syms), 7), dtype=np.float16); data[:, :, 3] = np.nan
    if edit: edit(data)
    if ts_edit: ts_edit(ts)
    E = int(ts[-1]) if E is None else E
    hr = np.array([h[0] for h in holes], dtype=np.int64); hc = np.array([h[1] for h in holes], dtype=np.int64)
    (np.savez_compressed if compressed else np.savez)(os.path.join(d, "cache.npz"), ts=ts, symbols=np.array(syms), ch=np.array(CH), data=data)
    np.savez(os.path.join(d, "holes.npz"), row=hr, col=hc, symbols=np.array(syms))
    # ★ R12: `members` / `E` are stored with the dtype the caller gave (np.array(...) without a forced int64) — several round-12
    #   cases ARE about dtype, and a fixture that coerces them would test nothing.
    _mk = lambda v: v if isinstance(v, np.ndarray) else np.array(v)
    mem = np.empty(1, dtype=object); mem[0] = _mk(members if members is not None else [0])
    _ets = np.array([E])
    np.savez(os.path.join(d, "meta.npz"), E_ts=_ets, members=mem)
    dm = np.empty(1, dtype=object); dm[0] = _mk(dl_members if dl_members is not None else (members if members is not None else [0]))
    np.savez(os.path.join(d, "targets.npz"), E_ts=_ets, members=dm, symbols=np.array(syms))
    return d


def gate(d, extra=None):
    out = os.path.join(d, "gate.json")
    env = dict(os.environ, CACHE=f"{d}/cache.npz", HOLE_CELLS=f"{d}/holes.npz", KING_META=f"{d}/meta.npz", DLW_TARGETS=f"{d}/targets.npz", OUT=out, **(extra or {}))
    r = subprocess.run([PY, GATE], capture_output=True, text=True, env=env)
    j = json.load(open(out)) if os.path.exists(out) else None
    return r.returncode, j, (r.stdout + r.stderr)[-300:]


def mask(d, mask_in=None, mask_in_sha=None):
    out = os.path.join(d, "mask.npz"); rec = os.path.join(d, "mask_receipt.json")
    env = dict(os.environ, CACHE=f"{d}/cache.npz", HOLE_CELLS=f"{d}/holes.npz", OUT=out, RECEIPT=rec)
    if mask_in: env["MASK_IN"] = mask_in
    if mask_in_sha: env["MASK_IN_SHA"] = mask_in_sha
    r = subprocess.run([PY, MASK], capture_output=True, text=True, env=env)
    j = json.load(open(rec)) if os.path.exists(rec) else None
    return r.returncode, j, (np.load(out, allow_pickle=True) if os.path.exists(out) else None), (r.stdout + r.stderr)[-300:]


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


print("[0] green baseline: one real bar (log_qv = 0) at the anchor row ⇒ live ⇒ gate PASS rc 0; mask True")
d = fixture("one_zero", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0)); rc, j, o = gate(d)
check("gate PASS rc 0 on a live member", rc == 0 and j and j["PASS"] is True and j["dead_but_member_total"] == 0, o)
check("receipt is bound: gate name, self_sha256, four inputs hashed", j and j["gate"] == "MEMBER_LIVENESS" and j.get("self_sha256") and set(j["inputs_sha256"]) == {"cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets"}, j and j.get("inputs_sha256"))
rc, mj, mz, o = mask(d)
check("mask builder PASS rc 0 and the anchor cell is True", rc == 0 and mj["VERDICT"] == "PASS" and bool(mz["mask"][-1, 0]) is True, o)

print("\n[1] reviewer probe all_nan: every row NaN ⇒ dead-but-member 1 ⇒ gate FAIL rc 3 (the measuring device counted 1 but returned rc 0)")
d = fixture("all_nan"); rc, j, o = gate(d)
check("gate FAIL rc 3, dead_but_member_total 1, name listed", rc == 3 and j["PASS"] is False and j["dead_but_member_total"] == 2 and j["sets"]["wide_fea_v4_meta"]["top_names"][0][0] == "XUSDT", (rc, j and j["dead_but_member_total"]))
rc, mj, mz, o = mask(d); check("mask builder: anchor cell False", rc == 0 and bool(mz["mask"][-1, 0]) is False, o)

print("\n[2] reviewer probe one_inf: every row NaN except +inf at the anchor ⇒ NOT live (finite rule); measuring device said dead 0")
d = fixture("one_inf", edit=lambda a: a.__setitem__((-1, 0, 3), np.inf)); rc, j, o = gate(d)
check("gate FAIL: +inf is not a real bar", rc == 3 and j["dead_but_member_total"] == 2, (rc, j and j["dead_but_member_total"]))
rc, mj, mz, o = mask(d); check("mask builder: +inf cell ⇒ False", bool(mz["mask"][-1, 0]) is False, o)

print("\n[3] reviewer probes on the window boundary: last real bar at E−23h55 ⇒ live; at E−24h ⇒ dead (rows (r−288, r])")
d = fixture("edge_in", edit=lambda a: a.__setitem__((1, 0, 3), 0.0)); rc, j, o = gate(d)
check("real bar at row 1 (= E−23h55) ⇒ live, PASS", rc == 0 and j["dead_but_member_total"] == 0, (rc, j and j["dead_but_member_total"]))
d2 = fixture("edge_out", edit=lambda a: a.__setitem__((0, 0, 3), 0.0)); rc2, j2, o2 = gate(d2)
check("real bar at row 0 (= E−24h, outside the window) ⇒ dead, FAIL", rc2 == 3 and j2["dead_but_member_total"] == 2, (rc2, j2 and j2["dead_but_member_total"]))
rc, mj, mz, o = mask(d); rc2, mj2, mz2, o2 = mask(d2)
check("mask builder agrees on both boundary cases (in ⇒ True, out ⇒ False)", bool(mz["mask"][-1, 0]) is True and bool(mz2["mask"][-1, 0]) is False)

print("\n[4] reviewer probe future_row_in_unsorted_axis: a row with ts = E+300 placed at r−1 ⇒ refusal (axis not strictly increasing), never a verdict")
def _unsort(ts): ts[-2] = ts[-1] + 300
d = fixture("unsorted", edit=lambda a: a.__setitem__((-2, 0, 3), 0.0), ts_edit=_unsort); rc, j, o = gate(d)
check("gate refuses: PASS false with a refusal naming the axis", rc == 3 and j["PASS"] is False and any("strictly increasing" in x for x in j["refusals"]), j and j["refusals"])
rc, mj, mz, o = mask(d); check("mask builder FAIL (C0) and writes nothing", rc == 1 and mj["VERDICT"] == "FAIL" and mz is None, (rc, mj and mj["VERDICT"]))

print("\n[5] reviewer probe missing_anchor: E not on the cache ts axis ⇒ refusal (measuring device: continue, empty stats, rc 0)")
d = fixture("missing_anchor", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), E=BASE + 288 * 300 + 1); rc, j, o = gate(d)
check("gate refuses with 'absent from the cache ts axis'", rc == 3 and any("absent from the cache ts axis" in x for x in j["refusals"]), j and j["refusals"])

print("\n[6] hole cells: a real-looking cell listed in HOLE_CELLS is not live; symbols axis mismatch is a refusal")
d = fixture("holed", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), holes=[(288, 0)]); rc, j, o = gate(d)
check("the only finite cell is hole-filled ⇒ dead ⇒ FAIL", rc == 3 and j["dead_but_member_total"] == 2, (rc, j and j["dead_but_member_total"]))
d = fixture("holes_axis", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0)); np.savez(f"{d}/holes.npz", row=np.array([], np.int64), col=np.array([], np.int64), symbols=np.array(["OTHER"]))
rc, j, o = gate(d); check("hole cells with a different symbols axis ⇒ refusal", rc == 3 and any("hole cells" in x for x in j["refusals"]), j and j["refusals"])

print("\n[7] three-end identity: the DL targets member set is checked on its own (a dead DL member with a live king member ⇒ FAIL)")
d = fixture("dl_dead", syms=("XUSDT", "YUSDT"), edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), members=[0], dl_members=[0, 1]); rc, j, o = gate(d)
check("king set clean (0 dead) but DL set has YUSDT dead ⇒ FAIL with the DL set named", rc == 3 and j["sets"]["wide_fea_v4_meta"]["dead_but_member"] == 0 and j["sets"]["dlw_v4raw_targets"]["dead_but_member"] == 1, j and {k: v["dead_but_member"] for k, v in j["sets"].items()})
d = fixture("bad_index", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), members=[5]); rc, j, o = gate(d)
check("member index outside [0, N) ⇒ refusal, never used as an index", rc == 3 and any("member index" in x for x in j["refusals"]), j and j["refusals"])
_PIN = BASE + 288 * 300                      # the 289-row fixtures' last row, on the 4h grid; the export end now judges a DECLARED moment
d = fixture("export_end", syms=("XUSDT", "YUSDT"), edit=lambda a: a.__setitem__((-1, 0, 3), 0.0))
json.dump({"symbols_live": ["XUSDT", "YUSDT"], "export_anchor_ts": _PIN}, open(f"{d}/config.json", "w"))
rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("export end: bundle config symbols_live with a dead name (YUSDT) ⇒ FAIL with the export set named", rc == 3 and j["sets"].get("bundle_symbols_live", {}).get("dead_at_last_anchor") == ["YUSDT"], j and j["sets"].get("bundle_symbols_live"))
json.dump({"symbols_live": ["XUSDT"], "export_anchor_ts": _PIN}, open(f"{d}/config.json", "w")); rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("export end: only live names ⇒ PASS", rc == 0 and j["PASS"] is True, j and j["sets"].get("bundle_symbols_live"))

print("\n[7b] export end judges a DECLARED moment and never searches for one that passes (R14-C1)")
# ROUND 13 I made the gate step BACKWARDS when the last 4h anchor's window was entirely hole-filled (the production cache ends with holefix2's
# synthetic 2026-08-31). Round 14 showed that rule lets the gate hunt for a green moment: deleting ONE unrelated non-shipping name's final bar
# moved the anchor back and turned the SAME dead shipping list from FAIL into PASS. The anchor is now declared, never searched.
# Fixture: 865 rows = 72 h. DEADUSDT (shipped) has real bars only in rows 1..288; OTHERUSDT (not shipped) only at the very last row.
# The member sets are pinned at row 288, where DEADUSDT is live, so the TRAINING ends stay clean and only the export end is under test.
_ROWS, _LASTA = 865, BASE + 864 * 300
def _ship_dead_other_live(a):
    a[1:289, 0, 3] = 0.0          # DEADUSDT: real bars in the first window only
    a[-1, 1, 3] = 0.0             # OTHERUSDT: a real bar at the very end
def _ship_dead_other_gone(a):
    a[1:289, 0, 3] = 0.0          # identical except that OTHERUSDT's final bar is removed

_dA = fixture("anchor_other_live", syms=("DEADUSDT", "OTHERUSDT"), rows=_ROWS, edit=_ship_dead_other_live, E=BASE + 288 * 300, members=[0])
_dB = fixture("anchor_other_gone", syms=("DEADUSDT", "OTHERUSDT"), rows=_ROWS, edit=_ship_dead_other_gone, E=BASE + 288 * 300, members=[0])
_vers = {}
for _tag, _dir in (("other_live", _dA), ("other_gone", _dB)):
    json.dump({"symbols_live": ["DEADUSDT"], "export_anchor_ts": _LASTA}, open(f"{_dir}/config.json", "w"))
    _rc, _j, _ = gate(_dir, {"BUNDLE_CONFIG": f"{_dir}/config.json"})
    _vers[_tag] = (_rc, bool((_j or {}).get("PASS")), ((_j or {}).get("sets", {}).get("bundle_symbols_live", {}) or {}).get("checked_at_anchor"), (_j or {}).get("refusals", []))
check("★★★ [R14-C1] deleting an UNRELATED name's final bar does not flip the shipped list's verdict: both stay non-PASS at the same declared anchor",
      _vers["other_live"][1] is False and _vers["other_gone"][1] is False and _vers["other_live"][0] == 3 and _vers["other_gone"][0] == 3
      and _vers["other_live"][2] == _LASTA and _vers["other_gone"][2] == _LASTA, _vers)
check("★★ [R14-C1] and the two非-PASS verdicts say WHY they differ: a dead shipped name vs insufficient coverage at that moment",
      any("insufficient_coverage_at_export_anchor" in x for x in _vers["other_gone"][3]) and not _vers["other_live"][3], _vers)
for _tag, _dir in (("other_live", _dA), ("other_gone", _dB)):
    json.dump({"symbols_live": ["DEADUSDT"]}, open(f"{_dir}/config.json", "w"))
    _rc, _j, _ = gate(_dir, {"BUNDLE_CONFIG": f"{_dir}/config.json"})
    _vers[_tag] = (_rc, bool((_j or {}).get("PASS")), (_j or {}).get("refusals", []))
check("★★★ [R14-C1] with NO declared anchor the gate refuses by name in BOTH caches — it never picks a moment off the axis itself",
      all(v[0] == 3 and v[1] is False and any("export_anchor_not_declared" in x for x in v[2]) for v in _vers.values()), _vers)

json.dump({"symbols_live": ["DEADUSDT"], "provenance": {"king_train_end_utc": "2026-01-01T00:00:00Z"}}, open(f"{_dA}/config.json", "w"))
rc, j, o = gate(_dA, {"BUNDLE_CONFIG": f"{_dA}/config.json"})
check("★★ [R14-C1] a TRAINING cutoff is not an export time ⇒ refused by name, never used as the anchor",
      rc == 3 and any("export_anchor_is_a_training_cutoff" in x for x in (j or {}).get("refusals", [])), (rc, (j or {}).get("refusals")))
json.dump({"symbols_live": ["DEADUSDT"], "export_anchor_ts": BASE + 289 * 300}, open(f"{_dA}/config.json", "w"))
rc, j, o = gate(_dA, {"BUNDLE_CONFIG": f"{_dA}/config.json"})
check("★★ [R14-C1] a declared anchor on the cache axis but OFF the 4h grid ⇒ refused by name",
      rc == 3 and any("export_anchor_off_4h_grid" in x for x in (j or {}).get("refusals", [])), (rc, (j or {}).get("refusals")))
json.dump({"symbols_live": ["DEADUSDT"], "export_anchor_ts": BASE + 99999 * 300}, open(f"{_dA}/config.json", "w"))
rc, j, o = gate(_dA, {"BUNDLE_CONFIG": f"{_dA}/config.json"})
check("★★ a declared anchor NOT on this cache's axis ⇒ refusal (the bundle was built from a different cache), not a silent fallback",
      rc == 3 and any("export_anchor_off_cache_axis" in x for x in (j or {}).get("refusals", [])), (rc, (j or {}).get("refusals")))

_iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
d = fixture("export_prov_utc", syms=("XUSDT", "YUSDT"), edit=lambda a: a.__setitem__((-1, 0, 3), 0.0))
json.dump({"symbols_live": ["XUSDT"], "provenance": {"data_axis_end_utc": _iso(_PIN), "king_train_end_utc": _iso(BASE)}}, open(f"{d}/config.json", "w"))
rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
_S = (j or {}).get("sets", {}).get("bundle_symbols_live", {})
check("★★★ GREEN: the field the real exporter writes (provenance.data_axis_end_utc) is the export anchor, and the training cutoff beside it is ignored",
      rc == 0 and _S.get("checked_at_anchor") == _PIN and "data_axis_end_utc" in str(_S.get("anchor_source")), (rc, _S))
rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json", "EXPORT_ANCHOR_TS": str(_PIN)})
_S = (j or {}).get("sets", {}).get("bundle_symbols_live", {})
check("★★ EXPORT_ANCHOR_TS pinned by the caller wins and is recorded as such", rc == 0 and "pinned by the caller" in str(_S.get("anchor_source")), (rc, _S))

print("\n[7c] the MANIFEST takes part in anchor selection, so it is a recorded dependency (R14-C2)")
d = fixture("manifest_dep", syms=("XUSDT", "YUSDT"), edit=lambda a: a.__setitem__((-1, 0, 3), 0.0))
json.dump({"symbols_live": ["XUSDT"]}, open(f"{d}/config.json", "w"))
json.dump({"provenance": {"export_anchor_ts": _PIN}}, open(f"{d}/MANIFEST.json", "w"))
rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
_S = (j or {}).get("sets", {}).get("bundle_symbols_live", {})
check("★★★ [R14-C2] the MANIFEST supplies the anchor AND is recorded in the receipt's inputs, so a later edit is re-hashable",
      rc == 0 and "MANIFEST" in str(_S.get("anchor_source")) and "bundle_manifest" in (j or {}).get("inputs_sha256", {})
      and (j or {}).get("inputs_sha256", {}).get("bundle_manifest"), (rc, _S, sorted((j or {}).get("inputs_sha256", {}))))
_before = sha(f"{d}/MANIFEST.json")
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "require", f"{d}/gate.json", "gate=MEMBER_LIVENESS", "recorded_extras=1", f"self_sha={sha(GATE)}",
                    f"cache={d}/cache.npz", f"hole_cells={d}/holes.npz", f"wide_fea_v4_meta={d}/meta.npz", f"dlw_v4raw_targets={d}/targets.npz"],
                   capture_output=True, text=True)
check("★★ [R14-C2] require accepts the receipt while the MANIFEST is unchanged (green baseline for the mutation below)", r.returncode == 0, (r.stdout + r.stderr).strip()[-160:])
json.dump({"provenance": {"export_anchor_ts": BASE}}, open(f"{d}/MANIFEST.json", "w"))          # same shape, different anchor
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "require", f"{d}/gate.json", "gate=MEMBER_LIVENESS", "recorded_extras=1", f"self_sha={sha(GATE)}",
                    f"cache={d}/cache.npz", f"hole_cells={d}/holes.npz", f"wide_fea_v4_meta={d}/meta.npz", f"dlw_v4raw_targets={d}/targets.npz"],
                   capture_output=True, text=True)
check("★★★ [R14-C2] editing the MANIFEST after the PASS ⇒ require REFUSES (round 13 accepted it, because a dependency never recorded cannot be re-hashed)",
      r.returncode != 0 and sha(f"{d}/MANIFEST.json") != _before, (r.returncode, (r.stdout + r.stderr).strip()[-200:]))

print("\n[8] mask builder: MASK_IN AND semantics, sha pin, compressed cache path")
d = fixture("mask_and", syms=("XUSDT", "YUSDT"), edit=lambda a: (a.__setitem__((-1, 0, 3), 0.0), a.__setitem__((-1, 1, 3), 0.0)))
rc, mj, mz, o = mask(d); grid = mz["ts"]
mi = os.path.join(d, "mask_in.npz"); np.savez(mi, ts=grid, symbols=np.array(["XUSDT", "YUSDT"]), mask=np.array([[True, False]] * len(grid)), definition=np.array("test tradable"))
rc, mj, mz2, o = mask(d, mi, sha(mi))
n_grid = len(grid); live_only_last = 1                       # only the anchor row carries a real bar ⇒ X is live at the last anchor only
check("live ∧ MASK_IN: at the last anchor X True and Y False (MASK_IN kept Y out); the AND is not a no-op",
      rc == 0 and bool(mz2["mask"][-1, 0]) and not bool(mz2["mask"][-1, 1]), (rc, mj and mj.get("result")))
check("cells_removed_beyond_mask_in == the cells MASK_IN kept but liveness removes (X at the earlier anchors) = n_grid − 1",
      mj["result"]["cells_removed_beyond_mask_in"] == n_grid - live_only_last, (n_grid, mj and mj.get("result")))
out_before = sha(os.path.join(d, "mask.npz"))
rc, mj, mz3, o = mask(d, mi, "0" * 64)
check("wrong MASK_IN_SHA ⇒ FAIL C3, the previous output is left untouched (a failed run writes nothing)",
      rc == 1 and mj["VERDICT"] == "FAIL" and sha(os.path.join(d, "mask.npz")) == out_before, (rc, mj and mj["VERDICT"]))
rc, mj, mz4, o = mask(d, mi); check("MASK_IN without MASK_IN_SHA ⇒ UNAVAILABLE rc 3", rc == 3 and mj["VERDICT"] == "UNAVAILABLE", (rc, mj and mj["VERDICT"]))
d = fixture("compressed", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), compressed=True); rc, j, o = gate(d)
check("compressed cache (np.savez_compressed) takes the np.load fallback and gives the same PASS", rc == 0 and j["PASS"] is True, o)

print("\n[9] REQUIRED_INPUTS registration and the contract approval of the gate source")
sys.path.insert(0, HERE); import v4_gate_common as GC
check("REQUIRED_INPUTS[MEMBER_LIVENESS] == [cache, hole_cells, wide_fea_v4_meta, dlw_v4raw_targets]", GC.REQUIRED_INPUTS.get("MEMBER_LIVENESS") == ["cache", "hole_cells", "wide_fea_v4_meta", "dlw_v4raw_targets"], GC.REQUIRED_INPUTS.get("MEMBER_LIVENESS"))
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "approved", "MEMBER_LIVENESS", sha(GATE)], capture_output=True, text=True)
check("the on-disk gate source is APPROVED for MEMBER_LIVENESS in ELIGIBILITY_CONTRACT.json (rc 0)", r.returncode == 0 and r.stdout.startswith("APPROVED"), r.stdout.strip()[:120])
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "approved", "MEMBER_LIVENESS", "0" * 64], capture_output=True, text=True)
check("a foreign sha is NOT_APPROVED (rc ≠ 0) — the approval check discriminates", r.returncode != 0 and r.stdout.startswith("NOT_APPROVED"), r.stdout.strip()[:120])
d = fixture("require_flow", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0)); rc, j, o = gate(d)
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "require", f"{d}/gate.json", "gate=MEMBER_LIVENESS", f"self_sha={sha(GATE)}", f"cache={d}/cache.npz", f"hole_cells={d}/holes.npz", f"wide_fea_v4_meta={d}/meta.npz", f"dlw_v4raw_targets={d}/targets.npz"], capture_output=True, text=True)
check("require: a PASS receipt with unchanged inputs and the approved self sha ⇒ rc 0", r.returncode == 0, (r.stdout + r.stderr).strip()[-160:])
np.savez(f"{d}/holes.npz", row=np.array([288], np.int64), col=np.array([0], np.int64), symbols=np.array(["XUSDT"]))
r = subprocess.run([PY, os.path.join(HERE, "v4_gate_common.py"), "require", f"{d}/gate.json", "gate=MEMBER_LIVENESS", f"self_sha={sha(GATE)}", f"cache={d}/cache.npz", f"hole_cells={d}/holes.npz", f"wide_fea_v4_meta={d}/meta.npz", f"dlw_v4raw_targets={d}/targets.npz"], capture_output=True, text=True)
check("require: an input changed after the receipt ⇒ rc ≠ 0 (stale receipt refused)", r.returncode != 0, (r.stdout + r.stderr).strip()[-160:])

print("\n[10] ROUND 12 (R12-C4): the reviewer's eight probes — every one of them PASSed on the round-11 gate while measuring nothing")
d = fixture("r12_good", syms=("XUSDT", "YUSDT"), edit=lambda a: (a.__setitem__((-1, 0, 3), 0.0), a.__setitem__((-1, 1, 3), 0.0)), members=[0, 1])
json.dump({"symbols_live": ["XUSDT", "YUSDT"], "export_anchor_ts": _PIN}, open(f"{d}/config.json", "w"))   # R14-C1: the export end judges a DECLARED moment
rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("★ green baseline first: two live names, a real symbols_live ⇒ PASS rc 0, window 288 rows derived from the 300 s spacing",
      rc == 0 and j["PASS"] is True and j["window_rows"] == 288 and j["row_spacing_s"] == 300, (rc, j.get("window_rows"), j.get("row_spacing_s"), j.get("refusals")))

json.dump({}, open(f"{d}/config.json", "w")); rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("(1) bundle config {} ⇒ refusal naming keep_names as NOT a substitute (was: PASS with export n_names = 0)",
      rc == 3 and any("symbols_live" in x and "keep_names" in x for x in j["refusals"]), j.get("refusals"))
json.dump({"symbols_live": []}, open(f"{d}/config.json", "w")); rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("(2) symbols_live = [] ⇒ refusal 'measures nothing' (was: PASS)", rc == 3 and any("EMPTY" in x for x in j["refusals"]), j.get("refusals"))
json.dump({"symbols_live": ["XUSDT"], "keep_names": ["fea_0", "fea_1"], "export_anchor_ts": _PIN}, open(f"{d}/config.json", "w")); rc, j, o = gate(d, {"BUNDLE_CONFIG": f"{d}/config.json"})
check("(2b) a real symbols_live beside keep_names is still read from symbols_live ⇒ PASS (the fallback is gone, not the key)",
      rc == 0 and j["PASS"] is True and j["sets"]["bundle_symbols_live"]["n_names"] == 1, (rc, j["sets"].get("bundle_symbols_live")))

d = fixture("r12_frac_member", syms=("XUSDT", "YUSDT"), edit=lambda a: (a.__setitem__((-1, 0, 3), 0.0), a.__setitem__((-1, 1, 3), 0.0)), members=[0.9, 1.1])
rc, j, o = gate(d)
check("(3) members [0.9, 1.1] ⇒ refusal (was: cast to the positions [0, 1] and PASS)",
      rc == 3 and any("float member array" in x for x in j["refusals"]), j.get("refusals"))
d = fixture("r12_bool_member", syms=("XUSDT", "YUSDT"), edit=lambda a: (a.__setitem__((-1, 0, 3), 0.0), a.__setitem__((-1, 1, 3), 0.0)), members=[False, True])
rc, j, o = gate(d)
check("(4) members [False, True] ⇒ refusal (was: cast to [0, 1], i.e. a bool MASK read as a position list)",
      rc == 3 and any("boolean member array" in x for x in j["refusals"]), j.get("refusals"))

d = fixture("r12_empty_pop", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), members=[0])
import numpy as _np
_e = _np.empty(0, dtype=object)
_np.savez(f"{d}/meta.npz", E_ts=_np.array([], dtype=_np.int64), members=_e)
_np.savez(f"{d}/targets.npz", E_ts=_np.array([], dtype=_np.int64), members=_e, symbols=_np.array(["XUSDT"]))
rc, j, o = gate(d)
check("(5) king and DL both with zero anchors ⇒ refusal 'nothing was measured' (was: PASS with n_member_cells 0 on both ends)",
      rc == 3 and sum(1 for x in j["refusals"] if "empty member population" in x) == 2, j.get("refusals"))

d = fixture("r12_frac_anchor", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), E=float(BASE + 288 * 300) + 0.5)
rc, j, o = gate(d)
check("(6) E_ts offset by +0.5 s ⇒ refusal (was: truncated back onto the grid by astype(int64) and PASS)",
      rc == 3 and any("non-integral" in x for x in j["refusals"]), j.get("refusals"))

def _grid600(ts):
    ts[:] = BASE + np.arange(len(ts), dtype=np.int64) * 600
d = fixture("r12_600s", edit=lambda a: a.__setitem__((1, 0, 3), 0.0), ts_edit=_grid600, E=BASE + 288 * 600)
rc, j, o = gate(d)
check("(7) a 600 s grid: the window is 144 rows (24 h), so the only real bar 47h50m back is DEAD ⇒ FAIL (was: 288 rows = 48 h ⇒ 'live')",
      rc == 3 and j["window_rows"] == 144 and j["row_spacing_s"] == 600 and j["dead_but_member_total"] == 2, (rc, j.get("window_rows"), j.get("dead_but_member_total")))
def _nonuniform(ts):
    ts[5] = ts[5] + 7
d = fixture("r12_nonuniform", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0), ts_edit=_nonuniform)
rc, j, o = gate(d)
check("(8) a non-uniform ts axis ⇒ refusal: the 24 h window cannot be expressed in rows at all",
      rc == 3 and any("not uniformly spaced" in x for x in j["refusals"]), j.get("refusals"))

print("\n[11] ROUND 12 (R12-C2): a receipt that carries only name + PASS is no longer a prerequisite")
import subprocess as _sp
_pr = os.path.join(TMP, "prereq"); os.makedirs(_pr, exist_ok=True)
open(f"{_pr}/minimal.json", "w").write(json.dumps({"gate": "MEMBER_LIVENESS", "PASS": True}))
_env = dict(os.environ, PY=PY, R=_pr, L="/dev/stdout", CHAIN_DEVICE_DIR=HERE)
_cmd = 'source "$1"; prereq_receipt decision liveness "$2" MEMBER_LIVENESS'
r = _sp.run(["bash", "-c", _cmd, "probe", f"{HERE}/chain_lib.sh", f"{_pr}/minimal.json"], capture_output=True, text=True, env=_env)
check("the reviewer's {\"gate\": \"MEMBER_LIVENESS\", \"PASS\": true} is refused (was: rc 0, opening every downstream stage)",
      r.returncode != 0 and "FAIL_decision_prereq_liveness" in (r.stdout + r.stderr), (r.returncode, (r.stdout + r.stderr)[-150:]))
d = fixture("r12_prereq_green", edit=lambda a: a.__setitem__((-1, 0, 3), 0.0)); rc, j, o = gate(d)
r = _sp.run(["bash", "-c", _cmd, "probe", f"{HERE}/chain_lib.sh", f"{d}/gate.json"], capture_output=True, text=True, env=_env)
check("green control: the REAL receipt passes the same helper, re-verified (source approved in the contract + recorded inputs re-hashed)",
      r.returncode == 0 and "re-verified" in (r.stdout + r.stderr), (r.returncode, (r.stdout + r.stderr)[-170:]))
np.savez(f"{d}/holes.npz", row=np.array([288], np.int64), col=np.array([0], np.int64), symbols=np.array(["XUSDT"]))
r = _sp.run(["bash", "-c", _cmd, "probe", f"{HERE}/chain_lib.sh", f"{d}/gate.json"], capture_output=True, text=True, env=_env)
check("red control: an input changed AFTER the receipt ⇒ the same helper refuses (a stale receipt is not a prerequisite)",
      r.returncode != 0, (r.returncode, (r.stdout + r.stderr)[-150:]))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  gate sha {sha(GATE)[:16]}  mask sha {sha(MASK)[:16]}")
sys.exit(0 if not FAILS else 1)
