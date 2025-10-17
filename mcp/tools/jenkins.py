"""Jenkins tools implementation for MCP server."""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
from typing import Any, Dict, Optional, Tuple, List
import xml.etree.ElementTree as ET


import httpx
from pydantic import Field

from config.server import mcp
from utils.types import ToolOutput

# -----------------------------
# Credential resolution helpers
# -----------------------------


def _parse_credentials_ref(credentials_ref: str) -> Tuple[str, str]:
    """Parse a credentials_ref strictly in the form 'namespace/name'."""
    if not credentials_ref or "/" not in credentials_ref or ":" in credentials_ref:
        raise ValueError("credentials_ref must be in the form 'namespace/name'")
    namespace, name = credentials_ref.split("/", 1)
    if not namespace or not name:
        raise ValueError("credentials_ref components cannot be empty")
    # Basic character allowlist to reduce risk of shell injection
    for part in (namespace, name):
        if not all(c.isalnum() or c in ("-", ".", "_") for c in part):
            raise ValueError("credentials_ref contains invalid characters")
    return namespace, name


def resolve_credentials_from_k8s(credentials_ref: str) -> Tuple[str, str]:
    namespace, name = _parse_credentials_ref(credentials_ref)
    try:
        proc = subprocess.run(
            ["kubectl", "-n", namespace, "get", "secret", name, "-o", "json"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError("Timeout retrieving credentials Secret via kubectl")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get Secret {namespace}/{name}: {e.stderr}")

    secret = json.loads(proc.stdout)
    data = secret.get("data", {}) or {}

    b64_username = data.get("username")
    b64_api_token = data.get("api-token")
    if not b64_username or not b64_api_token:
        raise ValueError(
            "credentials not found in Secret: expected 'username' and 'api-token' keys"
        )
    username = base64.b64decode(b64_username).decode("utf-8")
    api_token = base64.b64decode(b64_api_token).decode("utf-8")
    return username, api_token


# -----------------------------
# HTTP client helpers
# -----------------------------


class JenkinsClient:
    def __init__(
        self, base_url: str, username: str, api_token: str, verify: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(username, api_token),
            timeout=httpx.Timeout(15.0, connect=5.0),
            verify=verify,
        )

    async def _crumb_headers(self) -> Dict[str, str]:
        try:
            resp = await self.client.get("/crumbIssuer/api/json")
            if resp.status_code in (403, 404):
                return {}
            resp.raise_for_status()
            data = resp.json()
            field = data.get("crumbRequestField")
            crumb = data.get("crumb")
            if field and crumb:
                return {field: crumb}
        except Exception:
            return {}
        return {}

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        return await self.client.get(path, params=params)

    async def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        crumb_hdrs = await self._crumb_headers()
        merged_headers = {**(headers or {}), **crumb_hdrs}
        return await self.client.post(path, data=data, headers=merged_headers)

    async def close(self) -> None:
        await self.client.aclose()


def is_jenkins_post_success(resp: httpx.Response) -> bool:
    """Check if a Jenkins POST request was successful.

    Jenkins sometimes returns redirects (302, 303) for successful POST operations,
    so we treat both successful responses and redirects as success.
    """
    return resp.is_success or resp.status_code in [302, 303]


def build_job_path(job_full_name: str) -> str:
    # Convert 'Folder/Sub/My Job' -> '/job/Folder/job/Sub/job/My%20Job'
    if not job_full_name:
        raise ValueError("jobFullName is required")
    segments = [seg.strip() for seg in job_full_name.split("/") if seg.strip()]
    encoded = [httpx.QueryParams({"s": seg}).get("s") for seg in segments]
    return "/" + "/".join([f"job/{seg}" for seg in encoded])


def normalize_response(
    resp: httpx.Response, body_text: Optional[str] = None
) -> ToolOutput:
    info: Dict[str, Any] = {
        "status": resp.status_code,
        "headers": {
            k: v for k, v in resp.headers.items() if k.lower().startswith("x-")
        },
    }
    try:
        info["body"] = resp.json()
    except Exception:
        info["body"] = body_text if body_text is not None else resp.text
    return {"output": json.dumps(info), "error": not resp.is_success}


async def _with_client(
    api_url: str, credentials_ref: str, verify: bool = True
) -> JenkinsClient:
    username, api_token = resolve_credentials_from_k8s(credentials_ref)
    return JenkinsClient(api_url, username, api_token, verify=verify)


# -----------------------------
# Tools: Job Management
# -----------------------------


@mcp.tool(
    title="Jenkins: Get Job", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_get_job(
    api_url: str = Field(
        description="Base Jenkins URL, e.g., https://jenkins.example.com"
    ),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path, e.g., Folder/Sub/Job"),
    tree: Optional[str] = Field(
        default="name,url,color", description="Optional tree filter"
    ),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        path = f"{build_job_path(jobFullName)}/api/json"
        params = {"tree": tree} if tree else None
        resp = await client.get(path, params=params)
        return normalize_response(resp)
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: List Jobs",
    tags=["jenkins"],
    annotations={"readOnlyHint": True},
)
async def jenkins_get_jobs(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    start: Optional[int] = Field(default=0, description="Pagination start index"),
    limit: Optional[int] = Field(default=50, description="Page size (max ~100)"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        tree = f"jobs[name,url]{{0,{max(0, limit or 50)}}}"
        resp = await client.get("/api/json", params={"tree": tree})
        if not resp.is_success:
            return normalize_response(resp)
        body = resp.json()
        jobs = body.get("jobs", [])
        sliced = jobs[start : (start or 0) + (limit or 50)]
        data = {"status": resp.status_code, "body": {"jobs": sliced}}
        return {"output": json.dumps(data), "error": False}
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Trigger Build",
    tags=["jenkins"],
    annotations={"readOnlyHint": False},
)
async def jenkins_trigger_build(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional parameters for parameterized jobs"
    ),
    verify: Optional[bool] = Field(default=True, description="TLS verify"),
) -> ToolOutput:
    client = await _with_client(
        api_url, credentials_ref, verify=verify if verify is not None else True
    )
    try:
        path_base = build_job_path(jobFullName)
        path = (
            f"{path_base}/buildWithParameters" if parameters else f"{path_base}/build"
        )
        resp = await client.post(path, data=parameters or {})
        if not is_jenkins_post_success(resp):
            return normalize_response(resp)

        queue_url = resp.headers.get("Location")
        if not queue_url:
            return {
                "output": json.dumps(
                    {
                        "status": resp.status_code,
                        "body": {"message": "No queue Location header"},
                    }
                ),
                "error": True,
            }

        async def poll_queue() -> Dict[str, Any]:
            attempt = 0
            while attempt < 30:
                queue_path = queue_url.replace(client.base_url, "")
                if not queue_path.endswith("/api/json"):
                    queue_path = queue_path.rstrip("/") + "/api/json"
                q_resp = await client.get(queue_path)
                if q_resp.is_success:
                    try:
                        q_body = q_resp.json()
                    except Exception:
                        q_body = {}
                    exe = q_body.get("executable")
                    if exe and isinstance(exe, dict) and "number" in exe:
                        return {"buildNumber": exe["number"], "url": exe.get("url")}
                await asyncio.sleep(min(1.0 * (2**attempt), 5.0))
                attempt += 1
            return {"message": "Timed out waiting for build to start"}

        result = await poll_queue()
        err = "buildNumber" not in result
        return {"output": json.dumps(result), "error": err}
    finally:
        await client.close()


# -----------------------------
# Tools: Build Information
# -----------------------------


@mcp.tool(
    title="Jenkins: Get Build", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_get_build(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[str] = Field(
        default="lastBuild", description="Build number or 'lastBuild'"
    ),
    tree: Optional[str] = Field(
        default="number,result,timestamp,url", description="Optional tree filter"
    ),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        path = f"{build_job_path(jobFullName)}/{build or 'lastBuild'}/api/json"
        params = {"tree": tree} if tree else None
        resp = await client.get(path, params=params)
        return normalize_response(resp)
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Get Builds",
    tags=["jenkins"],
    annotations={"readOnlyHint": True},
)
async def jenkins_get_last_builds(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    count: Optional[int] = Field(
        default=10,
        description="Number of recent builds to retrieve (default: 10, max: 100)",
    ),
    tree: Optional[str] = Field(
        default="number,result,timestamp,url,duration",
        description="Optional tree filter for build fields",
    ),
) -> ToolOutput:
    """Get the last N builds for a Jenkins job."""
    client = await _with_client(api_url, credentials_ref)
    try:
        build_count = max(1, min(count or 10, 100))

        builds_tree = f"builds[{tree}]{{0,{build_count}}}"

        path = f"{build_job_path(jobFullName)}/api/json"
        params = {"tree": builds_tree}

        resp = await client.get(path, params=params)

        if not resp.is_success:
            return normalize_response(resp)

        body = resp.json()
        builds = body.get("builds", [])

        builds.sort(key=lambda b: b.get("number", 0), reverse=True)

        result = {
            "status": resp.status_code,
            "body": {
                "jobFullName": jobFullName,
                "totalBuilds": len(builds),
                "builds": builds,
            },
        }

        return {"output": json.dumps(result), "error": False}
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Update Build", tags=["jenkins"], annotations={"readOnlyHint": False}
)
async def jenkins_update_build(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[int] = Field(
        default=None, description="Build number; defaults to lastBuild"
    ),
    displayName: Optional[str] = Field(default=None, description="New display name"),
    description: Optional[str] = Field(default=None, description="New description"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        target = f"{build_job_path(jobFullName)}/{build if build is not None else 'lastBuild'}"
        last_resp: Optional[httpx.Response] = None
        if description is not None:
            last_resp = await client.post(
                f"{target}/submitDescription", data={"description": description}
            )
            if not is_jenkins_post_success(last_resp):
                return normalize_response(last_resp)
        if displayName is not None:
            last_resp = await client.post(
                f"{target}/submitDisplayName", data={"displayName": displayName}
            )
            if not is_jenkins_post_success(last_resp):
                return normalize_response(last_resp)
        if last_resp is None:
            return {
                "output": json.dumps(
                    {"status": 400, "body": {"message": "No fields to update"}}
                ),
                "error": True,
            }
        return normalize_response(last_resp)
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Stop Build", tags=["jenkins"], annotations={"readOnlyHint": False}
)
async def jenkins_stop_build(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[str] = Field(
        default="lastBuild", description="Build number or 'lastBuild'"
    ),
) -> ToolOutput:
    """Stop/cancel a running Jenkins build.
    
    This tool attempts to stop a running build. If the build is not currently running,
    it will return a clear message indicating the current state.
    """
    
    client = await _with_client(api_url, credentials_ref)
    try:
        info_path = f"{build_job_path(jobFullName)}/{build or 'lastBuild'}/api/json"
        info_resp = await client.get(info_path, params={"tree": "number,result,building,url"})
        
        if not info_resp.is_success:
            return normalize_response(info_resp)
        
        build_info = info_resp.json()
        build_number = build_info.get("number")
        is_building = build_info.get("building", False)
        result = build_info.get("result")
        build_url = build_info.get("url", "")

        if not is_building:
            status_msg = "completed" if result else "not running"
            message = f"Build #{build_number} is {status_msg} and cannot be stopped"
            if result:
                message += f" (result: {result})"
            
            return {
                "output": json.dumps({
                    "status": 200,
                    "body": {
                        "message": message,
                        "buildNumber": build_number,
                        "building": False,
                        "result": result,
                        "url": build_url
                    }
                }),
                "error": False
            }
        
        stop_path = f"{build_job_path(jobFullName)}/{build_number}/stop"
        stop_resp = await client.post(stop_path)

        # Check if stop request was accepted
        if not is_jenkins_post_success(stop_resp):
            return normalize_response(stop_resp)
        
        # Wait a moment for Jenkins to process the stop request
        await asyncio.sleep(1)
        
        updated_build_info_resp = await client.get(info_path, params={"tree": "number,result,building,url"})
        
        if not updated_build_info_resp.is_success:
            return {
                "output": json.dumps({
                    "status": stop_resp.status_code,
                    "body": {
                        "message": f"Stop command sent for build #{build_number} (status: {stop_resp.status_code}). Unable to verify completion.",
                        "buildNumber": build_number,
                        "stopResponseCode": stop_resp.status_code,
                        "url": build_url
                    }
                }),
                "error": False
            }
        
        updated_build_info = updated_build_info_resp.json()
        is_building_after_stop = updated_build_info.get("building", False)
        result_after_stop = updated_build_info.get("result")

        return {
            "output": json.dumps({
                "status": 200,
                "body": {
                    "message": f"Successfully stopped build #{build_number}" if not is_building_after_stop else f"Stop requested for build #{build_number} (still stopping...)",
                    "buildNumber": build_number,
                    "building": is_building_after_stop,
                    "result": result_after_stop,
                    "stopResponseCode": stop_resp.status_code,
                    "url": build_url
                }
            }),
            "error": False
        }
            
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Get Build Log", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_get_build_log(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[int] = Field(
        default=None, description="Build number; defaults to lastBuild"
    ),
    start: Optional[int] = Field(default=0, description="Log offset to start from"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        b = build if build is not None else "lastBuild"
        path = f"{build_job_path(jobFullName)}/{b}/logText/progressiveText"
        resp = await client.get(path, params={"start": max(0, start or 0)})
        headers = {k: v for k, v in resp.headers.items() if k.lower().startswith("x-")}
        payload = {
            "status": resp.status_code,
            "headers": headers,
            "body": resp.text,
        }
        return {"output": json.dumps(payload), "error": not resp.is_success}
    finally:
        await client.close()


# -----------------------------
# Tools: SCM Integration
# -----------------------------


@mcp.tool(
    title="Jenkins: Get Job SCM", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_get_job_scm(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        # Try JSON first
        resp = await client.get(f"{build_job_path(jobFullName)}/api/json")
        if resp.is_success:
            data = resp.json()
            if "scm" in data and data["scm"]:
                return normalize_response(resp)
        # Fallback to config.xml
        xml_resp = await client.get(f"{build_job_path(jobFullName)}/config.xml")
        return normalize_response(xml_resp)
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Get Build SCM", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_get_build_scm(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[int] = Field(
        default=None, description="Build number; defaults to lastBuild"
    ),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        b = build if build is not None else "lastBuild"
        resp = await client.get(f"{build_job_path(jobFullName)}/{b}/api/json")
        return normalize_response(resp)
    finally:
        await client.close()


@mcp.tool(
    title="Jenkins: Get Build Change Sets",
    tags=["jenkins"],
    annotations={"readOnlyHint": True},
)
async def jenkins_get_build_changesets(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name)"),
    jobFullName: str = Field(description="Full job path"),
    build: Optional[int] = Field(
        default=None, description="Build number; defaults to lastBuild"
    ),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        b = build if build is not None else "lastBuild"
        tree = "changeSets[items[commitId,author[fullName],msg,date]],url,number"
        resp = await client.get(
            f"{build_job_path(jobFullName)}/{b}/api/json", params={"tree": tree}
        )
        return normalize_response(resp)
    finally:
        await client.close()


# -----------------------------
# Tools: Identity
# -----------------------------


@mcp.tool(
    title="Jenkins: Who Am I", tags=["jenkins"], annotations={"readOnlyHint": True}
)
async def jenkins_whoami(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref)
    try:
        resp = await client.get("/me/api/json")
        return normalize_response(resp)
    finally:
        await client.close()

# -----------------------------
# Tools: Job Parameter Helpers
# -----------------------------


def _normalize_param_type(raw_type: Optional[str]) -> str:
    if not raw_type:
        return "string"
    short = raw_type.split(".")[-1]
    mapping = {
        "StringParameterDefinition": "string",
        "BooleanParameterDefinition": "boolean",
        "ChoiceParameterDefinition": "choice",
        "TextParameterDefinition": "text",
        "PasswordParameterDefinition": "password",
        "FileParameterDefinition": "file",
    }
    return mapping.get(short, "string")

def _parse_config_xml(xml_text: str) -> List[dict]:
    params = []
    ns = {"jenkins": "http://hudson.model"}
    root = ET.fromstring(xml_text)
    for param_def in root.findall(".//parameterDefinitions/*", ns):
        ptype = param_def.tag.split(".")[-1]
        name = param_def.findtext("name") or ""
        desc = param_def.findtext("description") or ""
        default = param_def.findtext("defaultValue")
        # Jenkins writes choices in multiple shapes; collect any string-like children
        choices_el = param_def.find("choices")
        choices: List[str] = []
        if choices_el is not None:
            # Common: <choices><string>opt</string>...</choices>
            for c in choices_el.findall(".//string"):
                if c.text is not None:
                    choices.append(c.text)
            # Fallback: any direct child text nodes
            if not choices:
                for child in list(choices_el):
                    if child.text:
                        choices.append(child.text)
        params.append({
            "name": name,
            "type": _normalize_param_type(ptype),
            "description": desc,
            "default": default,
            "choices": choices if choices else None,
        })
    return params


# -----------------------------
# Tools: Get Job Parameters
# -----------------------------


@mcp.tool(
    title="Jenkins: Get Job Parameters",
    tags=["jenkins"],
    annotations={"readOnlyHint": True},
)
async def jenkins_get_job_parameters(
    api_url: str = Field(description="Base Jenkins URL"),
    credentials_ref: str = Field(description="Kubernetes Secret ref: namespace/name"),
    jobFullName: str = Field(description="Full job path"),
    verify: Optional[bool] = Field(default=True, description="TLS verify"),
) -> ToolOutput:
    client = await _with_client(api_url, credentials_ref, verify=verify)
    try:
        # Try JSON first
        tree = "actions[parameterDefinitions[name,description,defaultParameterValue[value],choices,type,_class]]"
        resp = await client.get(f"{build_job_path(jobFullName)}/api/json", params={"tree": tree})
        params = []
        if resp.is_success:
            data = resp.json()
            for action in data.get("actions", []):
                defs = action.get("parameterDefinitions")
                if defs:
                    for d in defs:
                        name = d.get("name")
                        desc = d.get("description")
                        raw_type = d.get("_class") or d.get("type")
                        default = (d.get("defaultParameterValue") or {}).get("value")
                        choices_field = d.get("choices")
                        if isinstance(choices_field, dict) and "values" in choices_field:
                            choices = choices_field.get("values")
                        elif isinstance(choices_field, list):
                            choices = choices_field
                        elif isinstance(choices_field, str):
                            choices = [c.strip() for c in choices_field.splitlines() if c.strip()]
                        else:
                            choices = None
                        params.append({
                            "name": name,
                            "type": _normalize_param_type(raw_type),
                            "description": desc,
                            "default": default,
                            "choices": choices,
                        })
        # Fallback to XML
        if not params:
            xml_resp = await client.get(f"{build_job_path(jobFullName)}/config.xml")
            if xml_resp.is_success:
                params = _parse_config_xml(xml_resp.text)
        return {"output": json.dumps(params), "error": False}
    except Exception as e:
        return {"output": json.dumps({"error": str(e)}), "error": True}
    finally:
        await client.close()