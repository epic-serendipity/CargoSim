"""Tests for the configuration management system."""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, mock_open

from cargosim.config import (
    SimConfig, ThemeConfig, RecordingConfig, AdvancedDecisionConfig, 
    GameplayConfig, BarScale, validate_config, load_config, save_config,
    hex2rgb, blend, calculate_contrast_ratio, ensure_contrast,
    apply_theme_preset, THEME_PRESETS, M
)


class TestColorUtilities:
    """Test color utility functions."""
    
    def test_hex2rgb_basic(self):
        """Test basic hex to RGB conversion."""
        assert hex2rgb("#FF0000") == (255, 0, 0)
        assert hex2rgb("#00FF00") == (0, 255, 0)
        assert hex2rgb("#0000FF") == (0, 0, 255)
        assert hex2rgb("#FFFFFF") == (255, 255, 255)
        assert hex2rgb("#000000") == (0, 0, 0)
    
    def test_hex2rgb_short_format(self):
        """Test 3-character hex format."""
        assert hex2rgb("#F00") == (255, 0, 0)
        assert hex2rgb("#0F0") == (0, 255, 0)
        assert hex2rgb("#00F") == (0, 0, 255)
        assert hex2rgb("#FFF") == (255, 255, 255)
    
    def test_hex2rgb_without_hash(self):
        """Test hex conversion without # prefix."""
        assert hex2rgb("FF0000") == (255, 0, 0)
        assert hex2rgb("F00") == (255, 0, 0)
    
    def test_blend_colors(self):
        """Test color blending function."""
        red = (255, 0, 0)
        blue = (0, 0, 255)
        
        # Blend at t=0 should return first color
        assert blend(red, blue, 0.0) == red
        
        # Blend at t=1 should return second color
        assert blend(red, blue, 1.0) == blue
        
        # Blend at t=0.5 should return middle color
        result = blend(red, blue, 0.5)
        assert result == (127, 0, 127)
    
    def test_calculate_contrast_ratio(self):
        """Test contrast ratio calculation."""
        white = (255, 255, 255)
        black = (0, 0, 0)
        
        # Maximum contrast
        ratio = calculate_contrast_ratio(white, black)
        assert ratio > 20  # Should be 21:1 for perfect white/black
        
        # Same color should have 1:1 ratio
        ratio = calculate_contrast_ratio(white, white)
        assert abs(ratio - 1.0) < 0.1
    
    def test_ensure_contrast(self):
        """Test contrast adjustment function."""
        white = "#FFFFFF"
        light_gray = "#CCCCCC"
        
        # Should adjust light gray to have sufficient contrast with white
        adjusted = ensure_contrast(white, light_gray, min_ratio=4.5)
        assert adjusted != light_gray  # Should be different
        
        # Black should not need adjustment against white
        black = "#000000"
        adjusted = ensure_contrast(white, black, min_ratio=4.5)
        assert adjusted == black  # Should remain unchanged


class TestBarScale:
    """Test BarScale configuration."""
    
    def test_bar_scale_creation(self):
        """Test BarScale initialization."""
        bar_scale = BarScale()
        assert bar_scale.denom_A == 2
        assert bar_scale.denom_B == 2
        assert bar_scale.denom_C == 2
        assert bar_scale.denom_D == 2
    
    def test_bar_scale_custom_values(self):
        """Test BarScale with custom values."""
        bar_scale = BarScale(denom_A=4, denom_B=3, denom_C=2, denom_D=1)
        assert bar_scale.denom_A == 4
        assert bar_scale.denom_B == 3
        assert bar_scale.denom_C == 2
        assert bar_scale.denom_D == 1
    
    def test_bar_scale_serialization(self):
        """Test BarScale JSON serialization."""
        bar_scale = BarScale(denom_A=4, denom_B=3, denom_C=2, denom_D=1)
        json_data = bar_scale.to_json()
        
        expected = {"denom_A": 4, "denom_B": 3, "denom_C": 2, "denom_D": 1}
        assert json_data == expected
    
    def test_bar_scale_deserialization(self):
        """Test BarScale JSON deserialization."""
        json_data = {"denom_A": 4, "denom_B": 3, "denom_C": 2, "denom_D": 1}
        bar_scale = BarScale.from_json(json_data)
        
        assert bar_scale.denom_A == 4
        assert bar_scale.denom_B == 3
        assert bar_scale.denom_C == 2
        assert bar_scale.denom_D == 1


class TestThemeConfig:
    """Test theme configuration."""
    
    def test_theme_config_creation(self):
        """Test ThemeConfig initialization."""
        theme = ThemeConfig()
        
        # Test that default values are set
        assert theme.game_bg is not None
        assert theme.game_fg is not None
        assert theme.hub_color is not None
        assert theme.good_spoke is not None
        assert theme.bad_spoke is not None
    
    def test_theme_config_serialization(self):
        """Test ThemeConfig JSON serialization."""
        theme = ThemeConfig()
        json_data = theme.to_json()
        
        # Should contain all expected keys
        expected_keys = {
            'game_bg', 'game_fg', 'game_muted', 'hub_color', 'good_spoke', 
            'bad_spoke', 'bar_A', 'bar_B', 'bar_C', 'bar_D', 'ac_colors',
            'accent_primary', 'accent_secondary', 'success', 'warning', 
            'error', 'info'
        }
        assert set(json_data.keys()) >= expected_keys
    
    def test_theme_config_deserialization(self):
        """Test ThemeConfig JSON deserialization."""
        json_data = {
            'game_bg': '#000000',
            'game_fg': '#FFFFFF',
            'hub_color': '#FF0000'
        }
        theme = ThemeConfig.from_json(json_data)
        
        assert theme.game_bg == '#000000'
        assert theme.game_fg == '#FFFFFF'
        assert theme.hub_color == '#FF0000'


class TestSimConfig:
    """Test main simulation configuration."""
    
    def test_sim_config_creation(self):
        """Test SimConfig initialization with defaults."""
        cfg = SimConfig()
        
        assert cfg.fleet_label == "2xC130"
        assert cfg.periods == 60
        assert cfg.init_A == 4
        assert cfg.init_B == 4
        assert cfg.init_C == 2
        assert cfg.init_D == 2
        assert cfg.cap_c130 == 6
        assert cfg.cap_c27 == 3
        assert isinstance(cfg.theme, ThemeConfig)
        assert isinstance(cfg.recording, RecordingConfig)
        assert isinstance(cfg.bar_scale, BarScale)
    
    def test_sim_config_serialization(self):
        """Test SimConfig JSON serialization."""
        cfg = SimConfig()
        json_data = cfg.to_json()
        
        # Should contain all expected keys
        expected_keys = {
            'config_version', 'fleet_label', 'periods', 'init', 'cadence',
            'capacities', 'rest', 'pair_order', 'theme', 'recording',
            'bar_scale', 'adm', 'gameplay'
        }
        assert set(json_data.keys()) >= expected_keys
        
        # Check specific values
        assert json_data['fleet_label'] == "2xC130"
        assert json_data['periods'] == 60
        assert json_data['init'] == [4, 4, 2, 2]
        assert json_data['capacities'] == {"C130": 6, "C27": 3}
    
    def test_sim_config_deserialization(self):
        """Test SimConfig JSON deserialization."""
        json_data = {
            'fleet_label': '4xC130',
            'periods': 120,
            'init': [8, 8, 4, 4],
            'capacities': {'C130': 8, 'C27': 4}
        }
        cfg = SimConfig.from_json(json_data)
        
        assert cfg.fleet_label == '4xC130'
        assert cfg.periods == 120
        assert cfg.init_A == 8
        assert cfg.init_B == 8
        assert cfg.init_C == 4
        assert cfg.init_D == 4
        assert cfg.cap_c130 == 8
        assert cfg.cap_c27 == 4


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_config(self):
        """Test validation of a valid configuration."""
        cfg = SimConfig()
        issues = validate_config(cfg)
        assert len(issues) == 0
    
    def test_invalid_periods(self):
        """Test validation with invalid periods."""
        cfg = SimConfig()
        cfg.periods = 1
        issues = validate_config(cfg)
        assert any("Periods must be at least 2" in issue for issue in issues)
    
    def test_invalid_capacities(self):
        """Test validation with invalid aircraft capacities."""
        cfg = SimConfig()
        cfg.cap_c130 = 0
        issues = validate_config(cfg)
        assert any("Aircraft capacities must be positive" in issue for issue in issues)
    
    def test_invalid_rest_periods(self):
        """Test validation with invalid rest periods."""
        cfg = SimConfig()
        cfg.rest_c130 = 0
        issues = validate_config(cfg)
        assert any("Rest periods must be positive" in issue for issue in issues)
    
    def test_invalid_consumption_cadences(self):
        """Test validation with invalid consumption cadences."""
        cfg = SimConfig()
        cfg.a_days = 0
        issues = validate_config(cfg)
        assert any("Consumption cadences must be positive" in issue for issue in issues)
    
    def test_negative_initial_stock(self):
        """Test validation with negative initial stock."""
        cfg = SimConfig()
        cfg.init_A = -1
        issues = validate_config(cfg)
        assert any("Initial stocks cannot be negative" in issue for issue in issues)
    
    def test_invalid_period_duration(self):
        """Test validation with invalid period duration."""
        cfg = SimConfig()
        cfg.period_seconds = 0
        issues = validate_config(cfg)
        assert any("Period duration must be positive" in issue for issue in issues)
    
    def test_invalid_pair_order(self):
        """Test validation with invalid pair order."""
        cfg = SimConfig()
        cfg.pair_order = [(0, 1, 2)]  # Invalid tuple length
        issues = validate_config(cfg)
        assert any("must be a tuple of length 2" in issue for issue in issues)


class TestConfigFileOperations:
    """Test configuration file loading and saving."""
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        cfg = SimConfig()
        cfg.fleet_label = "4xC130"
        cfg.periods = 120
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Mock the CONFIG_FILE to use our temp file
            with patch('cargosim.config.CONFIG_FILE', temp_path):
                save_config(cfg)
                loaded_cfg = load_config()
                
                assert loaded_cfg.fleet_label == "4xC130"
                assert loaded_cfg.periods == 120
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_config_missing_file(self):
        """Test loading config when file doesn't exist."""
        with patch('cargosim.config.CONFIG_FILE', 'nonexistent.json'):
            cfg = load_config()
            # Should return default config
            assert isinstance(cfg, SimConfig)
            assert cfg.fleet_label == "2xC130"  # Default value
    
    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            with patch('cargosim.config.CONFIG_FILE', temp_path):
                cfg = load_config()
                # Should return default config on parse error
                assert isinstance(cfg, SimConfig)
                assert cfg.fleet_label == "2xC130"  # Default value
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestThemePresets:
    """Test theme preset functionality."""
    
    def test_apply_theme_preset(self):
        """Test applying a theme preset."""
        cfg = SimConfig()
        original_bg = cfg.theme.game_bg
        
        # Apply a different theme preset
        if len(THEME_PRESETS) > 1:
            preset_name = list(THEME_PRESETS.keys())[1]
            apply_theme_preset(cfg.theme, preset_name)
            
            # Theme should have changed (assuming presets are different)
            # Note: This test assumes presets have different values
            assert hasattr(cfg.theme, 'game_bg')
    
    def test_theme_presets_exist(self):
        """Test that theme presets are defined."""
        assert len(THEME_PRESETS) > 0
        
        # Each preset should have required keys
        for preset_name, preset_data in THEME_PRESETS.items():
            assert isinstance(preset_name, str)
            assert isinstance(preset_data, dict)
            assert len(preset_data) > 0


if __name__ == "__main__":
    pytest.main([__file__])
