"use client";

import React, { useEffect } from "react";
import { MdClose } from "react-icons/md";

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
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleBackdropClick}
      />

      <div
        className={`relative w-full ${sizeClasses[size]} bg-[#171D2B] border border-slate-600/60 rounded-lg shadow-xl shadow-black/20 animate-in fade-in zoom-in duration-200`}
      >
        <div className="flex items-center justify-between p-6 border-b border-slate-600/60">
          <h2 className="text-lg font-semibold text-slate-200">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
            aria-label="Close modal"
          >
            <MdClose className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">{children}</div>
      </div>
    </div>
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
      ? "bg-red-500/20 hover:bg-red-500/30 text-red-400" // HERE
      : "bg-blue-500/10 hover:bg-blue-500/20 text-blue-400";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size={size}>
      <div className="space-y-6">
        <p className="text-slate-300">{message}</p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300/80 bg-slate-700/50 hover:bg-slate-700 rounded-md transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${confirmButtonClass}`}
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
      <form onSubmit={handleSubmit} className="space-y-6">
        {children}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300/80 bg-slate-700/50 hover:bg-slate-700 rounded-md transition-colors"
          >
            {cancelText}
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-500/20 hover:bg-blue-500/30 rounded-md transition-colors"
          >
            {submitText}
          </button>
        </div>
      </form>
    </Modal>
  );
}
