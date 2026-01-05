"""
LLM Monitoring and Metrics
==========================

Tracks performance metrics for your LLM deployment.

LEARNING NOTES:

Why monitor LLMs?
    1. Cost tracking - Know how much you're spending
    2. Latency - Detect slowdowns before users complain
    3. Quality - Track error rates and failures
    4. Capacity - Know when to scale

Key metrics:
    - Tokens/second (throughput)
    - Time to First Token (TTFT) - critical for UX
    - Total latency (end-to-end)
    - Error rate
    - Cost per request

Usage:
    from app.llm.monitoring import LLMMetrics, track_request
    
    metrics = LLMMetrics()
    
    with metrics.track_request():
        response = await llm.generate(prompt)
    
    # Get stats
    print(metrics.get_summary())
"""

import time
import asyncio
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import threading
import json
import os


@dataclass
class RequestMetric:
    """Metrics for a single request."""
    start_time: float
    end_time: Optional[float] = None
    first_token_time: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    success: bool = True
    error: Optional[str] = None
    
    @property
    def total_latency_ms(self) -> float:
        """Total request latency in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0
    
    @property
    def ttft_ms(self) -> float:
        """Time to first token in milliseconds."""
        if self.first_token_time:
            return (self.first_token_time - self.start_time) * 1000
        return 0
    
    @property
    def tokens_per_second(self) -> float:
        """Generation speed in tokens/second."""
        if self.end_time and self.completion_tokens > 0:
            duration = self.end_time - self.start_time
            return self.completion_tokens / duration if duration > 0 else 0
        return 0


@dataclass
class MetricsSummary:
    """Summary of metrics over a time window."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    avg_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    
    avg_ttft_ms: float = 0
    p95_ttft_ms: float = 0
    
    avg_tokens_per_second: float = 0
    
    error_rate: float = 0
    
    # Cost estimate (if using OpenAI-like pricing)
    estimated_cost_usd: float = 0


class LLMMetrics:
    """
    Collects and reports LLM performance metrics.
    
    Thread-safe for use in async applications.
    """
    
    # Cost per 1M tokens (OpenAI gpt-4o-mini pricing)
    DEFAULT_PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "local": {"input": 0.0, "output": 0.0},  # Self-hosted = free
    }
    
    def __init__(
        self,
        window_size: int = 1000,
        export_path: Optional[str] = None,
    ):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of requests to keep in memory
            export_path: Optional path to export metrics periodically
        """
        self._metrics: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._export_path = export_path
        self._current_metric: Optional[RequestMetric] = None
        
        # Pricing (override for your setup)
        self._pricing = self.DEFAULT_PRICING.copy()
    
    def set_pricing(self, model: str, input_cost: float, output_cost: float):
        """Set custom pricing per 1M tokens."""
        self._pricing[model] = {"input": input_cost, "output": output_cost}
    
    @contextmanager
    def track_request(self, model: str = "unknown"):
        """
        Context manager to track a request.
        
        Usage:
            with metrics.track_request("gpt-4o-mini") as tracker:
                response = llm.generate(prompt)
                tracker.set_tokens(prompt_tokens=100, completion_tokens=50)
        """
        metric = RequestMetric(start_time=time.time(), model=model)
        tracker = _RequestTracker(metric)
        
        try:
            yield tracker
            metric.success = True
        except Exception as e:
            metric.success = False
            metric.error = str(e)
            raise
        finally:
            metric.end_time = time.time()
            with self._lock:
                self._metrics.append(metric)
    
    @asynccontextmanager
    async def track_request_async(self, model: str = "unknown"):
        """Async version of track_request."""
        metric = RequestMetric(start_time=time.time(), model=model)
        tracker = _RequestTracker(metric)
        
        try:
            yield tracker
            metric.success = True
        except Exception as e:
            metric.success = False
            metric.error = str(e)
            raise
        finally:
            metric.end_time = time.time()
            with self._lock:
                self._metrics.append(metric)
    
    def record_metric(self, metric: RequestMetric):
        """Manually record a metric."""
        with self._lock:
            self._metrics.append(metric)
    
    def get_summary(
        self,
        last_n: Optional[int] = None,
        last_minutes: Optional[int] = None,
    ) -> MetricsSummary:
        """
        Get summary of recent metrics.
        
        Args:
            last_n: Only consider last N requests
            last_minutes: Only consider requests from last N minutes
        """
        with self._lock:
            metrics = list(self._metrics)
        
        # Filter by time if specified
        if last_minutes:
            cutoff = time.time() - (last_minutes * 60)
            metrics = [m for m in metrics if m.start_time >= cutoff]
        
        # Limit count if specified
        if last_n:
            metrics = metrics[-last_n:]
        
        if not metrics:
            return MetricsSummary()
        
        # Calculate statistics
        latencies = [m.total_latency_ms for m in metrics if m.end_time]
        ttfts = [m.ttft_ms for m in metrics if m.first_token_time]
        tps = [m.tokens_per_second for m in metrics if m.tokens_per_second > 0]
        
        latencies.sort()
        ttfts.sort()
        
        def percentile(values: List[float], p: float) -> float:
            if not values:
                return 0
            k = (len(values) - 1) * p
            f = int(k)
            c = min(f + 1, len(values) - 1)
            return values[f] + (k - f) * (values[c] - values[f])
        
        # Calculate cost
        total_cost = 0
        for m in metrics:
            pricing = self._pricing.get(m.model, self._pricing.get("local", {}))
            input_cost = (m.prompt_tokens / 1_000_000) * pricing.get("input", 0)
            output_cost = (m.completion_tokens / 1_000_000) * pricing.get("output", 0)
            total_cost += input_cost + output_cost
        
        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        
        return MetricsSummary(
            total_requests=len(metrics),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_prompt_tokens=sum(m.prompt_tokens for m in metrics),
            total_completion_tokens=sum(m.completion_tokens for m in metrics),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            p50_latency_ms=percentile(latencies, 0.50),
            p95_latency_ms=percentile(latencies, 0.95),
            p99_latency_ms=percentile(latencies, 0.99),
            avg_ttft_ms=sum(ttfts) / len(ttfts) if ttfts else 0,
            p95_ttft_ms=percentile(ttfts, 0.95),
            avg_tokens_per_second=sum(tps) / len(tps) if tps else 0,
            error_rate=len(failed) / len(metrics) if metrics else 0,
            estimated_cost_usd=total_cost,
        )
    
    def get_model_breakdown(self) -> Dict[str, MetricsSummary]:
        """Get metrics broken down by model."""
        with self._lock:
            metrics = list(self._metrics)
        
        models = set(m.model for m in metrics)
        
        breakdown = {}
        for model in models:
            model_metrics = [m for m in metrics if m.model == model]
            # Create a temporary LLMMetrics to calculate summary
            temp = LLMMetrics()
            temp._metrics = deque(model_metrics)
            breakdown[model] = temp.get_summary()
        
        return breakdown
    
    def export_metrics(self, path: Optional[str] = None):
        """Export metrics to JSON file."""
        path = path or self._export_path
        if not path:
            return
        
        with self._lock:
            metrics = list(self._metrics)
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "summary": self.get_summary().__dict__,
            "by_model": {k: v.__dict__ for k, v in self.get_model_breakdown().items()},
            "requests": [
                {
                    "start_time": m.start_time,
                    "latency_ms": m.total_latency_ms,
                    "ttft_ms": m.ttft_ms,
                    "prompt_tokens": m.prompt_tokens,
                    "completion_tokens": m.completion_tokens,
                    "model": m.model,
                    "success": m.success,
                    "error": m.error,
                }
                for m in metrics
            ]
        }
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def print_summary(self, last_minutes: int = 5):
        """Print a human-readable summary."""
        summary = self.get_summary(last_minutes=last_minutes)
        
        print(f"\n{'='*50}")
        print(f"LLM Metrics Summary (last {last_minutes} minutes)")
        print(f"{'='*50}")
        print(f"Requests: {summary.total_requests} ({summary.successful_requests} ok, {summary.failed_requests} failed)")
        print(f"Error Rate: {summary.error_rate*100:.1f}%")
        print(f"\nLatency:")
        print(f"  Average: {summary.avg_latency_ms:.0f}ms")
        print(f"  P50: {summary.p50_latency_ms:.0f}ms")
        print(f"  P95: {summary.p95_latency_ms:.0f}ms")
        print(f"  P99: {summary.p99_latency_ms:.0f}ms")
        print(f"\nTime to First Token:")
        print(f"  Average: {summary.avg_ttft_ms:.0f}ms")
        print(f"  P95: {summary.p95_ttft_ms:.0f}ms")
        print(f"\nThroughput:")
        print(f"  Average: {summary.avg_tokens_per_second:.1f} tokens/sec")
        print(f"\nTokens:")
        print(f"  Prompt: {summary.total_prompt_tokens:,}")
        print(f"  Completion: {summary.total_completion_tokens:,}")
        print(f"\nEstimated Cost: ${summary.estimated_cost_usd:.4f}")
        print(f"{'='*50}\n")


class _RequestTracker:
    """Helper class for tracking a single request."""
    
    def __init__(self, metric: RequestMetric):
        self._metric = metric
    
    def record_first_token(self):
        """Record when first token was received."""
        if not self._metric.first_token_time:
            self._metric.first_token_time = time.time()
    
    def set_tokens(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        """Set token counts."""
        self._metric.prompt_tokens = prompt_tokens
        self._metric.completion_tokens = completion_tokens
    
    def set_model(self, model: str):
        """Set model name."""
        self._metric.model = model


# Global metrics instance
_global_metrics: Optional[LLMMetrics] = None


def get_metrics() -> LLMMetrics:
    """Get the global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = LLMMetrics()
    return _global_metrics


# Convenience decorator
def track_llm_call(model: str = "unknown"):
    """
    Decorator to track LLM calls.
    
    Usage:
        @track_llm_call("gpt-4o-mini")
        async def my_llm_call():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with get_metrics().track_request_async(model):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

