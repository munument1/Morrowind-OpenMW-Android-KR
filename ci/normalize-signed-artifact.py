"""Copy exactly one of each required signed-build member into a flat directory.

upload-artifact preserves the common ancestor when release/native paths mix.
Accept flat and nested downloads, but reject ambiguous or incomplete artifacts
before copying any files. Never re-sign or modify the recovered bytes.
"""
import argparse
from pathlib import Path
import shutil


def normalize(source, destination, apk):
    if Path(apk).name != apk or not apk.endswith('.apk'):
        raise ValueError('Expected an APK basename')
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('Source and destination must be separate directories')
    names = (apk, apk + '.sha256', 'kr124-certificate.txt',
             'kr124-badging.txt', '16k-verification.txt',
             'korean-origin.txt', 'libopenmw.so.sha256')
    members = []
    for name in names:
        found = [p for p in source.rglob(name) if p.is_file() and p.name == name]
        if len(found) != 1 or found[0].stat().st_size == 0:
            raise ValueError(f'Expected one nonempty {name}; found {len(found)}')
        if (destination / name).exists():
            raise ValueError(f'Refusing to overwrite {destination / name}')
        members.append(found[0])
    destination.mkdir(parents=True, exist_ok=True)
    for member in members:
        shutil.copyfile(member, destination / member.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--apk', required=True)
    args = parser.parse_args()
    normalize(args.source, args.destination, args.apk)
