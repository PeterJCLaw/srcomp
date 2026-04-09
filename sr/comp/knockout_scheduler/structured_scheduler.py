"""An automatic seeded knockout schedule."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..match_period import KnockoutMatch, MatchSlot, MatchType
from ..match_period_clock import MatchPeriodClock, Spacing
from ..scores import Scores
from ..teams import Team
from ..types import (
    ArenaName,
    MatchNumber,
    ScheduleStructuredKnockoutData,
    StructuredKnockoutData,
    StructuredMatchInfo,
    StructuredMatchTeamReference,
    TLA,
)
from .automatic_scheduler import RoundsSpacing
from .base_scheduler import (
    BaseKnockoutScheduleData,
    BaseKnockoutScheduler,
    DEFAULT_KNOCKOUT_BRACKET_NAME,
)
from .static_scheduler import (
    InvalidReferenceError,
    InvalidSeedError,
    WrongNumberOfTeamsError,
)
from .types import ScheduleHost


class StructuredKnockoutScheduleData(BaseKnockoutScheduleData):
    schedule: ScheduleStructuredKnockoutData
    structure: StructuredKnockoutData


class StructuredScheduler(BaseKnockoutScheduler[StructuredKnockoutScheduleData]):
    """
    A class that can be used to generate a knockout schedule based on a structure.

    :param schedule: The league schedule.
    :param scores: The scores.
    :param arenas: The arenas.
    :param num_teams_per_arena: The usual number of teams per arena.
    :param teams: The teams.
    :param config: Custom configuration for the knockout scheduler.
    """

    def __init__(
        self,
        schedule: ScheduleHost,
        scores: Scores,
        arenas: Iterable[ArenaName],
        num_teams_per_arena: int,
        teams: Mapping[TLA, Team],
        config: StructuredKnockoutScheduleData,
    ) -> None:
        super().__init__(schedule, scores, arenas, num_teams_per_arena, teams, config)

        self.clock = MatchPeriodClock(self.period, self.schedule.delays)

        # Collect a list of the teams eligible for the knockouts, in seeded order.
        self._knockout_seeds = self._get_seeds()

        # Lookup by structure reference, purely for internal lookup
        self._matches: dict[tuple[int, int, ArenaName], KnockoutMatch] = {}

    def get_team(self, team_ref: StructuredMatchTeamReference | None) -> TLA | None:
        if team_ref is None:
            return None

        if 'seed' in team_ref:
            seed = team_ref['seed']  # type: ignore[typeddict-item]
            # seed numbers are 1 based
            if seed < 1:
                raise InvalidSeedError(f"Invalid seed {team_ref!r} (seed numbers start at 1)")
            seed -= 1
            try:
                return self._knockout_seeds[seed]
            except IndexError:
                raise InvalidSeedError(
                    "Cannot reference seed {}, there are only {} eligible teams!".format(
                        team_ref,
                        len(self._knockout_seeds),
                    ),
                ) from None

        assert 'seed' not in team_ref, "Unknown team reference format"
        assert 'round' in team_ref, "Unknown team reference format"

        # get a position from a match

        arena = team_ref['arena']
        if arena not in self.arenas:
            raise InvalidReferenceError(f"Reference {team_ref!r} to unknown arena!")

        round_num = team_ref['round']
        slot_num = team_ref['slot']
        match_ref = (round_num, slot_num, arena)
        pos = team_ref['position']

        try:
            match = self._matches[match_ref]
        except KeyError:
            rounds_info = self.config['structure']['rounds']

            if round_num not in rounds_info:
                raise InvalidReferenceError(
                    f"Reference {team_ref!r} to unknown match round! "
                    f"(Cannot refer to round {round_num} when there are only "
                    f"{len(rounds_info)} rounds; note that round numbers "
                    "are 0-indexed)",
                ) from None

            slots = rounds_info[round_num]['match_slots']
            if slot_num not in slots:
                raise InvalidReferenceError(
                    f"Reference {team_ref!r} to unknown match slot! "
                    f"(Cannot refer to slot {slot_num} when there are only "
                    f"{len(slots)} slot(s) in round {round_num}; "
                    "note that slot numbers are 0-indexed)",
                ) from None

            matches = slots[slot_num]
            if arena not in matches:
                raise InvalidReferenceError(
                    f"Reference {team_ref!r} to unknown arena! "
                    f"(Cannot refer to arena {arena} within slot {slot_num} which "
                    f"only has matches in {list(matches.keys())}",
                ) from None

            raise RuntimeError(
                f"Reference {team_ref!r} to unknown match, yet all elements appear valid!",
            )

        try:
            ranking = self.get_ranking(match)
            return ranking[pos]
        except IndexError:
            raise InvalidReferenceError(
                f"Reference {team_ref!r} to invalid ranking! "
                f"Position {pos!r} does not exist in match \"{match.display_name}\". "
                f"Available positions: {tuple(range(len(ranking)))}.",
            ) from None

    def _apply_spacing(self, spacing: Spacing) -> None:
        self.clock.apply_spacing(
            spacing=spacing,
            recover_time=self.schedule._recover_time,
        )

    def _add_match_slot(
        self,
        round_num: int,
        slot_num: int,
        slot_info: Mapping[ArenaName, StructuredMatchInfo],
        rounds_remaining: int,
    ) -> None:
        new_matches = {}

        for arena, match_info in sorted(slot_info.items()):
            start_time = self.clock.current_time
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
            match = KnockoutMatch(
                num,
                display_name,
                arena,
                teams,
                start_time,
                end_time,
                MatchType.knockout,
                use_resolved_ranking=not is_final,
                knockout_bracket=match_info.get('bracket', DEFAULT_KNOCKOUT_BRACKET_NAME),
            )
            self.knockout_rounds[-1].append(match)
            self._matches[round_num, slot_num, arena] = match
            new_matches[arena] = match

        self.clock.advance_time(self.schedule.match_duration)
        self.schedule.matches.append(MatchSlot(new_matches))
        self.period.matches.append(MatchSlot(new_matches))

    def add_knockouts(self) -> None:
        rounds_info = self.config['structure']['rounds']
        rounds_spacing = RoundsSpacing.parse(
            self.config['schedule']['round_spacing'],
        )

        for round_num, round_info in sorted(rounds_info.items()):
            rounds_remaining = len(rounds_info) - round_num - 1
            self._append_knockout_round(
                rounds_remaining,
                name=round_info.get('display_name'),
            )

            for slot_num, slot_info in sorted(round_info['match_slots'].items()):
                self._add_match_slot(
                    round_num,
                    slot_num,
                    slot_info,
                    rounds_remaining,
                )

            if rounds_remaining > 0:
                # Add the delay between rounds
                self._apply_spacing(rounds_spacing.get(
                    round_num=len(self.knockout_rounds),
                    rounds_remaining=rounds_remaining,
                ))
