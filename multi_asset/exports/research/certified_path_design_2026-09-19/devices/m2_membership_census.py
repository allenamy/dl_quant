#!/usr/bin/env python3
"""M2 — membership look-ahead (D20), OOF coverage gap (D10) decomposition, king-seat warm-up, and S2 book exposure to
non-live / non-tradable names (READ-ONLY; design doc DESIGN_certified_production_path_2026-09-19 §3-§4).

Reads (never writes):
  king meta   /workspace/data/wide_fea_v4_meta.npz              12ea42c4  (E_ts, members, y4) — builder pod_fea_ext_clamp.py L33-40
  DL targets  /workspace/dlw_v4raw/data/dlw_targets.npz          d1976cf6  (E_ts, members, y4s) — builder pod_dlw_targets_raw.py L116-127
  universe    /workspace/uplift_r2_2026-09-13/P2/work/universe.npz 6322b573 (ts, pit)
  liveness    /workspace/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz 9b59678b (FP3 MEMBER_LIVENESS, tradable AND live)
  tradability /workspace/fx_data_2026-09-13/out/trd/tradability_v1.npz 54d409d0 (state_W24H: 2 = TRADABLE)
  S2 records  RUN_S2_{v4,A0pred}_s42.json + .vec.npz (pins as M1)
Writes only: /workspace/certified_path_design_2026-09-19/receipts/M2_MEMBERSHIP_CENSUS.json

Sections
 (a) LOOKAHEAD exits: j in members[i-1] (finite forward label at i-1 by construction) and y4[i, j] non-finite => j cannot be a member at i
     (membership requires a finite FORWARD 4h label, builder L37 / L124). Split permanent (never a member again) vs transient.
     Invariant check: members[i] with non-finite y4[i] must be 0.
 (b) D10 decomposition on the S2 axis (v4_s42 records): production members, king/F10 scored, and research members outside PIT(A)
     (crowding: the research top-400 is drawn from all 829 names, production from PIT names), plus look-ahead exits among PIT names.
 (c) king seat warm-up: first served anchor, first anchor with >= 900 king-served leg returns in the seat window, share of anchors
     with a non-equal-weight seat and w3[0] > 0 by quarter.
 (d) exposure: gross share of the S2 P2-CMB book (0.55 kc + 0.45 fc, hold when no state) and P2-LIT book (combo | king H | hold)
     on names outside the FP3 liveness mask and on names whose tradability state_W24H != TRADABLE, per year.
"""
import os, sys, json, time, hashlib, collections, calendar
import numpy as np

W = "/workspace"
SRC = {"king_meta": (f"{W}/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"),
       "dl_targets": (f"{W}/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
       "universe": (f"{W}/uplift_r2_2026-09-13/P2/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7"),
       "liveness": (f"{W}/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz", "9b59678b4529246cdf46fcc029f1cc36ea75e908aa1dcc63a4af9f8c67a2dfa7"),
       "tradability": (f"{W}/fx_data_2026-09-13/out/trd/tradability_v1.npz", "54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302"),
       "S2_v4_s42": (f"{W}/uplift_r2_2026-09-13/P2/receipts/RUN_S2_v4_s42.json", "4c5612f613ddad105d7c8997dcdc5a37bda8ccb8892b80cf18b370d325232bc6"),
       "S2_A0pred_s42": (f"{W}/uplift_r2_2026-09-13/P2/receipts/RUN_S2_A0pred_s42.json", "d01063c0ee68a48799229aef60736e7a1a8e46dbbdc9d5d72f3f227f95affbbe")}
OUT = f"{W}/certified_path_design_2026-09-19/receipts/M2_MEMBERSHIP_CENSUS.json"
H4 = 14400; TRADABLE = 2


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def qtr(t): g = time.gmtime(int(t)); return f"{g.tm_year}Q{(g.tm_mon - 1) // 3 + 1}"


def lookahead(E, MS, Y4, tag):
    nA = len(E); last_member = np.full(829, -1, np.int64)
    for i in range(nA):
        last_member[np.asarray(MS[i], np.int64)] = i
    inv = 0; out = collections.defaultdict(collections.Counter); names = collections.defaultdict(set)
    for i in range(nA):
        m = np.asarray(MS[i], np.int64); inv += int((~np.isfinite(Y4[i, m])).sum())
        if i == 0 or E[i] - E[i - 1] != H4: continue
        p = np.asarray(MS[i - 1], np.int64)
        la = p[~np.isfinite(Y4[i, p])]
        if len(la) == 0: continue
        Yk = str(yr(E[i])); c = out[Yk]
        c["cells"] += len(la); c["anchors_with_any"] += 1
        perm = la[last_member[la] < i]; c["permanent"] += len(perm); c["transient"] += len(la) - len(perm)
        names[Yk] |= set(int(x) for x in la)
    res = {}
    for Yk, c in sorted(out.items()):
        d = dict(c); d["distinct_names"] = len(names[Yk]); res[Yk] = d
    return {"array": tag, "invariant_members_with_nonfinite_forward_label": inv, "by_year": res}


def vec_rows(V, nm, k):
    a, b = V[nm + "_off"][k], V[nm + "_off"][k + 1]
    return V[nm + "_idx"][a:b], V[nm + "_val"][a:b]


def main():
    assert set(os.environ) <= {"PATH", "HOME", "LC_CTYPE", "PWD", "SHLVL", "_", "OLDPWD"}, sorted(os.environ)
    t0 = time.time(); shas = {}
    for k, (p, s) in SRC.items():
        got = sha(p); assert got == s, (k, got); shas[k] = got
    KM = np.load(SRC["king_meta"][0], allow_pickle=True); KE = KM["E_ts"].astype(np.int64); KMS = KM["members"]; KY = np.array(KM["y4"])
    DT = np.load(SRC["dl_targets"][0], allow_pickle=True); DE = DT["E_ts"].astype(np.int64); DMS = DT["members"]; DY = np.array(DT["y4s"])
    doc = {"inputs_sha256": shas}
    # (a)
    doc["a_lookahead_exits"] = {"king_meta": lookahead(KE, KMS, KY, "wide_fea_v4_meta"), "dl_targets": lookahead(DE, DMS, DY, "dlw_v4raw targets")}
    print("a done", round(time.time() - t0, 1), flush=True)
    # (b) D10 decomposition on the S2 axis
    U = np.load(SRC["universe"][0], allow_pickle=True); UT = U["ts"].astype(np.int64); PIT = np.array(U["pit"]); urow = {int(t): i for i, t in enumerate(UT)}
    krow = {int(t): i for i, t in enumerate(KE)}; drow = {int(t): i for i, t in enumerate(DE)}
    R = json.load(open(SRC["S2_v4_s42"][0]))["records"]
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in R:
        A = int(r["anchor"]); Yk = str(yr(A)); ko = r.get("king_oof") or {}; fo = r.get("f10_oof") or {}
        pm = int(ko.get("n_members") or 0); a = acc[Yk]; a["prod_members"].append(pm)
        pit = PIT[urow[A]]
        if ko.get("served"): a["king_gap"].append(pm - int(ko.get("n_finite") or 0))
        if fo.get("served"): a["f10_gap"].append(pm - int(fo.get("n_scored") or 0))
        if A in krow:
            i = krow[A]; m = np.asarray(KMS[i], np.int64)
            a["king_research_members"].append(len(m)); a["king_research_outside_pit"].append(int((~pit[m]).sum()))
            if i > 0 and KE[i] - KE[i - 1] == H4:
                p = np.asarray(KMS[i - 1], np.int64); la = p[~np.isfinite(KY[i, p])]
                a["king_lookahead_exits_in_pit"].append(int(pit[la].sum()))
        if A in drow:
            i = drow[A]; m = np.asarray(DMS[i], np.int64)
            a["dl_research_members"].append(len(m)); a["dl_research_outside_pit"].append(int((~pit[m]).sum()))
            if i > 0 and DE[i] - DE[i - 1] == H4:
                p = np.asarray(DMS[i - 1], np.int64); la = p[~np.isfinite(DY[i, p])]
                a["dl_lookahead_exits_in_pit"].append(int(pit[la].sum()))
    doc["b_d10_decomposition_v4_s42_axis"] = {Yk: {k: {"mean": round(float(np.mean(v)), 3), "n": len(v), "max": int(np.max(v))} for k, v in d.items() if len(v)}
                                              for Yk, d in sorted(acc.items())}
    print("b done", round(time.time() - t0, 1), flush=True)
    # (c) king seat warm-up (v4_s42 and A0pred_s42)
    seat = {}
    for arm in ("S2_v4_s42", "S2_A0pred_s42"):
        RR = R if arm == "S2_v4_s42" else json.load(open(SRC[arm][0]))["records"]
        served = [int(r["anchor"]) for r in RR if (r.get("king_oof") or {}).get("served")]
        cum = 0; first900 = None
        for r in RR:
            if (r.get("king_oof") or {}).get("served"): cum += 1
            if cum >= 900 and first900 is None: first900 = int(r["anchor"])
        q = collections.defaultdict(collections.Counter)
        for r in RR:
            A = int(r["anchor"])
            if A < calendar.timegm((2023, 10, 1, 0, 0, 0)): continue
            w3 = (r.get("signal") or {}).get("w3")
            if w3 is None: continue
            c = q[qtr(A)]; c["n"] += 1
            eq = all(abs(float(x) - 0.3333) < 1e-3 for x in w3)
            c["king_seat_gt0_not_equalweight"] += int(float(w3[0]) > 0 and not eq); c["equal_weight_fallback"] += int(eq)
            c["king_seat_sum"] += float(w3[0])
        seat[arm] = {"first_served": iso(served[0]) if served else None, "anchor_with_900_served_rows": iso(first900) if first900 else None,
                     "by_quarter": {k: {"n": v["n"], "king_seat_gt0_not_equalweight": v["king_seat_gt0_not_equalweight"], "equal_weight_fallback": v["equal_weight_fallback"],
                                        "mean_king_seat": round(v["king_seat_sum"] / v["n"], 4)} for k, v in sorted(q.items())}}
    doc["c_king_seat_warmup"] = seat
    print("c done", round(time.time() - t0, 1), flush=True)
    # (d) exposure of S2 books to non-live / non-tradable names
    LV = np.load(SRC["liveness"][0], allow_pickle=True); LT = LV["ts"].astype(np.int64); LM = np.array(LV["mask"]); lrow = {int(t): i for i, t in enumerate(LT)}
    TR = np.load(SRC["tradability"][0], allow_pickle=True); TT = TR["anchor_ts"].astype(np.int64); TS = np.array(TR["state_W24H"]); trow = {int(t): i for i, t in enumerate(TT)}
    assert [str(s) for s in LV["symbols"]] == [str(s) for s in TR["symbols"]] == [str(s) for s in U["symbols"]]
    expo = {}
    for arm in ("S2_v4_s42", "S2_A0pred_s42"):
        RR = R if arm == "S2_v4_s42" else json.load(open(SRC[arm][0]))["records"]
        vp = SRC[arm][0].replace(".json", ".vec.npz"); _Z = np.load(vp); V = {k_: np.array(_Z[k_]) for k_ in _Z.files}
        cmb = np.zeros(829); lit = np.zeros(829); acc2 = collections.defaultdict(collections.Counter)
        for k, r in enumerate(RR):
            A = int(r["anchor"]); tf = r.get("traded_file")
            ki, kv = vec_rows(V, "kc", k); fi, fv = vec_rows(V, "fc", k)
            if len(ki) or len(fi):
                w = np.zeros(829); w[ki] += 0.55 * kv; w[fi] += 0.45 * fv; w[np.abs(w) <= 1e-9] = 0.0; cmb = w
            if tf == "combo": lit = cmb.copy()
            elif tf == "king":
                hi, hv = vec_rows(V, "king", k); w = np.zeros(829); w[hi] = hv; lit = w
            Yk = str(yr(A)); c = acc2[Yk]; c["n"] += 1
            for nm_, book in (("cmb", cmb), ("lit", lit)):
                g = np.abs(book).sum()
                if g <= 0: continue
                c[nm_ + "_gross"] += g
                if A in lrow:
                    dead = ~LM[lrow[A]]; c[nm_ + "_gross_nonlive"] += np.abs(book[dead]).sum(); c[nm_ + "_names_nonlive"] += int((np.abs(book) > 0)[dead].sum()); c[nm_ + "_anch_live_ok"] += 1
                if A in trow:
                    nt = TS[trow[A]] != TRADABLE; c[nm_ + "_gross_nontradable"] += np.abs(book[nt]).sum(); c[nm_ + "_names_nontradable"] += int((np.abs(book) > 0)[nt].sum())
        expo[arm] = {Yk: {"n": c["n"],
                          **{f"{b}_gross_share_nonlive": (round(c[f"{b}_gross_nonlive"] / c[f"{b}_gross"], 6) if c[f"{b}_gross"] else None) for b in ("cmb", "lit")},
                          **{f"{b}_book_name_anchor_cells_nonlive": c[f"{b}_names_nonlive"] for b in ("cmb", "lit")},
                          **{f"{b}_gross_share_nontradable_W24H": (round(c[f"{b}_gross_nontradable"] / c[f"{b}_gross"], 6) if c[f"{b}_gross"] else None) for b in ("cmb", "lit")},
                          **{f"{b}_book_name_anchor_cells_nontradable": c[f"{b}_names_nontradable"] for b in ("cmb", "lit")},
                          "anchors_on_liveness_axis": c["cmb_anch_live_ok"]} for Yk, c in sorted(acc2.items())}
    doc["d_book_exposure_nonlive_nontradable"] = expo
    print("d done", round(time.time() - t0, 1), flush=True)
    doc.update({"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "python": sys.version.split()[0], "numpy": np.__version__,
                "env": dict(os.environ), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runtime_s": round(time.time() - t0, 1)})
    tmp = OUT + ".tmp"; json.dump(doc, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, OUT)
    print("WROTE", OUT, sha(OUT))


if __name__ == "__main__":
    main()
