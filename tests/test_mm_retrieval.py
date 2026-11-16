"""Pure-Python tests for the multimodal index / retrieval helpers (no model, no DB, no PDF)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.eval_retrieval import complete, cover, supports  # noqa: E402
from src.mm.index import _split, parse_pages, unverified_numbers  # noqa: E402
from src.mm.layout import Block, pad, table_rows, union  # noqa: E402
from src.retrieval import BM25, tokenize  # noqa: E402


class TokenizeTest(unittest.TestCase):
    def test_numbers_kept_whole_and_diacritics_kept(self):
        toks = tokenize("Doanh thu 2023 đạt 52.618 tỷ, tăng 11,6%")
        self.assertIn("52.618", toks)
        self.assertIn("11,6%", toks)
        self.assertIn("đạt", toks)
        self.assertNotIn("và", tokenize("doanh thu và lợi nhuận"))

    def test_bigrams_skip_numbers(self):
        toks = tokenize("lợi nhuận 2025", bigrams=True)
        self.assertIn("lợi_nhuận", toks)
        self.assertFalse(any("2025_" in t or "_2025" in t for t in toks))


class BM25Test(unittest.TestCase):
    def test_exact_number_ranks_first(self):
        docs = [tokenize(t) for t in ("doanh thu 52.618 tỷ", "doanh thu 44.010 tỷ", "lợi nhuận sau thuế")]
        s = BM25(docs).scores(tokenize("doanh thu 52.618"))
        self.assertEqual(max(range(3), key=lambda i: s[i]), 0)
        self.assertEqual(s[2], 0.0)


class TableRowsTest(unittest.TestCase):
    def test_cells_in_separate_blocks_are_regrouped_by_row(self):
        # unruled table: label column and two value columns extracted as separate blocks
        labels = Block("b0", (250, 100, 400, 140), ["Lãi vay phải trả", "Khác"], 9,
                       [(250, 100, 330, 110), (250, 130, 280, 140)])
        col1 = Block("b1", (450, 100, 520, 140), ["85.922", "1.316.399"], 9,
                     [(450, 100, 520, 110), (450, 130, 520, 140)])
        col2 = Block("b2", (560, 100, 630, 140), ["93.317", "831.648"], 9,
                     [(560, 100, 630, 110), (560, 130, 630, 140)])
        rows = [r for r, _ in table_rows([col2, labels, col1])]
        self.assertEqual(rows, ["Lãi vay phải trả | 85.922 | 93.317", "Khác | 1.316.399 | 831.648"])


class GeometryTest(unittest.TestCase):
    def test_union_pad_cover(self):
        self.assertEqual(union([(0, 0, 10, 10), (5, 5, 20, 8)]), (0, 0, 20, 10))
        self.assertEqual(pad((5, 5, 95, 95), 100, 100, p=10), (0, 0, 100, 100))
        self.assertAlmostEqual(cover((0, 0, 50, 100), (0, 0, 100, 100)), 0.5)


class IndexHelpersTest(unittest.TestCase):
    def test_parse_pages(self):
        self.assertEqual(parse_pages("1-3,10,2", 232), [1, 2, 3, 10])
        self.assertEqual(parse_pages("230-240", 232), [230, 231, 232])

    def test_unverified_numbers_ignores_years_and_found_values(self):
        text = "Tổng doanh thu 70.113 Tỷ VNĐ 11,6%"
        self.assertEqual(unverified_numbers("Năm 2025: 70.113; tăng 11,6%", text), [])
        self.assertEqual(unverified_numbers("2024: 62.849", text), ["62.849"])

    def test_split_respects_limit(self):
        parts = _split(["a" * 10] * 5, len, 25)
        self.assertEqual([len(p) for p in parts], [2, 2, 1])


class ProxyLabelTest(unittest.TestCase):
    ev = {"id": "Q:E1", "pdf_page": 10, "quotes": ["52.618", "Tổng doanh thu"], "bbox_pt": [250, 150, 630, 350]}

    def test_requires_same_page(self):
        hit = {"pdf_page": 11, "text": "Tổng doanh thu 52.618", "bbox": [250, 150, 630, 350]}
        self.assertFalse(supports(hit, self.ev))

    def test_quote_or_bbox_match(self):
        by_quote = {"pdf_page": 10, "text": "Tổng doanh thu ... 52.618", "bbox": [0, 0, 10, 10]}
        by_bbox = {"pdf_page": 10, "text": "khác", "bbox": [240, 140, 640, 360]}
        neither = {"pdf_page": 10, "text": "khác", "bbox": [700, 400, 900, 500]}
        self.assertTrue(supports(by_quote, self.ev))
        self.assertTrue(supports(by_bbox, self.ev))
        self.assertFalse(supports(neither, self.ev))

    def test_all_of_groups(self):
        case = {"evidence_groups": [{"all_of": ["E1", "E2"]}, {"all_of": ["E3"]}]}
        self.assertFalse(complete(case, {"E1"}))
        self.assertTrue(complete(case, {"E1", "E2"}))
        self.assertTrue(complete(case, {"E3"}))


class CitationExpansionTest(unittest.TestCase):
    def test_only_distinctive_numbers_and_verbatim_matches(self):
        from src.agent import distinctive_numbers, expand_citations
        self.assertEqual(distinctive_numbers("Năm 2025 doanh thu 52.618 tỷ, tăng 11,6%, 7 công ty"), {"52.618"})
        seen = {"a": {"text": "Doanh thu 52.618"}, "b": {"text": "thuyết minh: 52.618 tỷ"}, "c": {"text": "2025"}}
        self.assertEqual(expand_citations("Doanh thu 52.618 tỷ [a]", ["a"], seen), ["b"])
        self.assertEqual(expand_citations("Có, theo chính sách [a]", ["a"], seen), [])


if __name__ == "__main__":
    unittest.main()
