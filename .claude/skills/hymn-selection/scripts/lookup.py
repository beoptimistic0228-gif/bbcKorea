#!/usr/bin/env python3
"""찬송 선곡 추천 보조 도구.

두 가지 반복 조회를 자동화한다(추천 근거를 빠르고 정확하게 확보하기 위함):
  1) 찬송 번호 → 제목·분류  (침례교찬송가_가사DB_마스터.md / 색인.csv)
  2) 본문 책(±장) → 과거 실제 선곡 실적  (설교_찬송_실적.csv = '정답지')

사용법:
  python lookup.py --hymns 59,179,402
  python lookup.py --book 로마서
  python lookup.py --book 로마서 --chapter 8
  python lookup.py --book 열왕기상 --chapter 17 --hymns 80,500,435,359

저장소 루트는 '02_성경_흠정역' 폴더를 위로 탐색해 자동으로 찾는다.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

# 원문 한글이 깨지거나 인코딩 에러로 죽지 않도록 출력 스트림을 UTF-8로 고정.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "02_성경_흠정역").is_dir() and (p / "03_찬송가").is_dir():
            return p
    raise SystemExit("저장소 루트를 찾지 못했습니다(02_성경_흠정역/03_찬송가 폴더 기준).")


ROOT = find_repo_root(Path(__file__).resolve())
MASTER = ROOT / "03_찬송가" / "침례교찬송가_가사DB_마스터.md"
INDEX = ROOT / "03_찬송가" / "침례교찬송가_색인.csv"
RECORD = ROOT / "04_예배기록" / "설교_찬송_실적.csv"


def load_hymn_info():
    """번호 -> (제목, 분류). 마스터 md가 기준, 색인은 제목 보강."""
    info = {}
    if MASTER.exists():
        cur = ""
        for line in MASTER.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s*분류[:：]\s*(.+)", line)
            if m:
                cur = re.sub(r"\s*\(계속\)", "", m.group(1).strip())
                continue
            m = re.match(r"^\*\*(\d+)\.\s*(.+?)\*\*", line)
            if m:
                info[m.group(1)] = (m.group(2).strip(), cur)
    if INDEX.exists():
        with INDEX.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                num = (r.get("번호") or "").strip()
                title = (r.get("제목") or "").strip()
                if num and num not in info:
                    info[num] = (title, "?")
    return info


def show_hymns(nums, info):
    print("=== 찬송 번호 조회 ===")
    for n in nums:
        n = n.strip()
        if not n:
            continue
        title, cat = info.get(n, ("(색인에 없음 — 확인 필요)", "?"))
        print(f"  {n:>3}  {title}  〔{cat}〕")
    print()


def load_records():
    if not RECORD.exists():
        return []
    with RECORD.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def book_of(passage: str) -> str:
    passage = (passage or "").strip()
    if not passage:
        return ""
    first = passage.split()[0]
    return re.split(r"[0-9]", first)[0]


def chapter_of(passage: str):
    m = re.search(r"(\d+)\s*:", passage or "")
    return int(m.group(1)) if m else None


def show_records(book, chapter, info, rows):
    print(f"=== 과거 실적 조회: '{book}'" + (f" {chapter}장" if chapter else "") + " ===")
    hits = []
    for r in rows:
        if book_of(r.get("본문", "")) != book:
            continue
        if chapter is not None:
            ch = chapter_of(r.get("본문", ""))
            if ch is None or abs(ch - chapter) > 1:  # 같은/인접 장
                continue
        hits.append(r)
    if not hits:
        print("  (해당 책/장의 과거 실적 없음 → 주제매칭으로 추천)\n")
        return
    hits.sort(key=lambda r: r.get("날짜", ""))

    def label(n):
        n = (n or "").strip()
        if not n:
            return ""
        t, c = info.get(n, ("?", "?"))
        return f"{n} {t}〔{c}〕"

    for r in hits:
        am = " / ".join(label(x) for x in r.get("오전찬송", "").split(";") if x.strip())
        print(f"  [{r.get('날짜','')}] {r.get('본문','')}  ({r.get('설교제목','')})")
        print(f"      오전 : {am}")
        print(f"      헌금 : {label(r.get('헌금찬송',''))}")
        print(f"      마무리: {label(r.get('마무리찬송',''))}")
        if r.get("비고", "").strip():
            print(f"      비고 : {r.get('비고')}")
    print(f"\n  → {len(hits)}건. ※개별 행은 기입오류/당일수정 노이즈 가능 — 참고용, 패턴을 신뢰.\n")


def main():
    ap = argparse.ArgumentParser(description="찬송 선곡 추천 보조 조회")
    ap.add_argument("--hymns", help="쉼표로 구분한 찬송 번호 (예: 59,179,402)")
    ap.add_argument("--book", help="본문 책 이름 (예: 로마서, 열왕기상)")
    ap.add_argument("--chapter", type=int, help="장 번호(있으면 같은/인접 장만)")
    args = ap.parse_args()

    if not args.hymns and not args.book:
        ap.print_help()
        sys.exit(0)

    info = load_hymn_info()
    if args.book:
        show_records(args.book.strip(), args.chapter, info, load_records())
    if args.hymns:
        show_hymns(args.hymns.split(","), info)


if __name__ == "__main__":
    main()
