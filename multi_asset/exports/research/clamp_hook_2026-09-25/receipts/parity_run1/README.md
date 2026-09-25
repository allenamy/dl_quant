> **Created:** 2026-09-25 15:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** first reading of the live-vs-engine held-untradable parity (run 2 = reported; run 1 crashed on the cache's string entries) | **Invalidated by:** a change of the ledger / notify_audit / hook rows c4hook3

# Held-untradable (clamped) sets, live vs engine
Device `../../devices/parity_held_untradable.py` (rev 1). Live: 09-16 12Z → 09-25 12Z from the executor's own clamped_after_reshape names; engine: hook v2 run c4hook3 (control PASS, series bitwise == filed SER row 0), path 0, whose axis ends 09-18T20Z ⇒ overlap = 15 anchors 09-16 12Z … 09-18 20Z.

| side / source | name-anchors | names | median \|held\| USDT | max run (anchors) | Σ shift (held − reshape target) USDT |
|---|---|---|---|---|---|
| **live, whole window** held exit | 273 | 37 | **0.4** | **54** | +26,646 |
| live stop cooldown | 80 | 3 (BCH, ENA, ZAMA) | **0.8** | 35 | **+66,763** |
| live stopped | 16 | 14 | 1,017 | 35 | −5,313 |
| live dust (target < 2×minNotional) | 62 | 19 | 22 | 16 | −2,401 |
| live unattributed | 2 | 2 (AIN, UAI) | 1,509 | 1 | +3,018 |
| **engine, overlap** held exit | 24 | 18 | **4,389** | **2** | — |
| engine stop cooldown | 18 | 2 (IOST, TAC) | 0.0 | 15 (= window) | — |
| engine stopped | 4 | 4 | 4,250 | 15 | — |
| engine dust | 2 | 1 | 135 | 2 | — |
| live, overlap only: held exit | 106 | 23 | 0.4 | 15 | +20,044 |

**First reading (to be confirmed per name)**
1. **Exit tails**: a live held exit stays "held" for up to 54 anchors at a median of **0.4 USDT** — a residual below the venue's min notional that the reduce-only / flatten path cannot close — so every anchor it is clamped (not popped) and its reshape target is not re-absorbed. In the engine an exit is gone within 1–2 anchors (median held 4,389 USDT at the exit anchor, then closed): no dust tail.
2. **Cooldown names**: live keeps the three cooldown names BCH / ENA / ZAMA held as ~1 USDT dust for ~33 anchors while the producer keeps a large short target on them; that alone is Σ +66,763 USDT of net shift (≈ +2,500 per anchor in the NC window). The engine's cooldown names sit at exactly 0.0 (float residue) — also clamped, but fewer names and no persistent producer short measured here (the hook did not record the engine's reshape target per name).
3. Engine net / NAV in the overlap is −0.4 … −2.6 % (short), live −0.02 … −0.09 % in the same 15 anchors (the large live long tilt starts later, with the cooldown trio from 09-19/09-23).
Open: the live exit / cooldown dust sizes come from the venue readback (quantity × mid); why the live reduce-only path leaves 0.4–1 USDT (min-notional floor on the closing order) and whether the engine's fill model closes to exactly zero by construction — the next step, with the lines that close positions on each side.
