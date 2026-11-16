"use client";
import Image from "next/image";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Check,
  FileText,
  Fingerprint,
  ImageIcon,
  Layers3,
  RefreshCw,
  Table2,
  BarChart3,
} from "lucide-react";
import type { BackendHealth } from "@/lib/contracts";
import { SOURCE } from "@/lib/demo";
import { Pill } from "./ui";
export function Library({
  onSource,
  onChat,
}: {
  onSource: (page: number) => void;
  onChat: () => void;
}) {
  const [status, setStatus] = useState<"loading" | "available" | "error">(
    "loading",
  );
  const [bytes, setBytes] = useState(0);
  const [index, setIndex] = useState<BackendHealth | null>(null);
  const check = async () => {
    setStatus("loading");
    try {
      const [response, health] = await Promise.all([
        fetch("/api/document?meta=1"),
        fetch("/api/agent/health", { cache: "no-store" }).catch(() => null),
      ]);
      setIndex(health?.ok ? ((await health.json()) as BackendHealth) : null);
      if (!response.ok) throw Error();
      const data = await response.json();
      setBytes(data.bytes);
      setStatus("available");
    } catch {
      setStatus("error");
    }
  };
  useEffect(() => {
    void check();
  }, []);
  return (
    <div className="page-scroll">
      <div className="content-page">
        <div className="page-intro">
          <div>
            <span className="eyebrow">YOUR KNOWLEDGE, CONNECTED</span>
            <h1>Thư viện nguồn</h1>
            <p>Một tài liệu. Mọi bằng chứng đều có điểm bắt đầu.</p>
          </div>
          <button
            className="secondary-button"
            onClick={() => void check()}
            disabled={status === "loading"}
          >
            <RefreshCw
              size={15}
              className={status === "loading" ? "spin" : ""}
            />{" "}
            Kiểm tra nguồn
          </button>
        </div>
        <div className="source-library-grid">
          <div
            className="document-cover"
            onClick={() => onSource(1)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSource(1);
            }}
            aria-label="Mở báo cáo FPT"
          >
            <Image
              src="/documents/page-1.png"
              alt="Bìa Báo cáo thường niên FPT 2025"
              width={635}
              height={357}
            />
            <span>
              <BookOpen size={15} /> Mở tài liệu gốc
              <ArrowUpRight size={15} />
            </span>
          </div>
          <div className="document-info">
            <Pill
              tone={
                status === "available"
                  ? "green"
                  : status === "error"
                    ? "amber"
                    : "neutral"
              }
            >
              <span className="dot" />
              {status === "available"
                ? "PDF local sẵn sàng"
                : status === "error"
                  ? "Chưa tìm thấy file PDF"
                  : "Đang kiểm tra tài liệu"}
            </Pill>
            <h2>
              Báo cáo thường niên
              <br />
              FPT 2025
            </h2>
            <p className="filename">{SOURCE.filename}</p>
            <div className="document-facts">
              <div>
                <strong>232</strong>
                <span>trang PDF</span>
              </div>
              <div>
                <strong>4</strong>
                <span>loại nội dung</span>
              </div>
              <div>
                <strong>
                  {bytes ? (bytes / 1024 / 1024).toFixed(1) : "—"}
                </strong>
                <span>MB</span>
              </div>
            </div>
            <button className="primary-button" onClick={onChat}>
              <FileText size={16} /> Trò chuyện với tài liệu
              <ArrowUpRight size={15} />
            </button>
          </div>
        </div>
        <div className="section-heading">
          <div>
            <h2>Toàn vẹn nguồn & index</h2>
            <p>Giữ liên kết về trang gốc cho từng loại nội dung.</p>
          </div>
          <Pill tone={index ? "green" : "amber"}>
            {index
              ? `${index.chunks} chunk · ${index.embeddings} embedding`
              : "Chưa kết nối index"}
          </Pill>
        </div>
        <div className="modality-grid">
          {[
            {
              icon: FileText,
              name: "Văn bản",
              kinds: ["text"],
              hint: "Nội dung, tiêu đề, chú thích",
            },
            {
              icon: Table2,
              name: "Bảng số liệu",
              kinds: ["table"],
              hint: "Hàng, cột, đơn vị và kỳ báo cáo",
            },
            {
              icon: BarChart3,
              name: "Biểu đồ",
              kinds: ["chart"],
              hint: "Trục, chú giải và giá trị",
            },
            {
              icon: ImageIcon,
              name: "Ảnh & sơ đồ",
              kinds: ["photo", "diagram", "infographic"],
              hint: "Vùng ảnh và quan hệ trực quan",
            },
          ].map((m) => (
            <div className="modality-card" key={m.name}>
              <m.icon size={21} />
              <h3>{m.name}</h3>
              <p>{m.hint}</p>
              <span>
                <span className="dot" />{" "}
                {index
                  ? `${m.kinds.reduce((n, kind) => n + (index.chunks_by_kind[kind] ?? 0), 0)} chunk`
                  : "Chờ kết nối backend"}
              </span>
            </div>
          ))}
        </div>
        <div className="source-bottom-grid">
          <div className="surface-card">
            <div className="card-heading">
              <Fingerprint size={18} />
              <h3>Phiên bản nguồn</h3>
            </div>
            <dl className="detail-list">
              <dt>Source ID</dt>
              <dd>{SOURCE.id}</dd>
              <dt>Năm báo cáo</dt>
              <dd>2025</dd>
              <dt>Trang PDF / trang in</dt>
              <dd>Ví dụ: PDF 31 → trang in 30</dd>
              <dt>SHA-256 chuẩn</dt>
              <dd className="hash">{SOURCE.sha256}</dd>
            </dl>
            <small>
              Hash tham chiếu từ benchmark. Kiểm tra byte bằng công cụ validate
              khi đánh giá.
            </small>
          </div>
          <div className="surface-card">
            <div className="card-heading">
              <Layers3 size={18} />
              <h3>Coverage theo trang</h3>
            </div>
            <div className="coverage-figure">
              <strong>
                {index?.indexed_pages ?? "—"} <span>/ 232</span>
              </strong>
              <Pill tone="neutral">
                {index
                  ? `${index.ledger.length} trang có ledger`
                  : "Chờ ledger"}
              </Pill>
            </div>
            <div
              className="page-ledger"
              aria-label="Trạng thái index của từng trang PDF"
            >
              {Array.from({ length: 232 }, (_, i) => {
                const page = index?.ledger.find((p) => p.pdf_page === i + 1);
                return (
                  <button
                    key={i}
                    className={page?.status ?? "pending"}
                    aria-label={`Trang ${i + 1}: ${page?.status ?? "chưa có dữ liệu"}`}
                    title={`PDF ${i + 1}: ${page?.chunks ?? "?"} chunk${page?.reason ? ` — ${page.reason}` : ""}`}
                    onClick={() => onSource(i + 1)}
                  />
                );
              })}
            </div>
            <p className="muted small">
              {index
                ? "Ô tím: có chunk. Ô vàng: bỏ có lý do (trang mở chương). Bấm một ô để mở trang gốc. Thống kê đọc trực tiếp từ PostgreSQL."
                : "Khởi động backend để đọc ledger và số chunk thực tế từ database."}
            </p>
          </div>
        </div>
        <div className="library-footnote">
          <Check size={15} /> Đang dùng cùng một PDF cho phần cơ bản và
          advanced.
          <a
            href="https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien"
            target="_blank"
            rel="noreferrer"
          >
            Nguồn công bố
            <ArrowUpRight size={13} />
          </a>
        </div>
      </div>
    </div>
  );
}
