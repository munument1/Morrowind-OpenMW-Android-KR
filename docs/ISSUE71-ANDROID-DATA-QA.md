# 이슈 #71 Android 수정 범위

사용자의 Android 제외 지시는 **Nexus 업로드만 제외**한다는 뜻이다. Android 수정·검증은 포함한다. 이번 작업은 Nexus 업로드 및 GitHub 정식 릴리스 발행을 하지 않는다.

이미 검증된 KR14 서명 APK 후보는 Windows #71의 최종 커밋 `ec69b1133c284cae65a1446174d869fafcd3251e`에서 패치 0018/0019를 가져와 목록·응답 제목·일지·음성 자막 정리를 포함한다. 이 엔진은 다시 수정하거나 이름만 바꿔 재빌드하지 않았다. 기존 네이티브 회귀 검사·서명·16KiB 정렬 검증은 [KR14 빌드 기록](KR14-BUILD-QA-20261116.json)을 따른다.

빠졌던 본편 자막 데이터는 새 Android KR14 데이터 후보에 반영했다. 기존 Android KR13 ZIP의 ESP만 검증된 Windows KR13.2 ESP로 교체하고 새 설치 안내를 추가했다. 기존 Android 폰트·영상 자막·TOP/MRK/CEL/JRN·로케일과 ZIP 멤버 메타데이터는 보존했다.

- 전체 48,146 레코드의 순서·플래그·필드를 대조했다. VampireMolag의 Say 3개와 playScript의 Say 8개만 변경됐다. 음성 ID·퀘스트 조건·다른 명령·컴파일 바이트코드는 같다.
- 조건·음성 ID·바이트코드 변경 및 잘린 파일을 거부하는 회귀 검사를 통과했다. 기존 Android KR14 소스 검사 7개도 통과했다.
- 새 ESP SHA256: `571683041b5b43f3a7d5c370f01dd6d8976de12c634c32c9ec00692a3d9ec682`.
- 로컬 데이터 ZIP SHA256: `98ba6e161a9b45107c3bb72b4a76d701e0ae1635704d7546423426a03eee7c2d`. 플랫폼별 압축 결과는 다를 수 있으며, CI는 고정 원본과 실제 멤버 SHA256·CRC·메타데이터를 다시 검증한다.
- 기존 서명 APK SHA256: `b66c684c0cf5bf92bd61e4d0a73749f112830ccb9797c126e2476028b629de5f`. 로컬에서 CRC·SHA256·libopenmw SHA256과 ARM64 라이브러리 9개의 LOAD 정렬(최소 16KiB)을 재확인했다.

Android KR14 APK(`com.ast.openmw.korean`, versionCode 5119, 0001–0019 패치)와 새 데이터 ZIP을 함께 사용한다. KR12.4 APK에는 #71의 엔진 수정이 없다. 지역 모드·PFP·Rebirth 번역 ZIP은 플랫폼 공통이며 이번에 검증한 새 DSP/플러그인을 사용할 수 있다. 일반 Cyr/Sky와 Rebirth 전용본은 동시에 활성화하지 않는다.

실제 Android 기기의 설치·업그레이드·렌더링·저장/불러오기·전체 퀘스트는 미검증이다. 기존 공개 릴리스와 CURRENT_RELEASE.json을 후보로 교체하지 않았다. Nexus에는 올리지 않았다.

[CI 43806850434](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/43806850434)이 성공했고, CI에서 생성한 후보 ZIP의 모든 멤버 SHA256은 로컬 후보와 같다. [확인 수치](ISSUE71-ANDROID-CI-QA.json)를 보관한다. 이 실행은 읽기 권한과 Actions 후보 artifact 업로드만 사용하며 Nexus/정식 Releases 업로드 단계가 없다.
