"""
Tests for configuration handling and mode resolution.

Tests the ResolvedConfig class in src/config.py and verifies
the contract between entry points and handlers.

Modes:
    - "test": cheap models, no submission
    - "preview": production models, no submission
    - "live": production models, submits
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import ResolvedConfig


class TestResolvedConfigFromDict:
    """Tests for ResolvedConfig.from_dict() method."""

    def test_test_mode_uses_cheap_models(self, sample_config):
        """Test that test mode selects cheap models."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        assert resolved.mode == "test"
        assert resolved.active_models == sample_config["models"]["cheap"]
        assert resolved.active_agents == sample_config["ensemble"]["cheap"]
        assert resolved.should_submit is False

    def test_preview_mode_uses_production_models(self, sample_config):
        """Test that preview mode selects production models but doesn't submit."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="preview")

        assert resolved.mode == "preview"
        assert resolved.active_models == sample_config["models"]["production"]
        assert resolved.active_agents == sample_config["ensemble"]["production"]
        assert resolved.should_submit is False

    def test_live_mode_submits(self, sample_config):
        """Test that live mode uses production models and enables submission."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="live")

        assert resolved.mode == "live"
        assert resolved.active_models == sample_config["models"]["production"]
        assert resolved.active_agents == sample_config["ensemble"]["production"]
        assert resolved.should_submit is True

    def test_dry_run_flag_overrides_config(self, sample_config):
        """Test that dry_run=True flag overrides config.mode."""
        sample_config["mode"] = "live"  # Set live in config
        resolved = ResolvedConfig.from_dict(sample_config, dry_run=True)

        assert resolved.mode == "test"
        assert resolved.should_submit is False

    def test_explicit_mode_overrides_dry_run_flag(self, sample_config):
        """Test that explicit mode= parameter takes precedence over dry_run flag."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="live", dry_run=True)

        # mode= should win over dry_run=
        assert resolved.mode == "live"
        assert resolved.should_submit is True

    def test_defaults_to_config_mode(self, sample_config):
        """Test that config's mode is used when no arguments provided."""
        sample_config["mode"] = "preview"
        resolved = ResolvedConfig.from_dict(sample_config)

        assert resolved.mode == "preview"

    def test_defaults_to_test_if_no_mode(self):
        """Test that test is the default when no mode specified anywhere."""
        config = {
            "models": {"cheap": {"utility": "model-a"}, "production": {"utility": "model-b"}},
            "ensemble": {"cheap": [], "production": []},
        }
        resolved = ResolvedConfig.from_dict(config)

        assert resolved.mode == "test"

    def test_fallback_for_missing_model_tier(self):
        """Test fallback when model tier doesn't exist in config."""
        config = {
            "mode": "test",
            "models": {"utility": "fallback-model"},  # Old format without tiers
            "ensemble": {"agents": [{"name": "test"}]},  # Old format
        }
        resolved = ResolvedConfig.from_dict(config, mode="test")

        # Should fall back to the direct models dict
        assert resolved.active_models == {"utility": "fallback-model"}
        assert resolved.active_agents == [{"name": "test"}]

    def test_raw_config_preserved(self, sample_config):
        """Test that original config is preserved in raw attribute."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        # Raw config should contain original keys
        assert "models" in resolved.raw
        assert "ensemble" in resolved.raw
        assert "mode" in resolved.raw


class TestResolvedConfigToDict:
    """Tests for ResolvedConfig.to_dict() backward compatibility."""

    def test_to_dict_creates_private_keys(self, sample_config):
        """Test that to_dict() creates private _active_* keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        result = resolved.to_dict()

        assert "_active_models" in result
        assert "_active_agents" in result
        assert "_should_submit" in result

    def test_to_dict_preserves_original_keys(self, sample_config):
        """Test that to_dict() preserves original config keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        result = resolved.to_dict()

        # Original keys should still be present
        assert "models" in result
        assert "ensemble" in result
        assert "mode" in result

    def test_to_dict_mode_is_effective_mode(self, sample_config):
        """Test that to_dict() sets mode to the effective mode, not config default."""
        # Config has mode="test" but we override with "live"
        sample_config["mode"] = "test"
        resolved = ResolvedConfig.from_dict(sample_config, mode="live")
        result = resolved.to_dict()

        # mode should be the EFFECTIVE mode, not the config default
        assert result["mode"] == "live"
        assert result["_should_submit"] is True

    def test_to_dict_values_match_attributes(self, sample_config):
        """Test that to_dict() values match the resolved attributes."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="live")
        result = resolved.to_dict()

        assert result["_active_models"] == resolved.active_models
        assert result["_active_agents"] == resolved.active_agents
        assert result["_should_submit"] == resolved.should_submit
        assert result["mode"] == resolved.mode


class TestConfigContract:
    """Tests verifying the contract between config and handlers."""

    def test_active_agents_is_list(self, sample_config):
        """Test that active_agents is always a list."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        assert isinstance(resolved.active_agents, list)

    def test_active_models_is_dict(self, sample_config):
        """Test that active_models is always a dict."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        assert isinstance(resolved.active_models, dict)

    def test_should_submit_is_bool(self, sample_config):
        """Test that should_submit is always a boolean."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        assert isinstance(resolved.should_submit, bool)

    def test_mode_is_string(self, sample_config):
        """Test that mode is always a string."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        assert isinstance(resolved.mode, str)

    def test_agent_structure(self, sample_config):
        """Test that each agent in active_agents has expected keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

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
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        assert len(resolved.active_agents) == 5


class TestModeValidation:
    """Tests for mode value validation."""

    def test_valid_modes(self, sample_config):
        """Test that all valid modes are accepted."""
        valid_modes = ["test", "preview", "live"]

        for mode in valid_modes:
            resolved = ResolvedConfig.from_dict(sample_config.copy(), mode=mode)
            assert resolved.mode == mode

    def test_invalid_mode_raises_error(self, sample_config):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ResolvedConfig.from_dict(sample_config, mode="invalid_mode")

        assert "Invalid mode" in str(exc_info.value)

    def test_only_live_submits(self, sample_config):
        """Test that only live mode enables submission."""
        modes_and_submit = [
            ("test", False),
            ("preview", False),
            ("live", True),
        ]

        for mode, expected_submit in modes_and_submit:
            resolved = ResolvedConfig.from_dict(sample_config.copy(), mode=mode)
            assert resolved.should_submit == expected_submit, f"Mode {mode} should_submit={expected_submit}"

    def test_only_test_uses_cheap(self, sample_config):
        """Test that only test mode uses cheap models."""
        resolved_test = ResolvedConfig.from_dict(sample_config.copy(), mode="test")
        resolved_preview = ResolvedConfig.from_dict(sample_config.copy(), mode="preview")
        resolved_live = ResolvedConfig.from_dict(sample_config.copy(), mode="live")

        assert resolved_test.active_models == sample_config["models"]["cheap"]
        assert resolved_preview.active_models == sample_config["models"]["production"]
        assert resolved_live.active_models == sample_config["models"]["production"]


class TestResolvedConfigAccessors:
    """Tests for dict-like accessor methods."""

    def test_get_returns_raw_values(self, sample_config):
        """Test that get() returns values from raw config."""
        sample_config["custom_key"] = "custom_value"
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        assert resolved.get("custom_key") == "custom_value"
        assert resolved.get("nonexistent", "default") == "default"

    def test_getitem_returns_raw_values(self, sample_config):
        """Test that [] operator returns values from raw config (not resolved)."""
        # sample_config has mode="test" in raw config
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        # __getitem__ reads from raw, so returns original config value
        # Use resolved.mode for the effective/resolved mode
        assert resolved["models"] == sample_config["models"]
        assert "mode" in resolved  # mode key exists in raw

    def test_getitem_raises_keyerror(self, sample_config):
        """Test that [] operator raises KeyError for missing keys."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        with pytest.raises(KeyError):
            _ = resolved["nonexistent_key"]

    def test_contains_checks_raw_config(self, sample_config):
        """Test that 'in' operator checks raw config."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")

        assert "mode" in resolved
        assert "models" in resolved
        assert "nonexistent" not in resolved


class TestResolvedConfigImmutability:
    """Tests for config immutability behavior."""

    def test_does_not_modify_original_config(self, sample_config):
        """Test that from_dict() does not modify the original config."""
        original_keys = set(sample_config.keys())

        _ = ResolvedConfig.from_dict(sample_config, mode="test")

        # Original config should not have _active_* keys
        assert set(sample_config.keys()) == original_keys
        assert "_active_models" not in sample_config

    def test_to_dict_returns_copy(self, sample_config):
        """Test that to_dict() returns a copy, not the original."""
        resolved = ResolvedConfig.from_dict(sample_config, mode="test")
        result = resolved.to_dict()

        # Modifying result should not affect raw
        result["new_key"] = "new_value"
        assert "new_key" not in resolved.raw
