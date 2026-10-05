"""論文テキストを見出し候補に基づいてセクションへ分割する。"""

from __future__ import annotations

import re
import unicodedata

from paper_ai.models import PaperSection

_NUMBERED_HEADING = re.compile(
    r"^\s*(?:(?:\d+|[IVXLC]+)(?:\.(?:\d+|[IVXLC]+))*[.)]?\s+|\d+[.)]\s*)"
    r"(?P<title>\S.*)$",
    re.IGNORECASE,
)
_REFERENCES = {
    "references",
    "reference",
    "bibliography",
    "works cited",
    "literature cited",
    "参考文献",
}
_COMMON_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "methods",
    "method",
    "methodology",
    "materials and methods",
    "experimental methods",
    "results",
    "discussion",
    "results and discussion",
    "conclusion",
    "conclusions",
    "acknowledgements",
    "acknowledgments",
    "appendix",
}
_TRAILING_PAGE = re.compile(r"\s+\d{1,4}\s*$")


def _title_text(line: str) -> tuple[str, bool]:
    """見出し候補のタイトルと番号付きかどうかを返す。"""
    numbered = _NUMBERED_HEADING.match(line)
    if numbered:
        return numbered.group("title").strip(), True
    return _TRAILING_PAGE.sub("", line).strip(), False


def _canonical(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    normalized = re.sub(r"^[\W_]+|[\W_]+$", "", normalized)
    return re.sub(r"\s+", " ", normalized)


def _looks_like_heading(line: str) -> bool:
    title, numbered = _title_text(line)
    canonical = _canonical(title)
    words = title.split()
    if not title or len(title) > 100 or len(words) > 12:
        return False
    if canonical in _REFERENCES or canonical in _COMMON_HEADINGS:
        return True
    if numbered:
        return True
    if title.endswith((".", ",", ";", ":", "?", "!")):
        return False

    # テキスト抽出ではフォントサイズ等が失われるため、短い単独行の
    # 大文字・タイトルケースを体裁上の手掛かりにする。
    letters = [char for char in title if char.isalpha()]
    if not letters:
        return False
    if len(letters) >= 3 and all(char.isupper() for char in letters):
        return True
    if not any(char.isascii() and char.isalpha() for char in letters):
        return len(title) <= 30 and not any(char in title for char in "。！？；，")
    return all(word[:1].isupper() for word in words if word[:1].isalpha())


def _is_references_title(title: str) -> bool:
    canonical = _canonical(title)
    return canonical in _REFERENCES or canonical.startswith(
        ("references ", "bibliography ", "works cited ", "literature cited ")
    )


def split_sections(text: str) -> list[PaperSection]:
    """見出しらしい行で分割し、見出しと本文を保持する。

    見出しの番号形式や表記に固定のテンプレートは要求しない。
    認識できる見出しがない場合は、全文を単一セクションとして返す。
    """
    sections: list[PaperSection] = []
    current_title = "本文"
    current_lines: list[str] = []
    references_started = False

    def append_section() -> None:
        content = "\n".join(current_lines).strip()
        if content or current_title != "本文":
            sections.append(
                PaperSection(
                    title=current_title,
                    text=content,
                    translatable=not references_started,
                )
            )

    for line in text.splitlines():
        candidate = line.strip()
        if candidate and not references_started and _looks_like_heading(candidate):
            title, _numbered = _title_text(candidate)
            append_section()
            current_title = title
            current_lines = []
            if _is_references_title(title):
                references_started = True
            continue
        current_lines.append(line)

    append_section()
    return sections
