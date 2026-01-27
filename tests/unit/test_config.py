"""
Tests for configuration handling and mode resolution.

Tests the ResolvedConfig class in src/config.py and verifies
the contract between entry points and handlers.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import ResolvedConfig


class TestResolvedConfigFromDict:
    """Tests for ResolvedConfig.from_dict() method."""

    def test_dry_run_mode_uses_cheap_models(self, sample_config):
        """Test that dry_run mode selects cheap models."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        assert resolved.mode == "dry_run"
        assert resolved.active_models == sample_config["models"]["cheap"]
        assert resolved.active_agents == sample_config["ensemble"]["cheap"]
        assert resolved.should_submit is False

    def test_dry_run_heavy_uses_production_models(self, sample_config):
        """Test that dry_run_heavy mode selects production models but doesn't submit."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run_heavy")

        assert resolved.mode == "dry_run_heavy"
        assert resolved.active_models == sample_config["models"]["production"]
        assert resolved.active_agents == sample_config["ensemble"]["production"]
        assert resolved.should_submit is False

    def test_production_mode_submits(self, sample_config):
        """Test that production mode uses production models and enables submission."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="production")

        assert resolved.mode == "production"
        assert resolved.active_models == sample_config["models"]["production"]
        assert resolved.active_agents == sample_config["ensemble"]["production"]
        assert resolved.should_submit is True

    def test_dry_run_flag_overrides_config(self, sample_config):
        """Test that dry_run=True flag overrides config.mode."""
        sample_config["mode"] = "production"  # Set production in config
        resolved = ResolvedConfig.from_dict(sample_config, dry_run=True)

        assert resolved.mode == "dry_run"
        assert resolved.should_submit is False

    def test_explicit_mode_overrides_dry_run_flag(self, sample_config):
        """Test that explicit mode= parameter takes precedence over dry_run flag."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="production", dry_run=True)

        # mode= should win over dry_run=
        assert resolved.mode == "production"
        assert resolved.should_submit is True

    def test_defaults_to_config_mode(self, sample_config):
        """Test that config's mode is used when no arguments provided."""
        sample_config["mode"] = "dry_run_heavy"
        resolved = ResolvedConfig.from_dict(sample_config)

        assert resolved.mode == "dry_run_heavy"

    def test_defaults_to_dry_run_if_no_mode(self):
        """Test that dry_run is the default when no mode specified anywhere."""
        config = {
            "models": {"cheap": {"utility": "model-a"}, "production": {"utility": "model-b"}},
            "ensemble": {"cheap": [], "production": []},
        }
        resolved = ResolvedConfig.from_dict(config)

        assert resolved.mode == "dry_run"

    def test_fallback_for_missing_model_tier(self):
        """Test fallback when model tier doesn't exist in config."""
        config = {
            "mode": "dry_run",
            "models": {"utility": "fallback-model"},  # Old format without tiers
            "ensemble": {"agents": [{"name": "test"}]},  # Old format
        }
        resolved = ResolvedConfig.from_dict(config, mode="dry_run")

        # Should fall back to the direct models dict
        assert resolved.active_models == {"utility": "fallback-model"}
        assert resolved.active_agents == [{"name": "test"}]

    def test_raw_config_preserved(self, sample_config):
        """Test that original config is preserved in raw attribute."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        # Raw config should contain original keys
        assert "models" in resolved.raw
        assert "ensemble" in resolved.raw
        assert "mode" in resolved.raw


class TestResolvedConfigToDict:
    """Tests for ResolvedConfig.to_dict() backward compatibility."""

    def test_to_dict_creates_private_keys(self, sample_config):
        """Test that to_dict() creates private _active_* keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        result = resolved.to_dict()

        assert "_active_models" in result
        assert "_active_agents" in result
        assert "_should_submit" in result
        assert "_effective_mode" in result

    def test_to_dict_preserves_original_keys(self, sample_config):
        """Test that to_dict() preserves original config keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        result = resolved.to_dict()

        # Original keys should still be present
        assert "models" in result
        assert "ensemble" in result
        assert "mode" in result

    def test_to_dict_values_match_attributes(self, sample_config):
        """Test that to_dict() values match the resolved attributes."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="production")
        result = resolved.to_dict()

        assert result["_active_models"] == resolved.active_models
        assert result["_active_agents"] == resolved.active_agents
        assert result["_should_submit"] == resolved.should_submit
        assert result["_effective_mode"] == resolved.mode


class TestConfigContract:
    """Tests verifying the contract between config and handlers."""

    def test_active_agents_is_list(self, sample_config):
        """Test that active_agents is always a list."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        assert isinstance(resolved.active_agents, list)

    def test_active_models_is_dict(self, sample_config):
        """Test that active_models is always a dict."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        assert isinstance(resolved.active_models, dict)

    def test_should_submit_is_bool(self, sample_config):
        """Test that should_submit is always a boolean."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        assert isinstance(resolved.should_submit, bool)

    def test_mode_is_string(self, sample_config):
        """Test that mode is always a string."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        assert isinstance(resolved.mode, str)

    def test_agent_structure(self, sample_config):
        """Test that each agent in active_agents has expected keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        for agent in resolved.active_agents:
            assert "name" in agent, "Agent missing 'name' key"
            assert "model" in agent, "Agent missing 'model' key"
            assert "weight" in agent, "Agent missing 'weight' key"

    def test_agents_limited_to_five(self, sample_config):
        """Test that active_agents is limited to 5 agents."""
        # Add more than 5 agents
        sample_config["ensemble"]["cheap"] = [
            {"name": f"agent_{i}", "model": "test", "weight": 1.0}
            for i in range(10)
        ]
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        assert len(resolved.active_agents) == 5


class TestModeValidation:
    """Tests for mode value validation."""

    def test_valid_modes(self, sample_config):
        """Test that all valid modes are accepted."""
        valid_modes = ["dry_run", "dry_run_heavy", "production"]

        for mode in valid_modes:
            resolved = ResolvedConfig.from_dict(sample_config.copy(), mode=mode)
            assert resolved.mode == mode

    def test_invalid_mode_raises_error(self, sample_config):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ResolvedConfig.from_dict(sample_config, mode="invalid_mode")

        assert "Invalid mode" in str(exc_info.value)

    def test_only_production_submits(self, sample_config):
        """Test that only production mode enables submission."""
        modes_and_submit = [
            ("dry_run", False),
            ("dry_run_heavy", False),
            ("production", True),
        ]

        for mode, expected_submit in modes_and_submit:
            resolved = ResolvedConfig.from_dict(sample_config.copy(), mode=mode)
            assert resolved.should_submit == expected_submit, f"Mode {mode} should_submit={expected_submit}"

    def test_only_dry_run_uses_cheap(self, sample_config):
        """Test that only dry_run mode uses cheap models."""
        resolved_dry = ResolvedConfig.from_dict(sample_config.copy(), mode="dry_run")
        resolved_heavy = ResolvedConfig.from_dict(sample_config.copy(), mode="dry_run_heavy")
        resolved_prod = ResolvedConfig.from_dict(sample_config.copy(), mode="production")

        assert resolved_dry.active_models == sample_config["models"]["cheap"]
        assert resolved_heavy.active_models == sample_config["models"]["production"]
        assert resolved_prod.active_models == sample_config["models"]["production"]


class TestResolvedConfigAccessors:
    """Tests for dict-like accessor methods."""

    def test_get_returns_raw_values(self, sample_config):
        """Test that get() returns values from raw config."""
        sample_config["custom_key"] = "custom_value"
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        assert resolved.get("custom_key") == "custom_value"
        assert resolved.get("nonexistent", "default") == "default"

    def test_getitem_returns_raw_values(self, sample_config):
        """Test that [] operator returns values from raw config."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        assert resolved["mode"] == "dry_run"

    def test_getitem_raises_keyerror(self, sample_config):
        """Test that [] operator raises KeyError for missing keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        with pytest.raises(KeyError):
            _ = resolved["nonexistent_key"]

    def test_contains_checks_raw_config(self, sample_config):
        """Test that 'in' operator checks raw config."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        assert "mode" in resolved
        assert "models" in resolved
        assert "nonexistent" not in resolved


class TestResolvedConfigImmutability:
    """Tests for config immutability behavior."""

    def test_does_not_modify_original_config(self, sample_config):
        """Test that from_dict() does not modify the original config."""
        original_keys = set(sample_config.keys())

        _ = ResolvedConfig.from_dict(sample_config, mode="dry_run")

        # Original config should not have _active_* keys
        assert set(sample_config.keys()) == original_keys
        assert "_active_models" not in sample_config

    def test_to_dict_returns_copy(self, sample_config):
        """Test that to_dict() returns a copy, not the original."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="dry_run")
        result = resolved.to_dict()

        # Modifying result should not affect raw
        result["new_key"] = "new_value"
        assert "new_key" not in resolved.raw
