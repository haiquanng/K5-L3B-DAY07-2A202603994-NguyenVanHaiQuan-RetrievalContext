"use client";

import Image from "next/image";
import { FileText, ImageOff, ArrowUpRight } from "lucide-react";
import { useState } from "react";
import type { AnswerImage } from "@/lib/contracts";

function SourceFigure({
  image,
  onSource,
}: {
  image: AnswerImage;
  onSource: (page: number) => void;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <figure
      className={`answer-figure ${image.width < image.height ? "answer-portrait" : ""}`}
    >
      <button
        className="answer-image-preview"
        onClick={() => onSource(image.pdf_page)}
        aria-label={`${image.title}. Mở trang PDF ${image.pdf_page}`}
      >
        {failed ? (
          <span className="answer-image-fallback">
            <ImageOff size={24} aria-hidden />
            Ảnh chưa tải được. Mở trang gốc để xem.
          </span>
        ) : (
          <Image
            src={`/api/agent/asset?chunk=${encodeURIComponent(image.chunk_id)}`}
            alt={image.alt}
            width={image.width}
            height={image.height}
            unoptimized
            onError={() => setFailed(true)}
          />
        )}
        <span className="answer-image-open">
          <ArrowUpRight size={16} aria-hidden />
        </span>
      </button>
      <figcaption>
        <strong>{image.title}</strong>
        <button
          className="answer-image-source"
          onClick={() => onSource(image.pdf_page)}
        >
          <FileText size={13} aria-hidden />
          PDF {image.pdf_page}
          {image.printed_page ? ` · Trang in ${image.printed_page}` : ""}
        </button>
        <span>Ảnh trích từ báo cáo FPT 2025</span>
      </figcaption>
    </figure>
  );
}

export function AnswerImages({
  images,
  onSource,
}: {
  images: AnswerImage[];
  onSource: (page: number) => void;
}) {
  if (!images.length) return null;
  return (
    <div
      className="answer-images"
      role="group"
      aria-label="Hình ảnh từ tài liệu nguồn"
    >
      {images.map((image) => (
        <SourceFigure key={image.chunk_id} image={image} onSource={onSource} />
      ))}
    </div>
  );
}
