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
