"""
A static knockout schedule.
"""

from __future__ import annotations

import datetime
from typing import Any, NewType
from typing_extensions import TypedDict

from ..match_period import Match, MatchSlot, MatchType
from ..types import ArenaName, MatchNumber, TLA
from .base_scheduler import BaseKnockoutScheduler, UNKNOWABLE_TEAM

StaticMatchTeamReference = NewType('StaticMatchTeamReference', str)


class StaticMatchInfo(TypedDict):
    arena: ArenaName
    start_time: datetime.datetime
    teams: list[StaticMatchTeamReference]
    display_name: str | None


class StaticScheduler(BaseKnockoutScheduler):
    """
    A knockout scheduler which loads almost fixed data from the config. Assumes
    only a single arena.

    Due to the nature of its interaction with the seedings, this scheduler has a
    very limited handling of dropped-out teams: it only adjusts its scheduling
    for dropouts before the knockouts.

    The practical results of this dropout behaviour are:
      * the schedule is stable when teams drop out, as this either affects the
        entire knockout or none of it
      * dropping out a team such that there are no longer enough seeds requires
        manual changes to the schedule to remove the seeds which cannot be filled
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Collect a list of the teams eligible for the knockouts, in seeded order.
        last_league_match_num = self.schedule.n_matches()
        self._knockout_seeds = self._get_non_dropped_out_teams(
            MatchNumber(last_league_match_num),
        )

    def get_team(self, team_ref: StaticMatchTeamReference | None) -> TLA | None:
        if not self._played_all_league_matches():
            return UNKNOWABLE_TEAM

        if team_ref is None:
            return None

        if team_ref.startswith('S'):
            # get a seeded position
            pos = int(team_ref[1:])
            pos -= 1  # seed numbers are 1 based
            try:
                return self._knockout_seeds[pos]
            except IndexError:
                raise ValueError(
                    "Cannot reference seed {}, there are only {} eligible teams!".format(
                        team_ref,
                        len(self._knockout_seeds),
                    ),
                ) from None

        # get a position from a match
        assert len(team_ref) == 3
        round_num, match_num, pos = (int(x) for x in team_ref)

        try:
            match = self.knockout_rounds[round_num][match_num]
        except IndexError:
            raise ValueError(
                f"Reference '{team_ref}' to unscheduled match!",
            ) from None

        try:
            ranking = self.get_ranking(match)
            return ranking[pos]
        except IndexError:
            raise ValueError(
                f"Reference '{team_ref}' to invalid ranking!",
            ) from None

    def _add_match(
        self,
        match_info: StaticMatchInfo,
        rounds_remaining: int,
        round_num: int,
    ) -> None:
        new_matches = {}

        arena = match_info['arena']
        start_time = match_info['start_time']
        end_time = start_time + self.schedule.match_duration
        num = MatchNumber(len(self.schedule.matches))

        teams = [
            self.get_team(team_ref)
            for team_ref in match_info['teams']
        ]

        if len(teams) < self.num_teams_per_arena:
            # Fill empty zones with None
            teams += [None] * (self.num_teams_per_arena - len(teams))

        display_name = self.get_match_display_name(
            rounds_remaining,
            round_num,
            num,
        )

        # allow overriding the name
        override_name = match_info.get('display_name')
        if override_name is not None:
            display_name = f"{override_name} (#{num})"

        is_final = rounds_remaining == 0
        match = Match(
            num,
            display_name,
            arena,
            teams,
            start_time,
            end_time,
            MatchType.knockout,
            use_resolved_ranking=not is_final,
        )
        self.knockout_rounds[-1].append(match)

        new_matches[match_info['arena']] = match

        self.schedule.matches.append(MatchSlot(new_matches))
        self.period.matches.append(MatchSlot(new_matches))

    def add_knockouts(self) -> None:
        knockout_conf = self.config['static_knockout']['matches']

        for round_num, round_info in sorted(knockout_conf.items()):
            self.knockout_rounds += [[]]
            rounds_remaining = len(knockout_conf) - round_num - 1
            for match_num, match_info in sorted(round_info.items()):
                self._add_match(match_info, rounds_remaining, match_num)
