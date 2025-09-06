"use client";

import React, { createContext, useState, useContext, ReactNode } from "react";

interface TooltipContextType {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const TooltipContext = createContext<TooltipContextType | undefined>(undefined);

export function TooltipProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      {children}
    </TooltipContext.Provider>
  );
}

export function Tooltip({ children }: { children: ReactNode }) {
  return <div className="relative inline-block">{children}</div>;
}

export function TooltipTrigger({
  children,
  asChild = false,
}: {
  children: ReactNode;
  asChild?: boolean;
}) {
  const context = useContext(TooltipContext);
  if (!context)
    throw new Error("TooltipTrigger must be used within a TooltipProvider");

  const { setOpen } = context;

  const trigger = asChild ? (
    React.Children.only(children)
  ) : (
    <button type="button">{children}</button>
  );

  const child = trigger as React.ReactElement;
  const originalProps = child.props || {};
  const { onClick: originalOnClick } = originalProps;

  return React.cloneElement(child, {
    onMouseEnter: (e: React.MouseEvent) => {
      setOpen(true);
      if (originalProps.onMouseEnter) originalProps.onMouseEnter(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      setOpen(false);
      if (originalProps.onMouseLeave) originalProps.onMouseLeave(e);
    },
    onFocus: (e: React.FocusEvent) => {
      setOpen(true);
      if (originalProps.onFocus) originalProps.onFocus(e);
    },
    onBlur: (e: React.FocusEvent) => {
      setOpen(false);
      if (originalProps.onBlur) originalProps.onBlur(e);
    },
    onClick: (e: React.MouseEvent) => {
      if (originalOnClick) {
        originalOnClick(e);
      }
    },
  });
}

export function TooltipContent({
  children,
  side = "top",
}: {
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
}) {
  const context = useContext(TooltipContext);
  if (!context)
    throw new Error("TooltipContent must be used within a TooltipProvider");

  const { open } = context;

  if (!open) return null;

  const sideClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-3 whitespace-nowrap",
    right: "left-full top-1/2 -translate-y-1/2 ml-2 whitespace-nowrap",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2 whitespace-nowrap",
    left: "right-full top-1/2 -translate-y-1/2 mr-2 whitespace-nowrap",
  };

  return (
    <div
      className={`absolute z-10 px-3 py-1.5 border border-border-menu text-xs text-white bg-dark-navbar rounded shadow-lg ${sideClasses[side]}`}
    >
      {children}
    </div>
  );
}
