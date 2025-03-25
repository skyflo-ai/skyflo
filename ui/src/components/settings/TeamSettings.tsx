import { useState, useEffect } from "react";
import { MdGroup, MdPersonAdd } from "react-icons/md";
import { IoTrash } from "react-icons/io5";
import {
  HiOutlineMail,
  HiOutlineUserGroup,
  HiOutlineLockClosed,
} from "react-icons/hi";
import { TeamMember } from "@/lib/types/auth";
import { useAuthStore } from "@/store/useAuthStore";
import { showSuccess, showError } from "@/lib/toast";

interface TeamSettingsProps {}

export default function TeamSettings({}: TeamSettingsProps) {
  // Get the current user from auth store
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  // Team management state
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("Member");
  const [newMemberPassword, setNewMemberPassword] = useState("");

  // Separate loading states for different actions
  const [isTeamLoading, setIsTeamLoading] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [removingMemberIds, setRemovingMemberIds] = useState<string[]>([]);

  // Fetch team members on component mount
  useEffect(() => {
    if (isAdmin) {
      fetchTeamMembers();
    }
  }, [isAdmin]);

  // Fetch team members from API
  const fetchTeamMembers = async () => {
    setIsTeamLoading(true);
    try {
      const response = await fetch("/api/team");

      if (response.ok) {
        const data = await response.json();
        // always show the current user on top of the list
        const currentUser = data.find(
          (member: TeamMember) => member.id === user?.id
        );
        const otherMembers = data.filter(
          (member: TeamMember) => member.id !== user?.id
        );

        setTeamMembers([currentUser, ...otherMembers]);
      } else {
        const error = await response.json();
        if (typeof error === "object" && error !== null) {
          showError(
            typeof error.error === "string"
              ? error.error
              : "Failed to fetch team members"
          );
        } else {
          showError("Failed to fetch team members");
        }
      }
    } catch (error) {
      console.error("[Team] Error fetching team members:", error);
      showError("An unexpected error occurred");
    } finally {
      setIsTeamLoading(false);
    }
  };

  // Handle team member invite
  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newMemberEmail || !isAdmin) return;

    setIsInviting(true);

    try {
      const response = await fetch("/api/team", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: newMemberEmail,
          role: newMemberRole,
          password: newMemberPassword,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // always show the current user on top of the list
        setTeamMembers([data, ...teamMembers]);
        setNewMemberEmail("");
        setNewMemberPassword("");
        showSuccess("Team member invitation sent");
      } else {
        const error = await response.json();
        showError(error.error || "Failed to invite team member");
      }
    } catch (error) {
      console.error("[Team] Error inviting team member:", error);
      showError("An unexpected error occurred");
    } finally {
      setIsInviting(false);
    }
  };

  // Handle removing a team member
  const handleRemoveMember = async (memberId: string) => {
    if (!isAdmin) return;

    // Add member ID to the removing array
    setRemovingMemberIds((prev) => [...prev, memberId]);

    try {
      const response = await fetch(`/api/team?memberId=${memberId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        // Remove member from state
        setTeamMembers(teamMembers.filter((member) => member.id !== memberId));
        showSuccess("Team member removed successfully");
      } else {
        const error = await response.json();
        showError(error.error || "Failed to remove team member");
      }
    } catch (error) {
      console.error("[Team] Error removing team member:", error);
      showError("An unexpected error occurred");
    } finally {
      // Remove member ID from the removing array
      setRemovingMemberIds((prev) => prev.filter((id) => id !== memberId));
    }
  };

  // If user is not an admin, show access denied message
  if (!isAdmin) {
    return (
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm">
          <h2 className="text-xl font-semibold text-slate-100">
            Team Management
          </h2>
        </div>
        <div className="p-6 text-center">
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 text-amber-400">
            <p>Only administrators can access team management features.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Team Members List */}
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden flex-1">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2.5 rounded-full">
              <MdGroup className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">
              Team Management
            </h2>
          </div>
        </div>
        <div className="p-6">
          <div className="w-full">
            <div className="overflow-hidden rounded-lg border border-slate-700/60 bg-[#0F1D2F]">
              {isTeamLoading && teamMembers.length === 0 ? (
                <div className="py-8 text-center text-slate-400">
                  <div className="flex justify-center mb-3">
                    <div className="h-5 w-5 rounded-full border-2 border-blue-400 border-r-transparent animate-spin" />
                  </div>
                  <p>Loading team members...</p>
                </div>
              ) : teamMembers.length === 0 ? (
                <div className="py-8 text-center text-slate-400">
                  <p>No team members found. Invite someone to get started.</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/60 bg-[#121E30] text-left">
                      <th className="py-3 px-4 text-slate-300 font-medium">
                        Name
                      </th>
                      <th className="py-3 px-4 text-slate-300 font-medium">
                        Email
                      </th>
                      <th className="py-3 px-4 text-slate-300 font-medium">
                        Role
                      </th>
                      <th className="py-3 px-4 text-slate-300 font-medium">
                        Status
                      </th>
                      <th className="py-3 px-4 text-slate-300 font-medium">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/40">
                    {teamMembers.map((member) => (
                      <tr
                        key={member.id}
                        className="hover:bg-slate-800/30 transition-colors"
                      >
                        <td className="py-3 px-4 text-slate-300">
                          {member.name}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {member.email}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              member.role === "Admin"
                                ? "bg-blue-500/20 text-blue-400"
                                : member.role === "Viewer"
                                ? "bg-purple-500/20 text-purple-400"
                                : "bg-slate-500/20 text-slate-300"
                            }`}
                          >
                            {member.role}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              member.status === "active"
                                ? "bg-green-500/20 text-green-400"
                                : "bg-amber-500/20 text-amber-400"
                            }`}
                          >
                            {member.status === "active" ? "Active" : "Pending"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {member.id !== user?.id && (
                            <button
                              type="button"
                              className="text-slate-400 hover:text-rose-400 transition-colors flex items-center gap-1"
                              aria-label="Remove member"
                              onClick={() => handleRemoveMember(member.id)}
                              disabled={removingMemberIds.includes(member.id)}
                            >
                              {removingMemberIds.includes(member.id) ? (
                                <div className="h-3 w-3 rounded-full border-2 border-rose-400 border-r-transparent animate-spin" />
                              ) : (
                                <IoTrash className="w-3 h-3" />
                              )}
                              {removingMemberIds.includes(member.id)
                                ? "Removing..."
                                : "Remove"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Invite New Team Member */}
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2.5 rounded-full">
              <MdPersonAdd className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">
              Invite Team Member
            </h2>
          </div>
        </div>
        <div className="p-6">
          <form onSubmit={handleInviteMember}>
            <div className="space-y-6">
              <div>
                <label
                  htmlFor="memberEmail"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineMail className="text-blue-400" />
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    id="memberEmail"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={newMemberEmail}
                    onChange={(e) => setNewMemberEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    required
                    disabled={isInviting}
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <HiOutlineMail className="text-slate-500" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="memberPassword"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineLockClosed className="text-blue-400" />
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="memberPassword"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none"
                    value={newMemberPassword}
                    onChange={(e) => setNewMemberPassword(e.target.value)}
                    placeholder="Set initial password"
                    required
                    disabled={isInviting}
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <HiOutlineLockClosed className="text-slate-500" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="memberRole"
                  className="block text-sm font-medium mb-2 text-slate-300 flex items-center gap-2"
                >
                  <HiOutlineUserGroup className="text-blue-400" />
                  Role
                </label>
                <div className="relative">
                  <select
                    id="memberRole"
                    className="w-full p-3 pl-10 rounded-lg bg-[#0F1D2F] border border-slate-700/60 text-slate-300 shadow-inner focus:border-blue-600/80 focus:ring-2 focus:ring-blue-600/30 transition-all duration-200 focus:outline-none appearance-none"
                    value={newMemberRole}
                    onChange={(e) => setNewMemberRole(e.target.value)}
                    disabled={isInviting}
                  >
                    <option value="Member">Member</option>
                    <option value="Admin">Admin</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdGroup className="text-slate-500" />
                  </div>
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                    <svg
                      className="h-5 w-5 text-slate-500"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="group relative bg-gradient-to-r from-blue-600 to-cyan-600 p-[1px] hover:from-blue-500 hover:to-cyan-500 text-white transition-all duration-300 rounded-md overflow-hidden w-full"
                disabled={isInviting}
              >
                <div className="relative bg-[#030712] rounded-md group-hover:bg-opacity-90 px-4 py-2 transition-all duration-300 flex items-center justify-center">
                  {isInviting ? (
                    <>
                      <div className="h-4 w-4 rounded-full border-2 border-white/80 border-r-transparent animate-spin mr-2" />
                      <span className="text-sm font-medium">
                        Sending Invitation...
                      </span>
                    </>
                  ) : (
                    <>
                      <MdPersonAdd
                        className="h-4 w-4 mr-2"
                        aria-hidden="true"
                      />
                      <span className="text-sm font-medium">Add Member</span>
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
