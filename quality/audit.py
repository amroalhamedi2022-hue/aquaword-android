#!/usr/bin/env python3
"""AquaWord product acceptance audit: user requirements versus runtime evidence.

This is intentionally stricter than a successful compile. In particular:
- No evidence file or no matching SHA-256 -> NOT VERIFIED.
- A developer's implemented-source claim never equals functional verification.
- No release approval without *physical* device evidence for critical features.
- Android emulator evidence is recorded separately from Xiaomi Pad 5 evidence.

Usage:
  python3 quality/audit.py --evidence-dir smoke-evidence --report quality-report.md
  python3 quality/audit.py --evidence-dir release-evidence --require-release
"""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "quality" / "requirements.json"
CRITICAL_DEVICE_GATES = {"APP-01", "APP-02", "FILE-03", "FILE-04", "SAFE-02", "SAFE-03", "UI-01", "PERF-01"}
ALLOWED_STATES = {"PASS", "FAIL", "NOT_VERIFIED"}
ALLOWED_DEVICES = {"emulator", "physical"}


class AuditError(ValueError):
    pass


def secure_evidence_file(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise AuditError("Evidence file path must be relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise AuditError("Evidence file escapes its root folder")
    if not path.is_file() or path.stat().st_size == 0:
        raise AuditError("Evidence file does not exist or is empty: " + relative)
    return path


def validate_receipt(root: Path, receipt: dict[str, Any]) -> tuple[bool, str]:
    if receipt.get("result") != "PASS":
        return False, "Failed or missing PASS result"
    for key in ("tester", "device", "method", "observed", "time_utc"):
        if not str(receipt.get(key, "")).strip():
            return False, f"Missing reviewer field: {key}"
    if receipt.get("device_class") not in ALLOWED_DEVICES:
        return False, "Unknown device class"
    files = receipt.get("evidence_files", [])
    if not isinstance(files, list) or not files:
        return False, "No first-hand evidence"
    try:
        for item in files:
            path = secure_evidence_file(root, item["path"])
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha != item["sha256"]:
                return False, "Evidence digest mismatch for " + item["path"]
    except (AuditError, KeyError, TypeError) as exc:
        return False, str(exc)
    return True, "Evidence files matched"


def audit(matrix: dict[str, Any], root: Path) -> tuple[list[dict], bool]:
    receipts_path = root / "receipts.json"
    receipts = json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.is_file() else []
    if not isinstance(receipts, list):
        raise AuditError("Receipts must be a JSON array")
    receipts_by_id: dict[str, list[dict]] = {}
    for receipt in receipts:
        if not isinstance(receipt, dict) or "requirement_id" not in receipt:
            raise AuditError("Every receipt requires a requirement_id")
        receipts_by_id.setdefault(receipt["requirement_id"], []).append(receipt)
    result = []
    ids = set()
    release = True
    for requirement in matrix["requirements"]:
        rid = requirement["id"]
        if rid in ids:
            raise AuditError("Duplicate requirement: " + rid)
        ids.add(rid)
        approved_devices = set()
        notes = []
        has_fail = False
        for receipt in receipts_by_id.get(rid, []):
            if receipt.get("result") == "FAIL":
                has_fail = True
                notes.append("Observed failure: " + str(receipt.get("observed", "")))
                continue
            ok, message = validate_receipt(root, receipt)
            if ok:
                approved_devices.add(receipt["device_class"])
            else:
                notes.append("Rejected evidence: " + message)
        if has_fail:
            status = "FAIL"
        elif not approved_devices:
            status = "NOT_VERIFIED"
        elif rid in CRITICAL_DEVICE_GATES and "physical" not in approved_devices:
            status = "EMULATOR_ONLY"
        else:
            status = "PASS"
        # The user requested a complete application, not a reduced feature set.
        # Neither an unverified major feature nor an emulator-only critical gate
        # can silently pass a final release review.
        if status != "PASS":
            release = False
        result.append({**requirement, "actual_status": status,
                       "verified_devices": sorted(approved_devices),
                       "audit_notes": notes})
    if set(receipts_by_id).difference(ids):
        raise AuditError("Receipt references nonexistent requirement")
    if any(item["priority"] == "major" and item["actual_status"] == "FAIL" for item in result):
        release = False
    return result, release


def markdown(items: list[dict], release: bool) -> str:
    groups: dict[str, int] = {}
    for item in items:
        groups[item["actual_status"]] = groups.get(item["actual_status"], 0) + 1
    lines = ["# AquaWord — المطلوب مقابل ما تم التحقق منه", "",
             "**قرار التسليم: " + ("مسموح بعد مراجعة بشرية" if release else "ممنوع — متطلبات غير مثبتة") + "**",
             "",
             f"**إجمالي المطالب:** {len(items)}  |  " +
             "  |  ".join(f"{k}: {v}" for k, v in sorted(groups.items())),
             "",
             "| المتطلب | الأولوية | الإثبات | الحالة |",
             "|---|---|---|---|"]
    for item in items:
        title = item["description"].replace("|", "/")
        proof = ", ".join(item["verified_devices"]) or "—"
        lines.append(f"| {item['id']}: {title} | {item['priority']} | {proof} | {item['actual_status']} |")
    lines.extend(["", "CI PASS ≠ RELEASE PASS. A screenshot of the Android home screen is not proof that AquaWord works.",
                  "Visual comparisons must reference the approved design, contain actual app screenshots and a named reviewer.",
                  "A real-device check on Xiaomi Pad 5 remains necessary before final release.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path("smoke-evidence"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-release", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if matrix.get("schema_version") != 1:
        raise AuditError("Unsupported acceptance schema")
    items, release = audit(matrix, args.evidence_dir)
    output = markdown(items, release)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output)
    return 0 if release or not args.require_release else 2


if __name__ == "__main__":
    raise SystemExit(main())
