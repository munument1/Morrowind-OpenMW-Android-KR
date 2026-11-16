"""Build an Android KR14 data candidate from approved Android/Windows archives.

Preserves Android fonts, video, sidecars and metadata. Never uploads anywhere.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

from patch_kr12_quest_entry_topics import chunks, fields

ANDROID_SHA = 'b6ac2eccba6ca333774e47ccd1a2bdbe98ac7f838911b4776bd95ae2c2f757bc'
WINDOWS_SHA = '805fd9dc6ffdb61639378893690d6c8eeda2b48e6b0f331c23828f3e21929115'
OLD_ESP = '9f94b1c96b10a491cec00d4931123ef1e0f52f52c6095da6b9b380eb9a617b1c'
NEW_ESP = '571683041b5b43f3a7d5c370f01dd6d8976de12c634c32c9ec00692a3d9ec682'
MEMBER = 'Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp'
ASSET = 'OpenMW-Android-0.51.0-14-Korean-Data-KR14.zip'
SAY = re.compile(rb'(?i)(\bSay\s+"[^"\r\n]+"\s*,?\s*)"[^"\r\n]*"')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def verify_scripts(before, after):
    left, right = list(chunks(before, 16)), list(chunks(after, 16))
    if len(left) != len(right):
        raise ValueError('Record count changed')
    changed = {}
    for (tag, header, body), (tag2, header2, body2) in zip(left, right):
        if tag != tag2 or header[8:] != header2[8:]:
            raise ValueError('Record order/flags changed')
        if body == body2:
            continue
        if tag != b'SCPT':
            raise ValueError('Only voice script subtitles may change')
        a, b = fields(body), fields(body2)
        name = dict(a)[b'SCHD'][:32].rstrip(b'\0').decode('ascii')
        if len(a) != len(b) or name not in ('VampireMolag', 'playScript') or name in changed:
            raise ValueError('Unexpected script')
        count = 0
        for (key, old), (key2, new) in zip(a, b):
            if key != key2:
                raise ValueError('Script field order changed')
            if old == new:
                continue
            if key != b'SCTX' or SAY.sub(rb'\1"<subtitle>"', old) != SAY.sub(rb'\1"<subtitle>"', new):
                raise ValueError('Script logic/audio/bytecode changed')
            old_text, new_text = list(SAY.finditer(old)), list(SAY.finditer(new))
            count += sum(x.group() != y.group() for x, y in zip(old_text, new_text))
        changed[name] = count
    if set(changed) != {'VampireMolag', 'playScript'} or sum(changed.values()) != 11:
        raise ValueError('Expected exactly two scripts and 11 subtitles')
    return {'records_checked': len(left), 'changed_subtitles': changed,
            'other_fields_ids_conditions_and_bytecode_unchanged': True}


def read_archive(path, digest):
    if sha(path.read_bytes()) != digest:
        raise ValueError('Unapproved source archive: ' + path.name)
    with ZipFile(path) as z:
        if z.testzip() or len(z.namelist()) != len(set(n.casefold() for n in z.namelist())):
            raise ValueError('ZIP CRC/duplicate paths')
        return [(info, z.read(info)) for info in z.infolist()]


def build(android, windows, output):
    original = read_archive(android, ANDROID_SHA)
    approved = dict((info.filename, data) for info, data in read_archive(windows, WINDOWS_SHA))
    old = dict((info.filename, data) for info, data in original)[MEMBER]
    new = approved['payload/mods/' + MEMBER]
    if sha(old) != OLD_ESP or sha(new) != NEW_ESP:
        raise ValueError('Unapproved core ESP')
    verification = verify_scripts(old, new)
    output.mkdir(parents=True, exist_ok=True)
    target = output / ASSET
    note = ('OpenMW Android KR14 / 이슈 #71 데이터 후보\n\n'
            '본편 VampireMolag/playScript의 Say 자막 11개 보완. 토픽 ID·퀘스트 조건·분기는 유지합니다.\n'
            'Android KR14 서명 APK(0.51.0-14-KR14, versionCode 5119, 패치 0001–0019)와 함께 검증한 후보입니다.\n'
            'KR12.4 APK에는 새 토픽 표시/일지 엔진 수정이 없어 데이터만으로 동일한 동작을 제공하지 않습니다.\n'
            '기존 데이터·저장을 백업하고 Morrowind_Korean_ReTranslation 폴더를 갱신하십시오.\n'
            '지역 모드의 DSP/번역 플러그인은 해당 TR·TD·Cyr·Sky·Rebirth·PFP 최신 한글 ZIP을 사용합니다.\n'
            '일반 Cyr/Sky와 Rebirth 전용본을 동시에 활성화하지 마십시오.\n'
            '이 ZIP에는 APK·원본 게임 마스터·모드 아트·세이브가 없습니다. 기존 KR13 안내는 이력으로 보존합니다.\n'
            'Android 실기기 설치·전체 퀘스트 검증은 미완료입니다. Nexus에는 업로드하지 않습니다.\n').encode('utf-8')
    with target.open('xb') as handle, ZipFile(handle, 'w', ZIP_DEFLATED, compresslevel=9) as z:
        for info, data in original:
            z.writestr(info, new if info.filename == MEMBER else data)
        z.writestr('KR14-ISSUE71-UPGRADE.txt', note)
    expected = {info.filename: sha(new if info.filename == MEMBER else data) for info, data in original}
    expected['KR14-ISSUE71-UPGRADE.txt'] = sha(note)
    with ZipFile(target) as z:
        if z.testzip() or {n: sha(z.read(n)) for n in z.namelist()} != expected:
            raise ValueError('Output payload mismatch')
        for info, _ in original:
            actual = z.getinfo(info.filename)
            if any(getattr(info, k) != getattr(actual, k) for k in ('date_time', 'external_attr', 'comment', 'extra')):
                raise ValueError('Android member metadata changed')
    report = {'status': 'ANDROID_KR14_ISSUE71_DATA_CANDIDATE_PASS', 'asset': ASSET,
              'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size,
              'source_android_sha256': ANDROID_SHA, 'source_windows_sha256': WINDOWS_SHA,
              'esp_sha256': NEW_ESP, 'payload': expected, **verification,
              'android_other_members_and_metadata_preserved': True, 'apk_rebuilt': False,
              'nexus_upload': False, 'physical_device_tested': False}
    (output / (ASSET + '.sha256')).write_text(report['sha256'] + '  ' + ASSET + '\n', encoding='ascii')
    (output / 'KR14-ISSUE71-DATA-QA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--android', type=Path, required=True)
    parser.add_argument('--windows', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.android, args.windows, args.output), ensure_ascii=False, indent=2))
