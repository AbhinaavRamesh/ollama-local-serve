"""
Configuration for the smart model router.

Supports loading routing rules from a YAML config file or environment variables.
"""

import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class RoutingRule(BaseModel):
    """A single routing rule that maps task types to models."""

    task_type: str = Field(..., description="Task type identifier (code, chat, reasoning, creative)")
    models: list[str] = Field(..., description="Priority-ordered list of model names")
    keywords: list[str] = Field(default_factory=list, description="Keywords that trigger this rule")


class RouterConfig(BaseSettings):
    """
    Configuration for the smart model router.

    Can be loaded from environment variables or a YAML config file.
    """

    model_config = SettingsConfigDict(
        env_prefix="ROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=False, description="Enable smart routing")
    default_model: str = Field(default="llama3.2", description="Default model when no rule matches")
    fallback_model: str | None = Field(
        default=None, description="Fallback model when primary is unavailable"
    )
    strategy: Literal["priority", "round-robin"] = Field(
        default="priority", description="Routing strategy"
    )
    rules: list[RoutingRule] = Field(default_factory=list, description="Routing rules")
    config_path: str | None = Field(
        default=None,
        alias="ROUTER_CONFIG_PATH",
        description="Path to YAML config file",
    )

    def load_from_yaml(self) -> "RouterConfig":
        """Load routing rules from the YAML config file if specified."""
        config_path = self.config_path or os.getenv("ROUTER_CONFIG_PATH")
        if not config_path:
            return self

        try:
            import yaml

            with open(config_path) as f:
                data = yaml.safe_load(f)

            if not data:
                return self

            return RouterConfig(
                enabled=data.get("enabled", self.enabled),
                default_model=data.get("default_model", self.default_model),
                fallback_model=data.get("fallback_model", self.fallback_model),
                strategy=data.get("strategy", self.strategy),
                rules=[RoutingRule(**r) for r in data.get("rules", [])],
            )

        except ImportError:
            logger.warning("PyYAML not installed, cannot load router config from YAML")
            return self
        except FileNotFoundError:
            logger.warning(f"Router config file not found: {config_path}")
            return self
        except Exception as e:
            logger.error(f"Failed to load router config: {e}")
            return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dictionary."""
        return {
            "enabled": self.enabled,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "strategy": self.strategy,
            "rules": [
                {
                    "task_type": r.task_type,
                    "models": r.models,
                    "keywords": r.keywords,
                }
                for r in self.rules
            ],
        }
