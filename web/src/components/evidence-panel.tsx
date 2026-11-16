"use client";
import Image from "next/image";
import { useState } from "react";
import {
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  FileSearch,
  FileText,
  GitBranch,
  ScanText,
  X,
} from "lucide-react";
import type { Config } from "@/lib/types";
import type { AgentTrace, Chunk, TraceEvent } from "@/lib/contracts";
import { Pill } from "./ui";
import { AnswerImages } from "./answer-images";
import { sourceImages } from "@/lib/image-presentation";
export type InspectorTab = "sources" | "trace" | "context";
const KIND_LABELS: Record<string, string> = {
  text: "Văn bản",
  table: "Bảng",
  chart: "Biểu đồ",
  photo: "Ảnh",
  diagram: "Sơ đồ",
  infographic: "Infographic",
};
const EVENT_LABELS: Record<string, string> = {
  search: "Truy xuất",
  open_page: "Mở rộng cùng trang",
  view_image: "Xem ảnh vùng nguồn",
  answer: "Hoàn tất",
  citation_repair: "Kiểm tra lại citation",
  invalid_or_missing_citations: "Citation không hợp lệ",
  step_limit: "Đạt giới hạn bước",
  citation_expansion: "Mở rộng citation",
};
function SourceCard({
  chunk,
  index,
  onSource,
}: {
  chunk: Chunk;
  index: number;
  onSource: (p: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [noImage, setNoImage] = useState(false);
  return (
    <div className="source-card">
      <div className="source-top">
        <span className="source-number">{index + 1}</span>
        <span>FPT · Báo cáo 2025</span>
        <Pill tone="neutral">PDF {chunk.pdf_page}</Pill>
      </div>
      <h3>
        {chunk.title || KIND_LABELS[chunk.kind]} · trang {chunk.pdf_page}
      </h3>
      <button
        className={`source-preview ${chunk.kind === "photo" ? "source-preview-photo" : ""}`}
        onClick={() => onSource(chunk.pdf_page)}
        aria-label={`Mở trang PDF ${chunk.pdf_page}`}
      >
        {!noImage && (
          <Image
            src={`/api/agent/asset?chunk=${encodeURIComponent(chunk.chunk_id)}`}
            alt={`Vùng gốc của ${chunk.chunk_id}`}
            width={635}
            height={357}
            unoptimized
            onError={() => setNoImage(true)}
          />
        )}
        <span>
          Xem trang gốc <ArrowUpRight size={13} />
        </span>
      </button>
      <p className="source-quote">
        {chunk.text.slice(0, 650)}
        {chunk.text.length > 650 ? "…" : ""}
      </p>
      <button
        className="text-button source-detail"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Vị
        trí & metadata
      </button>
      {expanded && (
        <div className="metadata">
          <code>{chunk.chunk_id}</code>
          <span>
            Trang in {chunk.printed_page ?? "—"} · {KIND_LABELS[chunk.kind]}
          </span>
          <p>
            Vùng PDF (points): {chunk.bbox.map((n) => n.toFixed(1)).join(", ")}
          </p>
        </div>
      )}
    </div>
  );
}
export function EvidencePanel({
  trace,
  config,
  liveEvents,
  liveChunks,
  busy,
  tab,
  onTab,
  onClose,
  onSource,
}: {
  trace?: AgentTrace;
  config: Config;
  liveEvents: TraceEvent[];
  liveChunks: Chunk[];
  busy: boolean;
  tab: InspectorTab;
  onTab: (t: InspectorTab) => void;
  onClose: () => void;
  onSource: (page: number) => void;
}) {
  const chunks = trace?.context ?? liveChunks;
  const citations = trace
    ? trace.citations.flatMap((id) => {
        const chunk = chunks.find((c) => c.chunk_id === id);
        return chunk ? [chunk] : [];
      })
    : [];
  const events = trace?.events ?? liveEvents;
  const relatedImages = sourceImages(trace).filter(
    (image) => !citations.some((chunk) => chunk.chunk_id === image.chunk_id),
  );
  const chars =
    trace?.context_chars ?? chunks.reduce((n, c) => n + c.text.length, 0);
  const budget = trace?.config.budget_chars ?? config.budget;
  return (
    <aside className="inspector" aria-label="Kiểm tra bằng chứng">
      <div className="inspector-heading">
        <div>
          <span className="eyebrow">BEHIND THE ANSWER</span>
          <h2>Kiểm chứng câu trả lời</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Đóng bảng kiểm chứng"
        >
          <X size={18} />
        </button>
      </div>
      <div
        className="inspector-tabs"
        role="tablist"
        aria-label="Bằng chứng và trace"
      >
        {(
          [
            ["sources", "Nguồn"],
            ["trace", "Luồng xử lý"],
            ["context", "Context"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            id={`inspect-${id}`}
            role="tab"
            aria-controls="inspector-panel"
            aria-selected={tab === id}
            onClick={() => onTab(id)}
            className={tab === id ? "active" : ""}
          >
            {label}
            {id === "sources" && <span>{citations.length}</span>}
          </button>
        ))}
      </div>
      <div
        className="inspector-content"
        id="inspector-panel"
        role="tabpanel"
        aria-labelledby={`inspect-${tab}`}
      >
        <div className="demo-note">
          <span className="dot" />
          {trace
            ? "Trace từ agent thật · chưa chấm chất lượng"
            : busy
              ? "Đang nhận tiến trình từ backend"
              : "Gửi câu hỏi để xem bằng chứng"}
        </div>
        {tab === "sources" && (
          <>
            <p className="panel-description">
              Các vùng được trích trong câu trả lời. Mở bản gốc để kiểm tra nội
              dung và điều kiện.
            </p>
            {relatedImages.length > 0 && (
              <section
                className="related-source-images"
                aria-label="Ảnh liên quan"
              >
                <h3>Ảnh liên quan trong báo cáo</h3>
                <AnswerImages images={relatedImages} onSource={onSource} />
              </section>
            )}
            {citations.length ? (
              citations.map((chunk, index) => (
                <SourceCard
                  key={chunk.chunk_id}
                  {...{ chunk, index, onSource }}
                />
              ))
            ) : (
              <div className="panel-empty">
                <FileSearch size={30} />
                <h3>{busy ? "Đang tìm nguồn" : "Chưa có nguồn được trích"}</h3>
                <p>
                  {trace?.status === "abstain"
                    ? "Agent chưa tìm được đủ bằng chứng cho phần được hỏi."
                    : "Nguồn sẽ xuất hiện khi agent hoàn tất câu trả lời."}
                </p>
              </div>
            )}
          </>
        )}
        {tab === "trace" && (
          <>
            <p className="panel-description">
              Query và kết quả tool thực tế, theo thứ tự chạy. Không hiển thị
              suy nghĩ nội bộ của model.
            </p>
            <ol className="trace-timeline">
              {events.map((event, index) => (
                <li key={index}>
                  <span className="trace-icon">
                    <GitBranch size={16} />
                  </span>
                  <div>
                    <h3>
                      {EVENT_LABELS[event.event] ?? event.event}
                      {event.event === "search" && ` · ${event.method}`}
                    </h3>
                    {event.query && (
                      <div className="query-box">
                        <small>
                          {index === 0 ? "QUERY GỐC" : "QUERY BỔ SUNG"}
                        </small>
                        <span>{event.query}</span>
                      </div>
                    )}
                    {event.pdf_page && (
                      <button
                        className="text-button"
                        onClick={() => onSource(event.pdf_page!)}
                      >
                        PDF {event.pdf_page} <ArrowUpRight size={12} />
                      </button>
                    )}
                    {event.chunk_id && <code>{event.chunk_id}</code>}
                    {event.elapsed_ms !== undefined && (
                      <p>
                        {event.elapsed_ms.toFixed(0)} ms ·{" "}
                        {event.results?.length ?? 0} candidate
                      </p>
                    )}
                    {event.shown_to_model && (
                      <p>
                        {event.shown_to_model.length} candidate được xét vào
                        context (sau đó áp dụng budget).
                      </p>
                    )}
                    {event.results?.length ? (
                      <details className="rank-details">
                        <summary>Candidate, rank & score</summary>
                        <ol>
                          {event.results.map((result, i) =>
                            typeof result === "string" ? (
                              <li key={`${result}-${i}`}>
                                <code>{result}</code>
                              </li>
                            ) : (
                              <li key={`${result.chunk_id}-${i}`}>
                                <button
                                  className="text-button"
                                  onClick={() =>
                                    result.pdf_page && onSource(result.pdf_page)
                                  }
                                >
                                  #{result.rank ?? i + 1} · PDF{" "}
                                  {result.pdf_page} · {result.kind}
                                </button>
                                <code>{result.chunk_id}</code>
                                <small>Score: {result.score ?? "—"}</small>
                              </li>
                            ),
                          )}
                        </ol>
                      </details>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
            {trace && (
              <div className="trace-footer">
                <span>Model</span>
                <strong>{trace.config.model}</strong>
                <span>Thời gian / chi phí</span>
                <strong>
                  {(trace.elapsed_ms / 1000).toFixed(1)} s /{" "}
                  {trace.cost_usd === null
                    ? "—"
                    : `$${trace.cost_usd.toFixed(4)}`}
                </strong>
                <span>Token vào / ra</span>
                <strong>
                  {trace.usage.input.toLocaleString()} /{" "}
                  {trace.usage.output.toLocaleString()}
                </strong>
                <span>Lượt model / giới hạn</span>
                <strong>
                  {trace.model_calls} / {trace.config.max_steps}
                </strong>
                <span>Điều kiện dừng</span>
                <strong>{trace.stop_reason}</strong>
              </div>
            )}
          </>
        )}
        {tab === "context" && (
          <>
            <div className="context-budget">
              <span>Text bằng chứng đã gửi model</span>
              <strong>
                {chars.toLocaleString("vi-VN")}{" "}
                <small>/ {budget.toLocaleString("vi-VN")} ký tự</small>
              </strong>
              <div className="progress-track">
                <span
                  style={{ width: `${Math.min(100, (chars / budget) * 100)}%` }}
                />
              </div>
              <small>
                {chunks.length} chunk sau loại trùng ·{" "}
                {trace?.dropped_for_budget.length ?? 0} đoạn bỏ do budget. Ngân
                sách không bao gồm prompt, lịch sử chat và ảnh.
              </small>
            </div>
            {chunks.map((chunk, i) => (
              <div className="context-chunk" key={chunk.chunk_id}>
                <div>
                  <span>CHUNK {String(i + 1).padStart(2, "0")}</span>
                  <button
                    className="text-button"
                    onClick={() => onSource(chunk.pdf_page)}
                  >
                    <FileText size={12} /> PDF {chunk.pdf_page}
                  </button>
                </div>
                <code>{chunk.chunk_id}</code>
                <p>{chunk.text}</p>
              </div>
            ))}
            {!chunks.length && (
              <div className="panel-empty">
                <ScanText size={28} />
                <p>Chưa có context từ backend.</p>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
