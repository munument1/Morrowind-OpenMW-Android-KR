# Android OpenMW 0.51.0-14 Handheld Mode — KR14 signed candidate

**상태: ARM64 빌드·영구 서명·정적/네이티브 검사 완료, 실기기 설치·공개 배포 전.** 기존 공개 APK/데이터 릴리스와 CURRENT_RELEASE.json은 바꾸지 않았다.

## 구현 범위

현재 한국어 main에 기존 PowerVR 0.51.0-13 수정과 Handheld 0.51.0-14 기능을 통합했다. L1 원형 메뉴, R1 일지, Select 휴식, L3 커서 전환, 게임패드 조작과 글꼴 설정을 포함한다. 원형 메뉴의 한국어 및 영어 fallback은 24개 키로 일치하며, 새 설정 문구도 기존 언어 리소스 검사를 통과했다.

앱 ID `com.ast.openmw.korean`과 기존 영구 인증서를 유지하고 versionCode를 공개 KR12.4의 5117보다 높은 **5119**, versionName을 **0.51.0-14-KR14**로 설정했다. NDK는 27.3.13750724이며, 새 libhandheld.so에도 16 KiB ELF 정렬을 적용했다.

## 실제 빌드와 검증

- [네이티브 빌드 43789314649](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/43789314649)는 OpenMW 0.51.0 고정 커밋 및 한국어 패치 0001–0019를 컴파일했다. 실제 ARM64 libopenmw의 커서 함수 3개, Environment의 window-manager 포인터 오프셋 0x30, 16 KiB LOAD 정렬을 확인했다. 실제 패치 적용 소스의 표시명/자막·한국어 어미·기존 영어 토픽/별칭 회귀 검사도 통과했다.
- 이 실행은 APK까지 생성했지만 마지막 검사에서 AGP가 생성한 libhandheld.so를 소스 jniLibs 폴더에서 찾는 잘못된 경로 때문에 종료됐다. APK 내부 파일과 ELF 보고서에는 해당 라이브러리가 있었다. 검사를 APK 내부 경로로 바로잡았다.
- [패키징·서명 43792923660](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/43792923660)는 원래 네이티브 빌드의 성공 단계·artifact digest 및 소스 불변을 검사한 뒤 그 네이티브 파일을 재사용했다. Java/JNI APK를 다시 빌드하고 기존 영구 키로 서명했다. app ID/버전, non-debuggable, zipalign -P16, apksigner 검사와 네이티브 바이트 보존을 통과했다.
- 내려받은 APK의 체크섬·ZIP CRC, JDK jarsigner의 V1 서명, PKCS7 인증서 지문을 독립 검사했다. 9개 ARM64 .so의 모든 LOAD 정렬은 최소 16384였다. en/ko 원형 메뉴 24개 키와 원본 문구도 줄바꿈 정규화 후 일치했다.
- 앞서 별칭 테스트에 잘못 넣은 대소문자 키는 실제 배포 TOP의 소문자 키 규칙에 맞게 수정했다. 원래 테스트 실패 및 수정 후 통과를 로컬의 실제 C++ 모듈로 재현했다. 엔진의 토픽 처리 코드를 우회하거나 변경한 것이 아니다.

APK: `OpenMW-Android-0.51.0-14-Korean-KR14-Permanent-16K.apk`

SHA256: `b66c684c0cf5bf92bd61e4d0a73749f112830ccb9797c126e2476028b629de5f`

인증서 SHA256: `ebf75015d1b61b14ffa2a3539d8981434c30272219eb6b0ae0c3de16bb2228f2`

상세 수치와 소스/CI 핀은 [KR14-BUILD-QA-20261116.json](KR14-BUILD-QA-20261116.json)을 따른다. 별도 데이터는 기존 [검증된 KR13 전체 데이터 ZIP](https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr13-data-only)을 사용하며 새 데이터라고 이름만 바꾸지 않았다. 원본 게임 데이터는 포함하지 않는다.

## 남은 실기기 검증

실제 Android 기기에서 설치/기존 APK 업그레이드, L1/R1/Select/L3 및 마우스·터치 fallback, 저장/불러오기, 글꼴, PowerVR 렌더링과 Handheld OFF 동작을 확인하지 않았다. 같은 ID·서명과 높은 versionCode는 바이너리에서 확인했지만 실제 설치 성공을 주장하지 않는다. 이 후보는 공개 배포하거나 이슈를 닫지 않았다.
