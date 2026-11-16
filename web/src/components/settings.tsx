"use client";
import { Check, Layers3, Network, ScanLine, Settings2 } from "lucide-react";
import type { Config, Method } from "@/lib/types";
import { METHOD_LABELS } from "@/lib/demo";
import { Modal, Pill } from "./ui";
export function Settings({
  config,
  onChange,
  onClose,
}: {
  config: Config;
  onChange: (c: Config) => void;
  onClose: () => void;
}) {
  const update = (patch: Partial<Config>) => onChange({ ...config, ...patch });
  return (
    <Modal title="Cấu hình truy xuất" onClose={onClose}>
      <p className="muted settings-description">
        Thiết lập được áp dụng cho các lượt chat tiếp theo. Các lượt trước giữ
        nguyên cấu hình và trace.
      </p>
      <label className="field-label">Phạm vi</label>
      <div className="setting-mode">
        {(["basic", "advanced"] as const).map((m) => (
          <button
            key={m}
            className={config.mode === m ? "active" : ""}
            onClick={() => update({ mode: m })}
          >
            <ScanLine size={17} />
            <strong>{m === "basic" ? "Cơ bản" : "Advanced"}</strong>
            <span>
              {m === "basic" ? "Đọc text đã index" : "Có thể xem ảnh crop gốc"}
            </span>
            {config.mode === m && <Check size={15} />}
          </button>
        ))}
      </div>
      <label className="field-label">Phương pháp retrieval</label>
      <div className="method-options">
        {(["lexical", "dense", "hybrid"] as Method[]).map((m) => (
          <button
            key={m}
            className={config.method === m ? "active" : ""}
            onClick={() =>
              update({ method: m, rerank: m === "hybrid" && config.rerank })
            }
          >
            <Network size={16} />
            {METHOD_LABELS[m]}
            {config.method === m && <Check size={14} />}
          </button>
        ))}
      </div>
      <div className="slider-field">
        <label htmlFor="top-k">
          Top-k cho context <Pill tone="neutral">Top-{config.topK}</Pill>
        </label>
        <input
          id="top-k"
          type="range"
          min={3}
          max={20}
          value={config.topK}
          onChange={(e) => update({ topK: Number(e.target.value) })}
        />
        <div>
          <span>3</span>
          <span>20</span>
        </div>
      </div>
      <div className="settings-two">
        <label>
          Ngân sách context
          <select
            value={config.budget}
            onChange={(e) => update({ budget: Number(e.target.value) })}
          >
            {[4096, 8192, 16384, 24000].map((v) => (
              <option key={v} value={v}>
                {v.toLocaleString("vi-VN")} ký tự
              </option>
            ))}
          </select>
        </label>
        <label>
          Giới hạn bước model
          <select
            value={config.maxSteps}
            onChange={(e) => update({ maxSteps: Number(e.target.value) })}
          >
            {[2, 3, 4, 6].map((v) => (
              <option key={v} value={v}>
                {v} bước
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="toggle-row">
        <span>
          <Layers3 size={18} />
          <span>
            <strong>Reranking</strong>
            <small>Hybrid top-20 → model xếp hạng lại; thêm chi phí API</small>
          </span>
        </span>
        <button
          className={`switch ${config.rerank ? "on" : ""}`}
          role="switch"
          aria-checked={config.rerank}
          aria-label="Bật reranking"
          onClick={() => update({ rerank: !config.rerank, method: "hybrid" })}
        >
          <span />
        </button>
      </div>
      <div className="toggle-row">
        <span>
          <Settings2 size={18} />
          <span>
            <strong>Mở rộng cùng trang</strong>
            <small>
              Cho phép agent gọi open_page để lấy thêm đoạn cùng trang
            </small>
          </span>
        </span>
        <button
          className={`switch ${config.neighbors ? "on" : ""}`}
          role="switch"
          aria-checked={config.neighbors}
          aria-label="Bật neighbor context"
          onClick={() => update({ neighbors: !config.neighbors })}
        >
          <span />
        </button>
      </div>
      <div className="settings-footer">
        <span>Các lượt trước giữ cấu hình ban đầu.</span>
        <button className="primary-button" onClick={onClose}>
          Hoàn tất
          <Check size={16} />
        </button>
      </div>
    </Modal>
  );
}
