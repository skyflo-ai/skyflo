import { User } from "@/types/auth";
import { useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { HiOutlineMail, HiOutlineKey } from "react-icons/hi";
import { MdLock, MdPerson } from "react-icons/md";
import { showSuccess, showError } from "@/components/ui/toast";
import { actionBtnClass, inputClass } from "./constants";

interface ProfileSettingsProps {
  user: User | null;
}

function SpinnerLabel({ text }: { text: string }) {
  return (
    <>
      <div className="h-3.5 w-3.5 rounded-full border-2 border-blue-400 border-r-transparent animate-spin" />
      <span>{text}</span>
    </>
  );
}

export default function ProfileSettings({ user }: ProfileSettingsProps) {
  const { login } = useAuthStore();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [isProfileUpdating, setIsProfileUpdating] = useState(false);
  const [isPasswordChanging, setIsPasswordChanging] = useState(false);

  const isFullNameDirty = fullName.trim() !== (user?.full_name || "").trim();

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;
    if (!isFullNameDirty) return;

    setIsProfileUpdating(true);

    try {
      const response = await fetch("/api/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: fullName }),
      });

      const data = await response.json();

      if (response.ok) {
        login(
          {
            ...user,
            full_name: data.full_name || user.full_name,
          },
          ""
        );
        showSuccess("Profile updated");
      } else {
        showError(data.error || "Failed to update profile");
      }
    } catch (error: any) {
      showError(error.message || "Failed to update profile");
    } finally {
      setIsProfileUpdating(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

    if (newPassword !== confirmPassword) {
      showError("New passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      showError("Password must be at least 8 characters long");
      return;
    }

    setIsPasswordChanging(true);

    try {
      const response = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        showSuccess("Password changed");
      } else {
        showError(data.error || "Failed to change password");
      }
    } catch (error: any) {
      showError(error.message || "Failed to change password");
    } finally {
      setIsPasswordChanging(false);
    }
  };

  return (
    <>
      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden flex-1">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-400/[0.08] text-blue-400 text-sm">
            <HiOutlineMail />
          </div>
          <h2 className="text-sm font-medium text-zinc-300">
            Profile Information
          </h2>
        </div>
        <div className="p-5">
          <form onSubmit={handleProfileUpdate}>
            <div className="space-y-5">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    id="email"
                    className="w-full p-3 pl-10 rounded-lg bg-white/[0.02] border border-white/[0.04] text-zinc-500 cursor-not-allowed"
                    value={user?.email}
                    disabled
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdLock className="text-zinc-600" />
                  </div>
                </div>
                <p className="text-[11px] text-zinc-600 mt-1.5 ml-0.5">
                  Email cannot be changed after account creation
                </p>
              </div>

              <div>
                <label
                  htmlFor="fullName"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Full Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="fullName"
                    className={inputClass}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdPerson className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className={actionBtnClass}
                disabled={isProfileUpdating || !isFullNameDirty}
              >
                {isProfileUpdating ? (
                  <SpinnerLabel text="Updating..." />
                ) : (
                  <span>Update Profile</span>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-400/[0.08] text-blue-400 text-sm">
            <HiOutlineKey />
          </div>
          <h2 className="text-sm font-medium text-zinc-300">
            Security Settings
          </h2>
        </div>
        <div className="p-5">
          <form onSubmit={handlePasswordChange}>
            <div className="space-y-5">
              <div>
                <label
                  htmlFor="currentPassword"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="currentPassword"
                    className={inputClass}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdLock className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  New Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="newPassword"
                    className={inputClass}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdLock className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="confirmPassword"
                    className={inputClass}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdLock className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className={actionBtnClass}
                disabled={isPasswordChanging}
              >
                {isPasswordChanging ? (
                  <SpinnerLabel text="Changing Password..." />
                ) : (
                  <span>Change Password</span>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
