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
- 시계열 필드(동일하게 가정): `predcDt`, `predcTdlvVl`
- 이 필드 매핑은 공개 사용례와 문서에 근거한 **잠정 구현**입니다. 정식 API 키로 받은 실제 응답은 아직 검증하지 않았습니다.
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

## 조위값 필드 누락 시 진단 (v3)

실제 API 호출 후 `Missing predicted tide height (predcTdlvVl)`가 발생했다면, 아래 명령으로 **인천 1개 지점의 두 API**가 반환하는 필드 이름만 확인합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_schema_probe.ps1
```

두 키를 다시 입력해야 하지만, 화면에 나타나는 것은 구조(`first row fields`)와 필드 존재 여부뿐입니다. **API 키, 호출 URL, 조위 수치, 원본 응답은 출력하거나 파일로 저장하지 않습니다.**

이 결과를 받아 실제 필드 이름과 단위를 확인한 뒤 파서를 수정합니다. 확인되지 않은 필드명을 추측해 조위로 사용하지 않습니다.
