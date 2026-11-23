# 오늘의 바다 — 토스 미니앱 SDK 3.x UI v1 (미배포)

## 현재 작업 범위

- 앱인토스 WebView SDK 3.x용 `apps-in-toss.config.ts`, 자동 네비게이션, TDS Provider를 구성했어요.
- TDS Button, Badge를 재조회/상태 확인에 사용하고, 조위 차트·만조/간조 카드만 자체 디자인했어요.
- 기존 `korea_miniapp/output/weekly/`에 저장된 **실제 API 검증 데이터**를 개발 서버에서 읽어요. 가짜 조석 값은 포함하지 않아요.
- 서버에 Cloudflare Worker가 배포되기 전에는 정식 앱의 예보 조회가 실패하도록 설계했어요. 브라우저에 API 키를 넣지 않아요.
- SDK 네비게이션이 자동 표시되므로 웹 본문에는 별도 닫기/뒤로가기나 중복 앱 상단바가 없어요.
- **미배포 상태**: 토스 콘솔 등록, QR 테스트, 실데이터 Cloudflare 배포, 앱 이름/브랜드 로고 설정은 아직 진행하지 않았어요.

## PC에서 실행하기 (Windows PowerShell)

폴더 위치는 기존 `E:\개인작업\앱인토스\오늘의바다\korea_miniapp\miniapp`로 가정해요.

```powershell
Set-Location 'E:\개인작업\앱인토스\오늘의바다\korea_miniapp\miniapp'; npm install; npm run test; npm run dev
```

로컬 브라우저: `http://127.0.0.1:3000` (앱인토스 Devtools 포함)

`miniapp`의 한 단계 위에 `output/weekly/incheon.json`, `busan.json`, `jeju.json`이 있어야 해요. 만료된 날짜의 파일이면 **예보 없음 상태**가 정상이에요. 새 데이터는 별도의 `run_week_check.ps1`로 수집해요.

## 토스 번들 만들기

1. 콘솔에 등록한 앱의 실제 고유 키와 `apps-in-toss.config.ts`의 `appName`을 일치시키세요. 현재는 가칭 `oneul-bada`로 설정했어요.
2. **별도** Cloudflare Worker에서 KHOA 키 2개를 Secret으로 저장하고 HTTPS 데이터 조회 API를 배포하세요. 아직 실배포하지 않았어요.
3. `.env.local`에 **공개 조회용 Worker 도메인만** `VITE_TIDE_API_BASE_URL=https://...` 형식으로 넣으세요. 이 변수는 번들에 포함되므로 비밀 키를 넣으면 안 돼요.
4. `npm run build`로 `.ait`를 만들고, 앱인토스 콘솔에서 QR 테스트 후 출시 검수를 신청하세요.

```
# Local tests (no API calls)
npm run test
# Statically build the UI only
npm run build:web
# Build the actual app bundle (needs SDK and real appName)
npm run build
```

## 정책 기준

- 필수 내비게이션: 토스 SDK 자동 UI, 앱 내 중복 구현 없음.
- TDS: `@toss/tds-mobile`, `@toss/tds-mobile-ait`, `TDSMobileAITProvider`; 버튼/상태 컴포넌트 사용.
- 광고·로그인·위치 권한 요청 없음. 개인정보 입력 없음. 관심 지역은 기기 저장소에만 저장해요.
- 사용자 식별키는 앱 로드 후 요청하되 화면 제공을 막지 않아요. 식별키를 로그·외부 API에 전송하지 않아요.
- 시계열은 30분 간격 48건을 필수 검증해요. 예측 조위(cm)를 실제 수심이나 해양 활동 안전성으로 표현하지 않아요.

공식 문서: https://developers-apps-in-toss.toss.im/ai-vibe-coding/tutorials/webview

## 전국 20개 관측소 등록 (2026-11-20)

지역 선택에서 **서해 6 · 남해 7 · 동해 5 · 제주 2**개 예보지점을 선택할 수 있습니다. 지점 목록은 바로 위 폴더 `../stations.json`에서 가져옵니다. `miniapp` 폴더만 따로 복사하면 빌드되지 않으므로 **반드시 동일 위치에 `korea_miniapp/stations.json`이 있어야** 합니다.

처음 신규 지점을 조회하기 전에 `korea_miniapp/run_week_check.ps1`로 공식 API에서 7일 자료를 수집하세요. 아직 확인하지 않은 지역의 예보는 보여주지 않으며, API 키는 프런트엔드나 GitHub에 저장하지 않습니다.

## 배너 + 보상형 광고 시스템 v1.3 (미배포)

앱인토스 인앱광고 2.0 ver2 공식 WebView SDK를 연동했습니다.

- **배너 1개**: 만조·간조 및 출처 하단에서만 보입니다. `TossAds.initialize`는 한 번 호출하고 `TossAds.attachBanner`로 부착합니다. 광고 SDK UI를 변조하지 않으며, 컴포넌트가 종료되면 `destroy()` 합니다. No Fill 또는 미지원이면 숨깁니다. 배너를 자체적으로 반복 갱신하지 않습니다.
- **리워드 1개**: 광고 시청을 자발적으로 선택하고 공식 `userEarnedReward` 이벤트를 실제로 받은 경우에만 **24시간 주간 물때 비교표 이용권**을 부여합니다. 광고 클릭·노출·닫힘은 보상이 아닙니다. 현금, 토스 포인트, 가상화폐를 지급하지 않습니다.
- **기본 예보는 계속 무료**: 지역 선택, 날짜별 7일 조석 예보, 만조·간조 시간, 조위 그래프는 광고를 보지 않아도 사용할 수 있습니다.
- **브라우저 개발 모드**: 광고 영역만 '미리보기'로 표시하고 실제 광고를 흉내 내지 않습니다. 리워드 버튼은 토스 앱 SDK 미지원이면 비활성화됩니다.
- **토스 QR 광고 테스트**: `npm.cmd run build:adtest`로 공식 테스트 광고 그룹 ID를 사용합니다. **이 테스트 빌드를 출시하지 마세요.** SDK와 토스 앱의 광고 지원 버전을 확인하세요.
- **실제 출시용**: 토스 콘솔에서 배너 광고 그룹 ID와 리워드 광고 그룹 ID를 발급받고, `.env.local`에 아래 두 값을 넣은 뒤 `npm.cmd run build`(production)로 빌드하세요. 설정하지 않은 유형은 광고가 비활성화됩니다. 테스트 ID는 릴리스 모드에서 거절합니다.

```dotenv
VITE_BANNER_AD_GROUP_ID=콘솔에서_발급한_배너_ID
VITE_REWARDED_AD_GROUP_ID=콘솔에서_발급한_리워드_ID
```

`VITE_` 값은 앱 번들에 포함됩니다. 따라서 공식 광고 그룹 ID만 입력할 수 있고 **국립해양조사원 인증키는 절대 입력하면 안 됩니다**. 리워드 광고 그룹의 보상명은 **주간비교권**, 수량은 **1**로 설정하면 화면 안내와 일치합니다. 이 보상은 기기 저장소 기준의 비금전적 24시간 이용권입니다.

```powershell
# 프로젝트 miniapp 폴더
npm.cmd install
npm.cmd run test
npm.cmd run dev
# 토스 실기기 광고 테스트 전용: npm.cmd run build:adtest
# 정식 광고 ID와 Cloudflare 서비스 준비 후: npm.cmd run build
```

**아직 남은 일:** 토스 콘솔 사업자·정산 정보·광고 그룹 등록, 토스 실제 기기에서 광고 테스트(ID가 실제 노출되는지, No Fill/중간 종료/리워드 지급 여부), Cloudflare 실제 데이터 서버 배포, 공식 앱 심사. 브라우저 화면만으로 실제 광고 운영 성공을 판단하면 안 됩니다.

공식 가이드:
- https://developers-apps-in-toss.toss.im/guide/monetization/in-app-ad.md
- https://developers-apps-in-toss.toss.im/documentation/common/monetization/iaa/web-banner.md
- https://developers-apps-in-toss.toss.im/documentation/common/monetization/iaa/interstitial-rewarded-ad.md
