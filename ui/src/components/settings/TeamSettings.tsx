import { useState, useEffect } from "react";
import {
  MdAdminPanelSettings,
  MdGroup,
  MdOutlineLock,
  MdPerson,
  MdPersonAdd,
} from "react-icons/md";
import { IoTrash } from "react-icons/io5";
import { HiOutlineMail, HiOutlineLockClosed } from "react-icons/hi";
import { TeamMember } from "@/types/auth";
import { useAuthStore } from "@/store/useAuthStore";
import { showSuccess, showError } from "@/components/ui/toast";
import { ConfirmModal } from "@/components/ui/modal";
import { actionBtnClass, inputClass } from "./constants";

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
    const handleClickOutside = () => setIsRoleDropdownOpen(false);
    if (isRoleDropdownOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [isRoleDropdownOpen]);

  const fetchTeamMembers = async () => {
    setIsTeamLoading(true);
    try {
      const response = await fetch("/api/team");

      if (response.ok) {
        const data = await response.json();
        const currentUser = data.find(
          (member: TeamMember) => member.id === user?.id,
        );
        const otherMembers = data.filter(
          (member: TeamMember) => member.id !== user?.id,
        );
        setTeamMembers([currentUser, ...otherMembers]);
      } else {
        const error = await response.json();
        if (typeof error === "object" && error !== null) {
          showError(
            typeof error.error === "string"
              ? error.error
              : "Failed to fetch team members",
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
        headers: { "Content-Type": "application/json" },
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
      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-400/[0.08] text-blue-400 text-sm">
            <MdGroup />
          </div>
          <h2 className="text-sm font-medium text-zinc-300">Team Management</h2>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-2 bg-amber-500/5 border border-amber-500/10 rounded-lg p-4 text-amber-400 text-sm">
            <MdOutlineLock className="w-4 h-4 shrink-0" />
            <p>Only admins can access team management features.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden flex-1">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-400/[0.08] text-blue-400 text-sm">
            <MdGroup />
          </div>
          <h2 className="text-sm font-medium text-zinc-300">Team Management</h2>
        </div>
        <div className="p-5">
          <div className="w-full">
            <div className="overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02]">
              {isTeamLoading && teamMembers.length === 0 ? (
                <div className="py-8 text-center text-zinc-500 text-sm">
                  <div className="flex justify-center mb-3">
                    <div className="h-4 w-4 rounded-full border-2 border-sky-400 border-r-transparent animate-spin" />
                  </div>
                  <p>Loading team members...</p>
                </div>
              ) : teamMembers.length === 0 ? (
                <div className="py-8 text-center text-zinc-500 text-sm">
                  <p>No team members found. Invite someone to get started.</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-left">
                      <th className="py-2.5 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Name
                      </th>
                      <th className="py-2.5 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="py-2.5 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Role
                      </th>
                      <th className="py-2.5 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="py-2.5 px-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {teamMembers.map((member) => (
                      <tr
                        key={member.id}
                        className="hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="py-2.5 px-4 text-zinc-300 text-xs">
                          {member.name}
                        </td>
                        <td className="py-2.5 px-4 text-zinc-300 text-xs">
                          {member.email}
                        </td>
                        <td className="py-2.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              member.role === "Admin"
                                ? "bg-blue-500/10 text-blue-400"
                                : "bg-zinc-500/10 text-zinc-400"
                            }`}
                          >
                            {member.role}
                          </span>
                        </td>
                        <td className="py-2.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              member.status === "active"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "bg-amber-500/10 text-amber-400"
                            }`}
                          >
                            {member.status === "active" ? "Active" : "Pending"}
                          </span>
                        </td>
                        <td className="py-2.5 px-4">
                          {member.id !== user?.id && (
                            <button
                              type="button"
                              className="text-zinc-500 hover:text-rose-400 transition-colors flex items-center gap-1 text-xs cursor-pointer"
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

      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-400/[0.08] text-blue-400 text-sm">
            <MdPersonAdd />
          </div>
          <h2 className="text-sm font-medium text-zinc-300">
            Invite Team Member
          </h2>
        </div>
        <div className="p-5">
          <form onSubmit={handleInviteMember}>
            <div className="space-y-5">
              <div>
                <label
                  htmlFor="memberEmail"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    id="memberEmail"
                    className={inputClass}
                    value={newMemberEmail}
                    onChange={(e) => setNewMemberEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    required
                    disabled={isInviting}
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <HiOutlineMail className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="memberPassword"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    id="memberPassword"
                    className={inputClass}
                    value={newMemberPassword}
                    onChange={(e) => setNewMemberPassword(e.target.value)}
                    placeholder="Set initial password"
                    required
                    disabled={isInviting}
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <HiOutlineLockClosed className="text-zinc-600" />
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor="memberRole"
                  className="block text-sm font-medium mb-2 text-zinc-400"
                >
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
                    className="w-full p-3 pl-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-zinc-200 outline-none focus:border-white/[0.15] transition-colors duration-200 text-left flex items-center justify-between"
                    disabled={isInviting}
                  >
                    <span>{newMemberRole}</span>
                    <svg
                      className={`h-4 w-4 text-zinc-500 transition-transform duration-200 ${
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
                  <div className="absolute left-3 top-1/2 -translate-y-1/2">
                    <MdGroup className="text-zinc-600" />
                  </div>

                  {isRoleDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-950/90 backdrop-blur-sm border border-white/[0.08] rounded-lg shadow-2xl z-[100]">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setNewMemberRole("Member");
                          setIsRoleDropdownOpen(false);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-white/[0.04] rounded-t-lg transition-colors flex items-center gap-2"
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
                        className="w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-white/[0.04] rounded-b-lg transition-colors flex items-center gap-2"
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
                className={actionBtnClass}
                disabled={isInviting}
              >
                {isInviting ? (
                  <>
                    <div className="h-3.5 w-3.5 rounded-full border-2 border-blue-400 border-r-transparent animate-spin" />
                    <span>Adding Member...</span>
                  </>
                ) : (
                  <span>Add Member</span>
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
