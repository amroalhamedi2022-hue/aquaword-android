#!/usr/bin/env python3
"""Validate the *actual* LibreOffice Android shared object, not cache markers.

The pinned Collabora engine builds liblo-native-code.so under
engine/android/jniLibs/<ABI> (MPL-2.0 upstream). Restoring only workdir/instdir
can restore the gbuild 'done' marker without the generated shared object.
This tool invalidates that stale marker before make and checks the resulting
ELF before any Gradle packaging attempt. No binary is synthesized or copied.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

ABI_ELF = {"arm64-v8a": (2, 183), "armeabi-v7a": (1, 40),
           "x86": (1, 3), "x86_64": (2, 62)}
MIN_NATIVE_BYTES = 1024 * 1024


class NativeArtifactError(ValueError):
    """A missing, invalid or wrong-architecture native library."""


def artifact_path(engine: Path, abi: str) -> Path:
    if abi not in ABI_ELF:
        raise NativeArtifactError(f"Unsupported Android ABI: {abi}")
    return engine / "android" / "jniLibs" / abi / "liblo-native-code.so"


def inspect_artifact(engine: Path, abi: str, minimum_bytes: int = MIN_NATIVE_BYTES) -> dict:
    path = artifact_path(engine, abi)
    if path.is_symlink():
        raise NativeArtifactError(f"Refusing symlinked native library: {path}")
    if not path.is_file():
        raise NativeArtifactError(f"Missing native library: {path}")
    size = path.stat().st_size
    if size < minimum_bytes:
        raise NativeArtifactError(f"Native library too small ({size} bytes): {path}")
    with path.open("rb") as stream:
        header = stream.read(20)
        if len(header) < 20 or header[:4] != b"\x7fELF":
            raise NativeArtifactError(f"Not an ELF shared library: {path}")
        elf_class, machine = ABI_ELF[abi]
        if header[4] != elf_class or header[5] != 1:
            raise NativeArtifactError(f"Wrong ELF class/endianness for {abi}: {path}")
        e_type, e_machine = struct.unpack("<HH", header[16:20])
        if e_type != 3 or e_machine != machine:
            raise NativeArtifactError(
                f"Wrong ELF type/machine for {abi}: type={e_type}, machine={e_machine}")
        digest = hashlib.sha256()
        digest.update(header)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "size": size, "sha256": digest.hexdigest(), "abi": abi}


def prepare_engine(engine: Path, abi: str) -> bool:
    """Invalidate *only* stale generated Android targets, preserving LO objects.

    Returns True if the Android link stage must run again. The gbuild custom
    target has both a recipe's source/done marker and an outer target stamp.
    Restored stamps without jniLibs would otherwise incorrectly skip linking.
    """
    try:
        inspect_artifact(engine, abi)
        print(f"Native {abi} ELF present; keeping cached gbuild stamps")
        return False
    except NativeArtifactError as exc:
        print(f"Native ELF missing/invalid; forcing Android link: {exc}")
    target = artifact_path(engine, abi)
    stamps = (
        engine / "workdir" / "CustomTarget" / "android" / "source" / "done",
        engine / "workdir" / "CustomTarget" / "android" / "loandroid3.done",
    )
    for path in (target, *stamps):
        if path.is_file() or path.is_symlink():
            path.unlink()
            print(f"Removed stale generated output: {path}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--abi", choices=tuple(ABI_ELF), default="arm64-v8a")
    args = parser.parse_args(argv)
    if not args.engine_dir.is_dir():
        parser.error(f"Engine directory not found: {args.engine_dir}")
    try:
        if args.action == "prepare":
            prepare_engine(args.engine_dir, args.abi)
        else:
            evidence = inspect_artifact(args.engine_dir, args.abi)
            print("PASS native ELF: {abi} {size} bytes SHA-256={sha256} path={path}".format(**evidence))
        return 0
    except NativeArtifactError as exc:
        print(f"FAIL native ELF: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
