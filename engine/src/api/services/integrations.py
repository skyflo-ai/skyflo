import json
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from tortoise.transactions import in_transaction

from ..config import settings
from ..models.integration import Integration
from ..integrations.jenkins import build_jenkins_secret_yaml
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


def _dns_safe_uid(max_len: int = 20) -> str:
    raw = uuid.uuid4().hex
    return raw[: max(1, max_len)]


def _provider_secret_name(provider: str) -> str:
    return f"{provider}-cred-{_dns_safe_uid()}"


class IntegrationService:
    def __init__(self, mcp_client: Optional[MCPClient] = None) -> None:
        self._mcp = mcp_client
        self._owns_client = mcp_client is None

    async def _get_mcp_client(self) -> MCPClient:
        if self._mcp is None:
            self._mcp = MCPClient()
        return self._mcp

    async def _apply_secret(self, content: str, namespace: Optional[str]) -> Dict[str, Any]:
        if self._owns_client:
            async with MCPClient() as mcp:
                return await mcp.call_tool(
                    "k8s_apply", {"content": content, "namespace": namespace}
                )
        else:
            return await self._mcp.call_tool(
                "k8s_apply", {"content": content, "namespace": namespace}
            )

    async def _delete_secret(self, name: str, namespace: Optional[str]) -> Dict[str, Any]:
        if self._owns_client:
            async with MCPClient() as mcp:
                return await mcp.call_tool(
                    "k8s_delete", {"name": name, "resource_type": "secret", "namespace": namespace}
                )
        else:
            return await self._mcp.call_tool(
                "k8s_delete", {"name": name, "resource_type": "secret", "namespace": namespace}
            )

    async def _create_or_replace_secret(
        self, provider: str, credentials: Dict[str, str], namespace: Optional[str]
    ) -> Tuple[str, str]:
        ns = namespace or settings.INTEGRATIONS_SECRET_NAMESPACE or "default"
        secret_name = _provider_secret_name(provider)

        if provider == "jenkins":
            yaml_content = build_jenkins_secret_yaml(secret_name, ns, credentials)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        await self._apply_secret(yaml_content, ns)
        return ns, secret_name

    async def create_integration(
        self,
        created_by_user_id: str,
        provider: str,
        metadata: Optional[Dict[str, Any]],
        credentials: Dict[str, str],
        name: Optional[str] = None,
    ) -> Integration:
        provider = (provider or "").strip().lower()
        if not provider:
            raise ValueError("provider is required")

        existing = await Integration.get_or_none(provider=provider)
        if existing:
            raise ValueError(f"Integration for provider '{provider}' already exists")

        ns, secret_name = await self._create_or_replace_secret(provider, credentials, None)
        credentials_ref = f"{ns}/{secret_name}"

        async with in_transaction():
            integration = await Integration.create(
                user_id=created_by_user_id,
                provider=provider,
                name=name,
                metadata=(metadata or {}),
                credentials_ref=credentials_ref,
                status="active",
            )
        return integration

    async def update_integration(
        self,
        integration_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Integration:
        integration = await Integration.get(id=integration_id)

        if credentials is not None:
            ns, secret_name = await self._create_or_replace_secret(
                integration.provider, credentials, None
            )
            integration.credentials_ref = f"{ns}/{secret_name}"

        if metadata is not None:
            integration.metadata = metadata
        if name is not None:
            integration.name = name
        if status is not None:
            integration.status = status

        await integration.save()
        return integration

    async def delete_integration(self, integration_id: str) -> None:
        integration = await Integration.get(id=integration_id)
        if integration.credentials_ref:
            try:
                ns, name = integration.credentials_ref.split("/", 1)
                await self._delete_secret(name=name, namespace=ns)
            except Exception as e:
                logger.warning(
                    f"Failed to delete credentials secret {integration.credentials_ref}: {e}"
                )
        await integration.delete()

    async def list_integrations(self, provider: Optional[str] = None):
        if provider:
            return await Integration.filter(provider=provider.lower())
        return await Integration.all()

    async def get_integration(self, provider: str) -> Optional[Integration]:
        return await Integration.get_or_none(provider=(provider or "").lower())
