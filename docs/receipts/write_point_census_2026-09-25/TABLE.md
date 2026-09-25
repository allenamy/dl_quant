> **Created:** 2026-09-25 05:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** read-only census (lead asked for a table only; no file was changed; production fixes are scheduled separately under the deploy protocol, research-side fixes are made by each owner) | **Invalidated by:** a code change at any row

# Write-point census (E-0925-A class: a truncated write + "hash the on-disk file" certifies a damaged artefact)

Instruments: `write_point_census.py` (AST, triage only; every row below was checked by reading the line) and `gc_close_probe.py` (measurement).
Full tables: `PRODUCER.csv`, `EXECUTOR.csv`, `NC_DEVICES_REPO.csv`, `RESEARCH_POD2.csv`. Categories:
A = atomic write + read-back check · B = atomic write, no read-back · C = direct write · D = append. sha source: MEMORY (hash of the in-memory
bytes) / FILE (hash of the file re-read from disk).

## 0. A measured finding bigger than E-0925-A: `json.dump(x, open(p, "w"))` loses the disk-full error
`gc_close_probe.py` (every write to a stand-in raw file raises ENOSPC):
- /usr/bin/python3 3.9.6 (the executor's interpreter): object smaller than the buffer ⇒ **no exception reaches the caller**; with a `with` block the exception propagates.
- venv Python 3.14.4 (the producer's interpreter): small **and** large objects ⇒ **no exception reaches the caller**. The error only goes to stderr as "Exception ignored while finalizing file"; `with` propagates.

Reason: the handle is never closed explicitly, so the last buffer is flushed by the implicit close at garbage collection, and errors there are not raised to the caller.

Number of these unclosed-handle idiom sites (census column `unclosed_handle_idiom`): producer 25, executor 67 (including ops/ and the producer_release copies), my NC devices 53, pod2 research devices 257.

**The most dangerous chain (executor):**
1. `scheduler/anchor_loop.py` L799–803 `_save`: `json.dump(obj, open(tmp, "w"))` → `os.replace(tmp, path)`. When the disk is full, an empty or truncated tmp file silently replaces the good state.
2. L792–796 `_load`: `except Exception: return default`.
3. Result: at the next anchor, the loop state (STATE_PATH, L1044 default `{"positions": {}, …}`), the band state (`_hp` L1976, no_trade_band L2173) and the fee baseline (L2747) are **silently reset to defaults**.
4. Same idiom: `live/watchdog.py` L3307 `state.json` (the trip state, direct write) and L3311 `last_eval.json`; `live/state_root.py` L148; `live/factor_version_registry.py` L174; `live/deliver_report.py` L99.
5. On the producer side: `fea171/combo_stage.py` L327–334 target_combo, L367 / L488 `combo_live_status.json`.

## 1. Producer `~/wide_shadow` (live paths)
| Write point | File:line | Category | sha source / notes |
|---|---|---|---|
| **target_live (combo, the book)** | fea171/combo_stage.py L443–450 staged in a private temp dir → L453–458 the executor's own `verify_file` + `parse_target` read back the staged file → L481–482 `os.replace` | **A** (no fsync) | sidecar sha = MEMORY (`_raw`) |
| target_live_king backup | combo_stage.py L420–421 `shutil.copy2` | C | sidecar copied, not recomputed |
| weights_combo/A.npz | combo_stage.py L427–428 tmp + replace, then L429–430 `_wsha = sha256(open(_wnpz).read())` into target_live `weights_sha` | B | **FILE** (the E-0925-A shape) |
| target_combo/A.json | combo_stage.py L327–334 `json.dump({...}, open(..., "w"))` | C + unclosed-handle idiom | — |
| state_H_kc / state_H_fc / f10 H npz | combo_stage.py L322, L251 `np.savez` | C | — |
| mini cache / dlw_targets / xfer_panel | combo_stage.py L178–179, L198 `np.savez` (feature workspace) | C | the features' meta holds cache_sha256 = FILE |
| combo_live_status.json | combo_stage.py L367, L488 | C + unclosed-handle idiom | — |
| king target_live (shadow_loop) | shadow_loop_v3.py L100–102 `atomic_write` (tmp + os.replace) | B (no fsync) | json sha = MEMORY; the reader checks the sidecar when consuming |
| weights/A.npz (shadow_loop) | shadow_loop_v3.py L868 `np.savez_compressed` direct; L88–89 `wsha` = FILE | C | **FILE** (E-0925-A shape) |
| rolling.npz / boundary_raw / members_hist | shadow_loop_v3.py L416–418, L399–402 tmp + replace | B | none; a truncated zip fails loudly at the next load (CRC) |
| aux.json | shadow_loop_v3.py L419 `atomic_json` | B | none; a truncated file fails loudly at load |
| snapshot state/snap/A | fea171/combo_state_snapshot.sh L31–42: copy to D.tmp; `SHA256SUMS` is FILE, but L38 re-checks the copies with `shasum -c` against the sha taken of the source before copying (PRE), and on mismatch the snapshot is discarded; `mv` last | **A** | FILE, but checked against the source (safe) |
| shadow log | shadow_loop_v3.py L109 | D | — |

## 2. Executor `~/dl_quant_live`
| Write point | File:line | Category | Notes |
|---|---|---|---|
| **pilot_log ledgers** (anchors / orders / fills / daily_nav …) | live/pilot_log.py L454–456 append + `flush()` per row, no fsync | D | on a full disk the flush raises (loud) but can leave a partial line; the reader of fills.jsonl (L461–) indexes complete lines only |
| fills_quarantine | pilot_log.py L515 | D | — |
| pilot_log meta | pilot_log.py L446–449 | C | — |
| **loop state / bands / fee baseline** | scheduler/anchor_loop.py L799–803 `_save` | B + unclosed-handle idiom | see §0: the error is lost, then `_load` falls back to the default |
| **watchdog trip state** | live/watchdog.py L3307 state.json, L3311 last_eval.json | C + unclosed-handle idiom | trip archive L3294 `with open(...,"wb")` (C, but errors raise) |
| watchdog events / ALARM.log | watchdog.py L3218, L3248, L3300, L955, L2743 | D | — |
| per_name_stop state | live/per_name_stop.py L78–79 tmp + rename | B | — |
| stuck_orders | live/stuck_orders.py L160–161 tmp + fsync + rename | B (+fsync) | — |
| book_config self-check probe | live/book_config.py L281–282 `json.dump(book, open(tmp,"w"))` in a fresh `tempfile.mkdtemp()` (a probe copy for the tolerance self-check, not the production book) | C + unclosed-handle idiom | no production state |
| state_root bind / stamp_mode | live/state_root.py L125–127, L148 | C (+ unclosed-handle idiom at L148) | — |
| run_anchor trip / receipts / rate_timeline | scheduler/run_anchor.py L709–713, L730–734, L1016–1017 | C | L1016 is inside try/except (logged) |
| runlog / self-record | run_anchor.py L74, L153 | D | — |
| venue cache / funding stamp | live/binance_executor.py L542–544, live/binance_funding.py L452–455 | C | — |
| ledger notarisation | ops/notarize_ledgers.py L229–230 `open(path, "x")` | C | notarises the ledger bytes on disk = FILE by design |
| anchor_report | ops/anchor_report.py L334–335 `with open` | C | — |

## 3. Research references (read-only; fixes are the owners')
| Write point | File:line | Category | sha source |
|---|---|---|---|
| news2 F10 per-fold model + scores | news2_2026-09-23/devices/news2_train_f10.py L132 `torch.save`, L133 `np.savez_compressed(scores.npz)` → L135–137 sha helper over the written files → FOLD_RECEIPT | C | **FILE** (the original E-0925-A instance) |
| news2 F10 merge | news2_train_f10.py L58–59 tmp + replace, then FILE sha | B | FILE |
| news2 King OOF | news2_train_king.py L73 `np.savez(KING_OOF.npz)` → L75–76 sha FILE | C | FILE |
| the same trainers (copies) | train_f10.py L129–132, L48–49; train_king.py L45–47 (news2 devices); the identical copies under pnoise_2026-09-24/devices | C / B | FILE |
| **mine: NC installer** | nc_2026-09-23/devices/nc_install.py L69–74 `atomic_copy` (tmp `xb` + fsync + replace); L231 re-reads the installed bytes and compares them with the contract's candidate_sha256 | **A** | candidate sha = MEMORY (nc_package.py L127 `sha_b(raw)`); installer L100 re-checks the package files |
| mine: NC packager | nc_package.py L124 direct write; L148 INSTALL_CONTRACT `json.dump(..., open(...))` | C + unclosed-handle idiom (L148) | MEMORY |
| mine: tree derivation receipt | nc_derive_producer.py L894 (MEMORY), L900 / L907 `copyfile` then `sha_file(out/k)` = FILE, L916 PATCH_RECEIPT | C | **FILE** (E-0925-A shape, mine) |
| mine: NC build | pod2 nc_2026-09-23/devices (e.g. nc_p2_build.py L188–196: `NC_FEATURES.npz` written, then `sha(o)` into the receipt) | C | **FILE** (mine) |
