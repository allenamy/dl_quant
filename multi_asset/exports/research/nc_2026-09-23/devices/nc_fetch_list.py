#!/usr/bin/env python3
"""The deploy-time dynamic fetch list (DESIGN §A1): production's last exchangeInfo TRADING perpetual-USDT list (aux base_syms, refreshed
every anchor by M1) ∩ the 829 axis ∩ the frozen crypto rule, in axis order. The SAME definition as nc_seed_state.py's default; written
once and passed to both nc_deploy_fetch.py and nc_seed_state.py --fetch-list so the two use one list. No exchange call.
usage: ~/wide_shadow/venv/bin/python nc_fetch_list.py <production state dir> <crypto npz> <out json>"""
import json, os, sys, hashlib
import numpy as np


def main():
    st, crypto, out = sys.argv[1:4]
    assert not os.path.exists(out), "refusing to overwrite"
    cfg = json.load(open(os.path.expanduser("~/wide_shadow/shadow_bundle/config.json"))); syms = cfg["symbols_panel"]
    z = np.load(crypto, allow_pickle=True); assert [str(x) for x in z["symbols"]] == syms, "crypto npz axis differs from symbols_panel"
    cr = z["crypto"].astype(bool); aux = json.load(open(f"{st}/aux.json"))
    tb = aux.get("base_syms") or []
    assert len(tb) >= 300, f"aux base_syms has {len(tb)} names (< 300): production's exchangeInfo refresh did not run; stop"
    tb = set(tb); fl = [s for j, s in enumerate(syms) if s in tb and cr[j]]
    live = set(cfg["symbols_live"])
    json.dump(fl, open(out, "w"))
    print("NC_FETCH_LIST", json.dumps({"out": out, "n": len(fl), "not_in_symbols_live": sum(1 for s in fl if s not in live),
                                       "anchor": aux.get("last_anchor"), "sha256": hashlib.sha256(open(out, "rb").read()).hexdigest()}))


if __name__ == "__main__":
    main()
