#!/usr/bin/env python3
"""十次平仓窗: 旧原始件(v2/v3 拉取, 无查询清单/页凭据) vs v4.1 新拉取原始件, 逐行对照。只读, 不联网。

userTrades: 键 (symbol, id)。报 只在旧 / 只在新 / 同键字段不同(qty, quoteQty, price, commission, commissionAsset, realizedPnl,
            buyer, maker, orderId, side, time; 数值按 Decimal 比, 其余按值比)。
income:     行身份 = 全部字段的规范 JSON(与 fetch_income_paged 的 row_identity 同义)按多重集比; 另按 (incomeType, tranId, asset) 键报金额差。
另报: 旧件声明的查询个数 vs 新件的实际查询清单; v4.1 新收据与冻结 v3 收据 A/C 是否逐字段相同(判词两行除外)。
usage: compare_flatten_raw_old_vs_fresh.py <receipts_dir> <out.json>"""
import collections, glob, hashlib, json, os, sys
from decimal import Decimal

FIELDS_NUM = ("qty", "quoteQty", "price", "commission", "realizedPnl")
FIELDS_EQ = ("commissionAsset", "buyer", "maker", "orderId", "side", "time", "positionSide")


def rid(r): return json.dumps(r, sort_keys=True, separators=(",", ":"))


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    d, out = sys.argv[1], sys.argv[2]
    rep = []
    for fresh in sorted(glob.glob(os.path.join(d, "FLATTEN_CLOSURE_v4fresh_FLATTEN-*_venue_trades.json"))):
        ev = os.path.basename(fresh)[len("FLATTEN_CLOSURE_v4fresh_"):-len("_venue_trades.json")]
        old = os.path.join(d, f"FLATTEN_CLOSURE_{ev}_venue_trades.json")
        A, B = json.load(open(old)), json.load(open(fresh))
        ta = {(t["symbol"], str(t["id"])): t for t in A["body"]}; tb = {(t["symbol"], str(t["id"])): t for t in B["body"]}
        only_old = sorted(set(ta) - set(tb)); only_new = sorted(set(tb) - set(ta))
        diffs = []
        for k in sorted(set(ta) & set(tb)):
            a, b = ta[k], tb[k]
            f = [x for x in FIELDS_NUM if Decimal(str(a.get(x))) != Decimal(str(b.get(x)))] + [x for x in FIELDS_EQ if a.get(x) != b.get(x)]
            if f: diffs.append([list(k), f])
        ia = collections.Counter(rid(r) for r in A["income_rows"]); ib = collections.Counter(rid(r) for r in B["income_rows"])
        ka = {(r["incomeType"], str(r["tranId"]), r.get("asset")): r for r in A["income_rows"]}
        kb = {(r["incomeType"], str(r["tranId"]), r.get("asset")): r for r in B["income_rows"]}
        inc_amt = [list(k) for k in set(ka) & set(kb) if Decimal(ka[k]["income"]) != Decimal(kb[k]["income"])]
        rv = os.path.join(d, f"FLATTEN_CLOSURE_v4fresh_{ev}.json"); r3 = os.path.join(d, f"FLATTEN_CLOSURE_v3_{ev}.json")
        R = json.load(open(rv)) if os.path.isfile(rv) else {}; V = json.load(open(r3))
        cdiff = [k for k in V["C_closure"] if not k.startswith("VERDICT") and R.get("C_closure", {}).get(k) != V["C_closure"][k]]
        rep.append({"event": ev, "old_raw": os.path.basename(old), "old_raw_sha256": sha(old),
                    "fresh_raw": os.path.basename(fresh), "fresh_raw_sha256": sha(fresh), "fresh_fetched_utc": B.get("fetched_utc"),
                    "old_n_symbols_queried_declared": A.get("n_symbols_queried"), "fresh_n_symbols_queried": len(B.get("symbols_queried") or []),
                    "trades_old": len(ta), "trades_fresh": len(tb), "trades_only_in_old": len(only_old), "trades_only_in_fresh": len(only_new),
                    "trades_same_key_field_diffs": len(diffs), "samples": {"only_old": only_old[:5], "only_fresh": only_new[:5], "field_diffs": diffs[:5]},
                    "income_old": len(A["income_rows"]), "income_fresh": len(B["income_rows"]),
                    "income_rows_only_in_old": sum((ia - ib).values()), "income_rows_only_in_fresh": sum((ib - ia).values()),
                    "income_same_key_amount_diffs": len(inc_amt),
                    "fresh_receipt_VERDICT": R.get("VERDICT"), "fresh_receipt_gates": R.get("gates"),
                    "fresh_vs_v3_A_equal": R.get("A_local_identity") == V["A_local_identity"],
                    "fresh_vs_v3_C_fields_differing": cdiff})
        print(json.dumps({k: v for k, v in rep[-1].items() if k != "samples"}, ensure_ascii=False))
    doc = {"receipt": "FLATTEN_RAW_OLD_VS_FRESH", "device": "compare_flatten_raw_old_vs_fresh.py",
           "self_sha256": sha(os.path.abspath(__file__)), "n_windows": len(rep), "windows": rep,
           "totals": {k: sum(r[k] for r in rep) for k in ("trades_old", "trades_fresh", "trades_only_in_old", "trades_only_in_fresh",
                                                        "trades_same_key_field_diffs", "income_old", "income_fresh", "income_rows_only_in_old",
                                                        "income_rows_only_in_fresh", "income_same_key_amount_diffs")}}
    tmp = out + ".part"
    with open(tmp, "w") as fh: json.dump(doc, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, out)
    print("TOTALS", json.dumps(doc["totals"]))


if __name__ == "__main__":
    main()
