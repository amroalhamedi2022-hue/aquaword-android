#!/usr/bin/env python3
"""Validate security-relevant fields in an apksigner verification report.

This parses tool output only; it does not itself verify an APK signature.
The report must come from a successful apksigner verify --verbose --print-certs
process, and this gate independently requires v2 verification plus a SHA-256
certificate digest in one of the known apksigner output formats.
"""
import argparse
import re
import sys
from pathlib import Path


class SignatureReportError(ValueError):
    """Raised when apksigner output lacks required, parseable evidence."""


_V2_OK = re.compile(
    r"^\s*Verified using v2 scheme \(APK Signature Scheme v2\):\s*true\s*$",
    re.MULTILINE,
)
_DIGEST_PREFIX = re.compile(
    r"^\s*(?:Signer #\d+ certificate SHA-256 digest:|"
    r"V2 Signer: certificate SHA-256 digest:)\s*(?P<digest>.*?)\s*$"
)
_HEX_DIGEST = re.compile(r"^[0-9a-fA-F]{64}$")


def verify_signature_report(report: str) -> tuple[str, ...]:
    """Return normalized SHA-256 certificate digests or raise on weak evidence."""
    if not _V2_OK.search(report):
        raise SignatureReportError("APK Signature Scheme v2 verification is not explicitly true")

    digest_lines = [
        line for line in report.splitlines()
        if "certificate SHA-256 digest:" in line
    ]
    if not digest_lines:
        raise SignatureReportError("No certificate SHA-256 digest was reported")

    digests = []
    for line in digest_lines:
        match = _DIGEST_PREFIX.match(line)
        if not match:
            raise SignatureReportError(f"Unrecognized certificate digest line: {line.strip()}")
        normalized = match.group("digest").replace(":", "")
        if not _HEX_DIGEST.fullmatch(normalized):
            raise SignatureReportError("Certificate SHA-256 digest is malformed")
        digests.append(normalized.lower())

    return tuple(digests)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = args.report.read_text(encoding="utf-8")
        digests = verify_signature_report(report)
    except (OSError, UnicodeError, SignatureReportError) as exc:
        print(f"FAIL apksigner report: {exc}", file=sys.stderr)
        return 1
    print("PASS apksigner report: v2=true certificate_sha256=" + ",".join(digests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
