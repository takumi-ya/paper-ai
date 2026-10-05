"""PDFのページテキストを抽出する。"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import fitz

from paper_ai.models import Paper, PaperPage
from paper_ai.pdf.section import split_sections

_PAGE_NUMBER = re.compile(r"^\s*(?:[-–—]\s*)?\d{1,4}(?:\s*[-–—])?\s*$")
_SPACE = re.compile(r"\s+")


class PDFParseError(ValueError):
    """PDFにテキストがなく、解析を続けられない場合のエラー。"""


def _normalized_line(line: str) -> str:
    return _SPACE.sub(" ", line).strip().casefold()


def _page_text_lines(page: fitz.Page) -> tuple[list[str], set[str]]:
    """ページ本文と、ページ端にある短い行を返す。"""
    edge_lines: set[str] = set()
    lines: list[str] = []
    height = page.rect.height

    for block in page.get_text("blocks", sort=True):
        x0, y0, _x1, y1, raw_text = block[:5]
        block_lines = raw_text.splitlines()
        lines.extend(block_lines)
        if y0 <= height * 0.1 or y1 >= height * 0.9:
            for line in block_lines:
                normalized = _normalized_line(line)
                if normalized and len(normalized) <= 100:
                    edge_lines.add(normalized)

    return lines, edge_lines


def parse_pdf(path: str | Path) -> Paper:
    """PDFを読み込み、ページ・全文・セクションを返す。

    ページ端で繰り返す短い行と単独のページ番号を除去する。
    画像だけで構成されたページはOCRせず、抽出テキストが空のまま保持する。
    """
    source = Path(path)
    page_lines: list[list[str]] = []
    edge_lines_by_page: list[set[str]] = []

    with fitz.open(source) as document:
        for page in document:
            lines, edge_lines = _page_text_lines(page)
            page_lines.append(lines)
            edge_lines_by_page.append(edge_lines)

    page_count = len(page_lines)
    repeated_threshold = max(2, math.ceil(page_count * 0.6))
    edge_counts = Counter(
        line for page_edges in edge_lines_by_page for line in page_edges
    )
    repeated_edge_lines = {
        line for line, count in edge_counts.items() if count >= repeated_threshold
    }

    pages: list[PaperPage] = []
    for index, lines in enumerate(page_lines, start=1):
        cleaned = [
            line
            for line in lines
            if _normalized_line(line) not in repeated_edge_lines
            and not _PAGE_NUMBER.fullmatch(line)
        ]
        pages.append(PaperPage(number=index, text="\n".join(cleaned).strip()))

    full_text = "\n\n".join(page.text for page in pages if page.text)
    if not full_text:
        raise PDFParseError(f"PDFからテキストを抽出できませんでした: {source}")

    return Paper(
        source=source,
        text=full_text,
        pages=tuple(pages),
        sections=tuple(split_sections(full_text)),
    )
