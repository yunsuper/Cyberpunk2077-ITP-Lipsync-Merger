# 🎙️ ITP Lipsync Merger

> **"영어 음성 전용 립싱크 데이터를 다른 음성 언어 환경으로 이식하는 Cyberpunk 2077 모딩 파이프라인"**

[Immersive Third Person - Best Of Both Worlds V2](https://www.nexusmods.com/cyberpunk2077/mods/32203) (by CybrDrake)의 V 립싱크는 영어 음성(`en-us`) 전용입니다. 이 도구는 **사용자 PC에 설치된 원본 모드와 게임 파일만으로** 다른 음성 언어용 립싱크 아카이브를 만듭니다.

- 🎮 **한국어 완성본(넥서스)**: [Immersive Third Person V2 - Korean VO Lipsync](https://www.nexusmods.com/cyberpunk2077/mods/35165) · ▶️ [인게임 영상](https://youtu.be/BUVCYmAJE1Q)
- 이 저장소에는 **원본 모드 데이터와 게임 파일이 포함되어 있지 않습니다.** 코드만 있습니다.

---

## 🔍 Problem

- 사이버펑크 2077은 텍스트 언어와 음성 언어를 따로 설정하고, **립싱크 데이터는 음성 언어를 따릅니다.**
- 1인칭 기본 게임에서는 V의 얼굴이 보이지 않아 V 입모양 데이터가 일부 장면에만 있습니다. 원본 모드는 이를 **영어용으로만** 보충합니다.
- 그래서 한국어 더빙으로 플레이하면 3인칭 대화에서 V의 입이 움직이지 않습니다.

## 🧩 How It Works

`.lipmap`은 장면별로 "어느 목소리 태그가 어느 입모양 파일을 쓰는지" 적은 **전체 목록**이고, 게임 원본을 통째로 대체합니다. 경로가 해시로 저장되는 아카이브라 폴더 이름만 바꿔서는 동작하지 않습니다.

```
원본 모드 archive ──extract──▶ en-us.lipmap + v.anims
                                     │ convert s (CR2W → JSON)
게임 kr-kr.lipmap ──convert s──▶ JSON ┤
                                     ▼
                        V 항목만 선별 병합 (Python)
                                     │ convert d (JSON → CR2W)
                                     ▼
              kr-kr.lipmap + v.anims(kr-kr 경로) ──pack──▶ 새 archive
```

**병합 규칙**
1. 영어 목록에서 **모드가 추가한** V 항목만 뽑습니다. (게임 원본 V 항목은 제외)
2. 같은 장면이 대상 언어 목록에 있으면,
   - 이미 V 항목이 있으면 **건너뜁니다** (그 언어 음성에 맞춘 원본 유지)
   - 없으면 V 태그와 대상 언어 경로의 `v.anims`를 추가합니다.
3. 대상 언어 목록에 없는 장면은 V 항목만 가진 새 장면으로 추가하고, `scenePaths` 숫자 정렬을 유지합니다.
4. NPC 입모양은 **대상 언어 원본을 그대로** 둡니다.

`v.anims` 안의 애니메이션 이름은 언어와 무관한 대사 ID(`f_…`, `m_…`)라서 그대로 재사용할 수 있습니다. 단, **영어 음성 길이 기준이라 타이밍은 어긋납니다.**

## ✅ Verification (자동 수행)

| 단계 | 확인 내용 |
| :--- | :--- |
| 변환 신뢰성 | 대상 `.lipmap`을 JSON으로 바꿨다가 되돌린 결과가 **원본과 바이트 단위로 동일**한지 확인. 다르면 중단 |
| 패킹 무결성 | 만든 아카이브를 다시 풀어 넣은 파일과 **전부 일치**하는지 확인 |

**한국어(`kr-kr`) 결과**

| 게임 버전 | 원본 모드 | 기존 장면에 V 추가 | 대상 원본 V 유지 | 새 장면 | `v.anims` | 결과 장면 / V 항목 | 인게임 테스트 |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| 2.3 | 2.0.0, 2.0.1 (결과 동일) | 786 | 134 | 9 | 795 | 3,453 / 958 | 완료 |
| 2.5 | 2.0.1 | 785 | 135 | 9 | 794 | 3,485 / 987 | 게임 2.5에서는 미검증 |

- 원본 모드 2.0.0 → 2.0.1에서 립싱크 아카이브는 파일 2개만 바뀌었고(게임 2.5 새 장면이 추가된 `en-us.lipmap`, `v.anims` 1개), 게임 2.3 기준 결과물은 **바이트 단위로 동일**합니다.
- 게임 2.5의 `kr-kr.lipmap`은 장면이 32개 늘었고(3,444 → 3,476), 일부 장면에는 게임 원본 V 입모양이 새로 들어갔습니다.

## 🎯 게임 버전을 맞춰야 하는 이유

결과물은 대상 언어 `.lipmap`을 **통째로 대체**하므로, **`.lipmap`을 꺼낸 게임 버전에서만** 올바르게 동작합니다.

| 상황 | 증상 |
| :--- | :--- |
| 옛 게임 버전용 결과물을 새 게임에 사용 | 새로 추가된 장면이 목록에서 빠져, 그 장면의 입모양(V와 NPC 모두)이 나오지 않을 수 있음 |
| 새 게임 버전용 결과물을 옛 게임에 사용 | 옛 게임에 없는 입모양 파일을 가리키는 장면에서 V의 입이 움직이지 않음 (게임 2.3에 게임 2.5용 결과물, 즉 넥서스 배포본 1.1을 넣어 테스트: 미스티 기본 대화에서 V 입이 멈춤. 튕김은 없음) |

게임이 업데이트되면 그 버전의 `.lipmap`으로 다시 만드세요.

---

## 🛠 Usage

### 준비물
- Python 3.8+
- [WolvenKit](https://github.com/WolvenKit/WolvenKit) CLI (9.1.0에서 확인, **.NET 10 Runtime** 필요)
- 원본 모드 [Immersive Third Person - Best Of Both Worlds V2](https://www.nexusmods.com/cyberpunk2077/mods/32203) 설치
- 게임의 **음성 언어**를 원하는 언어로 설정해 데이터가 받아진 상태 (해당 언어의 `.lipmap`은 그 음성 데이터가 있을 때만 보입니다)

### 1. 대상 언어 `.lipmap` 꺼내기 (WolvenKit GUI)
1. Asset Browser에서 **Mod Browser를 꺼서** 게임 원본 보기로 전환
2. `.lipmap` 검색 → 설치된 음성 언어의 파일만 보입니다 (한국어는 `ko-kr`이 아니라 **`kr-kr`**)
3. 원하는 언어 파일 우클릭 → **Add selected items to project**
4. 프로젝트 폴더 `source\archive\base\localization\` 아래에 생깁니다.

### 1-B. 게임을 업데이트하지 않고 다른 게임 버전의 `.lipmap` 꺼내기 (선택)
모드팩 때문에 게임을 옛 버전으로 유지하면서 최신 버전용 결과물을 만들고 싶을 때 쓰는 방법입니다. 설치된 게임은 건드리지 않습니다.

1. 스팀 콘솔을 엽니다: `Win + R` → `steam://open/console`
2. 원하는 음성 언어의 depot만 받습니다 (한국어 약 5GB, 진행률은 표시되지 않음).
   ```text
   download_depot 1091500 1460470
   ```
   | 음성 언어 | depot | 음성 언어 | depot |
   | :--- | :--- | :--- | :--- |
   | 한국어 | 1460470 | 일본어 | 1091508 |
   | 중국어(간체) | 1091509 | 포르투갈어(브라질) | 1460471 |
   | 폴란드어 | 1091502 | 러시아어 | 1091503 |
   | 프랑스어 | 1091504 | 이탈리아어 | 1091505 |
   | 독일어 | 1091506 | 스페인어 | 1091507 |

   (depot 번호는 SteamDB 기준. 한국어만 직접 확인했습니다.)
3. 받은 위치: `<Steam 폴더>\steamapps\content\app_1091500\depot_<번호>\archive\pc\content\lang_<언어>_voice.archive`. 다운로드가 끝나 파일 잠금이 풀린 뒤 진행합니다.
4. WolvenKit CLI로 `.lipmap`만 꺼냅니다 (Windows PowerShell 기준).
   ```powershell
   & "C:\Tools\WolvenKit.CLI\WolvenKit.CLI.exe" unbundle `
     "<받은 위치>\lang_ko_voice.archive" -o ".\lipmap_out" -w "*.lipmap"
   ```
   결과: `lipmap_out\base\localization\kr-kr.lipmap` → 이 파일을 `--target-lipmap`에 넣습니다.

### 2. 실행 (Windows PowerShell 기준)
```powershell
python lipsync_merge.py `
  --wolvenkit "C:\Tools\WolvenKit.CLI\WolvenKit.CLI.exe" `
  --mod-archive "<원본 모드 폴더>\archive\pc\mod\immersive_third_person_v_lipsync_en.archive" `
  --target-lipmap "<WolvenKit 프로젝트>\source\archive\base\localization\kr-kr.lipmap" `
  --out ".\output"
```

결과: `output\archive\pc\mod\immersive_third_person_v_lipsync_<언어>.archive`

아카이브 안의 `.lipmap` 이름은 입력 파일 이름과 상관없이 **lipmap 안의 언어 코드**(`kr-kr.lipmap` 등)로 들어갑니다. 버전별로 `kr-kr_2.5.lipmap`처럼 이름을 바꿔 보관해도 됩니다.

### 3. 적용
- `output` 폴더 내용을 게임 폴더 또는 MO2 모드 폴더에 넣습니다.
- 원본 모드와 **함께 켜둡니다.** 영어 립싱크 아카이브는 그대로 둡니다.
- 게임 **음성 언어**를 대상 언어로 설정했을 때만 효과가 있습니다.

### 다시 만들어야 하는 경우
- 원본 모드의 `immersive_third_person_v_lipsync_en.archive`가 바뀔 때
- 게임 패치로 대상 언어 `.lipmap`이 바뀔 때 (예: 2.3 → 2.5)
- 다른 모드가 같은 `.lipmap`을 덮어쓰면 충돌합니다. 이 경우 두 목록을 합쳐야 합니다.

---

## ⚠️ Notes

- 한국어(`kr-kr`) 외 언어는 **테스트하지 않았습니다.** 같은 구조라 동작할 것으로 예상하지만 보장하지 않습니다.
- Linux용 WolvenKit CLI는 Oodle을 쓸 수 없어 Kraken 대체 압축으로 패킹됩니다. 한국어 결과물은 이 방식으로도 게임에서 정상 동작했습니다.
- 한국어 2.5용 결과물은 게임 2.3에서 실행해 아카이브 자체가 정상임을 확인했지만(튕김 없음, 기존 장면 정상), **게임 2.5 환경에서는 아직 테스트하지 못했습니다.**
- 통계의 "대상 원본 V 유지"는 **장면 수** 기준, "V 항목"은 목소리 태그 수 기준입니다.
- `--keep-work` 옵션을 주면 중간 작업 폴더를 남겨 결과를 직접 확인할 수 있습니다.
- 결과 아카이브는 원본 모드 제작자의 데이터를 포함하므로 **개인 사용 목적**으로만 만드세요. 재배포하려면 원작자의 허락이 필요합니다.

## 🙏 Credits

- **CybrDrake**: Immersive Third Person - Best Of Both Worlds 및 모든 V 립싱크 애니메이션
- **WolvenKit Team**: WolvenKit
- 이 도구는 원본 모드와 공식적인 관계가 없는 비공식 도구입니다.

## 📄 License

이 저장소의 **소스 코드**는 [MIT License](LICENSE)를 따릅니다.
Immersive Third Person - Best Of Both Worlds(CybrDrake), 그 립싱크 애니메이션, 그리고 이 도구가 처리하는 Cyberpunk 2077 게임 파일은 이 라이선스에 포함되지 않으며 각 권리자에게 있습니다.
