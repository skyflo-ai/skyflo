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




@router.get(
    "/analytics/metrics",
    dependencies=[rate_limit_dependency],
    response_model=MetricsAggregation,
)
async def get_metrics(
    last_n_days: int = Query(default=30, ge=1, le=365),
    user=Depends(fastapi_users.current_user(optional=True)),
) -> MetricsAggregation:
    try:
        if not user:
            # If no user, return empty metrics or raise error depending on policy.
            # Assuming we return empty for unauthenticated to avoid error, or 403.
            # If the user is optional in dependency but required for metrics:
            raise HTTPException(status_code=401, detail="Authentication required for metrics")

        end_date = date.today()
        start_date = end_date - timedelta(days=last_n_days)
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.now()

        # Fetch conversations
        conversations = await Conversation.filter(
            user=user, created_at__gte=period_start
        ).all()

        # Aggregation structures
        daily_map: Dict[date, Dict[str, Any]] = defaultdict(
            lambda: {
                "cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cached_tokens": 0,
                "total_tokens": 0,
                "ttft_ms_sum": 0,
                "ttft_count": 0,
                "ttr_ms_sum": 0,
                "ttr_count": 0,
                "conversation_count": 0,
            }
        )

        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cached_tokens = 0
        total_tokens = 0
        
        # Latency accumulators for the period average
        period_ttft_sum = 0
        period_ttft_count = 0
        period_ttr_sum = 0
        period_ttr_count = 0

        for conv in conversations:
            conv_date = conv.created_at.date()
            if conv_date < start_date:
                continue

            daily = daily_map[conv_date]
            daily["conversation_count"] += 1

            messages = conv.messages_json or []
            for msg in messages:
                if msg.get("type") == "assistant" and "token_usage" in msg:
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
        # Ensure we return entries for all days in range, or just days with data?
        # Usually checking all days is better for charts, but for simplicity let's do days with data 
        # or fill zeroes. Let's start with sparse to match data found.
        
        sorted_dates = sorted(daily_map.keys())
        for d in sorted_dates:
            stats = daily_map[d]
            avg_ttft = stats["ttft_ms_sum"] / stats["ttft_count"] if stats["ttft_count"] > 0 else None
            avg_ttr = stats["ttr_ms_sum"] / stats["ttr_count"] if stats["ttr_count"] > 0 else None
            
            daily_breakdown.append(
                DailyMetrics(
                    date=d,
                    cost=stats["cost"],
                    prompt_tokens=stats["prompt_tokens"],
                    completion_tokens=stats["completion_tokens"],
                    cached_tokens=stats["cached_tokens"],
                    total_tokens=stats["total_tokens"],
                    avg_ttft_ms=avg_ttft,
                    avg_ttr_ms=avg_ttr,
                    conversation_count=stats["conversation_count"],
                )
            )

        # Period Averages
        avg_ttft_ms = period_ttft_sum / period_ttft_count if period_ttft_count > 0 else None
        avg_ttr_ms = period_ttr_sum / period_ttr_count if period_ttr_count > 0 else None
        
        total_conversations = len(conversations)
        avg_cost_per_conversation = total_cost / total_conversations if total_conversations > 0 else 0.0
        avg_tokens_per_conversation = total_tokens / total_conversations if total_conversations > 0 else 0.0
        
        cache_hit_rate = (total_cached_tokens / total_prompt_tokens) if total_prompt_tokens > 0 else 0.0
        
        return MetricsAggregation(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_cached_tokens=total_cached_tokens,
            total_conversations=total_conversations,
            avg_ttft_ms=avg_ttft_ms,
            avg_ttr_ms=avg_ttr_ms,
            avg_cost_per_conversation=avg_cost_per_conversation,
            avg_tokens_per_conversation=avg_tokens_per_conversation,
            cache_hit_rate=cache_hit_rate,
            daily_breakdown=daily_breakdown,
            cost_change_pct=None, # Placeholder
            tokens_change_pct=None, # Placeholder
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting metrics: {str(e)}",
        )
