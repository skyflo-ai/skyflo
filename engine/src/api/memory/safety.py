"""Memory content safety scanner -- blocks secrets, large logs, and prompt injection."""

import math
import re
from typing import List, Optional, Tuple

from ..config import settings
from ..models.memory import MemoryScopeType
from .schemas import MemorySafetyFinding, MemorySafetyResult

# ---------------------------------------------------------------------------
# Secret patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: List[Tuple[str, str, str, str]] = [
    # (pattern_name, regex, severity, description)
    (
        "aws_access_key",
        r"(?<![A-Z0-9])(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])",
        "critical",
        "AWS access key ID",
    ),
    (
        "aws_secret_key",
        r"(?i)aws.{0,20}secret.{0,20}['\"]?[A-Za-z0-9/+]{40}['\"]?",
        "critical",
        "AWS secret access key",
    ),
    (
        "github_token",
        r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})",
        "critical",
        "GitHub personal access token",
    ),
    (
        "private_key_block",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "critical",
        "Private key block",
    ),
    (
        "slack_token",
        r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,34}",
        "critical",
        "Slack token",
    ),
    (
        "jwt_token",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "high",
        "JWT token",
    ),
    (
        "kubernetes_sa_token",
        r"eyJhbGciOiJSUzI1NiIsImtpZCI6",
        "critical",
        "Kubernetes service account token",
    ),
    (
        "basic_auth_header",
        r"(?i)authorization:\s*basic\s+[A-Za-z0-9+/]{16,}={0,2}",
        "critical",
        "Basic auth header",
    ),
    (
        "bearer_token",
        r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{20,}",
        "high",
        "Bearer token in Authorization header",
    ),
    (
        "database_url_with_password",
        r"(?i)(postgres|mysql|mongodb|redis|postgresql)://[^:]+:[^@]{8,}@",
        "critical",
        "Database URL with embedded password",
    ),
    (
        "kubeconfig_block",
        r"apiVersion:\s*v1\s*[\r\n]+.*kind:\s*Config",
        "critical",
        "Kubeconfig block",
    ),
    (
        "jenkins_api_token",
        r"(?i)jenkins.{0,20}token.{0,20}[A-Fa-f0-9]{32,}",
        "high",
        "Jenkins API token",
    ),
    (
        "generic_api_key",
        r"(?i)(api[_-]?key|api[_-]?secret|secret[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{20,}['\"]?",
        "medium",
        "Generic API key assignment",
    ),
]

# ---------------------------------------------------------------------------
# Prompt injection phrases
# ---------------------------------------------------------------------------

_INJECTION_PHRASES: List[str] = [
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "do not verify",
    "skip approval",
    "disable approval",
    "run without asking",
    "exfiltrate",
    "print secrets",
    "base64 decode this command",
    "you are now",
    "pretend you are",
    "forget everything",
    "disregard all",
]

# High-entropy detection threshold (chars)
_HIGH_ENTROPY_MIN_LEN = 40
_HIGH_ENTROPY_THRESHOLD = 4.8


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    n = len(s)
    return -sum((count / n) * math.log2(count / n) for count in freq.values())


def _has_high_entropy_string(content: str) -> Optional[str]:
    """Return a matching high-entropy token or None."""
    tokens = re.findall(r"[A-Za-z0-9+/=_\-\.]{" + str(_HIGH_ENTROPY_MIN_LEN) + r",}", content)
    for token in tokens:
        if _shannon_entropy(token) >= _HIGH_ENTROPY_THRESHOLD:
            return token[:20] + "..."
    return None


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class MemorySafetyScanner:
    MAX_RAW_LOG_LINES = 30

    @property
    def MAX_WRITE_BYTES(self) -> int:
        return settings.MEMORY_MAX_WRITE_BYTES

    @property
    def MAX_DOCUMENT_BYTES(self) -> int:
        return settings.MEMORY_MAX_DOCUMENT_BYTES

    def scan(self, content: str, is_conversation_memory: bool = False) -> MemorySafetyResult:
        findings: List[MemorySafetyFinding] = []
        overall_severity = "none"

        max_doc = self.MAX_DOCUMENT_BYTES
        max_write = self.MAX_WRITE_BYTES

        # Size limits
        byte_size = len(content.encode("utf-8"))
        if byte_size > max_doc:
            return MemorySafetyResult(
                allowed=False,
                redacted_content=None,
                findings=[
                    MemorySafetyFinding(
                        pattern_name="document_too_large",
                        severity="critical",
                        description=f"Document exceeds hard limit of {max_doc} bytes ({byte_size} bytes)",
                    )
                ],
                severity="critical",
            )

        if byte_size > max_write:
            findings.append(
                MemorySafetyFinding(
                    pattern_name="document_large",
                    severity="medium",
                    description=f"Document exceeds soft limit of {max_write} bytes. Consider summarizing.",
                )
            )
            overall_severity = "medium"

        # Raw log volume check (many lines with typical log timestamp patterns)
        lines = content.splitlines()
        log_line_re = re.compile(
            r"^\d{4}-\d{2}-\d{2}|^\[\d{2}:\d{2}:\d{2}\]|^[A-Z]+ \d{4}|level=(info|warn|error|debug)"
        )
        log_line_count = sum(1 for line in lines if log_line_re.match(line.strip()))
        if log_line_count > self.MAX_RAW_LOG_LINES:
            return MemorySafetyResult(
                allowed=False,
                redacted_content=None,
                findings=[
                    MemorySafetyFinding(
                        pattern_name="raw_log_volume",
                        severity="high",
                        description=f"Content appears to be raw logs ({log_line_count} log lines). Summarize the operational lesson instead.",
                    )
                ],
                severity="high",
            )

        # Secret pattern scanning
        for name, pattern, severity, description in _SECRET_PATTERNS:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                findings.append(
                    MemorySafetyFinding(
                        pattern_name=name,
                        severity=severity,
                        description=description,
                    )
                )

        # High-entropy string detection
        high_entropy_match = _has_high_entropy_string(content)
        if high_entropy_match:
            findings.append(
                MemorySafetyFinding(
                    pattern_name="high_entropy_string",
                    severity="medium",
                    description=f"High-entropy string detected (may be a token or key): {high_entropy_match}",
                )
            )

        # Determine overall severity from findings
        severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        for finding in findings:
            if severity_rank.get(finding.severity, 0) > severity_rank.get(overall_severity, 0):
                overall_severity = finding.severity

        # Block on critical secrets
        critical_findings = [f for f in findings if f.severity == "critical"]
        if critical_findings:
            return MemorySafetyResult(
                allowed=False,
                redacted_content=None,
                findings=findings,
                severity="critical",
            )

        # Prompt injection detection
        content_lower = content.lower()
        injection_findings: List[MemorySafetyFinding] = []
        for phrase in _INJECTION_PHRASES:
            if phrase in content_lower:
                injection_findings.append(
                    MemorySafetyFinding(
                        pattern_name="prompt_injection",
                        severity="high",
                        description=f"Possible prompt injection phrase: '{phrase}'",
                    )
                )

        if injection_findings:
            if not is_conversation_memory:
                # Only allow in conversation memory (agent_draft), block elsewhere
                all_findings = findings + injection_findings
                return MemorySafetyResult(
                    allowed=False,
                    redacted_content=None,
                    findings=all_findings,
                    severity="high",
                )
            # In conversation_memory: note the findings but allow (it's ephemeral draft)
            findings.extend(injection_findings)
            overall_severity = "high"

        return MemorySafetyResult(
            allowed=True,
            redacted_content=None,
            findings=findings,
            severity=overall_severity,
        )

    def scan_write(self, content: str, store_scope_type: MemoryScopeType) -> MemorySafetyResult:
        is_conversation = store_scope_type == MemoryScopeType.CONVERSATION
        return self.scan(content, is_conversation_memory=is_conversation)
