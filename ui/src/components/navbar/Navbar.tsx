"use client";

import React from "react";
import Image from "next/image";
import { Home, History, LogOut, Settings } from "lucide-react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useAuthStore } from "@/store/useAuthStore";
import { handleLogout } from "@/lib/auth";
import { useRouter, usePathname } from "next/navigation";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { logout } = useAuth();
  const { logout: storeLogout } = useAuthStore();

  const handleLogoutOnClick = async () => {
    await handleLogout();
    storeLogout();
    logout();
    router.push("/login");
  };

  return (
    <nav className="h-screen w-16 bg-dark-navbar flex flex-col items-center py-4 px-8 border-r border-border">
      {/* Logo placeholder */}
      <div className="w-10 h-10 rounded-full mb-8">
        <Image
          src="/logo_vector_transparent.png"
          alt="logo"
          width={40}
          height={40}
          className="rounded-full"
        />
      </div>

      {/* Nav icons */}
      <div className="flex-grow flex flex-col space-y-3">
        <NavIcon
          icon={<Home size={20} />}
          tooltip="Home"
          onClick={() => router.push("/")}
          isActive={pathname === "/"}
        />
        <NavIcon
          icon={<History size={20} />}
          tooltip="History"
          onClick={() => router.push("/history")}
          isActive={pathname === "/history"}
        />
      </div>

      {/* Admin/Settings Menu Icons */}
      <div className="mt-auto flex flex-col space-y-3 mb-4">
        <NavIcon
          icon={<Settings size={20} />}
          tooltip="Settings"
          onClick={() => router.push("/settings")}
          isActive={pathname === "/settings"}
        />
        <NavIcon
          icon={<LogOut size={20} />}
          tooltip="Logout"
          onClick={handleLogoutOnClick}
        />
      </div>
    </nav>
  );
}

function NavIcon({
  icon,
  tooltip,
  onClick,
  isActive,
}: {
  icon: React.ReactNode;
  tooltip: string;
  onClick?: () => void;
  isActive?: boolean;
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onClick) onClick();
            }}
            className={`p-2.5 rounded-lg text-white ${
              isActive ? "bg-dark-active" : "hover:bg-dark-hover"
            } transition-colors cursor-pointer`}
          >
            {icon}
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">
          <p className="text-white text-xs">{tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
