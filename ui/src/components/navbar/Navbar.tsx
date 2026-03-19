"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import {
  MdLogout,
  MdSettings,
  MdAdd,
  MdBarChart,
  MdSearch,
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from "react-icons/md";
import { FaGithub } from "react-icons/fa";
import { FiLayers } from "react-icons/fi";

import { useAuth } from "@/components/auth/AuthProvider";
import { useRouter, usePathname } from "next/navigation";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import SidebarHistory from "./SidebarHistory";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { logout } = useAuth();

  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("sidebar-expanded") !== "false";
    }
    return true;
  });

  const [isCollapsedRailHovered, setIsCollapsedRailHovered] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const toggleSidebar = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-expanded", String(next));
      return next;
    });
  }, []);

  const handleLogoutOnClick = async () => {
    await logout();
  };

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setIsExpanded((prev) => {
        if (prev) return prev;
        localStorage.setItem("sidebar-expanded", "true");
        return true;
      });
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <nav
      className={`relative h-screen ${
        isExpanded ? "w-[264px]" : "w-[68px]"
      } bg-dark-navbar flex flex-col border-r border-border shrink-0 overflow-hidden transition-[width] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]`}
    >
      <div
        className={`absolute inset-0 flex flex-col transition-all duration-300 ease-out ${
          isExpanded
            ? "opacity-100 translate-x-0 pointer-events-auto"
            : "opacity-0 -translate-x-2 pointer-events-none"
        }`}
      >
        <div className="flex items-center justify-between px-3 pt-4 pb-3">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2.5 cursor-pointer"
            aria-label="Go to home page"
          >
            <Image
              src="/logo_vector_transparent.png"
              alt="logo"
              width={28}
              height={28}
              className="rounded-full"
            />
            <span className="text-sm font-semibold text-white tracking-tight">
              Skyflo
            </span>
          </button>
          <SidebarToggleButton
            isExpanded={isExpanded}
            tooltip="Collapse sidebar"
            onClick={toggleSidebar}
          />
        </div>

        <div className="px-2 mt-2 space-y-1 mb-1">
          <SidebarNavItem
            icon={<MdAdd size={20} />}
            label="New Chat"
            onClick={() => router.push("/")}
            isActive={pathname === "/"}
          />
          <SidebarNavItem
            icon={<FiLayers size={20} />}
            label="Integrations"
            onClick={() => router.push("/integrations")}
            isActive={pathname === "/integrations"}
          />
          <SidebarNavItem
            icon={<MdBarChart size={20} />}
            label="Analytics"
            onClick={() => router.push("/analytics")}
            isActive={pathname === "/analytics"}
          />
        </div>

        <SidebarHistory searchInputRef={searchInputRef} />

        <div className="border-t border-border px-2 py-3 space-y-1">
          <SidebarNavItem
            icon={<FaGithub size={20} />}
            label="GitHub"
            href="https://github.com/skyflo-ai/skyflo"
            target="_blank"
            rel="noopener noreferrer"
          />
          <SidebarNavItem
            icon={<MdSettings size={20} />}
            label="Settings"
            onClick={() => router.push("/settings")}
            isActive={pathname === "/settings"}
          />
          <SidebarNavItem
            icon={<MdLogout size={20} />}
            label="Logout"
            onClick={handleLogoutOnClick}
          />
        </div>
      </div>

      <div
        className={`absolute inset-0 flex flex-col cursor-e-resize transition-all duration-300 ease-out ${
          isExpanded
            ? "opacity-0 translate-x-2 pointer-events-none"
            : "opacity-100 translate-x-0 pointer-events-auto"
        }`}
        onMouseEnter={() => setIsCollapsedRailHovered(true)}
        onMouseLeave={() => setIsCollapsedRailHovered(false)}
        onClick={() => {
          if (!isExpanded) {
            toggleSidebar();
          }
        }}
      >
        <div className="flex items-center justify-center pt-4 pb-2">
          {isCollapsedRailHovered ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSidebar();
                    }}
                    className="h-9 w-9 flex items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-zinc-300 transition-all duration-200 hover:bg-white/[0.08] active:scale-95 cursor-pointer"
                    aria-label="Expand sidebar"
                  >
                    <MdKeyboardDoubleArrowRight size={20} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="text-white text-sm">Expand sidebar</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleSidebar();
              }}
              className="h-9 w-9 flex items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-zinc-300 transition-all duration-200 active:scale-95 cursor-pointer"
              aria-label="Expand sidebar"
            >
              <Image
                src="/logo_vector_transparent.png"
                alt="logo"
                width={28}
                height={28}
                className="rounded-full"
              />
            </button>
          )}
        </div>

        <div className="flex flex-col items-center space-y-1 mt-2">
          <NavIconButton
            icon={<MdAdd size={20} />}
            tooltip="New Chat"
            onClick={() => router.push("/")}
            isActive={pathname === "/"}
          />
          <NavIconButton
            icon={<FiLayers size={20} />}
            tooltip="Integrations"
            onClick={() => router.push("/integrations")}
            isActive={pathname === "/integrations"}
          />
          <NavIconButton
            icon={<MdBarChart size={20} />}
            tooltip="Analytics"
            onClick={() => router.push("/analytics")}
            isActive={pathname === "/analytics"}
          />
          <NavIconButton
            icon={<MdSearch size={20} />}
            tooltip="Search chats"
            onClick={() => {
              toggleSidebar();
              setTimeout(() => searchInputRef.current?.focus(), 150);
            }}
          />
        </div>

        <div className="flex-grow" />

        <div className="flex flex-col items-center space-y-1 mb-3">
          <NavIconButton
            icon={<FaGithub size={20} />}
            tooltip="GitHub"
            href="https://github.com/skyflo-ai/skyflo"
            target="_blank"
            rel="noopener noreferrer"
          />
          <NavIconButton
            icon={<MdSettings size={20} />}
            tooltip="Settings"
            onClick={() => router.push("/settings")}
            isActive={pathname === "/settings"}
          />
          <NavIconButton
            icon={<MdLogout size={20} />}
            tooltip="Logout"
            onClick={handleLogoutOnClick}
          />
        </div>
      </div>
    </nav>
  );
}

function NavIconButton({
  icon,
  tooltip,
  onClick,
  isActive,
  href,
  target,
  rel,
}: {
  icon: React.ReactNode;
  tooltip: string;
  onClick?: () => void;
  isActive?: boolean;
  href?: string;
  target?: string;
  rel?: string;
}) {
  const className = `relative inline-flex h-11 w-11 items-center justify-center overflow-hidden rounded-lg text-zinc-400 hover:text-white ${
    isActive
      ? "bg-dark-active text-white border border-white/[0.08]"
      : "border border-transparent hover:bg-dark-hover hover:border-white/[0.06]"
  } transition-all duration-200 ease-out cursor-pointer hover:scale-[1.03] active:scale-95`;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {href ? (
            <a
              href={href}
              target={target}
              rel={rel}
              className={className}
              aria-label={tooltip}
            >
              {icon}
            </a>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (onClick) onClick();
              }}
              className={className}
              aria-label={tooltip}
            >
              {icon}
            </button>
          )}
        </TooltipTrigger>
        <TooltipContent side="right">
          <p className="text-white text-sm">{tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function SidebarToggleButton({
  isExpanded,
  tooltip,
  onClick,
}: {
  isExpanded: boolean;
  tooltip: string;
  onClick: () => void;
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className="group relative inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-zinc-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition-all duration-200 ease-out hover:scale-[1.04] hover:text-white hover:bg-white/[0.08] active:scale-95 cursor-pointer"
            aria-label={tooltip}
          >
            <span className="absolute inset-0 rounded-xl bg-gradient-to-b from-white/[0.08] to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100" />
            <span className="relative z-10 transition-transform duration-200 group-hover:translate-x-[1px]">
              {isExpanded ? (
                <MdKeyboardDoubleArrowLeft size={20} />
              ) : (
                <MdKeyboardDoubleArrowRight size={20} />
              )}
            </span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">
          <p className="text-white text-sm">{tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function SidebarNavItem({
  icon,
  label,
  onClick,
  isActive,
  href,
  target,
  rel,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  isActive?: boolean;
  href?: string;
  target?: string;
  rel?: string;
}) {
  const className = `w-full flex h-11 items-center gap-0 rounded-lg px-1 text-sm transition-colors cursor-pointer ${
    isActive
      ? "bg-dark-active text-white"
      : "text-zinc-400 hover:text-zinc-200 hover:bg-dark-hover"
  }`;

  const content = (
    <>
      <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center">
        {icon}
      </span>
      <span className="text-sm font-medium">{label}</span>
    </>
  );

  if (href) {
    return (
      <a href={href} target={target} rel={rel} className={className}>
        {content}
      </a>
    );
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        if (onClick) onClick();
      }}
      className={className}
    >
      {content}
    </button>
  );
}
