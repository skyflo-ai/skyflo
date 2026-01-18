from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import date, timedelta, datetime
from collections import defaultdict
import logging

from ..models.conversation import Conversation, MetricsAggregation, DailyMetrics
from ..config import rate_limit_dependency
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
            # use custom range
            s_date = start_date
            # if end_date is provided, use it, otherwise valid until today
            e_date = end_date if end_date else date.today()
            
            # period_start is start_date at 00:00:00
            period_start = datetime.combine(s_date, datetime.min.time())
            
            # period_end is end_date at 23:59:59.999999
            period_end = datetime.combine(e_date, datetime.max.time())
            period_end_dt = period_end
        else:
            # use last_n_days
            days = last_n_days if last_n_days else 30
            e_date = date.today()
            s_date = e_date - timedelta(days=days)
            period_start = datetime.combine(s_date, datetime.min.time())
            # period_end is now (up to current moment)
            period_end = datetime.now()
            period_end_dt = period_end

        # Fetch conversations
        query = Conversation.filter(
            user=user, 
            updated_at__gte=period_start,
            updated_at__lte=period_end_dt
        )
        conversations = await query.all()


        # Aggregation structures
        daily_map: Dict[date, Dict[str, Any]] = defaultdict(_empty_daily_stats)

        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cached_tokens = 0
        total_tokens = 0

        total_approvals = 0
        total_rejections = 0
        
        # Latency accumulators for the period average
        period_ttft_sum = 0
        period_ttft_count = 0
        period_ttr_sum = 0
        period_ttr_count = 0

        for conv in conversations:
            messages = conv.messages_json or []
            for msg in messages:
                timestamp = msg.get("timestamp")
                if not timestamp:
                    continue
                msg_date = date.fromtimestamp(timestamp/1000)
                if msg_date > period_end_dt.date() or msg_date < period_start.date():
                    continue
                daily = daily_map[msg_date]
                if msg.get("type") == "assistant":
                    for segment in msg.get("segments", []):
                        if segment.get("kind") != "tool":
                            continue

                        tool_exec = segment.get("toolExecution")
                        if not tool_exec or not tool_exec.get("requires_approval"):
                            continue

                        status = tool_exec.get("status")
                        if status == "completed":
                            total_approvals += 1
                        elif status == "denied":
                            total_rejections += 1
                                
                            
                    if "token_usage" not in msg:
                        continue
                    usage = msg["token_usage"]
                    
                    # Cost
                    cost = float(usage.get("cost", 0.0))
                    total_cost += cost
                    daily["cost"] += cost

                    # Tokens
                    p_tok = int(usage.get("prompt_tokens", 0))
                    c_tok = int(usage.get("completion_tokens", 0))
                    msg_total = int(usage.get("total_tokens", 0))
                    cached = int(usage.get("cached_tokens", 0))

                    total_prompt_tokens += p_tok
                    total_completion_tokens += c_tok
                    total_tokens += msg_total
                    total_cached_tokens += cached

                    daily["prompt_tokens"] += p_tok
                    daily["completion_tokens"] += c_tok
                    daily["total_tokens"] += msg_total
                    daily["cached_tokens"] += cached

                    # Latency
                    ttft = usage.get("ttft_ms")
                    if ttft is not None:
                        period_ttft_sum += ttft
                        period_ttft_count += 1
                        daily["ttft_ms_sum"] += ttft
                        daily["ttft_count"] += 1
                    
                    ttr = usage.get("ttr_ms")
                    if ttr is not None:
                        period_ttr_sum += ttr
                        period_ttr_count += 1
                        daily["ttr_ms_sum"] += ttr
                        daily["ttr_count"] += 1

                
        # Build DailyMetrics list
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
        # Period Averages
        avg_ttft_ms = period_ttft_sum / period_ttft_count if period_ttft_count > 0 else None
        avg_ttr_ms = period_ttr_sum / period_ttr_count if period_ttr_count > 0 else None
        
        total_conversations = len(conversations)
        avg_cost_per_conversation = total_cost / total_conversations if total_conversations > 0 else 0.0
        avg_tokens_per_conversation = total_tokens / total_conversations if total_conversations > 0 else 0.0
        
        cache_hit_rate = min((total_cached_tokens / total_prompt_tokens), 1.0) if total_prompt_tokens > 0 else 0.0



        # Approval metrics
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
