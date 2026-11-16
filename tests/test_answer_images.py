"""Image attribution checks; no DB, model API, or benchmark gold."""
import base64
import copy
from pathlib import Path
import tempfile
import unittest

from src.answer_images import image_delivery, select_answer_images


class AnswerImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")
        self.name = "Trương Gia Bình"
        self.bio = self.chunk("text01", "text", f"Ông {self.name}", "Thành viên sáng lập, Chủ tịch HĐQT.")
        self.photo = self.chunk("photo01", "photo", f"Ảnh chân dung Ông {self.name}", f"Ảnh chân dung ông {self.name}.")
        self.trace = {"status": "answered", "question": f"Ông {self.name} là ai?",
                      "answer": f"Ông {self.name} là Chủ tịch HĐQT FPT.",
                      "citations": [self.bio["chunk_id"]],
                      "context": [{**self.bio, "text": self.bio["content"]}]}

    def chunk(self, suffix, kind, title, content, page=37):
        path = f"assets/p{page}-{suffix}.png"
        (self.root / path).write_bytes(self.png)
        return {"chunk_id": f"fpt-ar2025:p{page:03}:{suffix}", "kind": kind,
                "pdf_page": page, "printed_page": str(page - 1), "title": title,
                "content": title + "\n" + content, "bbox": [1, 2, 3, 4], "crop_path": path}

    def select(self, chunks=None, trace=None, **kwargs):
        return select_answer_images(trace or self.trace, chunks or [self.bio, self.photo],
                                    project_root=self.root, asset_root=self.assets, doc_id="fpt-ar2025", **kwargs)

    def test_biography_links_to_named_portrait_without_mutating_model_evidence(self):
        original = copy.deepcopy(self.trace)
        images = self.select()
        self.assertEqual([i["chunk_id"] for i in images], [self.photo["chunk_id"]])
        self.assertEqual(images[0]["matched_by"], "portrait_name")
        self.assertEqual(images[0]["supporting_chunk_ids"], self.trace["citations"])
        self.assertEqual(images[0]["identity_source_chunk_ids"], [self.bio["chunk_id"]])
        self.assertEqual((images[0]["pdf_page"], images[0]["printed_page"]), (37, "36"))
        self.assertNotIn("crop_path", images[0])
        self.assertEqual(self.trace, original)

    def test_other_people_on_same_page_and_group_caption_are_not_attached(self):
        other = self.chunk("photo02", "photo", "Ông Bùi Quang Ngọc", "Ảnh chân dung ông Bùi Quang Ngọc.")
        group = self.chunk("photo03", "photo", "Ông Trương Gia Bình và ông Bùi Quang Ngọc",
                           "Ảnh chân dung hai thành viên HĐQT.")
        images = self.select([self.bio, other, group, self.photo])
        self.assertEqual([i["chunk_id"] for i in images], [self.photo["chunk_id"]])

    def test_name_in_question_or_uncited_search_hit_alone_is_insufficient(self):
        trace = copy.deepcopy(self.trace)
        trace["answer"] = "Báo cáo đề cập HĐQT FPT."
        self.assertEqual(self.select(trace=trace), [])
        trace = copy.deepcopy(self.trace)
        trace["citations"] = []
        self.assertEqual(self.select(trace=trace), [])

    def test_use_exact_visible_evidence_not_unseen_full_index_content(self):
        trace = copy.deepcopy(self.trace)
        trace["context"][0]["text"] = "Đoạn này đã bị cắt trước phần tên."
        self.assertEqual(self.select(trace=trace), [])

    def test_vision_caption_without_original_pdf_name_is_not_identity_proof(self):
        bio = {**self.bio, "content": "Bài viết không nêu tên lãnh đạo."}
        self.assertEqual(self.select([bio, self.photo]), [])

    def test_original_pdf_blocks_inside_photo_can_confirm_caption(self):
        photo = {**self.photo, "content": self.photo["content"] +
                 "\nNội dung trích từ PDF:\nÔng TRƯƠNG GIA BÌNH | Chủ tịch HĐQT"}
        self.assertEqual(len(self.select([photo, {**self.bio, "pdf_page": 4}])), 1)

    def test_case_accents_and_followup_without_repeated_name(self):
        trace = copy.deepcopy(self.trace)
        trace.update(question="Ông ấy giữ chức vụ gì?", answer="TRUONG GIA BINH là Chủ tịch HĐQT.")
        self.assertEqual(len(self.select(trace=trace)), 1)
        trace["answer"] = "Trương Gia là Chủ tịch."
        self.assertEqual(self.select(trace=trace), [])
        trace["answer"] = "Trương Gia BìnhMinh"
        self.assertEqual(self.select(trace=trace), [])

    def test_abstention_or_error_never_attaches_image(self):
        for status in ("abstain", "error"):
            with self.subTest(status=status):
                self.assertEqual(self.select(trace={**self.trace, "status": status}), [])

    def test_missing_invalid_or_outside_asset_is_skipped(self):
        outside = self.root / "outside.png"
        outside.write_bytes(self.png)
        (self.assets / "bad.png").write_bytes(b"not a PNG")
        for path in (None, "assets/missing.png", "assets/bad.png", str(outside)):
            with self.subTest(path=path):
                self.assertEqual(self.select([self.bio, {**self.photo, "crop_path": path}]), [])
        (self.assets / "linked.png").symlink_to(outside)
        self.assertEqual(self.select([self.bio, {**self.photo, "crop_path": "assets/linked.png"}]), [])

    def test_cited_portrait_preferred_and_duplicate_person_suppressed(self):
        other = self.chunk("photo02", "photo", self.photo["title"], self.photo["content"], page=40)
        bio = {**self.bio, "chunk_id": "fpt-ar2025:p040:text01", "pdf_page": 40}
        trace = copy.deepcopy(self.trace)
        trace["citations"].append(other["chunk_id"])
        trace["context"].append({**other, "text": other["content"]})
        images = self.select([self.bio, self.photo, bio, other], trace)
        self.assertEqual([i["chunk_id"] for i in images], [other["chunk_id"]])

    def test_cited_figures_only_deduplicate_crop_and_limit_attachments(self):
        figures = [self.chunk(f"chart{i}", "chart", f"Biểu đồ {i}", "Số liệu", page=10) for i in range(5)]
        duplicate = {**figures[0], "chunk_id": "fpt-ar2025:p010:chart-copy"}
        figures.insert(1, duplicate)
        uncited = self.chunk("uncited", "table", "Bảng không trích", "Số liệu", page=10)
        trace = {**self.trace, "answer": "Doanh thu tăng.", "citations": [c["chunk_id"] for c in figures],
                 "context": [{**c, "text": c["content"]} for c in figures + [uncited]]}
        images = self.select(figures + [uncited], trace)
        self.assertEqual(len(images), 3)
        self.assertEqual([i["chunk_id"] for i in images], [figures[i]["chunk_id"] for i in (0, 2, 3)])
        self.assertTrue(all(i["matched_by"] == "cited_region" for i in images))

    def test_other_document_not_selected_even_if_named_and_cited(self):
        other = {**self.photo, "chunk_id": "other-document:p037:photo01"}
        self.assertEqual(self.select([self.bio, other]), [])

    def test_default_delivery_keeps_portrait_in_sidebar(self):
        candidates = self.select()
        for selection in (None, {}, {"request_quote": "", "chunk_ids": [self.photo["chunk_id"]]}):
            with self.subTest(selection=selection):
                delivery = image_delivery(self.trace, candidates, selection)
                self.assertEqual(delivery["answer_images"], [])
                self.assertEqual(delivery["source_images"], candidates)
                self.assertEqual(delivery["image_presentation"]["mode"], "sidebar")

    def test_explicit_model_choice_shows_only_requested_seen_portrait(self):
        trace = copy.deepcopy(self.trace)
        trace["question"] = "Cho tôi xem ảnh chân dung ông Trương Gia Bình."
        trace["context"].append({**self.photo, "text": self.photo["content"]})
        candidates = self.select()
        table = {**candidates[0], "chunk_id": "fpt-ar2025:p086:table01", "kind": "table"}
        selection = {"request_quote": "xem ảnh chân dung ông Trương Gia Bình", "chunk_ids": [self.photo["chunk_id"]]}
        delivery = image_delivery(trace, candidates + [table], selection)
        self.assertEqual(delivery["answer_images"], candidates)
        self.assertEqual(len(delivery["source_images"]), 2)
        self.assertEqual(delivery["image_presentation"]["mode"], "inline")

    def test_prior_turn_request_cannot_switch_images_on_in_current_turn(self):
        delivery = image_delivery(self.trace, self.select(), {
            "request_quote": "Cho tôi xem ảnh chân dung", "chunk_ids": [self.photo["chunk_id"]]})
        self.assertEqual(delivery["answer_images"], [])
        self.assertEqual(delivery["image_presentation"]["request_quote"], "")

    def test_selection_cannot_send_unseen_or_unvalidated_images(self):
        selection = {"request_quote": self.trace["question"], "chunk_ids": [self.photo["chunk_id"], "invented-id"]}
        self.assertEqual(image_delivery(self.trace, self.select(), selection)["answer_images"], [])
        trace = {**self.trace, "context": self.trace["context"] + [{"chunk_id": "invented-id"}]}
        self.assertEqual(image_delivery(trace, [], selection)["answer_images"], [])

    def test_inline_selection_is_unique_and_capped_at_two(self):
        candidates = [{**self.select()[0], "chunk_id": str(i)} for i in range(4)]
        trace = {**self.trace, "question": "Cho xem các ảnh", "context": candidates}
        delivery = image_delivery(trace, candidates, {
            "request_quote": "Cho xem các ảnh", "chunk_ids": ["0", "0", "1", "2", "3"]})
        self.assertEqual([i["chunk_id"] for i in delivery["answer_images"]], ["0", "1"])
        self.assertEqual(len(delivery["source_images"]), 3)

    def test_bad_selection_and_abstention_fail_closed(self):
        for selection in ("image", {"request_quote": None, "chunk_ids": []},
                          {"request_quote": self.trace["question"], "chunk_ids": "not-an-array"}):
            with self.subTest(selection=selection):
                self.assertEqual(image_delivery(self.trace, self.select(), selection)["answer_images"], [])
        delivery = image_delivery({**self.trace, "status": "abstain"}, self.select(), {})
        self.assertEqual(delivery["source_images"], [])


if __name__ == "__main__":
    unittest.main()
