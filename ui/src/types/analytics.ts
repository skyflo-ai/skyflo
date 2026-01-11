

export interface MetricsAggregation {
    period_start: string
    period_end: string
    // Totals
    total_cost: number
    total_tokens: number
    total_prompt_tokens: number
    total_completion_tokens: number
    total_cached_tokens: number
    total_conversations: number
    // Averages
    avg_ttft_ms: number | null
    avg_ttr_ms: number | null
    avg_cost_per_conversation: number
    avg_tokens_per_conversation: number
    // Derived
    cache_hit_rate: number  // cached_tokens / prompt_tokens
    // Time series
    daily_breakdown: DailyMetrics[]
    // Approval metrics
    total_approvals: number
    total_rejections: number
    approval_acceptance_rate: number | null
}


export interface DailyMetrics {
    date: string
    cost: number
    total_tokens: number
    prompt_tokens: number
    completion_tokens: number
    cached_tokens: number
    avg_ttft_ms?: number | null
    avg_ttr_ms?: number | null
}


