"""
从伯克希尔·哈撒韦官网抓取巴菲特致股东信，转换为 Markdown 格式。

用法:
    uv run fetch_letters.py              # 抓取全部年份
    uv run fetch_letters.py 2020 2021    # 抓取指定年份
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from functools import reduce

import httpx
import pymupdf
import pymupdf4llm
from bs4 import BeautifulSoup

BASE_URL = "https://www.berkshirehathaway.com/letters"
OUTPUT_DIR = Path(__file__).parent / "letters"

# 1998-2003 的 PDF 文件名不规则
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


def is_table_line(line: str) -> bool:
    """判断是否为表格/财务数据行（大量对齐点号、美元符号、连字符分隔线等）。"""
    stripped = line.strip()
    return bool(
        re.search(r"\.{3,}", stripped)        # 对齐用的点号 ...
        or re.search(r"-{5,}", stripped)       # 分隔线 ------
        or re.search(r"={5,}", stripped)       # 分隔线 ======
        or re.search(r"\$[\s\d,()\-]+\$", stripped)  # 多个金额
        or stripped.count("  ") >= 3           # 大量对齐空格（表格特征）
    )


def merge_short_lines(text: str) -> str:
    """合并 <PRE> 中因固定宽度截断的短行为完整段落。"""
    # 统一换行符
    text = text.replace("\r\n", "\n")
    paragraphs = re.split(r"\n\s*\n", text)
    merged = []
    for para in paragraphs:
        lines = para.strip().splitlines()
        if not lines:
            continue
        # 如果段落中多数行是表格行，保留原格式
        table_lines = sum(1 for l in lines if is_table_line(l))
        if table_lines > len(lines) / 2:
            merged.append(para.strip())
        else:
            merged.append(" ".join(l.strip() for l in lines))
    return "\n\n".join(merged)


def html_to_markdown(text: str) -> str:
    """将 HTML 致股东信转换为干净的 Markdown。"""
    soup = BeautifulSoup(text, "html.parser")

    # 删除 script 标签
    for tag in soup.find_all("script"):
        tag.decompose()

    # 提取 <PRE> 块内容并转为普通文本段落
    for pre in soup.find_all("pre"):
        # 保留 <PRE> 中的 <B>, <I> 等内联标签的文本
        content = pre.get_text()
        # 合并短行
        content = merge_short_lines(content)
        pre.replace_with(BeautifulSoup(f"<div>{content}</div>", "html.parser"))

    # 提取正文文本
    body = soup.find("body")
    if not body:
        body = soup

    parts = []
    for elem in body.children:
        text_content = elem.get_text(strip=True) if hasattr(elem, "get_text") else str(elem).strip()
        if not text_content:
            continue

        # 处理标题（居中粗体通常是标题）
        if hasattr(elem, "name") and elem.name:
            # 检测粗体标题
            bold = elem.find("b") or elem.find("strong")
            if bold and hasattr(bold, "get_text") and bold.get_text(strip=True) == text_content:
                parts.append(f"\n## {text_content}\n")
                continue

        parts.append(text_content)

    return "\n\n".join(parts)


def pdf_to_markdown(raw: bytes) -> str:
    """使用 pymupdf4llm 将 PDF 转换为高质量 Markdown。"""
    doc = pymupdf.open(stream=raw, filetype="pdf")
    md = pymupdf4llm.to_markdown(doc)
    doc.close()
    return strip_page_numbers(md)


def strip_page_numbers(text: str) -> str:
    """移除 PDF 转换后残留的孤立页码。"""
    return re.sub(r"\n\n\d{1,3}\s*\n", "\n", text)


def convert(fetched: FetchedLetter) -> MarkdownLetter:
    if fetched.format == "html":
        content = html_to_markdown(fetched.text)
    else:
        content = pdf_to_markdown(fetched.raw)
    return MarkdownLetter(year=fetched.year, content=content)


def add_frontmatter(letter: MarkdownLetter) -> MarkdownLetter:
    header = f"# Berkshire Hathaway Shareholder Letter {letter.year}\n\n"
    return MarkdownLetter(year=letter.year, content=header + letter.content)


def clean_whitespace(letter: MarkdownLetter) -> MarkdownLetter:
    """清理多余空行。"""
    content = re.sub(r"\n{4,}", "\n\n\n", letter.content)
    return MarkdownLetter(year=letter.year, content=content.strip() + "\n")


def transform(fetched: FetchedLetter) -> MarkdownLetter:
    return reduce(lambda x, f: f(x), [convert, add_frontmatter, clean_whitespace], fetched)


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
