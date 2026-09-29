#!/usr/bin/env python3
"""Streaming AES-256-GCM archives. Key arrives on stdin, never in argv or logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b'POD_AES256_GCM_V1\n'
HEADER_BYTES = len(MAGIC) + 12 + 8 + 32
CHUNK = 4*1024*1024


def verify_or_decrypt(path, key, destination=None):
    partial = None
    if destination is not None:
        if destination.exists():
            raise RuntimeError('Refuse to overwrite a restored file')
        partial = destination.with_name(destination.name + '.partial')
        output = partial.open('xb')
    else:
        output = None
    try:
        with path.open('rb') as src:
            header = src.read(HEADER_BYTES)
            if len(header) != HEADER_BYTES or not header.startswith(MAGIC):
                raise RuntimeError('Invalid encryption header')
            off = len(MAGIC); nonce = header[off:off+12]
            size = struct.unpack('>Q', header[off+12:off+20])[0]
            expected = header[-32:].hex()
            if path.stat().st_size != HEADER_BYTES + size + 16:
                raise RuntimeError('Invalid ciphertext length')
            src.seek(-16, os.SEEK_END); tag = src.read(16); src.seek(HEADER_BYTES)
            dec = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            dec.authenticate_additional_data(header)
            h = hashlib.sha256(); remaining = size
            while remaining:
                chunk = src.read(min(CHUNK, remaining))
                if not chunk: raise RuntimeError('Truncated ciphertext')
                remaining -= len(chunk); plain = dec.update(chunk); h.update(plain)
                if output is not None: output.write(plain)
            dec.finalize()
            if h.hexdigest() != expected: raise RuntimeError('Plaintext hash mismatch')
        if output is not None:
            output.flush(); os.fsync(output.fileno()); output.close(); output = None
            os.replace(partial, destination)
        return {'plaintext_bytes': size, 'plaintext_sha256': expected, 'authentication': 'PASS'}
    finally:
        if output is not None: output.close()
        if partial is not None and partial.exists(): partial.unlink()


def encrypt(source, destination, key, expected):
    if destination.exists(): raise RuntimeError('Refuse to overwrite encrypted archive')
    before = source.stat(); nonce = os.urandom(12)
    if before.st_size >= 2**36-32: raise RuntimeError('GCM per-message size limit')
    header = MAGIC + nonce + struct.pack('>Q', before.st_size) + bytes.fromhex(expected)
    enc = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    enc.authenticate_additional_data(header)
    partial = destination.with_name(destination.name+'.partial'); h = hashlib.sha256()
    with source.open('rb') as src, partial.open('xb') as dst:
        dst.write(header)
        while chunk := src.read(CHUNK):
            h.update(chunk); dst.write(enc.update(chunk))
        dst.write(enc.finalize()); dst.write(enc.tag); dst.flush(); os.fsync(dst.fileno())
    after = source.stat()
    if h.hexdigest() != expected or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Original archive changed')
    os.replace(partial, destination)
    result = verify_or_decrypt(destination, key)
    h = hashlib.sha256()
    with destination.open('rb') as f:
        while chunk := f.read(CHUNK): h.update(chunk)
    result.update(encrypted_file=destination.name, encrypted_sha256=h.hexdigest(),
                  encrypted_bytes=destination.stat().st_size)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['seal', 'decrypt'])
    ap.add_argument('--root', type=Path)
    ap.add_argument('--input', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    os.umask(0o077)
    with os.fdopen(os.dup(0), 'rb') as f: key = f.read(33)
    if len(key) != 32: raise RuntimeError('Exactly 32 key bytes required on stdin')
    if args.action == 'decrypt':
        if args.input is None or args.output is None: raise RuntimeError('input/output required')
        print(json.dumps(verify_or_decrypt(args.input, key, args.output))); return
    if args.root is None: raise RuntimeError('root required')
    manifest = json.loads((args.root/'FILE_BACKUP_VERIFIED.json').read_text())
    results = []
    for row in manifest['verification']:
        source = args.root/(row['label']+'.tar')
        print(json.dumps({'stage': 'encrypt_and_verify', 'archive': source.name}), flush=True)
        results.append(encrypt(source, source.with_name(source.name+'.aes256gcm'), key, row['sha256']))
        print(json.dumps(results[-1]), flush=True)
    receipt = {'status': 'PASS', 'cipher': 'AES-256-GCM', 'key_bits': 256,
               'key_saved_on_pod': False, 'archives': results,
               'completed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with (args.root/'ENCRYPTION_VERIFIED.json').open('x') as f:
        json.dump(receipt, f, indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


if __name__ == '__main__':
    main()
