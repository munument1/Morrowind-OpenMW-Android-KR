"""Fail-closed CEL-only fix for issue #13, packaged from an exact KR7 ZIP."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

KEY = 'Vivec, Aradraen: Fletcher'
VALUE = '비벡, 아라드라엔: 화살 제작자'
LINE = f'{KEY}\t{VALUE}\n'.encode('utf-8')
ORIGINAL_CEL_SHA256 = '62f9676b6bcb78ae8ad7219d9ddad5664bd284a254dce537e1867cce799876e0'
MEMBERS = {
    'android': 'Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.cel',
    'windows': 'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.cel',
}

def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def patch_cel(raw: bytes) -> bytes:
    if sha256(raw) != ORIGINAL_CEL_SHA256:
        raise ValueError('Refusing unreviewed CEL version: SHA-256 mismatch')
    if not raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('Missing UTF-8 BOM')
    lines = raw.decode('utf-8-sig').splitlines(keepends=True)
    if len(lines) != 1439 or any(not s.endswith('\n') or s.count('\t') != 1 for s in lines):
        raise ValueError('Unexpected CEL structure')
    keys = [s.split('\t', 1)[0] for s in lines]
    if KEY in keys:
        raise ValueError('Duplicate or already translated CELL key')
    try:
        index = keys.index('Vivec, Arena')
    except ValueError as exc:
        raise ValueError('Missing insertion anchor') from exc
    if keys[index - 1] != 'Vivec, Andilu Drothan: Alchemist':
        raise ValueError('Unexpected CEL ordering')
    lines.insert(index, LINE.decode('utf-8'))
    patched = b'\xef\xbb\xbf' + ''.join(lines).encode('utf-8')
    if patched.replace(LINE, b'', 1) != raw:
        raise ValueError('Modification outside the reviewed CEL line')
    return patched

def build(source: Path, output: Path, variant: str, expected_source_sha: str) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError('Output must be a new ZIP')
    if sha256(source.read_bytes()) != expected_source_sha.lower():
        raise ValueError('Source KR7 release ZIP SHA-256 mismatch')
    member = MEMBERS[variant]
    with ZipFile(source) as source_zip:
        names = source_zip.namelist()
        if names.count(member) != 1 or len(names) != len(set(names)):
            raise ValueError('Missing CEL or duplicate ZIP paths')
        if source_zip.testzip() is not None:
            raise ValueError('Corrupted input ZIP')
        original_cel = source_zip.read(member)
        patched_cel = patch_cel(original_cel)
        with ZipFile(output, 'w') as destination_zip:
            destination_zip.comment = source_zip.comment
            for info in source_zip.infolist():
                destination_zip.writestr(info, patched_cel if info.filename == member else source_zip.read(info.filename))
    with ZipFile(source) as source_zip, ZipFile(output) as destination_zip:
        if destination_zip.testzip() is not None or source_zip.namelist() != destination_zip.namelist():
            raise ValueError('ZIP integrity/parity failure')
        diffs = [name for name in source_zip.namelist() if source_zip.read(name) != destination_zip.read(name)]
        if diffs != [member]:
            raise ValueError(f'Unexpected modified archive entries: {diffs!r}')
    digest = sha256(output.read_bytes())
    output.with_name(output.name + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
    return {
        'variant': variant, 'source_zip_sha256': expected_source_sha.lower(),
        'output_zip_sha256': digest, 'original_cel_sha256': sha256(original_cel),
        'patched_cel_sha256': sha256(patched_cel), 'modified_entries': diffs,
        'original_lines': 1439, 'patched_lines': 1440,
        'key': KEY, 'value': VALUE, 'result': 'PASS',
    }

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--variant', choices=('android', 'windows'), required=True)
    ap.add_argument('--expected-source-sha256', required=True)
    opts = ap.parse_args()
    print(json.dumps(build(opts.source, opts.output, opts.variant, opts.expected_source_sha256), ensure_ascii=False, indent=2))
