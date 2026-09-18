from datetime import time

import pytest
from pydantic import ValidationError

from auto_invest.settings import (
    Ceilings,
    CeilingExceeded,
    Settings,
    check_against_ceilings,
    load_settings,
)

BASE = {
    "risk_per_trade": 0.005,
    "daily_loss_limit": 0.01,
    "per_symbol_cap": 0.25,
    "total_exposure_cap": 0.80,
    "entries_per_day": 3,
    "settled_cash_only": True,
    "no_leverage": True,
    "entry_window_start": "10:00",
    "entry_window_end": "15:30",
    "forced_close": "15:50",
    "quote_max_age_seconds": 5,
    "price_band": 0.10,
    "spread_cap": 0.0005,
    "volume_floor": 1000000,
    "max_cost_fraction_of_risk": 0.10,
    "score_threshold": 0.6,
    "order_value_cap": 0.25,
}
EXTRA = {
    "currency": "USD",
    "timezone": "America/New_York",
    "approved_symbols": ["SPY", "QQQ"],
    "opening_range_minutes": 5,
    "history_sessions": 20,
}


def settings_with(**overrides) -> Settings:
    return Settings.model_validate({**BASE, **EXTRA, **overrides})


def ceilings() -> Ceilings:
    return Ceilings.model_validate(BASE)


def test_repo_config_files_load():
    settings = load_settings()
    assert settings.risk_per_trade == 0.005
    assert settings.daily_loss_limit == 0.01
    assert settings.per_symbol_cap == 0.25
    assert settings.total_exposure_cap == 0.80
    assert settings.entries_per_day == 3
    assert settings.settled_cash_only is True
    assert settings.no_leverage is True
    assert settings.entry_window_start == time(10, 0)
    assert settings.entry_window_end == time(15, 30)
    assert settings.forced_close == time(15, 50)
    assert settings.approved_symbols == ["SPY", "QQQ"]
    assert settings.currency == "USD"
    assert settings.quote_max_age_seconds == 5
    assert settings.price_band == 0.10
    assert settings.spread_cap == 0.0005
    assert settings.volume_floor == 1000000
    assert settings.max_cost_fraction_of_risk == 0.10
    assert settings.score_threshold == 0.6
    assert settings.order_value_cap == 0.25
    assert settings.opening_range_minutes == 5
    assert settings.history_sessions == 20


def test_settings_at_the_ceiling_pass():
    check_against_ceilings(settings_with(), ceilings())


def test_tightened_settings_pass():
    check_against_ceilings(
        settings_with(
            risk_per_trade=0.0025,
            daily_loss_limit=0.005,
            per_symbol_cap=0.10,
            total_exposure_cap=0.50,
            entries_per_day=1,
            entry_window_start="10:30",
            entry_window_end="15:00",
            forced_close="15:40",
        ),
        ceilings(),
    )


def test_tightened_phase_1_settings_pass():
    check_against_ceilings(
        settings_with(
            quote_max_age_seconds=2,
            price_band=0.05,
            spread_cap=0.0002,
            volume_floor=2000000,
            max_cost_fraction_of_risk=0.05,
            score_threshold=0.8,
            order_value_cap=0.10,
        ),
        ceilings(),
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("risk_per_trade", 0.0051),
        ("daily_loss_limit", 0.02),
        ("per_symbol_cap", 0.26),
        ("total_exposure_cap", 0.81),
        ("entries_per_day", 4),
        ("entry_window_start", "09:59"),
        ("entry_window_end", "15:31"),
        ("forced_close", "15:51"),
        ("quote_max_age_seconds", 6),
        ("price_band", 0.11),
        ("spread_cap", 0.0006),
        ("volume_floor", 999999),
        ("max_cost_fraction_of_risk", 0.11),
        ("score_threshold", 0.59),
        ("order_value_cap", 0.26),
    ],
)
def test_each_setting_over_its_ceiling_fails(field, value):
    with pytest.raises(CeilingExceeded, match=field):
        check_against_ceilings(settings_with(**{field: value}), ceilings())


@pytest.mark.parametrize("flag", ["settled_cash_only", "no_leverage"])
def test_safety_flags_cannot_be_turned_off(flag):
    with pytest.raises(CeilingExceeded, match=flag):
        check_against_ceilings(settings_with(**{flag: False}), ceilings())


@pytest.mark.parametrize("flag", ["settled_cash_only", "no_leverage"])
def test_ceilings_file_cannot_turn_off_safety_flags(flag):
    with pytest.raises(ValidationError, match=flag):
        Ceilings.model_validate({**BASE, flag: False})


def test_entry_window_must_be_ordered():
    with pytest.raises(ValidationError, match="entry_window_start"):
        settings_with(entry_window_start="15:30", entry_window_end="10:00")


def test_unknown_setting_is_rejected():
    with pytest.raises(ValidationError):
        settings_with(max_leverage=2)


def test_missing_setting_is_rejected():
    data = {**BASE, **EXTRA}
    del data["entries_per_day"]
    with pytest.raises(ValidationError, match="entries_per_day"):
        Settings.model_validate(data)
