import { User } from "@/lib/types/auth";
import { useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { HiOutlineMail, HiOutlineKey, HiOutlineRefresh } from "react-icons/hi";
import { MdLock, MdPerson } from "react-icons/md";
import { showSuccess, showError } from "@/lib/toast";

// ProfileSettings Component
interface ProfileSettingsProps {
  user: User | null;
}

export default function ProfileSettings({ user }: ProfileSettingsProps) {
  const { login } = useAuthStore();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Separate loading states for each action
  const [isProfileUpdating, setIsProfileUpdating] = useState(false);
  const [isPasswordChanging, setIsPasswordChanging] = useState(false);

  // Handle profile update
  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

    setIsProfileUpdating(true);

    try {
      const response = await fetch("/api/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: fullName,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Update the user in the store with the new data
        login(
          {
            ...user,
            full_name: data.full_name || user.full_name,
          },
          localStorage.getItem("skyflo-auth-storage")
            ? JSON.parse(localStorage.getItem("skyflo-auth-storage") || "{}")
                .state?.token
            : ""
        );
        showSuccess("Profile updated successfully");
      } else {
        showError(data.error || "Failed to update profile");
      }
    } catch (error: any) {
      console.error("[Profile] Error updating profile:", error);
      showError(error.message || "Failed to update profile");
    } finally {
      setIsProfileUpdating(false);
    }
  };

  // Handle password change
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

    // Validate passwords
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Clear password fields
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");

        showSuccess("Password changed successfully");
      } else {
        showError(data.error || "Failed to change password");
      }
    } catch (error: any) {
      console.error("[Profile] Error changing password:", error);
      showError(error.message || "Failed to change password");
    } finally {
      setIsPasswordChanging(false);
    }
  };

  return (
    <>
      {/* Profile Information */}
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden flex-1">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2.5 rounded-full">
              <HiOutlineMail className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">
              Profile Information
            </h2>
          </div>
        </div>
        <div className="p-6">
          <form onSubmit={handleProfileUpdate}>
            <div className="space-y-6">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineMail className="text-blue-400" />
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    id="email"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner opacity-70 focus:outline-none"
                    value={user?.email}
                    disabled
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdLock className="text-slate-500" />
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-2 ml-1">
                  Email cannot be changed after account creation
                </p>
              </div>

              <div>
                <label
                  htmlFor="fullName"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <MdPerson className="text-blue-400" />
                  Full Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="fullName"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdPerson className="text-slate-500" />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="group relative bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] hover:from-blue-500 hover:to-cyan-500 text-white transition-all duration-300 rounded-md overflow-hidden w-full"
                disabled={isProfileUpdating}
              >
                <div className="relative bg-[#030712] rounded-md group-hover:bg-opacity-90 px-4 py-2 transition-all duration-300 flex items-center justify-center">
                  {isProfileUpdating ? (
                    <>
                      <div className="h-4 w-4 rounded-full border-2 border-white/80 border-r-transparent animate-spin mr-2" />
                      <span className="text-sm font-medium">
                        Updating Profile...
                      </span>
                    </>
                  ) : (
                    <>
                      <HiOutlineRefresh
                        className="h-4 w-4 mr-2"
                        aria-hidden="true"
                      />
                      <span className="text-sm font-medium">
                        Update Profile
                      </span>
                    </>
                  )}
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600 opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Password Change */}
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2.5 rounded-full">
              <HiOutlineKey className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">
              Security Settings
            </h2>
          </div>
        </div>
        <div className="p-6">
          <form onSubmit={handlePasswordChange}>
            <div className="space-y-6">
              <div>
                <label
                  htmlFor="currentPassword"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineKey className="text-blue-400" />
                  Current Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="currentPassword"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdLock className="text-slate-500" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineKey className="text-blue-400" />
                  New Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="newPassword"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdLock className="text-slate-500" />
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-2 ml-1 flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-blue-400"></span>
                  Password must be at least 8 characters long
                </p>
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineKey className="text-blue-400" />
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="confirmPassword"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdLock className="text-slate-500" />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="group relative bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] hover:from-blue-500 hover:to-cyan-500 text-white transition-all duration-300 rounded-md overflow-hidden w-full"
                disabled={isPasswordChanging}
              >
                <div className="relative bg-[#030712] rounded-md group-hover:bg-opacity-90 px-4 py-2 transition-all duration-300 flex items-center justify-center">
                  {isPasswordChanging ? (
                    <>
                      <div className="h-4 w-4 rounded-full border-2 border-white/80 border-r-transparent animate-spin mr-2" />
                      <span className="text-sm font-medium">
                        Changing Password...
                      </span>
                    </>
                  ) : (
                    <>
                      <HiOutlineKey
                        className="h-4 w-4 mr-2"
                        aria-hidden="true"
                      />
                      <span className="text-sm font-medium">
                        Change Password
                      </span>
                    </>
                  )}
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600 opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
