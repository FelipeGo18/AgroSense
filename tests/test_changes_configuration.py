"""HU-218: configuración versionada válida, sin cortes inventados."""

import pytest

from backend.config.changes import load_change_parameters


def test_loads_versioned_parameters():
    parameters = load_change_parameters()
    assert 0 < parameters.min_year_share <= 1
    assert 0 <= parameters.dry_quantile <= 1


@pytest.mark.parametrize("text", ["{}", "null", "[", "change_periods: {}", "change_periods: {min_year_share: true}"])
def test_incomplete_configuration_is_rejected(tmp_path, text):
    path = tmp_path / "region.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Configuración"):
        load_change_parameters(path)


@pytest.mark.parametrize("share, quantile", [(0, 0.2), (1.1, 0.2), (0.8, -1), (0.8, 2), (0.8, ".nan"), ("false", 0.2)])
def test_invalid_parameters_are_rejected(tmp_path, share, quantile):
    path = tmp_path / "region.yaml"
    path.write_text(f"change_periods: {{min_year_share: {share}}}\nclimate_normal: {{dry_quantile: {quantile}}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Configuración"):
        load_change_parameters(path)


def test_missing_configuration_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Configuración"):
        load_change_parameters(tmp_path / "missing.yaml")
