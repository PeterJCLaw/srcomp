"""Knockout schedule generation."""

from .automatic_scheduler import AutoKnockoutScheduleData, KnockoutScheduler
from .base_scheduler import UNKNOWABLE_TEAM
from .converters import (
    modernise_automatic_knockout_config,
    modernise_knockout_config_if_needed,
)
from .static_scheduler import StaticKnockoutScheduleData, StaticScheduler
from .structured_scheduler import (
    StructuredKnockoutScheduleData,
    StructuredScheduler,
)
from .types import KnockoutBracket, KnockoutRound

__all__ = (
    'AutoKnockoutScheduleData',
    'KnockoutBracket',
    'KnockoutRound',
    'KnockoutScheduler',
    'modernise_automatic_knockout_config',
    'modernise_knockout_config_if_needed',
    'StaticKnockoutScheduleData',
    'StaticScheduler',
    'StructuredKnockoutScheduleData',
    'StructuredScheduler',
    'UNKNOWABLE_TEAM',
)
