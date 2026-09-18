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
}
EXTRA = {"currency": "USD", "timezone": "America/New_York", "approved_symbols": ["SPY", "QQQ"]}


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
