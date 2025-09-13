"use client";

import React, { useCallback, useEffect, useState } from "react";
import { format } from "date-fns";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmModal, InputModal } from "@/components/ui/modal";
import { showSuccess, showError } from "@/components/ui/toast";
import {
  MdIntegrationInstructions,
  MdMoreVert,
  MdEdit,
  MdDelete,
  MdAdd,
  MdSettings,
  MdCheckCircle,
  MdCancel,
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

export default function Integrations() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  // State
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Modal states
  const [createModal, setCreateModal] = useState({ isOpen: false });
  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    integration: Integration | null;
  }>({ isOpen: false, integration: null });
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    integration: Integration | null;
  }>({ isOpen: false, integration: null });

  // Create modal form state
  const [createProvider, setCreateProvider] = useState("jenkins");
  const [createApiUrl, setCreateApiUrl] = useState("");
  const [createUsername, setCreateUsername] = useState("");
  const [createApiToken, setCreateApiToken] = useState("");

  // Edit modal form state
  const [editStatus, setEditStatus] = useState("active");
  const [editApiUrl, setEditApiUrl] = useState("");
  const [editUsername, setEditUsername] = useState("");
  const [editApiToken, setEditApiToken] = useState("");
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);

  // API calls
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
        headers: {
          "Content-Type": "application/json",
        },
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
        headers: {
          "Content-Type": "application/json",
        },
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
      const url = `/api/integrations/${id}`;

      const response = await fetch(url, {
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

  // Event handlers

  const handleMenuToggle = (integrationId: string, event: React.MouseEvent) => {
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

  // Effects
  useEffect(() => {
    const handleClickOutside = () => {
      setOpenMenuId(null);
    };

    if (openMenuId) {
      document.addEventListener("click", handleClickOutside);
      return () => {
        document.removeEventListener("click", handleClickOutside);
      };
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
    const handleClickOutside = () => {
      setIsStatusDropdownOpen(false);
    };

    if (isStatusDropdownOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => {
        document.removeEventListener("click", handleClickOutside);
      };
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
        return <MdCheckCircle className="w-4 h-4 text-green-400" />;
      case "disabled":
        return <MdCancel className="w-4 h-4 text-red-400" />;
      default:
        return <MdSettings className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="flex flex-col h-full w-full overflow-auto px-2 py-2">
      <div
        className="relative bg-[#0A1525]/50 border border-[#1E2D45] 
                  p-8 rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10 overflow-hidden mb-8"
      >
        <div className="absolute inset-0 bg-blue-600/5 rounded-xl" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent rounded-xl" />

        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center">
          <div className="flex-1">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent tracking-tight flex items-center">
              Integrations
            </h1>
            {isAdmin ? (
              <p className="text-slate-400 mt-2">
                Configure third-party integrations for your workspace
              </p>
            ) : (
              integrations.length !== 0 && (
                <p className="text-slate-400 mt-2">
                  Ask an admin to configure integrations for your workspace
                </p>
              )
            )}
          </div>
        </div>
      </div>

      <div className="h-full">
        {integrations.length === 0 && loading ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-6"
              >
                <Skeleton className="h-6 w-2/3 bg-slate-700/50 mb-3" />
                <Skeleton className="h-4 w-1/3 bg-slate-700/30 mb-2" />
                <Skeleton className="h-4 w-full bg-slate-700/30" />
              </div>
            ))}
          </div>
        ) : integrations.length === 0 ? (
          <div className="flex justify-center items-center h-full">
            <div className="text-center py-12 px-4">
              <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 inline-block">
                <MdIntegrationInstructions className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-300 mb-2">
                  No integrations configured
                </h3>
                {isAdmin ? (
                  <p className="text-slate-400 mb-4">
                    Add your first integration to connect with external
                    services.
                  </p>
                ) : (
                  <p className="text-slate-400 mb-4">
                    Ask an admin to configure integrations for your workspace
                  </p>
                )}
                {isAdmin && (
                  <button
                    onClick={() => setCreateModal({ isOpen: true })}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 hover:border-blue-500/50 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    <MdAdd className="w-5 h-5" />
                    Add Integration
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <>
            {integrations.length === 0 ? (
              <div className="text-center py-12 px-4">
                <div className="bg-blue-500/10 rounded-lg border border-slate-700/60 p-8 inline-block">
                  <h3 className="text-lg font-semibold text-slate-300 mb-2">
                    No results found
                  </h3>
                  <p className="text-slate-400">Try a different search term.</p>
                </div>
              </div>
            ) : null}
            <div className="grid gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {integrations.map((integration) => {
                const providerInfo = getProviderInfo(integration.provider);

                return (
                  <div
                    key={integration.id}
                    className="relative group transition-all duration-300"
                  >
                    <div
                      className={`bg-blue-500/10 border border-[#1E2D45] 
                    ${
                      isAdmin
                        ? "hover:bg-blue-500/15 hover:border-blue-500/30"
                        : ""
                    } rounded-lg p-4 h-full transition-all duration-200`}
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-start gap-3">
                          <div className="flex-1">
                            <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                              {integration.name || providerInfo.name}
                              {getStatusIcon(integration.status)}
                            </h3>
                            <p className="text-sm text-slate-400">
                              {providerInfo.description}
                            </p>
                          </div>
                        </div>
                        <div className="relative">
                          {isAdmin && (
                            <button
                              onClick={(e) =>
                                handleMenuToggle(integration.id, e)
                              }
                              className="p-1 rounded-md hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors opacity-0 group-hover:opacity-100"
                              aria-label="More options"
                              aria-expanded={openMenuId === integration.id}
                            >
                              <MdMoreVert className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-400">Status:</span>
                          <span
                            className={`capitalize ${
                              integration.status === "active"
                                ? "text-green-400"
                                : integration.status === "disabled"
                                ? "text-red-400"
                                : "text-gray-400"
                            }`}
                          >
                            {integration.status}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-400">Created:</span>
                          <span className="text-slate-300">
                            {format(
                              new Date(integration.created_at),
                              "MMM d, yyyy"
                            )}
                          </span>
                        </div>
                      </div>
                    </div>

                    {openMenuId === integration.id && (
                      <div className="absolute right-6 top-16 bg-[#1A2332] border border-slate-600/60 rounded-lg shadow-lg shadow-black/20 z-[100] min-w-[150px]">
                        <button
                          onClick={(e) => handleEdit(integration, e)}
                          className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 rounded-t-lg transition-colors flex items-center gap-2"
                        >
                          <MdEdit className="w-4 h-4" />
                          Edit
                        </button>
                        <button
                          onClick={(e) => handleDelete(integration, e)}
                          className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 rounded-b-lg transition-colors flex items-center gap-2"
                        >
                          <MdDelete className="w-4 h-4" />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Create Modal */}
      <InputModal
        isOpen={createModal.isOpen}
        onClose={() => setCreateModal({ isOpen: false })}
        onSubmit={(_formData) => {
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
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Provider
            </label>
            <select
              value={createProvider}
              onChange={(e) => setCreateProvider(e.target.value)}
              className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
            >
              {Object.entries(PROVIDERS).map(([key, info]) => (
                <option key={key} value={key}>
                  {info.name}
                </option>
              ))}
            </select>
          </div>

          {createProvider === "jenkins" ? (
            <div className="space-y-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Jenkins API URL *
                  </label>
                  <input
                    type="url"
                    value={createApiUrl}
                    onChange={(e) => setCreateApiUrl(e.target.value)}
                    placeholder="https://jenkins.example.com"
                    required
                    className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    The base URL of your Jenkins server
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Username *
                  </label>
                  <input
                    type="text"
                    value={createUsername}
                    onChange={(e) => setCreateUsername(e.target.value)}
                    placeholder="jenkins-user"
                    required
                    className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    API Token *
                  </label>
                  <input
                    type="password"
                    value={createApiToken}
                    onChange={(e) => setCreateApiToken(e.target.value)}
                    placeholder="Your Jenkins API token"
                    required
                    className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Generate an API token in Jenkins under User → Configure →
                    API Token
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-slate-400">Provider form not implemented</p>
            </div>
          )}
        </div>
      </InputModal>

      {/* Edit Modal */}
      <InputModal
        isOpen={editModal.isOpen}
        onClose={() => setEditModal({ isOpen: false, integration: null })}
        onSubmit={(_formData) => {
          if (!editModal.integration) return;
          const updateData: UpdateIntegrationData = {
            status: editStatus,
            metadata: { api_url: editApiUrl },
          };
          const creds: Record<string, any> = {};
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
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Provider
              </label>
              <input
                type="text"
                value={editModal.integration.provider}
                disabled
                className="w-full p-3 rounded-lg bg-gray-900 border border-slate-700/60 text-slate-500 shadow-inner cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Status
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsStatusDropdownOpen(!isStatusDropdownOpen);
                  }}
                  className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200 text-left flex items-center justify-between"
                >
                  <span className="capitalize">{editStatus}</span>
                  <svg
                    className={`h-5 w-5 text-slate-500 transition-transform duration-200 ${
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
                  <div className="absolute top-full left-0 right-0 mb-1 bg-[#1A2332] border border-slate-600/60 rounded-lg shadow-2xl">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setEditStatus("active");
                        setIsStatusDropdownOpen(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 rounded-t-lg transition-colors flex items-center gap-2"
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
                      className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700/50 rounded-b-lg transition-colors flex items-center gap-2"
                    >
                      Disabled
                    </button>
                  </div>
                )}
              </div>
            </div>

            {editModal.integration.provider === "jenkins" ? (
              <div className="space-y-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Jenkins API URL *
                    </label>
                    <input
                      type="url"
                      value={editApiUrl}
                      onChange={(e) => setEditApiUrl(e.target.value)}
                      placeholder="https://jenkins.example.com"
                      required
                      className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      The base URL of your Jenkins server
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={editUsername}
                      onChange={(e) => setEditUsername(e.target.value)}
                      placeholder="jenkins-user"
                      className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      API Token
                      <span className="text-xs text-slate-400 ml-2">
                        (leave empty to keep current token)
                      </span>
                    </label>
                    <input
                      type="password"
                      value={editApiToken}
                      onChange={(e) => setEditApiToken(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full p-3 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 placeholder-slate-400 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Generate an API token in Jenkins under User → Configure →
                      API Token
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-slate-400">Provider form not implemented</p>
              </div>
            )}
          </div>
        )}
      </InputModal>

      {/* Delete Modal */}
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
