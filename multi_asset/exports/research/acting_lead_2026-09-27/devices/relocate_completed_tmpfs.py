#!/usr/bin/env python3
"""Relocate exact inactive historical artifacts; preserve names and bytes.

No global cache operations, deletion of evidence, or job/process control.
Single-link regular files only. Original bytes remain until durable, independently
rehashed destination and PREPARED journal entry exist. Atomic symlink replacement
then releases tmpfs. A crash leaves an original or a verified destination.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOTS = ('/dev/shm/news_2026-09-23/runs', '/dev/shm/news2_2026-09-23/runs')
EXACT = ('/dev/shm/nc_2026-09-23/work/cache_crypto.npy',
         '/dev/shm/nc_2026-09-23/work/R_crypto.npy')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def signature(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_nlink,
            s.st_ctime_ns, s.st_mode, s.st_uid, s.st_gid)


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def assert_not_open(path):
    # Refuse research-user or capable-process fd/mmap references. A different
    # unprivileged UID cannot write the owner-only-writable sources admitted
    # below. Its read-only fd would retain the unchanged old inode if one existed.
    # Do not claim a system-wide no-reader proof or inspect environment/argv.
    wanted = str(path)
    for proc in Path('/proc').glob('[0-9]*'):
        if proc.name == str(os.getpid()):
            continue
        try:
            status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines())
            uids = {int(v) for v in status['Uid'].split()}
            if os.getuid() not in uids and int(status['CapEff'].strip(), 16) == 0:
                continue
            for fd in (proc / 'fd').iterdir():
                try:
                    if os.readlink(fd) == wanted:
                        raise ValueError('active fd: ' + wanted)
                except FileNotFoundError:
                    pass
            if wanted in (proc / 'maps').read_text():
                raise ValueError('active mmap: ' + wanted)
        except (FileNotFoundError, ProcessLookupError):
            pass


def relocate(path, destination, journal):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError('not an unaliased regular file: ' + str(path))
    if before.st_uid != os.getuid() or before.st_mode & 0o022:
        raise ValueError('source not privately writable: ' + str(path))
    assert_not_open(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Sync created parent hierarchy before removing the tmpfs directory entry.
    parent = destination.parent
    while str(parent) != '/':
        fsync_dir(parent)
        if str(parent) == '/workspace':
            break
        parent = parent.parent
    with open(path, 'rb') as src, open(destination, 'xb') as dst:
        if signature(os.fstat(src.fileno())) != signature(before):
            raise ValueError('source changed before copy')
        digest = hashlib.sha256()
        for block in iter(lambda: src.read(1024 * 1024), b''):
            dst.write(block); digest.update(block)
        dst.flush(); os.fchmod(dst.fileno(), stat.S_IMODE(before.st_mode)); os.fsync(dst.fileno())
        if signature(os.fstat(src.fileno())) != signature(before):
            raise ValueError('source changed during copy')
    expected = digest.hexdigest()
    if sha(destination) != expected or signature(path.lstat()) != signature(before):
        raise ValueError('post-copy identity differs')
    fsync_dir(destination.parent)
    record = {'source': str(path), 'destination': str(destination), 'sha256': expected,
              'bytes': before.st_size, 'source_identity': signature(before)}
    journal('PREPARED', record)
    assert_not_open(path)
    if signature(path.lstat()) != signature(before):
        raise ValueError('source changed before atomic switch')
    link = path.with_name(path.name + '.acting_relocate_link')
    os.symlink(str(destination), link)
    os.replace(link, path); fsync_dir(path.parent)
    if not path.is_symlink() or path.resolve() != destination or sha(path) != expected:
        raise ValueError('post-switch original path mismatch')
    # Only our freshly created private copy; never advise or drop shared caches.
    with open(destination, 'rb') as own_copy:
        os.posix_fadvise(own_copy.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    journal('COMMITTED', record)
    return record


def main(out):
    out = Path(out)
    if not str(out).startswith('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/tmpfs_archive_'):
        raise ValueError('private archive root required')
    out.mkdir(mode=0o700)  # Existing root is refused; no ambiguous resume/overwrite.
    def journal(state, record):
        with open(out / 'JOURNAL.jsonl', 'a') as f:
            f.write(json.dumps({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                'state': state, **record}, sort_keys=True) + '\n')
            f.flush(); os.fsync(f.fileno())
        fsync_dir(out)
    files = [Path(p) for p in EXACT]
    for root in ROOTS:
        files += sorted(Path(root).glob('*/PATH_*.npz'))
    if len(files) != 706 or len(set(files)) != len(files):
        raise ValueError('historical population changed: ' + str(len(files)))
    for p in files:
        if p.is_symlink() or p.stat().st_nlink != 1:
            raise ValueError('aliased population: ' + str(p))
        assert_not_open(p)
    plan = {str(p): {'bytes': p.stat().st_size, 'identity': signature(p.stat())} for p in files}
    journal('PLAN', {'files': plan, 'bytes_total': sum(v['bytes'] for v in plan.values())})
    rows = []
    for p in files:
        if signature(p.lstat()) != tuple(plan[str(p)]['identity']):
            raise ValueError('plan identity changed')
        rows.append(relocate(p, out / 'data' / p.relative_to('/dev/shm'), journal))
        if len(rows) <= 2 or len(rows) % 64 == 0:
            print(json.dumps({'completed': len(rows), 'bytes': sum(r['bytes'] for r in rows)}), flush=True)
    journal('DONE', {'count': len(rows), 'bytes': sum(r['bytes'] for r in rows)})
    print('RELOCATION_DONE', len(rows), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
