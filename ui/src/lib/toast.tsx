import React, { FC } from "react";
import { toast, ToastOptions, TypeOptions } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { HiMiniSparkles } from "react-icons/hi2";

interface ToastContentProps {
  message: string;
  type: TypeOptions;
  heading?: string;
}

const ToastContent: FC<ToastContentProps> = ({ message, type, heading }) => (
  <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] p-4 rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 backdrop-blur-sm flex items-center gap-4">
    {type === "info" && (
      <div className="bg-gradient-to-r from-blue-600/20 to-[#0A1525] p-2.5 rounded-lg flex items-center justify-center">
        <HiMiniSparkles className="w-6 h-6 text-blue-400" />
      </div>
    )}
    <div className="flex-1">
      <h3 className="text-sm font-semibold text-slate-100 mb-1">
        {heading || type.charAt(0).toUpperCase() + type.slice(1)}
      </h3>
      <p className="text-sm text-slate-300">{message}</p>
    </div>
  </div>
);

// Default toast configuration to match Skyflo.ai design system
const defaultOptions: ToastOptions = {
  position: "top-right",
  autoClose: 3500,
  hideProgressBar: true,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  className: "!bg-transparent !p-0 !shadow-none",
};

const approvalRequiredOptions: ToastOptions = {
  position: "top-right",
  autoClose: 5000,
  hideProgressBar: true,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  className: "!bg-transparent !p-0 !shadow-none",
};

// Custom toast styles by type
const toastStyles = {
  success: {
    style: {
      background: "transparent",
      padding: 0,
      margin: 0,
    },
    icon: true,
  },
  error: {
    style: {
      background: "transparent",
      padding: 0,
      margin: 0,
    },
    icon: true,
  },
  info: {
    style: {
      background: "transparent",
      padding: 0,
      margin: 0,
    },
    icon: true,
  },
  warning: {
    style: {
      background: "transparent",
      padding: 0,
      margin: 0,
    },
    icon: true,
  },
};

// Toast API
export const showToast = (
  message: string,
  type: TypeOptions = "default",
  options?: ToastOptions
) => {
  const toastStyle = toastStyles[type as keyof typeof toastStyles];

  return toast(<ToastContent message={message} type={type} />, {
    ...defaultOptions,
    type,
    style: {
      ...toastStyle?.style,
    },
    icon: false,
    ...options,
  });
};

const approvalRequiredToast = (
  heading: string,
  message: string,
  options?: ToastOptions
) => {
  const toastStyle = toastStyles["info" as keyof typeof toastStyles];

  return toast(
    <ToastContent message={message} type="info" heading={heading} />,
    {
      ...approvalRequiredOptions,
      type: "info",
      style: {
        ...toastStyle?.style,
      },
      icon: false,
      ...options,
    }
  );
};

// Helper functions for specific toast types
export const showSuccess = (message: string, options?: ToastOptions) =>
  showToast(message, "success", options);

export const showError = (message: string, options?: ToastOptions) =>
  showToast(message, "error", options);

export const showInfo = (message: string, options?: ToastOptions) =>
  showToast(message, "info", options);

export const showWarning = (message: string, options?: ToastOptions) =>
  showToast(message, "warning", options);

export const showApprovalRequired = (
  heading: string,
  message: string,
  options?: ToastOptions
) => approvalRequiredToast(heading, message, options);
