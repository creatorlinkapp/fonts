#!/usr/bin/env python3
"""
CreatorlinkSansKR 빌드 스크립트
================================
Pretendard(OFL) 를 베이스로 웹빌더용 자체 폰트를 만든다.

  1. name 테이블 리네이밍  (Pretendard → CreatorlinkSansKR, RFN 회피)
  2. 수직 메트릭 통일      (hhea = typo = win, USE_TYPO_METRICS on)
  3. TTF 계열엔 gasp 추가   (Windows GDI 안티앨리어싱 강제)
  4. 다이나믹 서브셋 92청크 (Pretendard 공식 unicode-range 재사용) → woff2 (힌트 유지)
  0. (사전 단계) 힌팅 — OTF: otfautohint + 라틴/한글 별도 FDDict(fontinfo), TTF: ttfautohint. Noto Sans KR(=플로우 FlowSansKR)과 같은 방식
  5. 라틴 파트너(Roboto / Inter)를 같은 메트릭으로 맞춰 letters+digits 전용 woff2 생성
  6. @font-face CSS 생성    (한글 청크 → 라틴 파트너 순서, alias 포함)

사용:  python3 build_font.py [--flavor otf|ttf|both] [--jobs N]
"""
import argparse, json, os, sys, shutil, io
from concurrent.futures import ProcessPoolExecutor
from fontTools.ttLib import TTFont, newTable
from fontTools import subset

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")

FAMILY = "CreatorlinkSansKR"
VENDOR = "Creatorlink"
VERSION = "1.000"
WEIGHTS = {400: "Regular", 500: "Medium", 700: "Bold"}

# 베이스 폰트 소스 (Pretendard 1.3.9)
BASE_RAW = {
    "otf": os.path.join(SRC, "pretendard/public/static/Pretendard-{style}.otf"),
    "ttf": os.path.join(SRC, "pretendard/public/static/alternative/Pretendard-{style}.ttf"),
}
# 힌팅된 소스 (없으면 hint_sources() 가 만든다)
BASE = {
    "otf": os.path.join(SRC, "hinted/Pretendard-{style}.otf"),
    "ttf": os.path.join(SRC, "hinted/Pretendard-{style}.ttf"),
}
# 라틴 파트너 폰트 (원본 TTF)
LATIN = {
    "roboto": os.path.join(SRC, "roboto-hinted/Roboto-{style}.ttf"),   # Google Fonts 힌팅판 (플로우가 쓰는 것과 동일 빌드)
    "inter":  os.path.join(SRC, "inter/extras/ttf/Inter-{style}.ttf"),
}
# 라틴 파트너가 담당할 범위: 영문 대소문자 + 숫자 + 라틴 확장 (문장부호는 한글 폰트가 담당 → 플로우와 동일)
LATIN_RANGE = "U+30-39, U+41-5A, U+61-7A, U+C0-24F"

# Pretendard 기준 메트릭 (2048 upm). 모든 파트너 폰트를 여기에 맞춘다 → line-height: normal 이 흔들리지 않음
METRICS = dict(asc=1949, desc=-494, gap=0)

KO_RANGES = json.load(open(os.path.join(SRC, "ko_ranges.json")))  # 92 chunks, [0]=희귀 … [91]=기본 라틴/자주 쓰는 한글


# ---------------------------------------------------------------- hinting (사전 단계)
def hint_sources(jobs):
    """Pretendard 원본엔 스템 힌트가 전혀 없다(BlueValues 만 존재). Windows DPR1 에서 흐릿한 원인.
    OTF: otfautohint + fontinfo(라틴/한글 FDDict 분리)  — Source Han Sans / Noto Sans KR 과 같은 방식
    TTF: ttfautohint (라틴 정식 힌팅, 한글은 fallback 스크립트로 수평 스템 정렬)"""
    import subprocess
    os.makedirs(os.path.join(SRC, "hinted"), exist_ok=True)
    os.makedirs(os.path.join(SRC, "fontinfo"), exist_ok=True)
    for w, s in WEIGHTS.items():
        out = BASE["otf"].format(style=s)
        if not os.path.exists(out):
            fi = os.path.join(SRC, "fontinfo", f"fontinfo-{s}")
            subprocess.run([sys.executable, os.path.join(ROOT, "make_fontinfo.py"), BASE_RAW["otf"].format(style=s), fi], check=True)
            print(f"[hint] otfautohint {s} …", flush=True)
            subprocess.run(["otfautohint", "-p", str(jobs), "--fontinfo-file", fi, "-o", out, BASE_RAW["otf"].format(style=s)], check=True)
        out = BASE["ttf"].format(style=s)
        if not os.path.exists(out):
            print(f"[hint] ttfautohint {s} …", flush=True)
            from ttfautohint import ttfautohint
            ttfautohint(in_file=BASE_RAW["ttf"].format(style=s), out_file=out,
                        fallback_script="latn", windows_compatibility=True, hinting_range_min=8, hinting_range_max=50,
                        hinting_limit=200, no_info=True)


def split_fds(font, style):
    """otfautohint 는 FDDict 별로 힌트를 계산하지만 단일 FD 폰트엔 존을 하나의 BlueValues 로 합쳐 쓴다.
    합친 BlueValues 는 첫 쌍만 베이스라인으로 취급되므로 라틴 베이스라인 [-22,0] 이 '상단 존'이 되어 버린다.
    → Source Han Sans 처럼 FDArray 를 라틴/한글 2개로 분리하고 각자 존·스템 폭을 갖게 한다."""
    import copy
    sys.path.insert(0, ROOT)
    from make_fontinfo import measure
    hangul, latin, hg, names = measure(BASE_RAW["otf"].format(style=style))
    cff = font["CFF "].cff; td = cff.topDictIndex[0]
    if len(td.FDArray) != 1:
        return
    fd_lat = td.FDArray[0]
    fd_han = copy.deepcopy(fd_lat)
    pl, ph = fd_lat.Private, fd_han.Private
    pl.BlueValues = [latin["base"] + latin["base_over"], latin["base"], latin["lc"], latin["lc"] + latin["lc_over"], latin["cap"], latin["cap"] + latin["cap_over"]]
    pl.StdHW, pl.StdVW = latin["H"], latin["V"]
    ph.BlueValues = [hangul["base"] + hangul["base_over"], hangul["base"], hangul["top"], hangul["top"] + hangul["top_over"]]
    ph.StdHW, ph.StdVW = hangul["H"], hangul["V"]
    for k in ("OtherBlues", "StemSnapH", "StemSnapV"):
        for pdict in (pl, ph):
            if hasattr(pdict, k): delattr(pdict, k)
    fd_han.FontName = fd_lat.FontName + "-Hangul"
    fd_lat.FontName = fd_lat.FontName + "-Latin"
    td.FDArray.append(fd_han)
    hset = set(hg); order = font.getGlyphOrder()
    td.FDSelect.gidArray = [1 if g in hset else 0 for g in order]
    td.FDSelect.format = 3


# ---------------------------------------------------------------- name / metrics
def set_names(font, family, style, weight, note):
    name = font["name"]
    ps = f"{family.replace(' ', '')}-{style}"   # PostScript 이름엔 공백 불가
    full = f"{family} {style}"
    # 기존 Pretendard 명칭이 들어간 레코드 제거 (RFN 회피), 라이선스(13,14)/저작권(0)은 유지
    for rec in list(name.names):
        if rec.nameID in (1, 2, 3, 4, 5, 6, 16, 17, 18, 21, 22):
            name.names.remove(rec)
    copyright_old = name.getDebugName(0) or ""
    name.setName(f"{copyright_old}\n{note}", 0, 3, 1, 0x409)
    # 웨이트별 style-linked 이름: Medium 은 subfamily 'Regular'가 아니라 별도 family 이름을 쓰는 게 표준
    if style in ("Regular", "Bold"):
        fam1, sub2 = family, style
    else:
        fam1, sub2 = f"{family} {style}", "Regular"
    for pid, eid, lid in ((3, 1, 0x409), (1, 0, 0)):
        name.setName(fam1, 1, pid, eid, lid)
        name.setName(sub2, 2, pid, eid, lid)
        name.setName(f"{VENDOR};{ps}", 3, pid, eid, lid)
        name.setName(full, 4, pid, eid, lid)
        name.setName(f"Version {VERSION}", 5, pid, eid, lid)
        name.setName(ps, 6, pid, eid, lid)
        name.setName(family, 16, pid, eid, lid)
        name.setName(style, 17, pid, eid, lid)
    os2 = font["OS/2"]
    os2.usWeightClass = weight
    os2.achVendID = "CRLK"
    # fsSelection: REGULAR / BOLD 비트 정리
    os2.fsSelection &= ~(1 << 0 | 1 << 5 | 1 << 6)
    if style == "Bold":
        os2.fsSelection |= 1 << 5
    else:
        os2.fsSelection |= 1 << 6
    font["head"].macStyle = (1 << 0) if style == "Bold" else 0


def set_metrics(font):
    """hhea / OS2 typo / OS2 win 을 동일하게 맞추고 USE_TYPO_METRICS 켜기.
    upm 이 다르면 비율로 환산. win 값은 글리프 bbox 를 덮도록 보정(Windows 클리핑 방지)."""
    upm = font["head"].unitsPerEm
    scale = upm / 2048
    asc, desc, gap = (round(METRICS["asc"] * scale), round(METRICS["desc"] * scale), 0)
    hhea, os2, head = font["hhea"], font["OS/2"], font["head"]
    hhea.ascent, hhea.descent, hhea.lineGap = asc, desc, gap
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = asc, desc, gap
    os2.usWinAscent = max(asc, head.yMax)
    os2.usWinDescent = max(-desc, -head.yMin)
    os2.fsSelection |= 1 << 7  # USE_TYPO_METRICS
    os2.version = max(os2.version, 4)


def add_gasp(font):
    """힌팅 없는 TTF 에 gasp 테이블을 넣어 Windows GDI/DirectWrite 에서 모든 크기에 그레이스케일+대칭 스무딩 적용."""
    if "glyf" not in font:
        return
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000F}  # GRIDFIT | DOGRAY | SYMMETRIC_GRIDFIT | SYMMETRIC_SMOOTHING
    font["gasp"] = gasp


# ---------------------------------------------------------------- subset → woff2
def subset_to_woff2(font_bytes, unicode_range, out_path, keep_hinting=True):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]          # tnum, pnum, ss01…, kern 등 모든 피처 유지
    opts.name_IDs = ["*"]
    opts.name_legacy = True
    opts.notdef_outline = True
    opts.hinting = keep_hinting
    opts.desubroutinize = True            # CFF 서브루틴 해제 → woff2 압축률 ↑, 브라우저 파싱 ↓
    opts.drop_tables += ["DSIG"]
    font = TTFont(io.BytesIO(font_bytes))
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=subset.parse_unicodes(unicode_range.replace("U+", "").replace(" ", "")))
    sub.subset(font)
    font.flavor = "woff2"
    font.save(out_path)
    return os.path.getsize(out_path)


def _chunk_job(args):
    font_bytes, rng, out_path = args
    return subset_to_woff2(font_bytes, rng, out_path)


def build_base(flavor, weight, style, jobs):
    src = BASE[flavor].format(style=style)
    font = TTFont(src)
    set_names(font, FAMILY, style, weight,
              f"{FAMILY} is derived from Pretendard (c) 2021 Kil Hyung-jin, licensed under SIL OFL 1.1. Modified by {VENDOR}.")
    set_metrics(font)
    if flavor == "otf":
        split_fds(font, style)
    if flavor == "ttf" and "gasp" not in font:   # ttfautohint 가 만든 gasp 가 있으면 존중
        add_gasp(font)
    buf = io.BytesIO(); font.save(buf); font_bytes = buf.getvalue()

    out_dir = os.path.join(DIST, flavor, "woff2-dynamic-subset")
    os.makedirs(out_dir, exist_ok=True)
    # 참고용 풀 폰트도 저장
    full_dir = os.path.join(DIST, flavor, "full")
    os.makedirs(full_dir, exist_ok=True)
    with open(os.path.join(full_dir, f"{FAMILY}-{style}.{flavor}"), "wb") as f:
        f.write(font_bytes)

    jobs_list = [(font_bytes, rng, os.path.join(out_dir, f"{FAMILY}-{style}.subset.{i}.woff2"))
                 for i, rng in enumerate(KO_RANGES)]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        sizes = list(ex.map(_chunk_job, jobs_list))
    print(f"[{flavor}] {style}: {len(sizes)} chunks, total {sum(sizes)/1024:.0f} KB, "
          f"max {max(sizes)/1024:.0f} KB (chunk {sizes.index(max(sizes))})", flush=True)


def build_latin(partner, weight, style):
    src = LATIN[partner].format(style=style)
    font = TTFont(src)
    set_names(font, f"{FAMILY} Latin {partner.title()}", style, weight,
              f"Latin companion for {FAMILY}, derived from {partner.title()}. Vertical metrics harmonized with {FAMILY}.")
    set_metrics(font)
    if "gasp" not in font:
        add_gasp(font)
    buf = io.BytesIO(); font.save(buf)
    out_dir = os.path.join(DIST, "latin")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{FAMILY}-Latin-{partner.title()}-{style}.woff2")
    size = subset_to_woff2(buf.getvalue(), LATIN_RANGE, out)
    print(f"[latin] {partner} {style}: {size/1024:.0f} KB", flush=True)


# ---------------------------------------------------------------- CSS
HEADER = f"""/*
{FAMILY} — derived from Pretendard (c) 2021 Kil Hyung-jin (SIL OFL 1.1, https://github.com/orioncactus/pretendard)
Latin companions derived from Roboto (Apache 2.0) / Inter (SIL OFL 1.1). Vertical metrics harmonized.

사용법:  font-family: '{FAMILY}', sans-serif;
  · 한글/기호는 {FAMILY} 청크(92개, 필요한 것만 다운로드), 영문·숫자는 라틴 파트너가 담당 (unicode-range)
  · 고정폭 숫자:  font-feature-settings: "tnum";   (또는 font-variant-numeric: tabular-nums)
*/
"""

def css_face(family, weight, src, unicode_range, comment=None, display="swap"):
    c = f"/* {comment} */\n" if comment else ""
    return (f"{c}@font-face {{\n  font-family: '{family}';\n  font-style: normal;\n  font-weight: {weight};\n"
            f"  font-display: {display};\n  src: url('{src}') format('woff2');\n  unicode-range: {unicode_range};\n}}\n")

def write_css(flavor, partner):
    lines = [HEADER]
    families = [FAMILY, "Pretendard", "Noto Sans KR"]  # alias: 기존 템플릿 호환
    for family in families:
        lines.append(f"\n/* ===== {family}{' (alias → ' + FAMILY + ')' if family != FAMILY else ''} ===== */\n")
        for weight, style in WEIGHTS.items():
            for i, rng in enumerate(KO_RANGES):
                lines.append(css_face(family, weight, f"./{flavor}/woff2-dynamic-subset/{FAMILY}-{style}.subset.{i}.woff2", rng,
                                      comment=f"[{i}] {style}" if i in (0, 91) else None))
            # 라틴 파트너는 같은 family 이름으로 '마지막에' 선언 → 겹치는 범위(영문/숫자)에서 이 face 가 우선
            lines.append(css_face(family, weight, f"./latin/{FAMILY}-Latin-{partner.title()}-{style}.woff2", LATIN_RANGE,
                                  comment=f"Latin companion ({partner}) {style} — letters/digits override"))
    path = os.path.join(DIST, f"creatorlink-sans-kr.{flavor}.{partner}.css")
    open(path, "w").write("".join(lines))
    print("css →", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flavor", default="both", choices=["otf", "ttf", "both"])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--skip-base", action="store_true")
    a = ap.parse_args()
    flavors = ["otf", "ttf"] if a.flavor == "both" else [a.flavor]
    if not a.skip_base:
        hint_sources(a.jobs)
    if not a.skip_base:
        for fl in flavors:
            for w, s in WEIGHTS.items():
                build_base(fl, w, s, a.jobs)
    for p in LATIN:
        for w, s in WEIGHTS.items():
            build_latin(p, w, s)
    for fl in flavors:
        for p in LATIN:
            write_css(fl, p)
    shutil.copy(os.path.join(SRC, "pretendard/LICENSE.txt"), os.path.join(DIST, "LICENSE-Pretendard.txt")) \
        if os.path.exists(os.path.join(SRC, "pretendard/LICENSE.txt")) else None


if __name__ == "__main__":
    main()
