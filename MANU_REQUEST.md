# BSD Brawl Plus — Colt 에임봇/닷지봇 개발 의뢰서

> 마누스에게: 이 프로젝트는 구현 코드와 분석 자료가 이미 완성되어 있음. APK 빌드 및 libBSD.p.so / libg.so 패치 주입만 남았음. 아래 자료를 참고하여 완성해줘.

---

## 요구사항

- **캐릭터**: Colt (Star Power 1 + Buffy 장착)
- **핵심 기능**:
  1. 움직이는 상대에게 모든 탄환 적중 (Moving Aimbot + Auto-Move)
  2. 콜트 궁극기 벽 관통 + 감속 반영
  3. 에임봇/닷지봇 ON/OFF 플로팅 버튼
  4. 자체 학습 (적 이동 패턴 분석 → 정확도 향상)

---

## 완성된 구현 파일

| 파일 | 설명 | 바이트 |
|------|------|--------|
| `aimbot_enhanced.cpp` | 자체학습 다중적 에임봇 | 14.7KB |
| `joystick_controller.cpp` | 발사 중 조이스틱 가로채기 | 4.1KB |
| `colt_super_physics.cpp` | 콜트 궁 벽 관통 + 감속 물리 | 5.8KB |
| `aimbot_native.cpp` | 기본 에임봇/닷지봇 | 12.1KB |
| `arm64_hook.cpp` | ARM64 인라인 후킹 | 8.2KB |
| `AimbotFloatingService.java` | 플로팅 ON/OFF 버튼 | 6.3KB |
| `MainActivity.java` | 앱 진입점 | 2.0KB |
| `AndroidManifest.xml` | 권한 | 1.1KB |
| `Android.mk` | NDK 빌드 스크립트 | 0.8KB |

---

## Colt 설정값

```cpp
#define PROJECTILE_SPEED_COLT        8.33f
#define PROJECTILE_SPEED_COLT_SUPER  6.0f
#define WALL_PENETRATION_DECAY       0.5f
#define COLT_OPTIMAL_RANGE_MIN       4.0f
#define COLT_OPTIMAL_RANGE_MAX       9.0f
#define COLT_OPTIMAL_RANGE_CENTER    6.5f
#define MAX_PREDICTION_TIME          1.5f
#define DODGE_DISTANCE               2.0f
```

---

## libBSD.p.so Hook Chain (패치 대상)

### 발사 관련
```
0x004b8c — TriggerProjectileOnBasicAttack
0x004bb8 — TriggerProjectileOnBasicAttack
0x004be4 — TriggerProjectileOnBasicAttack
0x004c3c — UltiTrigger
0x004c94 — ShootTrigger
0x004cc0 — Input/Fire trigger (메인)
```

### 조이스틱/입력 관련
```
0x004c10 — input (+0x0094)
0x004c68 — control (+0x02ef)
0x004cc0 — Input (+0x0527)
0x004d18 — Axis (+0x1026)
0x004d44 — Axis (+0x061e)
0x0055f8~0x005b10 — joystick (14개 hook)
```

### 이동 관련
```
0x004e20 — movement
0x004e4c — movement
0x004e78 — movement
0x004ea4 — movement
```

### 터치/스와이프 관련
```
0x0051bc~0x005374 — touch/swipe (10개 hook)
```

### 위치/투사체 관련
```
0x004f80, 0x004fac, 0x004fd8 — position
0x004f28, 0x004f54, 0x0056a8 — projectile
```

---

## 빌드 방법

### 1. NDK 빌드
```bash
ndk-build NDK_PROJECT_PATH=. APP_BUILD_SCRIPT=Android.mk
```
출력: `libs/arm64-v8a/libbsd_aimbot.so`

### 2. APK 삽입
- MT Manager로 bsd_brawl_plus_v67.264.apk 열기
- `lib/arm64-v8a/libbsd_aimbot.so` 추가
- smali에 `System.loadLibrary("bsd_aimbot")` 삽입
- 서명 → 설치

### 3. 직접 패치
- libBSD.p.so: 기존 hook (0x004cc0, 0x004c10 등)에 에임봇 로직 삽입
- 또는 libg.so: position setter (0x005b05e0, 0x008e76a4) 직접 패치

---

## 원본 APK
- 링크: `https://cloud.mysticte.ch/project_bsd/bsd_brawl_plus_v67.264.apk`
- 분석 대상: `libBSD.p.so` (7.2MB), `libg.so` (19MB)

---

## 분석 결과 요약

- `libBSD.p.so`: MOD hook 라이브러리. 1041개의 hook table 존재.
- `libg.so`: Supercell Titan 엔진. position setter, projectile speed, enemy detection 함수 존재.
- Position offsets: `X=+0x10`, `Y=+0x14`, `Z=+0x18`
- libBSD.p.so가 이미 완전한 입력/발사/이동 프레임워크를 가지고 있음 → 이 hook chain을 활용하여 에임봇 삽입 가능

---

## 진행 상황
- ✅ 요구사항 분석 완료
- ✅ 구현 코드 완성 (9개 파일)
- ✅ libBSD.p.so / libg.so 분석 완료
- ✅ hook chain mapping 완료
- ❌ APK 실제 패치/빌드 (이 서버에서 불가)
- ❌ 게임 내 실제 동작 검증

---

## 마누스에게
이 프로젝트는 **코드와 분석이 100% 완성**되어 있음. 남은 것은:
1. Android NDK로 .so 빌드
2. MT Manager 또는 Apktool로 APK에 주입
3. 실제 기기에서 동작 검증
4. 필요시 hook 주소 미세 조정

자료: `/root/.openclaw/workspace/analysis/`
