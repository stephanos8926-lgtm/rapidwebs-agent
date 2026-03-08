"""Token budget enforcement for cost control.

This module provides token budget tracking and enforcement to prevent
runaway token usage and control operating costs.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum
import threading
import json
from pathlib import Path


class ActionOnExceed(Enum):
    """Action to take when budget is exceeded."""
    WARN = "warn"
    BLOCK = "block"
    COMPRESS = "compress"
    QUEUE = "queue"


@dataclass
class TokenBudgetConfig:
    """Token budget enforcement configuration.
    
    Attributes:
        enabled: Enable budget enforcement
        daily_limit: Maximum tokens per day
        per_request_limit: Maximum tokens per single request
        warning_threshold: Threshold (0.0-1.0) for warning alerts
        action_on_exceed: Action to take when limit exceeded
        reset_hour: Hour of day to reset daily counter (0-23)
    """
    enabled: bool = True
    daily_limit: int = 100000
    per_request_limit: int = 8000
    warning_threshold: float = 0.8
    action_on_exceed: ActionOnExceed = ActionOnExceed.WARN
    reset_hour: int = 0  # Midnight UTC


@dataclass
class TokenUsageRecord:
    """Record of token usage.
    
    Attributes:
        timestamp: When the usage occurred
        tokens: Number of tokens used
        request_type: Type of request (prompt, completion, etc.)
        model: Model name
        description: Optional description
    """
    timestamp: datetime
    tokens: int
    request_type: str
    model: str
    description: str = ''


class TokenBudgetEnforcer:
    """Enforce token budgets with daily tracking and alerts.
    
    This class tracks token usage and enforces configurable budgets
    with support for warnings, blocking, and compression strategies.
    
    Example:
        >>> config = TokenBudgetConfig(
        ...     daily_limit=100000,
        ...     per_request_limit=8000,
        ...     warning_threshold=0.8
        ... )
        >>> enforcer = TokenBudgetEnforcer(config)
        >>> # Check before making request
        >>> if enforcer.check_budget(5000):
        ...     response = call_llm_api(prompt)
        ...     enforcer.record_usage(5000, "completion", "coder-model")
        >>> # Get usage report
        >>> report = enforcer.get_usage_report()
        >>> print(f"Used {report['daily_usage']}/{report['daily_limit']} tokens")
    """

    def __init__(self, config: TokenBudgetConfig = None):
        """Initialize token budget enforcer.
        
        Args:
            config: Budget configuration (uses defaults if None)
        """
        self.config = config or TokenBudgetConfig()
        self.daily_usage = 0
        self.last_reset = datetime.now().date()
        self.request_count = 0
        self.session_usage = 0
        self.usage_history: List[TokenUsageRecord] = []
        self._lock = threading.RLock()
        self._warnings_issued: Dict[str, datetime] = {}

    def _reset_if_new_day(self):
        """Reset daily counter if date changed or reset hour passed."""
        now = datetime.now()
        today = now.date()

        # Check if date changed
        if today != self.last_reset:
            self.daily_usage = 0
            self.request_count = 0
            self.session_usage = 0
            self.last_reset = today
            self._warnings_issued.clear()

        # Check if reset hour passed (for custom reset times)
        elif now.hour == self.config.reset_hour and now.minute == 0:
            self.daily_usage = 0
            self.request_count = 0
            self.session_usage = 0
            self._warnings_issued.clear()

    def check_budget(self, estimated_tokens: int) -> bool:
        """Check if request is within budget.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            True if request is allowed, False if blocked
        """
        if not self.config.enabled:
            return True

        with self._lock:
            self._reset_if_new_day()

            # Check per-request limit
            if estimated_tokens > self.config.per_request_limit:
                if self.config.action_on_exceed == ActionOnExceed.BLOCK:
                    return False
                elif self.config.action_on_exceed == ActionOnExceed.WARN:
                    self._issue_warning(
                        f"Request exceeds per-request limit "
                        f"({estimated_tokens} > {self.config.per_request_limit})"
                    )

            # Check daily limit
            if self.daily_usage + estimated_tokens > self.config.daily_limit:
                if self.config.action_on_exceed == ActionOnExceed.BLOCK:
                    return False
                elif self.config.action_on_exceed == ActionOnExceed.WARN:
                    self._check_daily_warning()

            return True

    def _check_daily_warning(self):
        """Issue daily limit warning if threshold reached."""
        usage_ratio = self.daily_usage / self.config.daily_limit
        
        if usage_ratio >= self.config.warning_threshold:
            self._issue_warning(
                f"Approaching daily token limit "
                f"({self.daily_usage}/{self.config.daily_limit} = {usage_ratio*100:.1f}%)"
            )

    def _issue_warning(self, message: str):
        """Issue warning with rate limiting."""
        now = datetime.now()
        
        # Rate limit warnings to once per minute
        if 'daily' in message.lower():
            last_warning = self._warnings_issued.get('daily')
            if last_warning and (now - last_warning).total_seconds() < 60:
                return
        
        self._warnings_issued['daily'] = now
        print(f"⚠️  TOKEN BUDGET WARNING: {message}")

    def record_usage(self, tokens: int, request_type: str = 'completion',
                     model: str = '', description: str = ''):
        """Record token usage.
        
        Args:
            tokens: Number of tokens used
            request_type: Type of request (prompt, completion, embedding, etc.)
            model: Model name
            description: Optional description
        """
        with self._lock:
            self._reset_if_new_day()
            
            self.daily_usage += tokens
            self.session_usage += tokens
            self.request_count += 1

            # Record in history
            record = TokenUsageRecord(
                timestamp=datetime.now(),
                tokens=tokens,
                request_type=request_type,
                model=model,
                description=description
            )
            self.usage_history.append(record)

            # Keep history bounded (last 1000 records)
            if len(self.usage_history) > 1000:
                self.usage_history = self.usage_history[-1000:]

    def get_usage_report(self) -> Dict[str, Any]:
        """Get current usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        with self._lock:
            self._reset_if_new_day()

            usage_ratio = (
                self.daily_usage / self.config.daily_limit * 100
                if self.config.daily_limit > 0 else 0
            )

            return {
                'daily_usage': self.daily_usage,
                'daily_limit': self.config.daily_limit,
                'usage_percentage': round(usage_ratio, 2),
                'remaining': max(0, self.config.daily_limit - self.daily_usage),
                'request_count': self.request_count,
                'session_usage': self.session_usage,
                'per_request_limit': self.config.per_request_limit,
                'warning_threshold': self.config.warning_threshold * 100,
                'is_enabled': self.config.enabled,
                'reset_hour': self.config.reset_hour
            }

    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed usage report with history.
        
        Returns:
            Dictionary with detailed usage statistics
        """
        with self._lock:
            self._reset_if_new_day()

            # Calculate hourly breakdown
            now = datetime.now()
            hourly_usage: Dict[int, int] = {}
            type_breakdown: Dict[str, int] = {}
            model_breakdown: Dict[str, int] = {}

            for record in self.usage_history:
                hour = record.timestamp.hour
                hourly_usage[hour] = hourly_usage.get(hour, 0) + record.tokens
                type_breakdown[record.request_type] = (
                    type_breakdown.get(record.request_type, 0) + record.tokens
                )
                model_breakdown[record.model] = (
                    model_breakdown.get(record.model, 0) + record.tokens
                )

            # Calculate averages
            avg_per_request = (
                self.session_usage / self.request_count
                if self.request_count > 0 else 0
            )

            return {
                **self.get_usage_report(),
                'hourly_breakdown': hourly_usage,
                'type_breakdown': type_breakdown,
                'model_breakdown': model_breakdown,
                'average_per_request': round(avg_per_request, 2),
                'history_size': len(self.usage_history),
                'last_reset': self.last_reset.isoformat()
            }

    def reset_daily(self):
        """Manually reset daily counter."""
        with self._lock:
            self.daily_usage = 0
            self.request_count = 0
            self._warnings_issued.clear()

    def reset_session(self):
        """Reset session counter only."""
        with self._lock:
            self.session_usage = 0

    def set_daily_limit(self, limit: int):
        """Update daily limit.
        
        Args:
            limit: New daily limit in tokens
        """
        with self._lock:
            self.config.daily_limit = limit

    def set_per_request_limit(self, limit: int):
        """Update per-request limit.
        
        Args:
            limit: New per-request limit in tokens
        """
        with self._lock:
            self.config.per_request_limit = limit

    def set_action_on_exceed(self, action: ActionOnExceed):
        """Update action when budget exceeded.
        
        Args:
            action: Action to take
        """
        with self._lock:
            self.config.action_on_exceed = action

    def enable(self):
        """Enable budget enforcement."""
        with self._lock:
            self.config.enabled = True

    def disable(self):
        """Disable budget enforcement."""
        with self._lock:
            self.config.enabled = False

    def save_state(self, output_path: Path):
        """Persist usage state to disk.
        
        Args:
            output_path: Path to save state file
        """
        with self._lock:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'version': 1,
                'timestamp': datetime.now().isoformat(),
                'daily_usage': self.daily_usage,
                'last_reset': self.last_reset.isoformat(),
                'request_count': self.request_count,
                'session_usage': self.session_usage,
                'config': {
                    'enabled': self.config.enabled,
                    'daily_limit': self.config.daily_limit,
                    'per_request_limit': self.config.per_request_limit,
                    'warning_threshold': self.config.warning_threshold,
                    'action_on_exceed': self.config.action_on_exceed.value,
                    'reset_hour': self.config.reset_hour
                },
                'recent_history': [
                    {
                        'timestamp': r.timestamp.isoformat(),
                        'tokens': r.tokens,
                        'request_type': r.request_type,
                        'model': r.model,
                        'description': r.description
                    }
                    for r in self.usage_history[-100:]
                ]
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

    def load_state(self, input_path: Path):
        """Load usage state from disk.
        
        Args:
            input_path: Path to state file
        """
        if not input_path.exists():
            return

        with self._lock:
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Restore counters
                self.daily_usage = data.get('daily_usage', 0)
                self.request_count = data.get('request_count', 0)
                self.session_usage = data.get('session_usage', 0)

                # Restore last reset date
                last_reset_str = data.get('last_reset')
                if last_reset_str:
                    self.last_reset = datetime.fromisoformat(last_reset_str).date()

                # Restore config
                config_data = data.get('config', {})
                self.config.enabled = config_data.get('enabled', True)
                self.config.daily_limit = config_data.get('daily_limit', 100000)
                self.config.per_request_limit = config_data.get('per_request_limit', 8000)
                self.config.warning_threshold = config_data.get('warning_threshold', 0.8)
                
                action_str = config_data.get('action_on_exceed', 'warn')
                try:
                    self.config.action_on_exceed = ActionOnExceed(action_str)
                except ValueError:
                    self.config.action_on_exceed = ActionOnExceed.WARN

                self.config.reset_hour = config_data.get('reset_hour', 0)

                # Restore recent history
                history_data = data.get('recent_history', [])
                self.usage_history = [
                    TokenUsageRecord(
                        timestamp=datetime.fromisoformat(r['timestamp']),
                        tokens=r['tokens'],
                        request_type=r['request_type'],
                        model=r['model'],
                        description=r.get('description', '')
                    )
                    for r in history_data
                ]

            except (json.JSONDecodeError, IOError, KeyError):
                # Corrupted state file - start fresh
                pass

    def get_projected_usage(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Project token usage based on current rate.
        
        Args:
            hours_ahead: Hours to project ahead
            
        Returns:
            Dictionary with projected usage
        """
        with self._lock:
            self._reset_if_new_day()

            now = datetime.now()
            current_hour = now.hour

            # Calculate usage rate for today so far
            hours_elapsed = max(1, current_hour - self.config.reset_hour)
            hourly_rate = self.daily_usage / hours_elapsed

            # Project remaining hours
            hours_remaining = 24 - hours_elapsed
            projected_additional = hourly_rate * hours_remaining
            projected_total = self.daily_usage + projected_additional

            return {
                'current_usage': self.daily_usage,
                'hours_elapsed': hours_elapsed,
                'hourly_rate': round(hourly_rate, 2),
                'hours_remaining': hours_remaining,
                'projected_additional': round(projected_additional, 2),
                'projected_total': round(projected_total, 2),
                'daily_limit': self.config.daily_limit,
                'will_exceed': projected_total > self.config.daily_limit,
                'excess_tokens': max(0, projected_total - self.config.daily_limit)
            }
