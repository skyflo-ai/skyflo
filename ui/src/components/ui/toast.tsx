import React, { FC } from "react";
import { toast, ToastOptions, TypeOptions } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {
  HiMiniSparkles,
  HiCheckCircle,
  HiExclamationTriangle,
  HiXCircle,
} from "react-icons/hi2";

interface ToastContentProps {
  message: string;
  type: TypeOptions;
  heading?: string;
}

const ToastContent: FC<ToastContentProps> = ({ message, type, heading }) => {
  const getIconAndColor = () => {
    switch (type) {
      case "success":
        return {
          icon: <HiCheckCircle className="w-6 h-6 text-green-400" />,
        };
      case "error":
        return {
          icon: <HiXCircle className="w-6 h-6 text-red-400" />,
        };
      case "warning":
        return {
          icon: <HiExclamationTriangle className="w-6 h-6 text-yellow-400" />,
        };
      case "info":
      default:
        return {
          icon: <HiMiniSparkles className="w-6 h-6 text-blue-400" />,
        };
    }
  };

  const { icon } = getIconAndColor();

  return (
    <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] p-4 rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 backdrop-blur-sm flex items-center gap-4 min-w-[320px]">
      <div
        className={`p-2.5 rounded-lg flex items-center justify-center flex-shrink-0`}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-slate-100 mb-1 truncate">
          {heading || type.charAt(0).toUpperCase() + type.slice(1)}
        </h3>
        <p className="text-sm text-slate-300 break-words">{message}</p>
      </div>
    </div>
  );
};

const defaultOptions: ToastOptions = {
  position: "top-right",
  autoClose: 3500,
  hideProgressBar: true,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  className: "!bg-transparent !p-0 !shadow-none !border-none !rounded-none",
  style: {
    background: "transparent",
    padding: 0,
    margin: 0,
    boxShadow: "none",
    border: "none",
  },
};

const approvalRequiredOptions: ToastOptions = {
  position: "top-right",
  autoClose: 5000,
  hideProgressBar: true,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  className: "!bg-transparent !p-0 !shadow-none !border-none !rounded-none",
  style: {
    background: "transparent",
    padding: 0,
    margin: 0,
    boxShadow: "none",
    border: "none",
  },
};

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
      ...defaultOptions.style,
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
        ...approvalRequiredOptions.style,
        ...toastStyle?.style,
      },
      icon: false,
      ...options,
    }
  );
};

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
