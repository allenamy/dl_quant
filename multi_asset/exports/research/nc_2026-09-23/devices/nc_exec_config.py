#!/usr/bin/env python3
"""Executor config edit for the NC release (DESIGN §D-3; AMENDMENT_2/3 m3). Edits ONE file, config/book.json of an ISOLATED executor
checkout (never the running tree), and asserts that nothing else in it changes:
  external_book.booster_sha_pin / f10_sha_pin : from --expect-old to the new pins (the package's INSTALL_CONTRACT executor_pins, or --pins)
  beta_overlay.mode                           : --beta-mode (off | shadow | on)
  beta_overlay.max_combined_leverage          : --max-combined (set when given; otherwise kept as is)
  external_book.producer_contract             : --producer-contract nc_v1 (set) | legacy (removed: key missing = legacy) — read by
                                                ops/anchor_report.py's daemon check; moves with the pins (lead 2026-09-23)
The edit is textual (the two pin strings and the beta_overlay block) so the file keeps its layout; the result is re-parsed and compared
key by key with the original. Prints old -> new; exit 3 on any refusal.
usage: /usr/bin/python3 nc_exec_config.py <checkout>/config/book.json (--contract INSTALL_CONTRACT.json | --pins BOOSTER F10)
       --expect-old BOOSTER F10 --beta-mode MODE --producer-contract {nc_v1,legacy} [--max-combined 2.5]"""
import argparse, copy, json, sys


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("book"); ap.add_argument("--contract"); ap.add_argument("--pins", nargs=2)
    ap.add_argument("--expect-old", nargs=2, required=True); ap.add_argument("--beta-mode", required=True, choices=["off", "shadow", "on"])
    ap.add_argument("--max-combined", type=float); ap.add_argument("--producer-contract", required=True, choices=["nc_v1", "legacy"])
    a = ap.parse_args()
    if a.book.startswith("/Users/haosiyu/dl_quant_live/"):
        print("NC_EXEC_CONFIG REFUSED: edit an isolated checkout, never the running tree"); return 3
    new_pins = a.pins or [json.load(open(a.contract))["executor_pins"][k] for k in ("booster_sha_pin", "f10_sha_pin")]
    raw = open(a.book).read(); b = json.loads(raw); eb = b["external_book"]
    old = (eb["booster_sha_pin"], eb["f10_sha_pin"])
    if list(old) != list(a.expect_old):
        print("NC_EXEC_CONFIG REFUSED: current pins", old, "!= expected", a.expect_old); return 3
    if "beta_overlay" not in b:
        print("NC_EXEC_CONFIG REFUSED: no beta_overlay block (the checkout does not carry the m3-beta-overlay commits)"); return 3
    if a.beta_mode in ("shadow", "on") and a.max_combined is None and "max_combined_leverage" not in b["beta_overlay"]:
        print("NC_EXEC_CONFIG REFUSED: shadow / on needs --max-combined (user ruling 2026-09-23: 2.5)"); return 3
    for o, n in zip(old, new_pins):
        if o != n and raw.count(o) != 1:
            print("NC_EXEC_CONFIG REFUSED: pin string not unique in the file", o[:12]); return 3
    new = raw
    for o, n in zip(old, new_pins): new = new.replace(o, n)
    nb = json.loads(new)
    bo = nb["beta_overlay"]; bo["mode"] = a.beta_mode
    if a.max_combined is not None: bo["max_combined_leverage"] = a.max_combined
    # re-serialise only the beta_overlay block: find it textually and replace it with the edited block at the same indentation
    start = new.index('"beta_overlay": {'); depth = 0; i = new.index("{", start)
    for k in range(i, len(new)):
        depth += {"{": 1, "}": -1}.get(new[k], 0)
        if depth == 0: end = k + 1; break
    ind = new[:start].split("\n")[-1]
    block = json.dumps(bo, indent=1, ensure_ascii=False).replace("\n", "\n" + ind)
    new = new[:i] + block + new[end:]
    # external_book.producer_contract: inserted right after f10_sha_pin (textual, same indentation) / removed
    pc_old = json.loads(new)["external_book"].get("producer_contract")
    if a.producer_contract == "nc_v1" and pc_old != "nc_v1":
        if pc_old is not None:
            print("NC_EXEC_CONFIG REFUSED: producer_contract has an unexpected value", pc_old); return 3
        anchor = f'"f10_sha_pin": "{new_pins[1]}",'
        if new.count(anchor) != 1:
            print("NC_EXEC_CONFIG REFUSED: cannot place producer_contract (f10_sha_pin line not unique)"); return 3
        ind = new[:new.index(anchor)].split("\n")[-1]
        new = new.replace(anchor, anchor + "\n" + ind + '"producer_contract": "nc_v1",')
    elif a.producer_contract == "legacy" and pc_old is not None:
        line = f'"producer_contract": "{pc_old}",'
        if new.count(line) != 1:
            print("NC_EXEC_CONFIG REFUSED: producer_contract line not unique"); return 3
        i0 = new.index(line); ls = new.rfind("\n", 0, i0); new = new[:ls] + new[i0 + len(line):]
    nb2 = json.loads(new)
    # every key other than the edited ones is unchanged
    chk = copy.deepcopy(nb2); chk["external_book"]["booster_sha_pin"], chk["external_book"]["f10_sha_pin"] = old
    if a.producer_contract == "nc_v1": assert chk["external_book"].pop("producer_contract") == "nc_v1"
    if "producer_contract" in b["external_book"]: chk["external_book"]["producer_contract"] = b["external_book"]["producer_contract"]
    chk["beta_overlay"]["mode"] = b["beta_overlay"]["mode"]
    if a.max_combined is not None:
        if "max_combined_leverage" in b["beta_overlay"]: chk["beta_overlay"]["max_combined_leverage"] = b["beta_overlay"]["max_combined_leverage"]
        else: del chk["beta_overlay"]["max_combined_leverage"]
    if chk != b:
        print("NC_EXEC_CONFIG REFUSED: other keys would change"); return 3
    open(a.book, "w").write(new)
    print("NC_EXEC_CONFIG OK", json.dumps({"pins": [f"{o[:8]}->{n[:8]}" for o, n in zip(old, new_pins)],
                                           "beta_overlay": {"mode": f"{b['beta_overlay']['mode']}->{a.beta_mode}",
                                                            "max_combined_leverage": f"{b['beta_overlay'].get('max_combined_leverage')}->{nb2['beta_overlay'].get('max_combined_leverage')}"},
                                           "producer_contract": f"{b['external_book'].get('producer_contract')}->{nb2['external_book'].get('producer_contract')}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
