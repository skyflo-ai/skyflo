import React from "react";
import { ToastContainer as ReactToastifyContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export const ToastContainer: React.FC = () => {
  return (
    <>
      <style jsx global>{`
        .Toastify__close-button {
          position: absolute !important;
          top: 8px !important;
          right: 8px !important;
          opacity: 0.7 !important;
          transition: opacity 0.2s !important;
          color: #94a3b8 !important;
          background: rgba(15, 24, 42, 0.8) !important;
          border-radius: 6px !important;
          width: 28px !important;
          height: 28px !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          border: 1px solid rgba(36, 49, 71, 0.6) !important;
        }
        .Toastify__close-button:hover {
          opacity: 1 !important;
          background: rgba(15, 24, 42, 0.95) !important;
          border-color: rgba(36, 49, 71, 0.8) !important;
        }
      `}</style>
      <ReactToastifyContainer
        position="top-right"
        autoClose={3500}
        hideProgressBar={true}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
        className="!p-0 !m-0 !bg-transparent"
        toastClassName="!bg-transparent !p-0 !shadow-none !border-none !rounded-none !mb-3"
        style={{
          zIndex: 9999,
        }}
      />
    </>
  );
};

export default ToastContainer;
