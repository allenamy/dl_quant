# live-tree fingerprint, BEFORE my 05:05Z battery  2026-09-16T04:40:05Z
# helper: fx_prod fx/live_tree_fingerprint.py sha256 77c5f94d41532cd64c7f16dd3981c67456c5ec4d4a24cf87ad92af1ffea1dd6d
# root: ~/dl_quant_live/state   n_files=39410  n_sha_compared=39323  sha256=32e01275b0b73334

## HONEST SCOPE OF THIS CONTROL
The live executor is RUNNING. Its own daemons (sidecar, shadowloop, icmonitor, notary,
markout_backfill) write into this tree continuously, so the after-diff will NOT be empty and
an empty one would be the surprise. This control therefore does not prove 'nothing changed';
it proves that nothing MY BATTERY could write changed, with every difference attributed to a
named live writer. The 04Z anchor completed before this snapshot and the next is 08:00Z, so
no scheduled anchor falls inside the window.

## THE FILE THAT MATTERS MOST (TEST-01: a test wrote a venue ban into this tree on 09-13)
-rw-r--r--@ 1 haosiyu  staff  658 Sep 13 19:58 /Users/haosiyu/dl_quant_live/state/venue_ban.json
sha256 = 45d75caedef34ac559090963d2d9f5153dfac9acff238180b80b848e3f379801
mtime  = 2026-09-13T19:58:21Z
⇒ this must be byte-identical afterwards. It is the exact file the 09-13 battery wrote into.

## A SECOND ATTRIBUTION SOURCE, NAMED IN ADVANCE
FX-PROD runs its own battery (`tests_fx_prod.py`, not `run_acceptance.sh`, so it needs no
BATTERY.lock) starting 04:50Z — inside my before/after window. Its subject PROD-45 is precisely a
producer path that writes via `WS` instead of `_outdir`, so a write from it into
`~/dl_quant_live/state` during this window is POSSIBLE and would be theirs, not my battery's.
Named here BEFORE the fact so that if such a difference appears I cannot be accused of — and
cannot accidentally perform — attribution after seeing the answer. If it appears I will send them
the path and the timestamps rather than assigning it myself.
