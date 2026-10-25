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

from native_engine_artifact import NativeArtifactError, inspect_artifact


class NativeApkError(ValueError):
    """The APK cannot be trusted as a packaging test result."""


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
            if member.file_size != expected["size"]:
                raise NativeApkError(
                    f"Packaged ARM64 library size differs from engine: "
                    f"{member.file_size} != {expected['size']}")
            digest = hashlib.sha256()
            total = 0
            with archive.open(member, "r") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    total += len(chunk)
                    digest.update(chunk)
            if total != expected["size"] or digest.hexdigest() != expected["sha256"]:
                raise NativeApkError("Packaged native library SHA-256 differs from verified engine")
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
