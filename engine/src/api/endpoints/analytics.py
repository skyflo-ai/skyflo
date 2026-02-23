from collections import defaultdict
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from ..config import rate_limit_dependency
from ..models.conversation import MetricsAggregation, DailyMetrics, Message
from ..services.auth import fastapi_users

logger = logging.getLogger(__name__)

router = APIRouter()


def _empty_daily_stats() -> Dict[str, Any]:
    return {
        "cost": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "ttft_ms_sum": 0,
        "ttft_count": 0,
        "ttr_ms_sum": 0,
        "ttr_count": 0,
    }

@router.get(
    "/metrics",
    dependencies=[rate_limit_dependency],
    response_model=MetricsAggregation,
)
async def get_metrics(
    last_n_days: Optional[int] = Query(default=30, ge=1, le=365),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    user=Depends(fastapi_users.current_user(optional=True)),
) -> MetricsAggregation:
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required for metrics")

        period_end_dt = datetime.now()

        if start_date:
            s_date = start_date
            e_date = end_date if end_date else date.today()

            period_start = datetime.combine(s_date, datetime.min.time())
            period_end = datetime.combine(e_date, datetime.max.time())
            period_end_dt = period_end
        else:
            days = last_n_days if last_n_days else 30
            e_date = date.today()
            s_date = e_date - timedelta(days=days)
            period_start = datetime.combine(s_date, datetime.min.time())
            period_end = datetime.now()
            period_end_dt = period_end

        messages = await Message.filter(
            conversation__user=user,
            created_at__gte=period_start,
            created_at__lte=period_end_dt
        ).distinct().prefetch_related('conversation')

        conversation_ids = {msg.conversation_id for msg in messages}

        daily_map: Dict[date, Dict[str, Any]] = defaultdict(_empty_daily_stats)

        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cached_tokens = 0
        total_tokens = 0

        total_approvals = 0
        total_rejections = 0

        period_ttft_sum = 0
        period_ttft_count = 0
        period_ttr_sum = 0
        period_ttr_count = 0

        for message in messages:

            msg_date = message.created_at.date()
            if msg_date > period_end_dt.date() or msg_date < period_start.date():
                continue

            daily = daily_map[msg_date]

            if message.role == "assistant":

                message_metadata = message.message_metadata or {}
                token_usage = message.token_usage or {}

                if message_metadata:
                    for segments in message_metadata.get("segments", []):
                        if segments.get("kind") != "tool":
                            continue

                        tool_exec = segments.get("toolExecution")
                        if not tool_exec or not tool_exec.get("requires_approval"):
                            continue

                        status = tool_exec.get("status")
                        if status == "completed":
                            total_approvals += 1
                        elif status == "denied":
                            total_rejections += 1

                if token_usage:

                    cost = float(token_usage.get("cost", 0.0))
                    total_cost += cost
                    daily["cost"] += cost

                    p_tok = int(token_usage.get("prompt_tokens", 0))
                    c_tok = int(token_usage.get("completion_tokens", 0))
                    msg_total = int(token_usage.get("total_tokens", 0))
                    cached = int(token_usage.get("cached_tokens", 0))

                    total_prompt_tokens += p_tok
                    total_completion_tokens += c_tok
                    total_tokens += msg_total
                    total_cached_tokens += cached

                    daily["prompt_tokens"] += p_tok
                    daily["completion_tokens"] += c_tok
                    daily["total_tokens"] += msg_total
                    daily["cached_tokens"] += cached

                    ttft = token_usage.get("ttft_ms")
                    if ttft is not None:
                        period_ttft_sum += ttft
                        period_ttft_count += 1
                        daily["ttft_ms_sum"] += ttft
                        daily["ttft_count"] += 1

                    ttr = token_usage.get("ttr_ms")
                    if ttr is not None:
                        period_ttr_sum += ttr
                        period_ttr_count += 1
                        daily["ttr_ms_sum"] += ttr
                        daily["ttr_count"] += 1

        daily_breakdown: List[DailyMetrics] = []

        current_date = period_start.date()
        while current_date <= period_end_dt.date():
            stats = daily_map.get(current_date, _empty_daily_stats())
            avg_ttft = stats["ttft_ms_sum"] / stats["ttft_count"] if stats["ttft_count"] > 0 else None
            avg_ttr = stats["ttr_ms_sum"] / stats["ttr_count"] if stats["ttr_count"] > 0 else None

            daily_breakdown.append(
                DailyMetrics(
                    date=current_date,
                    cost=stats["cost"],
                    prompt_tokens=stats["prompt_tokens"],
                    completion_tokens=stats["completion_tokens"],
                    cached_tokens=stats["cached_tokens"],
                    total_tokens=stats["total_tokens"],
                    avg_ttft_ms=avg_ttft,
                    avg_ttr_ms=avg_ttr,
                )
            )
            current_date += timedelta(days=1)

        avg_ttft_ms = period_ttft_sum / period_ttft_count if period_ttft_count > 0 else None
        avg_ttr_ms = period_ttr_sum / period_ttr_count if period_ttr_count > 0 else None

        total_conversations = len(conversation_ids)
        avg_cost_per_conversation = total_cost / total_conversations if total_conversations > 0 else 0.0
        avg_tokens_per_conversation = total_tokens / total_conversations if total_conversations > 0 else 0.0

        cache_hit_rate = min((total_cached_tokens / total_prompt_tokens), 1.0) if total_prompt_tokens > 0 else 0.0

        approval_acceptance_rate = (total_approvals / (total_approvals + total_rejections)) if (total_approvals + total_rejections) > 0 else None

        return MetricsAggregation(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_cached_tokens=total_cached_tokens,
            total_conversations=total_conversations,
            total_approvals=total_approvals,
            total_rejections=total_rejections,
            avg_ttft_ms=avg_ttft_ms,
            avg_ttr_ms=avg_ttr_ms,
            avg_cost_per_conversation=avg_cost_per_conversation,
            avg_tokens_per_conversation=avg_tokens_per_conversation,
            cache_hit_rate=cache_hit_rate,
            approval_acceptance_rate=approval_acceptance_rate,
            daily_breakdown=daily_breakdown,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting metrics: {str(e)}",
        ) from e