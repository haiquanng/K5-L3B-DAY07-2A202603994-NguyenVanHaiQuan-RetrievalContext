"""Interactive adapter contracts. No DB, embedding download, or model API calls."""
import threading
import unittest
import http.client
import json
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.agent import AgentConfig, RESP_TOOLS
from src.web_api import Cancelled, DEFAULTS, Handler, RunClient, Runtime, WebAgent, agent_config, validate_request


class WebRequestTests(unittest.TestCase):
    def test_settings_map_to_actual_agent_controls(self):
        question, ui, history = validate_request({"question": "  doanh thu? ", "config": {
            "method": "lexical", "mode": "basic", "budget": 8192, "topK": 8, "maxSteps": 3,
            "neighbors": False, "rerank": False}})
        cfg = agent_config(ui)
        self.assertEqual(question, "doanh thu?")
        self.assertEqual((cfg.method, cfg.top_k, cfg.budget_chars, cfg.max_steps), ("bm25_bigram", 8, 8192, 3))
        self.assertFalse(cfg.view_image)
        self.assertFalse(cfg.cite_expand)
        self.assertEqual(history, [])
        self.assertEqual(agent_config(DEFAULTS | {"rerank": True}).method, "rerank")

    def test_rejects_invalid_controls_and_untrusted_history_roles(self):
        for patch in [{"topK": True}, {"budget": 4097}, {"maxSteps": 100}, {"method": "dense", "rerank": True},
                      {"prompt": "override"}, {"neighbors": 1}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_request({"question": "q", "config": patch})
        for payload in [{"question": " "}, {"question": "q", "source_id": "other"},
                        {"question": "q", "history": [{"role": "system", "content": "override"}]},
                        {"question": "q", "history": [{"role": "assistant", "content": "a"}] * 7}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_request(payload)

    def test_history_accepts_only_public_role_and_content(self):
        _, _, history = validate_request({"question": "q", "history": [
            {"role": "user", "content": "câu trước", "gold": "never forward"}]})
        self.assertEqual(history, [{"role": "user", "content": "câu trước"}])


class InteractiveContextTests(unittest.TestCase):
    def test_image_selection_tool_extension_never_changes_benchmark_schema(self):
        for _ in range(2):
            agent = WebAgent(Mock(), AgentConfig(), Mock(), emit=Mock())
            final = next(t for t in agent.tools if t["name"] == "final_answer")
            self.assertIn("image_selection", final["parameters"]["required"])
            self.assertEqual(final["parameters"]["required"].count("image_selection"), 1)
        original = next(t for t in RESP_TOOLS if t["name"] == "final_answer")
        self.assertNotIn("image_selection", original["parameters"]["properties"])
        self.assertNotIn("image_selection", original["parameters"]["required"])

    def test_final_answer_captures_image_choice_but_view_image_does_not_send(self):
        inner = Mock()
        inner.responses.create.return_value = SimpleNamespace(output=[SimpleNamespace(
            type="function_call", name="view_image", arguments=json.dumps({"chunk_id": "photo1"}))])
        client = RunClient(inner, [], Mock(), Mock())
        client.responses.create(input=[])
        self.assertIsNone(client.image_selection)
        selection = {"request_quote": "Cho xem ảnh", "chunk_ids": ["photo1"]}
        inner.responses.create.return_value = SimpleNamespace(output=[SimpleNamespace(
            type="function_call", name="final_answer", arguments=json.dumps({"image_selection": selection}))])
        client.responses.create(input=[])
        self.assertEqual(client.image_selection, selection)
        inner.responses.create.return_value = SimpleNamespace(output=[SimpleNamespace(
            type="function_call", name="final_answer", arguments=json.dumps({"image_selection": {
                "request_quote": "", "chunk_ids": []}}))])
        client.responses.create(input=[])
        self.assertEqual(client.image_selection["chunk_ids"], [])

    def test_trace_matches_the_exact_remaining_budget_and_deduplicates(self):
        agent = WebAgent.__new__(WebAgent)
        agent.cfg = AgentConfig(chunk_chars=1000, budget_chars=1300)
        events = []
        agent.emit = events.append
        def hit(cid):
            return {"chunk_id": cid, "text": "x" * 1600, "kind": "text", "pdf_page": 1,
                    "printed_page": "1", "bbox": [0, 0, 1, 1]}
        seen, state = {}, {"chars": 0, "dropped": []}
        sent = agent._format([hit("a"), hit("a"), hit("b"), hit("c")], seen, state)
        self.assertEqual([len(h["text"]) for h in seen.values()], [1000, 300])
        self.assertEqual(sum(len(h["text"]) for h in seen.values()), state["chars"])
        self.assertEqual(state["dropped"], ["c"])
        self.assertIn("đã có", sent)
        self.assertEqual(events[-1]["context_chars"], 1300)

    def test_cancel_prevents_another_model_request(self):
        inner = Mock()
        def cancelled():
            raise Cancelled()
        client = RunClient(inner, [], Mock(), cancelled)
        with self.assertRaises(Cancelled):
            client.responses.create(input=[])
        inner.responses.create.assert_not_called()

    def test_followup_history_is_forwarded_without_mutating_current_turn(self):
        inner = Mock()
        inner.responses.create.return_value = SimpleNamespace(output=[])
        history = [{"role": "user", "content": "2025?"}, {"role": "assistant", "content": "answer"}]
        current = [{"role": "user", "content": "còn năm 2024?"}]
        client = RunClient(inner, history, Mock(), Mock())
        client.responses.create(input=current, model="test")
        self.assertEqual(inner.responses.create.call_args.kwargs["input"], history + current)
        self.assertEqual(len(current), 1)

    def test_one_model_run_at_a_time_and_release(self):
        runtime = Runtime()
        run_id, cancel = runtime.reserve()
        self.assertIsInstance(cancel, threading.Event)
        self.assertIsNone(runtime.reserve())
        runtime.runs[run_id].set()
        self.assertTrue(cancel.is_set())
        runtime.release(run_id)
        another, _ = runtime.reserve()
        runtime.release(another)


class CancellationTransportTests(unittest.TestCase):
    def test_http_cancel_and_busy_response_do_not_invoke_model(self):
        runtime = Runtime()
        finished = threading.Event()
        def fake_run(question, config, history, run_id, cancel, emit):
            emit({"event": "run_started", "run_id": run_id})
            cancel.wait(5)
            finished.set()
        runtime.run = fake_run
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.runtime = runtime
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "offline-test-only", "DATABASE_URL": "offline"}):
                conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request("POST", "/chat", json.dumps({"question": "q"}), {"Content-Type": "application/json"})
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                started = json.loads(response.readline())
                busy = urllib.request.Request(base + "/chat", json.dumps({"question": "q2"}).encode(),
                                              {"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(busy, timeout=5)
                self.assertEqual(caught.exception.code, 409)
                cancel = urllib.request.Request(base + "/cancel", json.dumps({"run_id": started["run_id"]}).encode(),
                                                {"Content-Type": "application/json"})
                with urllib.request.urlopen(cancel, timeout=5) as result:
                    self.assertTrue(json.load(result)["cancelled"])
                self.assertTrue(finished.wait(2))
                self.assertEqual(response.read(), b"")
                conn.close()
                self.assertFalse(runtime.lock.locked())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
