#!/usr/bin/env python3
"""Preserve a quiescent Pod's volatile files. Never stops jobs or calls a venue.

Archives are private, uncompressed PAX tar files. They are NOT machine images.
Run from /workspace; restore only into a staging directory, never over a live Pod.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import time

CHUNK = 4 * 1024 * 1024
EXCLUDES = ['/workspace', '/proc', '/sys', '/dev', '/run', '/var/log',
            '/var/cache', '/root/.cache', '/root/.local/share/jupyter/runtime']


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while b := f.read(CHUNK):
            h.update(b)
    return h.hexdigest()


def mounts():
    rows = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        a, b = left.split(), right.split()
        p = a[4].replace('\\040', ' ').replace('\\011', '\t').replace('\\134', '\\')
        rows.append({'path': p, 'type': b[0], 'source': b[1]})
    return rows


def signature(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


class HashRead:
    def __init__(self, stream):
        self.stream = stream
        self.h = hashlib.sha256()
    def read(self, n=-1):
        b = self.stream.read(n); self.h.update(b); return b


def inventory(root, excludes):
    result, skipped = [], []
    device = root.stat().st_dev
    def walk(p):
        if str(p) in excludes:
            skipped.append({'path': str(p), 'reason': 'explicit_or_mount_exclusion'})
            return
        s = p.lstat()
        if s.st_dev != device:
            skipped.append({'path': str(p), 'reason': 'other_filesystem'}); return
        if not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode)):
            skipped.append({'path': str(p), 'reason': 'runtime_special_file'}); return
        result.append((p, signature(s)))
        if stat.S_ISDIR(s.st_mode):
            for child in sorted(p.iterdir()):
                walk(child)
    walk(root)
    return result, skipped


def pack(root, label, dest, excludes):
    entries, skipped = inventory(root, excludes)
    write_json(dest / (label + '_excluded.json'), skipped)
    output = dest / (label + '.tar')
    manifest = dest / (label + '_manifest.jsonl')
    count, nbytes = 0, 0
    started = time.monotonic(); last = started
    print(json.dumps({'stage': 'pack', 'label': label, 'entries': len(entries)}), flush=True)
    with manifest.open('w') as mf, output.open('wb') as raw:
        with tarfile.open(fileobj=raw, mode='w|', format=tarfile.PAX_FORMAT, bufsize=1024*1024) as tf:
            for p, expected in entries:
                before = signature(p.lstat())
                if not stat.S_ISDIR(before[2]) and before != expected:
                    raise RuntimeError('Source changed before capture: ' + str(p))
                name = label if p == root else label + '/' + str(p.relative_to(root))
                info = tf.gettarinfo(str(p), arcname=name)
                row = {'name': name, 'source': str(p), 'signature': before,
                       'size': info.size, 'mode': stat.S_IMODE(info.mode), 'uid': info.uid, 'gid': info.gid,
                       'type': info.type.decode('ascii'), 'linkname': info.linkname}
                if info.isfile():
                    with p.open('rb') as src:
                        reader = HashRead(src); tf.addfile(info, reader)
                        row['sha256'] = reader.h.hexdigest()
                    nbytes += info.size
                else:
                    tf.addfile(info)
                after = signature(p.lstat())
                if not info.isdir() and after != before:
                    raise RuntimeError('Source changed during capture: ' + str(p))
                mf.write(json.dumps(row, ensure_ascii=False) + '\n')
                count += 1
                if time.monotonic() - last > 25:
                    print(json.dumps({'stage': 'pack', 'label': label, 'files': count,
                                      'bytes': nbytes, 'elapsed_s': round(time.monotonic()-started)}), flush=True)
                    last = time.monotonic()
        raw.flush(); os.fsync(raw.fileno())
        mf.flush(); os.fsync(mf.fileno())
    return {'label': label, 'entries': count, 'data_bytes': nbytes,
            'archive_bytes': output.stat().st_size, 'excluded_entries': len(skipped)}


def verify(label, dest, check_source=True, write_receipt=True):
    manifest = dest / (label + '_manifest.jsonl')
    records = [json.loads(x) for x in manifest.read_text().splitlines()]
    source_changed, count, bytes_read = [], 0, 0
    seen = set(); started = time.monotonic(); last = started
    with (dest / (label + '.tar')).open('rb') as raw:
        reader = HashRead(raw)
        with tarfile.open(fileobj=reader, mode='r|', bufsize=1024*1024) as tf:
            for member in tf:
                if count >= len(records):
                    raise RuntimeError('Unexpected extra member')
                row = records[count]
                for key, actual in [('name', member.name), ('size', member.size), ('mode', member.mode),
                                    ('uid', member.uid), ('gid', member.gid),
                                    ('type', member.type.decode('ascii')), ('linkname', member.linkname)]:
                    if row[key] != actual:
                        raise RuntimeError('Archive metadata mismatch: ' + row['name'] + ':' + key)
                if member.isfile():
                    h = hashlib.sha256()
                    with tf.extractfile(member) as f:
                        while b := f.read(CHUNK):
                            h.update(b); bytes_read += len(b)
                    if h.hexdigest() != row['sha256']:
                        raise RuntimeError('Archive content mismatch: ' + row['name'])
                if member.islnk() and member.linkname not in seen:
                    raise RuntimeError('Unresolved archive hard link: ' + row['name'])
                seen.add(member.name)
                if check_source and not member.isdir():
                    p = Path(row['source'])
                    if not p.exists() and not p.is_symlink():
                        source_changed.append({'path': str(p), 'reason': 'missing'})
                    elif signature(p.lstat()) != row['signature']:
                        source_changed.append({'path': str(p), 'reason': 'changed'})
                count += 1
                if time.monotonic()-last > 25:
                    print(json.dumps({'stage': 'verify', 'label': label, 'files': count,
                                      'bytes': bytes_read}), flush=True); last = time.monotonic()
        while reader.read(CHUNK):
            pass
        archive_sha = reader.h.hexdigest()
    if count != len(records):
        raise RuntimeError('Archive missing members')
    result = {'label': label, 'entries_verified': count, 'bytes_verified': bytes_read,
              'sha256': archive_sha, 'manifest_sha256': sha(manifest),
              'source_changed': source_changed, 'verified_utc': now(),
              'status': 'PASS' if not source_changed else 'SOURCE_CHANGED'}
    if write_receipt:
        write_json(dest / (label + '_verification.json'), result)
    if source_changed:
        raise RuntimeError('Source changed after capture; see private verification receipt')
    return result


def process_inventory():
    result = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            args = (p/'cmdline').read_bytes().split(b'\0')
            if not args or b'python' not in args[0]:
                continue
            status = (p/'status').read_text().splitlines()
            row = {'pid': int(p.name), 'executable': args[0].decode(errors='replace'),
                   'state': next(x for x in status if x.startswith('State:')),
                   'script_paths': [a.decode(errors='replace') for a in args[1:]
                                    if a.startswith(b'/') and a.endswith(b'.py')],
                   'cwd': os.readlink(p/'cwd')}
            result.append(row)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--destination', required=True, type=Path)
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--skip-source-check', action='store_true')
    args = ap.parse_args(); dest = args.destination.resolve()
    os.umask(0o077)
    if args.verify_only:
        results = [verify(label, dest, not args.skip_source_check, write_receipt=False)
                   for label in ('rootfs', 'shm')]
        print(json.dumps(results), flush=True); return
    if args.skip_source_check:
        raise RuntimeError('Cannot skip source checks when creating a backup')
    mi = mounts()
    wm = next((x for x in mi if x['path'] == '/workspace'), None)
    if wm is None or not str(dest).startswith('/workspace/') or wm['type'] != 'fuse':
        raise RuntimeError('Destination must be on the inspected network /workspace mount')
    dest.mkdir(mode=0o700, parents=False, exist_ok=False)
    gpu = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,used_gpu_memory',
                          '--format=csv,noheader'], text=True, capture_output=True, check=True)
    if gpu.stdout.strip():
        raise RuntimeError('GPU process appeared; reconcile its checkpoint before backup')
    write_json(dest/'PREFLIGHT.json', {'created_utc': now(), 'host': os.uname().nodename,
               'mounts': mi, 'python_processes': process_inventory(), 'gpu_compute_processes': [],
               'note': 'File preservation only. No RAM snapshot, no service or automatic restart.'})
    probe = dest/'WRITE_PROBE.bin'; block = os.urandom(1024*1024)
    with probe.open('wb') as f:
        for _ in range(256): f.write(block)
        f.flush(); os.fsync(f.fileno())
    expected = hashlib.sha256(block*256).hexdigest()
    if sha(probe) != expected: raise RuntimeError('Network write/read probe failed')
    probe.unlink()
    write_json(dest/'WRITE_PROBE.json', {'status': 'PASS', 'bytes': 256*1024*1024,
                                        'sha256': expected, 'utc': now()})
    excluded = set(EXCLUDES + [x['path'] for x in mi if x['path'] != '/'])
    packs, results = [], []
    for root, label, exc in [(Path('/'), 'rootfs', excluded), (Path('/dev/shm'), 'shm', set())]:
        packs.append(pack(root, label, dest, exc))
        results.append(verify(label, dest))
    write_json(dest/'FILE_BACKUP_VERIFIED.json', {'status': 'PASS', 'completed_utc': now(),
               'archives': packs, 'verification': results,
               'limitations': ['No in-memory process checkpoint.',
                               'Not a bootable container image; recover files selectively.',
                               'Runtime mounts, logs and caches listed in exclusion receipts are omitted.',
                               'Does not certify restored Python/CUDA numerical parity.']})
    print(json.dumps({'status': 'FILE_BACKUP_VERIFIED', 'destination': str(dest)}), flush=True)


if __name__ == '__main__':
    main()
