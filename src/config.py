"""
Centralized configuration module for Metaculus AI Forecasting Bot.

Provides a single source of truth for mode resolution, model selection,
and submission behavior. Replaces the duplicated apply_mode_to_config()
logic that was previously split across main.py, run_bot.py, and forecaster.py.

Modes:
    - "test": Cheap models (Haiku), no submission - for testing pipeline
    - "preview": Production models, no submission - for evaluating quality
    - "live": Production models, submits to Metaculus

Usage:
    config = ResolvedConfig.from_yaml("config.yaml", mode="live")
    print(config.should_submit)  # True
    print(config.active_models)  # Production model dict
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

RunMode = Literal["test", "preview", "live"]


@dataclass
class ResolvedConfig:
    """
    Configuration with resolved mode settings.

    This dataclass provides a clean interface for accessing configuration
    values after mode resolution. It resolves:
    - Which model tier to use (cheap vs production)
    - Which ensemble agents to use
    - Whether to submit predictions

    Access Patterns:
        Use ATTRIBUTE access for resolved values:
            config.mode          # "test", "preview", or "live"
            config.active_models # Models for utility tasks
            config.active_agents # Ensemble agent configurations
            config.should_submit # Whether to submit to Metaculus

        Use DICT-LIKE access for raw config values:
            config.get("research")      # Research settings
            config["submission"]        # Submission settings
            "research" in config        # Check if key exists

    Attributes:
        raw: The complete raw configuration dictionary
        mode: The resolved run mode ("test", "preview", or "live")
        active_models: Dictionary of models for utility tasks (query generation, etc.)
        active_agents: List of agent configurations for the ensemble
        should_submit: Whether to submit predictions to Metaculus
    """

    raw: dict[str, Any]
    mode: RunMode
    active_models: dict[str, Any]
    active_agents: list[dict[str, Any]]
    should_submit: bool

    @classmethod
    def from_yaml(
        cls,
        path: str | Path = "config.yaml",
        mode: RunMode | None = None,
        dry_run: bool = False,
    ) -> "ResolvedConfig":
        """
        Load configuration from YAML file and resolve mode settings.

        Args:
            path: Path to the YAML configuration file
            mode: Explicit mode override ("test", "preview", "live")
            dry_run: Shortcut for mode="test" (mode= takes precedence)

        Returns:
            ResolvedConfig with resolved mode settings

        Mode resolution priority:
            1. Explicit `mode` argument
            2. `dry_run=True` argument (equivalent to mode="test")
            3. `mode` key in config file
            4. Default to "test"
        """
        with open(path) as f:
            raw = yaml.safe_load(f)

        return cls.from_dict(raw, mode=mode, dry_run=dry_run)

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        mode: RunMode | None = None,
        dry_run: bool = False,
    ) -> "ResolvedConfig":
        """
        Create ResolvedConfig from a configuration dictionary.

        Args:
            raw: Configuration dictionary (typically loaded from YAML)
            mode: Explicit mode override
            dry_run: Shortcut for mode="test"

        Returns:
            ResolvedConfig with resolved mode settings
        """
        # Determine mode (priority: mode arg > dry_run flag > config > default)
        if mode:
            resolved_mode = mode
        elif dry_run:
            resolved_mode = "test"
        else:
            resolved_mode = raw.get("mode", "test")

        # Validate mode
        valid_modes = ("test", "preview", "live")
        if resolved_mode not in valid_modes:
            raise ValueError(f"Invalid mode '{resolved_mode}'. Must be one of: {valid_modes}")

        # Select model tier based on mode
        model_tier = "cheap" if resolved_mode == "test" else "production"

        # Resolve active models
        if "models" in raw and model_tier in raw["models"]:
            active_models = raw["models"][model_tier]
        else:
            # Fallback for old config format (flat models dict)
            active_models = raw.get("models", {})

        # Resolve active agents
        if "ensemble" in raw and model_tier in raw["ensemble"]:
            active_agents = raw["ensemble"][model_tier]
        else:
            # Fallback for old config format (agents list under ensemble)
            active_agents = raw.get("ensemble", {}).get("agents", [])

        # Ensure active_agents is a list (limit to 5 agents)
        if not isinstance(active_agents, list):
            active_agents = []
        active_agents = active_agents[:5]

        # Submission only in live mode
        should_submit = resolved_mode == "live"

        return cls(
            raw=raw,
            mode=resolved_mode,
            active_models=active_models,
            active_agents=active_agents,
            should_submit=should_submit,
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization and backward compatibility.

        The returned dict includes:
        - All raw config values (models, ensemble, research, etc.)
        - "mode" is set to the resolved mode (CLI override > config file)
        - Resolved values for handlers: active_models, active_agents, should_submit

        Returns:
            Dictionary ready for serialization with unambiguous mode
        """
        result = self.raw.copy()
        # Set mode to resolved value
        result["mode"] = self.mode
        # Resolved values for handlers
        result["active_models"] = self.active_models
        result["active_agents"] = self.active_agents
        result["should_submit"] = self.should_submit
        return result

    def get(self, key: str, default=None):
        """
        Get a value from the raw config.

        This allows ResolvedConfig to be used somewhat like a dict
        for accessing non-resolved config values (e.g., research settings).
        """
        return self.raw.get(key, default)

    def __getitem__(self, key: str):
        """Allow dict-like access to raw config values."""
        return self.raw[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for raw config keys."""
        return key in self.raw


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file.

    This is a simple loader that returns the raw dict.
    For resolved configuration, use ResolvedConfig.from_yaml() instead.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Raw configuration dictionary
    """
    with open(config_path) as f:
        return yaml.safe_load(f)
