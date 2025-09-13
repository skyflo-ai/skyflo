"""Shared command execution utilities for MCP tools."""

import asyncio
from typing import Optional
from .types import ToolOutput


async def run_command(
    cmd: str, args: list[str], stdin: Optional[str] = None
) -> ToolOutput:
    """Run a command and return its output with error status."""
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        )
        stdout, stderr = await proc.communicate(
            input=stdin.encode() if stdin is not None else None
        )

        stdout_text = stdout.decode().strip()
        stderr_text = stderr.decode().strip()

        if proc.returncode != 0:
            return {
                "output": f"Error executing command {cmd} with args {args}: {stderr_text}",
                "error": True,
            }

        if stdout_text:
            output_text = stdout_text
            error = False
        elif stderr_text:
            output_text = stderr_text
            error = True
        else:
            output_text = (
                "The command was executed successfully, but no output was returned."
            )
            error = False

        return {"output": output_text, "error": error}
    except Exception as e:
        return {
            "output": f"Error executing command {cmd} with args {args}: {str(e)}",
            "error": True,
        }
