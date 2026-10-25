"""Native Collabora cache and ELF contract tests; no Android SDK required."""
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("native_engine_artifact", ROOT / "scripts" / "native_engine_artifact.py")
NATIVE = module_from_spec(SPEC)
SPEC.loader.exec_module(NATIVE)


class NativeEngineArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = Path(self.tmp.name) / "engine"
        self.engine.mkdir()
        self.lib = NATIVE.artifact_path(self.engine, "arm64-v8a")
        self.lib.parent.mkdir(parents=True)
        self.done = self.engine / "workdir" / "CustomTarget" / "android" / "source" / "done"
        self.stamp = self.engine / "workdir" / "CustomTarget" / "android" / "loandroid3"

    def write_elf(self, machine=183, elf_class=2, e_type=3):
        header = bytearray(64)
        header[:4] = b"\x7fELF"
        header[4] = elf_class
        header[5] = 1
        header[6] = 1
        header[16:20] = struct.pack("<HH", e_type, machine)
        self.lib.write_bytes(bytes(header) + b"\0" * 96)

    def write_markers(self):
        self.done.parent.mkdir(parents=True, exist_ok=True)
        self.done.write_text("done")
        self.stamp.write_text("stamp")

    def test_valid_arm64_elf_digest_and_metadata(self):
        self.write_elf()
        evidence = NATIVE.inspect_artifact(self.engine, "arm64-v8a", minimum_bytes=64)
        self.assertEqual(evidence["abi"], "arm64-v8a")
        self.assertEqual(evidence["size"], 160)
        self.assertEqual(evidence["sha256"], hashlib.sha256(self.lib.read_bytes()).hexdigest())

    def test_rejects_wrong_architecture_and_wrong_elf_type(self):
        for machine, elf_class, e_type in [(62, 2, 3), (183, 1, 3), (183, 2, 2)]:
            with self.subTest(machine=machine, elf_class=elf_class, e_type=e_type):
                self.write_elf(machine, elf_class, e_type)
                with self.assertRaises(NATIVE.NativeArtifactError):
                    NATIVE.inspect_artifact(self.engine, "arm64-v8a", minimum_bytes=64)

    def test_rejects_non_elf_and_tiny_file(self):
        self.lib.write_bytes(b"not-an-ELF")
        with self.assertRaises(NATIVE.NativeArtifactError):
            NATIVE.inspect_artifact(self.engine, "arm64-v8a", minimum_bytes=1)
        self.write_elf()
        with self.assertRaisesRegex(NATIVE.NativeArtifactError, "too small"):
            NATIVE.inspect_artifact(self.engine, "arm64-v8a")

    def test_missing_artifact_invalidates_both_gbuild_stamps(self):
        self.write_markers()
        self.assertTrue(NATIVE.prepare_engine(self.engine, "arm64-v8a"))
        self.assertFalse(self.done.exists())
        self.assertFalse(self.stamp.exists())
        self.assertFalse(self.lib.exists())

    def test_valid_artifact_keeps_gbuild_stamps(self):
        self.write_markers()
        self.write_elf()
        self.lib.write_bytes(self.lib.read_bytes() + b"\0" * NATIVE.MIN_NATIVE_BYTES)
        self.assertFalse(NATIVE.prepare_engine(self.engine, "arm64-v8a"))
        self.assertTrue(self.done.exists())
        self.assertTrue(self.stamp.exists())
        self.assertTrue(self.lib.exists())

    def test_invalid_artifact_deleted_and_rebuild_requested(self):
        self.write_markers()
        self.write_elf(machine=62)
        self.lib.write_bytes(self.lib.read_bytes() + b"\0" * NATIVE.MIN_NATIVE_BYTES)
        self.assertTrue(NATIVE.prepare_engine(self.engine, "arm64-v8a"))
        self.assertFalse(self.lib.exists())
        self.assertFalse(self.done.exists())
        self.assertFalse(self.stamp.exists())

    def test_symlink_cannot_be_accepted_as_engine_output(self):
        outside = Path(self.tmp.name) / "external.so"
        outside.write_bytes(b"external")
        self.lib.symlink_to(outside)
        with self.assertRaisesRegex(NATIVE.NativeArtifactError, "symlinked"):
            NATIVE.inspect_artifact(self.engine, "arm64-v8a", minimum_bytes=1)
        self.assertTrue(NATIVE.prepare_engine(self.engine, "arm64-v8a"))
        self.assertTrue(outside.exists())
        self.assertFalse(self.lib.is_symlink())

    def test_cli_fails_before_gradle_for_missing_binary(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "native_engine_artifact.py"),
             "verify", "--engine-dir", str(self.engine), "--abi", "arm64-v8a"],
            text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing native library", result.stderr)


if __name__ == "__main__":
    unittest.main()
