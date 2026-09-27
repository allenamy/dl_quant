#!/usr/bin/env python3
"""Serial queue: successful corrected KSR readout -> strict resources -> pinned rerun6.

Does not sync, kill other jobs, change gates, or write production/exchange state.
The frozen runner owns its existing D3 quota probe and isolated dry-run outputs.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from ksr_readout_waiter import GIB, check_hashes, group_alive, memory_headroom, sha, write_json


def resources_ready(headroom, other_rss, shm_free):
    return headroom >= 28 * GIB and other_rss <= 4 * GIB and shm_free >= 4 * GIB


def dependency_state(text, alive):
    lines = text.splitlines()
    if any(re.match(r'^\S+ KSR_READOUT_FAILED\b', x) for x in lines):
        return 'FAILED'
    if any(re.match(r'^\S+ KSR_READOUT_DONE\b', x) for x in lines):
        return 'DONE'
    return 'RUNNING' if alive else 'GONE_WITHOUT_MARKER'


def row_counts(rows):
    counts = {}
    for row in rows:
        counts[row['verdict']] = counts.get(row['verdict'], 0) + 1
    passed = bool(rows) and set(counts) <= {'PASS', 'IDENTICAL', 'IDENTICAL_EXCEPT_DECLARED'}
    return counts, passed


def other_user_rss():
    total = 0
    for p in Path('/proc').glob('[0-9]*/status'):
        if p.parent.name == str(os.getpid()):
            continue
        try:
            fields = dict(line.split(':', 1) for line in p.read_text().splitlines())
            if int(fields['Uid'].split()[0]) == os.getuid():
                total += int(fields.get('VmRSS', '0 kB').split()[0]) * 1024
        except (FileNotFoundError, ProcessLookupError):
            continue
    return total


def main(config_path):
    cfg = json.loads(Path(config_path).read_text()); root = Path(cfg['root']); marker = Path(cfg['marker_root'])
    marker.mkdir(parents=True, exist_ok=True)
    def say(message):
        line = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + ' ' + message
        with open(marker / 'queue.log', 'a') as f:
            f.write(line + '\n'); f.flush(); os.fsync(f.fileno())
        print(line, flush=True)
    try:
        (root / '.queue_claim').mkdir()
        meta = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'self_sha256': sha(__file__),
                'config_sha256': sha(config_path), 'role': 'WAIT_KSR_READOUT_THEN_SERIAL_DRYRUN',
                'start_ticks': int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])}
        write_json(marker / 'PGID.json', meta)
        say('D10_QUEUE_START ' + json.dumps(meta, sort_keys=True))
        check_hashes(cfg['queue_pins'])
        deadline = time.monotonic() + 60 * 3600
        kl = Path(cfg['ksr_marker_root']) / 'waiter.log'
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError('dependency wait exceeded 60 hours')
            state = dependency_state(kl.read_text(), group_alive(cfg['ksr_waiter_pgid'], cfg['ksr_waiter_start_ticks']))
            if state == 'DONE':
                break
            if state != 'RUNNING':
                raise RuntimeError('KSR readout ' + state)
            say('D10_QUEUE_WAIT KSR_READOUT_RUNNING'); time.sleep(60)
        kdone = json.loads(Path(cfg['ksr_done']).read_text())
        if kdone['status'] != 'DONE' or kdone['pgid'] != cfg['ksr_waiter_pgid']:
            raise ValueError('KSR terminal receipt identity differs')
        if kdone['waiter_sha256'] != cfg['ksr_waiter_sha256'] or kdone['config_sha256'] != cfg['ksr_config_sha256']:
            raise ValueError('KSR terminal receipt code/config differs')
        if sha(kdone['output']) != kdone['output_sha256']:
            raise ValueError('KSR terminal output hash differs')
        book = json.loads(Path(kdone['output']).read_text())
        if book['self_sha256'] != cfg['ksr_reader_sha256']:
            raise ValueError('KSR result was not made by corrected reader')
        say('D10_QUEUE_KSR_ACCEPTED output_sha=' + kdone['output_sha256'])
        # Parent gates are deliberately stricter than the frozen runner's gates.
        while True:
            head = memory_headroom(); rss = other_user_rss(); st = os.statvfs('/dev/shm'); shm = st.f_bavail * st.f_frsize
            snapshot = {'cgroup_headroom': head, 'other_user_rss': rss, 'shm_free': shm}
            if resources_ready(head, rss, shm):
                write_json(root / 'RESOURCE_GATE.json', snapshot); break
            if time.monotonic() > deadline:
                raise TimeoutError('strict resource gates remained closed for 60 hours')
            say('D10_QUEUE_WAIT_RESOURCE ' + json.dumps(snapshot, sort_keys=True)); time.sleep(60)
        check_hashes(cfg['queue_pins'])
        manifest = json.loads(Path(cfg['manifest']).read_text())
        verify = json.loads(Path(cfg['source_verify_receipt']).read_text())
        if verify.get('PASS') is not True or sha(cfg['source_verify_receipt']) != manifest['source_verify_receipt_sha256']:
            raise ValueError('source verification receipt identity or PASS differs')
        check_hashes(manifest['pins'])
        for path in manifest['must_remain_absent']:
            if Path(path).exists():
                raise ValueError('import resolution changed: ' + path)
        for directory, expected in manifest['code_inventory'].items():
            names = sorted(p.name for p in Path(directory).iterdir() if p.is_file() and p.suffix in ('.py', '.sh'))
            if names != expected:
                raise ValueError('deployed code inventory changed: ' + directory)
        exp = Path(cfg['exp']); existing = [exp / 'out/DRYRUN_RESULT_rerun6.json', Path(cfg['runner_log'])]
        if any(p.exists() and p.stat().st_size for p in existing):
            raise ValueError('rerun6 already has output/log; refuse overwrite or duplicate')
        command = [cfg['python'], '-B', str(exp / 'devices/d10_dryrun_run.py'), str(exp), '--part', 'rerun6',
                   '--expect', str(exp / 'prereg/RERUN6_EXPECTED_DIFFS_2026-09-27.json'), '--expect-sha', cfg['expect_sha']]
        clean = {'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LC_CTYPE': 'C', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
        with open(root / 'runner.stdout', 'x') as out:
            child = subprocess.Popen(command, env=clean, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            write_json(marker / 'RUNNER_PGID.json', {'pid': child.pid, 'pgid': os.getpgid(child.pid), 'command': command})
            say('D10_QUEUE_RUNNER_START pid=' + str(child.pid))
            rc = child.wait()
        text = Path(cfg['runner_log']).read_text()
        if rc != 0 or re.search(r'^\S+ DRYRUN_STOP\b', text, re.M) or not re.search(r'^\S+ DRYRUN_DONE\b', text, re.M):
            raise RuntimeError('rerun6 missing success terminal or failed rc=' + str(rc))
        # The runner documents the tmpfs copy as authoritative if the output-volume copy fails.
        result_path = Path(cfg['runner_log']).parent / 'DRYRUN_RESULT_rerun6.json'
        result = json.loads(result_path.read_text())
        if not result.get('final', '').startswith('DONE ') or result.get('expect', {}).get('sha256') != cfg['expect_sha']:
            raise ValueError('rerun6 terminal receipt mismatch')
        check_hashes(manifest['pins'])
        counts, all_rows_pass = row_counts(result['rows'])
        done = {'status': 'DONE', 'result_path': str(result_path), 'result_sha256': sha(result_path),
                'counts': counts, 'all_rows_pass': all_rows_pass,
                'manifest_sha256': sha(cfg['manifest']), **meta}
        write_json(root / 'DONE.json', done)
        say('D10_QUEUE_DONE ' + json.dumps(done, sort_keys=True)); return 0
    except Exception as exc:
        fail = {'status': 'FAILED', 'type': type(exc).__name__, 'reason': str(exc)}
        write_json(marker / 'FAILED.json', fail)
        say('D10_QUEUE_FAILED ' + json.dumps(fail, sort_keys=True)); return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
