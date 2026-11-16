"""Local HTTP adapter for the existing agent. Run: python -m src.web_api

One cached embedding model, one interactive run at a time. This module never reads benchmark gold
and never writes benchmark runs. The CLI agent/configuration used by the frozen test is unchanged.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import psycopg
from dotenv import load_dotenv

from src.agent import Agent, AgentConfig, cost_usd
from src.answer_images import image_delivery, select_answer_images

ROOT = Path(__file__).resolve().parents[1]
DOC_ID = "fpt-ar2025"
SOURCE_ID = "fpt-ar2025-9449a725"
ASSETS = ROOT / "starter/data/mm" / DOC_ID
DEFAULTS = dict(method="hybrid", mode="advanced", topK=5, budget=24000, maxSteps=6,
                rerank=False, neighbors=True)


def validate_request(data: object) -> tuple[str, dict, list[dict]]:
    if not isinstance(data, dict):
        raise ValueError("Yêu cầu phải là một JSON object.")
    question = data.get("question")
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 4000:
        raise ValueError("Câu hỏi cần từ 1 đến 4.000 ký tự.")
    if data.get("source_id", SOURCE_ID) != SOURCE_ID:
        raise ValueError("Nguồn không hợp lệ; chỉ hỗ trợ báo cáo FPT 2025.")
    supplied = data.get("config", {})
    if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
        raise ValueError("Cấu hình không hợp lệ.")
    config = DEFAULTS | supplied
    if config["method"] not in ("dense", "lexical", "hybrid") or config["mode"] not in ("basic", "advanced"):
        raise ValueError("Phương pháp hoặc chế độ không hợp lệ.")
    for key, values in (("topK", range(3, 21)), ("budget", (4096, 8192, 16384, 24000)),
                        ("maxSteps", (2, 3, 4, 6))):
        if type(config[key]) is not int or config[key] not in values:
            raise ValueError(f"Giá trị {key} không hợp lệ.")
    if any(type(config[k]) is not bool for k in ("rerank", "neighbors")):
        raise ValueError("Rerank và neighbor phải là boolean.")
    if config["rerank"] and config["method"] != "hybrid":
        raise ValueError("Rerank sử dụng candidate từ Hybrid; hãy chọn Hybrid.")
    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > 6:
        raise ValueError("Lịch sử chỉ nhận tối đa 6 tin nhắn gần nhất.")
    for item in history:
        if (not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str) or len(item["content"]) > 6000):
            raise ValueError("Tin nhắn lịch sử không hợp lệ.")
    return question.strip(), config, [{"role": x["role"], "content": x["content"]} for x in history]


def agent_config(config: dict) -> AgentConfig:
    return AgentConfig(method="rerank" if config["rerank"] else
                       {"lexical": "bm25_bigram"}.get(config["method"], config["method"]),
                       top_k=config["topK"], max_steps=config["maxSteps"], budget_chars=config["budget"],
                       view_image=config["mode"] == "advanced", cite_expand=False)


class Cancelled(Exception):
    pass


class WebAgent(Agent):
    """Keep precisely the text sent to the model, including the last chunk's remaining budget.

    This adapter fixes interactive trace fidelity without changing the frozen benchmark agent.
    """
    def __init__(self, *args, emit, **kwargs):
        super().__init__(*args, **kwargs)
        self.emit = emit
        self.instructions += ("\nLịch sử hội thoại chỉ để hiểu câu hỏi tiếp nối, không phải bằng chứng. "
                              "Phải truy xuất lại và trích các chunk của lượt hiện tại.")
        # Extend only the interactive final-answer tool; never mutate the CLI/benchmark schema.
        self.tools = copy.deepcopy(self.tools)
        final_tool = next(t for t in self.tools if t["name"] == "final_answer")
        final_tool["parameters"]["properties"]["image_selection"] = {
            "type": "object", "additionalProperties": False, "required": ["request_quote", "chunk_ids"],
            "properties": {
                "request_quote": {"type": "string", "description":
                                  "Trích nguyên văn yêu cầu xem/đính kèm ảnh ở tin nhắn hiện tại; mặc định chuỗi rỗng."},
                "chunk_ids": {"type": "array", "maxItems": 2, "items": {"type": "string"},
                              "description": "Tối đa 2 vùng ảnh đã truy xuất để hiển thị trong chat; mặc định []."}}}
        final_tool["parameters"]["required"].append("image_selection")
        self.instructions += (
            "\nHIỂN THỊ ẢNH: Mặc định trả lời bằng chữ và citation; ảnh nguồn nằm ở bảng Nguồn bên phải. "
            "Trong final_answer, mặc định image_selection={request_quote:'',chunk_ids:[]}. "
            "Chỉ chọn ảnh khi người dùng ở LƯỢT HIỆN TẠI chủ động yêu cầu xem, gửi, đính kèm ảnh/hình/biểu đồ "
            "hoặc đồng ý rõ ràng với lời đề nghị xem ảnh ngay trước đó. Tôn trọng yêu cầu không gửi ảnh. "
            "Hỏi chức vụ/tiểu sử, hỏi số liệu, hoặc yêu cầu đọc/phân tích biểu đồ KHÔNG tự nó là yêu cầu đính kèm. "
            "Yêu cầu ảnh ở lượt trước không có nghĩa lượt sau cũng cần ảnh. "
            "Nếu cần đính kèm: tìm vùng nguồn qua search/open_page, chỉ chọn chunk_id đã thấy, đúng đối tượng "
            "và đúng loại ảnh được yêu cầu, ưu tiên 1 ảnh; tối đa 2 khi cần so sánh. Hỏi chân dung chỉ chọn photo, "
            "không gửi thêm bảng số liệu. Chép nguyên văn phần yêu cầu hiện tại vào request_quote. "
            "Không tìm được ảnh phù hợp thì để chunk_ids=[] và nói rõ, không hứa có ảnh. "
            "view_image chỉ để đọc ảnh làm bằng chứng, không phải lệnh gửi ảnh. Không chèn ảnh Markdown."
        )

    def _format(self, hits, seen, state):
        parts = []
        for hit in hits:
            room = max(0, self.cfg.budget_chars - state["chars"])
            shown = {**hit, "text": hit["text"][:min(self.cfg.chunk_chars, room)]}
            parts.append(super()._format([shown], seen, state))
        self.emit({"event": "context", "chunks": [public_chunk(h) for h in seen.values()],
                   "context_chars": state["chars"], "budget": self.cfg.budget_chars,
                   "dropped_for_budget": state["dropped"][:]})
        return "\n\n".join(parts) or "(không có kết quả)"


def public_chunk(hit: dict) -> dict:
    return {k: v for k, v in hit.items() if k in
            ("chunk_id", "pdf_page", "printed_page", "kind", "text", "bbox", "rank", "score", "title")}


class RunRetriever:
    def __init__(self, retriever, emit, check):
        self.inner, self.emit, self.check = retriever, emit, check

    def search(self, query, method, k):
        self.check()
        self.emit({"event": "search_started", "query": query, "method": method})
        hits, ms = self.inner.search(query, method, k)
        self.check()
        self.emit({"event": "search", "query": query, "method": method, "elapsed_ms": round(ms, 1),
                   "results": [{**public_chunk(h), "text": h["text"][:2500]} for h in hits]})
        return hits, ms

    def page_chunks(self, page):
        self.check()
        hits = self.inner.page_chunks(page)
        self.emit({"event": "open_page", "pdf_page": page, "results": [h["chunk_id"] for h in hits]})
        return hits


class RunClient:
    def __init__(self, client, history, emit, check):
        self.inner, self.history, self.emit, self.check = client, history, emit, check
        self.responses = SimpleNamespace(create=self.create)
        self.step = 0
        self.image_selection = None

    def create(self, **kwargs):
        self.check()
        self.step += 1
        self.emit({"event": "model_started", "step": self.step})
        response = self.inner.responses.create(**{**kwargs, "input": self.history + kwargs["input"]})
        self.check()
        for item in response.output:
            if item.type == "function_call" and item.name == "view_image":
                self.emit({"event": "view_image", "chunk_id": json.loads(item.arguments).get("chunk_id")})
            elif item.type == "function_call" and item.name == "final_answer":
                self.image_selection = json.loads(item.arguments).get("image_selection")
        return response


class Runtime:
    def __init__(self):
        self.lock = threading.Lock()
        self.runs: dict[str, threading.Event] = {}
        self.retriever = None
        self.index_revision = None

    def reserve(self) -> tuple[str, threading.Event] | None:
        if not self.lock.acquire(blocking=False):
            return None
        run_id, cancel = str(uuid.uuid4()), threading.Event()
        self.runs[run_id] = cancel
        return run_id, cancel

    def release(self, run_id):
        self.runs.pop(run_id, None)
        self.lock.release()

    def run(self, question, config, history, run_id, cancel, emit):
        start = time.perf_counter()
        deadline = start + 240

        def check():
            if cancel.is_set():
                raise Cancelled()
            if time.perf_counter() > deadline:
                raise TimeoutError()

        def send(event):
            check()
            emit(event)

        cfg = agent_config(config)
        with connection() as db:
            source = db.execute("SELECT sha256,indexed_at::text FROM mm_documents WHERE doc_id=%s",
                                (DOC_ID,)).fetchone()
        if not source:
            raise ValueError("missing index")
        source_hash, revision = source
        send({"event": "run_started", "run_id": run_id, "model": cfg.model, "config": config,
              "index_version": f"{DOC_ID}@{revision}", "context_budget_unit": "characters"})
        if self.retriever is None or revision != self.index_revision:
            send({"event": "loading", "message": "Đang nạp model embedding và index; lần đầu có thể mất khoảng một phút."})
            from src.retrieval import Retriever
            self.retriever = Retriever(embedder=self.retriever.emb if self.retriever else None)
            self.index_revision = revision
        check()
        from openai import OpenAI
        before = dict(getattr(self.retriever, "rerank_usage", {}))
        with OpenAI(max_retries=1, timeout=60) as client:
            run_client = RunClient(client, history, send, check)
            agent = WebAgent(RunRetriever(self.retriever, send, check), cfg,
                             run_client, emit=send)
            if not config["neighbors"]:
                agent.tools = [t for t in agent.tools if t["name"] != "open_page"]
                agent.instructions += "\nopen_page không khả dụng trong lượt này; dùng search khi cần thêm bằng chứng."
            trace = agent.run(question, f"interactive-{run_id}")
        check()
        if trace["status"] == "error":
            # Provider exceptions can contain credentials or internal URLs. Do not send raw exceptions.
            emit({"event": "error", "code": "agent_error", "message":
                  "Agent không hoàn tất lượt hỏi. Kiểm tra kết nối model/database rồi thử lại.",
                  "retryable": True, "run_id": run_id})
            return
        after = getattr(self.retriever, "rerank_usage", {})
        rerank_cost = cost_usd(cfg.model, {"input": after.get("input", 0) - before.get("input", 0),
                                         "output": after.get("output", 0) - before.get("output", 0), "cached": 0})
        trace["cost_usd"] = round((trace["cost_usd"] or 0) + (rerank_cost or 0), 6)
        trace["rerank_cost_usd"] = rerank_cost
        trace["elapsed_ms"] = round((time.perf_counter() - start) * 1000)
        trace["run_id"], trace["ui_config"], trace["purpose"] = run_id, config, "interactive"
        trace["index_version"] = f"{DOC_ID}@{revision}"
        trace["source_sha256"] = source_hash
        trace["embedding_model"] = self.retriever.emb.key
        candidates = select_answer_images(trace, self.retriever.chunks, project_root=ROOT,
                                          asset_root=ASSETS, doc_id=DOC_ID, limit=len(self.retriever.chunks))
        trace.update(image_delivery(trace, candidates, run_client.image_selection))
        # File locations stay private. Assets are resolved by chunk ID against the database.
        for chunk in trace["context"] + trace["citation_sources"]:
            chunk.pop("crop_path", None)
        for event in trace["events"]:
            event.pop("crop_path", None)
        trace["stop_reason"] = next((e["event"] for e in reversed(trace["events"])
                                    if e["event"] in ("step_limit", "invalid_or_missing_citations")), "final_answer")
        emit({"event": "complete", "trace": trace})


def connection():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=4,
                           options="-c default_transaction_read_only=on -c statement_timeout=5000")


def index_status(runtime):
    with connection() as db:
        doc = db.execute("SELECT sha256,page_count FROM mm_documents WHERE doc_id=%s", (DOC_ID,)).fetchone()
        if not doc:
            raise ValueError("missing index")
        kinds = dict(db.execute("SELECT kind,count(*) FROM mm_chunks WHERE doc_id=%s GROUP BY kind", (DOC_ID,)).fetchall())
        embeddings = db.execute("SELECT count(*) FROM mm_embeddings e JOIN mm_chunks k USING(chunk_id) "
                                "WHERE k.doc_id=%s", (DOC_ID,)).fetchone()[0]
        pages = db.execute("SELECT p.pdf_page,p.log,count(k.chunk_id) FROM mm_pages p LEFT JOIN mm_chunks k "
                           "ON p.doc_id=k.doc_id AND p.pdf_page=k.pdf_page WHERE p.doc_id=%s "
                           "GROUP BY p.pdf_page,p.log ORDER BY p.pdf_page", (DOC_ID,)).fetchall()
    return {"ready": bool(os.getenv("OPENAI_API_KEY")) and embeddings > 0,
            "api_configured": bool(os.getenv("OPENAI_API_KEY")), "embedding_loaded": runtime.retriever is not None,
            "busy": runtime.lock.locked(), "model": AgentConfig().model, "source_id": SOURCE_ID,
            "sha256": doc[0], "pages": doc[1], "chunks": sum(kinds.values()), "embeddings": embeddings,
            "chunks_by_kind": kinds, "indexed_pages": sum(n > 0 for _, _, n in pages),
            "ledger": [{"pdf_page": p, "status": "indexed" if n else "skipped", "chunks": n,
                        "reason": None if n else "Trang mở chương; không còn nội dung riêng sau khi lọc tiêu đề lặp."}
                       for p, _, n in pages]}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def runtime(self):
        return self.server.runtime

    def log_message(self, *_):
        pass  # No questions, credentials, or document content in HTTP logs.

    def reply(self, data, status=200, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                self.reply(index_status(self.runtime))
            elif parsed.path == "/asset":
                chunk_id = parse_qs(parsed.query).get("chunk", [""])[0]
                if not chunk_id.startswith(DOC_ID + ":") or len(chunk_id) > 160:
                    self.reply({"error": "Nguồn không hợp lệ."}, 400)
                    return
                with connection() as db:
                    row = db.execute("SELECT crop_path FROM mm_chunks WHERE doc_id=%s AND chunk_id=%s",
                                     (DOC_ID, chunk_id)).fetchone()
                file = (ROOT / row[0]).resolve() if row and row[0] else None
                if not file or not file.is_relative_to(ASSETS.resolve()) or not file.is_file():
                    self.reply({"error": "Không có ảnh vùng nguồn."}, 404)
                    return
                self.reply(file.read_bytes(), content_type="image/png")
            else:
                self.reply({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self.reply({"ready": False, "error": "Chưa kết nối được index. Kiểm tra PostgreSQL của Day 6."}, 503)

    def do_POST(self):
        # Only Next's server-side proxy calls this loopback service, never a browser cross-origin.
        if self.headers.get("Origin") or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.reply({"error": "Unsupported request"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 60000:
                self.reply({"error": "Request too large or empty"}, 413)
                return
            data = json.loads(self.rfile.read(length))
            if self.path == "/cancel":
                token = self.runtime.runs.get(data.get("run_id")) if isinstance(data, dict) else None
                if token:
                    token.set()
                self.reply({"cancelled": bool(token)})
                return
            if self.path != "/chat":
                self.reply({"error": "Not found"}, 404)
                return
            question, config, history = validate_request(data)
        except (ValueError, TypeError):
            self.reply({"error": "Câu hỏi hoặc cấu hình không hợp lệ."}, 400)
            return
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("DATABASE_URL"):
            self.reply({"error": "Backend thiếu cấu hình model hoặc database."}, 503)
            return
        reservation = self.runtime.reserve()
        if not reservation:
            self.reply({"error": "Agent đang xử lý một lượt khác. Vui lòng thử lại khi lượt đó kết thúc."}, 409)
            return
        run_id, cancel = reservation
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-transform")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

        def emit(data):
            body = (json.dumps(data, ensure_ascii=False) + "\n").encode()
            self.wfile.write(f"{len(body):x}\r\n".encode() + body + b"\r\n")
            self.wfile.flush()

        try:
            self.runtime.run(question, config, history, run_id, cancel, emit)
        except Cancelled:
            pass
        except (BrokenPipeError, ConnectionResetError):
            cancel.set()
        except Exception as error:
            try:
                emit({"event": "error", "code": type(error).__name__, "message":
                      "Backend chưa xử lý được câu hỏi. Kiểm tra kết nối model và index rồi thử lại.",
                      "retryable": True, "run_id": run_id})
            except (BrokenPipeError, ConnectionResetError):
                pass
        finally:
            self.runtime.release(run_id)
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8007)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server.runtime = Runtime()
    print(f"Lumina agent API: http://127.0.0.1:{args.port} (embedding loads on first question)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
