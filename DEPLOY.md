# 배포 가이드

## 1. 올릴 파일

```
<정적 호스팅 / CDN>/fonts/v1/
  woff2-dynamic-subset/   ← final/fonts/woff2-dynamic-subset/ 전체 (276개, 약 4.4MB)
  latin/                  ← final/fonts/latin/ (3개)
```
`fonts/full/`(디자인 툴용 OTF)은 웹에 올리지 않습니다. 버전 폴더(`v1`)를 두는 이유는 폰트를 갱신할 때
캐시 무효화 없이 `v2`로 갈아끼우기 위해서입니다.

## 2. CSS 경로를 절대 URL 로 바꾸기

```
./set-font-url.sh https://<도메인>/fonts/v1
```
→ `creatorlink-sans-kr.css` 가 절대 URL 로 다시 생성됩니다. 이 CSS 와 `creatorlink-type.css` 를
빌더의 전역 CSS(모든 사이트에 삽입되는 곳)에 포함시키세요. 순서는 `creatorlink-sans-kr.css` → `creatorlink-type.css`.

## 3. 서버/CDN 헤더 (필수 2개)

| 헤더 | 값 | 이유 |
|---|---|---|
| `Access-Control-Allow-Origin` | `*` (또는 빌더 사이트 도메인 목록) | 웹폰트는 CORS 필수. 사용자 사이트가 각자 도메인(커스텀 도메인 포함)이라 `*` 권장 |
| `Cache-Control` | `public, max-age=31536000, immutable` | 청크 276개가 매번 재검증되지 않도록. 버전은 폴더(`v1`)로 관리 |
| `Content-Type` | `font/woff2` | 대부분 자동. S3 는 업로드 시 지정 필요 |

woff2 는 이미 Brotli 압축이라 gzip/br 을 다시 적용할 필요 없습니다.

## 4. 확인

1. 사용자 사이트에서 개발자도구 → Network → 필터 `woff2`: 청크가 `200`(또는 캐시)으로 오고 CORS 오류가 없어야 합니다.
2. 한 페이지에 보통 5~20개 청크(100~250KB)만 내려오면 정상입니다. 92개가 전부 오면 CSS 의 unicode-range 가 깨진 겁니다.
3. `specimen.html` 을 같은 CSS 로 열어 11~14px 을 Windows 100% 배율에서 확인.

## 5. 갱신할 때

`build/` 스크립트로 재빌드 → `fonts/v2/` 에 올리고 → `set-font-url.sh …/fonts/v2` → CSS 교체.
이전 버전 폴더는 캐시가 빠질 때까지(약 1년) 남겨두면 안전합니다.

## 6. 라이선스 고지

배포 사이트 어딘가(폰트 안내 페이지, 이용약관 등)에 아래 문구를 두면 OFL 요건이 충족됩니다.
> CreatorlinkSansKR is derived from Pretendard © Kil Hyung-jin, licensed under SIL Open Font License 1.1. Latin glyphs from Roboto (Apache License 2.0).
