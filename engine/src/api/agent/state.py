import time
import uuid
import operator
from typing import Any, Dict, List, Optional, Annotated
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: Annotated[List[Dict[str, Any]], operator.add] = Field(default_factory=list)
    pending_tools: List[Dict[str, Any]] = Field(default_factory=list)
    start_time: float = Field(default_factory=time.time)
    end_time: float = 0.0
    duration: float = 0.0
    done: bool = False
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    auto_continue_turns: int = 0
    awaiting_approval: bool = False
    suppress_pending_event: bool = False
    ttft_emitted: bool = False
    approval_decisions: Dict[str, bool] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
