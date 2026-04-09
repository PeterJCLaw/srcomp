"""Helpers to upgrade older configuration formats"""


from __future__ import annotations

from typing import cast

from ..types import (
    LegacyScheduleKnockoutData,
    ScheduleAutomaticKnockoutData,
    ScheduleKnockoutData,
    ScheduleStaticKnockoutData,
)


def modernise_automatic_knockout_config(
    old_config: LegacyScheduleKnockoutData,
) -> ScheduleAutomaticKnockoutData:
    round_spacing = old_config['round_spacing']
    final_spacing = round_spacing + old_config['final_delay']

    new_config = ScheduleAutomaticKnockoutData(
        scheduler='automatic',
        round_spacing={
            'default': {
                'delay_flex': 0,
                'minimum': round_spacing,
                'nominal': round_spacing,
            },
            'overrides': {
                -1: {
                    'delay_flex': 0,
                    'minimum': final_spacing,
                    'nominal': final_spacing,
                },
            },
        },
        single_arena=old_config['single_arena'],
    )

    if (brackets := old_config.get('brackets')) is not None:
        new_config['brackets'] = brackets

    return new_config


def modernise_knockout_config_if_needed(
    config: ScheduleKnockoutData | LegacyScheduleKnockoutData,
) -> ScheduleKnockoutData:
    if 'scheduler' in config:
        return cast(ScheduleKnockoutData, config)

    if config.get('static'):
        return ScheduleStaticKnockoutData(scheduler='static')

    if 'single_arena' in config:
        return modernise_automatic_knockout_config(
            cast(LegacyScheduleKnockoutData, config),
        )

    raise ValueError("Unknown static knockout scheduler config structure")
