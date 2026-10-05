"""PDF抽出とセクション分割の単体テスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from paper_ai.pdf import PDFParseError, parse_pdf, split_sections


class SectionSplitTests(unittest.TestCase):
    def test_accepts_varied_heading_styles_and_excludes_references(self) -> None:
        text = """概要
全体の導入文。
1. Introduction
導入の本文。
Research Design
設計の本文。
RESULTS AND DISCUSSION
結果の本文。
References
文献一覧。
"""

        sections = split_sections(text)

        self.assertEqual(
            [section.title for section in sections],
            ["概要", "Introduction", "Research Design", "RESULTS AND DISCUSSION", "References"],
        )
        self.assertTrue(all(section.translatable for section in sections[:-1]))
        self.assertFalse(sections[-1].translatable)
        self.assertEqual(sections[-1].text, "文献一覧。")

    def test_text_without_detectable_headings_is_preserved(self) -> None:
        text = "この文書には見出しらしい行がありません。\n本文を保持します。"

        sections = split_sections(text)

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].text, text)


class PDFParserTests(unittest.TestCase):
    def _write_pdf(self, path: Path, pages: list[list[tuple[float, float, str]]]) -> None:
        document = fitz.open()
        for page_items in pages:
            page = document.new_page(width=612, height=792)
            for x, y, text in page_items:
                page.insert_text((x, y), text, fontsize=11)
        document.save(path)
        document.close()

    def test_extracts_pages_and_removes_repeated_edges_in_two_column_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "two-column.pdf"
            self._write_pdf(
                path,
                [
                    [
                        (40, 24, "Journal of Example Studies"),
                        (40, 90, "1 Introduction"),
                        (40, 130, "Left column text."),
                        (320, 130, "Right column text."),
                        (300, 770, "1"),
                    ],
                    [
                        (40, 24, "Journal of Example Studies"),
                        (40, 90, "2 Methods"),
                        (40, 130, "Second page left."),
                        (320, 130, "Second page right."),
                        (300, 770, "2"),
                    ],
                ],
            )

            paper = parse_pdf(path)

        self.assertEqual(len(paper.pages), 2)
        self.assertEqual([page.number for page in paper.pages], [1, 2])
        self.assertIn("Left column text.", paper.text)
        self.assertIn("Right column text.", paper.text)
        self.assertNotIn("Journal of Example Studies", paper.text)
        self.assertNotIn("\n1\n", paper.text)
        self.assertEqual([section.title for section in paper.sections], ["Introduction", "Methods"])

    def test_parses_a_second_document_with_different_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "different-format.pdf"
            self._write_pdf(
                path,
                [[
                    (60, 80, "OVERVIEW"),
                    (60, 120, "A short overview."),
                    (60, 170, "Experimental Setup"),
                    (60, 210, "The setup details."),
                    (60, 260, "Bibliography"),
                    (60, 300, "Source list."),
                ]],
            )

            paper = parse_pdf(path)

        self.assertEqual(len(paper.pages), 1)
        self.assertEqual([section.title for section in paper.sections], ["OVERVIEW", "Experimental Setup", "Bibliography"])
        self.assertFalse(paper.sections[-1].translatable)

    def test_rejects_pdf_without_extractable_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "empty.pdf"
            document = fitz.open()
            document.new_page()
            document.save(path)
            document.close()

            with self.assertRaises(PDFParseError):
                parse_pdf(path)


if __name__ == "__main__":
    unittest.main()
