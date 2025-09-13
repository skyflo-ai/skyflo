from copy import deepcopy
from typing import Dict, List, Any, Optional
from pathlib import Path


def build_jenkins_secret_yaml(name: str, namespace: str, creds: Dict[str, str]) -> str:
    username = creds.get("username") or creds.get("user")
    api_token = creds.get("api_token") or creds.get("api-token") or creds.get("token")

    if not username or not api_token:
        raise ValueError("Jenkins credentials must include 'username' and 'api_token'")

    template_path = Path(__file__).parent / "secret.yaml"
    with open(template_path, "r") as f:
        template = f.read()

    resolved_yaml = template.format(
        name=name, namespace=namespace, username=username, api_token=api_token
    )

    return resolved_yaml


def _tool_has_jenkins_tag(tool: Dict[str, Any]) -> bool:
    try:
        tags = tool.get("tags") or []
        if isinstance(tags, list) and "jenkins" in tags:
            return True
        meta = tool.get("meta", {}) or {}
        fastmcp = meta.get("_fastmcp", {}) or {}
        fm_tags = fastmcp.get("tags") or []
        return isinstance(fm_tags, list) and "jenkins" in fm_tags
    except Exception:
        return False


def _strip_jenkins_input_params(tool: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(tool)
    input_schema = updated.get("inputSchema") or updated.get("input_schema")
    if not isinstance(input_schema, dict):
        return updated

    props = input_schema.get("properties", {}) or {}
    required = list(input_schema.get("required", []) or [])
    params_to_strip = ["api_url", "credentials_ref"]

    for p in params_to_strip:
        if p in props:
            props.pop(p, None)
        if p in required:
            required = [r for r in required if r != p]

    input_schema["properties"] = props
    if required:
        input_schema["required"] = required
    else:
        input_schema.pop("required", None)
    updated["inputSchema"] = input_schema
    return updated


def filter_jenkins_tools(
    tools: List[Dict[str, Any]],
    integration_status: Optional[str] = None,
    is_configured: bool = False,
) -> List[Dict[str, Any]]:
    if not is_configured or integration_status == "disabled":
        return [t for t in tools if not _tool_has_jenkins_tag(t)]

    transformed: List[Dict[str, Any]] = []
    for tool in tools:
        if _tool_has_jenkins_tag(tool):
            tool = _strip_jenkins_input_params(tool)
        transformed.append(tool)

    return transformed


def _is_jenkins_tool(tool_metadata: Optional[Dict[str, Any]], tool_name: str) -> bool:
    if not tool_metadata:
        return tool_name.startswith("jenkins_")
    return _tool_has_jenkins_tag(tool_metadata) or tool_name.startswith("jenkins_")


def inject_jenkins_metadata_tool_args(
    tool_name: str,
    args: Dict[str, Any],
    tool_metadata: Optional[Dict[str, Any]],
    integration: Optional[Any] = None,
) -> tuple[Dict[str, Any], Optional[str]]:
    if not _is_jenkins_tool(tool_metadata, tool_name):
        return args, None

    if not integration or integration.status == "disabled":
        return (
            args,
            "Jenkins integration is not configured. Admins can create one via /api/v1/integrations.",
        )

    provided = dict(args or {})
    meta = integration.metadata or {}

    if "api_url" not in provided and "api_url" in meta:
        provided["api_url"] = meta["api_url"]

    if "credentials_ref" not in provided and integration.credentials_ref:
        provided["credentials_ref"] = integration.credentials_ref

    return provided, None


def strip_jenkins_metadata_tool_args(args: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(args, dict):
        return args
    if not args:
        return args

    metadata_keys = ["api_url", "credentials_ref"]

    if not any(key in args for key in metadata_keys):
        return args

    sanitized = {k: v for k, v in args.items() if k not in metadata_keys}
    return sanitized
