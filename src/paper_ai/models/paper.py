"""PDF論文と抽出結果を表すデータモデル。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PaperPage:
    """PDFの1ページ分の抽出結果。ページ番号は1始まり。"""

    number: int
    text: str


@dataclass(frozen=True, slots=True)
class PaperSection:
    """論文のセクション。"""

    title: str
    text: str
    translatable: bool = True


@dataclass(frozen=True, slots=True)
class Paper:
    """PDFから抽出した論文全体。"""

    source: Path
    text: str
    pages: tuple[PaperPage, ...]
    sections: tuple[PaperSection, ...]
