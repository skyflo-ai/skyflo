import uuid
from typing import Any, Dict, List, Optional
import json
from ..models.conversation import Conversation


class ConversationPersistenceService:
    def __init__(self):
        pass

    async def append_user_message(self, conversation_id: str, content: str, timestamp: int) -> None:
        conversation = await Conversation.get(id=conversation_id)
        messages: List[Dict[str, Any]] = conversation.messages_json or []

        if (
            messages
            and messages[-1].get("type") == "user"
            and messages[-1].get("content") == content
        ):
            return

        user_message = {
            "id": str(uuid.uuid4()),
            "type": "user",
            "content": content,
            "timestamp": timestamp,
        }

        messages.append(user_message)
        await conversation.update_from_dict({"messages_json": messages}).save()

    async def append_text_segment(self, conversation_id: str, text: str, timestamp: int) -> None:
        conversation = await Conversation.get(id=conversation_id)
        messages: List[Dict[str, Any]] = conversation.messages_json or []

        if not messages or messages[-1].get("type") != "assistant":
            assistant_message = {
                "id": str(uuid.uuid4()),
                "type": "assistant",
                "content": text,
                "timestamp": timestamp,
                "segments": [
                    {"kind": "text", "id": str(uuid.uuid4()), "text": text, "timestamp": timestamp}
                ],
            }
            messages.append(assistant_message)
        else:
            assistant = messages[-1]
            segments: List[Dict[str, Any]] = assistant.get("segments", [])

            segments.append(
                {"kind": "text", "id": str(uuid.uuid4()), "text": text, "timestamp": timestamp}
            )

            assistant["content"] = assistant.get("content", "") + text
            assistant["segments"] = segments

        await conversation.update_from_dict({"messages_json": messages}).save()

    async def append_tool_segment(
        self, conversation_id: str, tool_execution: Dict[str, Any], timestamp: int
    ) -> None:
        conversation = await Conversation.get(id=conversation_id)
        messages: List[Dict[str, Any]] = conversation.messages_json or []

        if not messages or messages[-1].get("type") != "assistant":
            assistant_message = {
                "id": str(uuid.uuid4()),
                "type": "assistant",
                "content": "",
                "timestamp": timestamp,
                "segments": [],
            }
            messages.append(assistant_message)

        assistant = messages[-1]
        segments: List[Dict[str, Any]] = assistant.get("segments", [])
        call_id = tool_execution.get("call_id")

        existing_index = next(
            (
                i
                for i in range(len(segments))
                if segments[i].get("kind") == "tool" and segments[i].get("id") == call_id
            ),
            -1,
        )

        if existing_index >= 0:
            return

        segment = {
            "kind": "tool",
            "id": call_id,
            "toolExecution": tool_execution,
            "timestamp": timestamp,
        }

        segments.append(segment)
        assistant["segments"] = segments

        await conversation.update_from_dict({"messages_json": messages}).save()

    async def update_tool_segment_status(
        self,
        conversation_id: str,
        call_id: str,
        status: str,
        error: Optional[str] = None,
        result: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        conversation = await Conversation.get(id=conversation_id)
        messages: List[Dict[str, Any]] = conversation.messages_json or []
        if not messages:
            return

        assistant = messages[-1]
        segments: List[Dict[str, Any]] = assistant.get("segments", [])
        for i in range(len(segments) - 1, -1, -1):
            seg = segments[i]
            if seg.get("kind") == "tool" and seg.get("id") == call_id:
                exec_obj = seg.get("toolExecution", {})
                exec_obj["status"] = status
                if error is not None:
                    exec_obj["error"] = error
                if result is not None:
                    exec_obj["result"] = result
                seg["toolExecution"] = exec_obj
                segments[i] = seg
                assistant["segments"] = segments
                await conversation.update_from_dict({"messages_json": messages}).save()
                return

    async def build_llm_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:

        messages_json: List[Dict[str, Any]] = conversation.messages_json or []

        llm_messages: List[Dict[str, Any]] = []

        for msg in messages_json:
            mtype = msg.get("type")
            if mtype == "user":
                content = str(msg.get("content", ""))
                if content:
                    llm_messages.append({"role": "user", "content": content})
                continue

            if mtype != "assistant":
                continue

            segments: List[Dict[str, Any]] = msg.get("segments", []) or []
            first_tool_index = next(
                (i for i, segment in enumerate(segments) if segment.get("kind") == "tool"), -1
            )
            last_tool_index = max(
                (i for i, segment in enumerate(segments) if segment.get("kind") == "tool"),
                default=-1,
            )

            if first_tool_index > 0:
                pre_text_parts: List[str] = []
                for segment in segments[:first_tool_index]:
                    if segment.get("kind") == "text":
                        pre_text_parts.append(str(segment.get("text", "")))
                pre_text = "".join(pre_text_parts)
                if pre_text:
                    llm_messages.append({"role": "assistant", "content": pre_text})

            tool_calls: List[Dict[str, Any]] = []
            tool_segments: List[Dict[str, Any]] = []
            for segment in segments:
                if segment.get("kind") != "tool":
                    continue
                tool_exec = segment.get("toolExecution", {}) or {}
                tool_name = tool_exec.get("tool") or ""
                call_id = str(tool_exec.get("call_id") or "").strip()
                args_obj = tool_exec.get("args") or {}
                args_str = json.dumps(args_obj) if isinstance(args_obj, dict) else str(args_obj)
                tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": args_str},
                    }
                )
                tool_segments.append(segment)

            if tool_calls:
                llm_messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})

                for segment in tool_segments:
                    tool_exec = segment.get("toolExecution", {}) or {}
                    tool_name = tool_exec.get("tool") or ""
                    call_id = str(tool_exec.get("call_id") or "").strip()
                    result_blocks = tool_exec.get("result") or []
                    result_content = ""
                    if result_blocks:
                        for block in result_blocks:
                            if isinstance(block, dict) and block.get("type") == "text":
                                result_content += str(block.get("text", ""))
                            else:
                                result_content += str(block)
                    else:
                        status = (tool_exec.get("status") or "").lower()
                        if status == "awaiting_approval":
                            result_content = "Pending tool approval from the user"
                        elif status == "denied":
                            result_content = "Tool call was denied by the user"
                        elif status == "error":
                            err = tool_exec.get("error") or "Tool execution failed"
                            result_content = str(err)

                    llm_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": tool_name,
                            "content": result_content,
                        }
                    )

            if last_tool_index >= 0 and last_tool_index < len(segments) - 1:
                post_text_parts: List[str] = []
                for segment in segments[last_tool_index + 1 :]:
                    if segment.get("kind") == "text":
                        post_text_parts.append(str(segment.get("text", "")))
                post_text = "".join(post_text_parts)
                if post_text:
                    llm_messages.append({"role": "assistant", "content": post_text})

            if not tool_calls:
                content = str(msg.get("content", ""))
                if content:
                    llm_messages.append({"role": "assistant", "content": content})

        return llm_messages

    async def build_llm_messages_for_title_generation(
        self, conversation: Conversation
    ) -> List[Dict[str, Any]]:
        """
        Build a simplified message list for title generation.
        - Includes only 'user' and 'assistant' messages with plain text content.
        - Excludes any tool call metadata and 'tool' role messages.
        """
        messages_json: List[Dict[str, Any]] = conversation.messages_json or []

        simplified: List[Dict[str, Any]] = []

        for msg in messages_json:
            mtype = msg.get("type")
            if mtype == "user":
                content = str(msg.get("content", ""))
                if content:
                    simplified.append({"role": "user", "content": content})
                continue

            if mtype != "assistant":
                continue

            # Prefer concatenated text content if present; otherwise, stitch text segments only
            content = str(msg.get("content", ""))
            if content:
                simplified.append({"role": "assistant", "content": content})
                continue

            segments: List[Dict[str, Any]] = msg.get("segments", []) or []
            text_parts: List[str] = []
            for segment in segments:
                if segment.get("kind") == "text":
                    text_parts.append(str(segment.get("text", "")))
            stitched = "".join(text_parts).strip()
            if stitched:
                simplified.append({"role": "assistant", "content": stitched})

        return simplified

    async def set_title(self, conversation_id: str, title: str) -> None:
        conversation = await Conversation.get(id=conversation_id)
        current = (conversation.title or "").strip() if conversation.title is not None else ""
        if current:
            return
        normalized = (title or "").strip()
        if not normalized:
            return
        await conversation.update_from_dict({"title": normalized}).save()
