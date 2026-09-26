#!/usr/bin/env python3
"""Derive the gap-class-fix producer tree from the PRODUCTION bytes (read-only on ~/wide_shadow).
Every edit is an exact-once string replacement against combo_stage.py sha 12a76de8…; any drift in production refuses.
usage: python3 make_tree.py <out tree dir>   (writes <out>/fea171/combo_stage.py, copies prev_state.py, PATCH_RECEIPT.json)"""
import hashlib, json, os, shutil, sys, time
HOME = os.path.expanduser("~"); SRC = f"{HOME}/wide_shadow/fea171/combo_stage.py"
BASE_SHA = "12a76de89831fb42d05ec722f2e2506d6b288b4b9f5b86be04bc390c789a62a9"
HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = [
("import durable_io as DIO   # C: durable state writes (imported here, before any executor path is put on sys.path)\n",
 "import durable_io as DIO   # C: durable state writes (imported here, before any executor path is put on sys.path)\n"
 "import prev_state as PS    # gap class fix 2026-09-26: previous state = most recent valid state before A, named source\n"),
("""# H_prev: 上上锚权重文件
wf = f"{WS}/state/weights/{A-14400}.npz"
H = np.zeros(NW)
if os.path.exists(wf):
    z = np.load(wf); H[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
""",
"""# H_prev: 生产者上一份权重文件。gap 类修复(2026-09-26): anchor<A 的最近一份有效文件 —— 生产者 st.H 跨缺锚同样承接最近一次计算,
# 原先恰好 A-14400 的取法在缺锚后给零向量(自平价①失真, 且作 kc/f10 回落源时 gross≈0.07 ⇒ 飞前中止并毒化后续锚)
STATE_LOOKUP = {}
_lk_w = PS.latest_state(f"{WS}/state/weights/{{a}}.npz", A, NW, anchor_key=False)
STATE_LOOKUP["weights"] = PS.record(_lk_w)
H = _lk_w["vec"] if _lk_w["vec"] is not None else np.zeros(NW)
"""),
("""h_source = "king_fallback"
hf_prev = f"{HERE}/state_H_f10_{A - 14400}.npz"
hf_p = f"{HERE}/state_H_f10_{A}.npz"
H_f10_prev = H.copy()
if os.path.exists(hf_prev):
    zz2 = np.load(hf_prev)
    if int(zz2["anchor"]) == A - 14400:
        H_f10_prev = np.zeros(NW); H_f10_prev[zz2["idx"].astype(np.int64)] = zz2["val"]
        h_source = "own"
elif os.path.exists(f"{HERE}/state_H_f10.npz"):""",
"""h_source = "king_fallback"
hf_p = f"{HERE}/state_H_f10_{A}.npz"
H_f10_prev = H.copy()
_lk_f10 = PS.latest_state(f"{HERE}/state_H_f10_{{a}}.npz", A, NW)   # gap 类修复: 最近一份有效状态(own / own_gap<m>[_rejected<n>][_beyond_bound])
STATE_LOOKUP["f10"] = PS.record(_lk_f10)
if _lk_f10["vec"] is not None:
    H_f10_prev = _lk_f10["vec"]
    h_source = _lk_f10["source"]
elif os.path.exists(f"{HERE}/state_H_f10.npz"):"""),
("""def _load_state2(pth, fallback, tag):
    if os.path.exists(pth):
        zz = np.load(pth)
        if int(zz["anchor"]) == A - 14400:
            v = np.zeros(NW); v[zz["idx"].astype(np.int64)] = zz["val"].astype(np.float64)
            return v, "own"
    return fallback.copy(), tag
H_kc_prev, kc_src = _load_state2(f"{HERE}/state_H_kc_{A-14400}.npz", H, "warmstart_live_H")
H_fc_prev, fc_src = _load_state2(f"{HERE}/state_H_fc_{A-14400}.npz", H_f10_prev, "warmstart_f10_H")
""",
"""def _load_state2(leg, fallback, tag):
    # gap 类修复(2026-09-26): 最近一份有效状态; 无任何有效状态才用具名回落(并页报)
    lk = PS.latest_state(f"{HERE}/state_H_{leg}_{{a}}.npz", A, NW)
    STATE_LOOKUP[leg] = PS.record(lk)
    if lk["vec"] is not None:
        return lk["vec"], lk["source"]
    STATE_LOOKUP[leg]["fallback"] = tag
    return fallback.copy(), tag
H_kc_prev, kc_src = _load_state2("kc", H, "warmstart_live_H")
H_fc_prev, fc_src = _load_state2("fc", H_f10_prev, "warmstart_f10_H")
_GAP_NONTRIVIAL = any(r.get("source") != "own" for r in STATE_LOOKUP.values())
_GAP_PAGE = [f"{k}: {r.get('source') or 'NO_VALID_STATE→' + str(r.get('fallback'))}"
             + (f" (used {r['anchor']}, gap {r['gap']})" if r.get("anchor") else "")
             + "".join(f"; rejected {os.path.basename(x['path'])}: {x['reason']}" for x in r.get("rejected", []))
             for k, r in STATE_LOOKUP.items() if r.get("source") is None or r.get("rejected") or r.get("beyond_bound")]
if _GAP_NONTRIVIAL:
    log(f"STATE_LOOKUP (gap class fix) {json.dumps({k: (r.get('source'), r.get('anchor')) for k, r in STATE_LOOKUP.items()})}")
"""),
("""           "n_f10_scored": int(okf.sum()), "ftrim": ftrim_rec},
          indent=1)""",
"""           "n_f10_scored": int(okf.sum()), "ftrim": ftrim_rec,
           **({"state_lookup": STATE_LOOKUP} if _GAP_NONTRIVIAL else {})},
          indent=1)"""),
("""    _status = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now0)), "ok": False, "step": "start"}
""",
"""    _status = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now0)), "ok": False, "step": "start",
               **({"state_lookup": STATE_LOOKUP, "state_lookup_page": _GAP_PAGE} if _GAP_NONTRIVIAL else {})}
"""),
("""    except SystemExit:
        raise
    except Exception as _e:
        # Never restore King: this invocation may not have published, or the
        # deadline may have passed. A partial pair is rejected by the reader.
        _bail(f"{type(_e).__name__}: {str(_e)[:220]}")""",
"""    except SystemExit:
        raise
    except Exception as _e:
        # Never restore King: this invocation may not have published, or the
        # deadline may have passed. A partial pair is rejected by the reader.
        _bail(f"{type(_e).__name__}: {str(_e)[:220]}")
    # gap 类修复: 状态来源需要人知道(被拒文件 / 越界 / 无有效状态)⇒ 发布之后 HIGH 页报(不占截止余量; 与 M3 同: 演练不发, 只记)
    if _GAP_PAGE:
        _gap_msg = (f"combo 写者: 上一锚状态非常规 [{time.strftime('%m-%d %H:%M', time.gmtime(A))}锚] 已发布, 来源如下(界 {PS.MAX_GAP_ANCHORS} 锚):\\n"
                    + "\\n".join(_GAP_PAGE))[:1500]
        log(f"GAP_PAGE {'(rehearsal: recorded, not sent)' if _rehearsal else 'HIGH'}: {_gap_msg.replace(chr(10), ' | ')}")   # one log line per event
        if not _rehearsal:
            try:
                _page("HIGH", _gap_msg)
            except Exception:                         # noqa: BLE001 — a page failure never turns a published book into an abort
                pass"""),
("""    MH_MISSING = 0
    for i in range(len(e_rows)):
        _ea = int(rts[e_rows[i]])
        if _ea == A:
            ms_arr[i] = pm
        elif _ea in MEMBERS_HIST:
            ms_arr[i] = np.asarray(MEMBERS_HIST[_ea], np.int64)
        else:
            ms_arr[i] = np.zeros(0, np.int64); MH_MISSING += 1
    log(f"NC A2 member history: {len(e_rows) - MH_MISSING}/{len(e_rows)} window anchors have members (missing {MH_MISSING})")
""",
"""    MH_MISSING = 0
    # gap 类修复(ACCEPTANCE AMENDMENT 2): 生产者没跑的锚在 members_hist 里无条目 ⇒ 用生产者成员规则(members_rule.py = shadow_loop_v3 L676-L701)
    # 在同一份滚动缓存上现算, fetch 名单取 A 时刻的(V2 实测: 事后重算平均 Jaccard 0.9987, carry-forward 0.9914); 历史齐全时本段不执行
    MH_RECOMPUTED, MH_RECOMPUTE_ERR = {}, {}
    _mh_need = [int(rts[e_rows[i]]) for i in range(len(e_rows)) if int(rts[e_rows[i]]) != A and int(rts[e_rows[i]]) not in MEMBERS_HIST]
    if _mh_need:
        import members_rule as MR, tradability as _TR
        _cr = json.load(open(f"{WS}/shadow_bundle/crypto_axis.json"))
        assert [str(x) for x in _cr["symbols"]] == [str(x) for x in _symbols], "crypto_axis.json axis differs from the producer axis"
        _crypto = np.array([bool(x) for x in _cr["crypto"]], bool)
        _cd16 = RD.astype(np.float16); _cd16[:, :, 0] = _source_snapshot["ch0_storage_f16"]   # the producer's st.cd (f16 storage, ch0 not rr)
        _fm = MR.fetch_mask_from_aux(aux, [str(x) for x in _symbols])
        for _t in _mh_need:
            try:
                MH_RECOMPUTED[_t] = MR.members_at(rts, _cd16, _t, _crypto, _fm, P, _TR, NC)
            except Exception as _me:                  # noqa: BLE001 — a failed recompute leaves the anchor memberless (named), never blocks
                MH_RECOMPUTE_ERR[_t] = f"{type(_me).__name__}: {str(_me)[:80]}"
        del _cd16
    for i in range(len(e_rows)):
        _ea = int(rts[e_rows[i]])
        if _ea == A:
            ms_arr[i] = pm
        elif _ea in MEMBERS_HIST:
            ms_arr[i] = np.asarray(MEMBERS_HIST[_ea], np.int64)
        elif _ea in MH_RECOMPUTED:
            ms_arr[i] = MH_RECOMPUTED[_ea]
        else:
            ms_arr[i] = np.zeros(0, np.int64); MH_MISSING += 1
    log(f"NC A2 member history: {len(e_rows) - MH_MISSING}/{len(e_rows)} window anchors have members (missing {MH_MISSING})")
    if _mh_need:
        log(f"MH_RECOMPUTED (gap class fix) {len(MH_RECOMPUTED)} anchors {sorted(MH_RECOMPUTED)[:12]} errors {MH_RECOMPUTE_ERR}")
"""),
("""           **({"state_lookup": STATE_LOOKUP} if _GAP_NONTRIVIAL else {})},""",
"""           **({"state_lookup": STATE_LOOKUP} if _GAP_NONTRIVIAL else {}),
           **({"members_recomputed": {str(t): int(len(v)) for t, v in sorted(MH_RECOMPUTED.items())}, "members_recompute_errors": {str(t): e for t, e in MH_RECOMPUTE_ERR.items()}}
              if (MH_RECOMPUTED or MH_RECOMPUTE_ERR) else {})},"""),
]
def main():
    out = os.path.abspath(sys.argv[1]); assert not os.path.exists(out), f"refusing to overwrite {out}"
    raw = open(SRC, "rb").read(); assert hashlib.sha256(raw).hexdigest() == BASE_SHA, "production combo_stage.py drifted from 12a76de8"
    s = raw.decode()
    for old, new in EDITS:
        n = s.count(old); assert n == 1, f"edit anchor occurs {n} times: {old[:60]!r}"
        s = s.replace(old, new)
    os.makedirs(f"{out}/fea171")
    b = s.encode()
    with open(f"{out}/fea171/combo_stage.py", "wb") as f: f.write(b)
    for _f in ("prev_state.py", "tests_prev_state.py", "members_rule.py"):
        shutil.copyfile(f"{HERE}/tree/fea171/{_f}", f"{out}/fea171/{_f}")
    rec = {"device": "make_tree.py", "device_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "base": {"fea171/combo_stage.py": BASE_SHA}, "gap_classfix": True, "n_edits": len(EDITS),
           "files": {r: hashlib.sha256(open(f"{out}/{r}", "rb").read()).hexdigest() for r in ("fea171/combo_stage.py", "fea171/prev_state.py", "fea171/tests_prev_state.py", "fea171/members_rule.py")}}
    with open(f"{out}/PATCH_RECEIPT.json", "w") as f: json.dump(rec, f, indent=1)
    print("GAP_TREE_OK", json.dumps(rec["files"]))
if __name__ == "__main__":
    main()
