#!/usr/bin/env python3
"""Verify the *exact* native engine library inside an AquaWord Android APK.

This is packaging evidence only: it does not certify that Writer starts,
that SAF works on a device, or that the APK is a final release.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile
import struct
import tempfile

from native_engine_artifact import NativeArtifactError, inspect_artifact


class NativeApkError(ValueError):
    """The APK cannot be trusted as a packaging test result."""


def load_segments(stream, size: int, abi: str) -> list[tuple]:
    """Fingerprint ELF PT_LOAD bytes, which survive ordinary debug stripping."""
    stream.seek(0)
    header = stream.read(64)
    machines = {"arm64-v8a": 183, "armeabi-v7a": 40, "x86": 3, "x86_64": 62}
    elf_class = 2 if abi in ("arm64-v8a", "x86_64") else 1
    if (abi not in machines or len(header) < 52 or header[:4] != b"\x7fELF"
            or header[4] != elf_class or header[5] != 1
            or struct.unpack_from("<HH", header, 16) != (3, machines[abi])):
        raise NativeApkError(f"Invalid ELF shared library for ABI {abi}")
    if elf_class == 2:
        if len(header) < 64:
            raise NativeApkError("Truncated ELF64 header")
        phoff = struct.unpack_from("<Q", header, 32)[0]
        entsize, count = struct.unpack_from("<HH", header, 54)
        fmt = "<IIQQQQQQ"
    else:
        phoff = struct.unpack_from("<I", header, 28)[0]
        entsize, count = struct.unpack_from("<HH", header, 42)
        fmt = "<IIIIIIII"
    minimum = struct.calcsize(fmt)
    if not (1 <= count <= 4096 and entsize >= minimum and
            phoff <= size and count * entsize <= size - phoff):
        raise NativeApkError("Invalid ELF program header table")
    segments = []
    for index in range(count):
        stream.seek(phoff + index * entsize)
        raw = stream.read(minimum)
        if len(raw) != minimum:
            raise NativeApkError("Truncated ELF program header")
        fields = struct.unpack(fmt, raw)
        if fields[0] != 1:  # PT_LOAD
            continue
        if elf_class == 2:
            _, flags, offset, vaddr, _, filesz, memsz, _ = fields
        else:
            _, offset, vaddr, _, filesz, memsz, flags, _ = fields
        if filesz > memsz or offset > size or filesz > size - offset:
            raise NativeApkError("Invalid ELF load segment bounds")
        stream.seek(offset)
        digest = hashlib.sha256()
        remaining = filesz
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise NativeApkError("Truncated ELF load segment")
            digest.update(chunk)
            remaining -= len(chunk)
        segments.append((vaddr, flags, filesz, memsz, digest.hexdigest()))
    if not segments:
        raise NativeApkError("ELF contains no loadable segments")
    return segments


def verify_native_apk(apk: Path, engine: Path, abi: str) -> dict:
    if apk.is_symlink() or not apk.is_file():
        raise NativeApkError(f"APK is missing or symlinked: {apk}")
    try:
        expected = inspect_artifact(engine, abi)
    except NativeArtifactError as exc:
        raise NativeApkError(str(exc)) from exc

    member_name = f"lib/{abi}/liblo-native-code.so"
    try:
        with zipfile.ZipFile(apk) as archive:
            names = archive.namelist()
            for required in ("classes.dex", member_name):
                if names.count(required) != 1:
                    raise NativeApkError(
                        f"APK must contain exactly one {required}; found {names.count(required)}")
            dex = archive.getinfo("classes.dex")
            if dex.file_size == 0:
                raise NativeApkError("APK contains empty classes.dex")
            member = archive.getinfo(member_name)
            if member.file_size > expected["size"] * 2 + 32 * 1024 * 1024:
                raise NativeApkError("Packaged native library exceeds bounded verification size")
            digest = hashlib.sha256()
            total = 0
            # Stream compressed content with bounded RAM; spill to disk.
            with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as extracted:
                with archive.open(member, "r") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        total += len(chunk)
                        digest.update(chunk)
                        extracted.write(chunk)
                if total != member.file_size:
                    raise NativeApkError("Truncated packaged native library")
                identical = total == expected["size"] and digest.hexdigest() == expected["sha256"]
                if not identical:
                    # Android Gradle may strip non-loadable debug sections.
                    # The executable/loadable bytes must still match the engine.
                    with Path(expected["path"]).open("rb") as source:
                        original_segments = load_segments(source, expected["size"], abi)
                    packaged_segments = load_segments(extracted, total, abi)
                    if packaged_segments != original_segments:
                        raise NativeApkError(
                            "Packaged native ELF loadable segments differ from verified engine")
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise NativeApkError(f"APK ZIP is invalid or unreadable: {exc}") from exc

    apk_digest = hashlib.sha256()
    with apk.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            apk_digest.update(chunk)
    return {"apk": str(apk), "apk_sha256": apk_digest.hexdigest(),
            "abi": abi, "native_sha256": expected["sha256"],
            "native_bytes": expected["size"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--engine-dir", required=True, type=Path)
    parser.add_argument("--abi", default="arm64-v8a")
    args = parser.parse_args(argv)
    try:
        info = verify_native_apk(args.apk, args.engine_dir, args.abi)
        print("PASS native APK: {apk} ABI={abi} native={native_bytes} bytes "
              "native-SHA256={native_sha256} APK-SHA256={apk_sha256}".format(**info))
        return 0
    except (NativeApkError, NativeArtifactError) as exc:
        print(f"FAIL native APK: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
