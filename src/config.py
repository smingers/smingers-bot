"""
Centralized configuration module for Metaculus AI Forecasting Bot.

Provides a single source of truth for mode resolution, model selection,
and submission behavior. Replaces the duplicated apply_mode_to_config()
logic that was previously split across main.py, run_bot.py, and forecaster.py.

Usage:
    config = ResolvedConfig.from_yaml("config.yaml", mode="production")
    print(config.should_submit)  # True
    print(config.active_models)  # Production model dict
"""

from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path
import yaml


Mode = Literal["dry_run", "dry_run_heavy", "production"]


@dataclass
class ResolvedConfig:
    """
    Configuration with resolved mode settings.

    This dataclass provides a clean interface for accessing configuration
    values after mode resolution. It resolves:
    - Which model tier to use (cheap vs production)
    - Which ensemble agents to use
    - Whether to submit predictions

    Attributes:
        raw: The complete raw configuration dictionary
        mode: The resolved run mode
        active_models: Dictionary of models for utility tasks (query generation, etc.)
        active_agents: List of agent configurations for the ensemble
        should_submit: Whether to submit predictions to Metaculus
    """

    raw: dict
    mode: Mode
    active_models: dict
    active_agents: list[dict]
    should_submit: bool

    @classmethod
    def from_yaml(
        cls,
        path: str | Path = "config.yaml",
        mode: Mode | None = None,
        dry_run: bool = False,
    ) -> "ResolvedConfig":
        """
        Load configuration from YAML file and resolve mode settings.

        Args:
            path: Path to the YAML configuration file
            mode: Explicit mode override ("dry_run", "dry_run_heavy", "production")
            dry_run: Shortcut for mode="dry_run" (mode= takes precedence)

        Returns:
            ResolvedConfig with resolved mode settings

        Mode resolution priority:
            1. Explicit `mode` argument
            2. `dry_run=True` argument (equivalent to mode="dry_run")
            3. `mode` key in config file
            4. Default to "dry_run"
        """
        with open(path) as f:
            raw = yaml.safe_load(f)

        return cls.from_dict(raw, mode=mode, dry_run=dry_run)

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        mode: Mode | None = None,
        dry_run: bool = False,
    ) -> "ResolvedConfig":
        """
        Create ResolvedConfig from a configuration dictionary.

        Args:
            raw: Configuration dictionary (typically loaded from YAML)
            mode: Explicit mode override
            dry_run: Shortcut for mode="dry_run"

        Returns:
            ResolvedConfig with resolved mode settings
        """
        # Determine effective mode (priority: mode arg > dry_run flag > config > default)
        if mode:
            effective_mode = mode
        elif dry_run:
            effective_mode = "dry_run"
        else:
            effective_mode = raw.get("mode", "dry_run")

        # Validate mode
        valid_modes = ("dry_run", "dry_run_heavy", "production")
        if effective_mode not in valid_modes:
            raise ValueError(f"Invalid mode '{effective_mode}'. Must be one of: {valid_modes}")

        # Select model tier based on mode
        model_tier = "cheap" if effective_mode == "dry_run" else "production"

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

        # Submission only in production mode
        should_submit = effective_mode == "production"

        return cls(
            raw=raw,
            mode=effective_mode,
            active_models=active_models,
            active_agents=active_agents,
            should_submit=should_submit,
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary with _active_* keys for backward compatibility.

        This preserves compatibility with handlers that expect:
        - config["_active_models"]
        - config["_active_agents"]
        - config["_should_submit"]
        - config["_effective_mode"]

        Returns:
            Dictionary combining raw config with resolved _active_* keys
        """
        result = self.raw.copy()
        result["_active_models"] = self.active_models
        result["_active_agents"] = self.active_agents
        result["_should_submit"] = self.should_submit
        result["_effective_mode"] = self.mode
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
