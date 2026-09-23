"""fresh_where.py — REPORT ONLY, no gate. Locates the FRESH − NEW_S book-layer gap in the channels the certified engine already
records, and tests one named mechanism hypothesis against the data instead of asserting it.

Nothing here is recomputed from paths: every channel number is read out of FRESH_STATS.json's own path tables (the same device that
produced the verdict), and the publication-gate counts are read out of each arm's combo scaled_diagnostic.npz.

Hypothesis under test (H-SEAT): FRESH's King leg scores better ⇒ the msharpe seat puts more weight on King ⇒ King and F10 disagree
⇒ the 0.55/0.45 mix cancels ⇒ raw gross falls under the preflight floor ⇒ the anchor is published as the fallback form instead of the
combo. If that were the carrier of the loss, the arm that loses should be the arm that fails the gross preflight more often.
The device prints the counts and states whether the hypothesis survives; it does NOT decide anything.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fresh_where.py PATH,HOME,LC_CTYPE <FRESH_STATS.json> <out.json> <out.md>
"""
import os, sys, json, hashlib
import numpy as np
WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
STATS, OUT, OUTMD = sys.argv[2:5]
W = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
SEGS = ("2023H2", "2024", "2025", "2026", "judge")
ARMS = ("FRESH_s42", "NEWS_s42", "FRESH_s2027", "NEWS_s2027")
CH = ("g", "price", "funding_paid", "fee", "turnover_over_gross", "halt_anchors", "hold_anchors")
COMBO = {"FRESH_s42": f"{W}/work/combo_s42", "NEWS_s42": f"{N}/work/combo_s42",
         "FRESH_s2027": f"{W}/work/combo_s2027", "NEWS_s2027": f"{N}/work/combo_s2027"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    R = json.load(open(STATS)); T = R["tables"]
    rec = {"device": "fresh_where.py", "self_sha256": sha(os.path.abspath(__file__)), "status": "REPORT ONLY — no gate, no verdict",
           "reads": {"stats": {"path": STATS, "sha256": sha(STATS)}}, "channels": {}, "publication_gate": {}, "H_SEAT": {}}
    for seg in SEGS:
        rec["channels"][seg] = {a: {k: T[a]["base"][seg]["paths"][k]["path_mean"] for k in CH} for a in ARMS}
    for a, d in COMBO.items():
        p = f"{d}/scaled_diagnostic.npz"; C = np.load(p, allow_pickle=True)
        rs = np.array([str(x) for x in C["reason"]]); u, c = np.unique(rs, return_counts=True)
        rec["publication_gate"][a] = {"npz_sha256": sha(p), "n_anchors": int(len(rs)), "counts": dict(zip(u.tolist(), [int(x) for x in c]))}
    # H-SEAT: does the arm that loses also fail the gross preflight more often? Per seed.
    hs = {}
    for s in ("s42", "s2027"):
        f, n = f"FRESH_{s}", f"NEWS_{s}"
        gf = rec["publication_gate"][f]["counts"].get("gross", 0); gn = rec["publication_gate"][n]["counts"].get("gross", 0)
        d_ret = T[f]["base"]["judge"]["paths"]["total_return"]["path_mean"] - T[n]["base"]["judge"]["paths"]["total_return"]["path_mean"]
        hs[s] = {"gross_preflight_failures": {"FRESH": gf, "NEWS": gn, "FRESH_minus_NEWS": gf - gn},
                 "judge_total_return_FRESH_minus_NEWS": d_ret,
                 "predicted_by_H_SEAT": "FRESH fails the gross preflight MORE than NEW_S", "observed": "MORE" if gf > gn else "FEWER"}
    same_direction = len({v["observed"] for v in hs.values()}) == 1
    rec["H_SEAT"] = {"per_seed": hs,
                     "SURVIVES": bool(same_direction and all(v["observed"] == "MORE" for v in hs.values())),
                     "verdict": ("REFUTED as the carrier: the two seeds move in OPPOSITE directions on the gross-preflight count while BOTH lose "
                                 "by a similar amount, so the preflight/fallback channel cannot be what carries the loss")
                               if not same_direction else
                                ("consistent with the data on both seeds — NOT established; a consistent sign is not a sized mechanism, and no "
                                 "counterfactual was run" if all(v["observed"] == "MORE" for v in hs.values()) else
                                 "REFUTED: both seeds fail the gross preflight LESS often in FRESH, the opposite of the prediction")}
    # where the gap sits, judge window, per seed
    gap = {}
    for s in ("s42", "s2027"):
        f, n = f"FRESH_{s}", f"NEWS_{s}"
        gap[s] = {k: T[f]["base"]["judge"]["paths"][k]["path_mean"] - T[n]["base"]["judge"]["paths"][k]["path_mean"] for k in CH}
        gap[s]["total_return"] = T[f]["base"]["judge"]["paths"]["total_return"]["path_mean"] - T[n]["base"]["judge"]["paths"]["total_return"]["path_mean"]
    rec["judge_window_gap_FRESH_minus_NEWS"] = gap
    # The engine's own identity (bt_tables.py L8/L183): g = price − funding_paid − fee − unknown_excluded, each the mean over the
    # segment's anchors of 1e4·x/(gross_mult·NAV_start), i.e. bps per anchor. Asserting it here is what licenses calling the split a
    # DECOMPOSITION rather than a list of correlated channels — and it is what lets each channel be given a SHARE of the gap.
    share = {}
    for s in ("s42", "s2027"):
        f, n = f"FRESH_{s}", f"NEWS_{s}"
        d = {k: T[f]["base"]["judge"]["paths"][k]["path_mean"] - T[n]["base"]["judge"]["paths"][k]["path_mean"]
             for k in ("g", "price", "funding_paid", "fee", "unknown_excluded")}
        resid = d["g"] - (d["price"] - d["funding_paid"] - d["fee"] - d["unknown_excluded"])
        tot = abs(d["price"]) + abs(d["funding_paid"]) + abs(d["fee"]) + abs(d["unknown_excluded"])
        share[s] = {"gap_in_g_bps_per_anchor": d["g"], "identity_residual_bps_per_anchor": resid,
                    "IDENTITY_HOLDS": bool(abs(resid) <= 1e-6 * max(1.0, abs(d["g"]))),
                    "contribution_bps_per_anchor": {"price": d["price"], "funding_paid": -d["funding_paid"], "fee": -d["fee"],
                                                    "unknown_excluded": -d["unknown_excluded"]},
                    "share_of_absolute_movement": {k: (abs(v) / tot if tot else None) for k, v in
                                                   (("price", d["price"]), ("funding_paid", d["funding_paid"]), ("fee", d["fee"]),
                                                    ("unknown_excluded", d["unknown_excluded"]))}}
    rec["gap_decomposition_judge"] = {"identity": "g = price − funding_paid − fee − unknown_excluded (bt_tables.py L8/L183); "
                                                  "each channel is the mean over the segment's anchors of 1e4·x/(gross_mult·NAV_start), i.e. bps per anchor",
                                      "per_seed": share,
                                      "note": "g is bps per ANCHOR; total_return in the level tables is a cumulative compounded return. "
                                              "They are different quantities and are NOT compared to each other here."}
    for s, v in share.items():
        assert v["IDENTITY_HOLDS"], f"{s}: channel identity does not close, residual {v['identity_residual_bps_per_anchor']}"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)

    L = []
    L.append(f"<!-- generated by fresh_where.py {rec['self_sha256'][:16]} from {os.path.basename(STATS)} {sha(STATS)[:16]}; REPORT ONLY, no gate -->\n")
    L.append("### 差落在哪个通道(判据窗,路径均值,FRESH − NEW_S)\n")
    L.append("引擎自己的恒等式 `g = price − funding_paid − fee − unknown_excluded`(bt_tables.py L8/L183),每个通道是该段锚上 "
             "`1e4·x/(gross_mult·NAV_start)` 的均值,即 **bps/锚**。下表先断言恒等式闭合,再给每个通道**占绝对移动的份额** —— "
             "有份额才敢把它叫分解,而不是一串相关的通道。`g` 是 bps/锚,水平表里的总收益是累计复利收益,**两者不是一个量,此处不相互比较**。\n")
    L.append("| 种子 | g 的差(bps/锚) | 恒等式残差 | price | −funding_paid | −fee | −unknown | price 份额 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s in ("s42", "s2027"):
        v = share[s]; c = v["contribution_bps_per_anchor"]; sh = v["share_of_absolute_movement"]
        L.append(f"| {s} | {v['gap_in_g_bps_per_anchor']:+.4f} | {v['identity_residual_bps_per_anchor']:+.2e} | {c['price']:+.4f} | "
                 f"{c['funding_paid']:+.4f} | {c['fee']:+.4f} | {c['unknown_excluded']:+.4f} | {sh['price']:.1%} |")
    L.append("\n| 种子 | 判据窗总收益差(累计) | 换手/gross 差 |")
    L.append("|---|---|---|")
    for s in ("s42", "s2027"):
        g = gap[s]
        L.append(f"| {s} | {g['total_return']:+.4f} | {g['turnover_over_gross']:+.4f} |")
    L.append("\n### 逐段逐臂通道(路径均值)\n")
    L.append("| 段 | 臂 | g | price | funding_paid | fee | 换手/gross | halt 锚 | hold 锚 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for seg in SEGS:
        for a in ARMS:
            c = rec["channels"][seg][a]
            L.append(f"| {seg} | {a} | {c['g']:+.4f} | {c['price']:+.4f} | {c['funding_paid']:+.4f} | {c['fee']:+.4f} | {c['turnover_over_gross']:.4f} | {c['halt_anchors']:.1f} | {c['hold_anchors']:.1f} |")
    L.append("\n### 发布门计数(combo scaled_diagnostic 的 reason)\n")
    L.append("| 臂 | 锚数 | publish | gross(预检未过) |")
    L.append("|---|---|---|---|")
    for a in ARMS:
        p = rec["publication_gate"][a]
        L.append(f"| {a} | {p['n_anchors']} | {p['counts'].get('publish', 0)} | {p['counts'].get('gross', 0)} |")
    L.append(f"\n**H-SEAT 假设检验**:{rec['H_SEAT']['verdict']}\n")
    for s, v in hs.items():
        L.append(f"- {s}: gross 预检未过 FRESH {v['gross_preflight_failures']['FRESH']} vs NEW_S {v['gross_preflight_failures']['NEWS']} "
                 f"({v['observed']});判据窗总收益差 {v['judge_total_return_FRESH_minus_NEWS']:+.4f}")
    open(OUTMD + ".tmp", "w").write("\n".join(L) + "\n"); os.replace(OUTMD + ".tmp", OUTMD)
    print(f"FRESH_WHERE written {OUT} {sha(OUT)} H_SEAT_SURVIVES={rec['H_SEAT']['SURVIVES']} "
          f"identity_holds={ {s: share[s]['IDENTITY_HOLDS'] for s in share} } "
          f"gap_in_g_bps_per_anchor={ {s: round(share[s]['gap_in_g_bps_per_anchor'], 4) for s in share} } "
          f"price_share={ {s: round(share[s]['share_of_absolute_movement']['price'], 3) for s in share} } "
          f"fee_share={ {s: round(share[s]['share_of_absolute_movement']['fee'], 3) for s in share} }", flush=True)


if __name__ == "__main__":
    main()
