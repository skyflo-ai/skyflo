import React from "react";
import { ToastContainer as ReactToastifyContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export const ToastContainer: React.FC = () => {
  return (
    <ReactToastifyContainer
      position="top-right"
      autoClose={3500}
      hideProgressBar={false}
      newestOnTop
      closeOnClick
      rtl={false}
      pauseOnFocusLoss
      draggable
      pauseOnHover
      theme="dark"
      className="backdrop-blur-sm"
      toastClassName={() =>
        "relative flex p-4 rounded-md justify-between overflow-hidden cursor-pointer my-3"
      }
    />
  );
};

export default ToastContainer;
