import tomllib
from datetime import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_per_trade: float = Field(gt=0, le=1)
    daily_loss_limit: float = Field(gt=0, le=1)
    per_symbol_cap: float = Field(gt=0, le=1)
    total_exposure_cap: float = Field(gt=0, le=1)
    entries_per_day: int = Field(ge=0)
    settled_cash_only: bool
    no_leverage: bool
    entry_window_start: time
    entry_window_end: time
    forced_close: time

    @model_validator(mode="after")
    def window_is_ordered(self) -> "Limits":
        if not self.entry_window_start < self.entry_window_end < self.forced_close:
            raise ValueError(
                "entry_window_start must be before entry_window_end, "
                "which must be before forced_close"
            )
        return self


class Ceilings(Limits):
    @model_validator(mode="after")
    def flags_are_locked(self) -> "Ceilings":
        if not self.settled_cash_only:
            raise ValueError("ceilings must keep settled_cash_only = true")
        if not self.no_leverage:
            raise ValueError("ceilings must keep no_leverage = true")
        return self


class Settings(Limits):
    currency: str
    timezone: str
    approved_symbols: list[str] = Field(min_length=1)


class CeilingExceeded(ValueError):
    pass


def check_against_ceilings(settings: Settings, ceilings: Ceilings) -> None:
    at_most = [
        "risk_per_trade",
        "daily_loss_limit",
        "per_symbol_cap",
        "total_exposure_cap",
        "entries_per_day",
        "entry_window_end",
        "forced_close",
    ]
    problems = []
    for name in at_most:
        if getattr(settings, name) > getattr(ceilings, name):
            problems.append(
                f"{name} = {getattr(settings, name)} exceeds ceiling {getattr(ceilings, name)}"
            )
    if settings.entry_window_start < ceilings.entry_window_start:
        problems.append(
            f"entry_window_start = {settings.entry_window_start} is earlier than "
            f"ceiling {ceilings.entry_window_start}"
        )
    for flag in ("settled_cash_only", "no_leverage"):
        if not getattr(settings, flag):
            problems.append(f"{flag} must be true")
    if problems:
        raise CeilingExceeded("; ".join(problems))


def load_settings(
    settings_path: Path = CONFIG_DIR / "settings.toml",
    ceilings_path: Path = CONFIG_DIR / "ceilings.toml",
) -> Settings:
    settings = Settings.model_validate(tomllib.loads(settings_path.read_text()))
    ceilings = Ceilings.model_validate(tomllib.loads(ceilings_path.read_text()))
    check_against_ceilings(settings, ceilings)
    return settings
