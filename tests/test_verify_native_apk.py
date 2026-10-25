"""Packaging acceptance tests without an Android SDK or native build."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_native_apk import NativeApkError, verify_native_apk
from native_engine_artifact import MIN_NATIVE_BYTES


class VerifyNativeApkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.engine = self.root / "engine"
        self.lib = self.engine / "android" / "jniLibs" / "arm64-v8a" / "liblo-native-code.so"
        self.lib.parent.mkdir(parents=True)
        elf = bytearray(64)
        elf[:4] = b"\x7fELF"
        elf[4:7] = b"\x02\x01\x01"
        elf[16:20] = struct.pack("<HH", 3, 183)
        self.lib.write_bytes(bytes(elf) + b"\0" * MIN_NATIVE_BYTES)
        self.apk = self.root / "aqua.apk"

    def package(self, *, lib=None, dex=b"dex\n035\0", abi="arm64-v8a", duplicate=False):
        if lib is None:
            lib = self.lib.read_bytes()
        with zipfile.ZipFile(self.apk, "w", compression=zipfile.ZIP_STORED) as archive:
            if dex is not None:
                archive.writestr("classes.dex", dex)
            archive.writestr(f"lib/{abi}/liblo-native-code.so", lib)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(f"lib/{abi}/liblo-native-code.so", lib)

    def test_valid_package_matches_exact_engine_bytes(self):
        self.package()
        proof = verify_native_apk(self.apk, self.engine, "arm64-v8a")
        self.assertEqual(proof["native_sha256"], hashlib.sha256(self.lib.read_bytes()).hexdigest())
        self.assertEqual(proof["apk_sha256"], hashlib.sha256(self.apk.read_bytes()).hexdigest())

    def test_wrong_library_contents_are_not_certified(self):
        corrupt = bytearray(self.lib.read_bytes())
        corrupt[-1] = 1
        self.package(lib=corrupt)
        with self.assertRaisesRegex(NativeApkError, "SHA-256 differs"):
            verify_native_apk(self.apk, self.engine, "arm64-v8a")

    def test_wrong_library_size_is_not_certified(self):
        self.package(lib=self.lib.read_bytes()[:-1])
        with self.assertRaisesRegex(NativeApkError, "size differs"):
            verify_native_apk(self.apk, self.engine, "arm64-v8a")

    def test_wrong_abi_cannot_pass_from_unrelated_shared_library(self):
        self.package(abi="x86_64")
        with self.assertRaisesRegex(NativeApkError, "exactly one"):
            verify_native_apk(self.apk, self.engine, "arm64-v8a")

    def test_empty_or_missing_dex_is_rejected(self):
        for dex in (None, b""):
            with self.subTest(dex=dex):
                self.package(dex=dex)
                with self.assertRaisesRegex(NativeApkError, "classes.dex"):
                    verify_native_apk(self.apk, self.engine, "arm64-v8a")

    def test_duplicate_library_member_is_rejected(self):
        self.package(duplicate=True)
        with self.assertRaisesRegex(NativeApkError, "exactly one"):
            verify_native_apk(self.apk, self.engine, "arm64-v8a")

    def test_truncated_apk_is_rejected(self):
        self.apk.write_bytes(b"not a zip")
        with self.assertRaisesRegex(NativeApkError, "ZIP is invalid"):
            verify_native_apk(self.apk, self.engine, "arm64-v8a")


if __name__ == "__main__":
    unittest.main()
