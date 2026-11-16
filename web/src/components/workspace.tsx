"use client";
import Image from "next/image";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Command,
  FileText,
  FlaskConical,
  FolderOpen,
  GitBranch,
  Menu,
  MessageCircle,
  MoreHorizontal,
  PanelRight,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import {
  DEFAULT_CONFIG,
  METHOD_LABELS,
  SOURCE,
  downloadJson,
} from "@/lib/demo";
import type { Config, Conversation, Message, View } from "@/lib/types";
import type {
  AgentTrace,
  BackendHealth,
  TraceEvent,
  Chunk,
} from "@/lib/contracts";
import { readAgentEvents } from "@/lib/agent-stream";
import { Brand, Modal, Pill } from "./ui";
import { Welcome, Composer, MessageList } from "./chat";
import { EvidencePanel, type InspectorTab } from "./evidence-panel";
import { Settings } from "./settings";
const Library = dynamic(() => import("./library").then((m) => m.Library));
const Benchmark = dynamic(() => import("./benchmark").then((m) => m.Benchmark));
const LabGuide = dynamic(() => import("./lab-guide").then((m) => m.LabGuide));
const STORAGE_KEY = "lumina.lab07.conversations.v2";
const NAV = [
  { id: "chat", label: "Trò chuyện", icon: MessageCircle },
  { id: "library", label: "Thư viện nguồn", icon: BookOpen },
  { id: "benchmark", label: "Phòng thử nghiệm", icon: FlaskConical },
  { id: "lab", label: "Đối chiếu lab", icon: ShieldCheck },
] as const;
const uid = () => crypto.randomUUID();
function validConfig(c: unknown): c is Config {
  if (!c || typeof c !== "object") return false;
  const x = c as Config;
  return (
    ["hybrid", "dense", "lexical"].includes(x.method) &&
    ["basic", "advanced"].includes(x.mode) &&
    Number.isInteger(x.topK) &&
    x.topK >= 3 &&
    x.topK <= 20 &&
    [4096, 8192, 16384, 24000].includes(x.budget) &&
    [2, 3, 4, 6].includes(x.maxSteps) &&
    typeof x.rerank === "boolean" &&
    typeof x.neighbors === "boolean"
  );
}
function restore(raw: string | null): Conversation[] {
  try {
    const data = JSON.parse(raw ?? "[]");
    if (!Array.isArray(data)) return [];
    return data
      .filter(
        (c: Conversation) =>
          typeof c?.id === "string" &&
          typeof c.title === "string" &&
          typeof c.createdAt === "string" &&
          Array.isArray(c.messages),
      )
      .slice(0, 20)
      .map((c: Conversation) => ({
        ...c,
        messages: c.messages
          .filter(
            (m) =>
              typeof m?.id === "string" &&
              ["user", "assistant"].includes(m.role) &&
              typeof m.text === "string" &&
              (!m.trace ||
                (m.trace.purpose === "interactive" &&
                  Array.isArray(m.trace.context) &&
                  Array.isArray(m.trace.events) &&
                  Array.isArray(m.trace.citations) &&
                  validConfig(m.config))),
          )
          .slice(-50),
      }));
  } catch {
    return [];
  }
}
export function Workspace() {
  const [view, setView] = useState<View>("chat"),
    [conversations, setConversations] = useState<Conversation[]>([]),
    [activeId, setActiveId] = useState<string | null>(null),
    [hydrated, setHydrated] = useState(false);
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG),
    [settings, setSettings] = useState(false),
    [navOpen, setNavOpen] = useState(false),
    [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false),
    [stage, setStage] = useState(0),
    [inspectorOpen, setInspectorOpen] = useState(false),
    [tab, setTab] = useState<InspectorTab>("sources");
  const [inspected, setInspected] = useState<{
    trace?: AgentTrace;
    config: Config;
  }>({ config: DEFAULT_CONFIG });
  const [liveEvents, setLiveEvents] = useState<TraceEvent[]>([]);
  const [liveChunks, setLiveChunks] = useState<Chunk[]>([]);
  const [progress, setProgress] = useState("");
  const [backend, setBackend] = useState<BackendHealth | null>(null);
  const [sourcePage, setSourcePage] = useState<number | null>(null),
    [about, setAbout] = useState(false),
    [notice, setNotice] = useState("");
  const pending = useRef<{
    controller: AbortController;
    runId?: string;
    conversationId: string;
  } | null>(null);
  const busyRef = useRef(false);
  const checkBackend = useCallback(async () => {
    try {
      const response = await fetch("/api/agent/health", { cache: "no-store" });
      setBackend(
        response.ok ? ((await response.json()) as BackendHealth) : null,
      );
    } catch {
      setBackend(null);
    }
  }, []);
  useEffect(() => {
    try {
      setConversations(restore(localStorage.getItem(STORAGE_KEY)));
      const stored = JSON.parse(
        localStorage.getItem("lumina.config.v2") ?? "null",
      );
      if (validConfig(stored)) setConfig(stored);
    } catch {
      /* Storage is optional. */
    }
    setHydrated(true);
    void checkBackend();
    const refresh = () => {
      if (document.visibilityState === "visible") void checkBackend();
    };
    document.addEventListener("visibilitychange", refresh);
    return () => {
      document.removeEventListener("visibilitychange", refresh);
      const current = pending.current;
      current?.controller.abort();
      if (current?.runId)
        void fetch("/api/agent/cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ run_id: current.runId }),
          keepalive: true,
        }).catch(() => {});
    };
  }, [checkBackend]);
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(conversations.slice(0, 20)),
      );
    } catch {
      setNotice(
        "Bộ nhớ trình duyệt đầy hoặc không khả dụng. Chat hiện tại vẫn dùng được.",
      );
    }
  }, [conversations, hydrated]);
  useEffect(() => {
    if (hydrated)
      try {
        localStorage.setItem("lumina.config.v2", JSON.stringify(config));
      } catch {
        /* In-memory preferences remain usable. */
      }
  }, [config, hydrated]);
  const stop = useCallback(() => {
    const current = pending.current;
    if (!current) return;
    pending.current = null;
    current.controller.abort();
    if (current.runId)
      void fetch("/api/agent/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: current.runId }),
      }).catch(() => {});
    setConversations((cs) =>
      cs.map((c) =>
        c.id === current.conversationId
          ? {
              ...c,
              messages: [
                ...c.messages,
                {
                  id: uid(),
                  role: "assistant",
                  text: "Đã dừng phản hồi. Lời gọi model đang thực hiện có thể cần thêm thời gian để kết thúc.",
                  stopped: true,
                } as Message,
              ],
            }
          : c,
      ),
    );
    busyRef.current = false;
    setBusy(false);
    setLiveEvents([]);
    setLiveChunks([]);
  }, []);
  const newChat = useCallback(() => {
    if (busyRef.current) stop();
    setActiveId(null);
    setView("chat");
    setInspectorOpen(false);
    setInspected({ config: DEFAULT_CONFIG });
    setNavOpen(false);
    setSearch("");
  }, [stop]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        newChat();
      }
      if (e.key === "Escape") {
        setNavOpen(false);
        setInspectorOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [newChat]);
  const active = conversations.find((c) => c.id === activeId);
  const messages = active?.messages ?? [];
  const navigate = (target: View) => {
    setView(target);
    setNavOpen(false);
  };
  const inspect = (trace: AgentTrace, c: Config, t: "sources" | "trace") => {
    setInspected({ trace, config: c });
    setTab(t);
    setInspectorOpen(true);
  };
  const send = async (text: string) => {
    if (busyRef.current || !text.trim()) return;
    busyRef.current = true;
    setBusy(true);
    setStage(0);
    setProgress("Đang kết nối agent…");
    setLiveEvents([]);
    setLiveChunks([]);
    setView("chat");
    setNavOpen(false);
    const id = activeId ?? uid();
    const user: Message = { id: uid(), role: "user", text: text.trim() };
    const snapshot = { ...config };
    let historyRoom = 10000;
    const history = messages
      .filter((m) => !m.error && !m.stopped)
      .slice(-6)
      .reverse()
      .flatMap((m) => {
        if (!historyRoom) return [];
        const content = m.text.slice(-Math.min(6000, historyRoom));
        historyRoom -= content.length;
        return [{ role: m.role, content }];
      })
      .reverse();
    if (!activeId) {
      setActiveId(id);
      setConversations((cs) =>
        [
          {
            id,
            title: text.trim().slice(0, 64),
            createdAt: new Date().toISOString(),
            messages: [user],
          },
          ...cs,
        ].slice(0, 20),
      );
    } else {
      setConversations((cs) =>
        cs.map((c) =>
          c.id === id
            ? { ...c, messages: [...c.messages, user].slice(-49) }
            : c,
        ),
      );
    }
    const current = {
      controller: new AbortController(),
      conversationId: id,
      runId: undefined as string | undefined,
    };
    pending.current = current;
    setInspected({ config: snapshot });
    const append = (answer: Message) =>
      setConversations((cs) =>
        cs.map((c) =>
          c.id === id
            ? { ...c, messages: [...c.messages, answer].slice(-50) }
            : c,
        ),
      );
    let completed = false;
    try {
      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: current.controller.signal,
        body: JSON.stringify({
          question: text.trim(),
          source_id: SOURCE.id,
          config: snapshot,
          history,
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error ?? "Không kết nối được agent.");
      }
      if (!response.body) throw new Error("Backend không trả về dữ liệu.");
      for await (const event of readAgentEvents(response.body)) {
        if (pending.current !== current) break;
        switch (event.event) {
          case "run_started":
            current.runId = event.run_id;
            break;
          case "loading":
            setProgress(event.message);
            break;
          case "search_started":
            setStage(1);
            setProgress(`Đang tìm nguồn: ${event.query}`);
            break;
          case "search":
            setLiveEvents((es) => [...es, event]);
            break;
          case "open_page":
            setLiveEvents((es) => [...es, event]);
            setProgress(`Đang mở trang PDF ${event.pdf_page}…`);
            break;
          case "view_image":
            setLiveEvents((es) => [...es, event]);
            setProgress("Đang đọc ảnh vùng nguồn…");
            break;
          case "context":
            setStage(2);
            setLiveChunks(event.chunks);
            break;
          case "model_started":
            setStage(3);
            setProgress(`Đang đối chiếu bằng chứng · lượt ${event.step}…`);
            break;
          case "error":
            throw new Error(event.message);
          case "complete":
            completed = true;
            append({
              id: uid(),
              role: "assistant",
              text: event.trace.answer,
              trace: event.trace,
              config: snapshot,
            });
            setInspected({ trace: event.trace, config: snapshot });
            setLiveEvents([]);
            setLiveChunks([]);
            break;
        }
      }
      if (
        !completed &&
        !current.controller.signal.aborted &&
        pending.current === current
      )
        throw new Error(
          "Kết nối kết thúc trước khi có câu trả lời. Vui lòng thử lại.",
        );
    } catch (error) {
      if (
        !current.controller.signal.aborted &&
        pending.current === current &&
        !completed
      ) {
        append({
          id: uid(),
          role: "assistant",
          error: true,
          text:
            error instanceof Error
              ? error.message
              : "Không xử lý được câu hỏi.",
        });
      }
    } finally {
      if (pending.current === current) {
        pending.current = null;
        busyRef.current = false;
        setBusy(false);
        void checkBackend();
      }
    }
  };
  const exportChat = () => {
    if (!active) return;
    downloadJson(`lumina-chat-${active.id.slice(0, 8)}.json`, {
      format: "lumina-interactive-v1",
      demo: false,
      human_reviewed: false,
      not_for_benchmark_scoring: true,
      exportedAt: new Date().toISOString(),
      source: SOURCE,
      conversation: active,
      traces: active.messages.flatMap((m) => (m.trace ? [m.trace] : [])),
    });
  };
  const deleteChat = (id: string) => {
    if (busyRef.current && id === activeId) stop();
    setConversations((cs) => cs.filter((c) => c.id !== id));
    if (activeId === id) {
      setActiveId(null);
      setInspectorOpen(false);
    }
  };
  return (
    <div className="app-frame">
      <a href="#main-content" className="skip-link">
        Đi tới nội dung chính
      </a>
      {navOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Đóng thanh điều hướng"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside
        className={`sidebar ${navOpen ? "sidebar-open" : ""}`}
        aria-label="Thanh điều hướng"
      >
        <div className="sidebar-brand">
          <Brand />
          <button
            className="icon-button mobile-only"
            aria-label="Đóng menu"
            onClick={() => setNavOpen(false)}
          >
            <X size={19} />
          </button>
        </div>
        <button className="new-chat-button" onClick={newChat}>
          <Plus size={18} />
          <span>Cuộc trò chuyện mới</span>
          <kbd>⌘ K</kbd>
        </button>
        <label className="sidebar-search">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm cuộc trò chuyện"
            aria-label="Tìm cuộc trò chuyện"
          />
          <span>
            <Command size={11} />
          </span>
        </label>
        <nav className="main-nav">
          {NAV.map((n) => (
            <button
              key={n.id}
              className={view === n.id ? "active" : ""}
              onClick={() => navigate(n.id)}
            >
              <n.icon size={19} />
              <span>{n.label}</span>
              {n.id === "chat" && view === "chat" && (
                <span className="active-dot" />
              )}
              {n.id === "benchmark" && <span className="nav-count">240</span>}
            </button>
          ))}
        </nav>
        <div className="history-heading">
          <span>GẦN ĐÂY</span>
          <MoreHorizontal size={16} />
        </div>
        <div className="history-list">
          {!hydrated ? (
            <p className="history-empty">Đang tải lịch sử…</p>
          ) : conversations.filter((c) =>
              c.title.toLowerCase().includes(search.toLowerCase()),
            ).length ? (
            conversations
              .filter((c) =>
                c.title.toLowerCase().includes(search.toLowerCase()),
              )
              .map((c) => (
                <div
                  className={`history-item ${activeId === c.id && view === "chat" ? "selected" : ""}`}
                  key={c.id}
                >
                  <button
                    disabled={busy}
                    onClick={() => {
                      setActiveId(c.id);
                      navigate("chat");
                      setInspectorOpen(false);
                      const last = c.messages.findLast((m) => m.trace);
                      setInspected({
                        trace: last?.trace,
                        config: last?.config ?? config,
                      });
                    }}
                    title={c.title}
                  >
                    <MessageCircle size={14} />
                    <span>{c.title}</span>
                  </button>
                  <button
                    className="delete-chat"
                    onClick={() => deleteChat(c.id)}
                    aria-label={`Xóa cuộc trò chuyện ${c.title}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
          ) : (
            <div className="history-empty">
              <span className="history-empty-line" />
              <p>
                {search
                  ? "Không tìm thấy cuộc trò chuyện."
                  : "Mỗi câu hỏi mở ra một góc nhìn mới."}
              </p>
            </div>
          )}
        </div>
        <div className="sidebar-bottom">
          <button className="pinned-source" onClick={() => navigate("library")}>
            <span>
              <FolderOpen size={19} />
            </span>
            <div>
              <strong>Nguồn của bạn</strong>
              <small>FPT 2025 · 232 trang</small>
            </div>
            <ChevronRight size={15} />
          </button>
          <div className="sidebar-bottom-links">
            <button onClick={() => setSettings(true)}>
              <Settings2 size={17} /> Cài đặt
            </button>
            <button onClick={() => navigate("lab")}>
              <CircleHelp size={17} /> Hướng dẫn demo
            </button>
          </div>
          <div className="user-profile">
            <span className="avatar">Q</span>
            <div>
              <strong>Hải Quân</strong>
              <small>Không gian cá nhân</small>
            </div>
            <button
              className="icon-button"
              onClick={() => setAbout(true)}
              aria-label="Thông tin không gian làm việc"
            >
              <MoreHorizontal size={19} />
            </button>
          </div>
        </div>
      </aside>
      <main
        className={`main-shell ${inspectorOpen && view === "chat" ? "with-inspector" : ""}`}
        id="main-content"
      >
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu"
              aria-label="Mở menu"
              onClick={() => setNavOpen(true)}
            >
              <Menu size={21} />
            </button>
            <button
              className="workspace-selector"
              onClick={() => setSettings(true)}
            >
              <span className="workspace-symbol">
                <Sparkles size={16} />
              </span>
              <strong>
                {view === "chat"
                  ? "Agentic RAG"
                  : NAV.find((n) => n.id === view)?.label}
              </strong>
              {view === "chat" && <ChevronDown size={14} />}
            </button>
            {view === "chat" && (
              <span className="mode-label">
                {config.mode === "advanced" ? "Advanced" : "Cơ bản"}
              </span>
            )}
          </div>
          <div className="topbar-right">
            <button
              className="demo-mode"
              onClick={() => {
                void checkBackend();
                setAbout(true);
              }}
            >
              <span className="dot" />{" "}
              {backend?.ready ? "Agent đã kết nối" : "Kiểm tra kết nối"}
            </button>
            {view === "chat" && (
              <>
                <button
                  className="icon-button header-export"
                  aria-label="Tải transcript và trace"
                  title="Tải transcript và trace"
                  onClick={exportChat}
                  disabled={!active}
                >
                  <ArrowDownToLine size={18} />
                </button>
                <button
                  className={`icon-button ${inspectorOpen ? "selected" : ""}`}
                  aria-label="Mở bảng kiểm chứng"
                  title="Nguồn, luồng xử lý và context"
                  onClick={() => setInspectorOpen((p) => !p)}
                >
                  <PanelRight size={19} />
                </button>
              </>
            )}
          </div>
        </header>
        {notice && (
          <div className="storage-notice" role="status">
            {notice}
            <button aria-label="Đóng thông báo" onClick={() => setNotice("")}>
              <X size={13} />
            </button>
          </div>
        )}
        <div className="main-body">
          <div className="main-view">
            {view === "chat" ? (
              messages.length === 0 ? (
                <Welcome
                  onSend={send}
                  onStop={stop}
                  busy={busy}
                  config={config}
                  onConfig={() => setSettings(true)}
                  onLibrary={() => navigate("library")}
                />
              ) : (
                <div className="conversation-view">
                  <MessageList
                    messages={messages}
                    busy={busy}
                    stage={stage}
                    progress={progress}
                    onInspect={inspect}
                    onSource={setSourcePage}
                    onSend={send}
                  />
                  <div className="conversation-composer">
                    <Composer
                      onSend={send}
                      onStop={stop}
                      busy={busy}
                      config={config}
                      onConfig={() => setSettings(true)}
                      onLibrary={() => navigate("library")}
                      compact
                    />
                  </div>
                </div>
              )
            ) : view === "library" ? (
              <Library onSource={setSourcePage} onChat={newChat} />
            ) : view === "benchmark" ? (
              <Benchmark onTry={send} />
            ) : (
              <LabGuide onNavigate={navigate} />
            )}
          </div>
          {inspectorOpen && view === "chat" && (
            <>
              <button
                className="inspector-backdrop"
                aria-label="Đóng bảng kiểm chứng"
                onClick={() => setInspectorOpen(false)}
              />
              <EvidencePanel
                trace={inspected.trace}
                liveEvents={liveEvents}
                liveChunks={liveChunks}
                busy={busy}
                config={inspected.config}
                tab={tab}
                onTab={setTab}
                onClose={() => setInspectorOpen(false)}
                onSource={setSourcePage}
              />
            </>
          )}
        </div>
      </main>
      {settings && (
        <Settings
          config={config}
          onChange={setConfig}
          onClose={() => setSettings(false)}
        />
      )}
      {sourcePage !== null && (
        <Modal
          title="Tài liệu gốc · FPT 2025"
          onClose={() => setSourcePage(null)}
          wide
        >
          <div className="pdf-toolbar">
            <div>
              <button
                className="icon-button"
                aria-label="Trang PDF trước"
                disabled={sourcePage === 1}
                onClick={() => setSourcePage((p) => Math.max(1, (p ?? 1) - 1))}
              >
                <ChevronLeft size={17} />
              </button>
              <label>
                Trang PDF
                <input
                  aria-label="Số trang PDF"
                  type="number"
                  min={1}
                  max={232}
                  value={sourcePage}
                  onChange={(e) =>
                    setSourcePage(
                      Math.max(1, Math.min(232, Number(e.target.value) || 1)),
                    )
                  }
                />{" "}
                / 232
              </label>
              <button
                className="icon-button"
                aria-label="Trang PDF sau"
                disabled={sourcePage === 232}
                onClick={() =>
                  setSourcePage((p) => Math.min(232, (p ?? 1) + 1))
                }
              >
                <ChevronRight size={17} />
              </button>
            </div>
            <a
              className="secondary-button"
              href={`/api/document#page=${sourcePage}`}
              target="_blank"
              rel="noreferrer"
            >
              Mở PDF đầy đủ
              <ArrowUpRight size={14} />
            </a>
          </div>
          {[1, 10, 31, 32, 33, 115].includes(sourcePage) ? (
            <Image
              className="pdf-page-image"
              src={`/documents/page-${sourcePage}.png`}
              alt={`Bản gốc trang PDF ${sourcePage}, trang in ${sourcePage - 1}`}
              width={1270}
              height={714}
            />
          ) : (
            <iframe
              key={sourcePage}
              className="pdf-frame"
              title={`Báo cáo FPT, trang PDF ${sourcePage}`}
              src={`/api/document#page=${sourcePage}&toolbar=0&navpanes=0`}
            />
          )}
          <p className="pdf-note">
            Nguồn: {SOURCE.filename} · Trang PDF vật lý {sourcePage}
            {sourcePage > 1 && sourcePage < 232
              ? ` · Trang in ${sourcePage - 1}`
              : ""}
          </p>
        </Modal>
      )}
      {about && (
        <Modal title="Không gian demo Lab 07" onClose={() => setAbout(false)}>
          <div className="about-content">
            <Brand />
            <h3>Khám phá tài liệu, nhìn rõ bằng chứng.</h3>
            <p>
              Chat kết nối agent Python và PostgreSQL của Day 6. Mỗi câu hỏi
              truy xuất báo cáo FPT, gọi model và trả về câu trả lời kèm nguồn.
              Các câu gợi ý cũng chạy qua agent thật.
            </p>
            <div className="about-facts">
              <span>
                <FileText size={16} /> PDF gốc & bộ 240 câu hỏi: dữ liệu thật
              </span>
              <span>
                <GitBranch size={16} /> Chat & trace: kết quả từ backend thật
              </span>
              <span>
                <FlaskConical size={16} /> Điểm số: chỉ hiển thị sau khi nhập
                kết quả
              </span>
            </div>
            <p className="small muted">
              Mỗi lượt chat có sử dụng API model; chi phí được ghi trong trace.
              Hội thoại tương tác chưa qua chấm thủ công và không tự động trở
              thành kết quả benchmark.
            </p>
            <a
              className="text-button"
              href="/animations/animation.lottie"
              target="_blank"
              rel="noreferrer"
            >
              Animation do bạn cung cấp · .lottie
              <ArrowUpRight size={13} />
            </a>
          </div>
        </Modal>
      )}
    </div>
  );
}
