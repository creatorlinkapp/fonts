#!/bin/sh
# 사용: ./set-font-url.sh https://cdn.creatorlink.net/fonts/v1
# → creatorlink-sans-kr.css 안의 폰트 경로를 절대 URL 로 바꿔 씁니다 (fonts/ 폴더의 내용을 그 URL 아래에 올리세요)
[ -z "$1" ] && { echo "usage: $0 <FONT_BASE_URL>"; exit 1; }
BASE="${1%/}"
sed "s|__FONT_BASE__|$BASE|g" creatorlink-sans-kr.template.css > creatorlink-sans-kr.css
echo "written creatorlink-sans-kr.css  (fonts → $BASE/woff2-dynamic-subset/…, $BASE/latin/…)"
