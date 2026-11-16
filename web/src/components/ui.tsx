"use client";
import Image from "next/image";
import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
export function Brand({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand ${small ? "brand-small" : ""}`}>
      <Image src="/images/logo.png" alt="" width={42} height={42} priority />
      <span>
        Lumina<span className="brand-caption">RETRIEVAL WORKSPACE</span>
      </span>
    </span>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label={title}
      className={`modal ${wide ? "modal-wide" : ""}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-header">
        <h2>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Đóng hộp thoại"
        >
          <X size={20} />
        </button>
      </div>
      <div className="modal-content">{children}</div>
    </dialog>
  );
}
export function Pill({
  children,
  tone = "purple",
}: {
  children: ReactNode;
  tone?: "purple" | "green" | "neutral" | "amber";
}) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}
export function EmptyMetric({ label }: { label: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>—</strong>
      <small>Chưa có lượt chạy thật</small>
    </div>
  );
}
