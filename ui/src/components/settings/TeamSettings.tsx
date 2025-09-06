import { useState, useEffect } from "react";
import {
  MdAdminPanelSettings,
  MdGroup,
  MdOutlineLock,
  MdPerson,
  MdPersonAdd,
} from "react-icons/md";
import { IoTrash } from "react-icons/io5";
import {
  HiOutlineMail,
  HiOutlineUserGroup,
  HiOutlineLockClosed,
} from "react-icons/hi";
import { TeamMember } from "@/types/auth";
import { useAuthStore } from "@/store/useAuthStore";
import { showSuccess, showError } from "@/components/ui/toast";
import { ConfirmModal } from "@/components/ui/modal";

interface TeamSettingsProps {}

export default function TeamSettings({}: TeamSettingsProps) {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("Member");
  const [newMemberPassword, setNewMemberPassword] = useState("");
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState(false);

  const [isTeamLoading, setIsTeamLoading] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [removingMemberIds, setRemovingMemberIds] = useState<string[]>([]);
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    memberId: string;
    memberName: string;
  }>({ isOpen: false, memberId: "", memberName: "" });

  useEffect(() => {
    if (isAdmin) {
      fetchTeamMembers();
    }
  }, [isAdmin]);

  useEffect(() => {
    const handleClickOutside = () => {
      setIsRoleDropdownOpen(false);
    };

    if (isRoleDropdownOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => {
        document.removeEventListener("click", handleClickOutside);
      };
    }
  }, [isRoleDropdownOpen]);

  const fetchTeamMembers = async () => {
    setIsTeamLoading(true);
    try {
      const response = await fetch("/api/team");

      if (response.ok) {
        const data = await response.json();
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
      showError("An unexpected error occurred");
    } finally {
      setIsTeamLoading(false);
    }
  };

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
        setTeamMembers([data, ...teamMembers]);
        setNewMemberEmail("");
        setNewMemberPassword("");
        showSuccess("Team member added");
      } else {
        const error = await response.json();
        showError(error.error || "Failed to invite team member");
      }
    } catch (error) {
      showError("An unexpected error occurred");
    } finally {
      setIsInviting(false);
    }
  };

  const handleRemoveMember = (memberId: string) => {
    if (!isAdmin) return;

    const member = teamMembers.find((m) => m.id === memberId);
    if (member) {
      setDeleteModal({
        isOpen: true,
        memberId,
        memberName: member.email,
      });
    }
  };

  const handleRemoveMemberConfirm = async () => {
    const { memberId } = deleteModal;
    if (!isAdmin || !memberId) return;

    setRemovingMemberIds((prev) => [...prev, memberId]);

    try {
      const response = await fetch(`/api/team?memberId=${memberId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setTeamMembers(teamMembers.filter((member) => member.id !== memberId));
        showSuccess("Team member removed");
      } else {
        const error = await response.json();
        showError(error.error || "Failed to remove team member");
      }
    } catch (error) {
      showError("An unexpected error occurred");
    } finally {
      setRemovingMemberIds((prev) => prev.filter((id) => id !== memberId));
    }
  };

  if (!isAdmin) {
    return (
      <div className="bg-gradient-to-br from-[#0A1020] to-[#0A1525] rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm">
          <h2 className="text-xl font-semibold text-slate-100">
            Team Management
          </h2>
        </div>
        <div className="p-6 text-center">
          <div className="flex items-center justify-center gap-2 bg-amber-600/10 border border-amber-500/20 rounded-lg p-4 text-amber-400">
            <MdOutlineLock className="w-5 h-5 text-amber-400" />
            <p>Only admins can access team management features.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-dark rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden flex-1">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-slate-500/15 p-2.5 rounded-full">
              <MdGroup className="w-5 h-5 text-slate-300" />
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
                                ? "bg-emerald-500/20 text-emerald-400"
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
                              className="text-slate-400 hover:text-rose-400 outline-none focus:outline-none focus-visible:outline-none transition-colors flex items-center gap-1"
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

      <div className="bg-dark rounded-xl border border-[#243147] shadow-xl shadow-blue-900/5 overflow-hidden">
        <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-5 border-b border-[#243147] backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-slate-500/15 p-2.5 rounded-full">
              <MdPersonAdd className="w-5 h-5 text-slate-300" />
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
                  <HiOutlineMail className="text-slate-400" />
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    id="memberEmail"
                    className="w-full p-3 pl-10 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
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
                  <HiOutlineLockClosed className="text-slate-400" />
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="memberPassword"
                    className="w-full p-3 pl-10 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
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
                  <HiOutlineUserGroup className="text-slate-400" />
                  Role
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsRoleDropdownOpen(!isRoleDropdownOpen);
                    }}
                    className="w-full p-3 pl-10 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200 text-left flex items-center justify-between"
                    disabled={isInviting}
                  >
                    <span>{newMemberRole}</span>
                    <svg
                      className={`h-5 w-5 text-slate-500 transition-transform duration-200 ${
                        isRoleDropdownOpen ? "rotate-180" : ""
                      }`}
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
                  </button>
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <MdGroup className="text-slate-500" />
                  </div>

                  {isRoleDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mb-1 bg-[#1A2332] border border-slate-600/60 rounded-lg shadow-[0px_-3px_2px_0px_rgba(0,_0,_0,_0.1)] z-[100]">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setNewMemberRole("Member");
                          setIsRoleDropdownOpen(false);
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 rounded-t-lg transition-colors flex items-center gap-2"
                        disabled={isInviting}
                      >
                        <MdPerson className="w-4 h-4" />
                        Member
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setNewMemberRole("Admin");
                          setIsRoleDropdownOpen(false);
                        }}
                        className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 transition-colors flex items-center gap-2"
                        disabled={isInviting}
                      >
                        <MdAdminPanelSettings className="w-4 h-4" />
                        Admin
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <button
                type="submit"
                className="group inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg w-full
                           bg-[#0A1525]/50 border border-blue-500/30 
                   hover:border-blue-500/40 hover:bg-[#0A1525]/80
                           outline-none focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0
                           transition-all duration-100 cursor-pointer text-white disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isInviting}
              >
                {isInviting ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-white/80 border-r-transparent animate-spin" />
                    <span className="text-sm font-medium">
                      Sending Invitation...
                    </span>
                  </>
                ) : (
                  <>
                    <MdPersonAdd
                      className="h-4 w-4 text-blue-400/70 group-hover:text-blue-400"
                      aria-hidden="true"
                    />
                    <span className="text-sm font-medium">Add Member</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() =>
          setDeleteModal({ isOpen: false, memberId: "", memberName: "" })
        }
        onConfirm={handleRemoveMemberConfirm}
        title="Remove Team Member"
        message={`Are you sure you want to remove "${deleteModal.memberName}" from the team?`}
        confirmText="Remove"
        variant="danger"
      />
    </>
  );
}
