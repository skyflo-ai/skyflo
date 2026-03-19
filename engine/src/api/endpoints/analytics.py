import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import rate_limit_dependency
from ..models.conversation import DailyMetrics, Message, MetricsAggregation
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default
            return int(float(stripped))
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default
            return float(stripped)
        return float(value)
    except (TypeError, ValueError):
        return default


def _find_assistant_message_in_conversation_json(
    message: Message,
) -> Optional[Dict[str, Any]]:
    conversation = getattr(message, "conversation", None)
    if not conversation:
        return None

    conversation_messages = conversation.messages_json or []
    if not isinstance(conversation_messages, list):
        return None

    message_id = str(message.id)
    message_ts = int(message.created_at.timestamp() * 1000)

    for conversation_message in reversed(conversation_messages):
        if conversation_message.get("type") != "assistant":
            continue
        if str(conversation_message.get("id", "")) == message_id:
            return conversation_message

    for conversation_message in reversed(conversation_messages):
        if conversation_message.get("type") != "assistant":
            continue
        timestamp = conversation_message.get("timestamp")
        if isinstance(timestamp, int) and abs(timestamp - message_ts) <= 2000:
            return conversation_message

    return None


def _get_fallback_data(message: Message) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    assistant_msg = _find_assistant_message_in_conversation_json(message)
    if not assistant_msg:
        return {}, {}

    usage = assistant_msg.get("token_usage")
    token_usage = usage if isinstance(usage, dict) else {}

    segments = assistant_msg.get("segments")
    metadata = {"segments": segments} if isinstance(segments, list) else {}

    return token_usage, metadata


def _get_ttr_from_thinking_segments(message_metadata: Dict[str, Any]) -> Optional[int]:
    if not message_metadata or not isinstance(message_metadata, dict):
        return None

    total_duration_ms = 0
    for segment in message_metadata.get("segments", []):
        if not isinstance(segment, dict) or segment.get("kind") != "thinking":
            continue
        duration = segment.get("durationMs")
        if isinstance(duration, int) and duration >= 0:
            total_duration_ms += duration

    return total_duration_ms if total_duration_ms > 0 else None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _select_bucket_size(period_start: datetime, period_end: datetime) -> timedelta:
    span = period_end - period_start
    if span <= timedelta(hours=2):
        return timedelta(minutes=5)
    if span <= timedelta(hours=12):
        return timedelta(minutes=15)
    if span <= timedelta(hours=48):
        return timedelta(hours=1)
    if span <= timedelta(days=14):
        return timedelta(hours=6)
    if span <= timedelta(days=90):
        return timedelta(days=1)
    return timedelta(days=7)


def _floor_datetime_to_bucket(dt: datetime, bucket_size: timedelta) -> datetime:
    dt_utc = _as_utc(dt)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    bucket_seconds = int(bucket_size.total_seconds())
    if bucket_seconds <= 0:
        return dt_utc

    seconds_from_epoch = int((dt_utc - epoch).total_seconds())
    floored_seconds = (seconds_from_epoch // bucket_seconds) * bucket_seconds
    return epoch + timedelta(seconds=floored_seconds)


@router.get(
    "/metrics",
    dependencies=[rate_limit_dependency],
    response_model=MetricsAggregation,
)
async def get_metrics(
    last_n_days: Optional[int] = Query(default=7, ge=1, le=365),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    start_datetime: Optional[datetime] = Query(default=None),
    end_datetime: Optional[datetime] = Query(default=None),
    user=Depends(fastapi_users.current_user(optional=True)),
) -> MetricsAggregation:
    try:
        using_datetime_window = bool(start_datetime or end_datetime)

        if not user:
            raise HTTPException(status_code=401, detail="Authentication required for metrics")

        if start_datetime or end_datetime:
            now_utc = datetime.now(timezone.utc)
            default_days = last_n_days if last_n_days else 7
            s_dt = start_datetime or (now_utc - timedelta(days=default_days))
            e_dt = end_datetime or now_utc

            s_dt = _as_utc(s_dt)
            e_dt = _as_utc(e_dt)

            if s_dt > e_dt:
                raise HTTPException(
                    status_code=400,
                    detail="start_datetime must be before end_datetime",
                )

            period_start = s_dt
            period_end = e_dt
        elif start_date:
            s_date = start_date
            e_date = end_date if end_date else datetime.now(timezone.utc).date()

            if s_date > e_date:
                raise HTTPException(status_code=400, detail="start_date must be before end_date")

            period_start = datetime.combine(s_date, datetime.min.time(), tzinfo=timezone.utc)
            period_end = datetime.combine(e_date, datetime.max.time(), tzinfo=timezone.utc)
        else:
            days = last_n_days if last_n_days else 7
            now_utc = datetime.now(timezone.utc)
            e_date = now_utc.date()
            s_date = e_date - timedelta(days=max(days - 1, 0))
            period_start = datetime.combine(s_date, datetime.min.time(), tzinfo=timezone.utc)
            period_end = now_utc

        messages = (
            await Message.filter(
                conversation__user=user,
                created_at__gte=period_start,
                created_at__lte=period_end,
            )
            .only("id", "role", "created_at", "token_usage", "message_metadata", "conversation_id")
            .prefetch_related("conversation")
        )

        total_conversations = len({m.conversation_id for m in messages})

        bucket_map: Dict[datetime, Dict[str, Any]] = defaultdict(_empty_daily_stats)
        bucket_size = (
            _select_bucket_size(period_start, period_end)
            if using_datetime_window
            else timedelta(days=1)
        )

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
            if message.role != "assistant":
                continue

            msg_bucket = _floor_datetime_to_bucket(message.created_at, bucket_size)
            daily = bucket_map[msg_bucket]

            token_usage = message.token_usage
            message_metadata = message.message_metadata

            if not token_usage or not message_metadata:
                fallback_usage, fallback_metadata = _get_fallback_data(message)
                if not token_usage:
                    token_usage = fallback_usage
                if not message_metadata:
                    message_metadata = fallback_metadata

            if message_metadata and isinstance(message_metadata, dict):
                for segment in message_metadata.get("segments", []):
                    if not isinstance(segment, dict):
                        continue
                    if segment.get("kind") != "tool":
                        continue

                    tool_exec = segment.get("toolExecution")
                    if not tool_exec or not tool_exec.get("requires_approval"):
                        continue

                    status = tool_exec.get("status")
                    if status in {"completed", "error"}:
                        total_approvals += 1
                    elif status == "denied":
                        total_rejections += 1

            if token_usage:
                cost = _safe_float(token_usage.get("cost", 0.0))
                if not math.isfinite(cost) or cost < 0:
                    cost = 0.0
                total_cost += cost
                daily["cost"] += cost

                p_tok = max(_safe_int(token_usage.get("prompt_tokens", 0)), 0)
                c_tok = max(_safe_int(token_usage.get("completion_tokens", 0)), 0)
                msg_total = max(_safe_int(token_usage.get("total_tokens", 0)), 0)
                cached = max(_safe_int(token_usage.get("cached_tokens", 0)), 0)

                total_prompt_tokens += p_tok
                total_completion_tokens += c_tok
                total_tokens += msg_total
                total_cached_tokens += cached

                daily["prompt_tokens"] += p_tok
                daily["completion_tokens"] += c_tok
                daily["total_tokens"] += msg_total
                daily["cached_tokens"] += cached

                ttft = _safe_float(token_usage.get("ttft_ms"), default=-1.0)
                if not math.isfinite(ttft) or ttft < 0:
                    ttft = None
                if ttft is not None:
                    period_ttft_sum += ttft
                    period_ttft_count += 1
                    daily["ttft_ms_sum"] += ttft
                    daily["ttft_count"] += 1

            ttr: Optional[int] = None
            if token_usage:
                token_ttr = _safe_int(token_usage.get("ttr_ms"), default=-1)
                if token_ttr >= 0:
                    ttr = token_ttr
            if ttr is None:
                ttr = _get_ttr_from_thinking_segments(message_metadata)

            if ttr is not None:
                period_ttr_sum += ttr
                period_ttr_count += 1
                daily["ttr_ms_sum"] += ttr
                daily["ttr_count"] += 1

        daily_breakdown: List[DailyMetrics] = []

        def _append_daily_row(bucket_start: datetime, stats: Dict[str, Any]) -> None:
            avg_ttft = (
                stats["ttft_ms_sum"] / stats["ttft_count"] if stats["ttft_count"] > 0 else None
            )
            avg_ttr = stats["ttr_ms_sum"] / stats["ttr_count"] if stats["ttr_count"] > 0 else None

            daily_breakdown.append(
                DailyMetrics(
                    date=bucket_start,
                    cost=stats["cost"],
                    prompt_tokens=stats["prompt_tokens"],
                    completion_tokens=stats["completion_tokens"],
                    cached_tokens=stats["cached_tokens"],
                    total_tokens=stats["total_tokens"],
                    avg_ttft_ms=avg_ttft,
                    avg_ttr_ms=avg_ttr,
                )
            )

        if using_datetime_window:
            current_bucket = _floor_datetime_to_bucket(period_start, bucket_size)
            while current_bucket <= period_end:
                _append_daily_row(
                    current_bucket,
                    bucket_map.get(current_bucket, _empty_daily_stats()),
                )
                current_bucket += bucket_size
        else:
            current_date = period_start.date()
            while current_date <= period_end.date():
                current_bucket = datetime.combine(
                    current_date,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                )
                _append_daily_row(
                    current_bucket,
                    bucket_map.get(current_bucket, _empty_daily_stats()),
                )
                current_date += timedelta(days=1)

        avg_ttft_ms = period_ttft_sum / period_ttft_count if period_ttft_count > 0 else None
        avg_ttr_ms = period_ttr_sum / period_ttr_count if period_ttr_count > 0 else None

        avg_cost_per_conversation = (
            total_cost / total_conversations if total_conversations > 0 else 0.0
        )
        avg_tokens_per_conversation = (
            total_tokens / total_conversations if total_conversations > 0 else 0.0
        )

        cache_hit_rate = (
            min((total_cached_tokens / total_prompt_tokens), 1.0)
            if total_prompt_tokens > 0
            else 0.0
        )

        approval_acceptance_rate = (
            (total_approvals / (total_approvals + total_rejections))
            if (total_approvals + total_rejections) > 0
            else None
        )

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
        logger.exception("Error getting metrics: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics",
        ) from e
