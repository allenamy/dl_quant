"""v2 (fix-pkg-e item 2, E-0926-H; criteria quant_research fixpkg_e_2026-09-27/CRITERIA_publication_boundary_v2.md 5e168330f).
Real combo publication AST plus actual external_book file/schema validation, offline.

WHY v2: the 20260922 harness executed the publication Try in a HAND-WRITTEN env. The C release (combo_stage 12a76de8) put `DIO` and
`io` into that Try; the missing names raised NameError, the Try's own except turned it into _bail, and four cases went red on the
production code while a comment still said the file was certified by them. v2 (1) supplies io and the producer's own durable_io,
(2) DERIVES the free names of the Try from its AST and fails, by name, on any the env does not provide — except a named
ALLOWED_ABSENT table whose every use must sit inside an inner `except Exception` try (derived, not asserted by hand), and (3) runs
late_status_error on the C release's contract (a status-file failure AFTER publication is not an abort).
The source defaults to the producer's running combo_stage (COMBO_PUBLICATION_SOURCE overrides)."""
import ast
import builtins
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent / "20260922"
SOURCE = Path(os.environ.get("COMBO_PUBLICATION_SOURCE", os.path.expanduser("~/wide_shadow/fea171/combo_stage.py")))
_DIO_PATH = os.environ.get("COMBO_PUBLICATION_DIO", os.path.expanduser("~/wide_shadow/fea171/durable_io.py"))
_dspec = importlib.util.spec_from_file_location("producer_durable_io", _DIO_PATH)
DIO = importlib.util.module_from_spec(_dspec); _dspec.loader.exec_module(DIO)
# Names the publication Try reads but the harness deliberately does NOT provide. Each must be read ONLY inside an inner try whose
# handler catches Exception (checked by test_env_covers_every_free_name), so its absence is a designed, contained outcome.
ALLOWED_ABSENT = {
    "rts": "M3 beta_overlay_producer input; absent => the field is omitted and the book publishes byte-identically (M3 design)",
    "RD": "M3 beta_overlay_producer input; same as rts",
    "_symbols": "M3 beta_overlay_producer input; same as rts",
    "_page": "post-publication HIGH page for a failed beta field; wrapped in try/except so a page failure never aborts",
}
TREE = ast.parse(SOURCE.read_text())
PUBLICATION = next(node for node in ast.walk(TREE) if isinstance(node, ast.Try)
                   and any(isinstance(item, ast.Assign)
                           and any(isinstance(target, ast.Name) and target.id == "_raw" for target in item.targets)
                           for item in node.body))
CODE = compile(ast.Module(body=[PUBLICATION], type_ignores=[]), str(SOURCE), "exec")


def reader():
    raw = (HERE / "tests_fixtures/external_book_409ea16.py.txt").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "b4b18dc08d5d7f22fcfc76d4d591f35ba41b0a7f6e5a11cc3b9ce36c649357d6"
    # Use the actual reader; BC is unrelated to these pure file/schema functions.
    module = types.ModuleType("external_book")
    with mock.patch.dict(sys.modules, {"book_config": types.ModuleType("book_config")}):
        exec(compile(raw, "frozen-external-book", "exec"), module.__dict__)
    return module


class PublicationTests(unittest.TestCase):
    def exercise(self, fault=None, drop=()):
        (HERE / "test_tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="combo-publication-offline-", dir=HERE / "test_tmp") as root:
            root = Path(root); live = root / "state/target_live"; live.mkdir(parents=True)
            anchor = 14400; target = live / f"{anchor}.json"
            symbols = [f"SYNTHETIC{i}" for i in range(400)]
            eb = reader(); tick = [anchor + 1359.0]
            old = {"schema": "wide_target_v1", "anchor_ts": anchor, "universe": symbols,
                   "universe_sha": eb.universe_sha(symbols), "booster_sha": "a" * 64,
                   "synthetic_existing": True}
            if fault == "bad_universe": old["universe_sha"] = "b" * 64
            old_raw = json.dumps(old).encode(); target.write_bytes(old_raw)
            target.with_suffix(".json.sha256").write_text(hashlib.sha256(old_raw).hexdigest())
            writes, verifications = [], []
            real_copy, real_replace = shutil.copy2, os.replace
            real_verify, real_parse, real_dump = eb.verify_file, eb.parse_target, json.dump
            def copy(src, dst, *args, **kw):
                if Path(dst).parent == live: writes.append(("copy", Path(dst).name, tick[0]))
                return real_copy(src, dst, *args, **kw)
            def replace(src, dst, *args, **kw):
                if Path(dst).parent == live: writes.append(("replace", Path(dst).name, tick[0]))
                if fault == "second_replace_failure" and Path(dst) == target.with_suffix(".json.sha256"):
                    tick[0] = anchor + 1361.0
                    raise OSError("synthetic second target replacement failed")
                return real_replace(src, dst, *args, **kw)
            def verify(path):
                verifications.append((str(path), len(writes)))
                return real_verify(path)
            def parse(*args, **kw):
                result = real_parse(*args, **kw)
                if fault == "validation_late": tick[0] = anchor + 1361.0
                return result
            def source_guard(identity):
                if fault == "source_changed":
                    target.write_bytes(b"concurrent-valid-target")
                    tick[0] = anchor + 1361.0
                    raise ValueError("synthetic source changed")
            def dump(doc, stream, *args, **kw):
                if fault == "late_status_error" and doc.get("step") == "done":
                    tick[0] = anchor + 1361.0
                    raise OSError("synthetic status write failure")
                return real_dump(doc, stream, *args, **kw)
            real_wjd = DIO.write_json_durable
            def wjd(path, obj, *args, **kw):              # the C release writes the status through durable_io
                if fault == "late_status_error" and isinstance(obj, dict) and obj.get("step") == "done":
                    tick[0] = anchor + 1361.0
                    raise DIO.DurableWriteError("synthetic status write failure")
                return real_wjd(path, obj, *args, **kw)
            def bail(why): raise SystemExit(3)
            clock = types.SimpleNamespace(time=lambda:tick[0], strftime=time.strftime, gmtime=time.gmtime,
                                          mktime=time.mktime, strptime=time.strptime, timezone=time.timezone)
            # Fake only clock, source guard and external side effects; execute real publication/files/reader.
            env = {"A": anchor, "WS": str(root), "HOME": str(root), "EXECUTOR_ROOT": str(root / "executor"), "_outdir": str(live),
                   "_rehearsal": False, "_now0": tick[0], "_status": {}, "_bail": bail,
                   "okf": np.ones(400, bool), "combo_raw": np.tile([.0025, -.0025], 200),
                   "syms": symbols, "_F10_SHA": "c" * 64, "_source_snapshot": {"identity": {}},
                   "verify_source_snapshot": source_guard, "verify_current_feature_cache": lambda *a:None,
                   "MINI": str(root / "mini"), "_feature_identity": {}, "log": lambda *a:None,
                   "np":np, "os":os, "shutil":shutil, "sys":sys, "json":json,
                   "hashlib":hashlib, "time":clock, "tempfile":tempfile, "io":io, "DIO":DIO}
            if drop: [env.pop(k) for k in drop]
            type(self).last_env = set(env)                 # the env ACTUALLY handed to the block (FreeNameTests reads this, not a copy)
            failed = False
            with mock.patch.dict(sys.modules, {"external_book":eb}), \
                 mock.patch.object(shutil,"copy2",copy), mock.patch.object(os,"replace",replace), \
                 mock.patch.object(eb,"verify_file",verify), mock.patch.object(eb,"parse_target",parse), \
                 mock.patch.object(json,"dump",dump), mock.patch.object(DIO,"write_json_durable",wjd), \
                 mock.patch.object(sys,"path",list(sys.path)):
                try: exec(CODE, env)
                except SystemExit: failed = True
            raw = target.read_bytes()
            return failed, writes, verifications, raw, old_raw, real_verify(str(target)), env.get("_status")

    def test_identity_error_before_publication_preserves_concurrent_target(self):
        failed,writes,_,raw,_,_,_ = self.exercise("source_changed")
        self.assertTrue(failed); self.assertEqual(writes, [])
        self.assertEqual(raw, b"concurrent-valid-target")

    def test_invalid_payload_rejected_by_real_reader_before_any_live_write(self):
        failed,writes,_,raw,old,_,_ = self.exercise("bad_universe")
        self.assertTrue(failed); self.assertEqual(writes, []); self.assertEqual(raw, old)

    def test_validation_crossing_deadline_does_not_publish(self):
        failed,writes,_,raw,old,_,_ = self.exercise("validation_late")
        self.assertTrue(failed); self.assertEqual(writes, []); self.assertEqual(raw, old)

    def test_late_postpublication_error_never_restores_king(self):
        # v2: the C release's contract — the target is ALREADY published, so a status-file failure is logged, never an abort
        failed,writes,_,raw,old,verified,_ = self.exercise("late_status_error")
        self.assertFalse(failed); self.assertNotEqual(raw, old); self.assertTrue(verified["ok"])
        self.assertEqual(len(writes), 2); self.assertTrue(all(kind=="replace" for kind,_,_ in writes))
        self.assertTrue(all(when <= 15760 for _,_,when in writes))

    def test_valid_candidate_passes_real_reader_before_live_replacements(self):
        failed,writes,checks,raw,old,verified,status = self.exercise()
        self.assertFalse(failed); self.assertTrue(verified["ok"]); self.assertTrue(status["reader_ok"])
        self.assertNotEqual(raw, old); self.assertEqual(len(writes), 2)
        self.assertEqual(checks[0][1], 0)
        self.assertEqual(len(json.loads(raw)["weights"]), 400)

    def test_partial_pair_failure_remains_rejected_and_never_restores_king(self):
        failed,writes,_,raw,old,verified,_ = self.exercise("second_replace_failure")
        self.assertTrue(failed); self.assertTrue(raw != old)
        self.assertFalse(verified["ok"]); self.assertEqual(verified["reason"], "sha_mismatch")
        self.assertEqual(len(writes), 2); self.assertTrue(all(kind=="replace" for kind,_,_ in writes))


class FreeNameTests(unittest.TestCase):
    @staticmethod
    def env_names(drop=()):
        t = PublicationTests("test_valid_candidate_passes_real_reader_before_live_replacements")
        t.exercise(drop=drop)
        return PublicationTests.last_env

    @staticmethod
    def free_names(node):
        stored, loaded = set(), {}
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                (stored.add(n.id) if isinstance(n.ctx, (ast.Store, ast.Del)) else loaded.setdefault(n.id, []).append(n))
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                stored.update((a.asname or a.name).split(".")[0] for a in n.names)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                stored.add(n.name)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stored.add(n.name)
        return {k: v for k, v in loaded.items() if k not in stored and not hasattr(builtins, k)}

    def uncovered(self, drop=()):
        return sorted(set(self.free_names(PUBLICATION)) - self.env_names(drop) - set(ALLOWED_ABSENT))

    def test_env_covers_every_free_name(self):
        """Every name the publication block reads and never assigns is provided — or ALLOWED_ABSENT and read only inside an
        inner try that catches Exception. A new global in combo_stage makes THIS test red by name (E-0926-H)."""
        free = self.free_names(PUBLICATION)
        uncovered = self.uncovered()
        self.assertEqual(uncovered, [], f"publication block reads names the harness does not provide: {uncovered}")
        guarded = set()
        for t in ast.walk(PUBLICATION):
            if isinstance(t, ast.Try) and t is not PUBLICATION and any(
                    h.type is None or (isinstance(h.type, ast.Name) and h.type.id in ("Exception", "BaseException")) for h in t.handlers):
                for stmt in t.body:
                    guarded.update(id(n) for n in ast.walk(stmt) if isinstance(n, ast.Name))
        for k in sorted(set(ALLOWED_ABSENT) & set(free)):
            bare = [n.lineno for n in free[k] if id(n) not in guarded]
            self.assertEqual(bare, [], f"ALLOWED_ABSENT name {k!r} is read OUTSIDE an except-Exception try at lines {bare}")
        # red control inside the suite: dropping a provided name MUST be reported by name
        self.assertEqual(self.uncovered(drop=("DIO",)), ["DIO"])


if __name__ == "__main__": unittest.main(verbosity=2)
