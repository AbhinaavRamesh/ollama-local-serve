"""
Smart model router for Ollama Local Serve.

Routes requests to the best-fit model based on task type keywords,
model availability, and configurable routing strategies.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import httpx

from ollama_local_serve.router.config import RouterConfig, RoutingRule

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """Result of a routing decision."""

    model: str
    task_type: str | None = None
    reason: str = "default"
    fallback_used: bool = False
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class RoutingRecord:
    """Record of a routing decision for stats."""

    timestamp: float
    model: str
    task_type: str | None
    reason: str
    fallback_used: bool


class ModelRouter:
    """
    Intelligent model router that selects the best model for each request.

    Supports:
    - Keyword-based task type detection
    - Priority-ordered model selection
    - Round-robin load distribution
    - Automatic fallback when models are unavailable
    """

    def __init__(self, config: RouterConfig, ollama_host: str = "http://localhost:11434"):
        self._config = config
        self._ollama_host = ollama_host
        self._lock = Lock()
        self._records: deque[RoutingRecord] = deque(maxlen=500)
        self._round_robin_counters: dict[str, int] = {}

    @property
    def config(self) -> RouterConfig:
        return self._config

    @config.setter
    def config(self, new_config: RouterConfig) -> None:
        with self._lock:
            self._config = new_config
            self._round_robin_counters.clear()

    async def route(self, prompt: str, explicit_model: str | None = None) -> RouteDecision:
        """
        Select the best model for a request.

        Args:
            prompt: The user's prompt text (used for keyword matching).
            explicit_model: If set and not "auto", passthrough to this model.

        Returns:
            RouteDecision with the selected model and routing metadata.
        """
        # Passthrough if explicit model specified (and not "auto")
        if explicit_model and explicit_model.lower() != "auto":
            decision = RouteDecision(model=explicit_model, reason="explicit")
            self._record_decision(decision)
            return decision

        # Detect task type from prompt keywords
        matched_rule, matched_keywords = self._match_task_type(prompt)

        if matched_rule:
            # Try models in priority order
            available = await self._get_available_models()
            selected = self._select_from_rule(matched_rule, available)

            if selected:
                decision = RouteDecision(
                    model=selected,
                    task_type=matched_rule.task_type,
                    reason=f"matched_{matched_rule.task_type}",
                    matched_keywords=matched_keywords,
                )
                self._record_decision(decision)
                return decision

        # No rule matched or no models available — use default
        decision = await self._fallback_decision()
        self._record_decision(decision)
        return decision

    def _match_task_type(self, prompt: str) -> tuple[RoutingRule | None, list[str]]:
        """Match prompt against routing rules by keywords."""
        prompt_lower = prompt.lower()
        best_match: RoutingRule | None = None
        best_keywords: list[str] = []
        best_count = 0

        for rule in self._config.rules:
            matched = [kw for kw in rule.keywords if kw.lower() in prompt_lower]
            if len(matched) > best_count:
                best_count = len(matched)
                best_match = rule
                best_keywords = matched

        return best_match, best_keywords

    def _select_from_rule(
        self, rule: RoutingRule, available_models: set[str]
    ) -> str | None:
        """Select a model from a routing rule based on strategy."""
        candidates = [m for m in rule.models if m in available_models]

        if not candidates:
            return None

        if self._config.strategy == "round-robin":
            with self._lock:
                counter = self._round_robin_counters.get(rule.task_type, 0)
                selected = candidates[counter % len(candidates)]
                self._round_robin_counters[rule.task_type] = counter + 1
            return selected

        # Default: priority (first available)
        return candidates[0]

    async def _fallback_decision(self) -> RouteDecision:
        """Create a fallback routing decision."""
        available = await self._get_available_models()

        # Try default model
        if self._config.default_model in available:
            return RouteDecision(
                model=self._config.default_model,
                reason="default_model",
            )

        # Try fallback model
        if self._config.fallback_model and self._config.fallback_model in available:
            return RouteDecision(
                model=self._config.fallback_model,
                reason="fallback_model",
                fallback_used=True,
            )

        # Last resort: use default even if not confirmed available
        return RouteDecision(
            model=self._config.default_model,
            reason="default_unverified",
        )

    async def _get_available_models(self) -> set[str]:
        """Query Ollama for currently available models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._ollama_host}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = {m["name"] for m in data.get("models", [])}
                # Also add base names without tags (e.g., "llama3.2" matches "llama3.2:latest")
                base_names = set()
                for name in models:
                    base = name.split(":")[0]
                    base_names.add(base)
                return models | base_names
        except Exception as e:
            logger.warning(f"Failed to get available models: {e}")
            return set()

    def _record_decision(self, decision: RouteDecision) -> None:
        """Record a routing decision for statistics."""
        with self._lock:
            self._records.append(
                RoutingRecord(
                    timestamp=time.time(),
                    model=decision.model,
                    task_type=decision.task_type,
                    reason=decision.reason,
                    fallback_used=decision.fallback_used,
                )
            )

    def get_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        with self._lock:
            records = list(self._records)

        if not records:
            return {
                "total_decisions": 0,
                "by_model": {},
                "by_task_type": {},
                "by_reason": {},
                "fallback_rate": 0,
            }

        total = len(records)
        fallback_count = sum(1 for r in records if r.fallback_used)

        # By model
        by_model: dict[str, int] = {}
        for r in records:
            by_model[r.model] = by_model.get(r.model, 0) + 1

        # By task type
        by_task_type: dict[str, int] = {}
        for r in records:
            key = r.task_type or "unmatched"
            by_task_type[key] = by_task_type.get(key, 0) + 1

        # By reason
        by_reason: dict[str, int] = {}
        for r in records:
            by_reason[r.reason] = by_reason.get(r.reason, 0) + 1

        return {
            "total_decisions": total,
            "by_model": by_model,
            "by_task_type": by_task_type,
            "by_reason": by_reason,
            "fallback_rate": round(fallback_count / total * 100, 1) if total > 0 else 0,
        }
