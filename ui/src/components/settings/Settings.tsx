"use client";

import { useState, useEffect } from "react";

import TeamSettings from "./TeamSettings";
import ProfileSettings from "./ProfileSettings";
import { User } from "@/types/auth";
import { motion } from "framer-motion";
import { MdError } from "react-icons/md";
import { IoSettingsOutline } from "react-icons/io5";

const fadeInVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.4 } },
};

interface SettingsProps {
  user: User | null;
}

export default function Settings({ user }: SettingsProps) {
  if (!user) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-rose-400 bg-rose-500/10 border border-rose-600/40 p-6 rounded-lg shadow-[0_0_15px_rgba(239,68,68,0.1)] backdrop-blur-sm"
      >
        <div className="flex items-center gap-3">
          <MdError className="text-rose-500 text-lg" />
          <h3 className="text-lg font-medium">Authentication Required</h3>
        </div>
        <p className="mt-2 text-gray-300">
          You need to be logged in to access profile settings.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeInVariants}
      className="flex flex-col h-full w-full overflow-auto px-2 py-2"
    >
      {/* <div className="relative bg-gradient-to-r from-[#0A1525] via-[#0F182A]/95 to-[#1A2C48]/90 p-8 rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10 overflow-hidden mb-8">
        <div className="absolute inset-0 bg-blue-600/5 rounded-xl" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl" />

        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center">
          <div className="flex-1">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent tracking-tight flex items-center">
              Settings
            </h1>
            <p className="text-gray-400 mt-2 max-w-2xl">
              Manage your personal profile and team member access in a
              centralized dashboard.
            </p>
          </div>{" "}
        </div>

        <div className="absolute bottom-0 right-0 opacity-10 transform translate-x-8 translate-y-4">
          <div className="flex items-end">
            <IoSettingsOutline className="text-blue-400 w-32 h-32" />
          </div>
        </div>
      </div> */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full flex-grow">
        <div className="flex flex-col space-y-8">
          <ProfileSettings user={user} />
        </div>

        <div className="flex flex-col space-y-8">
          <TeamSettings />
        </div>
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
          height: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(15, 29, 47, 0.3);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(100, 116, 139, 0.6);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(100, 116, 139, 0.8);
        }
      `}</style>
    </motion.div>
  );
}
