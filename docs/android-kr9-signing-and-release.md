# Android KR9 배포와 서명 호환성

## 출시 현황 (KR9 별도 설치판)

**Android KR9 별도 설치판이 공개됐습니다.** [다운로드 페이지](https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr9-standalone)

- 별도 앱 `com.ast.openmw.kr9`이며, 기존 KR8 앱 `com.ast.openmw`를 덮어쓰지 않습니다.
- 새로운 임시 디버그 서명으로 배포됐습니다. **서명 개인 키가 보존되지 않았으므로 이후 동일 앱을 직접 업데이트할 수 있다는 보장은 없습니다.**
- 두 앱의 저장 경로는 별개입니다. KR8을 삭제하지 말고, 새 앱에서 게임 데이터 위치를 재설정하세요. 세이브 이전은 원본 백업 후 수동으로 진행하세요.
- 새 앱은 기존 공용 `/omw` 데이터를 자동 이동·삭제하지 않도록 변경했습니다.
- [빌드·패키징 검사](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/40598251963) 통과. 번역 데이터는 KR8과 동일합니다.
- 아래의 **원래 KR8 개인 키 회수 절차**는 *기존 KR8 앱을 덮어쓰는 업그레이드형* APK에만 해당하며, 현재 배포된 **KR9 별도 설치판에는 필요하지 않습니다.**

---

## 기존 KR8을 덮어쓰는 방식이 차단된 이유


## 검증 완료 항목

- KR9 Android ARM64 `libopenmw.so`: 네이티브 빌드 성공, SHA-256 `cf106f05d5292663caef5ee2b4588517a9c0da211674f7571cee5d96f2dc8af9`.
- KR8 Android APK와의 JNI 내보내기 심볼·동적 라이브러리 의존성 비교 및 APK 내용 보존 검사 통과.
- Android KR8 원본 APK: 패키지 `com.ast.openmw`, versionCode `5112`, versionName `0.51.0-12`.
- KR8 APK 원본 서명 인증서 SHA-256: `5eea68aceb434506b04f563532460c83330145f3d4ca77ad6ef41792d05985f8`.
- CI 검증 자료: [네이티브 빌드](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/40514491647), [KR8 APK 및 KR9 네이티브 호환성](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/runs/40595784648).

## 출시에 필요한 원본 서명 개인 키

기존 KR8 APK는 **Android Debug** 인증서로 서명되어 있습니다. 공개 APK의 인증서만으로 같은 서명용 개인 키를 복원할 수 없습니다. CI가 과거에 임시 Debug 키를 만들었다면 그 키가 보존되어 있지 않을 수도 있습니다.

1. **과거 KR8 APK를 실제로 서명했던 키 저장소**를 신뢰할 수 있는 로컬 백업 또는 당시 빌드 환경에서 찾습니다. 기본 Android Debug 키의 후보 경로는 Windows의 `%USERPROFILE%\.android\debug.keystore`, macOS/Linux의 `~/.android/debug.keystore`입니다. 경로가 같다는 이유만으로 동일한 키라고 판단하면 안 됩니다.
2. `keytool -list -v -keystore <키파일 경로> -alias <별칭>`을 실행해 **SHA256 인증서 지문이 위 값과 정확히 일치하는지** 확인합니다. 일치하지 않으면 사용하지 않습니다.
3. 일치하는 개인 키를 찾은 경우에만 GitHub 저장소 `munument1/Morrowind-OpenMW-Android-KR`의 **Settings → Secrets and variables → Actions**에 다음 네 가지 repository secret을 설정합니다.
   - `ANDROID_KR8_KEYSTORE_BASE64`: 원본 키 저장소의 파일 바이트를 base64로 인코딩한 값
   - `ANDROID_KR8_STORE_PASSWORD`: 원본 키 저장소 비밀번호
   - `ANDROID_KR8_KEY_PASSWORD`: 선택한 개인 키 비밀번호
   - `ANDROID_KR8_KEY_ALIAS`: 해당 개인 키 별칭
4. 키파일, base64 원문, 비밀번호를 Git 커밋·PR·이슈·채팅에 붙이지 않습니다. base64는 암호화가 아닙니다. 인증서 SHA-256 지문은 비교용 공개 식별자이지만 개인 키는 비밀로 보관해야 합니다.

## 안전한 KR9 출시

원본 키의 일치 여부가 확인되고 GitHub Secrets 구성이 끝난 뒤, GitHub의 **Actions → Publish Android KR9 with original KR8 signing identity → Run workflow (main)** 를 실행합니다.

해당 워크플로는 실제 KR8 APK와 번역 데이터 ZIP을 다운로드하고, 고정된 KR9 엔진 바이너리를 삽입한 뒤 ZIP 정렬·서명·원본 인증서 일치 여부·패키지 식별자·해시·번역 데이터 무변경 여부를 확인합니다. **검사가 모두 통과한 경우에만** `android-korean-0.51.0-12-kr9` 릴리스와 README 변경을 수행합니다.

원본 서명 개인 키를 찾지 못하면 **기존 KR8을 덮어쓰는 유형으로 배포하지 않습니다.** 다른 키로 서명한 APK는 동일한 패키지명이어도 기존 설치본 위에 안전하게 설치할 수 없습니다. 별도 신규 설치용 배포를 택할 경우 사용자 데이터/세이브 백업과 이전 절차를 별도로 결정해야 합니다. 기존 앱을 무턱대고 삭제하도록 안내하지 않습니다.

게임 내부 플레이 테스트는 프로젝트 결정에 따라 생략했으며, 완료했다고 주장하지 않습니다.
