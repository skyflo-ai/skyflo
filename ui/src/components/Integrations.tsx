"use client";

import React, { useCallback, useEffect, useState } from "react";
import { format } from "date-fns";
import { ConfirmModal, InputModal } from "@/components/ui/modal";
import { showSuccess, showError } from "@/components/ui/toast";
import {
  MdIntegrationInstructions,
  MdMoreVert,
  MdEdit,
  MdDelete,
  MdAdd,
  MdCheckCircle,
  MdCancel,
  MdSettings,
} from "react-icons/md";
import { useAuthStore } from "@/store/useAuthStore";

interface Integration {
  id: string;
  provider: string;
  name?: string;
  metadata?: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

interface CreateIntegrationData {
  provider: string;
  metadata: Record<string, any>;
  credentials: Record<string, any>;
}

interface UpdateIntegrationData {
  metadata?: Record<string, any>;
  credentials?: Record<string, any>;
  status?: string;
}

const PROVIDERS = {
  jenkins: {
    name: "Jenkins",
    description: "Build Automation Server",
  },
};

const inputClass =
  "w-full p-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-zinc-200 placeholder-zinc-600 outline-none focus:border-white/[0.15] transition-colors duration-200";

export default function Integrations() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const [createModal, setCreateModal] = useState({ isOpen: false });
  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    integration: Integration | null;
  }>({ isOpen: false, integration: null });
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    integration: Integration | null;
  }>({ isOpen: false, integration: null });

  const [createProvider, setCreateProvider] = useState("jenkins");
  const [createApiUrl, setCreateApiUrl] = useState("");
  const [createUsername, setCreateUsername] = useState("");
  const [createApiToken, setCreateApiToken] = useState("");

  const [editStatus, setEditStatus] = useState("active");
  const [editApiUrl, setEditApiUrl] = useState("");
  const [editUsername, setEditUsername] = useState("");
  const [editApiToken, setEditApiToken] = useState("");
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);

  const fetchIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/integrations");
      const data = await response.json();

      if (response.ok && Array.isArray(data)) {
        setIntegrations(data);
      } else {
        showError("Failed to load integrations");
      }
    } catch (error) {
      showError("Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCreateIntegration = async (data: CreateIntegrationData) => {
    try {
      const response = await fetch("/api/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        setIntegrations((prev) => [...prev, result]);
        showSuccess(
          `${
            PROVIDERS[data.provider as keyof typeof PROVIDERS]?.name ||
            data.provider
          } integration created`
        );
        setCreateModal({ isOpen: false });
      } else {
        showError(result.detail || "Failed to create integration");
      }
    } catch (error) {
      showError("Failed to create integration");
    }
  };

  const handleUpdateIntegration = async (
    id: string,
    data: UpdateIntegrationData
  ) => {
    try {
      const response = await fetch(`/api/integrations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        setIntegrations((prev) =>
          prev.map((integration) =>
            integration.id === id ? result : integration
          )
        );
        showSuccess("Integration updated");
        setEditModal({ isOpen: false, integration: null });
      } else {
        showError(result.detail || "Failed to update integration");
      }
    } catch (error) {
      showError("Failed to update integration");
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    try {
      const response = await fetch(`/api/integrations/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setIntegrations((prev) =>
          prev.filter((integration) => integration.id !== id)
        );
        showSuccess("Integration deleted");
        setDeleteModal({ isOpen: false, integration: null });
      } else {
        const result = await response.json();
        showError(result.detail || "Failed to delete integration");
      }
    } catch (error) {
      showError("Failed to delete integration");
    }
  };

  const handleMenuToggle = (
    integrationId: string,
    event: React.MouseEvent
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(openMenuId === integrationId ? null : integrationId);
  };

  const handleEdit = (integration: Integration, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(null);
    setEditModal({ isOpen: true, integration });
  };

  const handleDelete = (integration: Integration, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpenMenuId(null);
    setDeleteModal({ isOpen: true, integration });
  };

  useEffect(() => {
    const handleClickOutside = () => setOpenMenuId(null);
    if (openMenuId) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [openMenuId]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  useEffect(() => {
    if (editModal.integration) {
      setEditStatus(editModal.integration.status);
      setEditApiUrl(editModal.integration.metadata?.api_url || "");
      setEditUsername("");
      setEditApiToken("");
    }
  }, [editModal.integration, editModal.isOpen]);

  useEffect(() => {
    const handleClickOutside = () => setIsStatusDropdownOpen(false);
    if (isStatusDropdownOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [isStatusDropdownOpen]);

  const getProviderInfo = (provider: string) => {
    return (
      PROVIDERS[provider as keyof typeof PROVIDERS] || {
        name: provider.charAt(0).toUpperCase() + provider.slice(1),
        description: "Third-party integration",
      }
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <MdCheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
      case "disabled":
        return <MdCancel className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <MdSettings className="w-3.5 h-3.5 text-zinc-500" />;
    }
  };

  return (
    <div className="flex flex-col gap-6 h-full w-full overflow-auto p-6">
      <div className="flex max-sm:flex-col max-sm:gap-4 justify-between items-start">
        <div>
          <h1 className="text-lg font-semibold text-white tracking-tight">
            Integrations
          </h1>
          {isAdmin ? (
            <p className="text-sm text-zinc-500 mt-0.5">
              Configure third-party integrations for your workspace
            </p>
          ) : (
            integrations.length !== 0 && (
              <p className="text-sm text-zinc-500 mt-0.5">
                Ask an admin to configure integrations for your workspace
              </p>
            )
          )}
        </div>
        {isAdmin && (
          <button
            onClick={() => setCreateModal({ isOpen: true })}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-sky-500/10 border border-sky-500/20 hover:border-sky-500/30 hover:bg-sky-500/15 text-sky-400 text-xs font-medium transition-colors duration-200 cursor-pointer"
          >
            <MdAdd className="w-4 h-4" />
            Create
          </button>
        )}
      </div>

      <div className="h-full">
        {integrations.length === 0 && loading ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-28 bg-zinc-800/15 rounded-xl animate-pulse"
              />
            ))}
          </div>
        ) : integrations.length === 0 ? (
          <div className="flex justify-center items-center h-full">
            <div className="flex flex-col items-center py-16">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.03] border border-white/[0.06] mb-4">
                <MdIntegrationInstructions className="w-5 h-5 text-zinc-500" />
              </div>
              <h3 className="text-sm font-medium text-zinc-300 mb-1">
                No integrations configured
              </h3>
              {isAdmin ? (
                <p className="text-xs text-zinc-500 mb-5">
                  Add your first integration to connect with external services.
                </p>
              ) : (
                <p className="text-xs text-zinc-500 mb-5">
                  Ask an admin to configure integrations for your workspace
                </p>
              )}
              {isAdmin && (
                <button
                  onClick={() => setCreateModal({ isOpen: true })}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-sky-500/10 border border-sky-500/20 hover:border-sky-500/30 hover:bg-sky-500/15 text-sky-400 text-xs font-medium transition-colors duration-200 cursor-pointer"
                >
                  <MdAdd className="w-4 h-4" />
                  Create
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {integrations.map((integration) => {
              const providerInfo = getProviderInfo(integration.provider);

              return (
                <div
                  key={integration.id}
                  className="relative group transition-all duration-200"
                >
                  <div
                    className={`rounded-xl bg-white/[0.03] border border-white/[0.06] ${
                      isAdmin ? "hover:border-white/[0.12]" : ""
                    } p-4 h-full transition-colors duration-200`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-sm font-medium text-zinc-200 flex items-center gap-2">
                          {integration.name || providerInfo.name}
                          {getStatusIcon(integration.status)}
                        </h3>
                        <p className="text-xs text-zinc-500 mt-0.5">
                          {providerInfo.description}
                        </p>
                      </div>
                      <div className="relative">
                        {isAdmin && (
                          <button
                            onClick={(e) =>
                              handleMenuToggle(integration.id, e)
                            }
                            className="p-1 rounded-md text-zinc-500 opacity-100 hover:bg-white/[0.06] hover:text-zinc-300 focus:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/[0.2] transition-colors transition-opacity cursor-pointer"
                            aria-label="More options"
                            aria-expanded={openMenuId === integration.id}
                          >
                            <MdMoreVert className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-zinc-500">Status</span>
                        <span
                          className={`capitalize ${
                            integration.status === "active"
                              ? "text-emerald-400"
                              : integration.status === "disabled"
                                ? "text-rose-400"
                                : "text-zinc-400"
                          }`}
                        >
                          {integration.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-zinc-500">Created</span>
                        <span className="text-zinc-300">
                          {format(
                            new Date(integration.created_at),
                            "MMM d, yyyy"
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  {openMenuId === integration.id && (
                    <div className="absolute right-6 top-16 bg-zinc-950/90 backdrop-blur-sm border border-white/[0.08] rounded-lg shadow-2xl z-[100] min-w-[140px]">
                      <button
                        onClick={(e) => handleEdit(integration, e)}
                        className="w-full px-3 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.04] rounded-t-lg transition-colors flex items-center gap-2"
                      >
                        <MdEdit className="w-3.5 h-3.5" />
                        Edit
                      </button>
                      <button
                        onClick={(e) => handleDelete(integration, e)}
                        className="w-full px-3 py-2 text-left text-xs text-rose-400 hover:bg-rose-500/5 rounded-b-lg transition-colors flex items-center gap-2"
                      >
                        <MdDelete className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <InputModal
        isOpen={createModal.isOpen}
        onClose={() => setCreateModal({ isOpen: false })}
        onSubmit={() => {
          const metadata = { api_url: createApiUrl };
          const credentials = {
            username: createUsername,
            api_token: createApiToken,
          };
          handleCreateIntegration({
            provider: createProvider,
            metadata,
            credentials,
          });
        }}
        title="Add Integration"
        submitText="Create Integration"
        size="lg"
      >
        <div className="space-y-5">
          <div>
            <label
              htmlFor="create-provider"
              className="block text-sm font-medium text-zinc-400 mb-2"
            >
              Provider
            </label>
            <select
              id="create-provider"
              value={createProvider}
              onChange={(e) => setCreateProvider(e.target.value)}
              className={inputClass}
            >
              {Object.entries(PROVIDERS).map(([key, info]) => (
                <option key={key} value={key}>
                  {info.name}
                </option>
              ))}
            </select>
          </div>

          {createProvider === "jenkins" ? (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="create-api-url"
                  className="block text-sm font-medium text-zinc-400 mb-2"
                >
                  Jenkins API URL *
                </label>
                <input
                  id="create-api-url"
                  type="url"
                  value={createApiUrl}
                  onChange={(e) => setCreateApiUrl(e.target.value)}
                  placeholder="https://jenkins.example.com"
                  required
                  className={inputClass}
                />
                <p className="text-[11px] text-zinc-600 mt-1.5">
                  The base URL of your Jenkins server
                </p>
              </div>
              <div>
                <label
                  htmlFor="create-username"
                  className="block text-sm font-medium text-zinc-400 mb-2"
                >
                  Username *
                </label>
                <input
                  id="create-username"
                  type="text"
                  value={createUsername}
                  onChange={(e) => setCreateUsername(e.target.value)}
                  placeholder="jenkins-user"
                  required
                  className={inputClass}
                />
              </div>
              <div>
                <label
                  htmlFor="create-api-token"
                  className="block text-sm font-medium text-zinc-400 mb-2"
                >
                  API Token *
                </label>
                <input
                  id="create-api-token"
                  type="password"
                  value={createApiToken}
                  onChange={(e) => setCreateApiToken(e.target.value)}
                  placeholder="Your Jenkins API token"
                  required
                  className={inputClass}
                />
                <p className="text-[11px] text-zinc-600 mt-1.5">
                  Generate an API token in Jenkins under User &rarr; Configure
                  &rarr; API Token
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-zinc-500">
                Provider form not implemented
              </p>
            </div>
          )}
        </div>
      </InputModal>

      <InputModal
        isOpen={editModal.isOpen}
        onClose={() => setEditModal({ isOpen: false, integration: null })}
        onSubmit={() => {
          if (!editModal.integration) return;
          const updateData: UpdateIntegrationData = { status: editStatus };
          const { provider, metadata: existingMetadata } =
            editModal.integration;
          const trimmedApiUrl = editApiUrl.trim();
          const providerSupportsApiUrl = provider in PROVIDERS;
          const shouldIncludeMetadata =
            trimmedApiUrl.length > 0 ||
            providerSupportsApiUrl ||
            Boolean(existingMetadata?.api_url);
          if (shouldIncludeMetadata) {
            const metadata: Record<string, string> = {};
            if (trimmedApiUrl.length > 0 || providerSupportsApiUrl) {
              metadata.api_url = trimmedApiUrl;
            } else if (existingMetadata?.api_url) {
              metadata.api_url = existingMetadata.api_url;
            }
            updateData.metadata = metadata;
          }
          const creds: Record<string, string> = {};
          if (editUsername.trim()) creds.username = editUsername.trim();
          if (editApiToken.trim()) creds.api_token = editApiToken.trim();
          if (Object.keys(creds).length > 0) updateData.credentials = creds;
          handleUpdateIntegration(editModal.integration.id, updateData);
        }}
        title="Edit Integration"
        submitText="Update Integration"
        size="lg"
      >
        {editModal.integration && (
          <div className="space-y-5">
            <div>
              <label
                htmlFor="edit-provider"
                className="block text-sm font-medium text-zinc-400 mb-2"
              >
                Provider
              </label>
              <input
                id="edit-provider"
                type="text"
                value={editModal.integration.provider}
                disabled
                className="w-full p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-zinc-500 cursor-not-allowed"
              />
            </div>

            <div>
              <label
                htmlFor="edit-status"
                className="block text-sm font-medium text-zinc-400 mb-2"
              >
                Status
              </label>
              <div className="relative">
                <button
                  id="edit-status"
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsStatusDropdownOpen(!isStatusDropdownOpen);
                  }}
                  className="w-full p-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-zinc-200 outline-none focus:border-white/[0.15] transition-colors duration-200 text-left flex items-center justify-between"
                >
                  <span className="capitalize">{editStatus}</span>
                  <svg
                    className={`h-4 w-4 text-zinc-500 transition-transform duration-200 ${
                      isStatusDropdownOpen ? "rotate-180" : ""
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

                {isStatusDropdownOpen && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-950/90 backdrop-blur-sm border border-white/[0.08] rounded-lg shadow-2xl z-[100]">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setEditStatus("active");
                        setIsStatusDropdownOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-white/[0.04] rounded-t-lg transition-colors"
                    >
                      Active
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setEditStatus("disabled");
                        setIsStatusDropdownOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-white/[0.04] rounded-b-lg transition-colors"
                    >
                      Disabled
                    </button>
                  </div>
                )}
              </div>
            </div>

            {editModal.integration.provider === "jenkins" ? (
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="edit-api-url"
                    className="block text-sm font-medium text-zinc-400 mb-2"
                  >
                    Jenkins API URL *
                  </label>
                  <input
                    id="edit-api-url"
                    type="url"
                    value={editApiUrl}
                    onChange={(e) => setEditApiUrl(e.target.value)}
                    placeholder="https://jenkins.example.com"
                    required
                    className={inputClass}
                  />
                  <p className="text-[11px] text-zinc-600 mt-1.5">
                    The base URL of your Jenkins server
                  </p>
                </div>
                <div>
                  <label
                    htmlFor="edit-username"
                    className="block text-sm font-medium text-zinc-400 mb-2"
                  >
                    Username
                  </label>
                  <input
                    id="edit-username"
                    type="text"
                    value={editUsername}
                    onChange={(e) => setEditUsername(e.target.value)}
                    placeholder="jenkins-user"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label
                    htmlFor="edit-api-token"
                    className="block text-sm font-medium text-zinc-400 mb-2"
                  >
                    API Token
                    <span className="text-[11px] text-zinc-600 ml-2">
                      (leave empty to keep current token)
                    </span>
                  </label>
                  <input
                    id="edit-api-token"
                    type="password"
                    value={editApiToken}
                    onChange={(e) => setEditApiToken(e.target.value)}
                    placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;"
                    className={inputClass}
                  />
                  <p className="text-[11px] text-zinc-600 mt-1.5">
                    Generate an API token in Jenkins under User &rarr; Configure
                    &rarr; API Token
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-sm text-zinc-500">
                  Provider form not implemented
                </p>
              </div>
            )}
          </div>
        )}
      </InputModal>

      <ConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false, integration: null })}
        onConfirm={() =>
          deleteModal.integration &&
          handleDeleteIntegration(deleteModal.integration.id)
        }
        title="Delete Integration"
        message={`Are you sure you want to delete the "${
          deleteModal.integration?.name ||
          deleteModal.integration?.provider ||
          "integration"
        }" integration?`}
        confirmText="Delete"
        variant="danger"
      />
    </div>
  );
}
