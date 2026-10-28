# Android KR9 — 재사용 가능한 영구 서명키

## 현황

- 최초 Android KR9 별도 설치판: `com.ast.openmw.kr9` (일회성 디버그 키, [기존 릴리스](https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr9-standalone))
- 앞으로 유지할 **새 안정판 앱 식별자**: `com.ast.openmw.korean`
- 영구 인증서 SHA-256: `509d883eb7c75eeb3b6c7203ffc4840eaf1b68a0b3f3db4d50708fcb772bff45`.
- [검증용 빌드](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/workflows/validate-kr9-permanent-source.yml).
- [실제 영구 키 서명·배포 워크플로](https://github.com/munument1/Morrowind-OpenMW-Android-KR/actions/workflows/publish-kr9-android-permanent.yml) — 수동 실행 전 2개 GitHub Secrets 필수.
- 이 새 앱은 기존 KR8 `com.ast.openmw` 및 초기 KR9 `com.ast.openmw.kr9`와 서로 다른 개인 저장 공간을 사용합니다. 이전 앱 삭제/자동 데이터 이동은 하지 않습니다.

## 보관해야 할 두 개의 파일

프로젝트 관리자가 제공받은 아래의 서로 다른 파일을 각기 안전하게 보관합니다.

1. `android_kr9_permanent_keystore.encrypted.json` — AES-256-GCM으로 암호화한 원본 서명키 백업 (암호문).
2. `ANDROID_KR9_SIGNING_KEY_HEX_PRIVATE.txt` — 암호문을 복호화할 수 있는 **비밀 복구 키**. 절대 공개/커밋/이슈/채팅에 붙이지 마세요.

백업 파일은 **둘 다** 있어야 합니다. 암호문만 있거나 비밀 복구 키만 있으면 원래 서명 개인 키를 복구할 수 없습니다. GitHub Secrets와 별도로 오프라인 백업도 보관하세요.

## GitHub Secrets 등록 (저장소 소유자)

인증된 기기에서 `gh auth login`을 완료하고 GitHub CLI를 사용합니다.

```bash
REPO=munument1/Morrowind-OpenMW-Android-KR
ENC=/path/to/android_kr9_permanent_keystore.encrypted.json
PRIV=/path/to/ANDROID_KR9_SIGNING_KEY_HEX_PRIVATE.txt

gh secret set ANDROID_KR9_ENCRYPTED_KEYSTORE_JSON --repo "$REPO" < "$ENC"
sed -n 's/^ANDROID_KR9_SIGNING_KEY_HEX=//p' "$PRIV" | gh secret set ANDROID_KR9_SIGNING_KEY_HEX --repo "$REPO"
```

GitHub 웹에서도 **Settings → Secrets and variables → Actions → New repository secret**에서 위 이름 두 개를 각각 만들 수 있습니다. 새로 만드는 Secret은 API 권한을 가진 사용자만 설정할 수 있으며, 연결된 GitHub 읽기/코드수정 도구만으로는 설정할 수 없습니다.

## 검증과 출시

1. **Actions → Validate Android KR9 permanent app source and ABI**가 성공했는지 확인합니다.
2. GitHub Actions Secrets 두 개를 등록합니다.
3. **Actions → Publish Android KR9 with persistent signing key → Run workflow (main)**을 실행합니다.
4. 워크플로가 인증서 SHA-256, ARM64 바이너리 SHA-256, 버전 및 패키지명, 16KiB 정렬, APK 재서명 검증, KR8 데이터 ZIP 동일성을 확인합니다.
5. 모두 성공한 경우에만 `android-korean-0.51.0-12-kr9-permanent` 릴리스를 게시합니다. 아직 출시 전이라면 README의 최신 배포판은 이전 릴리스를 가리키도록 유지합니다.

## 다음 버전 KR10 등

`com.ast.openmw.korean` 패키지명과 **같은 서명키**를 유지하고, Android `versionCode`를 이전 출시판보다 높여야 기존 사용자에게 인플레이스 업데이트를 제공할 수 있습니다. 키를 새로 생성하거나 인증서를 바꾸면 기존 설치판을 일반 업데이트로 덮어쓸 수 없습니다.

Android 기기에서의 실제 플레이 검증은 요청에 따라 생략했으며 완료했다고 표기하지 않습니다.
