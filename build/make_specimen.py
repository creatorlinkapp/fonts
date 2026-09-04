#!/usr/bin/env python3
"""스펙 비교 페이지 생성.
  dist/specimen.html            → 상대경로(다이나믹 서브셋 청크 로딩 확인용, http 서버 필요)
  out/specimen-embedded.html    → 폰트 data URI 임베드(단일 파일, Artifact 게시용)
"""
import os, io, json, base64
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist"); OUT = os.path.join(ROOT, "out"); os.makedirs(OUT, exist_ok=True)
FAMILY = "CreatorlinkSansKR"
WEIGHTS = {400: "Regular", 500: "Medium", 700: "Bold"}
KO_RANGES = json.load(open(os.path.join(ROOT, "src/ko_ranges.json")))
LATIN_RANGE = "U+30-39, U+41-5A, U+61-7A, U+C0-24F"

def face(fam, w, src, rng=None):
    r = f"\n  unicode-range: {rng};" if rng else ""
    return f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:block;src:url('{src}') format('woff2');{r}}}\n"

def b64(path):
    return "data:font/woff2;base64," + base64.b64encode(open(path, "rb").read()).decode()

def full_woff2(flavor, style):
    """dist/<flavor>/full/*.otf|ttf → woff2 bytes (임베드용 단일 파일)"""
    p = os.path.join(DIST, flavor, "full", f"{FAMILY}-{style}.{flavor}")
    f = TTFont(p); f.flavor = "woff2"; buf = io.BytesIO(); f.save(buf)
    return "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode()

def raw_woff2(style):
    """힌트 없는 Pretendard 원본 → 비교용 (dist/reference/)"""
    os.makedirs(os.path.join(DIST, "reference"), exist_ok=True)
    out = os.path.join(DIST, "reference", f"Pretendard-unhinted-{style}.woff2")
    if not os.path.exists(out):
        f = TTFont(os.path.join(ROOT, "src/pretendard/public/static", f"Pretendard-{style}.otf")); f.flavor = "woff2"; f.save(out)
    return out

def fontface_css(embed):
    css = []
    for w, s in WEIGHTS.items():
        p = raw_woff2(s)
        css.append(face("CL-raw", w, b64(p) if embed else f"./reference/{os.path.basename(p)}"))
    for flavor in ("otf", "ttf"):
        for w, s in WEIGHTS.items():
            if embed:
                css.append(face(f"CL-{flavor}", w, full_woff2(flavor, s)))
            else:
                for i, rng in enumerate(KO_RANGES):
                    css.append(face(f"CL-{flavor}", w, f"./{flavor}/woff2-dynamic-subset/{FAMILY}-{s}.subset.{i}.woff2", rng))
    for p in ("Roboto", "Inter"):
        for w, s in WEIGHTS.items():
            path = os.path.join(DIST, "latin", f"{FAMILY}-Latin-{p}-{s}.woff2")
            css.append(face(f"CL-latin-{p.lower()}", w, b64(path) if embed else f"./latin/{FAMILY}-Latin-{p}-{s}.woff2", LATIN_RANGE))
    return "".join(css)

def sizes():
    d = {}
    for flavor in ("otf", "ttf"):
        tot = sum(os.path.getsize(os.path.join(DIST, flavor, "woff2-dynamic-subset", f)) for f in os.listdir(os.path.join(DIST, flavor, "woff2-dynamic-subset")))
        d[flavor] = tot
    d["latin"] = {p: os.path.getsize(os.path.join(DIST, "latin", f"{FAMILY}-Latin-{p}-Regular.woff2")) for p in ("Roboto", "Inter")}
    return d

TEMPLATE = open(os.path.join(ROOT, "specimen.template.html"), encoding="utf-8").read()

def render(embed):
    sz = sizes()
    html = (TEMPLATE
            .replace("/*FONTFACE*/", fontface_css(embed))
            .replace("{{MODE}}", "임베드 (단일 파일)" if embed else "다이나믹 서브셋 (청크 로딩)")
            .replace("{{SZ_OTF}}", f"{sz['otf']/1024/3:.0f}").replace("{{SZ_TTF}}", f"{sz['ttf']/1024/3:.0f}")
            .replace("{{SZ_ROBOTO}}", f"{sz['latin']['Roboto']/1024:.0f}").replace("{{SZ_INTER}}", f"{sz['latin']['Inter']/1024:.0f}"))
    return html

if __name__ == "__main__":
    doc = render(False)
    open(os.path.join(DIST, "specimen.html"), "w", encoding="utf-8").write(
        '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        + doc.split("<!--HEAD-END-->")[0] + "</head>\n<body>\n" + doc.split("<!--HEAD-END-->")[1] + "\n</body>\n</html>\n")
    open(os.path.join(OUT, "specimen-embedded.html"), "w", encoding="utf-8").write(render(True).replace("<!--HEAD-END-->", ""))
    print("ok", os.path.getsize(os.path.join(OUT, "specimen-embedded.html")) // 1024, "KB embedded")
