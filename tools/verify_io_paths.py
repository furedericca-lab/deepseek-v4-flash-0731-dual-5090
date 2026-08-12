#!/usr/bin/env python3
"""Compare buffered and O_DIRECT SHA256 reads of one regular file.

O_DIRECT reads use aligned mmap buffers and aligned block lengths.  A final
unaligned tail is read buffered, since Linux cannot service it through the
direct-I/O interface without reading beyond the file boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import mmap
import os
from pathlib import Path

BLOCK = 4 * 1024 * 1024
ALIGN = 4096


def buffered_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while chunk := handle.read(BLOCK):
            digest.update(chunk)
    return digest.hexdigest()


def direct_sha256(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_DIRECT", 0)
    fd = os.open(path, flags)
    digest = hashlib.sha256()
    try:
        size = os.fstat(fd).st_size
        direct_size = size - (size % ALIGN)
        position = 0
        while position < direct_size:
            length = min(BLOCK, direct_size - position)
            length -= length % ALIGN
            buf = mmap.mmap(-1, length)
            try:
                view = memoryview(buf)
                read = os.readv(fd, [view])
                if read != length:
                    raise OSError(f"short O_DIRECT read at {position}: {read}/{length}")
                digest.update(view)
                view.release()
            finally:
                buf.close()
            position += length
        if position < size:
            with path.open("rb", buffering=0) as handle:
                handle.seek(position)
                digest.update(handle.read(size - position))
    finally:
        os.close(fd)
    return digest.hexdigest()


def verify(path: Path) -> dict[str, str | bool]:
    buffered = buffered_sha256(path)
    direct = direct_sha256(path)
    return {"path": str(path), "buffered_sha256": buffered,
            "direct_sha256": direct, "match": buffered == direct}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--direct-only", action="store_true",
                        help="hash only through O_DIRECT; required for large checkpoint scans")
    args = parser.parse_args()
    failures = []
    for path in args.paths:
        if not path.is_file():
            print(f"MISSING {path}")
            failures.append(str(path))
            continue
        try:
            if args.direct_only:
                direct = direct_sha256(path)
                result = {"path": str(path), "direct_sha256": direct, "match": True}
            else:
                result = verify(path)
        except OSError as exc:
            print(f"ERROR {path}: {exc}")
            failures.append(str(path))
            continue
        status = "PASS" if result["match"] else "MISMATCH"
        print(f"{status} {path}")
        if "buffered_sha256" in result:
            print(f"  buffered: {result['buffered_sha256']}")
        print(f"  direct:   {result['direct_sha256']}")
        if not result["match"]:
            failures.append(str(path))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
