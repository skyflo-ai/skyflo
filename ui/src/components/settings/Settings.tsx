"use client";

import TeamSettings from "./TeamSettings";
import ProfileSettings from "./ProfileSettings";
import { User } from "@/types/auth";
import { motion } from "framer-motion";
import { MdError } from "react-icons/md";

const fadeInVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.3 } },
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
        className="m-6 rounded-xl bg-rose-500/5 border border-rose-500/10 p-5"
      >
        <div className="flex items-center gap-3">
          <MdError className="text-rose-400 text-base" />
          <h3 className="text-sm font-medium text-rose-400">
            Authentication Required
          </h3>
        </div>
        <p className="mt-2 text-sm text-zinc-400">
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
      className="flex flex-col gap-6 h-full w-full overflow-auto p-6"
    >
      <div>
        <h1 className="text-lg font-semibold text-white tracking-tight">
          Settings
        </h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Profile, security, and team management
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full flex-grow">
        <div className="flex flex-col gap-6">
          <ProfileSettings user={user} />
        </div>

        <div className="flex flex-col gap-6">
          <TeamSettings />
        </div>
      </div>
    </motion.div>
  );
}
