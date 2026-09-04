# CreatorlinkSansKR

Pretendard(SIL OFL 1.1) 기반 웹빌더용 자체 폰트. 한글·기호는 CreatorlinkSansKR, 영문·숫자는 라틴 파트너(Roboto 또는 Inter)가 담당하며, 하나의 font-family 이름으로 묶여 있습니다.

## 적용

```html
<link rel="stylesheet" href="/fonts/creatorlink-sans-kr.css">
<style>
  body { font-family: 'CreatorlinkSansKR', -apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; }
  .table td { font-variant-numeric: tabular-nums; }   /* 숫자 열 정렬 */
</style>
```

`Pretendard`, `Noto Sans KR` 이름으로도 같은 파일이 alias 등록되어 있어 기존 템플릿 CSS를 고치지 않아도 자체 폰트로 대체됩니다. 서브셋을 안 쓰는 CSS(otf/ 또는 ttf/ 만)를 쓰려면 CSS에서 `latin/` 블록을 지우면 프리텐다드 라틴이 그대로 나옵니다.

## 구조

- `otf/woff2-dynamic-subset/`, `ttf/woff2-dynamic-subset/` — 웨이트당 92청크(Pretendard 공식 unicode-range). 브라우저가 페이지에 실제 쓰인 청크만 내려받음 (일반 페이지 100~250KB 수준).
- `otf/full/`, `ttf/full/` — 리네이밍·메트릭 정리된 풀 폰트(디자인 툴 설치용).
- `latin/` — Roboto / Inter 를 CreatorlinkSansKR 메트릭(1949 / −494)에 맞춘 letters+digits 전용 woff2 (24~38KB).
- `specimen.html` — 11~16px 비교 페이지. `python3 -m http.server` 등으로 http 서버에서 여세요 (file:// 에선 폰트가 로드되지 않을 수 있음).

## 힌팅 (Windows 에서 작은 한글이 흐릿하던 문제)

플로우의 FlowSansKR 은 Noto Sans KR(CFF) 이고, Roboto 는 Google Fonts 힌팅판입니다. 둘 다 힌트가 들어 있어 Windows DPR 1 에서 획이 픽셀에 맞게 떨어집니다. 프리텐다드 원본은 **스템 힌트가 하나도 없어서**(BlueValues 만 존재) 같은 환경에서 흐릿하게 보입니다. 그래서 다음을 추가했습니다.

- **OTF(CFF)**: `otfautohint` + `fontinfo`(라틴/한글 FDDict 분리) 로 14,700 글리프 전부 힌팅. 한글은 실측한 전용 존 — 상단 평탄선 1614(+6), 받침 하단 −142(−24), ㅡ/ㅣ 스템 폭 134/158 (Regular 기준, 웨이트별 자동 측정) — 을 쓰고 FDArray 를 Latin / Hangul 2개로 분리해 각자 존을 갖습니다. Source Han Sans 가 힌팅된 방식과 같습니다. **권장.**
- **TTF**: `ttfautohint`(라틴 정식, 한글은 fallback). 한글은 11px 에서 일부 획이 뭉개질 수 있어 비교용으로만 두었습니다.
- **Roboto**: Google Fonts 힌팅판(fpgm/prep/cvt/gasp)으로 교체, 서브셋 시 힌트 유지.
- `specimen.html` 의 "원본 (힌트 없음)" 옵션과 A/B 로 비교할 수 있습니다. 반드시 **Windows · DPR 1 (100% 배율)** 에서 보세요. Mac 은 힌트를 무시하므로 차이가 없습니다.

## 원본 대비 변경점

0. 힌팅: OTF otfautohint(한글/라틴 존 분리), TTF ttfautohint, Roboto 힌팅판
1. name 테이블: Pretendard → CreatorlinkSansKR (Reserved Font Name 회피), 저작권·라이선스 레코드 유지
2. hhea = OS/2 typo = 1949 / −494 / 0, USE_TYPO_METRICS on, win 은 bbox 로 보정 → OS·브라우저별 line-height 편차 제거
3. TTF 계열에 gasp(모든 크기 그레이스케일+대칭 스무딩) 추가
4. 모든 OpenType 피처 유지 (tnum, pnum, ss01~, cv01~, case, zero …), CFF 서브루틴 해제
5. 라틴 파트너 폰트도 같은 메트릭으로 통일 후 U+30-39, U+41-5A, U+61-7A, U+C0-24F 만 서브셋

## 재빌드

```
pip install fonttools brotli afdko ttfautohint-py
python3 build_font.py            # 전체 (힌팅 약 6분 + 서브셋 약 5분 / 2코어)
python3 make_specimen.py         # 스펙 페이지
```
`build_font.py` 상단의 FAMILY / WEIGHTS / LATIN_RANGE / METRICS 를 바꿔 다른 이름·웨이트·범위로 재생성할 수 있습니다.

## 라이선스
Pretendard © Kil Hyung-jin, SIL OFL 1.1 (`LICENSE-Pretendard.txt`). Roboto Apache 2.0, Inter SIL OFL 1.1. 파생 폰트에 "Pretendard" 명칭은 사용하지 않습니다.
