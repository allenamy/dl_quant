#!/usr/bin/env python3
"""Wait only for the pinned KSR run, bind its completed inputs, read once.

No training, kills, source mutations, exchange calls, or partial candidate reads.
Terminal log lives on /dev/shm; products live in a new /workspace directory.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

GIB = 1 << 30


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def check_hashes(expected):
    for path, digest in expected.items():
        if sha(path) != digest:
            raise ValueError('sha mismatch: ' + path)


def classify(text, start_line, alive):
    lines = text.splitlines()
    if lines.count(start_line) != 1:
        raise ValueError('upstream start identity missing or duplicated')
    scoped = lines[lines.index(start_line) + 1:]
    if any(re.match(r'^\S+ KSR_START\b', line) for line in scoped):
        raise ValueError('a different upstream run has started')
    if any(re.match(r'^\S+ STOP\b', line) or 'Traceback (most recent call last)' in line for line in scoped):
        return 'FAILED'
    if any(re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ KSR_DONE series=36(?:\s|$)', line) for line in scoped):
        return 'DONE'
    return 'RUNNING' if alive else 'GONE_WITHOUT_MARKER'


def group_alive(pgid, start_ticks):
    leader = Path(f'/proc/{pgid}/stat')
    if leader.exists():
        fields = leader.read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) != start_ticks:
            raise ValueError('upstream PID reused')
    for p in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = p.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                return True
        except (FileNotFoundError, ProcessLookupError):
            continue
    return False


def write_json(path, value):
    path = Path(path); temp = path.with_name(path.name + '.tmp')
    encoded = json.dumps(value, indent=2, allow_nan=False) + '\n'
    with open(temp, 'w') as f:
        f.write(encoded); f.flush(); os.fsync(f.fileno())
    if temp.read_text() != encoded:
        raise ValueError('write/readback mismatch: ' + str(path))
    os.replace(temp, path)


def memory_headroom():
    c = Path('/sys/fs/cgroup')
    maximum = (c / 'memory.max').read_text().strip()
    if maximum == 'max':
        raise ValueError('finite cgroup memory limit required')
    return int(maximum) - int((c / 'memory.current').read_text())


def reader_limits():
    os.nice(19)
    resource.setrlimit(resource.RLIMIT_AS, (3 * GIB, 3 * GIB))
    resource.setrlimit(resource.RLIMIT_CPU, (1200, 1200))


def main(config_path):
    cfg = json.loads(Path(config_path).read_text())
    root = Path(cfg['root']); marker = Path(cfg['marker_root'])
    marker.mkdir(parents=True, exist_ok=True)
    log = marker / 'waiter.log'

    def say(message):
        line = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') + ' ' + message
        with open(log, 'a') as f:
            f.write(line + '\n'); f.flush(); os.fsync(f.fileno())
        print(line, flush=True)

    claim = root / '.reader_claim'
    try:
        claim.mkdir()
    except FileExistsError:
        say('KSR_READOUT_FAILED claim_already_exists')
        return 1
    try:
        metadata = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'upstream_pgid': cfg['upstream_pgid'],
                    'upstream_start_ticks': cfg['upstream_start_ticks'], 'waiter_sha256': sha(__file__),
                    'config_sha256': sha(config_path), 'role': 'WAIT_THEN_READ_ONLY',
                    'limits': {'reader_RLIMIT_AS_bytes': 3 * GIB, 'reader_CPU_seconds': 1200,
                               'reader_timeout_seconds': 1500, 'minimum_cgroup_headroom_bytes': 4 * GIB,
                               'OMP_NUM_THREADS': 1, 'OPENBLAS_NUM_THREADS': 1, 'nice': 19}}
        write_json(marker / 'PGID.json', metadata)
        check_hashes(cfg['pins'])
        say('KSR_READOUT_START ' + json.dumps(metadata, sort_keys=True))
        deadline = time.monotonic() + 30 * 3600
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError('upstream wait exceeded 30 hours')
            state = classify(Path(cfg['upstream_log']).read_text(), cfg['upstream_start_line'],
                             group_alive(cfg['upstream_pgid'], cfg['upstream_start_ticks']))
            if state == 'DONE':
                say('KSR_READOUT_UPSTREAM_DONE series=36')
                break
            if state != 'RUNNING':
                raise RuntimeError('upstream_' + state)
            say('KSR_READOUT_WAIT RUNNING')
            time.sleep(60)

        # These are metadata/hash reads only, after the exact run's terminal.
        check_hashes(cfg['pins'])
        order = [tuple(line.split()) for line in Path(cfg['order']).read_text().splitlines() if line.strip()]
        if len(order) != 36 or len(set(order)) != 36:
            raise ValueError('ORDER must contain 36 unique cells')
        required = [Path(cfg['series']) / f'SER_{cell}_s{seed}.npz' for cell, seed in order]
        required += [Path(cfg['series']) / f'SER_KSR_S0_m0_s{seed}.npz' for seed in ('42', '2027')]
        required += [Path(cfg['tstats']) / f'KSR_S1_m{k}_s{seed}.npz' for k in range(8) for seed in ('42', '2027')]
        gate_names = [f'KSR_S1_m{k}' for k in range(8)] + ['KSR_RED_m0', 'KSR_SEAT_ONLY_m0', 'KSR_COMP_ONLY_m0']
        for cell in gate_names:
            p = Path(cfg['gate4']) / f'{cell}.json'
            gate = json.loads(p.read_text())
            if gate.get('PASS') is not True or gate.get('self_sha256') != cfg['gate4_sha256']:
                raise ValueError('gate4 identity or PASS invalid: ' + cell)
            required.append(p)
        for path in required:
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError('required input missing/empty: ' + str(path))
        bound = {str(path): sha(path) for path in required}
        write_json(root / 'INPUTS_BOUND.json', {'inputs': bound, 'code_pins': cfg['pins'], 'series_count': 38,
                                              'tstats_count': 16, 'gate4_count': 11,
                                              'terminal_log_sha256': sha(cfg['upstream_log'])})
        say('KSR_READOUT_INPUTS_BOUND series=38 tstats=16 gate4=11 sha=' + sha(root / 'INPUTS_BOUND.json'))
        resource_deadline = time.monotonic() + 2 * 3600
        while memory_headroom() < 4 * GIB:
            if time.monotonic() > resource_deadline:
                raise TimeoutError('cgroup headroom remained below 4 GiB')
            say('KSR_READOUT_WAIT_RESOURCE cgroup_headroom_bytes=' + str(memory_headroom()))
            time.sleep(60)

        output = root / 'KSR_BOOK_2026-09-27.json'
        if output.exists() or output.with_name(output.name + '.tmp').exists():
            raise ValueError('reader output already exists; refuse overwrite')
        command = [cfg['python'], '-B', str(root / 'dlarch_ksr_book.py'), 'PATH,HOME,LC_CTYPE',
                   str(root / 'cell_map.json'), cfg['series'], cfg['tstats'], str(output)]
        clean = {'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LC_CTYPE': 'C',
                 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
        say('KSR_READOUT_READER_START cgroup_headroom_bytes=' + str(memory_headroom()))
        started = time.monotonic()
        with open(root / 'reader.log', 'x') as stdout:
            result = subprocess.run(command, env=clean, stdout=stdout, stderr=subprocess.STDOUT,
                                    preexec_fn=reader_limits, timeout=1500)
        if result.returncode:
            raise RuntimeError('reader_rc=' + str(result.returncode))
        receipt = json.loads(output.read_text())
        if receipt['self_sha256'] != cfg['pins'][str(root / 'dlarch_ksr_book.py')]:
            raise ValueError('reader receipt source sha mismatch')
        for path, digest in receipt['inputs'].items():
            if bound.get(path) != digest:
                raise ValueError('reader consumed unbound or changed input: ' + path)
        check_hashes(bound)
        check_hashes(cfg['pins'])
        terminal = {'status': 'DONE', 'output': str(output), 'output_sha256': sha(output),
                    'reader_seconds': time.monotonic() - started, 'maxrss_child_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                    'input_manifest_sha256': sha(root / 'INPUTS_BOUND.json'), **metadata}
        write_json(root / 'DONE.json', terminal)
        say('KSR_READOUT_DONE output_sha256=' + terminal['output_sha256'])
        return 0
    except Exception as exc:
        failure = {'status': 'FAILED', 'error_type': type(exc).__name__, 'reason': str(exc)}
        write_json(marker / 'FAILED.json', failure)
        say('KSR_READOUT_FAILED ' + json.dumps(failure, sort_keys=True))
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
