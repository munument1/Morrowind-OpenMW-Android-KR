import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('normalizer', Path(__file__).with_name('normalize-signed-artifact.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactLayoutTests(unittest.TestCase):
    def populate(self, root, nested):
        names = ('test.apk', 'test.apk.sha256', 'kr124-certificate.txt',
                 'kr124-badging.txt', '16k-verification.txt',
                 'korean-origin.txt', 'libopenmw.so.sha256')
        for name in names:
            directory = root / ('native-artifacts' if name in names[-2:] else 'release-artifacts') if nested else root
            directory.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(name.encode() + b'\x00\xff')
        return names

    def test_flat_and_mixed_paths_preserve_bytes(self):
        for nested in (False, True):
            with self.subTest(nested=nested), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                names = self.populate(root / 'input', nested)
                module.normalize(root / 'input', root / 'output', 'test.apk')
                for name in names:
                    self.assertEqual((root / 'output' / name).read_bytes(), name.encode() + b'\x00\xff')

    def test_missing_and_duplicate_members_fail_before_copy(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.populate(root / 'input', True)
                if duplicate:
                    (root / 'input' / 'test.apk').write_bytes(b'duplicate')
                else:
                    (root / 'input' / 'native-artifacts' / 'libopenmw.so.sha256').unlink()
                with self.assertRaises(ValueError):
                    module.normalize(root / 'input', root / 'output', 'test.apk')
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
