# 오늘의 바다 — 한국 조석 데이터 연동 실험 (미배포)

**상태:** 개발용 격리 브랜치 실험. 기존 `CoastalNow` NOAA/미국 사이트의 운영 파이프라인은 변경하지 않았습니다. 이 폴더는 토스 SDK 또는 실제 미니앱 배포 기능을 포함하지 않습니다.

## 1. 확인한 공공 API

- 고·저조: `https://apis.data.go.kr/1192136/tideFcstHghLw/GetTideFcstHghLwApiService`
  - 원문: https://www.data.go.kr/data/15156018/openapi.do
- 조석 시계열: `https://apis.data.go.kr/1192136/tideFcstTime/GetTideFcstTimeApiService`
  - 원문: https://www.data.go.kr/data/15156022/openapi.do
- 공통 인자: `serviceKey`, `obsCode`, `reqDate=YYYYMMDD`, `type=json`, `numOfRows=300`
- 시계열 추가 인자: `min=30` (30분 간격)
- 초기 3개 지점: 인천 `DT_0001`, 부산 `DT_0005`, 제주 `DT_0004`
- 원본 조위 높이는 **cm**, 모든 표시 시각은 **Asia/Seoul (KST)** 가정. 공식 수직 기준면(datum), 실제 응답 형식 및 인코딩은 승인된 키로 통합 검증할 때 확정합니다.
- 이용 조건(2026-11): 무료, 공공누리 출처표시 제1유형, 개발 자동 승인 / 운영 심의 승인. **출시 전에 실제 운영 승인 여부를 확인**해야 합니다.

## 2. 현재 코드 동작

`pipeline.py`는 지점과 날짜 하루를 지정해 고·저조와 30분 조위 예보를 각각 1회씩 요청합니다. 두 API의 인증키가 다를 수 있으므로 `KHOA_HIGH_LOW_KEY`(고·저조)와 `KHOA_SERIES_KEY`(시계열)를 별도로 읽고,, 포맷·날짜·중복·단위 범위를 검증한 뒤 독립 JSON으로 저장합니다.

- 고·저조 필드: `predcDt`, `predcTdlvVl`, `extrSe` (`1·3 = 만조`, `2·4 = 간조`)
- 시계열 필드: `predcDt`, `tdlvHgt` (공식 가이드 기준, 조위 cm)
- **두 API의 높이 필드 이름이 다릅니다.** 2026-11-06 국립해양조사원 활용가이드 명세에 따라 구현했으며, 실제 API 수신은 다시 검증해야 합니다.
- 데이터가 없거나 응답 형식이 바뀌거나 API가 실패하면 명시적으로 오류를 내며, 임의의 조석 값을 생성하거나 운영 데이터로 교체하지 않습니다.
- 출력 JSON은 별도 실험용 형식입니다. 기존 `src/generate_tides.py`의 렌더링에는 바로 연결되지 않습니다(기존 렌더링은 미국/feet 표기를 전제).

## 3. 테스트 및 API 호출

```powershell
# 저장소 루트에서 오프라인 테스트 (외부 호출 0회)
python -m unittest discover -s korea_miniapp -p 'test_*.py' -v

# 키 없이 요청 구성만 검사 (외부 호출 0회)
python korea_miniapp/pipeline.py --station incheon --date 2026-11-17 --dry-run

# Windows PowerShell: 화면에서 두 서비스의 키를 별도로 입력합니다.
# 입력한 키는 화면에 표시되지 않으며 두 환경변수도 종료 시 삭제됩니다.
# 오프라인 테스트를 먼저 수행하고 인천·부산·제주 3곳을 조회합니다.
.\korea_miniapp\run_live_check.ps1

# 개별 호출도 가능 (키는 환경변수에만 저장해야 함)
# $env:KHOA_HIGH_LOW_KEY = (Read-Host '고·저조 API 키')
# $env:KHOA_SERIES_KEY = (Read-Host '시계열 API 키')
# python korea_miniapp/pipeline.py --station incheon
```

출력 JSON은 `korea_miniapp/output/`에 저장되며 이 디렉터리는 gitignore 처리했습니다. 파일과 키는 커밋하지 마세요. 스크립트는 성공 여부와 건수만 표시하고 키는 로그에 출력하지 않습니다.

## 4. 통합 검증 완료 조건

1. 공식 사이트에서 **개발용 활용신청**을 완료하고 발급된 인증키로 3개 지점에서 실제 호출 성공
2. 원본 응답 구조(`header/body/items`), 만조·간조 코드, 시계열 데이터 필드, 단위·시각·수직 기준을 공식 가이드와 대조
3. 같은 날짜/같은 관측소의 공식 조회 결과와 고·저조 시각 및 높이가 일치하는지 확인
4. 실패/데이터 지연 시 오래된 데이터를 정상값처럼 표시하지 않는지 확인
5. 7일 예보, 중앙 캐시, 호출량 제한, 데이터 갱신 모니터링 적용
6. 이후에만 토스 WebView SDK 3.x, 관심 지역 저장, 실제 UI를 개발하고 토스 검수 신청

**하지 않을 일:** 기존 미국 서비스의 갱신 주기나 배포, 서핑/낚시 추천 점수를 변경하지 않습니다. 국내 조석 데이터를 충분히 검증하기 전 안전한 활동 가능 여부를 단정하지 않습니다.

## 조위값 필드 누락 시 진단 (보조 수단)

공식 문서에 맞춘 수정 후에도 높이 필드 오류가 반복된다면, 아래 명령으로 **인천 1개 지점의 두 API**가 반환하는 필드 이름만 확인합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_schema_probe.ps1
```

두 키를 다시 입력해야 하지만, 화면에 나타나는 것은 구조(`first row fields`)와 필드 존재 여부뿐입니다. **API 키, 호출 URL, 조위 수치, 원본 응답은 출력하거나 파일로 저장하지 않습니다.**

이 결과를 받아 실제 필드 이름과 단위를 확인한 뒤 파서를 수정합니다. 확인되지 않은 필드명을 추측해 조위로 사용하지 않습니다.

## 2026-11-06 공식 활용가이드 반영 (v4)

| API | 예측일시 | 조위(cm) | 구분 |
| --- | --- | --- | --- |
| 고·저조 | `predcDt` | `predcTdlvVl` | `extrSe` 1/3=고조, 2/4=저조 |
| 시계열 | `predcDt` | `tdlvHgt` | `min=30`(1~60 허용) |

`type=json`, `numOfRows=300`을 유지합니다. 실제 키는 어떤 저장소에도 업로드하지 마세요.
오프라인 검증 이후 인천/부산/제주 테스트에서 두 종류의 예보가 모두 성공해야 데이터 연동이 완료됩니다.

## 7일 조석예보 묶음 검증 (v5)

`build_week.py`는 이미 검증된 `pipeline.py`를 사용해 **오늘부터 7일간** 고·저조와 30분 간격 시계열을 수집합니다. 총 **42회**의 API 호출을 계획하며, 고·저조 API와 시계열 API 각각 **21회**입니다(3지점 × 7일). 현재 이 코드는 로컬 개발용으로, 아직 서버나 토스 미니앱에는 배포되지 않았습니다.

```powershell
# korea_miniapp 폴더에서 실행. 두 인증키는 화면에 표시하지 않습니다.
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_week_check.ps1

# 네트워크 요청 없이 요청량만 확인
python .\build_week.py --dry-run
```

정상 수집 시 `output/weekly/incheon.json`, `busan.json`, `jeju.json`이 만들어집니다. **7일 전체 수집·검증에 성공한 지역만 파일을 원자적으로 교체**하므로, 중간에 한 날짜라도 실패하면 기존 파일을 덮어쓰지 않습니다.

**주의:** 기존 파일 보존은 '최신 예보 보증'이 아닙니다. 실제 앱은 각 파일의 `date_range`와 `generated_at_utc`를 확인하고 오래된 자료는 오류 상태로 표시해야 합니다. 검증 중인 수직기준면(`datum`)을 실제 수심처럼 해석하거나 안전한 해양활동을 단정하지 않습니다.

### PC 없이 클라우드 운영하기 위한 후속 준비

- GitHub Actions 또는 Cloudflare Cron에 **서버 측 수집 작업** 연결
- Cloudflare KV/R2 등 중앙 캐시에 검증된 JSON 저장하고 HTTPS 데이터 API 제공
- `KHOA_HIGH_LOW_KEY`, `KHOA_SERIES_KEY`는 서버 Secrets에서만 관리
- 갱신 실패 모니터링, 기준면과 KST 시각 검증, 공식 예보 대조
- 운영 단계 활용승인 및 출처 표기, 토스 WebView SDK 적용

**현 상태:** 7일 수집 코드 + 오프라인 테스트만 추가. GitHub 자동 스케줄과 실제 Cloudflare 배포는 아직 설정하지 않았으며 미국 CoastalNow 운영 변경은 없습니다.

### Windows PowerShell 5.1에서 한글 입력 안내가 깨질 때

Windows PowerShell 5.1은 BOM 없는 UTF-8 `.ps1` 파일을 기본 ANSI 문자셋으로 해석하는 경우가 있습니다. v5.1부터 실행 스크립트 3개를 **UTF-8 BOM**으로 저장했습니다. 기존 v5 파일을 이미 받은 경우에는 `Ctrl+C`로 입력을 중단한 후 해당 폴더의 PowerShell에서 다음 한 줄로 복구할 수도 있습니다.

```powershell
$p='.\run_week_check.ps1'; [System.IO.File]::WriteAllText((Resolve-Path $p).Path,[System.IO.File]::ReadAllText((Resolve-Path $p).Path,[System.Text.Encoding]::UTF8),[System.Text.UTF8Encoding]::new($true))
```

그다음 `powershell -NoProfile -ExecutionPolicy Bypass -File .\run_week_check.ps1` 로 재실행합니다. 보안상 API 키는 채팅이나 이미지로 공유하지 않습니다.

## 지역 확대: 20개 조석예보 지점 (2026-11-20)

사용자가 제공한 2026-11-06 국립해양조사원 고·저조/시계열 활용가이드의 공식 예보지점 목록을 기준으로 20곳의 코드와 이름을 `stations.json`에서 관리합니다.

- 서해 6곳: 인천, 평택, 태안, 보령, 군산, 목포
- 남해 7곳: 부산, 통영, 여수, 거제도, 완도, 진도, 마산
- 동해 5곳: 속초, 묵호, 포항, 울산, 울릉도
- 제주 2곳: 제주, 서귀포

`pipeline.py`(Python), 토스 미니앱, Vite 개발서버, Cloudflare Worker는 모두 **같은 station catalog**를 참조합니다. 새 17개 지점의 실제 API 응답 검증은 아직 필요합니다.

로컬에서 20곳의 7일 예보를 한꺼번에 검증하는 경우 `run_week_check.ps1`을 실행하면 **20 × 7 × 2 = 280회**의 공식 API 요청(각 서비스 140회)을 합니다. 지역별 예보를 검증하기 전에 해당 지역의 데이터가 정상이라고 가정하지 않습니다.

Cloudflare Worker는 무료 플랜의 실행당 50개 하위 요청 제한에 맞춰 **매시간 2곳씩 순환**, 한 번의 실행에서 28회 공식 API 호출 + 2회 KV 쓰기를 수행하도록 변경했습니다. 전체 20개 지역을 한 차례 갱신하는 데 예약 실행 10회가 필요합니다. 배포 직후 일부 지역에 캐시가 없는 동안에는 사용자에게 예보를 임의로 생성하지 않습니다. 업데이트가 30시간 이상 실패한 지역은 만료 상태(503)로 취급합니다.

**상태:** 개발 브랜치 구현 및 오프라인 테스트 단계. 정식 Cloudflare 배포와 운영 전 수치 대조, 토스 콘솔 연동은 별도로 진행합니다.
