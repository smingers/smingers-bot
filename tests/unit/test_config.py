"""
Tests for configuration handling and mode resolution.

Tests the apply_mode_to_config() function in main.py and verifies
the contract between entry points and handlers.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import apply_mode_to_config


class TestApplyModeToConfig:
    """Tests for apply_mode_to_config() function."""

    def test_dry_run_mode_uses_cheap_models(self, sample_config):
        """Test that dry_run mode selects cheap models."""
        result = apply_mode_to_config(sample_config, mode="dry_run")

        assert result["_effective_mode"] == "dry_run"
        assert result["_active_models"] == sample_config["models"]["cheap"]
        assert result["_active_agents"] == sample_config["ensemble"]["cheap"]
        assert result["_should_submit"] is False

    def test_dry_run_heavy_uses_production_models(self, sample_config):
        """Test that dry_run_heavy mode selects production models but doesn't submit."""
        result = apply_mode_to_config(sample_config, mode="dry_run_heavy")

        assert result["_effective_mode"] == "dry_run_heavy"
        assert result["_active_models"] == sample_config["models"]["production"]
        assert result["_active_agents"] == sample_config["ensemble"]["production"]
        assert result["_should_submit"] is False

    def test_production_mode_submits(self, sample_config):
        """Test that production mode uses production models and enables submission."""
        result = apply_mode_to_config(sample_config, mode="production")

        assert result["_effective_mode"] == "production"
        assert result["_active_models"] == sample_config["models"]["production"]
        assert result["_active_agents"] == sample_config["ensemble"]["production"]
        assert result["_should_submit"] is True

    def test_dry_run_flag_overrides_config(self, sample_config):
        """Test that dry_run=True flag overrides config.mode."""
        sample_config["mode"] = "production"  # Set production in config
        result = apply_mode_to_config(sample_config, dry_run=True)

        assert result["_effective_mode"] == "dry_run"
        assert result["_should_submit"] is False

    def test_explicit_mode_overrides_dry_run_flag(self, sample_config):
        """Test that explicit mode= parameter takes precedence over dry_run flag."""
        result = apply_mode_to_config(sample_config, mode="production", dry_run=True)

        # mode= should win over dry_run=
        assert result["_effective_mode"] == "production"
        assert result["_should_submit"] is True

    def test_defaults_to_config_mode(self, sample_config):
        """Test that config's mode is used when no arguments provided."""
        sample_config["mode"] = "dry_run_heavy"
        result = apply_mode_to_config(sample_config)

        assert result["_effective_mode"] == "dry_run_heavy"

    def test_defaults_to_dry_run_if_no_mode(self):
        """Test that dry_run is the default when no mode specified anywhere."""
        config = {
            "models": {"cheap": {"utility": "model-a"}, "production": {"utility": "model-b"}},
            "ensemble": {"cheap": [], "production": []},
        }
        result = apply_mode_to_config(config)

        assert result["_effective_mode"] == "dry_run"

    def test_fallback_for_missing_model_tier(self):
        """Test fallback when model tier doesn't exist in config."""
        config = {
            "mode": "dry_run",
            "models": {"utility": "fallback-model"},  # Old format without tiers
            "ensemble": {"agents": [{"name": "test"}]},  # Old format
        }
        result = apply_mode_to_config(config, mode="dry_run")

        # Should fall back to the direct models dict
        assert result["_active_models"] == {"utility": "fallback-model"}
        assert result["_active_agents"] == [{"name": "test"}]

    def test_preserves_original_config_keys(self, sample_config):
        """Test that original config keys are preserved."""
        result = apply_mode_to_config(sample_config, mode="dry_run")

        # Original keys should still be present
        assert "models" in result
        assert "ensemble" in result
        assert "mode" in result

    def test_creates_private_keys(self, sample_config):
        """Test that private _active_* keys are created."""
        result = apply_mode_to_config(sample_config, mode="dry_run")

        assert "_active_models" in result
        assert "_active_agents" in result
        assert "_should_submit" in result
        assert "_effective_mode" in result


class TestConfigContract:
    """Tests verifying the contract between config and handlers."""

    def test_active_agents_is_list(self, sample_config):
        """Test that _active_agents is always a list."""
        result = apply_mode_to_config(sample_config, mode="dry_run")
        assert isinstance(result["_active_agents"], list)

    def test_active_models_is_dict(self, sample_config):
        """Test that _active_models is always a dict."""
        result = apply_mode_to_config(sample_config, mode="dry_run")
        assert isinstance(result["_active_models"], dict)

    def test_should_submit_is_bool(self, sample_config):
        """Test that _should_submit is always a boolean."""
        result = apply_mode_to_config(sample_config, mode="dry_run")
        assert isinstance(result["_should_submit"], bool)

    def test_effective_mode_is_string(self, sample_config):
        """Test that _effective_mode is always a string."""
        result = apply_mode_to_config(sample_config, mode="dry_run")
        assert isinstance(result["_effective_mode"], str)

    def test_agent_structure(self, sample_config):
        """Test that each agent in _active_agents has expected keys."""
        result = apply_mode_to_config(sample_config, mode="dry_run")

        for agent in result["_active_agents"]:
            assert "name" in agent, "Agent missing 'name' key"
            assert "model" in agent, "Agent missing 'model' key"
            assert "weight" in agent, "Agent missing 'weight' key"


class TestModeValidation:
    """Tests for mode value validation."""

    def test_valid_modes(self, sample_config):
        """Test that all valid modes are accepted."""
        valid_modes = ["dry_run", "dry_run_heavy", "production"]

        for mode in valid_modes:
            result = apply_mode_to_config(sample_config.copy(), mode=mode)
            assert result["_effective_mode"] == mode

    def test_only_production_submits(self, sample_config):
        """Test that only production mode enables submission."""
        modes_and_submit = [
            ("dry_run", False),
            ("dry_run_heavy", False),
            ("production", True),
        ]

        for mode, expected_submit in modes_and_submit:
            result = apply_mode_to_config(sample_config.copy(), mode=mode)
            assert result["_should_submit"] == expected_submit, f"Mode {mode} should_submit={expected_submit}"

    def test_only_dry_run_uses_cheap(self, sample_config):
        """Test that only dry_run mode uses cheap models."""
        result_dry = apply_mode_to_config(sample_config.copy(), mode="dry_run")
        result_heavy = apply_mode_to_config(sample_config.copy(), mode="dry_run_heavy")
        result_prod = apply_mode_to_config(sample_config.copy(), mode="production")

        assert result_dry["_active_models"] == sample_config["models"]["cheap"]
        assert result_heavy["_active_models"] == sample_config["models"]["production"]
        assert result_prod["_active_models"] == sample_config["models"]["production"]


class TestConfigMutation:
    """Tests for config mutation behavior."""

    def test_modifies_config_in_place(self, sample_config):
        """Test that apply_mode_to_config modifies the original dict."""
        original_id = id(sample_config)
        result = apply_mode_to_config(sample_config, mode="dry_run")

        # Should return the same object
        assert id(result) == original_id

    def test_adds_keys_to_original(self, sample_config):
        """Test that new keys are added to the original config."""
        assert "_active_models" not in sample_config

        apply_mode_to_config(sample_config, mode="dry_run")

        # Now the key should be in the original
        assert "_active_models" in sample_config
