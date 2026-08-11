"""Fill in the exact find/replace for 0C's remaining 12 injections."""
import re

P = "/Users/haosiyu/dl_quant_live/ops/red_capability.py"
s = open(P).read()

PATCHES = {
    1: ('     "guards": "UNQUOTED symbol gets NO price"},',
        '''     "guards": "UNQUOTED symbol gets NO price",
     "find": "            if mid <= 0:",
     "replace": "            if False:  # INJECTED: an unquoted symbol is priced at 0.0 anyway"},'''),
    2: ('     "guards": "history floor"},',
        '''     "guards": "floor is exactly 90 days back",
     "find": "RETENTION_DAYS = 90 ",
     "replace": "RETENTION_DAYS = 30 "},'''),
    3: ('     "guards": "COLD_START"},',
        '''     "guards": "cold start is labelled COLD_START",
     "find": \'            return {"status": "COLD_START",\',
     "replace": \'            return {"status": "CONTINUOUS",  # INJECTED: cold start hidden\'},'''),
    6: ('     "guards": "deployable caliber"},',
        '''     "guards": "deployable",
     "find": \'DEPLOYABLE_CALIBERS = {"champion_fixfunding", "corrected_4leg", "B_fixfunding_4leg"}\',
     "replace": \'DEPLOYABLE_CALIBERS = {"champion_fixfunding", "corrected_4leg", \'
                \'"B_fixfunding_4leg", "A_provisional_3leg"}  # INJECTED\'},'''),
    7: ('     "guards": "decay"},',
        '''     "guards": "decay",
     "find": "    elif roll is not None and thr is not None and float(roll) < float(thr):",
     "replace": "    elif report.get(\\'decay_alarm\\'):  # INJECTED: cumulative flag, not current"},'''),
    8: ('     "guards": "TESTNET really is a different tree"},',
        '''     "guards": "TESTNET really is a different tree",
     "find": \'_SUBDIR = {"LIVE": "", "DRY_RUN": "", "TESTNET": "testnet"}\',
     "replace": \'_SUBDIR = {"LIVE": "", "DRY_RUN": "", "TESTNET": ""}  # INJECTED: shared root\'},'''),
    9: ('     "guards": "paths_for is PURE"},',
        '''     "guards": "paths_for is PURE",
     "find": "    root = root_for(mode)\\n    return {\\n        \\"root\\": root,",
     "replace": "    root = root_for(mode)\\n    os.makedirs(os.path.join(root, \\"_probe\\"), "
                "exist_ok=True)  # INJECTED\\n    return {\\n        \\"root\\": root,"},'''),
    10: ('     "guards": "delivered_offbox"},',
         '''     "guards": "delivered_offbox",
     "find": \'            rec["status"] = "NOT_CONFIGURED"\',
     "replace": \'            rec["status"] = "NOT_CONFIGURED"; rec["delivered_offbox"] = True\'},'''),
    11: ('     "guards": "not_null"},',
         '''     "guards": "not_null",
     "find": \'        "not_null": ["anchor_ts", "symbol", "order_type", "intended_notional", "mid_at_anchor",\',
     "replace": \'        "not_null": ["anchor_ts", "symbol", "order_type", "intended_notional",\'},'''),
    12: ('     "guards": "parity"},',
         '''     "guards": "parity",
     "find": "        self.mu = np.asarray(mu, np.float32)",
     "replace": "        self.mu = np.asarray(mu, np.float32) + np.float32(1e-3)  # INJECTED"},'''),
    13: ('     "guards": "warmup"},',
         '''     "guards": "warmup",
     "find": \'WARMUP_HARD_FLOOR_H = int(_panel_cfg("warmup_hours_hard_floor"))\',
     "replace": "WARMUP_HARD_FLOOR_H = 800  # INJECTED"},'''),
    14: ('     "guards": "tie"},',
         '''     "guards": "tie",
     "find": "        avg_rank = (cum - counts + 1 + cum) / 2.0",
     "replace": "        avg_rank = cum.astype(float)  # INJECTED: ordinal-ish, ties break by order"},'''),
    15: ('     "guards": "halt"},',
         '''     "guards": "halt",
     "find": "        if self.open_orders_halted and not order.get(\\"reduce_only\\"):",
     "replace": "        if False and self.open_orders_halted:  # INJECTED: halt lets openings through"},'''),
}

for k, (old, new) in PATCHES.items():
    if old not in s:
        raise SystemExit(f"anchor for injection {k} not found: {old[:60]}")
    s = s.replace(old, new, 1)

open(P, "w").write(s)
print(f"filled in {len(PATCHES)} patches")
