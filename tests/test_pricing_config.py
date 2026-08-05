"""Tests for pricing estimation and configuration precedence."""

from __future__ import annotations

from promptanalyzer.config import Config
from promptanalyzer.pricing import estimate_cost, register_price


def test_known_model_cost():
    cost = estimate_cost("gpt-4o-mini", 1000, 1000)
    assert cost == round(0.00015 + 0.00060, 8)


def test_prefix_match_for_dated_model():
    assert estimate_cost("gpt-4o-2024-08-06", 1000, 0) == estimate_cost("gpt-4o", 1000, 0)


def test_unknown_model_returns_none():
    assert estimate_cost("some-random-model", 100, 100) is None


def test_register_custom_price():
    register_price("my-model", 0.001, 0.002)
    assert estimate_cost("my-model-v2", 1000, 1000) == round(0.001 + 0.002, 8)


def test_env_overrides_defaults(monkeypatch):
    monkeypatch.setenv("PROMPTANALYZER_PORT", "9999")
    monkeypatch.setenv("PROMPTANALYZER_PROJECT", "team-x")
    monkeypatch.setenv("PROMPTANALYZER_LOG_COST", "false")
    cfg = Config()
    assert cfg.port == 9999
    assert cfg.project == "team-x"
    assert cfg.log_cost is False


def test_legacy_prefix_supported(monkeypatch):
    monkeypatch.delenv("PROMPTANALYZER_PORT", raising=False)
    monkeypatch.setenv("PROMPTLOG_PORT", "4321")
    assert Config().port == 4321
