"use client";

import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MdClose } from "react-icons/md";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = "md",
}: ModalProps) {
  const [mounted, setMounted] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<Element | null>(null);
  const titleId = useId();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    openerRef.current = document.activeElement;
    document.body.style.overflow = "hidden";

    const raf = requestAnimationFrame(() => {
      if (!modalRef.current) return;
      const first = modalRef.current.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      if (first) {
        first.focus();
      } else {
        modalRef.current.focus();
      }
    });

    return () => {
      cancelAnimationFrame(raf);
      document.body.style.overflow = "unset";
      if (openerRef.current instanceof HTMLElement) {
        openerRef.current.focus();
      }
    };
  }, [isOpen]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }

      if (event.key === "Tab" && modalRef.current) {
        const focusable = Array.from(
          modalRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
        );
        if (focusable.length === 0) {
          event.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    },
    [onClose],
  );

  if (!isOpen || !mounted) return null;

  const sizeClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
  };

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleBackdropClick}
      />

      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`relative w-full ${sizeClasses[size]} bg-zinc-950/95 backdrop-blur-md border border-white/[0.08] rounded-xl shadow-2xl animate-in fade-in zoom-in duration-200 outline-none`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
          <h2 id={titleId} className="text-sm font-medium text-zinc-200">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-white/[0.06] text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <MdClose className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "default";
  size?: "sm" | "md" | "lg";
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  size = "sm",
}: ConfirmModalProps) {
  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const confirmButtonClass =
    variant === "danger"
      ? "bg-rose-500/10 border border-rose-500/20 hover:border-rose-500/30 hover:bg-rose-500/15 text-rose-400"
      : "bg-blue-500/10 border border-blue-500/20 hover:border-blue-500/30 hover:bg-blue-500/15 text-blue-400";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size={size}>
      <div className="space-y-5">
        <p className="text-sm text-zinc-400">{message}</p>

        <div className="flex justify-end gap-2.5">
          <button
            onClick={onClose}
            className="px-3.5 py-2 text-xs font-medium text-zinc-400 bg-white/[0.04] border border-white/[0.06] hover:border-white/[0.1] hover:text-zinc-300 rounded-lg transition-colors duration-200 cursor-pointer"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`px-3.5 py-2 text-xs font-medium rounded-lg transition-colors duration-200 cursor-pointer ${confirmButtonClass}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
}

interface InputModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (formData: FormData) => void;
  title: string;
  children: React.ReactNode;
  submitText?: string;
  cancelText?: string;
  size?: "sm" | "md" | "lg";
}

export function InputModal({
  isOpen,
  onClose,
  onSubmit,
  title,
  children,
  submitText = "Save",
  cancelText = "Cancel",
  size = "sm",
}: InputModalProps) {
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    onSubmit(formData);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size={size}>
      <form onSubmit={handleSubmit} className="space-y-5">
        {children}

        <div className="flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 text-xs font-medium text-zinc-400 bg-white/[0.04] border border-white/[0.06] hover:border-white/[0.1] hover:text-zinc-300 rounded-lg transition-colors duration-200 cursor-pointer"
          >
            {cancelText}
          </button>
          <button
            type="submit"
            className="px-3.5 py-2 text-xs font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 hover:border-blue-500/30 hover:bg-blue-500/15 rounded-lg transition-colors duration-200 cursor-pointer"
          >
            {submitText}
          </button>
        </div>
      </form>
    </Modal>
  );
}
