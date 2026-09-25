> **Created:** 2026-09-25 07:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** one-pager for the lead to review before implementation (the user has ruled: keep the last 14 days in full; for older anchors keep only the small files; no archive to pod2) | **Invalidated by:** a user / lead ruling that changes the thresholds or the file list

# Producer snapshot retention `~/wide_shadow/state/snap/<A>/` (goes into C, treeNC6, through the deploy protocol)

## Measured (46 anchors, 2026-09-17T12Z → 2026-09-25T04Z)
| File | Per anchor (max / mean) | Role |
|---|---|---|
| rolling.npz | 78.3 / 72.0 MB | the 40-day 5-minute market copy (channel-0 storage and the rest) — the input to parity / gate 3′ / β parity replays |
| aux.json | 7.67 / 5.57 MB | prev_close / H / ema / ledger_tail / prev_rec … (**kept by the user's ruling**) |
| members_hist.npz | 0.20 MB (NC era) | membership history |
| leg_returns_live.json | 0.06 MB | |
| boundary_raw.npz, generation.json, SHA256SUMS, COMPLETE, combo_live_status.json, PARITY*.json / *.run.log | < 2 KB each | provenance and parity receipts |

Currently 3.3 GB total, growing about +0.5 GB/day.
> ⚠ **Correction (2026-09-25 06:5xZ, same author; original line kept below):** "no cap" is **wrong**. `combo_state_snapshot.sh` already ends with `find "$SNAP" -maxdepth 1 -mindepth 1 -type d -mtime +21 -exec rm -rf {} +` (header: "Retention: 21 days"), i.e. **whole snapshot directories are deleted after 21 days by mtime** (they have not been reached yet because the 46 snapshots are all under 21 days old; steady state ≈ 21 × 6 × 84 MB ≈ 10.6 GB). I wrote "no cap" without reading the script. Consequences for this plan: the user's rule "14 days in full, older keep only small files" **replaces** that 21-day whole-directory deletion (otherwise the small files would be deleted at day 21 too), so that `find … -mtime +21 … rm -rf` line must go in the same change; after the change the long-term residue is the small files (≈ 6–8 MB per anchor, +1.3 GB/month), versus the old rule's steady ≈ 10.6 GB with nothing beyond 21 days. Original line: "Currently 3.3 GB total, growing about +0.5 GB/day with no cap."

## Rule (runs after each successful snapshot, in the same process as combo_state_snapshot.sh)
- **Retention window:** anchors with A ≥ (newest anchor − 14 × 24 h) are left untouched (84 anchors). The window is set by the anchor ts in the directory name, not by mtime (the existing 21-day `find -mtime` rule used mtime; a copy or `touch` would silently change the window).
- **Removed at the same time:** the existing script line `find "$SNAP" -maxdepth 1 -mindepth 1 -type d -mtime +21 -exec rm -rf {} +` (whole-directory deletion after 21 days, which conflicts with the user's "keep the small files" ruling).
- **Older than the window:** delete **only files ≥ 1 MB that are not on the keep list**.
  - Keep list = `aux.json`, target files (the snap dir contains none; target_live / target_combo / target_live_king live elsewhere and are out of scope), and all small files (`SHA256SUMS`, `generation.json`, `COMPLETE`, `PARITY*`, `combo_live_status.json`, `leg_returns_live.json`, `members_hist.npz`, `boundary_raw.npz`).
  - ⇒ in practice only `rolling.npz` is deleted. Any new large file added later is also treated as "large but not on the keep list", deleted and recorded (rule by class, not by file name).
- **Before deleting:**
  1. recompute the sha256 of the file to be deleted, which must **equal** that file's line in its snapshot's `SHA256SUMS` (mismatch ⇒ do not delete, HIGH page: the snapshot has been damaged);
  2. append `sha256  <A>/<file>  <bytes>  <deleted_utc>` to the resident list `state/snap/RETENTION_DELETED.sha256` (append + fsync, and read back to confirm the line was written before deleting);
  3. write a small `RETENTION_TRIMMED.json` into the snapshot directory (names the deleted files and the rule version) so a reader can tell it has been trimmed.
- **Readers:** `combo_parity_agent.sh` only runs on the newest anchors (which are inside the window). The replay readers (combo_parity_replay.sh, my gate 3′ / β parity / selfcheck) must be told to **refuse by name** when `rolling.npz` is missing because of `RETENTION_TRIMMED.json`, not report "missing file" as some other error. A trimmed anchor is not a candidate for a gate that needs replay.
- **No archive to pod2** (the user's ruling; the pod2 quota is tight). A deleted `rolling.npz` cannot be recovered, but the resident list keeps its sha, so a copy found later (for example one pulled back from pod2) can be matched against it.

## Expected volume per anchor and in total
| | Size |
|---|---|
| inside the window, per anchor | ~78 MB (rolling) + ~5.6–7.7 MB (aux) + ~0.3 MB ≈ **84–86 MB** |
| inside the window, total (84 anchors) | ≈ **7.1–7.2 GB (steady state)** |
| outside the window, per anchor | aux 5.6–7.7 MB + ~0.3 MB ≈ **6–8 MB** |
| growth outside the window | ≈ 6 anchors × 7 MB ≈ **+42 MB/day ≈ +1.3 GB/month** |

Once the window is full (from 2026-10-01T12Z), the snapshot directory is ≈ 7.2 GB, plus about 1.3 GB per month after that.

**User's final ruling (2026-09-25 ~06:5xZ, relayed by the lead): small files are kept FOREVER; the long-term growth of about +1.3 GB/month is accepted with full knowledge.** Implementation: `snap_retention.py` (8833da2c) replaces the `find … -mtime +21 -exec rm -rf` line in combo_state_snapshot.sh; combo_parity_replay.sh refuses a trimmed snapshot by name (`CANNOT_REPLAY TRIMMED_BY_RETENTION`); built into treeNC7 by `nc_derive_producer --durable` (edits on the pinned production sources 58e58bd1 / d49cd834); test_snap_retention 14/14.

Optional (needs a ruling): aux.json accounts for about 90% of the long-term growth. If gzipped copies were allowed (keep the original's sha and delete the plaintext), long-term growth would be expected to fall to about 1/5–1/10. This has not been measured; the ratio is to be measured before the ruling.

## Tests (red controls, go with C)
- Within-window anchors are not touched.
- An out-of-window rolling.npz is deleted, and its sha line is appended and read back.
- A rolling.npz whose sha does not match SHA256SUMS ⇒ not deleted + HIGH.
- Small files / aux.json are never deleted (planting a 1.2 MB `aux.json` must not delete it; planting a 1.2 MB unknown file must delete it).
- The resident list is append-only (it must not be truncated).
- A replay reader given a trimmed anchor refuses by name.
