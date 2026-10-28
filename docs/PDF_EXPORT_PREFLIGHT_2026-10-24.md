# AquaWord PDF export preflight — source change (2026-10-24)

**Status:** SOURCE CHANGE; Android runtime and real SAF provider: **NOT TESTED**.

## Why
The prior export preflight accepted any file beginning with `%PDF-` and ending with a line-start `%%EOF`. A truncated or synthetic file could satisfy those markers while omitting the final `startxref` and usable cross-reference pointer, and the caller would then open a potentially truncating SAF destination.

## Production changes
- `history/src/org/libreoffice/androidapp/ui/AquaWordPdfPreflight.java` now verifies a supported PDF version header and the **last** `startxref` associated with the final EOF.
- Parse a bounded trailer window (4 KiB), reject absent, malformed, overflowing, zero, or out-of-file offsets.
- Seek to the declared cross-reference location and accept either a classic `xref` table or an indirect-object header for an xref stream.
- Continue accepting incremental updates and PDF whitespace after the final EOF. No whole-file buffering or extra dependencies.
- The existing native export flow still calls preflight **before** `ContentResolver.openOutputStream`.

## Source checks
`history/test/org/libreoffice/androidapp/ui/AquaWordPdfPreflightTest.java` exercises classic xref, xref-stream and incremental examples, malformed/missing EOF, invalid version, trailing junk, missing or invalid pointers and corrupt xref targets. `tests/test_overlay.py` checks ordering and the updated helper contract.

**Important limitation:** This is deliberately a conservative plausibility check, not a full PDF parser, PDF/A validator, content integrity guarantee, or signature verifier. Some otherwise readable nonconforming PDFs may be rejected rather than risking replacement. PDF import, printing, actual Collabora PDF output and Android SAF readback require separate device acceptance. A failed provider write can still leave the destination damaged.

## Release policy
Do not package an APK or enable Final-Ready on this basis. Independent source review, native ARM64 readiness, complete feature acceptance and real Android/Xiaomi Pad 5 verification remain outstanding. No main merge or paid API.
