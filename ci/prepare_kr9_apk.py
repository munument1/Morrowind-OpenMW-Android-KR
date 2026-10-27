"""Prepare Android KR9 APK payload from the authentic published KR8 APK.

This produces an UNSIGNED intermediate ZIP. It is NOT an installable release APK
until 16-KiB aligned and signed with the original Android signing key. Reject
changes to data/resources; only lib/arm64-v8a/libopenmw.so can differ.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

LIBRARY = 'lib/arm64-v8a/libopenmw.so'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(source: Path, binary: Path, output: Path, expected_sha: str):
    if output.exists() or output.resolve() in (source.resolve(), binary.resolve()):
        raise ValueError('Destination must be a new file')
    if digest(source.read_bytes()) != expected_sha.lower():
        raise ValueError('Source APK checksum does not match the KR8 release')
    new_lib = binary.read_bytes()
    # Android KR8 ships 64-bit ARM. Reject accidental x86, 32-bit or
    # non-shared-object binaries even when they start with the ELF magic.
    def is_arm64_shared_object(payload: bytes) -> bool:
        return (len(payload) >= 64 and payload[:6] == b'\x7fELF\x02\x01'
                and int.from_bytes(payload[16:18], 'little') == 3  # ET_DYN
                and int.from_bytes(payload[18:20], 'little') == 183)  # EM_AARCH64

    if len(new_lib) < 1024 * 1024 or not is_arm64_shared_object(new_lib):
        raise ValueError('Expected a substantial ARM64 ELF shared object')
    with ZipFile(source) as original:
        names = original.namelist()
        if names.count(LIBRARY) != 1 or len(names) != len(set(names)):
            raise ValueError('Missing or duplicate arm64 library')
        if original.testzip() is not None:
            raise ValueError('Corrupt source APK')
        old_lib = original.read(LIBRARY)
        if not is_arm64_shared_object(old_lib):
            raise ValueError('Published KR8 APK native library is not ARM64 ET_DYN')
        if old_lib == new_lib:
            raise ValueError('Unchanged libopenmw.so is not a KR9 runtime upgrade')
        with ZipFile(output, 'w') as prepared:
            prepared.comment = original.comment
            for entry in original.infolist():
                prepared.writestr(entry, new_lib if entry.filename == LIBRARY
                                  else original.read(entry))
    with ZipFile(source) as original, ZipFile(output) as prepared:
        if original.namelist() != prepared.namelist():
            raise ValueError('Unexpected APK member list or ordering')
        if prepared.testzip() is not None:
            raise ValueError('Corrupt prepared APK ZIP')
        modified = [n for n in original.namelist()
                    if original.read(n) != prepared.read(n)]
        if modified != [LIBRARY]:
            raise ValueError(f'Unexpected APK modifications: {modified}')
    return {
        'base_release': 'android-korean-0.51.0-12-kr8',
        'base_apk_sha256': expected_sha.lower(),
        'old_library_sha256': digest(old_lib),
        'new_library_sha256': digest(new_lib),
        'changed_entries': modified,
        'unchanged_members': len(names) - 1,
        'unsigned_apk_sha256': digest(output.read_bytes()),
        'WARNING': 'UNSIGNED. Existing KR8 v2 signature invalid after rewriting. '
                   'Must align and sign with the original KR8 key to preserve upgrade '
                   'compatibility; otherwise an uninstall/reinstall is required.',
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--library', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--expected-source-sha256', required=True)
    args = ap.parse_args()
    report = prepare(args.source, args.library, args.output, args.expected_source_sha256)
    print(json.dumps(report, ensure_ascii=False, indent=2))
