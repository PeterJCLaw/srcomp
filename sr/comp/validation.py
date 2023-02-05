"""Compstate validation routines."""

from __future__ import annotations

import dataclasses
import datetime
import itertools
import sys
from collections import defaultdict
from typing import Container, Iterable, Iterator, Mapping, NewType, Sequence
from typing_extensions import Literal

from .comp import SRComp
from .knockout_scheduler import UNKNOWABLE_TEAM
from .match_period import Match, MatchSlot, MatchType
from .matches import MatchSchedule
from .scores import BaseScores
from .types import ArenaName, MatchId, MatchNumber, TLA

ErrorType = NewType('ErrorType', str)
ErrorLevel = Literal['error', 'warning', 'hint']

NO_TEAM = None
META_TEAMS = {NO_TEAM, UNKNOWABLE_TEAM}


@dataclasses.dataclass(frozen=True)
class ValidationError(Exception):
    message: str
    code: str
    source: tuple[ErrorType, object] | None
    level: ErrorLevel = 'error'


class ScheduleValidationError(ValidationError):
    def __init__(
        self,
        message: str,
        code: str,
        source: str = '',
        level: ErrorLevel = 'error',
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            source=(ErrorType('Schedule'), source),
            level=level,
        )


@dataclasses.dataclass(frozen=True)
class NaiveValidationError:
    message: str
    code: str
    level: ErrorLevel = 'error'

    def with_source(self, error_type: ErrorType, id_: object) -> ValidationError:
        return ValidationError(
            self.message,
            self.code,
            source=(error_type, id_),
            level=self.level,
        )


def with_source(
    naive_errors: Iterable[NaiveValidationError],
    source: tuple[ErrorType, object],
) -> Iterator[ValidationError]:
    for error in naive_errors:
        yield error.with_source(*source)


def join_and(items: Iterable[object]) -> str:
    strings = [str(x) for x in items]
    if not strings:
        return ""

    if len(strings) == 1:
        return strings[0]

    *rest, last = strings

    return " and ".join((", ".join(rest), last))


def report_errors(error_type: ErrorType, id_: object, errors: list[str]) -> None:
    """
    Print out errors nicely formatted.

    :param str type: The human-readable 'type'.
    :param str id_: The human-readable 'ID'.
    :param list errors: A list of string errors.
    """

    if len(errors) == 0:
        return

    prefix = f"{error_type} {id_}" if id_ else error_type
    print(
        f"{prefix} has the following errors:",
        file=sys.stderr,
    )
    for error in errors:
        print(f"    {error}", file=sys.stderr)


def report_validation_errors(errors: Sequence[ValidationError]) -> None:
    for source, errors_group in itertools.groupby(errors, key=lambda x: x.source):
        messages = [x.message for x in errors_group]
        if source:
            report_errors(*source, messages)
        else:
            for message in messages:
                print(message, file=sys.stderr)


def validate(comp: SRComp) -> int:
    """
    Validate a Compstate repo.

    :param sr.comp.SRComp comp: A competition instance.
    :return: The number of errors that have occurred.
    """

    errors: list[ValidationError] = []

    errors += validate_schedule(comp.schedule, comp.teams.keys(), comp.arenas.keys())

    all_matches = comp.schedule.matches
    errors += validate_team_matches(all_matches, comp.teams.keys())

    errors += validate_scores(MatchType.league, comp.scores.league, all_matches)
    errors += validate_scores(MatchType.knockout, comp.scores.knockout, all_matches)
    errors += validate_scores(MatchType.tiebreaker, comp.scores.tiebreaker, all_matches)

    report_validation_errors(errors)

    return sum(1 for x in errors if x.level == 'error')


def validate_schedule(
    schedule: MatchSchedule,
    possible_teams: Iterable[TLA],
    possible_arenas: Container[ArenaName],
) -> Iterator[ValidationError]:
    """
    Check that the schedule contains enough time for all the matches,
    and that the matches themselves are valid.
    """

    # Check that each match features only valid teams
    for num, match in enumerate(schedule.matches):
        match_errors = validate_match(match, possible_teams)
        yield from with_source(match_errors, source=(ErrorType('Match'), num))

    yield from validate_schedule_count(schedule)

    errors = list(validate_schedule_timings(schedule.matches, schedule.match_duration))
    if len(errors):
        errors.append(
            ValidationError(
                "This usually indicates that the scheduled periods overlap.",
                code='hint-period-overlap',
                source=(ErrorType('Schedule'), 'timing'),
                level='hint',
            ),
        )
        yield from errors

    yield from validate_schedule_arenas(schedule.matches, possible_arenas)


def validate_schedule_count(schedule: MatchSchedule) -> Iterator[ValidationError]:
    planned = schedule.n_planned_league_matches
    actual = schedule.n_league_matches

    if planned > actual:
        yield ScheduleValidationError(
            "Only contains enough time for {} matches, {} are planned".format(
                actual,
                planned,
            ),
            code='not-enough-time',
            level='warning',
        )

    if planned == 0:
        yield ScheduleValidationError(
            "Doesn't contain any matches",
            code='no-matches-scheduled',
            level='warning',
        )


def validate_schedule_timings(
    scheduled_matches: Iterable[MatchSlot],
    match_duration: datetime.timedelta,
) -> Iterator[ValidationError]:
    timing_map = defaultdict(list)
    for match in scheduled_matches:
        game = list(match.values())[0]
        time = game.start_time
        timing_map[time].append(game.num)

    last_time: datetime.datetime | None = None
    for time, match_numbers in sorted(timing_map.items()):
        if len(match_numbers) != 1:
            yield ValidationError(
                "Multiple matches scheduled for {}: {}.".format(
                    time,
                    join_and(match_numbers),
                ),
                code='multiple-matches-at-time',
                source=(ErrorType('Schedule'), 'timing'),
            )

        if last_time is not None and time - last_time < match_duration:
            yield ValidationError(
                "Matches {} start at {} before matches {} have finished.".format(
                    join_and(match_numbers),
                    time,
                    join_and(timing_map[last_time]),
                ),
                code='matches-overlap',
                source=(ErrorType('Schedule'), 'timing'),
            )

        last_time = time


def validate_schedule_arenas(
    matches: Iterable[MatchSlot],
    possible_arenas: Container[ArenaName],
) -> Iterator[ValidationError]:
    """Check that any arena referenced by a match actually exists."""

    error_format_string = "Match {game.num} ({game.type}) references arena '{arena}'."

    for match in matches:
        for arena, game in match.items():
            if arena not in possible_arenas:
                yield ValidationError(
                    error_format_string.format(
                        arena=arena,
                        game=game,
                    ),
                    code='nonexistent-arena',
                    source=(ErrorType('Schedule'), 'arenas'),
                )


def validate_match(
    match: MatchSlot,
    possible_teams: Iterable[TLA],
) -> Iterator[NaiveValidationError]:
    """
    Check that the teams featuring in a match exist and are only
    required in one arena at a time.
    """

    all_teams: list[TLA | None] = []

    for a in match.values():
        all_teams += a.teams

    teams = set(all_teams) - META_TEAMS
    for t in teams:
        all_teams.remove(t)

    # Note: mypy doesn't know that removing META_TEAMS here means that we're
    # removing the Optional nature of the teams.
    # See https://github.com/python/mypy/issues/8526.
    duplicates: set[TLA] = set(all_teams) - META_TEAMS  # type: ignore[assignment]
    if len(duplicates):
        yield NaiveValidationError(
            "Teams {} appear more than once.".format(
                join_and(duplicates),
            ),
            code='team-more-than-one-appearance-in-match',
        )

    extras = teams - set(possible_teams)

    if len(extras):
        yield NaiveValidationError(
            "Teams {} do not exist.".format(
                join_and(extras),
            ),
            'nonexistent-teams',
        )


def validate_scores(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Sequence[MatchSlot],
) -> Iterator[ValidationError]:
    """Validate that the scores are sane."""
    yield from validate_scores_inner(match_type, scores, schedule)
    yield from warn_missing_scores(match_type, scores, schedule)


def validate_scores_inner(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Sequence[MatchSlot],
) -> Iterator[ValidationError]:
    """Validate that scores are sane."""
    # NB: more specific validation is already done during the scoring,
    # so all we need to do is check that the right teams are being awarded
    # points

    match_type_title = match_type.name.title()

    def get_scheduled_match(match_id: MatchId, error_type: ErrorType) -> Match:
        """Check that the requested match was scheduled, return it if so."""
        arena, num = match_id

        if num < 0 or num >= len(schedule):
            raise ValidationError(
                f"{match_type_title} Match not scheduled",
                code='nonexistent-match',
                source=(error_type, match_id),
            )

        match = schedule[num]
        if arena not in match:
            raise ValidationError(
                f"Arena not in this {match_type_title} match",
                code='arena-not-for-match',
                source=(error_type, match_id),
            )

        return match[arena]

    def check(
        error_type: ErrorType,
        match_id: MatchId,
        match: Mapping[TLA, object],
    ) -> Iterator[ValidationError]:
        try:
            scheduled_match = get_scheduled_match(match_id, error_type)
        except ValidationError as error:
            yield error
            return

        errors = validate_match_score(match_type, match, scheduled_match)
        yield from with_source(errors, source=(error_type, match_id))

    for match_id, game_points in scores.game_points.items():
        yield from check(ErrorType('Game Score'), match_id, game_points)

    if match_type == MatchType.league:
        for match_id, league_points in scores.ranked_points.items():
            yield from check(ErrorType('League Points'), match_id, league_points)


def validate_match_score(
    match_type: MatchType,
    match_score: Mapping[TLA, object],
    scheduled_match: Match,
) -> Iterator[NaiveValidationError]:
    """
    Check that the match awards points to the right teams, by checking
    that the teams with points were scheduled to appear in the match.
    """

    # only remove the empty corner marker -- we shouldn't have unknowable
    # teams in the match schedule by the time there's a score for it.
    expected_teams = {x for x in scheduled_match.teams if x is not NO_TEAM}
    # don't remove meta teams from the score's teams -- they shouldn't
    # be there to start with.
    actual_teams = set(match_score.keys())

    extra = actual_teams - expected_teams
    missing = expected_teams - actual_teams

    if len(missing):
        yield NaiveValidationError(
            "Teams {} missing from this {} match.".format(
                join_and(missing),
                match_type.name,
            ),
            code='score-missing-teams',
        )

    if len(extra):
        yield NaiveValidationError(
            "Teams {} not scheduled in this {} match.".format(
                join_and(extra),
                match_type.name,
            ),
            code='score-unexpected-teams',
        )


def warn_missing_scores(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Iterable[MatchSlot],
) -> Iterator[ValidationError]:
    """Check that the scores up to the most recent are all present."""
    match_ids = scores.ranked_points.keys()
    last_match = scores.last_scored_match

    missing = find_missing_scores(match_type, match_ids, last_match, schedule)
    if len(missing) == 0:
        return

    yield ValidationError(
        "\n".join((
            f"The following {match_type.name} scores are missing:",
            "Match   | Arena",
            *(
                f" {match_num:>3}    | {join_and(sorted(arenas))}"
                for match_num, arenas in missing
            ),
        )),
        code='missing-scores',
        source=None,
        level='warning',
    )


def find_missing_scores(
    match_type: MatchType,
    match_ids: Iterable[MatchId],
    last_match: int | None,
    schedule: Iterable[MatchSlot],
) -> Sequence[tuple[MatchNumber, set[ArenaName]]]:
    """
    Given a collection of ``match_ids`` for which we have scores, the
    ``match_type`` currently under consideration, the number of the
    ``last_match`` which was scored and the list of all known matches determine
    which scores should be present but aren't.
    """

    # If no matches have been scored, no scores can be missing.
    if last_match is None:
        return ()

    expected = set()
    for num, match in enumerate(schedule):
        if num > last_match:
            break
        for arena, game in match.items():
            # Filter to the right type of matches -- we only ever deal
            # with one type at a time
            if game.type == match_type:
                id_ = (arena, game.num)
                expected.add(id_)

    missing_ids = expected - set(match_ids)
    missing = defaultdict(set)
    for arena, num in missing_ids:
        missing[num].add(arena)

    missing_items = sorted(missing.items())
    return missing_items


def validate_team_matches(
    matches: Iterable[MatchSlot],
    possible_teams: Iterable[TLA],
) -> Iterator[ValidationError]:
    """
    Check that all teams have been assigned league matches. We don't need (or
    want) to check the knockouts, since those are scheduled dynamically based
    on the list of teams.
    """

    teams_without_matches = find_teams_without_league_matches(
        matches,
        possible_teams,
    )
    if teams_without_matches:
        yield ValidationError(
            "The following teams have no league matches: {}".format(
                join_and(sorted(teams_without_matches)),
            ),
            code='teams-without-league-matches',
            source=None,
        )


def find_teams_without_league_matches(
    matches: Iterable[MatchSlot],
    possible_teams: Iterable[TLA],
) -> set[TLA]:
    """
    Find teams that don't have league matches.

    :param list matches: A list of matches.
    :param possible_teams: A list of possible teams.
    :return: A :class:`set` of teams without matches.
    """
    teams_used = set()
    for match in matches:
        for game in match.values():
            if game.type == MatchType.league:
                teams_used |= set(game.teams)

    teams_without_matches = set(possible_teams) - teams_used

    return teams_without_matches
