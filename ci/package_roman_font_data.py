"""Build the font/data component paired with the separately compiled KR11 APK.
No ESP is generated or edited. The output must be new. Native APK compilation,
release signing and alignment checks belong to build-kr11-android.yml.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROMAN = range(0x2160, 0x2180)
FONT_NAMES = ('MysticCards.omwfont', 'DejaVuLGCSansMono.omwfont')

def digest(b): return sha256(b).hexdigest()

def ranges(raw):
    root=ET.fromstring(raw)
    return [tuple(map(int,e.attrib['range'].split())) for e in root.iter('Code')]

def covered(raw, code):
    return any(r[0]<=code<=r[-1] for r in ranges(raw))

def patch_font(raw):
    if all(covered(raw,n) for n in ROMAN):return raw
    assert not any(covered(raw,n) for n in ROMAN), 'partially covered Roman range requires review'
    text=raw.decode('utf-8-sig'); newline='\r\n' if '\r\n' in text else '\n'
    needle='            <Code range="12288 12317"/>'
    assert text.count(needle)==1
    result=text.replace(needle,'            <Code range="8544 8575"/>'+newline+needle).encode('utf8')
    assert all(covered(result,n) for n in ROMAN)
    assert set(ranges(result))-set(ranges(raw))=={(8544,8575)}
    # Confirm no character previously configured disappears.
    assert set(ranges(raw))<=set(ranges(result))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--base-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--platform',choices=('windows','android-data'),required=True)
    p.add_argument('--android-native',action='store_true')
    a=p.parse_args()
    raw=a.base.read_bytes(); assert digest(raw)==a.base_sha256.lower()
    assert a.output.resolve()!=a.base.resolve() and not a.output.exists()
    checksums=a.output.with_suffix(a.output.suffix+'.sha256')
    report=a.output.with_name(a.output.stem+'-verification.json')
    assert not checksums.exists() and not report.exists()
    z=zipfile.ZipFile(a.base); assert z.testzip() is None
    counts=Counter(z.namelist()); duplicates={k:n for k,n in counts.items() if n>1}
    for name in duplicates:
        versions=[z.read(info) for info in z.infolist() if info.filename==name]
        assert len(set(versions))==1, 'conflicting duplicate entries'
    entries={name:z.read(name) for name in z.namelist()}
    if a.platform=='windows':
        names=['payload/resources/vfs/fonts/'+n for n in FONT_NAMES]
        readme='README-KOREAN.txt'
    else:
        names=['Morrowind_Korean_ReTranslation/Fonts/MysticCards.omwfont']
        readme='README-ANDROID-KO.txt'
    revised=dict(entries)
    for name in names:
        assert name in entries
        revised[name]=patch_font(entries[name]); assert revised[name]!=entries[name]
    if a.platform=='windows':
        notice=('OpenMW 0.51.0 Korean Support KR11\n\n'
          'KR10의 엔진·번역·토픽 복구 기능을 유지한 폰트 리소스 수정판입니다.\n'
          'Ⅰ–Ⅻ 등 U+2160–U+217F 로마 숫자가 밑줄(_)로 표시되던 문제를 수정합니다.\n'
          '실행 파일 재빌드나 ESP 변경 없이 .omwfont의 허용 문자 범위만 추가했습니다.\n'
          'Windows KR10 사용자는 폰트 두 파일만 갱신할 수도 있습니다.\n'
          '설치: 공식 OpenMW 0.51.0 Windows 설치본 위에서 Install-Korean.bat 실행.\n'
          'Rebirth의 대화·스크립트·Daedric 번역 수정은 이 본편 패키지에 포함되지 않습니다.\n'
          '기존 릴리스와 세이브를 보존하세요.\n\n')
        previous=entries[readme].decode('utf-8-sig')
        revised[readme]=(notice+'--- KR10 설치 및 호환 안내 (계승) ---\n'+previous).encode('utf8')
    else:
        notice=('OpenMW Android/ChromeOS 한국어 KR11 데이터\n\n'
          'KR11은 Windows KR10의 토픽 복구 패치까지 이식한 새 네이티브 APK와 함께 제공합니다.\n'
          '새 APK 식별자는 com.ast.openmw.korean, versionCode는 5113입니다.\n'
          '기존 KR8/처음 KR9 앱을 삭제하거나 덮어쓰지 않으며 저장 공간은 별도입니다.\n'
          '새 앱에서 게임 경로를 설정하고 중요 세이브는 백업 후 수동으로 복사하세요.\n'
          '이 데이터 ZIP은 U+2160–U+217F 로마 숫자 폰트 범위를 추가합니다.\n'
          '기존 Android ESP/CEL/TOP/MRK/JRN·TTF·자막은 바이트 동일합니다.\n'
          'APK와 데이터 ZIP은 별개이므로 새 설치에는 둘 다 적용해야 합니다.\n\n')
        revised[readme]=(notice+'--- 기존 데이터 설치 안내 ---\n'+entries[readme].decode('utf-8-sig')).encode('utf8')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as dest:
        for name,data in revised.items():
            info=zipfile.ZipInfo(name,date_time=(2026,10,28,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=z.getinfo(name).external_attr
            dest.writestr(info,data)
    with zipfile.ZipFile(a.output) as check:
        assert check.testzip() is None and len(check.namelist())==len(set(check.namelist()))
        changed=[n for n in entries if check.read(n)!=entries[n]]
        assert set(changed)==set(names+[readme])
        for n in check.namelist():
            if n.lower().endswith(('.esp','.cel','.top','.mrk','.jrn','.srt','.ttf','.exe')):
                assert check.read(n)==entries[n], n
        for n in names: assert all(covered(check.read(n),code) for code in ROMAN)
    output_sha=digest(a.output.read_bytes())
    checksums.write_text(output_sha+'  '+a.output.name+'\n',encoding='utf8')
    result={'version':'KR11','platform':a.platform,'base_sha256':digest(raw),'output_sha256':output_sha,
      'only_changed_members':changed,'preserved_unique_members':len(entries)-len(changed),
      'identical_duplicate_entries_normalized':duplicates,'runtime_rebuilt_by_font_packager':False,'native_APK_is_separate':a.android_native,'ESP_modified':False,
      'roman_range':[8544,8575],'device_QA':False,'full_game_QA':False}
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert digest(a.base.read_bytes())==a.base_sha256.lower()
    print(json.dumps(result,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
