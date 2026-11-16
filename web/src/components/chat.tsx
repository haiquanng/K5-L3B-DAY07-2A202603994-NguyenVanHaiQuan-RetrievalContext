"use client";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUp,
  BarChart3,
  Check,
  ChevronDown,
  Copy,
  FileText,
  GitBranch,
  Image as ImageIcon,
  Network,
  Paperclip,
  ScanLine,
  ShieldQuestion,
  SlidersHorizontal,
  Sparkles,
  Square,
} from "lucide-react";
import type { Config, Message } from "@/lib/types";
import { METHOD_LABELS, SUGGESTIONS } from "@/lib/demo";
import { Orb } from "./orb";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentTrace } from "@/lib/contracts";
import { citationMarkdown } from "@/lib/agent-stream";
import { AnswerImages } from "./answer-images";
import { inlineImages, sourceImages } from "@/lib/image-presentation";
export function Composer({
  onSend,
  onStop,
  busy,
  config,
  onConfig,
  onLibrary,
  compact = false,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  config: Config;
  onConfig: () => void;
  onLibrary: () => void;
  compact?: boolean;
}) {
  const [text, setText] = useState("");
  const submit = () => {
    if (text.trim() && !busy) {
      onSend(text.trim());
      setText("");
    }
  };
  return (
    <div className={`composer-wrap ${compact ? "composer-compact" : ""}`}>
      <div className="composer">
        <textarea
          aria-label="Câu hỏi về tài liệu"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Hỏi điều bạn muốn biết về tài liệu…"
          rows={compact ? 2 : 3}
          maxLength={4000}
          disabled={busy}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <div className="composer-bottom">
          <div className="composer-tools">
            <button
              className="icon-button"
              title="Xem tài liệu đang dùng"
              aria-label="Xem tài liệu đang dùng"
              onClick={onLibrary}
            >
              <Paperclip size={18} />
            </button>
            <span className="tool-divider" />
            <button className="composer-option" onClick={onConfig}>
              <Network size={15} />
              {METHOD_LABELS[config.method]}
              <ChevronDown size={12} />
            </button>
            <button className="composer-option mode-option" onClick={onConfig}>
              <ScanLine size={15} />
              {config.mode === "advanced" ? "Đa phương thức" : "Cơ bản"}
            </button>
          </div>
          <button
            className={`send-button ${busy ? "is-stopping" : ""}`}
            disabled={!busy && !text.trim()}
            onClick={busy ? onStop : submit}
            aria-label={busy ? "Dừng phản hồi" : "Gửi câu hỏi"}
          >
            {busy ? (
              <Square size={17} fill="currentColor" />
            ) : (
              <ArrowUp size={21} />
            )}
          </button>
        </div>
      </div>
      <div className="composer-hint">
        <span>
          <span className="dot" /> Câu trả lời từ báo cáo FPT
        </span>
        <span>
          Enter để gửi <span className="hint-divider">·</span> Shift + Enter
          xuống dòng
        </span>
      </div>
    </div>
  );
}
export function Welcome({
  onSend,
  config,
  onConfig,
  onLibrary,
  busy,
  onStop,
}: {
  onSend: (s: string) => void;
  config: Config;
  onConfig: () => void;
  onLibrary: () => void;
  busy: boolean;
  onStop: () => void;
}) {
  const icons = [BarChart3, GitBranch, ImageIcon];
  return (
    <div className="welcome-scroll">
      <div className="welcome">
        <div className="hero">
          <Orb />
          <span className="hero-eyebrow">
            <Sparkles size={12} /> MỘT GÓC NHÌN MỚI TỪ TÀI LIỆU
          </span>
          <h1>
            Chào Quân,
            <br />
            <span>cùng khám phá điều hay.</span>
          </h1>
          <p>
            Từ câu hỏi đến câu trả lời có bằng chứng.
            <br className="mobile-only" /> Rõ nguồn, rõ ngữ cảnh.
          </p>
        </div>
        <div className="welcome-input">
          <button className="document-pill" onClick={onLibrary}>
            <span className="pdf-icon">
              <FileText size={14} />
            </span>
            <span>
              Báo cáo thường niên <strong>FPT 2025</strong>
            </span>
            <span className="document-pill-pages">232 trang</span>
            <ChevronDown size={13} />
          </button>
          <Composer
            {...{ onSend, onStop, busy, config, onConfig, onLibrary }}
          />
        </div>
        <div className="suggestions">
          {SUGGESTIONS.slice(0, 3).map((s, i) => {
            const Icon = icons[i];
            return (
              <button
                key={s.id}
                onClick={() => onSend(s.prompt)}
                disabled={busy}
                className="suggestion"
              >
                <span className={`suggestion-icon suggestion-${i}`}>
                  <Icon size={18} />
                </span>
                <span className="suggestion-title">
                  {s.title}
                  <ArrowRight size={14} />
                </span>
                <span className="suggestion-description">
                  {
                    [
                      "Theo dõi tăng trưởng doanh thu",
                      "Đối chiếu dữ liệu từ nhiều trang",
                      "Đọc cấu trúc công ty từ hình ảnh",
                    ][i]
                  }
                </span>
              </button>
            );
          })}
        </div>
        <button
          className="abstention-prompt"
          onClick={() => onSend(SUGGESTIONS[4].prompt)}
          disabled={busy}
        >
          <ShieldQuestion size={14} /> Nếu tài liệu không có câu trả lời thì
          sao?
          <ArrowRight size={13} />
        </button>
      </div>
      <footer className="welcome-footer">
        <span>THIẾT KẾ CHO NHỮNG CÂU HỎI CÓ CHIỀU SÂU</span>
        <span>
          LAB 07 <span> / </span> AGENTIC RAG
        </span>
      </footer>
    </div>
  );
}
function AssistantMessage({
  message,
  onInspect,
  onSource,
}: {
  message: Message;
  onInspect: (
    trace: AgentTrace,
    config: Config,
    tab: "sources" | "trace",
  ) => void;
  onSource: (p: number) => void;
  onSend: (q: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const trace = message.trace;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <article
      className={`assistant-message ${message.error ? "message-error" : ""}`}
    >
      <div className="assistant-avatar">
        <Image src="/images/logo.png" alt="Lumina" width={27} height={27} />
      </div>
      <div className="assistant-content">
        <div className="assistant-byline">
          <strong>Lumina</strong>
          <span>{trace?.config.model ?? "Trợ lý tài liệu"}</span>
          {trace?.status === "abstain" && (
            <span className="inline-demo">THIẾU BẰNG CHỨNG</span>
          )}
          {message.error && <span className="inline-demo">LỖI KẾT NỐI</span>}
        </div>
        {trace && message.config && (
          <button
            className="trace-summary"
            onClick={() => onInspect(trace, message.config!, "trace")}
          >
            <span
              className={`trace-summary-dot ${trace.status === "abstain" ? "amber" : ""}`}
            />
            {trace.search_calls} lượt truy xuất · {trace.citations.length} nguồn
            trích dẫn
            <ChevronDown size={13} />
          </button>
        )}
        <div className="answer-markdown">
          <Markdown
            remarkPlugins={[remarkGfm]}
            skipHtml
            components={{
              img: () => null,
              a: ({ href, children }) => {
                if (href?.startsWith("#source-")) {
                  let id: string;
                  try {
                    id = decodeURIComponent(href.slice(8));
                  } catch {
                    return <span>{children}</span>;
                  }
                  const chunk = trace?.context.find((c) => c.chunk_id === id);
                  return chunk ? (
                    <button
                      className="inline-citation"
                      title={`Mở trang PDF ${chunk.pdf_page}`}
                      onClick={() => onSource(chunk.pdf_page)}
                    >
                      {children}
                    </button>
                  ) : (
                    <span>{children}</span>
                  );
                }
                return href && /^https?:\/\//.test(href) ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    {children}
                  </a>
                ) : (
                  <span>{children}</span>
                );
              },
              table: ({ children }) => (
                <div className="answer-table">
                  <table>{children}</table>
                </div>
              ),
            }}
          >
            {citationMarkdown(message.text, trace?.citations ?? [])}
          </Markdown>
        </div>
        {trace?.status === "answered" && (
          <AnswerImages images={inlineImages(trace)} onSource={onSource} />
        )}
        {trace && message.config && (
          <>
            <div className="answer-citations">
              {trace.citations.map((id, i) => {
                const chunk = trace.context.find((c) => c.chunk_id === id);
                return chunk ? (
                  <button
                    className="citation-chip"
                    key={id}
                    onClick={() => onInspect(trace, message.config!, "sources")}
                  >
                    <span>{i + 1}</span>
                    <FileText size={13} /> PDF {chunk.pdf_page}
                  </button>
                ) : null;
              })}
            </div>
            <p className="run-metrics">
              {(trace.elapsed_ms / 1000).toLocaleString("vi-VN", {
                maximumFractionDigits: 1,
              })}{" "}
              giây
            </p>
          </>
        )}
        <div className="answer-actions">
          {trace && message.config && sourceImages(trace).length > 0 && (
            <button
              className="text-button"
              onClick={() => onInspect(trace, message.config!, "sources")}
            >
              <ImageIcon size={14} /> Xem ảnh nguồn
            </button>
          )}
          <button
            className="icon-button"
            aria-label={copied ? "Đã sao chép" : "Sao chép câu trả lời"}
            onClick={copy}
          >
            {copied ? <Check size={15} /> : <Copy size={15} />}
          </button>
          {trace && message.config && (
            <button
              className="text-button"
              onClick={() => onInspect(trace, message.config!, "trace")}
            >
              <GitBranch size={14} /> Xem luồng xử lý
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
export function MessageList({
  messages,
  busy,
  stage,
  progress,
  onInspect,
  onSource,
  onSend,
}: {
  messages: Message[];
  busy: boolean;
  stage: number;
  progress: string;
  onInspect: (s: AgentTrace, c: Config, t: "sources" | "trace") => void;
  onSource: (p: number) => void;
  onSend: (q: string) => void;
}) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "end",
    });
  }, [messages.length, busy, stage]);
  return (
    <div className="message-scroll">
      <div className="message-list">
        <div className="conversation-marker">BÁO CÁO THƯỜNG NIÊN FPT 2025</div>
        {messages.map((m) =>
          m.role === "user" ? (
            <div className="user-message" key={m.id}>
              <p>{m.text}</p>
              <span className="user-message-avatar">Q</span>
            </div>
          ) : (
            <AssistantMessage
              key={m.id}
              message={m}
              {...{ onInspect, onSource, onSend }}
            />
          ),
        )}
        {busy && (
          <div className="working-message" role="status">
            <Image src="/images/logo.png" alt="" width={28} height={28} />
            <div>
              <span>{progress || "Đang xử lý câu hỏi…"}</span>
              <div className="working-dots">
                <i />
                <i />
                <i />
              </div>
            </div>
            <small>ĐANG CHẠY</small>
          </div>
        )}
        <div ref={end} />
      </div>
    </div>
  );
}
