"""
从伯克希尔·哈撒韦官网抓取巴菲特致股东信，转换为 Markdown 格式。

用法:
    uv run fetch_letters.py              # 抓取全部年份
    uv run fetch_letters.py 2020 2021    # 抓取指定年份
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from functools import reduce

import httpx
import pymupdf
from markdownify import markdownify

BASE_URL = "https://www.berkshirehathaway.com/letters"
OUTPUT_DIR = Path(__file__).parent / "letters"

# 1998-2003 的 PDF 文件名不规则，需要硬编码
PDF_FILENAMES: dict[int, str] = {
    1998: "1998pdf.pdf",
    1999: "final1999pdf.pdf",
    2000: "2000pdf.pdf",
    2001: "2001pdf.pdf",
    2002: "2002pdf.pdf",
    2003: "2003ltr.pdf",
}

# --- Data types ---


@dataclass(frozen=True)
class Letter:
    year: int
    url: str
    format: str  # "html" or "pdf"


@dataclass(frozen=True)
class FetchedLetter:
    year: int
    text: str   # decoded text for html
    raw: bytes  # raw bytes for pdf
    format: str


@dataclass(frozen=True)
class MarkdownLetter:
    year: int
    content: str


# --- Pure functions: build letter index ---


def make_letter(year: int) -> Letter:
    if year <= 1997:
        return Letter(year=year, url=f"{BASE_URL}/{year}.html", format="html")
    if year in PDF_FILENAMES:
        return Letter(year=year, url=f"{BASE_URL}/{PDF_FILENAMES[year]}", format="pdf")
    return Letter(year=year, url=f"{BASE_URL}/{year}ltr.pdf", format="pdf")


def build_index(years: list[int]) -> list[Letter]:
    return list(map(make_letter, years))


ALL_YEARS = list(range(1977, 2025))


# --- IO: fetch ---


def fetch_one(client: httpx.Client, letter: Letter) -> FetchedLetter:
    print(f"  fetching {letter.year} ({letter.format})...")
    resp = client.get(letter.url)
    resp.raise_for_status()
    if letter.format == "html":
        return FetchedLetter(year=letter.year, text=resp.text, raw=b"", format="html")
    return FetchedLetter(year=letter.year, text="", raw=resp.content, format="pdf")


# --- Pure functions: convert ---


def strip_ga_script(text: str) -> str:
    """Remove Google Analytics inline script text that leaks into markdown."""
    lines = text.split("\n")
    ga_keywords = {"window.dataLayer", "function gtag", "gtag(", "UA-"}
    cleaned = [l for l in lines if not any(k in l for k in ga_keywords)]
    return "\n".join(cleaned)


def html_to_markdown(text: str) -> str:
    md = markdownify(text, strip=["img", "script"])
    return strip_ga_script(md)


def pdf_to_markdown(raw: bytes) -> str:
    doc = pymupdf.open(stream=raw, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n---\n\n".join(pages)


def convert(fetched: FetchedLetter) -> MarkdownLetter:
    if fetched.format == "html":
        content = html_to_markdown(fetched.text)
    else:
        content = pdf_to_markdown(fetched.raw)
    return MarkdownLetter(year=fetched.year, content=content)


def add_frontmatter(letter: MarkdownLetter) -> MarkdownLetter:
    header = f"# Berkshire Hathaway Shareholder Letter {letter.year}\n\n"
    return MarkdownLetter(year=letter.year, content=header + letter.content)


def transform(fetched: FetchedLetter) -> MarkdownLetter:
    return reduce(lambda x, f: f(x), [convert, add_frontmatter], fetched)


# --- IO: write ---


def write_one(letter: MarkdownLetter) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{letter.year}.md"
    path.write_text(letter.content, encoding="utf-8")
    return path


# --- Pipeline ---


def pipeline(years: list[int]) -> list[Path]:
    index = build_index(years)
    print(f"将抓取 {len(index)} 封致股东信...")

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        fetched = [fetch_one(client, letter) for letter in index]

    converted = list(map(transform, fetched))
    paths = list(map(write_one, converted))

    print(f"完成！已保存 {len(paths)} 个文件到 {OUTPUT_DIR}/")
    return paths


def parse_args(argv: list[str]) -> list[int]:
    if not argv:
        return ALL_YEARS
    return [int(y) for y in argv]


if __name__ == "__main__":
    years = parse_args(sys.argv[1:])
    pipeline(years)
