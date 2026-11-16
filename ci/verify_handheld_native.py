"""Check the exact ARM64 ABI used by the upstream -14 cursor bridge."""
import argparse
import json
import re
import subprocess
from pathlib import Path

SYMBOLS = (
    '_ZN6MWBase11Environment5sThisE',
    '_ZN5MWGui13WindowManager16setCursorVisibleEb',
    '_ZNK5MWGui13WindowManager9isGuiModeEv',
)


def verify_layout(header: str) -> None:
    match = re.search(r'class Environment\s*\{(.*?)\n\s*public:', header, re.S)
    if not match:
        raise ValueError('Environment class layout changed')
    declarations = match.group(1)
    declarations = re.sub(r'//[^\n]*|/\*.*?\*/', '', declarations, flags=re.S)
    expected = ['mWorld', 'mWorldModel', 'mWorldScene', 'mESMStore',
                'mSoundManager', 'mScriptManager', 'mWindowManager']
    members = []
    for declaration in declarations.split(';'):
        declaration = declaration.strip()
        if not declaration or declaration.startswith('static '):
            continue
        field = re.fullmatch(r'[\w:]+\s*\*\s*(\w+)\s*=\s*nullptr', declaration)
        if not field:
            break
        members.append(field.group(1))
    if members[:7] != expected:
        raise ValueError('Window-manager pointer is no longer at ARM64 offset 0x30')


def verify_symbols(output: str) -> None:
    lines = output.splitlines()
    for symbol in SYMBOLS:
        if not any(line.split()[-1:] == [symbol] and ' UND ' not in line
                   and (' GLOBAL ' in line or ' WEAK ' in line) for line in lines):
            raise ValueError(f'Handheld cursor symbol is not exported: {symbol}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--readelf', required=True)
    args = parser.parse_args()
    verify_layout((args.source / 'apps/openmw/mwbase/environment.hpp').read_text(encoding='utf-8'))
    header = subprocess.check_output([args.readelf, '-h', str(args.library)], text=True)
    if 'ELF64' not in header or 'AArch64' not in header:
        raise ValueError('Cursor ABI requires an ARM64 engine')
    symbols = subprocess.check_output([args.readelf, '--dyn-syms', '--wide', str(args.library)], text=True)
    verify_symbols(symbols)
    print(json.dumps({'status': 'PASS', 'architecture': 'AArch64',
                      'window_manager_offset': '0x30', 'exported_symbols': SYMBOLS,
                      'on_device_cursor_tested': False}, indent=2))


if __name__ == '__main__':
    main()
