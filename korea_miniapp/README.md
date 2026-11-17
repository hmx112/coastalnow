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

`pipeline.py`는 지점과 날짜 하루를 지정해 고·저조와 30분 조위 예보를 각각 1회씩 요청하고, 포맷·날짜·중복·단위 범위를 검증한 뒤 독립 JSON으로 저장합니다.

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

# 아래는 공공데이터포털에서 활용신청 후 발급받은 키가 있어야 실행됩니다.
# 키를 채팅, 깃허브, 코드, 커밋, 이슈에 붙여넣지 마세요.
$env:KHOA_SERVICE_KEY = (Read-Host '공공데이터포털 API 키')
python korea_miniapp/pipeline.py --station incheon --output .\korea-tide-test-incheon.json
Remove-Item Env:KHOA_SERVICE_KEY
```

출력 JSON은 커밋하지 말고 확인용으로만 사용하세요. 요청 URL과 인증키가 로그에 나오지 않도록 설계했으며, 오류 시 키를 출력하지 않습니다.

## 4. 통합 검증 완료 조건

1. 공식 사이트에서 **개발용 활용신청**을 완료하고 발급된 인증키로 3개 지점에서 실제 호출 성공
2. 원본 응답 구조(`header/body/items`), 만조·간조 코드, 시계열 데이터 필드, 단위·시각·수직 기준을 공식 가이드와 대조
3. 같은 날짜/같은 관측소의 공식 조회 결과와 고·저조 시각 및 높이가 일치하는지 확인
4. 실패/데이터 지연 시 오래된 데이터를 정상값처럼 표시하지 않는지 확인
5. 7일 예보, 중앙 캐시, 호출량 제한, 데이터 갱신 모니터링 적용
6. 이후에만 토스 WebView SDK 3.x, 관심 지역 저장, 실제 UI를 개발하고 토스 검수 신청

**하지 않을 일:** 기존 미국 서비스의 갱신 주기나 배포, 서핑/낚시 추천 점수를 변경하지 않습니다. 국내 조석 데이터를 충분히 검증하기 전 안전한 활동 가능 여부를 단정하지 않습니다.