# Nexus Mods #60496 — KR9 갱신 문안

Nexus Mods 등록 페이지: https://www.nexusmods.com/morrowind/mods/60496

**현재 이 문서는 업로드/등록 준비 문안입니다. Nexus Mods 사이트에 실제로 수정·게시된 것은 아닙니다.** 기존 Nexus Mods 페이지는 검색 시 버전 `0.51-kr4`로 표시되었습니다.

## 새 파일 (Windows)

- 표시 이름: `OpenMW 0.51.0 Korean Support KR9 - Windows`
- 파일명: `Morrowind-Korean-OpenMW-0.51.0-KR9-Full.zip`
- 버전: `0.51.0-KR9`
- 원본 파일과 체크섬: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr9
- 모드 페이지에 최신 Windows 파일로 등록하고, 이전 KR4 파일은 필요 시 Old files로 유지합니다. 자동 교체 전 사용자의 기존 설정 백업을 권장합니다.

## Nexus 모드 소개/변경 내역 (붙여넣기)

**OpenMW 0.51.0 Korean Support KR9**

모로윈드 본편, Tribunal, Bloodmoon의 한국어 번역과 OpenMW 0.51.0용 엔진 보정을 제공하는 비공식 한국어 지원판입니다.

KR9에서는 NPC 대화, 인사말, 설득 대사 및 저널에서 한국어 단어의 일부가 다른 토픽으로 잘못 인식되어 **원치 않는 파란 하이퍼링크가 생기는 문제**를 수정했습니다. 명시적 토픽 링크와 정상적인 조사·복합 토픽은 보존하도록 처리했습니다.

기존 KR8의 번역 ESP·CEL·TOP·MRK·폰트·영상 자막은 그대로 유지했습니다. KR8과 비교해 Windows 패키지에서 교체된 내용은 `payload/openmw.exe` 엔진 파일뿐입니다. 특히 KR8에 반영된 Aradraen CELL 이름 보정도 유지됩니다.

Windows/Ubuntu 컴파일·테스트, 실제 OpenMW 파서 검증, 번역 데이터 전체 감사 및 배포 ZIP 검사에 통과했습니다. 별도 인게임 실행 검증은 진행하지 않았습니다.

**Windows KR9 다운로드**
https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr9

**Android/ChromeOS**
기존 KR8 앱을 삭제하지 않고 나란히 설치 가능한 Android KR9 별도 앱이 제공됩니다.
https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr9-standalone

Android KR9는 기존 앱과 저장 공간을 공유하지 않습니다. 원본 앱을 삭제하지 말고 세이브를 먼저 백업하세요. 이 초기 별도 설치판은 일회성 Debug 서명으로 만들어져 동일 패키지에 대한 추후 덮어쓰기 업데이트를 보장하지 않습니다. **영구 서명용 후속 APK는 공개 검증 및 릴리스 완료 후 이 링크를 갱신해야 합니다.**

원본 Morrowind 게임 데이터와 Bethesda 저작권 자료는 포함하지 않습니다.

## Change log

- **KR9**: Korean dialogue and journal implicit hyperlink boundary fix; unchanged KR8 translation resources; verified Windows release archive.
- **KR8**: Official Area Effect Arrows / Aradraen interior CELL translation correction.
- **Older versions**: See GitHub Releases for details.

## Nexus 실제 게시 작업

1. Nexus Mods 계정으로 자신의 모드 페이지 `60496`를 관리자로 엽니다.
2. Files에 공식 Windows KR9 ZIP을 새 파일로 등록하고 버전을 `0.51.0-KR9`로 지정합니다.
3. Description/Changelog를 위 문안으로 갱신합니다.
4. 실제 게시 후, 페이지의 공개 파일명과 파일 버전·링크를 다시 확인합니다.

Nexus Mods에 직접 로그인해 수정·파일 업로드를 수행하는 연결은 현재 없습니다. GitHub에서 README나 모드 파일을 수정하는 것만으로 Nexus Mods 등록 파일은 자동으로 바뀌지 않습니다.
