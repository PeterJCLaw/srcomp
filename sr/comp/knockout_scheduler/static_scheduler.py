"""
A static knockout schedule.
"""

from __future__ import annotations

import datetime
import re
from typing import Any, NewType
from typing_extensions import TypedDict

from ..match_period import Match, MatchSlot, MatchType
from ..types import ArenaName, MatchNumber, TLA
from .base_scheduler import BaseKnockoutScheduler

StaticMatchTeamReference = NewType('StaticMatchTeamReference', str)
StaticMatchTeamReference.__doc__ = r"""
A logical reference to a team for pulling into a knockout match.

This supports the following formats:
 - 'S\d+': A seeded team, pulled from the results of the league stage.
 - '\d{3}': A reference to a tie-resolved rank in the results of another match
   within the knockout. The first digit refers to the round number, the second
   to the match number within that round and the last to the rank within the
   results of that match to look for a team. All of these are 0-indexed, so
   '000' is the winner of the first match from the first knockouts round. Ties
   are resolved using the standard league position logic.
 - 'R\d+M\d+P\d+': Alternative spelling of round/match/position reference, this
   supports indices containing more digits but otherwise behaves the same.
"""


class InvalidSeedError(ValueError):
    pass


class InvalidReferenceError(ValueError):
    pass


class WrongNumberOfTeamsError(ValueError):
    pass


class StaticMatchInfo(TypedDict):
    arena: ArenaName
    start_time: datetime.datetime
    teams: list[StaticMatchTeamReference]
    display_name: str | None


def parse_team_ref(team_ref: str) -> tuple[int, int, int]:
    """
    Parse a string reference into round/match/position.

    See docstring on `StaticMatchTeamReference` for further details -- this
    function supports both the compressed and RMP formats.
    """

    if len(team_ref) == 3 and team_ref.isdecimal():
        # Compressed format
        r, m, p = (int(x) for x in team_ref)
        return r, m, p

    # Longer "RMP" format
    match = re.match(r'^R(\d+)M(\d+)P(\d+)$', team_ref)
    if not match:
        raise InvalidReferenceError(
            "Match references must be of the form 'R<num>M<num>P<num>' "
            f"(or '<digit><digit><digit>'), not {team_ref!r}.",
        )

    r, m, p = (int(x) for x in match.groups())
    return r, m, p


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
        self._knockout_seeds = self._get_seeds()

    def get_team(self, team_ref: StaticMatchTeamReference | None) -> TLA | None:
        if team_ref is None:
            return None

        if team_ref.startswith('S'):
            # get a seeded position
            pos = int(team_ref[1:])
            # seed numbers are 1 based
            if pos < 1:
                raise InvalidSeedError(f"Invalid seed {team_ref!r} (seed numbers start at 1)")
            pos -= 1
            try:
                return self._knockout_seeds[pos]
            except IndexError:
                raise InvalidSeedError(
                    "Cannot reference seed {}, there are only {} eligible teams!".format(
                        team_ref,
                        len(self._knockout_seeds),
                    ),
                ) from None

        # get a position from a match
        round_num, match_num, pos = parse_team_ref(team_ref)

        try:
            knockout_round = self.knockout_rounds[round_num]
        except IndexError:
            raise InvalidReferenceError(
                f"Reference {team_ref!r} to unknown match round! "
                f"(Cannot refer to round {round_num} when there are only "
                f"{len(self.knockout_rounds)} rounds; note that round numbers "
                "are 0-indexed)",
            ) from None

        try:
            match = knockout_round[match_num]
        except IndexError:
            raise InvalidReferenceError(
                f"Reference {team_ref!r} to unknown match! "
                f"(Cannot refer to round {match_num} when there are only "
                f"{len(knockout_round)} matches in round {round_num}; note that "
                "match numbers are 0-indexed)",
            ) from None

        try:
            ranking = self.get_ranking(match)
            return ranking[pos]
        except IndexError:
            raise InvalidReferenceError(
                f"Reference {team_ref!r} to invalid ranking! "
                f"(Position {pos!r} does not exist in match \"{match.display_name}\")",
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

        if len(teams) != self.num_teams_per_arena:
            raise WrongNumberOfTeamsError(
                f"Unexpected number of teams in match {num} (round {round_num}); "
                f"got {len(teams)}, expecting {self.num_teams_per_arena}." + (
                    " Fill any expected empty places with `null`."
                    if len(teams) < self.num_teams_per_arena
                    else ""
                ),
            )

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
